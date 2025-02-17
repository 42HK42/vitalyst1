# Ticket 4.3: Implement the "Detail Panel" for Node Editing

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement a comprehensive sliding Detail Panel component for node editing and inspection in the Vitalyst Knowledge Graph frontend. This panel should provide rich editing capabilities for internal users, real-time validation feedback, AI enrichment integration, and hierarchical data visualization, while maintaining a read-only view for public users. The implementation must follow zero-trust security principles, ensure optimal performance, and provide seamless accessibility as specified in the blueprint.

## Technical Details
1. Detail Panel Component Implementation
```typescript
// src/components/DetailPanel/index.tsx
import { useEffect, useState, useCallback, useMemo } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { useAppContext } from '../../context/AppContext';
import { useNodeData } from '../../hooks/useNodeData';
import { useValidation } from '../../hooks/useValidation';
import { useAIEnrichment } from '../../hooks/useAIEnrichment';
import { usePerformanceMonitor } from '../../hooks/usePerformanceMonitor';
import { NodeEditor } from './NodeEditor';
import { AIEnrichment } from './AIEnrichment';
import { ValidationControls } from './ValidationControls';
import { HistoryTimeline } from './HistoryTimeline';
import { EnvironmentalMetrics } from './EnvironmentalMetrics';
import { RelationshipGraph } from './RelationshipGraph';
import { hasPermission } from '../../utils/roleAccess';
import { useReducedMotion } from '../../hooks/useReducedMotion';
import './DetailPanel.css';

export function DetailPanel() {
  const { state, dispatch } = useAppContext();
  const prefersReducedMotion = useReducedMotion();
  const { nodeData, isLoading, error, refetch } = useNodeData(state.selectedNode);
  const { validateNode, validationErrors } = useValidation();
  const { enrichNode, isEnriching } = useAIEnrichment();
  const { monitorPerformance } = usePerformanceMonitor();

  const [activeTab, setActiveTab] = useState('details');
  const [unsavedChanges, setUnsavedChanges] = useState(false);

  const slideAnimation = useMemo(() => ({
    initial: prefersReducedMotion ? { opacity: 0 } : { x: '100%' },
    animate: prefersReducedMotion ? { opacity: 1 } : { x: 0 },
    exit: prefersReducedMotion ? { opacity: 0 } : { x: '100%' },
    transition: {
      type: 'spring',
      damping: 25,
      stiffness: 180
    }
  }), [prefersReducedMotion]);

  const handleClose = useCallback(() => {
    if (unsavedChanges) {
      // Show confirmation dialog
      return;
    }
    dispatch({ type: 'SET_DETAIL_PANEL_OPEN', payload: false });
  }, [unsavedChanges, dispatch]);

  const handleSave = useCallback(async (data) => {
    try {
      await monitorPerformance('saveNode', async () => {
        const validationResult = await validateNode(data);
        if (validationResult.isValid) {
          // Save node data
          setUnsavedChanges(false);
          refetch();
        }
      });
    } catch (error) {
      console.error('Failed to save node:', error);
    }
  }, [validateNode, monitorPerformance, refetch]);

  const handleEnrich = useCallback(async () => {
    try {
      await enrichNode(state.selectedNode);
      refetch();
    } catch (error) {
      console.error('AI enrichment failed:', error);
    }
  }, [state.selectedNode, enrichNode, refetch]);

  return (
    <AnimatePresence>
      {state.isDetailPanelOpen && (
        <motion.div 
          className="detail-panel"
          {...slideAnimation}
          role="dialog"
          aria-labelledby="panel-title"
          aria-modal="true"
        >
          <div className="detail-panel-header">
            <h2 id="panel-title">{nodeData?.type}: {nodeData?.name}</h2>
            <div className="header-actions">
              {unsavedChanges && (
                <span className="unsaved-indicator" role="status">
                  Unsaved changes
                </span>
              )}
              <button 
                onClick={handleClose}
                className="close-button"
                aria-label="Close panel"
              >
                <XIcon className="h-6 w-6" />
              </button>
            </div>
          </div>

          <nav className="detail-panel-tabs" role="tablist">
            <button
              role="tab"
              aria-selected={activeTab === 'details'}
              onClick={() => setActiveTab('details')}
            >
              Details
            </button>
            <button
              role="tab"
              aria-selected={activeTab === 'history'}
              onClick={() => setActiveTab('history')}
            >
              History
            </button>
            <button
              role="tab"
              aria-selected={activeTab === 'relationships'}
              onClick={() => setActiveTab('relationships')}
            >
              Relationships
            </button>
          </nav>

          <div className="detail-panel-content">
            {isLoading ? (
              <LoadingSpinner />
            ) : error ? (
              <ErrorMessage error={error} onRetry={refetch} />
            ) : (
              <>
                {activeTab === 'details' && (
                  <>
                    <NodeEditor 
                      data={nodeData}
                      onValidationError={setValidationErrors}
                      onUnsavedChanges={setUnsavedChanges}
                      onSave={handleSave}
                      readOnly={!hasPermission(state.userRole, 'edit')}
                    />
                    
                    {hasPermission(state.userRole, 'enrich') && (
                      <AIEnrichment 
                        nodeId={state.selectedNode}
                        onEnrich={handleEnrich}
                        isEnriching={isEnriching}
                      />
                    )}

                    {hasPermission(state.userRole, 'validate') && (
                      <ValidationControls
                        nodeId={state.selectedNode}
                        currentStatus={nodeData?.validation_status}
                        onStatusChange={refetch}
                      />
                    )}

                    <EnvironmentalMetrics
                      metrics={nodeData?.environmental_metrics}
                      readOnly={!hasPermission(state.userRole, 'edit')}
                    />
                  </>
                )}

                {activeTab === 'history' && (
                  <HistoryTimeline
                    nodeId={state.selectedNode}
                    history={nodeData?.history}
                  />
                )}

                {activeTab === 'relationships' && (
                  <RelationshipGraph
                    nodeId={state.selectedNode}
                    relationships={nodeData?.relationships}
                  />
                )}
              </>
            )}
          </div>
        </motion.div>
      )}
    </AnimatePresence>
  );
}

// src/components/DetailPanel/NodeEditor.tsx
import { useForm, FormProvider } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { nodeSchema } from '../../schemas/node';
import { useDebounce } from '../../hooks/useDebounce';
import { FormField } from '../common/FormField';
import { NodeTypeFields } from './NodeTypeFields';

interface NodeEditorProps {
  data: any;
  onValidationError: (errors: string[]) => void;
  onUnsavedChanges: (hasChanges: boolean) => void;
  onSave: (data: any) => Promise<void>;
  readOnly?: boolean;
}

export function NodeEditor({
  data,
  onValidationError,
  onUnsavedChanges,
  onSave,
  readOnly
}: NodeEditorProps) {
  const methods = useForm({
    resolver: zodResolver(nodeSchema),
    defaultValues: data,
    mode: 'onChange'
  });

  const debouncedOnChange = useDebounce((formData) => {
    onUnsavedChanges(true);
    onValidationError(Object.values(methods.formState.errors).map(e => e.message));
  }, 300);

  return (
    <FormProvider {...methods}>
      <form
        onSubmit={methods.handleSubmit(onSave)}
        className="node-editor"
        onChange={() => debouncedOnChange(methods.getValues())}
      >
        <FormField
          name="name"
          label="Name"
          required
          readOnly={readOnly}
        />
        
        <NodeTypeFields
          type={data.type}
          readOnly={readOnly}
        />
        
        {!readOnly && (
          <div className="actions">
            <button
              type="button"
              onClick={() => methods.reset()}
              disabled={!methods.formState.isDirty}
            >
              Reset
            </button>
            <button
              type="submit"
              disabled={!methods.formState.isDirty || !methods.formState.isValid}
            >
              Save Changes
            </button>
          </div>
        )}
      </form>
    </FormProvider>
  );
}

2. Styling Implementation
```css
/* src/styles/DetailPanel.css */
.detail-panel {
  position: fixed;
  top: 0;
  right: 0;
  width: 480px;
  height: 100vh;
  background: var(--surface-color);
  box-shadow: -4px 0 12px rgba(0, 0, 0, 0.1);
  z-index: 1000;
  display: flex;
  flex-direction: column;
}

