# Ticket 6.2: Role Mapping and UI Routing

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive role mapping and UI routing system for the Vitalyst Knowledge Graph frontend that maps authenticated roles to UI components, routes users to appropriate dashboards, and manages authentication state. The system must provide role-specific views, secure route protection, real-time role updates, and optimized component loading while maintaining a seamless user experience and following zero-trust security principles as specified in the blueprint.

## Technical Details
1. Authentication Context Implementation
```typescript
// src/context/AuthContext.tsx
import { createContext, useContext, useEffect, useState, useCallback } from 'react';
import { useAuth0 } from '@auth0/auth0-react';
import { useNavigate } from 'react-router-dom';
import { Role, Permission, AuthState, AuthMetrics } from '../types/auth';
import { PerformanceMonitor } from '../monitoring/PerformanceMonitor';
import { AuditLogger } from '../logging/AuditLogger';
import { useRoleStore } from '../stores/roleStore';
import { usePermissionCache } from '../cache/permissionCache';

interface AuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  role: Role;
  permissions: Permission[];
  user: any;
  hasPermission: (permission: Permission, context?: any) => boolean;
  refreshAuth: () => Promise<void>;
  getMetrics: () => Promise<AuthMetrics>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const {
    isAuthenticated,
    isLoading,
    user,
    getAccessTokenSilently
  } = useAuth0();
  const navigate = useNavigate();
  const [authState, setAuthState] = useState<AuthState>({
    role: 'public',
    permissions: [],
    lastUpdated: null
  });
  const metrics = new PerformanceMonitor('auth-context');
  const auditLogger = new AuditLogger('auth');
  const roleStore = useRoleStore();
  const permissionCache = usePermissionCache();

  const initializeAuth = useCallback(async () => {
    const operationId = 'initialize_auth';
    metrics.startOperation(operationId);

    try {
      if (isAuthenticated && user) {
        // Get access token and user metadata
        const token = await getAccessTokenSilently();
        const userRole = await fetchUserRole(token);
        const userPermissions = await fetchUserPermissions(token);

        // Update state and stores
        setAuthState({
          role: userRole,
          permissions: userPermissions,
          lastUpdated: new Date()
        });
        roleStore.setRole(userRole);
        await permissionCache.setPermissions(userPermissions);

        // Log successful initialization
        await auditLogger.logEvent({
          type: 'auth_initialized',
          user_id: user.sub,
          role: userRole,
          timestamp: new Date()
        });

        metrics.endOperation(operationId);
      }
    } catch (error) {
      metrics.recordError(operationId, error);
      
      // Log initialization failure
      await auditLogger.logEvent({
        type: 'auth_initialization_failed',
        error: error.message,
        timestamp: new Date()
      });

      // Fallback to public role
      setAuthState({
        role: 'public',
        permissions: ['read'],
        lastUpdated: new Date()
      });
      roleStore.setRole('public');
    }
  }, [isAuthenticated, user, getAccessTokenSilently]);

  useEffect(() => {
    initializeAuth();
  }, [initializeAuth]);

  const hasPermission = useCallback((
    permission: Permission,
    context?: any
  ): boolean => {
    const operationId = `check_permission_${permission}`;
    metrics.startOperation(operationId);

    try {
      const hasPermission = authState.permissions.includes(permission);
      
      // Log permission check
      auditLogger.logEvent({
        type: 'permission_checked',
        permission,
        context,
        result: hasPermission,
        timestamp: new Date()
      });

      metrics.endOperation(operationId);
      return hasPermission;
    } catch (error) {
      metrics.recordError(operationId, error);
      return false;
    }
  }, [authState.permissions]);

  const refreshAuth = useCallback(async () => {
    const operationId = 'refresh_auth';
    metrics.startOperation(operationId);

    try {
      await initializeAuth();
      metrics.endOperation(operationId);
    } catch (error) {
      metrics.recordError(operationId, error);
      throw error;
    }
  }, [initializeAuth]);

  const getMetrics = useCallback(async (): Promise<AuthMetrics> => {
    return {
      operations: metrics.getMetrics(),
      roleUpdates: roleStore.getMetrics(),
      permissionChecks: {
        total: metrics.getCounter('permission_checks'),
        success_rate: metrics.getSuccessRate('permission_checks')
      },
      cacheHits: await permissionCache.getMetrics()
    };
  }, []);

  return (
    <AuthContext.Provider
      value={{
        isAuthenticated,
        isLoading,
        role: authState.role,
        permissions: authState.permissions,
        user,
        hasPermission,
        refreshAuth,
        getMetrics
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}
```

