# Ticket 3.1: Setup FastAPI Application

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive FastAPI application setup for the Vitalyst Knowledge Graph that establishes the foundation for secure, scalable, and maintainable backend services. The implementation must include structured logging, error handling, monitoring integration, and security configurations while following the blueprint specifications for API development and zero-trust principles.

## Technical Details

1. Application Structure Implementation
```python
# src/main.py
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.security import HTTPBearer
from contextlib import asynccontextmanager
from prometheus_client import Counter, Histogram
import structlog
import time
import uuid

# Metrics setup
REQUEST_COUNT = Counter(
    'http_requests_total',
    'Total HTTP requests',
    ['method', 'endpoint', 'status']
)

REQUEST_LATENCY = Histogram(
    'http_request_duration_seconds',
    'HTTP request latency',
    ['method', 'endpoint']
)

# Structured logger setup
logger = structlog.get_logger()

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("application_startup", 
        version=app.version,
        environment=app.state.environment
    )
    
    # Initialize services
    await initialize_services(app)
    
    yield
    
    # Shutdown
    logger.info("application_shutdown")
    await cleanup_services(app)

app = FastAPI(
    title="Vitalyst Knowledge Graph API",
    description="API for managing nutritional knowledge graph data",
    version="1.0.0",
    lifespan=lifespan
)

# Security middleware
security = HTTPBearer()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Metrics middleware
@app.middleware("http")
async def metrics_middleware(request: Request, call_next):
    start_time = time.time()
    method = request.method
    path = request.url.path
    
    try:
        response = await call_next(request)
        status = response.status_code
        return response
    except Exception as e:
        status = 500
        raise e
    finally:
        duration = time.time() - start_time
        REQUEST_COUNT.labels(
            method=method,
            endpoint=path,
            status=status
        ).inc()
        REQUEST_LATENCY.labels(
            method=method,
            endpoint=path
        ).observe(duration)

# Logging middleware
@app.middleware("http")
async def logging_middleware(request: Request, call_next):
    start_time = time.time()
    
    log_context = {
        "request_id": request.state.request_id,
        "method": request.method,
        "path": request.url.path,
        "client_ip": request.client.host,
        "user_agent": request.headers.get("user-agent")
    }
    
    logger.info("request_started", **log_context)
    
    try:
        response = await call_next(request)
        duration = time.time() - start_time
        
        logger.info("request_completed",
            **log_context,
            status_code=response.status_code,
            duration=duration
        )
        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error("request_failed",
            **log_context,
            error=str(e),
            duration=duration
        )
        raise

# Error handler
@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    logger.error("http_error",
        request_id=request.state.request_id,
        status_code=exc.status_code,
        detail=exc.detail
    )
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "request_id": request.state.request_id
        }
    )

# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "ok",
        "version": app.version,
        "environment": app.state.environment
    }

# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Vitalyst Knowledge Graph API",
        "version": app.version,
        "docs_url": "/docs"
    }
```

2. Logging Configuration Implementation
```python
# src/config/logging.py
import structlog
import logging
import json
from typing import Any, Dict

def setup_logging(
    level: str = "INFO",
    json_format: bool = True
) -> None:
    """Configure structured logging"""
    logging.basicConfig(
        format="%(message)s",
        level=level
    )

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.UnicodeDecoder(),
            structlog.processors.JSONRenderer() if json_format
            else structlog.processors.KeyValueRenderer()
        ],
        logger_factory=structlog.PrintLoggerFactory(),
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(level)
        ),
        cache_logger_on_first_use=True,
    )
```

3. Service Initialization Implementation
```python
# src/services/initialization.py
from fastapi import FastAPI
from neo4j import AsyncGraphDatabase
from redis import asyncio as aioredis
from typing import Dict, Any

async def initialize_services(app: FastAPI) -> None:
    """Initialize application services"""
    # Neo4j connection
    app.state.neo4j = AsyncGraphDatabase.driver(
        app.state.config.NEO4J_URI,
        auth=(app.state.config.NEO4J_USER, app.state.config.NEO4J_PASSWORD)
    )
    
    # Redis connection
    app.state.redis = await aioredis.from_url(
        app.state.config.REDIS_URL,
        encoding="utf-8",
        decode_responses=True
    )
    
    # Initialize other services
    await initialize_metrics_service(app)
    await initialize_security_service(app)
    await initialize_cache_service(app)

async def cleanup_services(app: FastAPI) -> None:
    """Cleanup application services"""
    # Close Neo4j connection
    await app.state.neo4j.close()
    
    # Close Redis connection
    await app.state.redis.close()
    
    # Cleanup other services
    await cleanup_metrics_service(app)
    await cleanup_security_service(app)
    await cleanup_cache_service(app)
```

