# Ticket 2.8: Historical Data Tracking

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive historical tracking system for the Vitalyst Knowledge Graph that captures changes in environmental metrics, validation states, data transformations, and relationships over time. The system must maintain complete data lineage, support efficient querying, and provide detailed audit trails while following the blueprint specifications.

## Technical Details

1. Historical Data Models
```python
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Union, Literal
from datetime import datetime
import uuid

class ChangeMetadata(BaseModel):
    change_id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str
    change_type: Literal['create', 'update', 'delete', 'validate', 'enrich']
    source: str
    reason: Optional[str]
    related_changes: List[str] = []
    metadata: Dict[str, any] = {}

class HistoricalMetric(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str
    metric_type: str
    value: float
    unit: str
    timestamp: datetime
    source: str
    reliability_score: float = Field(ge=0.0, le=1.0)
    raw_data: Dict[str, any]
    processed_data: Dict[str, any]
    validation_status: str
    change_metadata: ChangeMetadata
    previous_version: Optional[str]
    
    @validator('reliability_score')
    def validate_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Reliability score must be between 0 and 1')
        return v

class RelationshipHistory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    source_node: str
    target_node: str
    relationship_type: str
    properties: Dict[str, any]
    valid_from: datetime
    valid_to: Optional[datetime]
    change_metadata: ChangeMetadata

class ValidationHistory(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    node_id: str
    status: str
    confidence_score: float
    reviewer_id: Optional[str]
    comments: Optional[str]
    validation_data: Dict[str, any]
    change_metadata: ChangeMetadata
```

2. History Manager Implementation
```python
class HistoryManager:
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        
    async def track_metric_change(
        self,
        node_id: str,
        metric: HistoricalMetric,
        change_metadata: ChangeMetadata
    ) -> str:
        """Track changes in node metrics"""
        try:
            async with self.driver.session() as session:
                async with session.begin_transaction() as tx:
                    # Create historical record
                    result = await tx.run("""
                    MATCH (n) WHERE n.id = $node_id
                    CREATE (h:HistoricalMetric $metric_props)
                    CREATE (n)-[:HAS_HISTORY {
                        type: $metric_type,
                        timestamp: datetime()
                    }]->(h)
                    RETURN h.id as history_id
                    """, {
                        "node_id": node_id,
                        "metric_props": metric.dict(),
                        "metric_type": metric.metric_type
                    })
                    
                    history_id = (await result.single())["history_id"]
                    
                    # Link to previous version if exists
                    if metric.previous_version:
                        await tx.run("""
                        MATCH (h1:HistoricalMetric {id: $prev_id})
                        MATCH (h2:HistoricalMetric {id: $curr_id})
                        CREATE (h2)-[:PREVIOUS_VERSION]->(h1)
                        """, {
                            "prev_id": metric.previous_version,
                            "curr_id": history_id
                        })
                    
                    await tx.commit()
                    
                    self.logger.info(
                        f"Tracked metric change for node {node_id}",
                        extra={
                            "history_id": history_id,
                            "metric_type": metric.metric_type,
                            "change": change_metadata.dict()
                        }
                    )
                    
                    return history_id
                    
        except Exception as e:
            self.logger.error(
                f"Failed to track metric change: {str(e)}",
                extra={"node_id": node_id, "metric": metric.dict()}
            )
            raise
    
    async def track_relationship_change(
        self,
        relationship: RelationshipHistory,
        change_metadata: ChangeMetadata
    ) -> str:
        """Track changes in relationships"""
        try:
            async with self.driver.session() as session:
                # Close previous relationship version if exists
                if relationship.valid_from:
                    await session.run("""
                    MATCH (s)-[r]->(t)
                    WHERE s.id = $source_id
                      AND t.id = $target_id
                      AND r.type = $rel_type
                      AND r.valid_to IS NULL
                    SET r.valid_to = $valid_from
                    """, {
                        "source_id": relationship.source_node,
                        "target_id": relationship.target_node,
                        "rel_type": relationship.relationship_type,
                        "valid_from": relationship.valid_from
                    })
                
                # Create new relationship version
                result = await session.run("""
                MATCH (s) WHERE s.id = $source_id
                MATCH (t) WHERE t.id = $target_id
                CREATE (s)-[r:$rel_type $props]->(t)
                RETURN r.id as rel_id
                """, {
                    "source_id": relationship.source_node,
                    "target_id": relationship.target_node,
                    "rel_type": relationship.relationship_type,
                    "props": {
                        **relationship.properties,
                        "valid_from": relationship.valid_from,
                        "valid_to": None
                    }
                })
                
                return (await result.single())["rel_id"]
                
        except Exception as e:
            self.logger.error(
                f"Failed to track relationship change: {str(e)}",
                extra={"relationship": relationship.dict()}
            )
            raise
    
    async def get_metric_history(
        self,
        node_id: str,
        metric_type: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> List[HistoricalMetric]:
        """Retrieve metric history with optional filtering"""
        try:
            query = """
            MATCH (n)-[:HAS_HISTORY]->(h:HistoricalMetric)
            WHERE n.id = $node_id
            """
            
            if metric_type:
                query += " AND h.metric_type = $metric_type"
            if start_date:
                query += " AND h.timestamp >= $start_date"
            if end_date:
                query += " AND h.timestamp <= $end_date"
                
            query += """
            RETURN h
            ORDER BY h.timestamp DESC
            """
            
            async with self.driver.session() as session:
                result = await session.run(query, {
                    "node_id": node_id,
                    "metric_type": metric_type,
                    "start_date": start_date,
                    "end_date": end_date
                })
                
                return [
                    HistoricalMetric(**record["h"])
                    for record in await result.fetch()
                ]
                
        except Exception as e:
            self.logger.error(
                f"Failed to retrieve metric history: {str(e)}",
                extra={"node_id": node_id, "metric_type": metric_type}
            )
            raise
```

