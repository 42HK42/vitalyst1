# Ticket 6.1: OAuth Integration in Backend

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive OAuth integration in the FastAPI backend for the Vitalyst Knowledge Graph, using Auth0 as the identity provider. The system must handle user authentication, role mapping, secure token validation, and session management while following zero-trust security principles and maintaining optimal performance as specified in the blueprint. The implementation must support multiple identity providers, handle token rotation, provide detailed audit trails, and ensure secure session management.

## Technical Details
1. OAuth Middleware Implementation
```python
# src/middleware/auth.py
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import jwt, JWTError
from typing import Optional, Dict, List
import httpx
from functools import lru_cache
from datetime import datetime, timedelta
from src.monitoring import PerformanceMonitor
from src.logging import AuditLogger
from src.cache import TokenCache
from src.config import AuthConfig

class AuthMiddleware:
    def __init__(self, auth_config: AuthConfig):
        self.auth_config = auth_config
        self.security = HTTPBearer()
        self.jwks_client = None
        self.domain = auth_config.domain
        self.audience = auth_config.audience
        self.algorithms = ['RS256']
        self.token_cache = TokenCache()
        self.metrics = PerformanceMonitor('auth-middleware')
        self.audit_logger = AuditLogger('auth')
        self.http_client = httpx.AsyncClient(
            timeout=30.0,
            verify=True,
            http2=True
        )

    async def __call__(self, request: Request) -> Optional[Dict]:
        operation_id = f"auth_{request.url.path}"
        self.metrics.start_operation(operation_id)

        try:
            credentials: HTTPAuthorizationCredentials = await self.security(request)
            if not credentials:
                raise HTTPException(
                    status_code=401,
                    detail='No credentials provided'
                )

            token = credentials.credentials
            
            # Check token cache first
            cached_payload = await self.token_cache.get(token)
            if cached_payload:
                request.state.user = cached_payload
                self.metrics.end_operation(operation_id)
                return cached_payload

            # Validate token
            payload = await self.validate_token(token)
            
            # Enrich payload with roles and permissions
            enriched_payload = await self.enrich_token_payload(payload)
            
            # Cache validated token
            await self.token_cache.set(
                token,
                enriched_payload,
                ttl=self.calculate_token_ttl(payload)
            )

            request.state.user = enriched_payload
            
            # Log successful authentication
            await self.audit_logger.log_auth_event({
                'type': 'authentication_success',
                'user_id': enriched_payload.get('sub'),
                'roles': enriched_payload.get('roles', []),
                'ip': request.client.host,
                'path': request.url.path,
                'timestamp': datetime.utcnow()
            })

            self.metrics.end_operation(operation_id)
            return enriched_payload

        except Exception as e:
            self.metrics.record_error(operation_id, str(e))
            
            # Log authentication failure
            await self.audit_logger.log_auth_event({
                'type': 'authentication_failure',
                'error': str(e),
                'ip': request.client.host,
                'path': request.url.path,
                'timestamp': datetime.utcnow()
            })
            
            raise HTTPException(
                status_code=401,
                detail=str(e)
            )

    @lru_cache(maxsize=1)
    async def get_jwks(self) -> Dict:
        """Get JWKS from Auth0 with caching"""
        if not self.jwks_client:
            async with self.http_client as client:
                response = await client.get(
                    f'https://{self.domain}/.well-known/jwks.json'
                )
                response.raise_for_status()
                self.jwks_client = response.json()
        return self.jwks_client

    async def validate_token(self, token: str) -> Dict:
        """Validate JWT token with comprehensive checks"""
        try:
            jwks = await self.get_jwks()
            unverified_header = jwt.get_unverified_header(token)
            
            # Find matching key
            rsa_key = {}
            for key in jwks['keys']:
                if key['kid'] == unverified_header['kid']:
                    rsa_key = {
                        'kty': key['kty'],
                        'kid': key['kid'],
                        'n': key['n'],
                        'e': key['e']
                    }

            if not rsa_key:
                raise HTTPException(
                    status_code=401,
                    detail='Invalid token header'
                )

            # Decode and validate token
            payload = jwt.decode(
                token,
                rsa_key,
                algorithms=self.algorithms,
                audience=self.audience,
                issuer=f'https://{self.domain}/',
                options={
                    'verify_signature': True,
                    'verify_aud': True,
                    'verify_iat': True,
                    'verify_exp': True,
                    'verify_iss': True,
                    'leeway': 0
                }
            )

            return payload

        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=401,
                detail='Token has expired'
            )
        except jwt.JWTClaimsError:
            raise HTTPException(
                status_code=401,
                detail='Invalid claims'
            )
        except Exception as e:
            raise HTTPException(
                status_code=401,
                detail=f'Invalid token: {str(e)}'
            )

    async def enrich_token_payload(self, payload: Dict) -> Dict:
        """Enrich token payload with roles and permissions"""
        try:
            # Get user roles from Auth0 Management API
            roles = await self.get_user_roles(payload['sub'])
            
            # Map Auth0 roles to internal roles
            internal_roles = self.map_roles(roles)
            
            # Get permissions for roles
            permissions = await self.get_role_permissions(internal_roles)

            return {
                **payload,
                'roles': internal_roles,
                'permissions': permissions,
                'metadata': {
                    'last_verified': datetime.utcnow().isoformat(),
                    'verification_source': 'auth0_management_api'
                }
            }

        except Exception as e:
            self.audit_logger.log_error(
                'token_enrichment_failed',
                {'error': str(e), 'user_id': payload.get('sub')}
            )
            return payload

    def calculate_token_ttl(self, payload: Dict) -> int:
        """Calculate token TTL based on exp claim"""
        exp = payload.get('exp', 0)
        now = datetime.utcnow().timestamp()
        ttl = max(0, int(exp - now))
        return min(ttl, self.auth_config.max_token_ttl)

    async def get_metrics(self) -> Dict:
        """Get authentication metrics"""
        return {
            'operations': self.metrics.get_metrics(),
            'cache': await self.token_cache.get_metrics(),
            'active_sessions': await self.get_active_sessions(),
            'error_rates': self.get_error_rates(),
            'token_validations': {
                'total': self.metrics.get_counter('token_validations'),
                'success_rate': self.metrics.get_success_rate('token_validations'),
                'average_duration': self.metrics.get_average_duration('token_validations')
            }
        }
```