4. Configuration Management Implementation
```python
# src/config/settings.py
from pydantic import BaseSettings, validator
from typing import List, Optional
import os

class Settings(BaseSettings):
    # Application settings
    APP_NAME: str = "vitalyst"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = False
    
    # Server settings
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    WORKERS: int = 4
    
    # Security settings
    SECRET_KEY: str
    ALLOWED_HOSTS: List[str] = ["*"]
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]
    
    # Database settings
    NEO4J_URI: str
    NEO4J_USER: str
    NEO4J_PASSWORD: str
    
    # Redis settings
    REDIS_URL: str
    
    # Monitoring settings
    PROMETHEUS_ENABLED: bool = True
    METRICS_PREFIX: str = "vitalyst"
    
    # Logging settings
    LOG_LEVEL: str = "INFO"
    LOG_FORMAT: str = "json"
    
    class Config:
        env_file = ".env"
        case_sensitive = True

    @validator("SECRET_KEY", pre=True)
    def validate_secret_key(cls, v: Optional[str]) -> str:
        if not v:
            raise ValueError("SECRET_KEY must be set")
        return v
```

## Implementation Strategy
1. Application Setup
   - Create FastAPI application structure
   - Configure middleware stack
   - Set up error handling
   - Implement health checks

2. Logging System
   - Configure structured logging
   - Set up request logging
   - Implement error logging
   - Configure log formats

3. Monitoring Integration
   - Set up Prometheus metrics
   - Configure request tracking
   - Implement performance monitoring
   - Set up health checks

4. Service Management
   - Implement service initialization
   - Configure cleanup procedures
   - Set up dependency injection
   - Implement configuration management

## Acceptance Criteria
- [ ] FastAPI application successfully initialized with all middleware
- [ ] Structured JSON logging configured and working
- [ ] Error handling middleware implemented and tested
- [ ] Health check endpoint returning correct status
- [ ] Request ID middleware adding unique identifiers
- [ ] Metrics middleware collecting performance data
- [ ] CORS configured according to security requirements
- [ ] Service initialization and cleanup working
- [ ] Configuration management implemented
- [ ] Documentation generated and accessible
- [ ] All tests passing
- [ ] Logging format validated
- [ ] Metrics collection verified
- [ ] Security headers configured

## Dependencies
- Ticket 1.3: Environment Configuration
- Ticket 1.4: Dependency Installation
- Ticket 1.5: Docker & Compose Setup
- Ticket 2.1: Neo4j Deployment

## Estimated Hours
15

## Testing Requirements
- Unit Tests
  - Test application initialization
  - Verify middleware functionality
  - Check error handling
  - Validate logging format
- Integration Tests
  - Test service connections
  - Verify metrics collection
  - Check logging pipeline
  - Test health checks
- Performance Tests
  - Measure request latency
  - Test concurrent requests
  - Verify memory usage
  - Check logging performance
- Security Tests
  - Verify CORS settings
  - Test security headers
  - Check request validation
  - Validate error responses

## Documentation
- Application architecture overview
- Middleware configuration guide
- Logging format specification
- Metrics collection guide
- Service initialization procedures
- Configuration management
- Error handling patterns
- Security considerations
- Performance optimization
- Testing procedures

## Search Space Optimization
- Clear application structure
- Consistent middleware organization
- Standardized logging patterns
- Organized service management
- Structured configuration handling

## References
- Blueprint Section 3: API und Datenimport
- Blueprint Section 9: Frameworks, Deployment, Security & Monitoring
- Blueprint Section 4: Development Standards
- FastAPI Documentation
- Prometheus Python Client
- Structlog Documentation

## Notes
- Implements comprehensive application setup
- Ensures proper error handling
- Optimizes for monitoring
- Maintains security standards
- Supports scalability 