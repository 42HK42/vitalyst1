# Ticket 4.10: Node Relationship Visualization

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement a comprehensive node relationship visualization system for the Vitalyst Knowledge Graph frontend that displays different types of connections between nodes, correlation values, and interactive highlighting. The system must support hierarchical relationships, real-time updates through WebSocket connections, interactive exploration features, and accessibility features while maintaining optimal performance and user experience as specified in the blueprint.

## Technical Details
1. Relationship Edge Component Implementation
```typescript
// src/components/graph/RelationshipEdge.tsx
import { memo, useCallback, useEffect } from 'react';
import { EdgeProps, getBezierPath, useStore } from 'reactflow';
import { motion, AnimatePresence } from 'framer-motion';
import { useAccessibility } from '../../hooks/useAccessibility';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useRelationshipStore } from '../../stores/relationshipStore';
import { useTooltip } from '../../hooks/useTooltip';
import { usePerformanceMonitor } from '../../hooks/usePerformanceMonitor';
import { formatCorrelation } from '../../utils/formatting';
import './RelationshipEdge.css';

interface RelationshipEdgeData {
  type: 'direct' | 'indirect';
  validationStatus: 'validated' | 'pending' | 'needs_verification';
  correlationValue?: number;
  sourceType: string;
  targetType: string;
  confidence: number;
  lastVerified: string;
  verifiedBy?: string;
  evidence?: {
    source: string;
    strength: 'strong' | 'moderate' | 'weak';
    description: string;
  };
}

export const RelationshipEdge = memo(({
  id,
  source,
  target,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected
}: EdgeProps<RelationshipEdgeData>) => {
  const { prefersReducedMotion } = useAccessibility();
  const { trackRender } = usePerformanceMonitor();
  const { showTooltip, hideTooltip } = useTooltip();
  const ws = useWebSocket('ws://localhost:8000/ws/relationships');
  const { updateRelationship } = useRelationshipStore();
  const store = useStore();

  // Handle real-time updates
  useEffect(() => {
    if (ws) {
      ws.addEventListener('message', (event) => {
        const update = JSON.parse(event.data);
        if (update.relationshipId === id) {
          updateRelationship(id, update.data);
        }
      });
    }
  }, [ws, id, updateRelationship]);

  // Calculate edge path
  const [edgePath, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    sourcePosition,
    targetX,
    targetY,
    targetPosition
  });

  // Handle edge interactions
  const handleEdgeClick = useCallback((event: React.MouseEvent) => {
    event.stopPropagation();
    store.getState().setSelectedElements({ edges: [id], nodes: [] });
  }, [id, store]);

  const handleEdgeMouseEnter = useCallback((event: React.MouseEvent) => {
    const tooltipContent = (
      <div className="edge-tooltip">
        <h4>{data.type === 'direct' ? 'Direct Connection' : 'Indirect Connection'}</h4>
        <div className="tooltip-content">
          <p>
            <strong>Correlation:</strong> {formatCorrelation(data.correlationValue)}
          </p>
          <p>
            <strong>Confidence:</strong> {(data.confidence * 100).toFixed(0)}%
          </p>
          {data.evidence && (
            <div className="evidence-info">
              <p>
                <strong>Evidence:</strong> {data.evidence.strength} 
                ({data.evidence.source})
              </p>
              <p>{data.evidence.description}</p>
            </div>
          )}
        </div>
      </div>
    );
    showTooltip(tooltipContent, event.clientX, event.clientY);
  }, [data, showTooltip]);

  // Track render performance
  useEffect(() => {
    trackRender('relationship-edge', performance.now());
  }, [trackRender]);

  const isDirectConnection = data?.type === 'direct';
  const strokeDasharray = isDirectConnection ? 'none' : '5,5';
  const strokeWidth = selected ? 3 : isDirectConnection ? 2 : 1.5;

  const getEdgeColor = (status: string, selected: boolean) => {
    if (selected) return 'var(--edge-selected)';
    switch (status) {
      case 'validated': return 'var(--edge-validated)';
      case 'pending': return 'var(--edge-pending)';
      case 'needs_verification': return 'var(--edge-needs-verification)';
      default: return 'var(--edge-default)';
    }
  };

  return (
    <g 
      className="relationship-edge"
      onMouseEnter={handleEdgeMouseEnter}
      onMouseLeave={hideTooltip}
      onClick={handleEdgeClick}
      role="graphics-symbol"
      aria-label={`${data.type} connection from ${data.sourceType} to ${data.targetType}`}
    >
      <motion.path
        id={id}
        d={edgePath}
        className={`edge-path ${data.type} ${data.validationStatus} ${selected ? 'selected' : ''}`}
        strokeWidth={strokeWidth}
        strokeDasharray={strokeDasharray}
        stroke={getEdgeColor(data.validationStatus, selected)}
        initial={prefersReducedMotion ? false : { pathLength: 0 }}
        animate={{ pathLength: 1 }}
        transition={{ duration: prefersReducedMotion ? 0 : 0.5 }}
        markerEnd={`url(#${data.type}-arrow)`}
      />
      <AnimatePresence>
        {data.correlationValue && (
          <motion.g
            initial={{ opacity: 0, scale: 0 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0 }}
            transition={{ duration: prefersReducedMotion ? 0 : 0.3 }}
          >
            <rect
              x={labelX - 20}
              y={labelY - 10}
              width={40}
              height={20}
              rx={4}
              fill="var(--surface-color)"
              filter="url(#edge-label-shadow)"
            />
            <text
              x={labelX}
              y={labelY}
              className="edge-label"
              textAnchor="middle"
              dominantBaseline="central"
            >
              {formatCorrelation(data.correlationValue)}
            </text>
          </motion.g>
        )}
      </AnimatePresence>
    </g>
  );
});

