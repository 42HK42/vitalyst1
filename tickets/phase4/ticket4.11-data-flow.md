# Ticket 4.11: Data Flow Visualization

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement a comprehensive data flow visualization system for the Vitalyst Knowledge Graph frontend that displays hierarchical food-nutrient relationships, nutrient absorption pathways, environmental impact metrics, and seasonal variations. The system must support real-time updates, interactive exploration, accessibility features, and performance optimization while maintaining optimal user experience as specified in the blueprint.

## Technical Details
1. Hierarchical Layout Implementation
```typescript
// src/components/graph/HierarchicalGraph.tsx
import { memo, useCallback, useEffect, useMemo } from 'react';
import ReactFlow, {
  Node,
  Edge,
  useNodesState,
  useEdgesState,
  Position,
  MarkerType,
  useReactFlow
} from 'reactflow';
import dagre from 'dagre';
import { motion, AnimatePresence } from 'framer-motion';
import { useWebSocket } from '../../hooks/useWebSocket';
import { useAccessibility } from '../../hooks/useAccessibility';
import { usePerformanceMonitor } from '../../hooks/usePerformanceMonitor';
import { useGraphMetrics } from '../../hooks/useGraphMetrics';
import { useTooltip } from '../../hooks/useTooltip';
import { formatMetric } from '../../utils/formatting';
import './HierarchicalGraph.css';

interface HierarchicalGraphProps {
  initialNodes: Node[];
  initialEdges: Edge[];
  groupBy?: 'category' | 'type' | 'none';
  showEnvironmentalMetrics?: boolean;
  showSeasonalData?: boolean;
  showNutrientAbsorption?: boolean;
}

const nodeWidth = 250;
const nodeHeight = 120;

export const HierarchicalGraph = memo(({
  initialNodes,
  initialEdges,
  groupBy = 'none',
  showEnvironmentalMetrics = true,
  showSeasonalData = true,
  showNutrientAbsorption = true
}: HierarchicalGraphProps) => {
  const [nodes, setNodes, onNodesChange] = useNodesState(initialNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(initialEdges);
  const { prefersReducedMotion } = useAccessibility();
  const { trackRender } = usePerformanceMonitor();
  const { showTooltip, hideTooltip } = useTooltip();
  const { fitView, zoomTo } = useReactFlow();
  const ws = useWebSocket('ws://localhost:8000/ws/data-flow');

  // Handle real-time updates
  useEffect(() => {
    if (ws) {
      ws.addEventListener('message', (event) => {
        const update = JSON.parse(event.data);
        switch (update.type) {
          case 'node_metrics':
            updateNodeMetrics(update.nodeId, update.metrics);
            break;
          case 'seasonal_update':
            updateSeasonalData(update.data);
            break;
          case 'absorption_update':
            updateAbsorptionData(update.data);
            break;
        }
      });
    }
  }, [ws]);

  // Layout calculation with memoization
  const getLayoutedElements = useMemo(() => {
    const g = new dagre.graphlib.Graph();
    g.setGraph({ 
      rankdir: 'TB',
      nodesep: 80,
      ranksep: 100,
      align: 'UL'
    });
    g.setDefaultEdgeLabel(() => ({}));

    // Group nodes if specified
    const groupedNodes = groupBy !== 'none'
      ? groupNodesByProperty(nodes, groupBy)
      : nodes;

    // Add nodes to the graph
    groupedNodes.forEach(node => {
      g.setNode(node.id, { width: nodeWidth, height: nodeHeight });
    });

    // Add edges to the graph
    edges.forEach(edge => {
      g.setEdge(edge.source, edge.target);
    });

    // Calculate layout
    dagre.layout(g);

    // Apply layout to nodes
    const layoutedNodes = groupedNodes.map(node => {
      const nodeWithPosition = g.node(node.id);
      return {
        ...node,
        position: {
          x: nodeWithPosition.x - nodeWidth / 2,
          y: nodeWithPosition.y - nodeHeight / 2
        }
      };
    });

    return { nodes: layoutedNodes, edges };
  }, [nodes, edges, groupBy]);

  // Performance tracking
  useEffect(() => {
    trackRender('hierarchical-graph', performance.now());
  }, [trackRender]);

  // Node grouping implementation
  const groupNodesByProperty = useCallback((
    nodes: Node[],
    property: 'category' | 'type'
  ) => {
    const groups = new Map<string, Node[]>();
    
    // Group nodes by property
    nodes.forEach(node => {
      const groupKey = node.data[property];
      if (!groups.has(groupKey)) {
        groups.set(groupKey, []);
      }
      groups.get(groupKey)?.push(node);
    });

    // Create group containers and position nodes
    let yOffset = 0;
    const groupedNodes: Node[] = [];

    groups.forEach((groupNodes, groupKey) => {
      // Add group container
      groupedNodes.push({
        id: `group-${groupKey}`,
        type: 'group',
        data: { 
          label: groupKey,
          nodeCount: groupNodes.length,
          metrics: calculateGroupMetrics(groupNodes)
        },
        position: { x: 0, y: yOffset },
        style: {
          backgroundColor: getGroupColor(groupKey),
          padding: 20
        }
      });

      // Position nodes within group
      groupNodes.forEach((node, index) => {
        groupedNodes.push({
          ...node,
          position: {
            x: (index % 3) * (nodeWidth + 20),
            y: yOffset + Math.floor(index / 3) * (nodeHeight + 20)
          },
          parentNode: `group-${groupKey}`
        });
      });

      yOffset += (Math.ceil(groupNodes.length / 3) * (nodeHeight + 20)) + 100;
    });

    return groupedNodes;
  }, []);

  // Environmental metrics visualization
  const renderEnvironmentalMetrics = useCallback((metrics: any) => {
    return (
      <motion.g
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="environmental-metrics"
      >
        <rect
          width={nodeWidth - 20}
          height={60}
          rx={4}
          fill="var(--metrics-background)"
        />
        <g className="metrics-content">
          <MetricIcon type="co2" value={metrics.co2} />
          <MetricIcon type="water" value={metrics.water} />
          <MetricIcon type="land" value={metrics.land} />
        </g>
      </motion.g>
    );
  }, []);

  // Seasonal data visualization
  const renderSeasonalData = useCallback((data: any) => {
    return (
      <motion.g
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="seasonal-data"
      >
        <SeasonalChart data={data} width={nodeWidth - 20} height={40} />
      </motion.g>
    );
  }, []);

  // Nutrient absorption visualization
  const renderAbsorptionPathway = useCallback((pathway: any) => {
    return (
      <motion.g
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="absorption-pathway"
      >
        <AbsorptionFlow data={pathway} width={nodeWidth - 20} height={60} />
      </motion.g>
    );
  }, []);

  return (
    <div 
      className="hierarchical-graph"
      role="application"
      aria-label="Hierarchical data flow visualization"
    >
      <ReactFlow
        nodes={getLayoutedElements.nodes}
        edges={getLayoutedElements.edges}
        onNodesChange={onNodesChange}
        onEdgesChange={onEdgesChange}
        fitView
        minZoom={0.5}
        maxZoom={2}
        attributionPosition="bottom-right"
      >
        <Background />
        <Controls />
        <Panel position="top-left">
          <GraphControls
            showEnvironmentalMetrics={showEnvironmentalMetrics}
            showSeasonalData={showSeasonalData}
            showNutrientAbsorption={showNutrientAbsorption}
            groupBy={groupBy}
            onSettingsChange={handleSettingsChange}
          />
        </Panel>
        <Panel position="top-right">
          <GraphLegend />
        </Panel>
      </ReactFlow>
    </div>
  );
});

// src/components/graph/MetricIcon.tsx
interface MetricIconProps {
  type: 'co2' | 'water' | 'land';
  value: number;
}

const MetricIcon = memo(({ type, value }: MetricIconProps) => {
  const { showTooltip, hideTooltip } = useTooltip();
  
  const handleMouseEnter = useCallback((event: React.MouseEvent) => {
    const content = (
      <div className="metric-tooltip">
        <h4>{getMetricLabel(type)}</h4>
        <p>{formatMetric(value, type)}</p>
        <small>{getMetricDescription(type)}</small>
      </div>
    );
    showTooltip(content, event.clientX, event.clientY);
  }, [type, value, showTooltip]);

  return (
    <g
      className={`metric-icon ${type}`}
      onMouseEnter={handleMouseEnter}
      onMouseLeave={hideTooltip}
      role="img"
      aria-label={`${getMetricLabel(type)}: ${formatMetric(value, type)}`}
    >
      <IconSvg type={type} />
      <text
        x={24}
        y={12}
        className="metric-value"
      >
        {formatMetric(value, type)}
      </text>
    </g>
  );
});
```

