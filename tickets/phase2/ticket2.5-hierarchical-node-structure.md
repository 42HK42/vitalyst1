# Ticket 2.5: Hierarchical Node Structure Implementation

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive hierarchical node structure with subnodes (EnvironmentalMetrics, NutritionalDetails, ConsumerData) and their relationships, ensuring proper data propagation, versioning, and audit trail while following the blueprint specifications for hierarchical node modeling.

## Technical Details

1. Base Node Structure
```python
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Union
from datetime import datetime
from enum import Enum
import uuid

class NodeType(Enum):
    ENVIRONMENTAL = "environmental"
    NUTRITIONAL = "nutritional"
    CONSUMER = "consumer"

class VersionInfo(BaseModel):
    version: str
    created_at: datetime
    created_by: str
    changes: Dict[str, any]
    parent_version: Optional[str]

class BaseSubNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    parent_id: str
    node_type: NodeType
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    updated_by: str
    version_info: VersionInfo
    metadata: Dict[str, any] = {}
    validation_status: str = "pending"
    
    @validator('updated_at')
    def validate_dates(cls, v, values):
        if 'created_at' in values and v < values['created_at']:
            raise ValueError('updated_at cannot be earlier than created_at')
        return v

class EnvironmentalMetrics(BaseSubNode):
    node_type: NodeType = NodeType.ENVIRONMENTAL
    co2_footprint: Dict[str, Union[float, str]] = {
        "value": 0.0,
        "unit": "kg CO2e/kg",
        "calculation_method": "",
        "uncertainty": 0.0,
        "source": "",
        "verification_status": "pending"
    }
    water_usage: Dict[str, Union[float, str]] = {
        "value": 0.0,
        "unit": "L/kg",
        "calculation_method": "",
        "uncertainty": 0.0,
        "source": "",
        "verification_status": "pending"
    }
    land_use: Optional[Dict[str, Union[float, str]]]
    biodiversity_impact: Optional[Dict[str, Union[float, str]]]
    regional_availability: List[Dict[str, any]]
    seasonal_factors: Dict[str, float] = {}
    data_quality_score: float = Field(ge=0.0, le=1.0)
    
    @validator('data_quality_score')
    def validate_quality_score(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('data_quality_score must be between 0 and 1')
        return v

class NutritionalDetails(BaseSubNode):
    node_type: NodeType = NodeType.NUTRITIONAL
    bioavailability: Dict[str, Union[float, str]] = {
        "value": 0.0,
        "unit": "%",
        "measurement_method": "",
        "uncertainty": 0.0,
        "source": "",
        "verification_status": "pending"
    }
    absorption_rate: Dict[str, Union[float, str]] = {
        "value": 0.0,
        "unit": "%/hour",
        "measurement_method": "",
        "uncertainty": 0.0,
        "source": "",
        "verification_status": "pending"
    }
    interactions: List[Dict[str, any]] = []
    source_studies: List[Dict[str, any]] = []
    confidence_score: float = Field(ge=0.0, le=1.0)
    verification_history: List[Dict[str, any]] = []
    
    @validator('interactions')
    def validate_interactions(cls, v):
        if not all('effect' in item and 'confidence' in item for item in v):
            raise ValueError('All interactions must have effect and confidence')
        return v

class ConsumerData(BaseSubNode):
    node_type: NodeType = NodeType.CONSUMER
    popularity_score: float = Field(ge=0.0, le=1.0)
    seasonal_demand: Dict[str, float]
    regional_preferences: Dict[str, float]
    dietary_restrictions: List[str] = []
    allergen_info: List[str] = []
    preparation_methods: List[Dict[str, any]] = []
    storage_recommendations: List[Dict[str, any]] = []
    consumer_feedback: List[Dict[str, any]] = []
    
    @validator('seasonal_demand', 'regional_preferences')
    def validate_scores(cls, v):
        if not all(0 <= score <= 1 for score in v.values()):
            raise ValueError('All scores must be between 0 and 1')
        return v
```

