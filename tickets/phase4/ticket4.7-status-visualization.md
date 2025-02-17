# Ticket 4.7: Status Visualization System

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement a comprehensive status visualization system for the Vitalyst Knowledge Graph frontend that provides clear, real-time visual feedback about node states, validation progress, and system operations. The system must support hierarchical status visualization, real-time updates through WebSocket connections, role-based status views, and accessibility features while maintaining optimal performance and user experience as specified in the blueprint.

## Technical Details
1. Status Badge Component Implementation
```typescript
// src/components/status/StatusBadge.tsx
import { memo, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useStatusStore } from '../../stores/statusStore';
import { useAccessibility } from '../../hooks/useAccessibility';
import { Tooltip } from '../common/Tooltip';
import { ValidationStatus, StatusConfig } from '../../types';
import './StatusBadge.css';

interface StatusBadgeProps {
  status: ValidationStatus;
  nodeId: string;
  showTooltip?: boolean;
  animate?: boolean;
  size?: 'small' | 'medium' | 'large';
  showHistory?: boolean;
}

const statusConfig: Record<ValidationStatus, StatusConfig> = {
  draft: {
    color: '#9CA3AF',
    backgroundColor: '#F3F4F6',
    icon: '📝',
    description: 'Initial draft, pending review',
    priority: 1
  },
  pending_review: {
    color: '#FCD34D',
    backgroundColor: '#FEF3C7',
    icon: '⏳',
    description: 'Awaiting expert review',
    priority: 2
  },
  approved: {
    color: '#34D399',
    backgroundColor: '#D1FAE5',
    icon: '✓',
    description: 'Validated and approved',
    priority: 3
  },
  rejected: {
    color: '#EF4444',
    backgroundColor: '#FEE2E2',
    icon: '✗',
    description: 'Changes required',
    priority: 4
  },
  needs_revision: {
    color: '#F97316',
    backgroundColor: '#FFEDD5',
    icon: '⚠️',
    description: 'Requires updates',
    priority: 5
  },
  enriching: {
    color: '#60A5FA',
    backgroundColor: '#DBEAFE',
    icon: '🔄',
    description: 'AI enrichment in progress',
    priority: 6
  }
};

export const StatusBadge = memo(({
  status,
  nodeId,
  showTooltip = true,
  animate = true,
  size = 'medium',
  showHistory = false
}: StatusBadgeProps) => {
  const { prefersReducedMotion } = useAccessibility();
  const { updateStatus, addHistoryEntry } = useStatusStore();
  const ws = useWebSocket('ws://localhost:8000/ws/status');

  useEffect(() => {
    if (ws) {
      ws.addEventListener('message', (event) => {
        const update = JSON.parse(event.data);
        if (update.nodeId === nodeId) {
          updateStatus(nodeId, update.status);
          addHistoryEntry(nodeId, {
            status: update.status,
            timestamp: update.timestamp,
            user: update.user
          });
        }
      });
    }
  }, [ws, nodeId, updateStatus, addHistoryEntry]);

  const config = statusConfig[status];
  
  const badgeContent = (
    <motion.div
      className={`status-badge ${size}`}
      initial={animate && !prefersReducedMotion ? { scale: 0.8, opacity: 0 } : false}
      animate={{
        backgroundColor: config.backgroundColor,
        color: config.color,
        scale: 1,
        opacity: 1
      }}
      transition={{
        duration: 0.3,
        ease: 'easeOut'
      }}
      role="status"
      aria-label={`Status: ${status.replace('_', ' ')}`}
    >
      <span 
        className="status-icon" 
        role="img" 
        aria-hidden="true"
      >
        {config.icon}
      </span>
      <span className="status-text">
        {status.replace('_', ' ')}
      </span>
      {showHistory && (
        <motion.button
          className="history-button"
          onClick={() => showHistoryDialog(nodeId)}
          whileHover={{ scale: 1.1 }}
          whileTap={{ scale: 0.95 }}
          aria-label="Show status history"
        >
          <HistoryIcon />
        </motion.button>
      )}
    </motion.div>
  );

  return showTooltip ? (
    <Tooltip 
      content={config.description}
      position="top"
      delay={500}
    >
      {badgeContent}
    </Tooltip>
  ) : badgeContent;
});
```

