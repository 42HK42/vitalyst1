# Ticket 4.9: Interactive Node Dashboard

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement a comprehensive interactive node dashboard for the Vitalyst Knowledge Graph frontend that provides real-time insights into node data, validation progress, environmental metrics, and nutritional information. The system must support role-based views, real-time updates through WebSocket connections, interactive data visualization, and accessibility features while maintaining optimal performance and user experience as specified in the blueprint.

## Technical Details
1. Dashboard Container Implementation
```typescript
// src/components/dashboard/NodeDashboard.tsx
import { memo, useEffect, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAccessibility } from '../../hooks/useAccessibility';
import { useNodeStore } from '../../stores/nodeStore';
import { usePermissions } from '../../hooks/usePermissions';
import { ProgressCard } from './ProgressCard';
import { IssueTracker } from './IssueTracker';
import { EnvironmentalMetrics } from './EnvironmentalMetrics';
import { NutrientContent } from './NutrientContent';
import { ValidationHistory } from './ValidationHistory';
import { StatusBadge } from '../status/StatusBadge';
import { ErrorBoundary } from '../common/ErrorBoundary';
import { usePerformanceMonitor } from '../../hooks/usePerformanceMonitor';
import './NodeDashboard.css';

interface NodeDashboardProps {
  nodeId: string;
  showHistory?: boolean;
  showEnvironmental?: boolean;
  showNutrients?: boolean;
  onError?: (error: Error) => void;
}

export const NodeDashboard = memo(({
  nodeId,
  showHistory = true,
  showEnvironmental = true,
  showNutrients = true,
  onError
}: NodeDashboardProps) => {
  const { prefersReducedMotion } = useAccessibility();
  const { hasPermission } = usePermissions();
  const { trackRender } = usePerformanceMonitor();
  const queryClient = useQueryClient();
  const ws = useWebSocket('ws://localhost:8000/ws/nodes');

  // Fetch node data
  const { data: node, error } = useQuery({
    queryKey: ['node', nodeId],
    queryFn: () => fetchNodeData(nodeId)
  });

  // Handle real-time updates
  useEffect(() => {
    if (ws) {
      ws.addEventListener('message', (event) => {
        const update = JSON.parse(event.data);
        if (update.nodeId === nodeId) {
          queryClient.setQueryData(['node', nodeId], (oldData: any) => ({
            ...oldData,
            ...update.data
          }));
        }
      });
    }
  }, [ws, nodeId, queryClient]);

  // Calculate validation progress
  const validationProgress = useMemo(() => {
    if (!node) return 0;
    const { validatedFields, totalFields } = node;
    return (validatedFields / totalFields) * 100;
  }, [node]);

  if (error) {
    onError?.(error);
    return (
      <div className="dashboard-error" role="alert">
        <p>Failed to load dashboard data</p>
        <button 
          onClick={() => queryClient.invalidateQueries(['node', nodeId])}
          className="retry-button"
        >
          Retry
        </button>
      </div>
    );
  }

  if (!node) {
    return <LoadingSpinner size="large" />;
  }

  return (
    <ErrorBoundary
      fallback={
        <div className="dashboard-error">
          <p>An error occurred while displaying the dashboard</p>
        </div>
      }
    >
      <motion.div
        className="node-dashboard"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ 
          duration: prefersReducedMotion ? 0 : 0.3 
        }}
      >
        <header className="dashboard-header">
          <div className="header-content">
            <h2>{node.name}</h2>
            <StatusBadge 
              status={node.validation_status}
              nodeId={nodeId}
              size="large"
            />
          </div>
          {hasPermission('edit_nodes') && (
            <div className="header-actions">
              <motion.button
                onClick={() => handleEdit(nodeId)}
                whileHover={{ scale: 1.05 }}
                whileTap={{ scale: 0.95 }}
                className="action-button"
              >
                Edit
              </motion.button>
              {hasPermission('validate_nodes') && (
                <motion.button
                  onClick={() => handleValidate(nodeId)}
                  whileHover={{ scale: 1.05 }}
                  whileTap={{ scale: 0.95 }}
                  className="action-button validate"
                >
                  Validate
                </motion.button>
              )}
            </div>
          )}
        </header>

        <div className="dashboard-grid">
          <ProgressCard
            title="Validation Progress"
            percentage={validationProgress}
            metrics={[
              { 
                label: 'Validated Fields',
                value: node.validatedFields,
                icon: 'check'
              },
              { 
                label: 'Total Fields',
                value: node.totalFields,
                icon: 'list'
              }
            ]}
          />

          {hasPermission('view_issues') && (
            <IssueTracker
              issues={node.issues}
              onResolve={handleIssueResolution}
              onPrioritize={handleIssuePrioritization}
            />
          )}

          {showEnvironmental && (
            <EnvironmentalMetrics
              metrics={node.environmental}
              showHistory={hasPermission('view_history')}
              onThresholdAlert={handleThresholdAlert}
            />
          )}

          {showNutrients && (
            <NutrientContent
              nutrients={node.nutrients}
              showSourceInfo={hasPermission('view_sources')}
              onSourceVerify={handleSourceVerification}
            />
          )}

          {showHistory && hasPermission('view_history') && (
            <ValidationHistory
              history={node.validation_history}
              showUserInfo={hasPermission('view_user_info')}
            />
          )}
        </div>
      </motion.div>
    </ErrorBoundary>
  );
});

// src/components/dashboard/ProgressCard.tsx
interface ProgressCardProps {
  title: string;
  percentage: number;
  metrics: Array<{
    label: string;
    value: number;
    icon: string;
  }>;
}

export const ProgressCard = memo(({
  title,
  percentage,
  metrics
}: ProgressCardProps) => {
  const { prefersReducedMotion } = useAccessibility();

  return (
    <motion.div
      className="progress-card"
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: prefersReducedMotion ? 0 : 0.3 }}
    >
      <h3>{title}</h3>
      <div className="progress-circle">
        <svg viewBox="0 0 36 36">
          <motion.path
            d="M18 2.0845
              a 15.9155 15.9155 0 0 1 0 31.831
              a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="var(--progress-bg)"
            strokeWidth="3"
          />
          <motion.path
            d="M18 2.0845
              a 15.9155 15.9155 0 0 1 0 31.831
              a 15.9155 15.9155 0 0 1 0 -31.831"
            fill="none"
            stroke="var(--progress-fill)"
            strokeWidth="3"
            initial={{ strokeDasharray: "0, 100" }}
            animate={{ strokeDasharray: `${percentage}, 100` }}
            transition={{ 
              duration: prefersReducedMotion ? 0 : 1,
              ease: "easeOut"
            }}
          />
          <text x="18" y="20.35" className="progress-text">
            {percentage.toFixed(0)}%
          </text>
        </svg>
      </div>
      <div className="metrics-grid">
        {metrics.map(metric => (
          <div key={metric.label} className="metric">
            <span className="metric-icon">
              <Icon name={metric.icon} />
            </span>
            <span className="metric-label">{metric.label}</span>
            <span className="metric-value">{metric.value}</span>
          </div>
        ))}
      </div>
    </motion.div>
  );
});
```