// src/components/graph/InteractiveGraph.tsx
import { useCallback, useState, useEffect, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  Controls,
  Background,
  useNodesState,
  useEdgesState,
  ConnectionMode,
  useReactFlow
} from 'reactflow';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useGraphLayout } from '../../hooks/useGraphLayout';
import { useGraphMetrics } from '../../hooks/useGraphMetrics';
import { useAccessibility } from '../../hooks/useAccessibility';
import { RelationshipEdge } from './RelationshipEdge';
import { NodeCard } from './NodeCard';
import { GraphControls } from './GraphControls';
import { GraphLegend } from './GraphLegend';
import { GraphSearch } from './GraphSearch';
import { usePerformanceMonitor } from '../../hooks/usePerformanceMonitor';
import './InteractiveGraph.css';

const edgeTypes = {
  relationship: RelationshipEdge
};

const nodeTypes = {
  nodeCard: NodeCard
};

export const InteractiveGraph = () => {
  const [nodes, setNodes, onNodesChange] = useNodesState([]);
  const [edges, setEdges, onEdgesChange] = useEdgesState([]);
  const [highlightedChain, setHighlightedChain] = useState<string[]>([]);
  const { prefersReducedMotion } = useAccessibility();
  const { trackRender } = usePerformanceMonitor();
  const { fitView, zoomTo } = useReactFlow();
  const ws = useWebSocket('ws://localhost:8000/ws/graph');

  // Initialize graph layout
  const { layout, updateLayout } = useGraphLayout();
  const { metrics, updateMetrics } = useGraphMetrics();

  // Handle real-time updates
  useEffect(() => {
    if (ws) {
      ws.addEventListener('message', (event) => {
        const update = JSON.parse(event.data);
        switch (update.type) {
          case 'node_update':
            setNodes(nds => 
              nds.map(node => 
                node.id === update.nodeId ? { ...node, data: update.data } : node
              )
            );
            break;
          case 'edge_update':
            setEdges(eds => 
              eds.map(edge => 
                edge.id === update.edgeId ? { ...edge, data: update.data } : edge
              )
            );
            break;
          case 'layout_update':
            updateLayout(update.layout);
            break;
        }
      });
    }
  }, [ws, setNodes, setEdges, updateLayout]);

  // Handle node selection
  const handleNodeClick = useCallback((event: any, node: Node) => {
    const chain = findConnectedChain(node.id, edges);
    setHighlightedChain(chain);
    
    // Update metrics
    updateMetrics({
      selectedNodeId: node.id,
      chainLength: chain.length,
      connectionTypes: analyzeConnectionTypes(chain, edges)
    });

    // Animate to selected node
    if (!prefersReducedMotion) {
      const nodePosition = nodes.find(n => n.id === node.id)?.position;
      if (nodePosition) {
        zoomTo(1.2, { x: nodePosition.x, y: nodePosition.y, duration: 800 });
      }
    }
  }, [edges, nodes, updateMetrics, zoomTo, prefersReducedMotion]);

  // Find connected chain
  const findConnectedChain = useCallback((nodeId: string, edges: Edge[]): string[] => {
    const chain = new Set<string>([nodeId]);
    let changed = true;

    while (changed) {
      changed = false;
      edges.forEach(edge => {
        if (chain.has(edge.source) && !chain.has(edge.target)) {
          chain.add(edge.target);
          changed = true;
        }
        if (chain.has(edge.target) && !chain.has(edge.source)) {
          chain.add(edge.source);
          changed = true;
        }
      });
    }

    return Array.from(chain);
  }, []);

  // Analyze connection types
  const analyzeConnectionTypes = useCallback((chain: string[], edges: Edge[]): Record<string, number> => {
    return edges.reduce((acc, edge) => {
      if (chain.includes(edge.source) && chain.includes(edge.target)) {
        acc[edge.data.type] = (acc[edge.data.type] || 0) + 1;
      }
      return acc;
    }, {} as Record<string, number>);
  }, []);

  // Track render performance
  useEffect(() => {
    trackRender('interactive-graph', performance.now());
  }, [trackRender]);

  return (
    <div 
      className="interactive-graph"
      role="application"
      aria-label="Interactive graph visualization"
    >
      <ReactFlow
        nodes={nodes}
        edges={edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        onNodeClick={handleNodeClick}
        edgeTypes={edgeTypes}
        nodeTypes={nodeTypes}
        connectionMode={ConnectionMode.STRICT}
        minZoom={0.5}
        maxZoom={2}
        defaultViewport={{ x: 0, y: 0, zoom: 1 }}
        fitView
      >
        <Background />
        <Controls 
          showZoom={true}
          showFitView={true}
          showInteractive={false}
        />
        <GraphControls
          onLayoutChange={updateLayout}
          onMetricsChange={updateMetrics}
        />
        <GraphLegend />
        <GraphSearch
          nodes={nodes}
          onNodeSelect={(nodeId) => {
            const node = nodes.find(n => n.id === nodeId);
            if (node) handleNodeClick(null, node);
          }}
        />
      </ReactFlow>
    </div>
  );
};
```

2. Graph Styling Implementation
```css
/* src/styles/RelationshipEdge.css */
.relationship-edge {
  pointer-events: all;
  cursor: pointer;
}

.edge-path {
  transition: stroke 0.3s ease, stroke-width 0.3s ease;
}

.edge-path:hover {
  stroke-width: 3;
}

.edge-path.direct {
  stroke-linecap: round;
}

.edge-path.indirect {
  stroke-linecap: butt;
}

.edge-path.selected {
  filter: drop-shadow(0 0 4px var(--edge-selected-glow));
}

.edge-label {
  font-size: 10px;
  fill: var(--text-secondary);
  pointer-events: none;
  user-select: none;
}

.edge-tooltip {
  padding: 0.75rem;
  background: var(--surface-color);
  border-radius: 6px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
  max-width: 300px;
}

.edge-tooltip h4 {
  margin: 0 0 0.5rem;
  color: var(--text-primary);
}

.tooltip-content {
  font-size: 0.875rem;
  color: var(--text-secondary);
}

.evidence-info {
  margin-top: 0.5rem;
  padding-top: 0.5rem;
  border-top: 1px solid var(--border-color);
}

.highlighted-chain .edge-path {
  stroke-width: 3;
  filter: drop-shadow(0 0 4px var(--edge-highlight-glow));
}

@media (prefers-reduced-motion: reduce) {
  .edge-path {
    transition: none;
  }
}

/* Animation keyframes for correlation value updates */
@keyframes correlationPulse {
  0% { font-size: 10px; }
  50% { font-size: 12px; }
  100% { font-size: 10px; }
}

.correlation-update {
  animation: correlationPulse 0.5s ease;
}

/* SVG Definitions */
#edge-label-shadow {
  feDropShadow {
    dx: 0;
    dy: 1;
    stdDeviation: 2;
    flood-color: rgba(0, 0, 0, 0.1);
  }
}