3. Change Comparison Implementation
```python
class ChangeComparator:
    def __init__(self, logger):
        self.logger = logger
    
    def compare_metrics(
        self,
        old_metric: HistoricalMetric,
        new_metric: HistoricalMetric
    ) -> Dict[str, any]:
        """Compare two metric versions"""
        changes = {
            'field_changes': {},
            'value_changes': {},
            'metadata_changes': {}
        }
        
        # Compare values
        if old_metric.value != new_metric.value:
            changes['value_changes']['value'] = {
                'old': old_metric.value,
                'new': new_metric.value,
                'difference': new_metric.value - old_metric.value,
                'percentage_change': (
                    (new_metric.value - old_metric.value) / old_metric.value * 100
                    if old_metric.value != 0 else None
                )
            }
        
        # Compare reliability scores
        if old_metric.reliability_score != new_metric.reliability_score:
            changes['value_changes']['reliability'] = {
                'old': old_metric.reliability_score,
                'new': new_metric.reliability_score
            }
        
        # Compare processed data
        changes['field_changes'] = self._compare_dicts(
            old_metric.processed_data,
            new_metric.processed_data
        )
        
        # Compare metadata
        changes['metadata_changes'] = self._compare_dicts(
            old_metric.change_metadata.metadata,
            new_metric.change_metadata.metadata
        )
        
        return changes
    
    def _compare_dicts(
        self,
        old_dict: Dict,
        new_dict: Dict
    ) -> Dict[str, any]:
        """Compare two dictionaries recursively"""
        changes = {}
        
        # Find modified and new fields
        for key, new_value in new_dict.items():
            if key not in old_dict:
                changes[key] = {'added': new_value}
            elif old_dict[key] != new_value:
                changes[key] = {
                    'old': old_dict[key],
                    'new': new_value
                }
        
        # Find removed fields
        for key in old_dict:
            if key not in new_dict:
                changes[key] = {'removed': old_dict[key]}
        
        return changes
```