2. Role Mapping Implementation
```python
# src/services/role_mapper.py
from enum import Enum
from typing import List, Dict, Set
from pydantic import BaseModel
from src.monitoring import PerformanceMonitor
from src.logging import AuditLogger

class Role(Enum):
    ADMIN = 'admin'
    EDITOR = 'editor'
    REVIEWER = 'reviewer'
    PUBLIC = 'public'

class Permission(Enum):
    READ = 'read'
    WRITE = 'write'
    VALIDATE = 'validate'
    ENRICH = 'enrich'
    ADMIN = 'admin'

class RolePermissions(BaseModel):
    role: Role
    permissions: List[Permission]
    metadata: Dict = {}

class RoleMapper:
    def __init__(self):
        self.metrics = PerformanceMonitor('role-mapper')
        self.audit_logger = AuditLogger('roles')
        self.initialize_role_mappings()

    def initialize_role_mappings(self):
        self.role_map = {
            'auth0|admin': Role.ADMIN,
            'auth0|editor': Role.EDITOR,
            'auth0|reviewer': Role.REVIEWER,
            'auth0|public': Role.PUBLIC
        }

        self.permission_map = {
            Role.ADMIN: [
                Permission.READ,
                Permission.WRITE,
                Permission.VALIDATE,
                Permission.ENRICH,
                Permission.ADMIN
            ],
            Role.EDITOR: [
                Permission.READ,
                Permission.WRITE,
                Permission.ENRICH
            ],
            Role.REVIEWER: [
                Permission.READ,
                Permission.VALIDATE
            ],
            Role.PUBLIC: [
                Permission.READ
            ]
        }

        # Role inheritance
        self.role_hierarchy = {
            Role.ADMIN: {Role.EDITOR, Role.REVIEWER, Role.PUBLIC},
            Role.EDITOR: {Role.PUBLIC},
            Role.REVIEWER: {Role.PUBLIC},
            Role.PUBLIC: set()
        }

    def map_role(self, auth0_role: str) -> Role:
        """Map Auth0 role to internal role"""
        operation_id = f"map_role_{auth0_role}"
        self.metrics.start_operation(operation_id)

        try:
            role = self.role_map.get(auth0_role, Role.PUBLIC)
            
            self.audit_logger.log_event({
                'type': 'role_mapped',
                'auth0_role': auth0_role,
                'internal_role': role.value,
                'timestamp': datetime.utcnow()
            })

            self.metrics.end_operation(operation_id)
            return role

        except Exception as e:
            self.metrics.record_error(operation_id, str(e))
            return Role.PUBLIC

    def get_permissions(self, role: Role) -> Set[Permission]:
        """Get permissions for role including inherited permissions"""
        operation_id = f"get_permissions_{role.value}"
        self.metrics.start_operation(operation_id)

        try:
            # Get direct permissions
            permissions = set(self.permission_map.get(role, []))
            
            # Get inherited permissions
            for inherited_role in self.role_hierarchy.get(role, set()):
                permissions.update(self.permission_map.get(inherited_role, []))

            self.metrics.end_operation(operation_id)
            return permissions

        except Exception as e:
            self.metrics.record_error(operation_id, str(e))
            return {Permission.READ}

    def has_permission(
        self,
        role: Role,
        permission: Permission,
        context: Dict = None
    ) -> bool:
        """Check if role has permission in given context"""
        operation_id = f"check_permission_{role.value}_{permission.value}"
        self.metrics.start_operation(operation_id)

        try:
            has_permission = permission in self.get_permissions(role)
            
            # Log permission check
            self.audit_logger.log_event({
                'type': 'permission_check',
                'role': role.value,
                'permission': permission.value,
                'context': context,
                'result': has_permission,
                'timestamp': datetime.utcnow()
            })

            self.metrics.end_operation(operation_id)
            return has_permission

        except Exception as e:
            self.metrics.record_error(operation_id, str(e))
            return False

    async def get_metrics(self) -> Dict:
        """Get role mapping metrics"""
        return {
            'operations': self.metrics.get_metrics(),
            'role_mappings': {
                'total': len(self.role_map),
                'distribution': self.get_role_distribution()
            },
            'permission_checks': {
                'total': self.metrics.get_counter('permission_checks'),
                'success_rate': self.metrics.get_success_rate('permission_checks')
            }
        }
```