2. Protected Route Implementation
```typescript
// src/components/routing/ProtectedRoute.tsx
import { Navigate, useLocation } from 'react-router-dom';
import { useAuth } from '../../hooks/useAuth';
import { Permission, RouteConfig } from '../../types/auth';
import { PerformanceMonitor } from '../../monitoring/PerformanceMonitor';
import { AuditLogger } from '../../logging/AuditLogger';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ErrorBoundary } from '../common/ErrorBoundary';

interface ProtectedRouteProps {
  children: React.ReactNode;
  config: RouteConfig;
}

export function ProtectedRoute({
  children,
  config
}: ProtectedRouteProps) {
  const { isAuthenticated, isLoading, hasPermission, role } = useAuth();
  const location = useLocation();
  const metrics = new PerformanceMonitor('protected-route');
  const auditLogger = new AuditLogger('routing');

  const operationId = `route_access_${location.pathname}`;
  metrics.startOperation(operationId);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  if (!isAuthenticated) {
    // Log unauthorized access attempt
    auditLogger.logEvent({
      type: 'unauthorized_access',
      path: location.pathname,
      timestamp: new Date()
    });

    metrics.endOperation(operationId);
    return <Navigate to="/login" state={{ from: location }} replace />;
  }

  // Check role-based access
  if (config.roles && !config.roles.includes(role)) {
    // Log role-based access denial
    auditLogger.logEvent({
      type: 'role_access_denied',
      path: location.pathname,
      role,
      required_roles: config.roles,
      timestamp: new Date()
    });

    metrics.endOperation(operationId);
    return <Navigate to="/unauthorized" replace />;
  }

  // Check permissions
  const hasRequiredPermissions = config.permissions.every(permission =>
    hasPermission(permission, { path: location.pathname })
  );

  if (!hasRequiredPermissions) {
    // Log permission-based access denial
    auditLogger.logEvent({
      type: 'permission_access_denied',
      path: location.pathname,
      role,
      required_permissions: config.permissions,
      timestamp: new Date()
    });

    metrics.endOperation(operationId);
    return <Navigate to="/unauthorized" replace />;
  }

  // Log successful access
  auditLogger.logEvent({
    type: 'route_accessed',
    path: location.pathname,
    role,
    timestamp: new Date()
  });

  metrics.endOperation(operationId);

  return (
    <ErrorBoundary>
      {children}
    </ErrorBoundary>
  );
}
```