4. Query Optimization
```python
class HistoryQueryOptimizer:
    def __init__(self, driver):
        self.driver = driver
    
    async def get_changes_in_period(
        self,
        start_date: datetime,
        end_date: datetime,
        node_types: Optional[List[str]] = None,
        metric_types: Optional[List[str]] = None,
        include_relationships: bool = False
    ) -> Dict[str, List[Dict]]:
        """Get optimized view of changes in time period"""
        query = """
        MATCH (n)-[:HAS_HISTORY]->(h:HistoricalMetric)
        WHERE h.timestamp >= $start_date
          AND h.timestamp <= $end_date
        """
        
        if node_types:
            query += " AND n.type IN $node_types"
        if metric_types:
            query += " AND h.metric_type IN $metric_types"
            
        query += """
        WITH n, h
        ORDER BY h.timestamp
        WITH n, collect(h) as history
        RETURN n.id as node_id, n.type as node_type, history
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {
                "start_date": start_date,
                "end_date": end_date,
                "node_types": node_types,
                "metric_types": metric_types
            })
            
            changes = {}
            async for record in result:
                changes[record["node_id"]] = {
                    "node_type": record["node_type"],
                    "history": [h.data() for h in record["history"]]
                }
            
            if include_relationships:
                # Add relationship changes
                rel_changes = await self._get_relationship_changes(
                    session, start_date, end_date, list(changes.keys())
                )
                for node_id, rels in rel_changes.items():
                    if node_id in changes:
                        changes[node_id]["relationships"] = rels
            
            return changes
    
    async def _get_relationship_changes(
        self,
        session,
        start_date: datetime,
        end_date: datetime,
        node_ids: List[str]
    ) -> Dict[str, List[Dict]]:
        """Get relationship changes for nodes"""
        query = """
        MATCH (n)-[r]-(m)
        WHERE n.id IN $node_ids
          AND r.valid_from >= $start_date
          AND (r.valid_to <= $end_date OR r.valid_to IS NULL)
        RETURN n.id as node_id,
               collect({
                   type: type(r),
                   properties: r,
                   target_id: m.id,
                   valid_from: r.valid_from,
                   valid_to: r.valid_to
               }) as relationships
        """
        
        result = await session.run(query, {
            "node_ids": node_ids,
            "start_date": start_date,
            "end_date": end_date
        })
        
        return {
            record["node_id"]: record["relationships"]
            for record in await result.fetch()
        }
```

## Implementation Strategy
1. Data Model Setup
   - Implement historical data models
   - Create change tracking structures
   - Set up versioning system
   - Configure audit trails

2. History Management
   - Implement history manager
   - Create change tracking logic
   - Set up version control
   - Configure data lineage

3. Query Optimization
   - Create optimized queries
   - Implement caching strategy
   - Set up indexing
   - Configure aggregations

4. Integration
   - Implement node history
   - Set up relationship tracking
   - Configure change propagation
   - Implement reporting

## Acceptance Criteria
- [ ] Historical data models implemented
- [ ] Change tracking system working
- [ ] Version control functioning
- [ ] Data lineage tracking
- [ ] Relationship history implemented
- [ ] Query optimization completed
- [ ] Caching system working
- [ ] Audit trails functioning
- [ ] Documentation completed
- [ ] Performance benchmarks met
- [ ] Test coverage complete
- [ ] Integration tests passing

## Dependencies
- Ticket 2.5: Hierarchical Node Structure
- Ticket 2.6: Data Validation Workflow
- Ticket 2.7: CSV-Specific Models

## Estimated Hours
35

## Testing Requirements
- Model Tests
  - Test historical models
  - Verify change tracking
  - Check version control
  - Validate audit trails
- Query Tests
  - Test optimized queries
  - Verify caching
  - Check aggregations
  - Validate performance
- Integration Tests
  - Test node history
  - Verify relationship tracking
  - Test change propagation
  - Check data lineage
- Performance Tests
  - Measure query speed
  - Test concurrent access
  - Verify memory usage
  - Benchmark operations

## Documentation
- Historical tracking overview
- Change management guide
- Query optimization patterns
- Version control procedures
- Audit trail implementation
- Performance tuning guide
- Integration patterns
- Best practices

## Search Space Optimization
- Clear history hierarchy
- Logical change tracking
- Consistent version patterns
- Standardized audit trails
- Organized query patterns

## References
- Blueprint Section 3.1: Hierarchical Node Modeling
- Blueprint Section 8: Roles, Workflows & Validation
- Blueprint Section 3.2: Data Model Consistency
- Blueprint Section 5: Data Quality and Validation
- Neo4j Temporal Data Guidelines
- Graph History Patterns

## Notes
- Implements comprehensive tracking
- Ensures data lineage
- Optimizes queries
- Supports auditing
- Maintains performance