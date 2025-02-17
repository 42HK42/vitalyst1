# Ticket 4.2: Develop Interactive Dashboard and Graph Visualization

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive interactive dashboard and graph visualization components for the Vitalyst Knowledge Graph frontend, following zero-trust security principles and optimizing for performance. This includes integrating React Flow for graph exploration, creating role-specific dashboards, implementing smooth transitions, and providing real-time visual feedback mechanisms while ensuring accessibility and optimal user experience as specified in the blueprint.

## Technical Details
1. Graph Visualization Implementation
```typescript
// src/components/GraphVisualization/index.tsx
import ReactFlow, {
  Background,
  Controls,
  Edge,
  Node,
  NodeChange,
  applyNodeChanges,
  useNodesState,
  useEdgesState,
  ConnectionMode
} from 'reactflow';
import { useCallback, useState, useEffect, useMemo } from 'react';
import { useAppContext } from '../../context/AppContext';
import { useGraphLayout } from '../../hooks/useGraphLayout';
import { useGraphMetrics } from '../../hooks/useGraphMetrics';
import { CustomNode } from './CustomNode';
import { CustomEdge } from './CustomEdge';
import { StatusBadge } from '../StatusBadge';
import { GraphControls } from './GraphControls';
import { GraphLegend } from './GraphLegend';
import { GraphSearch } from './GraphSearch';
import { usePerformanceMonitor } from '../../hooks/usePerformanceMonitor';
import './GraphVisualization.css';

const nodeTypes = {
  foodNode: CustomNode,
  nutrientNode: CustomNode,
  contentNode: CustomNode,
  environmentalNode: CustomNode
};

const edgeTypes = {
  customEdge: CustomEdge
};

export function GraphVisualization() {
  const { state, dispatch } = useAppContext();
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [selectedNodes, setSelectedNodes] = useState<Set<string>>(new Set());
  const [viewPort, setViewPort] = useState({ zoom: 1, x: 0, y: 0 });
  const { layout, applyLayout } = useGraphLayout();
  const { metrics, updateMetrics } = useGraphMetrics();
  const { monitorPerformance } = usePerformanceMonitor();

  // Memoize node and edge configurations
  const nodeConfig = useMemo(() => ({
    nodeTypes,
    nodeDragThreshold: 2,
    nodesDraggable: true,
    nodesConnectable: true,
    elementsSelectable: true,
    minZoom: 0.5,
    maxZoom: 2,
    defaultViewport: { zoom: 1, x: 0, y: 0 }
  }), []);

  // Handle node selection with performance optimization
  const onNodesSelect = useCallback((changes: NodeChange[]) => {
    monitorPerformance('nodeSelection', () => {
      const selectedNode = changes.find(
        (change) => change.type === 'select' && change.selected
      );
      if (selectedNode) {
        setSelectedNodes(prev => new Set([...prev, selectedNode.id]));
        dispatch({ type: 'SET_SELECTED_NODE', payload: selectedNode.id });
        updateMetrics('nodeSelection');
      }
    });
  }, [dispatch, updateMetrics, monitorPerformance]);

  // Handle viewport changes with debouncing
  const onViewPortChange = useCallback((viewport: any) => {
    setViewPort(viewport);
    updateMetrics('viewportChange');
  }, [updateMetrics]);

  // Initialize graph data with error handling
  useEffect(() => {
    const initializeGraph = async () => {
      try {
        const graphData = await fetchGraphData();
        setNodes(graphData.nodes);
        setEdges(graphData.edges);
        applyLayout(graphData.nodes, graphData.edges);
      } catch (error) {
        console.error('Failed to initialize graph:', error);
        dispatch({ type: 'SET_ERROR', payload: 'Failed to load graph data' });
      }
    };

    initializeGraph();
  }, []);

  return (
    <div className="graph-visualization-container">
      <GraphControls
        onLayoutChange={applyLayout}
        onSearch={(query) => {/* Implement search */}}
        metrics={metrics}
      />
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={onNodesSelect}
        onViewportChange={onViewPortChange}
        nodeTypes={nodeTypes}
        edgeTypes={edgeTypes}
        connectionMode={ConnectionMode.STRICT}
        {...nodeConfig}
      >
        <Background />
        <Controls />
        <GraphLegend />
        <GraphSearch />
      </ReactFlow>
      <div className="graph-metrics">
        <p>Nodes: {metrics.nodeCount}</p>
        <p>Edges: {metrics.edgeCount}</p>
        <p>Selected: {selectedNodes.size}</p>
      </div>
    </div>
  );
}
```