3. Session Management Implementation
```python
# src/services/session_manager.py
from typing import Dict, Optional
from datetime import datetime, timedelta
from src.cache import SessionCache
from src.monitoring import PerformanceMonitor
from src.logging import AuditLogger

class SessionManager:
    def __init__(self):
        self.cache = SessionCache()
        self.metrics = PerformanceMonitor('session-manager')
        self.audit_logger = AuditLogger('sessions')

    async def create_session(
        self,
        user_id: str,
        metadata: Dict
    ) -> str:
        """Create new session"""
        operation_id = f"create_session_{user_id}"
        self.metrics.start_operation(operation_id)

        try:
            session_id = self.generate_session_id()
            session_data = {
                'user_id': user_id,
                'created_at': datetime.utcnow().isoformat(),
                'last_accessed': datetime.utcnow().isoformat(),
                'metadata': metadata
            }

            await self.cache.set(
                f'session:{session_id}',
                session_data,
                ttl=self.calculate_session_ttl(metadata)
            )

            # Log session creation
            await self.audit_logger.log_event({
                'type': 'session_created',
                'session_id': session_id,
                'user_id': user_id,
                'metadata': metadata,
                'timestamp': datetime.utcnow()
            })

            self.metrics.end_operation(operation_id)
            return session_id

        except Exception as e:
            self.metrics.record_error(operation_id, str(e))
            raise

    async def get_session(
        self,
        session_id: str
    ) -> Optional[Dict]:
        """Get session data"""
        operation_id = f"get_session_{session_id}"
        self.metrics.start_operation(operation_id)

        try:
            session_data = await self.cache.get(f'session:{session_id}')
            if session_data:
                # Update last accessed
                session_data['last_accessed'] = datetime.utcnow().isoformat()
                await self.cache.set(
                    f'session:{session_id}',
                    session_data,
                    ttl=self.calculate_session_ttl(session_data.get('metadata', {}))
                )

            self.metrics.end_operation(operation_id)
            return session_data

        except Exception as e:
            self.metrics.record_error(operation_id, str(e))
            return None

    async def invalidate_session(
        self,
        session_id: str,
        reason: str = 'user_logout'
    ) -> None:
        """Invalidate session"""
        operation_id = f"invalidate_session_{session_id}"
        self.metrics.start_operation(operation_id)

        try:
            session_data = await self.cache.get(f'session:{session_id}')
            if session_data:
                await self.cache.delete(f'session:{session_id}')
                
                # Log session invalidation
                await self.audit_logger.log_event({
                    'type': 'session_invalidated',
                    'session_id': session_id,
                    'user_id': session_data.get('user_id'),
                    'reason': reason,
                    'timestamp': datetime.utcnow()
                })

            self.metrics.end_operation(operation_id)

        except Exception as e:
            self.metrics.record_error(operation_id, str(e))
            raise

    def calculate_session_ttl(self, metadata: Dict) -> int:
        """Calculate session TTL based on metadata"""
        base_ttl = int(timedelta(hours=24).total_seconds())
        
        # Adjust TTL based on user role
        role_ttl_map = {
            'admin': timedelta(hours=4),
            'editor': timedelta(hours=8),
            'reviewer': timedelta(hours=12),
            'public': timedelta(hours=24)
        }
        
        role = metadata.get('role', 'public')
        return int(role_ttl_map.get(role, timedelta(hours=24)).total_seconds())

    async def get_metrics(self) -> Dict:
        """Get session metrics"""
        return {
            'operations': self.metrics.get_metrics(),
            'sessions': {
                'active': await self.get_active_session_count(),
                'distribution': await self.get_session_distribution(),
                'average_duration': await self.get_average_session_duration()
            },
            'cache': await self.cache.get_metrics()
        }
```