2. Relationship Management
```python
from neo4j import AsyncGraphDatabase
from typing import Union, List
import logging
from datetime import datetime

class NodeRelationshipManager:
    def __init__(self, uri: str, auth: tuple):
        self.driver = AsyncGraphDatabase.driver(uri, auth=auth)
        self.logger = self.setup_logger()
    
    def setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('relationship_manager')
        logger.setLevel(logging.INFO)
        handler = logging.FileHandler('relationship_logs.jsonl')
        handler.setFormatter(logging.Formatter(
            '{"timestamp": "%(asctime)s", "level": "%(levelname)s", "message": %(message)s}'
        ))
        logger.addHandler(handler)
        return logger
    
    async def create_subnode_relationships(
        self,
        parent_id: str,
        subnodes: Dict[str, Union[EnvironmentalMetrics, NutritionalDetails, ConsumerData]]
    ) -> Dict[str, str]:
        """Create subnodes and their relationships with proper versioning"""
        try:
            async with self.driver.session() as session:
                # Create transaction
                async with session.begin_transaction() as tx:
                    results = {}
                    
                    # Create each subnode and relationship
                    for node_type, subnode in subnodes.items():
                        query = """
                        MATCH (p) WHERE p.id = $parent_id
                        CREATE (s:Subnode $subnode_props)
                        CREATE (p)-[r:HAS_SUBNODE {
                            type: $node_type,
                            created_at: datetime(),
                            created_by: $created_by,
                            version: $version
                        }]->(s)
                        RETURN s.id as subnode_id
                        """
                        
                        result = await tx.run(
                            query,
                            parent_id=parent_id,
                            subnode_props=subnode.dict(),
                            node_type=node_type,
                            created_by=subnode.created_by,
                            version=subnode.version_info.version
                        )
                        
                        record = await result.single()
                        results[node_type] = record["subnode_id"]
                    
                    await tx.commit()
                    self.logger.info(
                        f"Created subnodes for parent {parent_id}: {results}"
                    )
                    return results
                    
        except Exception as e:
            self.logger.error(f"Failed to create subnodes: {str(e)}")
            raise
    
    async def update_subnode_relationship(
        self,
        parent_id: str,
        subnode_id: str,
        new_version: VersionInfo
    ) -> None:
        """Update subnode relationship with new version"""
        try:
            async with self.driver.session() as session:
                query = """
                MATCH (p)-[r:HAS_SUBNODE]->(s)
                WHERE p.id = $parent_id AND s.id = $subnode_id
                SET r.version = $new_version,
                    r.updated_at = datetime(),
                    r.updated_by = $updated_by,
                    r.previous_version = r.version
                """
                
                await session.run(
                    query,
                    parent_id=parent_id,
                    subnode_id=subnode_id,
                    new_version=new_version.version,
                    updated_by=new_version.created_by
                )
                
                self.logger.info(
                    f"Updated relationship version for subnode {subnode_id}"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to update relationship: {str(e)}")
            raise
    
    async def delete_subnode_relationships(
        self,
        parent_id: str,
        node_types: List[NodeType] = None
    ) -> None:
        """Delete subnode relationships with cascade option"""
        try:
            async with self.driver.session() as session:
                query = """
                MATCH (p)-[r:HAS_SUBNODE]->(s)
                WHERE p.id = $parent_id
                """
                
                if node_types:
                    query += " AND r.type IN $node_types"
                
                query += """
                DELETE r, s
                """
                
                await session.run(
                    query,
                    parent_id=parent_id,
                    node_types=[t.value for t in node_types] if node_types else None
                )
                
                self.logger.info(
                    f"Deleted subnodes for parent {parent_id}"
                )
                
        except Exception as e:
            self.logger.error(f"Failed to delete subnodes: {str(e)}")
            raise
```