2. Dashboard Implementation with Role-Based Access
```typescript
// src/components/Dashboard/index.tsx
import { useEffect, useCallback, useMemo } from 'react';
import { useAppContext } from '../../context/AppContext';
import { useAuth } from '../../hooks/useAuth';
import { useMetrics } from '../../hooks/useMetrics';
import { GraphVisualization } from '../GraphVisualization';
import { DetailPanel } from '../DetailPanel';
import { ValidationQueue } from '../ValidationQueue';
import { DashboardHeader } from './DashboardHeader';
import { DashboardSidebar } from './DashboardSidebar';
import { DashboardMetrics } from './DashboardMetrics';
import { ErrorBoundary } from '../ErrorBoundary';
import { PerformanceMonitor } from '../PerformanceMonitor';
import './Dashboard.css';

interface DashboardProps {
  userRole: 'admin' | 'editor' | 'reviewer' | 'public';
}

export function Dashboard({ userRole }: DashboardProps) {
  const { state, dispatch } = useAppContext();
  const { hasPermission } = useAuth();
  const { metrics, updateMetrics } = useMetrics();
  const isInternalUser = userRole !== 'public';

  // Memoize permission checks
  const permissions = useMemo(() => ({
    canValidate: hasPermission('validate'),
    canEnrich: hasPermission('enrich'),
    canEdit: hasPermission('edit'),
    canDelete: hasPermission('delete')
  }), [hasPermission]);

  // Handle dashboard updates
  const handleMetricUpdate = useCallback((metricType: string) => {
    updateMetrics(metricType);
  }, [updateMetrics]);

  return (
    <ErrorBoundary>
      <PerformanceMonitor>
        <div className="dashboard-container">
          <DashboardHeader
            userRole={userRole}
            metrics={metrics}
            permissions={permissions}
          />
          
          <div className="dashboard-content">
            <DashboardSidebar
              isInternalUser={isInternalUser}
              permissions={permissions}
            >
              {permissions.canValidate && (
                <ValidationQueue
                  onMetricUpdate={handleMetricUpdate}
                />
              )}
            </DashboardSidebar>

            <main className="main-content">
              <GraphVisualization />
              {state.isDetailPanelOpen && (
                <DetailPanel
                  permissions={permissions}
                  onMetricUpdate={handleMetricUpdate}
                />
              )}
            </main>

            <DashboardMetrics
              metrics={metrics}
              isVisible={isInternalUser}
            />
          </div>
        </div>
      </PerformanceMonitor>
    </ErrorBoundary>
  );
}
```

3. Performance Optimization Implementation
```typescript
// src/hooks/useGraphPerformance.ts
import { useCallback, useRef, useEffect } from 'react';
import { debounce } from 'lodash';

interface PerformanceMetrics {
  fps: number;
  renderTime: number;
  memoryUsage: number;
}

export function useGraphPerformance() {
  const metricsRef = useRef<PerformanceMetrics>({
    fps: 60,
    renderTime: 0,
    memoryUsage: 0
  });

  const updateMetrics = useCallback(debounce((metrics: Partial<PerformanceMetrics>) => {
    metricsRef.current = {
      ...metricsRef.current,
      ...metrics
    };
  }, 1000), []);

  const measurePerformance = useCallback((operation: () => void) => {
    const start = performance.now();
    operation();
    const end = performance.now();

    updateMetrics({
      renderTime: end - start,
      memoryUsage: (window.performance as any).memory?.usedJSHeapSize || 0
    });
  }, [updateMetrics]);

  useEffect(() => {
    let frameCount = 0;
    let lastTime = performance.now();

    const measureFPS = () => {
      const currentTime = performance.now();
      frameCount++;

      if (currentTime - lastTime >= 1000) {
        updateMetrics({
          fps: Math.round(frameCount * 1000 / (currentTime - lastTime))
        });
        frameCount = 0;
        lastTime = currentTime;
      }

      requestAnimationFrame(measureFPS);
    };

    const frameId = requestAnimationFrame(measureFPS);
    return () => cancelAnimationFrame(frameId);
  }, [updateMetrics]);

  return {
    metrics: metricsRef.current,
    measurePerformance
  };
}
```