2. Status History Implementation
```typescript
// src/components/status/StatusHistory.tsx
import { memo, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { formatDistance } from 'date-fns';
import { useStatusStore } from '../../stores/statusStore';
import { StatusBadge } from './StatusBadge';
import { ValidationStatus } from '../../types';
import './StatusHistory.css';

interface StatusHistoryProps {
  nodeId: string;
  maxEntries?: number;
  showUserInfo?: boolean;
}

export const StatusHistory = memo(({
  nodeId,
  maxEntries = 5,
  showUserInfo = true
}: StatusHistoryProps) => {
  const { getHistory } = useStatusStore();
  const history = getHistory(nodeId);

  const sortedHistory = useMemo(() => {
    return [...history]
      .sort((a, b) => new Date(b.timestamp).getTime() - new Date(a.timestamp).getTime())
      .slice(0, maxEntries);
  }, [history, maxEntries]);

  return (
    <motion.div
      className="status-history"
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
      role="log"
      aria-label="Status history"
    >
      <h3 className="history-title">Status History</h3>
      <div className="history-timeline">
        <AnimatePresence>
          {sortedHistory.map((entry, index) => (
            <motion.div
              key={entry.timestamp}
              className="history-entry"
              initial={{ opacity: 0, x: -20 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: 20 }}
              transition={{ delay: index * 0.1 }}
            >
              <StatusBadge
                status={entry.status}
                nodeId={nodeId}
                size="small"
                animate={false}
                showTooltip={false}
              />
              <div className="entry-details">
                <time 
                  className="entry-time"
                  dateTime={entry.timestamp}
                >
                  {formatDistance(new Date(entry.timestamp), new Date(), { 
                    addSuffix: true 
                  })}
                </time>
                {showUserInfo && entry.user && (
                  <span className="entry-user">
                    by {entry.user}
                  </span>
                )}
              </div>
            </motion.div>
          ))}
        </AnimatePresence>
      </div>
    </motion.div>
  );
});
```

3. Status Progress Implementation
```typescript
// src/components/status/StatusProgress.tsx
import { memo, useMemo } from 'react';
import { motion } from 'framer-motion';
import { useStatusStore } from '../../stores/statusStore';
import { ValidationStatus } from '../../types';
import './StatusProgress.css';

interface StatusProgressProps {
  nodeIds: string[];
  showPercentage?: boolean;
  showLegend?: boolean;
}

export const StatusProgress = memo(({
  nodeIds,
  showPercentage = true,
  showLegend = true
}: StatusProgressProps) => {
  const { getNodesStatus } = useStatusStore();
  
  const stats = useMemo(() => {
    const statuses = nodeIds.map(id => getNodesStatus(id));
    const total = statuses.length;
    
    return Object.values(ValidationStatus).reduce((acc, status) => {
      const count = statuses.filter(s => s === status).length;
      return {
        ...acc,
        [status]: {
          count,
          percentage: (count / total) * 100
        }
      };
    }, {} as Record<ValidationStatus, { count: number; percentage: number }>);
  }, [nodeIds, getNodesStatus]);

  return (
    <div 
      className="status-progress"
      role="region"
      aria-label="Validation progress"
    >
      <div className="progress-bars">
        {Object.entries(stats).map(([status, { percentage }]) => (
          <motion.div
            key={status}
            className={`progress-bar ${status}`}
            initial={{ width: 0 }}
            animate={{ width: `${percentage}%` }}
            transition={{ duration: 0.5, ease: 'easeOut' }}
          />
        ))}
      </div>
      
      {showPercentage && (
        <div className="progress-stats">
          {Object.entries(stats).map(([status, { count, percentage }]) => (
            <div key={status} className="stat-item">
              <span className="stat-label">
                {status.replace('_', ' ')}
              </span>
              <span className="stat-value">
                {count} ({percentage.toFixed(1)}%)
              </span>
            </div>
          ))}
        </div>
      )}

      {showLegend && (
        <div 
          className="progress-legend"
          role="list"
          aria-label="Status legend"
        >
          {Object.entries(statusConfig).map(([status, config]) => (
            <div 
              key={status}
              className="legend-item"
              role="listitem"
            >
              <span 
                className="legend-color"
                style={{ backgroundColor: config.color }}
              />
              <span className="legend-label">
                {status.replace('_', ' ')}
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
});
```

