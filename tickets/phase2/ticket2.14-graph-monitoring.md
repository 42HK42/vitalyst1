# Ticket 2.14: Graph-Specific Monitoring

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive graph-specific monitoring system for the Vitalyst Knowledge Graph that tracks node relationships, path patterns, and graph health metrics. The system must integrate with Prometheus/Grafana for visualization, provide detailed alerting, and maintain performance metrics while following the blueprint specifications for monitoring and observability.

## Technical Details

1. Graph Metrics Implementation
```python
from typing import Dict, List, Optional, Union
from enum import Enum
from pydantic import BaseModel
from prometheus_client import Counter, Gauge, Histogram, Summary
import logging
import asyncio

class MetricType(Enum):
    NODE = "node"
    RELATIONSHIP = "relationship"
    PATH = "path"
    QUERY = "query"
    CACHE = "cache"
    MEMORY = "memory"

class GraphMetric(BaseModel):
    name: str
    type: MetricType
    description: str
    labels: List[str] = []
    buckets: Optional[List[float]] = None

class GraphMonitor:
    def __init__(self, driver, logger, metrics_service):
        self.driver = driver
        self.logger = logger
        self.metrics_service = metrics_service
        
        # Initialize Prometheus metrics
        self.metrics = self._initialize_metrics()
        
    def _initialize_metrics(self) -> Dict[str, any]:
        """Initialize all graph-specific metrics"""
        return {
            # Node metrics
            "node_count": Gauge(
                'neo4j_node_count_total',
                'Total number of nodes by label',
                ['label']
            ),
            "node_properties": Gauge(
                'neo4j_node_properties_total',
                'Total number of node properties',
                ['label']
            ),
            
            # Relationship metrics
            "relationship_count": Gauge(
                'neo4j_relationship_count_total',
                'Total number of relationships by type',
                ['type']
            ),
            "relationship_depth": Histogram(
                'neo4j_relationship_depth',
                'Distribution of relationship path depths',
                ['type'],
                buckets=[1, 2, 3, 5, 8, 13, 21]
            ),
            
            # Path metrics
            "path_length": Histogram(
                'neo4j_path_length',
                'Distribution of path lengths',
                ['start_label', 'end_label'],
                buckets=[1, 2, 3, 5, 8, 13]
            ),
            "path_execution_time": Histogram(
                'neo4j_path_execution_time',
                'Path query execution time',
                ['pattern_type'],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
            ),
            
            # Query metrics
            "query_execution_time": Histogram(
                'neo4j_query_execution_time',
                'Query execution time in seconds',
                ['query_type'],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0, 10.0]
            ),
            "query_cache_hits": Counter(
                'neo4j_query_cache_hits_total',
                'Total number of query cache hits',
                ['query_type']
            ),
            
            # Memory metrics
            "memory_usage": Gauge(
                'neo4j_memory_usage_bytes',
                'Memory usage by type',
                ['memory_type']
            ),
            
            # Transaction metrics
            "transaction_count": Counter(
                'neo4j_transaction_count_total',
                'Total number of transactions',
                ['status']
            ),
            "transaction_duration": Histogram(
                'neo4j_transaction_duration_seconds',
                'Transaction duration in seconds',
                ['type'],
                buckets=[0.1, 0.5, 1.0, 2.0, 5.0]
            )
        }
        
    async def collect_graph_metrics(self) -> None:
        """Collect comprehensive graph metrics"""
        try:
            # Collect node metrics
            await self.collect_node_metrics()
            
            # Collect relationship metrics
            await self.collect_relationship_metrics()
            
            # Collect path metrics
            await self.collect_path_metrics()
            
            # Collect query metrics
            await self.collect_query_metrics()
            
            # Collect memory metrics
            await self.collect_memory_metrics()
            
        except Exception as e:
            self.logger.error(f"Failed to collect graph metrics: {str(e)}")
            raise
            
    async def collect_node_metrics(self) -> None:
        """Collect node-specific metrics"""
        query = """
        MATCH (n)
        WITH labels(n) as labels, count(n) as count
        RETURN labels, count
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query)
                records = await result.fetch()
                
                for record in records:
                    for label in record["labels"]:
                        self.metrics["node_count"].labels(label).set(
                            record["count"]
                        )
                        
        except Exception as e:
            self.logger.error(f"Failed to collect node metrics: {str(e)}")
            raise
            
    async def collect_relationship_metrics(self) -> None:
        """Collect relationship-specific metrics"""
        query = """
        MATCH ()-[r]->()
        WITH type(r) as rel_type, count(r) as count
        RETURN rel_type, count
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query)
                records = await result.fetch()
                
                for record in records:
                    self.metrics["relationship_count"].labels(
                        record["rel_type"]
                    ).set(record["count"])
                    
        except Exception as e:
            self.logger.error(
                f"Failed to collect relationship metrics: {str(e)}"
            )
            raise
            
    async def collect_path_metrics(self) -> None:
        """Collect path-specific metrics"""
        # Common path patterns to monitor
        patterns = [
            {
                "name": "food_to_nutrient",
                "query": """
                MATCH p=(f:Food)-[*]->(n:Nutrient)
                RETURN length(p) as path_length
                """
            },
            {
                "name": "nutrient_interaction",
                "query": """
                MATCH p=(n1:Nutrient)-[*]->(n2:Nutrient)
                RETURN length(p) as path_length
                """
            }
        ]
        
        try:
            async with self.driver.session() as session:
                for pattern in patterns:
                    start_time = asyncio.get_event_loop().time()
                    result = await session.run(pattern["query"])
                    records = await result.fetch()
                    duration = asyncio.get_event_loop().time() - start_time
                    
                    # Record execution time
                    self.metrics["path_execution_time"].labels(
                        pattern["name"]
                    ).observe(duration)
                    
                    # Record path lengths
                    for record in records:
                        self.metrics["path_length"].labels(
                            pattern["name"]
                        ).observe(record["path_length"])
                        
        except Exception as e:
            self.logger.error(f"Failed to collect path metrics: {str(e)}")
            raise

2. Health Check Implementation
```python
class GraphHealthCheck:
    def __init__(self, driver, logger, metrics_service):
        self.driver = driver
        self.logger = logger
        self.metrics_service = metrics_service
        
    async def check_graph_health(self) -> Dict[str, any]:
        """Perform comprehensive graph health check"""
        health_checks = {
            "database_status": await self.check_database_status(),
            "index_status": await self.check_indexes(),
            "constraint_status": await self.check_constraints(),
            "memory_status": await self.check_memory_health(),
            "connection_status": await self.check_connections()
        }
        
        # Update health metrics
        await self.metrics_service.record_health_status(health_checks)
        
        return health_checks
        
    async def check_database_status(self) -> Dict[str, any]:
        """Check database health status"""
        query = """
        CALL dbms.cluster.overview()
        YIELD id, addresses, role, database
        RETURN *
        """
        
        try:
            async with self.driver.session() as session:
                result = await session.run(query)
                records = await result.fetch()
                
                return {
                    "status": "healthy" if records else "unhealthy",
                    "nodes": len(records),
                    "details": [dict(record) for record in records]
                }
                
        except Exception as e:
            self.logger.error(f"Database health check failed: {str(e)}")
            return {
                "status": "unhealthy",
                "error": str(e)
            }