2. Environmental Metrics Implementation
```typescript
// src/components/dashboard/EnvironmentalMetrics.tsx
import { memo, useMemo } from 'react';
import { motion } from 'framer-motion';
import { LineChart } from '../charts/LineChart';
import { MetricCard } from '../common/MetricCard';
import { useThresholds } from '../../hooks/useThresholds';
import { formatMetricValue } from '../../utils/formatting';
import { EnvironmentalMetric } from '../../types';

interface EnvironmentalMetricsProps {
  metrics: {
    co2: EnvironmentalMetric;
    water: EnvironmentalMetric;
    land: EnvironmentalMetric;
    biodiversity: EnvironmentalMetric;
  };
  showHistory?: boolean;
  onThresholdAlert?: (metric: string, value: number) => void;
}

export const EnvironmentalMetrics = memo(({
  metrics,
  showHistory = true,
  onThresholdAlert
}: EnvironmentalMetricsProps) => {
  const { getThreshold, checkThreshold } = useThresholds();

  const metricCards = useMemo(() => [
    {
      title: 'CO2 Footprint',
      value: metrics.co2.value,
      unit: 'kg CO2e',
      change: calculateChange(metrics.co2.history),
      threshold: getThreshold('co2'),
      icon: 'carbon'
    },
    {
      title: 'Water Usage',
      value: metrics.water.value,
      unit: 'L',
      change: calculateChange(metrics.water.history),
      threshold: getThreshold('water'),
      icon: 'water'
    },
    {
      title: 'Land Use',
      value: metrics.land.value,
      unit: 'm²',
      change: calculateChange(metrics.land.history),
      threshold: getThreshold('land'),
      icon: 'land'
    },
    {
      title: 'Biodiversity Impact',
      value: metrics.biodiversity.value,
      unit: 'PDF',
      change: calculateChange(metrics.biodiversity.history),
      threshold: getThreshold('biodiversity'),
      icon: 'nature'
    }
  ], [metrics, getThreshold]);

  // Check thresholds and trigger alerts
  useEffect(() => {
    metricCards.forEach(card => {
      if (checkThreshold(card.value, card.threshold)) {
        onThresholdAlert?.(card.title, card.value);
      }
    });
  }, [metricCards, checkThreshold, onThresholdAlert]);

  return (
    <div className="environmental-metrics">
      <h3>Environmental Impact</h3>
      <div className="metrics-grid">
        <AnimatePresence>
          {metricCards.map((card, index) => (
            <motion.div
              key={card.title}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              <MetricCard
                title={card.title}
                value={formatMetricValue(card.value)}
                unit={card.unit}
                change={card.change}
                icon={card.icon}
                threshold={card.threshold}
              />
            </motion.div>
          ))}
        </AnimatePresence>
      </div>

      {showHistory && (
        <div className="metrics-history">
          <LineChart
            data={combineMetricHistory(metrics)}
            height={200}
            margin={{ top: 20, right: 20, bottom: 30, left: 40 }}
            xAxis={{ 
              label: 'Time',
              tickFormat: (d: Date) => format(d, 'MMM d')
            }}
            yAxis={{ 
              label: 'Value',
              tickFormat: (v: number) => formatMetricValue(v)
            }}
          />
        </div>
      )}
    </div>
  );
});
```