4. Accessibility Implementation
```typescript
// src/components/GraphVisualization/AccessibleGraph.tsx
import { useEffect, useRef } from 'react';
import { useA11yAnnouncer } from '../../hooks/useA11yAnnouncer';

interface AccessibleGraphProps {
  nodes: any[];
  selectedNodes: Set<string>;
  onNodeSelect: (nodeId: string) => void;
}

export function AccessibleGraph({
  nodes,
  selectedNodes,
  onNodeSelect
}: AccessibleGraphProps) {
  const containerRef = useRef<HTMLDivElement>(null);
  const { announce } = useA11yAnnouncer();

  useEffect(() => {
    if (selectedNodes.size > 0) {
      const selectedNode = nodes.find(n => selectedNodes.has(n.id));
      announce(`Selected node: ${selectedNode?.data.label}`);
    }
  }, [selectedNodes, nodes, announce]);

  return (
    <div
      ref={containerRef}
      role="application"
      aria-label="Graph Visualization"
      tabIndex={0}
      className="accessible-graph"
    >
      <div className="visually-hidden">
        <h2>Keyboard Navigation</h2>
        <ul>
          <li>Use arrow keys to navigate between nodes</li>
          <li>Press Enter to select a node</li>
          <li>Press Escape to clear selection</li>
        </ul>
      </div>
    </div>
  );
}
```

## Implementation Strategy
1. Graph Visualization
   - Implement React Flow integration
   - Create custom nodes and edges
   - Set up graph layout system
   - Implement performance monitoring

2. Dashboard Structure
   - Create role-based views
   - Implement sidebar components
   - Set up metrics display
   - Configure real-time updates

3. Performance Optimization
   - Implement virtualization
   - Set up performance monitoring
   - Configure caching system
   - Optimize render cycles

4. Accessibility
   - Implement keyboard navigation
   - Add screen reader support
   - Create ARIA labels
   - Test with assistive technologies

## Acceptance Criteria
- [ ] Interactive graph visualization with React Flow
- [ ] Custom nodes with status badges and animations
- [ ] Role-specific dashboard views
- [ ] Smooth panel transitions
- [ ] Real-time validation queue
- [ ] Performance monitoring system
- [ ] Accessibility compliance
- [ ] Responsive layout
- [ ] Error boundary implementation
- [ ] Memory optimization
- [ ] Performance benchmarks met
- [ ] Documentation complete

## Dependencies
- Ticket 4.1: Frontend Setup
- Ticket 3.2: Core API Endpoints
- Ticket 3.3: Zero-Trust Security
- Ticket 3.4: Backend Testing

## Estimated Hours
25

## Testing Requirements
- Unit Tests:
  - Test node selection logic
  - Verify role-based rendering
  - Test graph layout calculations
  - Validate performance monitoring
  - Test accessibility features

- Integration Tests:
  - Test graph-panel interaction
  - Verify data flow
  - Test role-based access
  - Validate real-time updates
  - Test error handling

- Performance Tests:
  - Test with 1000+ nodes
  - Measure render times
  - Verify memory usage
  - Test animation smoothness
  - Monitor FPS

- Accessibility Tests:
  - Test keyboard navigation
  - Verify screen readers
  - Test high contrast
  - Validate ARIA labels
  - Test focus management

## Documentation
- Graph visualization guide
- Performance optimization
- Accessibility implementation
- Role-based access control
- State management patterns
- Error handling procedures
- Testing strategies
- Deployment guidelines

## Search Space Optimization
- Clear component hierarchy
- Consistent naming patterns
- Logical feature grouping
- Standardized hooks
- Organized test structure
- Documented patterns
- Performance metrics
- Accessibility guidelines

## References
- **Phasedplan.md:** Phase 4, Ticket 4.2
- **Blueprint.md:** UI/UX & CX Guidelines
- React Flow Documentation
- Web Accessibility Guidelines
- Performance Optimization Guide
- Testing Best Practices

## Notes
- Implements comprehensive visualization
- Ensures performance optimization
- Maintains accessibility
- Supports role-based access
- Optimizes user experience 