#direct-arrow {
  path {
    fill: currentColor;
  }
}

#indirect-arrow {
  path {
    fill: none;
    stroke: currentColor;
  }
}
```

## Implementation Strategy
1. Core Components
   - Implement relationship edge component
   - Create interactive graph container
   - Develop graph controls
   - Set up real-time updates

2. Interaction Features
   - Implement chain highlighting
   - Create tooltips and info panels
   - Set up zoom and pan controls
   - Configure node selection

3. Performance Optimization
   - Implement edge caching
   - Optimize layout calculations
   - Configure render optimization
   - Set up performance monitoring

4. Accessibility & UX
   - Add ARIA attributes
   - Implement keyboard navigation
   - Configure screen reader support
   - Add reduced motion support

## Acceptance Criteria
- [ ] Different connection types visualization
- [ ] Real-time relationship updates
- [ ] Interactive chain highlighting
- [ ] Correlation value display
- [ ] Validation status indicators
- [ ] Evidence information display
- [ ] Performance optimization
- [ ] Accessibility features
- [ ] Responsive design
- [ ] Error handling
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
25

## Testing Requirements
- Unit Tests:
  - Test edge rendering
  - Verify chain highlighting
  - Test correlation display
  - Validate tooltips
  - Test WebSocket integration
  - Verify accessibility
  - Test animations
  - Validate interactions

- Integration Tests:
  - Test graph interactions
  - Verify real-time updates
  - Test layout changes
  - Validate state management
  - Test error recovery
  - Verify data flow

- Performance Tests:
  - Measure render times
  - Test large graphs
  - Verify memory usage
  - Test animation performance
  - Monitor WebSocket efficiency
  - Validate layout calculations

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
- Graph interaction patterns
- Layout algorithms
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
- Standardized graph patterns
- Organized WebSocket handlers

## References
- **Phasedplan.md:** Phase 4, Ticket 4.10
- **Blueprint.md:** Sections on Graph Visualization
- React Flow Documentation
- WebSocket Best Practices
- Graph Visualization Patterns
- WCAG Accessibility Guidelines

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the node relationship visualization system as specified in the blueprint, with particular attention to:
- Comprehensive visualization
- Real-time updates
- Interactive features
- Performance optimization
- Accessibility compliance
- User experience
- Error handling
- Documentation standards
- Testing coverage
- Maintenance procedures
``` 