3. Role-Based Dashboard Implementation
```typescript
// src/components/dashboard/DashboardRouter.tsx
import { Suspense, lazy } from 'react';
import { useAuth } from '../../hooks/useAuth';
import { Role } from '../../types/auth';
import { PerformanceMonitor } from '../../monitoring/PerformanceMonitor';
import { AuditLogger } from '../../logging/AuditLogger';
import { LoadingSpinner } from '../common/LoadingSpinner';
import { ErrorBoundary } from '../common/ErrorBoundary';

// Lazy load dashboards for better performance
const AdminDashboard = lazy(() => import('./AdminDashboard'));
const EditorDashboard = lazy(() => import('./EditorDashboard'));
const ReviewerDashboard = lazy(() => import('./ReviewerDashboard'));
const PublicDashboard = lazy(() => import('./PublicDashboard'));

const dashboardConfig: Record<Role, {
  component: React.ComponentType;
  preload?: () => void;
  features: string[];
}> = {
  admin: {
    component: AdminDashboard,
    preload: () => import('./AdminDashboard'),
    features: ['validation', 'enrichment', 'monitoring']
  },
  editor: {
    component: EditorDashboard,
    preload: () => import('./EditorDashboard'),
    features: ['editing', 'enrichment']
  },
  reviewer: {
    component: ReviewerDashboard,
    preload: () => import('./ReviewerDashboard'),
    features: ['validation']
  },
  public: {
    component: PublicDashboard,
    preload: () => import('./PublicDashboard'),
    features: ['viewing']
  }
};

export function DashboardRouter() {
  const { role, isLoading } = useAuth();
  const metrics = new PerformanceMonitor('dashboard-router');
  const auditLogger = new AuditLogger('dashboard');

  const operationId = `load_dashboard_${role}`;
  metrics.startOperation(operationId);

  if (isLoading) {
    return <LoadingSpinner />;
  }

  const config = dashboardConfig[role];
  
  // Preload dashboard if configured
  if (config.preload) {
    config.preload();
  }

  // Log dashboard access
  auditLogger.logEvent({
    type: 'dashboard_accessed',
    role,
    features: config.features,
    timestamp: new Date()
  });

  const Dashboard = config.component;

  metrics.endOperation(operationId);

  return (
    <ErrorBoundary>
      <Suspense fallback={<LoadingSpinner />}>
        <Dashboard />
      </Suspense>
    </ErrorBoundary>
  );
}

// src/components/dashboard/InternalDashboard.tsx
export function InternalDashboard() {
  const { hasPermission } = useAuth();
  const metrics = new PerformanceMonitor('internal-dashboard');

  return (
    <div className="dashboard-container">
      <Sidebar>
        <DashboardNav />
        {hasPermission('validate') && (
          <ValidationQueueWidget />
        )}
        {hasPermission('enrich') && (
          <EnrichmentQueueWidget />
        )}
      </Sidebar>

      <main className="dashboard-content">
        <ErrorBoundary>
          <Suspense fallback={<LoadingSpinner />}>
            <GraphVisualization />
            <DetailPanel />
            <ActionPanel />
          </Suspense>
        </ErrorBoundary>
      </main>

      {hasPermission('admin') && (
        <AdminPanel />
      )}
    </div>
  );
}
```

4. Authentication State Management
```typescript
// src/stores/authStore.ts
import { create } from 'zustand';
import { persist } from 'zustand/middleware';
import { Role, Permission, AuthState } from '../types/auth';
import { PerformanceMonitor } from '../monitoring/PerformanceMonitor';
import { AuditLogger } from '../logging/AuditLogger';

interface AuthStore extends AuthState {
  setRole: (role: Role) => void;
  setPermissions: (permissions: Permission[]) => void;
  clearAuth: () => void;
  getMetrics: () => Promise<any>;
}

const metrics = new PerformanceMonitor('auth-store');
const auditLogger = new AuditLogger('auth-store');

export const useAuthStore = create<AuthStore>()(
  persist(
    (set, get) => ({
      role: 'public',
      permissions: [],
      lastUpdated: null,

      setRole: (role: Role) => {
        const operationId = `set_role_${role}`;
        metrics.startOperation(operationId);

        try {
          set({ role, lastUpdated: new Date() });
          
          auditLogger.logEvent({
            type: 'role_updated',
            role,
            timestamp: new Date()
          });

          metrics.endOperation(operationId);
        } catch (error) {
          metrics.recordError(operationId, error);
          throw error;
        }
      },

      setPermissions: (permissions: Permission[]) => {
        const operationId = 'set_permissions';
        metrics.startOperation(operationId);

        try {
          set({ permissions, lastUpdated: new Date() });
          
          auditLogger.logEvent({
            type: 'permissions_updated',
            permissions,
            timestamp: new Date()
          });

          metrics.endOperation(operationId);
        } catch (error) {
          metrics.recordError(operationId, error);
          throw error;
        }
      },

      clearAuth: () => {
        const operationId = 'clear_auth';
        metrics.startOperation(operationId);

        try {
          set({
            role: 'public',
            permissions: [],
            lastUpdated: new Date()
          });
          
          auditLogger.logEvent({
            type: 'auth_cleared',
            timestamp: new Date()
          });

          metrics.endOperation(operationId);
        } catch (error) {
          metrics.recordError(operationId, error);
          throw error;
        }
      },

      getMetrics: async () => {
        return {
          operations: metrics.getMetrics(),
          state_updates: {
            role_updates: metrics.getCounter('set_role'),
            permission_updates: metrics.getCounter('set_permissions'),
            clears: metrics.getCounter('clear_auth')
          },
          performance: {
            average_update_duration: metrics.getAverageOperationDuration(),
            error_rate: metrics.getErrorRate()
          }
        };
      }
    }),
    {
      name: 'auth-store',
      partialize: (state) => ({
        role: state.role,
        permissions: state.permissions
      })
    }
  )
);
```