3. Nutrient Content Implementation
```typescript
// src/components/dashboard/NutrientContent.tsx
import { memo, useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Table } from '../common/Table';
import { SourceInfo } from './SourceInfo';
import { formatNutrientValue } from '../../utils/formatting';
import { NutrientData, Source } from '../../types';

interface NutrientContentProps {
  nutrients: NutrientData[];
  showSourceInfo?: boolean;
  onSourceVerify?: (source: Source) => void;
}

export const NutrientContent = memo(({
  nutrients,
  showSourceInfo = false,
  onSourceVerify
}: NutrientContentProps) => {
  const [selectedNutrient, setSelectedNutrient] = useState<string | null>(null);

  const columns = [
    {
      header: 'Nutrient',
      accessor: 'name',
      sortable: true
    },
    {
      header: 'Amount',
      accessor: 'amount',
      cell: ({ value, unit }: { value: number; unit: string }) => (
        <span>{formatNutrientValue(value)} {unit}</span>
      ),
      sortable: true
    },
    {
      header: 'Daily Value',
      accessor: 'dailyValue',
      cell: ({ value }: { value: number }) => (
        <span>{value}%</span>
      ),
      sortable: true
    },
    {
      header: 'Confidence',
      accessor: 'confidence',
      cell: ({ value }: { value: number }) => (
        <ConfidenceIndicator value={value} />
      ),
      sortable: true
    }
  ];

  return (
    <div className="nutrient-content">
      <h3>Nutritional Information</h3>
      <Table
        data={nutrients}
        columns={columns}
        onRowClick={nutrient => setSelectedNutrient(nutrient.id)}
        sortable
        pagination
        pageSize={10}
      />

      <AnimatePresence>
        {showSourceInfo && selectedNutrient && (
          <motion.div
            className="source-info-modal"
            initial={{ opacity: 0, scale: 0.95 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.95 }}
          >
            <SourceInfo
              sources={nutrients.find(n => n.id === selectedNutrient)?.sources || []}
              onVerify={onSourceVerify}
              onClose={() => setSelectedNutrient(null)}
            />
          </motion.div>
        )}
      </AnimatePresence>
    </div>
  );
});
```