2. Environmental Impact Visualization
```typescript
// src/components/graph/EnvironmentalMetrics.tsx
interface EnvironmentalMetricsProps {
  data: {
    co2: number;
    water: number;
    land: number;
    biodiversity: number;
  };
  width: number;
  height: number;
}

export const EnvironmentalMetrics = memo(({
  data,
  width,
  height
}: EnvironmentalMetricsProps) => {
  const { prefersReducedMotion } = useAccessibility();
  
  return (
    <motion.g
      className="environmental-metrics"
      initial={prefersReducedMotion ? false : { opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.3 }}
    >
      <rect
        width={width}
        height={height}
        rx={4}
        className="metrics-background"
      />
      <g transform={`translate(${width * 0.1}, ${height * 0.2})`}>
        <MetricBar
          label="CO₂"
          value={data.co2}
          maxValue={100}
          width={width * 0.8}
          height={height * 0.15}
          color="var(--co2-color)"
        />
        <MetricBar
          label="Water"
          value={data.water}
          maxValue={1000}
          width={width * 0.8}
          height={height * 0.15}
          color="var(--water-color)"
          y={height * 0.25}
        />
        <MetricBar
          label="Land"
          value={data.land}
          maxValue={10}
          width={width * 0.8}
          height={height * 0.15}
          color="var(--land-color)"
          y={height * 0.5}
        />
      </g>
    </motion.g>
  );
});
```