4. Status Styling Implementation
```css
/* src/styles/StatusBadge.css */
.status-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 9999px;
  font-weight: 500;
  transition: all 0.2s ease;
  user-select: none;
  cursor: default;
}

.status-badge:focus-visible {
  outline: 2px solid var(--focus-ring-color);
  outline-offset: 2px;
}

.status-badge.small {
  padding: 0.25rem 0.5rem;
  font-size: 0.75rem;
}

.status-badge.large {
  padding: 0.75rem 1.5rem;
  font-size: 1rem;
}

.status-icon {
  display: inline-block;
  width: 1.25em;
  text-align: center;
}

.status-text {
  text-transform: capitalize;
}

.history-button {
  padding: 0.25rem;
  border-radius: 50%;
  background: transparent;
  border: none;
  cursor: pointer;
  opacity: 0.7;
  transition: opacity 0.2s ease;
}

.history-button:hover {
  opacity: 1;
}

.history-timeline {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  padding: 1rem;
  max-height: 300px;
  overflow-y: auto;
  scrollbar-gutter: stable;
}

.history-entry {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.5rem;
  border-radius: 0.5rem;
  background: var(--surface-color);
  box-shadow: 0 1px 2px rgba(0, 0, 0, 0.05);
}

.entry-details {
  display: flex;
  flex-direction: column;
  font-size: 0.875rem;
}

.entry-time {
  color: var(--text-secondary);
}

.entry-user {
  font-weight: 500;
}

.status-progress {
  width: 100%;
  padding: 1rem;
  background: var(--surface-color);
  border-radius: 0.5rem;
  box-shadow: 0 1px 3px rgba(0, 0, 0, 0.1);
}

.progress-bars {
  height: 0.5rem;
  background: var(--surface-secondary);
  border-radius: 0.25rem;
  overflow: hidden;
  display: flex;
}

.progress-bar {
  height: 100%;
  transition: width 0.5s ease;
}

.progress-stats {
  margin-top: 1rem;
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.progress-legend {
  margin-top: 1rem;
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  padding: 0.5rem;
  background: var(--surface-secondary);
  border-radius: 0.25rem;
}

.legend-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.legend-color {
  width: 1rem;
  height: 1rem;
  border-radius: 50%;
}

@media (prefers-reduced-motion: reduce) {
  .status-badge,
  .history-button,
  .progress-bar {
    transition: none;
  }
}

@media (max-width: 640px) {
  .progress-stats {
    grid-template-columns: 1fr;
  }
}
```

## Implementation Strategy
1. Core Components
   - Implement status badge component
   - Create status history view
   - Develop progress visualization
   - Set up WebSocket integration

2. State Management
   - Implement status store
   - Set up real-time updates
   - Configure caching
   - Handle offline states

3. Accessibility & UX
   - Add ARIA attributes
   - Implement keyboard navigation
   - Configure screen reader support
   - Add reduced motion support

4. Performance Optimization
   - Implement component memoization
   - Configure render optimization
   - Set up performance monitoring
   - Optimize animations

## Acceptance Criteria
- [ ] Status badge component with real-time updates
- [ ] Status history with timeline view
- [ ] Progress visualization with statistics
- [ ] WebSocket integration for live updates
- [ ] Role-based status visibility
- [ ] Comprehensive accessibility support
- [ ] Responsive design implementation
- [ ] Performance optimization
- [ ] Offline support
- [ ] Animation and transition effects
- [ ] Error state handling
- [ ] Loading state management
- [ ] Documentation completed
- [ ] Unit tests with >90% coverage
- [ ] E2E tests for critical flows

## Dependencies
- Ticket 4.1: Frontend Setup
- Ticket 4.2: Interactive Dashboard
- Ticket 4.6: UI Transitions & Animations
- Ticket 3.2: Core API Endpoints

## Estimated Hours
20

## Testing Requirements
- Unit Tests:
  - Test badge rendering
  - Verify status updates
  - Test history display
  - Validate progress calculation
  - Test WebSocket integration
  - Verify role-based access
  - Test accessibility features
  - Validate animations

- Integration Tests:
  - Test real-time updates
  - Verify status transitions
  - Test offline behavior
  - Validate data persistence
  - Test error recovery
  - Verify state management

- Performance Tests:
  - Measure render performance
  - Test animation smoothness
  - Verify memory usage
  - Test WebSocket efficiency
  - Measure update latency

- Accessibility Tests:
  - Test screen reader compatibility
  - Verify keyboard navigation
  - Test color contrast
  - Validate ARIA attributes
  - Test reduced motion

## Documentation
- Component API documentation
- WebSocket integration guide
- State management patterns
- Animation specifications
- Accessibility implementation
- Performance optimization
- Testing procedures
- Error handling guide
- Offline support details
- Upgrade procedures

## Search Space Optimization
- Clear component hierarchy
- Consistent naming patterns
- Standardized prop interfaces
- Logical file organization
- Well-documented utilities
- Organized test structure
- Clear state management
- Consistent styling patterns
- Standardized animation configs
- Organized WebSocket handlers

## References
- **Phasedplan.md:** Phase 4, Ticket 4.7
- **Blueprint.md:** Sections on UI/UX & CX
- React Component Guidelines
- WebSocket Best Practices
- WCAG Accessibility Guidelines
- Performance Optimization Patterns

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the status visualization system as specified in the blueprint, with particular attention to:
- Real-time status updates
- Clear visual feedback
- Accessibility compliance
- Performance optimization
- User experience
- State management
- Error handling
- Documentation standards
- Testing coverage
- Maintenance procedures
``` 