4. Dashboard Styling Implementation
```css
/* src/styles/NodeDashboard.css */
.node-dashboard {
  padding: 2rem;
  background: var(--surface-color);
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.dashboard-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
}

.header-content {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.header-actions {
  display: flex;
  gap: 0.5rem;
}

.action-button {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  background: var(--primary-color);
  color: white;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.action-button.validate {
  background: var(--success-color);
}

.action-button:hover {
  filter: brightness(1.1);
}

.action-button:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 2px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
}

.progress-card {
  background: white;
  padding: 1.5rem;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.05);
}

.progress-circle {
  width: 120px;
  height: 120px;
  margin: 1rem auto;
}

.progress-text {
  font-size: 8px;
  text-anchor: middle;
  fill: var(--text-primary);
  font-weight: 600;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-top: 1rem;
}

.metric {
  display: flex;
  flex-direction: column;
  align-items: center;
  text-align: center;
  padding: 1rem;
  background: var(--surface-secondary);
  border-radius: 8px;
}

.metric-icon {
  margin-bottom: 0.5rem;
  color: var(--primary-color);
}

.metric-label {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.metric-value {
  font-size: 1.25rem;
  font-weight: 600;
  color: var(--text-primary);
}

.dashboard-error {
  padding: 1rem;
  border: 1px solid var(--error-color);
  border-radius: 8px;
  background: var(--error-bg);
  color: var(--error-color);
  text-align: center;
}

.retry-button {
  margin-top: 1rem;
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  background: var(--error-color);
  color: white;
  font-weight: 500;
  cursor: pointer;
}

@media (prefers-reduced-motion: reduce) {
  .action-button,
  .progress-circle path {
    transition: none;
  }
}

@media (max-width: 768px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .metrics-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 480px) {
  .header-content {
    flex-direction: column;
    align-items: flex-start;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }
}
```

## Implementation Strategy
1. Core Components
   - Implement dashboard container
   - Create progress visualization
   - Develop metrics display
   - Set up real-time updates

2. Data Management
   - Implement data fetching
   - Set up WebSocket integration
   - Configure caching
   - Handle state updates

3. Visualization Components
   - Create progress indicators
   - Implement metric cards
   - Set up data charts
   - Configure animations

4. Accessibility & UX
   - Add ARIA attributes
   - Implement keyboard navigation
   - Configure screen reader support
   - Add reduced motion support

## Acceptance Criteria
- [ ] Dashboard layout with responsive design
- [ ] Real-time data updates via WebSocket
- [ ] Progress visualization with animations
- [ ] Environmental metrics display
- [ ] Nutrient content visualization
- [ ] Role-based component visibility
- [ ] Interactive data exploration
- [ ] Comprehensive accessibility support
- [ ] Performance optimization
- [ ] Error handling and recovery
- [ ] Loading states
- [ ] Documentation
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance tests

## Dependencies
- Ticket 4.1: Frontend Setup
- Ticket 4.2: Interactive Dashboard
- Ticket 4.7: Status Visualization
- Ticket 3.2: Core API Endpoints

## Estimated Hours
30

## Testing Requirements
- Unit Tests:
  - Test component rendering
  - Verify data updates
  - Test progress calculations
  - Validate metrics display
  - Test role-based access
  - Verify WebSocket integration
  - Test error handling
  - Validate accessibility

- Integration Tests:
  - Test data flow
  - Verify real-time updates
  - Test component interactions
  - Validate state management
  - Test error recovery
  - Verify role permissions

- Performance Tests:
  - Measure render times
  - Test update performance
  - Verify memory usage
  - Test large datasets
  - Monitor WebSocket efficiency
  - Validate animation performance

- Accessibility Tests:
  - Test keyboard navigation
  - Verify screen readers
  - Test color contrast
  - Validate ARIA labels
  - Test reduced motion
  - Verify focus management

## Documentation
- Component API reference
- WebSocket integration guide
- State management patterns
- Data visualization guide
- Performance optimization
- Accessibility features
- Testing procedures
- Error handling
- Upgrade procedures
- User interaction guide

## Search Space Optimization
- Clear component hierarchy
- Consistent naming patterns
- Standardized prop interfaces
- Logical file organization
- Well-documented utilities
- Organized test structure
- Clear state management
- Consistent styling patterns
- Standardized metric formats
- Organized WebSocket handlers

## References
- **Phasedplan.md:** Phase 4, Ticket 4.9
- **Blueprint.md:** Sections on UI/UX & CX
- React Component Guidelines
- WebSocket Best Practices
- Data Visualization Patterns
- WCAG Accessibility Guidelines

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the interactive node dashboard as specified in the blueprint, with particular attention to:
- Comprehensive data visualization
- Real-time updates
- Role-based access
- Performance optimization
- Accessibility compliance
- User experience
- Error handling
- Documentation standards
- Testing coverage
- Maintenance procedures 