.detail-panel-header {
  padding: 1.5rem;
  border-bottom: 1px solid var(--border-color);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.detail-panel-content {
  flex: 1;
  overflow-y: auto;
  padding: 1.5rem;
}

.node-editor {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.error-message {
  color: var(--error-color);
  font-size: 0.875rem;
}

.actions {
  margin-top: 2rem;
  display: flex;
  justify-content: flex-end;
  gap: 1rem;
}

@keyframes slideIn {
  from { transform: translateX(100%); }
  to { transform: translateX(0); }
}

@keyframes slideOut {
  from { transform: translateX(0); }
  to { transform: translateX(100%); }
}
```

3. AI Enrichment Integration
```typescript
// src/components/DetailPanel/AIEnrichment.tsx
import { useState } from 'react';
import { useAppContext } from '../../context/AppContext';

interface AIEnrichmentProps {
  nodeId: string;
  onEnrich: () => void;
  isEnriching: boolean;
}

export function AIEnrichment({ nodeId, onEnrich, isEnriching }: AIEnrichmentProps) {
  const { dispatch } = useAppContext();

  const handleEnrich = async () => {
    try {
      await onEnrich();
    } catch (error) {
      console.error('AI enrichment failed:', error);
    }
  };

  return (
    <div className="ai-enrichment">
      <button
        onClick={handleEnrich}
        disabled={isEnriching}
        className="enrich-button"
      >
        {isEnriching ? 'Enriching...' : 'Enrich with AI'}
      </button>
    </div>
  );
}
```

## Implementation Strategy
1. Core Panel Implementation
   - Implement sliding panel with animations
   - Create form components with validation
   - Set up role-based access control
   - Implement AI enrichment integration

2. Performance Optimization
   - Implement virtualization for large datasets
   - Add debounced validation
   - Optimize animations
   - Configure caching

3. Accessibility Implementation
   - Add keyboard navigation
   - Implement focus management
   - Add screen reader support
   - Configure reduced motion

4. Testing and Documentation
   - Write comprehensive tests
   - Create documentation
   - Implement monitoring
   - Set up error tracking

## Acceptance Criteria
- [ ] Detail panel slides in/out smoothly with proper animations
- [ ] Form fields are dynamically rendered based on node type
- [ ] Real-time validation with clear error messages
- [ ] AI enrichment button is only visible for users with appropriate permissions
- [ ] Read-only mode works correctly for public users
- [ ] All form inputs follow the JSON schema definitions
- [ ] Changes are properly saved and validated
- [ ] Panel properly handles loading and error states
- [ ] Responsive layout works on all screen sizes
- [ ] Keyboard navigation and accessibility requirements are met
- [ ] Performance optimization for large datasets
- [ ] Comprehensive error handling and recovery
- [ ] Proper state management and caching
- [ ] Detailed activity history tracking
- [ ] Environmental metrics visualization
- [ ] Relationship graph visualization
- [ ] Reduced motion support
- [ ] Screen reader compatibility
- [ ] Focus management implementation
- [ ] Comprehensive test coverage

## Dependencies
- Ticket 4.1: Frontend Setup
- Ticket 4.2: Interactive Dashboard
- Ticket 3.2: Core API Endpoints
- Ticket 4.6: UI Transitions & Animations
- Ticket 4.7: Status Visualization System

## Estimated Hours
20

## Testing Requirements
- Unit Tests:
  - Test form validation logic
  - Verify permission-based rendering
  - Test animation behaviors
  - Validate form state management
  - Test accessibility features
  - Verify performance optimizations
  - Test caching mechanisms
  - Validate error handling

- Integration Tests:
  - Test API integration for saving changes
  - Verify AI enrichment workflow
  - Test real-time validation
  - Test state management
  - Verify data persistence
  - Test relationship visualization
  - Validate history tracking
  - Test environmental metrics

- Accessibility Tests:
  - Verify keyboard navigation
  - Test screen reader compatibility
  - Validate ARIA attributes
  - Test focus management
  - Verify reduced motion
  - Test color contrast
  - Validate form labels
  - Test error announcements

- Performance Tests:
  - Measure animation smoothness
  - Test form responsiveness with large datasets
  - Verify virtualization effectiveness
  - Test caching performance
  - Measure memory usage
  - Validate debouncing
  - Test concurrent operations
  - Verify render optimization

## Documentation
- Component API documentation
- Form validation rules
- Animation specifications
- Accessibility implementation details
- State management patterns
- Error handling procedures
- Performance optimization guide
- Testing strategy
- Caching implementation
- Keyboard shortcuts
- Screen reader usage
- Relationship visualization
- Environmental metrics
- History tracking

## Search Space Optimization
- Clear component hierarchy
- Consistent file organization
- Standardized naming conventions
- Logical hook structure
- Comprehensive type definitions
- Well-documented interfaces
- Organized test structure
- Clear error messages
- Consistent event handling
- Standardized styling patterns

## References
- **Phasedplan.md:** Phase 4, Ticket 4.3
- **Blueprint.md:** Sections on UI/UX & CX, Frontend Development
- Blueprint Section 11: User Interface and Experience
- React Hook Form documentation
- Framer Motion animation guidelines
- WCAG Accessibility Guidelines
- React Performance Optimization Guide
- Testing Best Practices

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the Detail Panel component as specified in the blueprint, with particular attention to:
- Comprehensive component architecture
- Zero-trust security principles
- Performance optimization
- Accessibility compliance
- Real-time validation
- AI integration
- State management
- Error handling
- Testing coverage
- Documentation standards
``` 