3. Seasonal Data Visualization
```typescript
// src/components/graph/SeasonalChart.tsx
interface SeasonalChartProps {
  data: {
    month: string;
    availability: number;
    price: number;
    quality: number;
  }[];
  width: number;
  height: number;
}

export const SeasonalChart = memo(({
  data,
  width,
  height
}: SeasonalChartProps) => {
  const { prefersReducedMotion } = useAccessibility();
  const months = useMemo(() => data.map(d => d.month), [data]);
  
  return (
    <motion.g
      className="seasonal-chart"
      initial={prefersReducedMotion ? false : { opacity: 0, scale: 0.9 }}
      animate={{ opacity: 1, scale: 1 }}
      transition={{ duration: 0.3 }}
    >
      <rect
        width={width}
        height={height}
        rx={4}
        className="chart-background"
      />
      {months.map((month, i) => (
        <g
          key={month}
          transform={`translate(${(width / 12) * i}, 0)`}
          className="month-column"
        >
          <rect
            y={height - (height * data[i].availability)}
            width={width / 14}
            height={height * data[i].availability}
            className="availability-bar"
            style={{
              fill: getSeasonalColor(data[i].quality)
            }}
          />
          <text
            x={(width / 12) / 2}
            y={height + 15}
            className="month-label"
          >
            {month.substring(0, 1)}
          </text>
        </g>
      ))}
    </motion.g>
  );
});
```