3. Alert Configuration Implementation
```python
class GraphAlertManager:
    def __init__(self, driver, logger, alert_service):
        self.driver = driver
        self.logger = logger
        self.alert_service = alert_service
        
    async def configure_alerts(self) -> None:
        """Configure graph-specific alerts"""
        alerts = [
            # Node count alerts
            {
                "name": "high_node_growth_rate",
                "query": """
                MATCH (n)
                WHERE n.created_at > datetime() - duration('P1D')
                RETURN count(n) as new_nodes
                """,
                "threshold": 10000,
                "interval": "5m",
                "severity": "warning"
            },
            
            # Memory alerts
            {
                "name": "high_memory_usage",
                "metric": "neo4j_memory_usage_bytes",
                "threshold": 0.9,  # 90% usage
                "interval": "1m",
                "severity": "critical"
            },
            
            # Query performance alerts
            {
                "name": "slow_queries",
                "metric": "neo4j_query_execution_time",
                "threshold": 5.0,  # 5 seconds
                "interval": "5m",
                "severity": "warning"
            }
        ]
        
        for alert in alerts:
            await self.alert_service.create_alert_rule(alert)

4. Dashboard Implementation
```yaml
# grafana/dashboards/graph_overview.json
{
  "dashboard": {
    "id": null,
    "title": "Neo4j Graph Overview",
    "tags": ["neo4j", "graph", "vitalyst"],
    "timezone": "browser",
    "panels": [
      {
        "title": "Node Count by Label",
        "type": "graph",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "neo4j_node_count_total",
            "legendFormat": "{{label}}"
          }
        ]
      },
      {
        "title": "Relationship Distribution",
        "type": "graph",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "neo4j_relationship_count_total",
            "legendFormat": "{{type}}"
          }
        ]
      },
      {
        "title": "Query Performance",
        "type": "heatmap",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "rate(neo4j_query_execution_time_bucket[5m])",
            "legendFormat": "{{query_type}}"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "gauge",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "neo4j_memory_usage_bytes",
            "legendFormat": "{{memory_type}}"
          }
        ]
      }
    ]
  }
}
```

## Implementation Strategy
1. Metric Collection Setup
   - Implement graph metrics
   - Create collection system
   - Set up aggregation
   - Configure storage

2. Health Check System
   - Implement health checks
   - Create validation rules
   - Set up monitoring
   - Configure alerts

3. Dashboard Creation
   - Design layouts
   - Create visualizations
   - Set up drill-downs
   - Configure filtering

4. Alert Configuration
   - Define thresholds
   - Create alert rules
   - Set up notifications
   - Configure escalations

## Acceptance Criteria
- [ ] Graph metrics collection implemented
- [ ] Health check system working
- [ ] Prometheus integration complete
- [ ] Grafana dashboards created
- [ ] Alert system configured
- [ ] Performance impact minimized
- [ ] Documentation completed
- [ ] Metric thresholds defined
- [ ] Alert rules tested
- [ ] Dashboard templates created
- [ ] Integration tests passing
- [ ] Monitoring guides completed

## Dependencies
- Ticket 2.10: Neo4j Graph Model
- Ticket 2.13: Performance Optimization
- Ticket 2.12: Data Migration

## Estimated Hours
30

## Testing Requirements
- Metric Tests
  - Test collection accuracy
  - Verify aggregation
  - Check performance impact
  - Validate storage
- Health Check Tests
  - Test system checks
  - Verify error detection
  - Check recovery procedures
  - Validate reporting
- Dashboard Tests
  - Test visualizations
  - Verify data refresh
  - Check filtering
  - Validate exports
- Alert Tests
  - Test rule triggers
  - Verify notifications
  - Check escalations
  - Validate resolution

## Documentation
- Monitoring system overview
- Metric specifications
- Dashboard configuration
- Alert rule definitions
- Health check procedures
- Troubleshooting guide
- Performance impact guide
- Integration patterns

## Search Space Optimization
- Clear metric hierarchy
- Logical health check organization
- Consistent alert patterns
- Standardized dashboard layouts
- Organized monitoring structure

## References
- Blueprint Section 3: Data Model & Graph Structure
- Blueprint Section 9: Frameworks, Deployment, Security & Monitoring
- Blueprint Section 3.2: Data Model Consistency
- Blueprint Section 5: Data Quality and Validation
- Prometheus Documentation
- Grafana Best Practices
- Neo4j Monitoring Guidelines

## Notes
- Implements comprehensive monitoring
- Ensures visibility
- Optimizes alerting
- Supports troubleshooting
- Maintains performance 