## Implementation Strategy
1. OAuth Integration
   - Implement Auth0 integration
   - Set up token validation
   - Configure role mapping
   - Implement session management

2. Security Implementation
   - Configure JWT validation
   - Set up role-based access
   - Implement token rotation
   - Configure audit logging

3. Performance Optimization
   - Implement token caching
   - Set up metrics collection
   - Configure performance monitoring
   - Optimize validation chains

4. Session Management
   - Implement session handling
   - Set up session storage
   - Configure session validation
   - Implement session cleanup

## Acceptance Criteria
- [ ] Auth0 integration complete
- [ ] Token validation implemented
- [ ] Role mapping configured
- [ ] Session management working
- [ ] Performance optimization complete
- [ ] Security measures implemented
- [ ] Audit logging configured
- [ ] Metrics collection working
- [ ] Documentation complete
- [ ] All tests passing
- [ ] Error handling implemented
- [ ] Monitoring configured

## Dependencies
- Ticket 3.1: Backend Setup
- Ticket 3.2: Core API Endpoints
- Ticket 3.3: Zero-Trust Security

## Estimated Hours
40

## Testing Requirements
- Unit Tests:
  - Test token validation
  - Verify role mapping
  - Test session management
  - Validate caching
  - Test error handling
  - Verify audit logging

- Integration Tests:
  - Test Auth0 integration
  - Verify token flow
  - Test role-based access
  - Validate session handling
  - Test performance monitoring
  - Verify metrics collection

- Performance Tests:
  - Measure token validation
  - Test concurrent sessions
  - Verify cache performance
  - Test session cleanup
  - Monitor resource usage
  - Validate optimization

- Security Tests:
  - Test token security
  - Verify role enforcement
  - Test session security
  - Validate audit trails
  - Test error handling
  - Verify zero-trust principles

## Documentation
- OAuth integration guide
- Token validation details
- Role mapping configuration
- Session management guide
- Performance optimization
- Security measures
- Monitoring setup
- Error handling procedures
- Testing guidelines
- API reference
- Configuration guide

## Search Space Optimization
- Clear service hierarchy
- Consistent naming patterns
- Standardized interfaces
- Logical file organization
- Well-documented utilities
- Organized test structure
- Clear state management
- Consistent error handling
- Standardized metrics
- Organized security patterns

## References
- **Phasedplan.md:** Phase 6, Ticket 6.1
- **Blueprint.md:** Sections on Authentication and Security
- Auth0 Documentation
- FastAPI Security Guidelines
- OAuth 2.0 Best Practices
- Zero Trust Architecture Guidelines

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the OAuth integration as specified in the blueprint, with particular attention to:
- Secure authentication
- Role-based access
- Session management
- Performance optimization
- Security measures
- Audit logging
- Error handling
- Documentation standards
- Testing coverage
- Monitoring integration
``` 