4. Nutrient Absorption Visualization
```typescript
// src/components/graph/AbsorptionFlow.tsx
interface AbsorptionFlowProps {
  data: {
    steps: {
      name: string;
      duration: number;
      efficiency: number;
      factors: string[];
    }[];
    totalDuration: number;
    netEfficiency: number;
  };
  width: number;
  height: number;
}

export const AbsorptionFlow = memo(({
  data,
  width,
  height
}: AbsorptionFlowProps) => {
  const { prefersReducedMotion } = useAccessibility();
  
  return (
    <motion.g
      className="absorption-flow"
      initial={prefersReducedMotion ? false : { opacity: 0 }}
      animate={{ opacity: 1 }}
      transition={{ duration: 0.3 }}
    >
      {data.steps.map((step, i) => (
        <g
          key={step.name}
          transform={`translate(${(width / data.steps.length) * i}, 0)`}
          className="absorption-step"
        >
          <circle
            r={height * 0.2}
            className="step-node"
            style={{
              fill: getEfficiencyColor(step.efficiency)
            }}
          />
          <text
            y={height * 0.4}
            className="step-label"
          >
            {step.name}
          </text>
          <text
            y={height * 0.6}
            className="step-duration"
          >
            {formatDuration(step.duration)}
          </text>
          {i < data.steps.length - 1 && (
            <path
              d={`M${height * 0.2} 0 L${width / data.steps.length - height * 0.2} 0`}
              className="step-connection"
              markerEnd="url(#arrow)"
            />
          )}
        </g>
      ))}
    </motion.g>
  );
});
```

## Implementation Strategy
1. Core Visualization
   - Implement hierarchical layout
   - Create environmental metrics display
   - Develop seasonal data visualization
   - Set up absorption pathway display

2. Real-time Updates
   - Implement WebSocket integration
   - Set up metric updates
   - Configure seasonal data updates
   - Handle absorption data changes

3. Interaction Features
   - Implement grouping controls
   - Create tooltips and info panels
   - Set up zoom and pan controls
   - Configure node selection

4. Performance & Accessibility
   - Optimize layout calculations
   - Implement component memoization
   - Add ARIA attributes
   - Support reduced motion
   - Configure keyboard navigation

## Acceptance Criteria
- [ ] Hierarchical data visualization
- [ ] Environmental impact metrics display
- [ ] Seasonal data visualization
- [ ] Nutrient absorption pathways
- [ ] Real-time data updates
- [ ] Interactive grouping
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
- Ticket 4.10: Node Relationships
- Ticket 3.2: Core API Endpoints

## Estimated Hours
30

## Testing Requirements
- Unit Tests:
  - Test layout calculations
  - Verify metric displays
  - Test seasonal charts
  - Validate absorption flows
  - Test WebSocket integration
  - Verify accessibility
  - Test animations
  - Validate interactions

- Integration Tests:
  - Test data flow
  - Verify real-time updates
  - Test grouping changes
  - Validate state management
  - Test error recovery
  - Verify data consistency

- Performance Tests:
  - Measure layout times
  - Test large datasets
  - Verify memory usage
  - Test animation performance
  - Monitor WebSocket efficiency
  - Validate caching

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
- Data flow patterns
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
- Standardized visualization patterns
- Organized WebSocket handlers

## References
- **Phasedplan.md:** Phase 4, Ticket 4.11
- **Blueprint.md:** Sections on Data Flow Visualization
- React Flow Documentation
- D3.js Visualization Patterns
- WebSocket Best Practices
- WCAG Accessibility Guidelines

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the data flow visualization system as specified in the blueprint, with particular attention to:
- Comprehensive visualization
- Environmental metrics
- Seasonal data
- Absorption pathways
- Real-time updates
- Performance optimization
- Accessibility compliance
- User experience
- Documentation standards
- Testing coverage
``` 