## Implementation Strategy
1. Authentication Context
   - Implement Auth0 context integration
   - Set up role management
   - Configure permission handling
   - Implement state persistence

2. Route Protection
   - Implement protected routes
   - Set up role-based access
   - Configure permission checks
   - Implement route guards

3. Dashboard Implementation
   - Create role-specific dashboards
   - Implement lazy loading
   - Set up feature flags
   - Configure component access

4. Performance Optimization
   - Implement code splitting
   - Set up route preloading
   - Configure component caching
   - Optimize state updates

## Acceptance Criteria
- [ ] Auth0 context integration complete
- [ ] Role-based routing implemented
- [ ] Protected routes configured
- [ ] Role-specific dashboards working
- [ ] Permission checks implemented
- [ ] Lazy loading configured
- [ ] Performance optimization complete
- [ ] State management working
- [ ] Error handling implemented
- [ ] Audit logging configured
- [ ] Documentation complete
- [ ] All tests passing

## Dependencies
- Ticket 6.1: OAuth Integration
- Ticket 4.1: Frontend Setup
- Ticket 4.2: Interactive Dashboard

## Estimated Hours
35

## Testing Requirements
- Unit Tests:
  - Test authentication context
  - Verify role mapping
  - Test permission checks
  - Validate route protection
  - Test state management
  - Verify error handling

- Integration Tests:
  - Test route protection
  - Verify dashboard loading
  - Test role transitions
  - Validate state persistence
  - Test error recovery
  - Verify audit logging

- Performance Tests:
  - Measure route transitions
  - Test lazy loading
  - Verify state updates
  - Test component caching
  - Monitor memory usage
  - Validate optimization

- User Flow Tests:
  - Test role-based navigation
  - Verify permission enforcement
  - Test dashboard features
  - Validate error messages
  - Test loading states
  - Verify user experience

## Documentation
- Authentication context guide
- Route protection overview
- Dashboard implementation
- Performance optimization
- State management guide
- Error handling procedures
- Testing guidelines
- Component access control
- Audit logging setup
- Configuration guide

## Search Space Optimization
- Clear component hierarchy
- Consistent naming patterns
- Standardized interfaces
- Logical route organization
- Well-documented hooks
- Organized state management
- Clear error handling
- Consistent logging patterns
- Standardized metrics
- Organized test structure

## References
- **Phasedplan.md:** Phase 6, Ticket 6.2
- **Blueprint.md:** Sections on UI/UX & CX, Authentication
- React Router Documentation
- Auth0 React SDK Guidelines
- Frontend Security Best Practices
- Performance Optimization Guidelines

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the role mapping and UI routing as specified in the blueprint, with particular attention to:
- Secure authentication
- Role-based access
- Component optimization
- Performance monitoring
- State management
- Error handling
- Documentation standards
- Testing coverage
- User experience
- Audit logging
``` 