3. Query Optimization
```python
# src/utils/query_optimization.ts
import { QueryBuilder } from '../database/query-builder';

class SubnodeQueryOptimizer {
    private queryBuilder: QueryBuilder;
    
    constructor() {
        this.queryBuilder = new QueryBuilder();
    }
    
    buildOptimizedQuery(
        parentId: string,
        nodeTypes: string[],
        includeHistory: boolean = false
    ): string {
        // Base query with index hints
        let query = `
        MATCH (p:Parent)
        USING INDEX p:Parent(id)
        WHERE p.id = $parentId
        `;
        
        // Add subnode patterns with type filtering
        if (nodeTypes && nodeTypes.length > 0) {
            query += `
            OPTIONAL MATCH (p)-[r:HAS_SUBNODE]->(s:Subnode)
            WHERE r.type IN $nodeTypes
            `;
        } else {
            query += `
            OPTIONAL MATCH (p)-[r:HAS_SUBNODE]->(s:Subnode)
            `;
        }
        
        // Add history if requested
        if (includeHistory) {
            query += `
            OPTIONAL MATCH (s)-[:HAS_VERSION]->(v:Version)
            `;
        }
        
        // Return statement with collected subnodes
        query += `
        RETURN p,
               collect({
                   subnode: s,
                   relationship: r
                   ${includeHistory ? ', history: collect(v)' : ''}
               }) as subnodes
        `;
        
        return query;
    }
    
    buildBulkLoadQuery(
        parentIds: string[],
        nodeType: string
    ): string {
        return `
        MATCH (p:Parent)
        USING INDEX p:Parent(id)
        WHERE p.id IN $parentIds
        OPTIONAL MATCH (p)-[r:HAS_SUBNODE]->(s:Subnode)
        WHERE r.type = $nodeType
        RETURN p.id as parentId,
               collect({
                   subnode: s,
                   relationship: r
               }) as subnodes
        `;
    }
}
```

## Implementation Strategy
1. Node Structure Setup
   - Implement base node types
   - Create subnode structures
   - Set up validation rules
   - Configure versioning

2. Relationship Management
   - Implement relationship creation
   - Set up version management
   - Configure cascading operations
   - Implement audit logging

3. Query Optimization
   - Create optimized queries
   - Set up index hints
   - Implement bulk operations
   - Configure caching

## Acceptance Criteria
- [ ] Base node structure implemented with versioning
- [ ] Subnode types created with validation
- [ ] Relationship management working with versioning
- [ ] Data propagation functioning correctly
- [ ] Query optimization implemented
- [ ] Cascading operations working
- [ ] Audit trail implemented
- [ ] Error handling configured
- [ ] Documentation completed
- [ ] Performance benchmarks met
- [ ] Test coverage complete
- [ ] Migration utilities created

## Dependencies
- Ticket 2.2: Graph Schema
- Ticket 2.3: Model Definitions
- Ticket 2.4: CSV-Specific Models

## Estimated Hours
30

## Testing Requirements
- Node Structure Tests
  - Test node creation
  - Verify validation rules
  - Check versioning
  - Test metadata handling
- Relationship Tests
  - Test relationship creation
  - Verify version management
  - Test cascading operations
  - Validate audit trail
- Query Tests
  - Test optimized queries
  - Verify bulk operations
  - Check index usage
  - Test cache efficiency
- Performance Tests
  - Measure query speed
  - Test concurrent operations
  - Verify memory usage
  - Benchmark scaling

## Documentation
- Node structure overview
- Relationship management guide
- Query optimization patterns
- Version control procedures
- Audit trail implementation
- Performance tuning guide
- Migration procedures
- Best practices

## Search Space Optimization
- Clear node hierarchy
- Logical relationship organization
- Consistent versioning patterns
- Standardized query structure
- Organized utility functions

## References
- Blueprint Section 2: Architecture and Module Overview
- Blueprint Section 3: Data Model & Graph Structure
- Blueprint Section 3.1: Hierarchical Node Modeling
- Blueprint Section 3.2: Data Model Consistency
- Neo4j Documentation
- Graph Database Best Practices

## Notes
- Implements comprehensive structure
- Ensures data integrity
- Optimizes queries
- Supports versioning
- Maintains audit trail 