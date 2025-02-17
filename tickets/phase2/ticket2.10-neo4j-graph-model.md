# Ticket 2.10: Neo4j Graph Model Implementation

## Priority
High

## Type
Development

## Status
To Do

## Description
Design and implement comprehensive Neo4j graph model for the Vitalyst Knowledge Graph, including node labels, relationship types, properties, constraints, and optimized index strategies. The implementation must support efficient querying, maintain data integrity, and integrate with multi-language and historical tracking features while following the blueprint specifications.

## Technical Details

1. Core Graph Model
```python
from enum import Enum
from typing import Dict, List, Optional, Union
from datetime import datetime
from pydantic import BaseModel, Field

class NodeLabel(str, Enum):
    BASE = "Base"  # Base node type
    NUTRIENT = "Nutrient"
    FOOD = "Food"
    CONTENT = "Content"
    USER = "User"
    ENVIRONMENTAL_METRICS = "EnvironmentalMetrics"
    NUTRITIONAL_DETAILS = "NutritionalDetails"
    CONSUMER_DATA = "ConsumerData"
    TRANSLATION = "Translation"
    VALIDATION = "Validation"
    HISTORY = "History"
    SOURCE = "Source"

class RelationshipType(str, Enum):
    # Core relationships
    HAS_NUTRIENT = "HAS_NUTRIENT"
    CONTAINS = "CONTAINS"
    REFERS_TO = "REFERS_TO"
    
    # Metadata relationships
    CREATED_BY = "CREATED_BY"
    UPDATED_BY = "UPDATED_BY"
    VALIDATED_BY = "VALIDATED_BY"
    
    # Hierarchical relationships
    HAS_DETAIL = "HAS_DETAIL"
    HAS_METRICS = "HAS_METRICS"
    HAS_HISTORY = "HAS_HISTORY"
    
    # Translation relationships
    HAS_TRANSLATION = "HAS_TRANSLATION"
    TRANSLATED_FROM = "TRANSLATED_FROM"
    
    # Validation relationships
    HAS_VALIDATION = "HAS_VALIDATION"
    VALIDATES = "VALIDATES"
    
    # Source relationships
    SOURCED_FROM = "SOURCED_FROM"
    VERIFIED_BY = "VERIFIED_BY"

class BaseNodeProperties(BaseModel):
    id: str = Field(..., description="Unique identifier")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    created_by: str
    updated_by: str
    version: str = "1.0.0"
    validation_status: str = "pending"
    metadata: Dict[str, any] = {}

class GraphModelManager:
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        
    async def initialize_schema(self) -> None:
        """Initialize graph schema with constraints and indexes"""
        try:
            async with self.driver.session() as session:
                # Create node constraints
                await self._create_node_constraints(session)
                # Create relationship constraints
                await self._create_relationship_constraints(session)
                # Create indexes
                await self._create_indexes(session)
                
                self.logger.info("Graph schema initialized successfully")
                
        except Exception as e:
            self.logger.error(f"Failed to initialize schema: {str(e)}")
            raise
    
    async def _create_node_constraints(self, session) -> None:
        """Create node property constraints"""
        constraints = [
            # Unique ID constraints
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Base) REQUIRE n.id IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Base) REQUIRE n.created_at IS NOT NULL",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Base) REQUIRE n.version IS NOT NULL",
            
            # Type-specific constraints
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Nutrient) REQUIRE n.vitID IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:Food) REQUIRE n.name IS UNIQUE",
            "CREATE CONSTRAINT IF NOT EXISTS FOR (n:User) REQUIRE n.email IS UNIQUE"
        ]
        
        for constraint in constraints:
            await session.run(constraint)
    
    async def _create_relationship_constraints(self, session) -> None:
        """Create relationship property constraints"""
        constraints = [
            # Temporal validity constraints
            "CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:HAS_HISTORY]-() REQUIRE r.valid_from IS NOT NULL",
            "CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:HAS_TRANSLATION]-() REQUIRE r.created_at IS NOT NULL",
            
            # Property existence constraints
            "CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:VALIDATED_BY]-() REQUIRE r.timestamp IS NOT NULL",
            "CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:CONTAINS]-() REQUIRE r.amount IS NOT NULL"
        ]
        
        for constraint in constraints:
            await session.run(constraint)
    
    async def _create_indexes(self, session) -> None:
        """Create optimized indexes"""
        indexes = [
            # B-tree indexes for exact lookups
            "CREATE INDEX IF NOT EXISTS FOR (n:Base) ON (n.id)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Nutrient) ON (n.vitID)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Food) ON (n.name)",
            
            # Composite indexes for common queries
            "CREATE INDEX IF NOT EXISTS FOR (n:Base) ON (n.type, n.validation_status)",
            "CREATE INDEX IF NOT EXISTS FOR (n:Translation) ON (n.language, n.content_type)",
            
            # Full-text indexes for search
            """
            CALL db.index.fulltext.createNodeIndex(
                'nutrientSearch',
                ['Nutrient'],
                ['name', 'description']
            )
            """,
            """
            CALL db.index.fulltext.createNodeIndex(
                'foodSearch',
                ['Food'],
                ['name', 'description']
            )
            """
        ]
        
        for index in indexes:
            await session.run(index)
```

2. Query Pattern Implementation
```python
class GraphQueryPatterns:
    def __init__(self, driver):
        self.driver = driver
    
    async def get_node_with_relationships(
        self,
        node_id: str,
        relationship_types: Optional[List[RelationshipType]] = None,
        include_history: bool = False,
        include_translations: bool = False
    ) -> Dict:
        """Get node with specified relationships"""
        query = """
        MATCH (n:Base {id: $node_id})
        """
        
        if relationship_types:
            for rel_type in relationship_types:
                query += f"""
                OPTIONAL MATCH (n)-[:{rel_type}]->(r_{rel_type})
                """
                
        if include_history:
            query += """
            OPTIONAL MATCH (n)-[:HAS_HISTORY]->(h:History)
            """
            
        if include_translations:
            query += """
            OPTIONAL MATCH (n)-[:HAS_TRANSLATION]->(t:Translation)
            """
            
        query += """
        RETURN n,
               [rel_type IN $rel_types | collect(r_{rel_type})] as relationships,
               collect(h) as history,
               collect(t) as translations
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {
                "node_id": node_id,
                "rel_types": [r.value for r in relationship_types] if relationship_types else []
            })
            
            return await result.single()
    
    async def find_nodes_by_property(
        self,
        label: NodeLabel,
        property_name: str,
        property_value: any,
        limit: int = 10
    ) -> List[Dict]:
        """Find nodes by property value using appropriate index"""
        query = f"""
        MATCH (n:{label})
        WHERE n.{property_name} = $value
        RETURN n
        LIMIT $limit
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {
                "value": property_value,
                "limit": limit
            })
            
            return [record["n"] for record in await result.fetch()]
```

3. Performance Optimization
```python
class GraphOptimizer:
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
    
    async def analyze_index_usage(self) -> Dict[str, any]:
        """Analyze index usage patterns"""
        query = """
        CALL db.indexes()
        YIELD name, type, labelsOrTypes, properties, state, popularity
        RETURN *
        """
        
        async with self.driver.session() as session:
            result = await session.run(query)
            return {
                record["name"]: {
                    "type": record["type"],
                    "labels": record["labelsOrTypes"],
                    "properties": record["properties"],
                    "popularity": record["popularity"]
                }
                for record in await result.fetch()
            }
    
    async def optimize_queries(
        self,
        query: str,
        params: Dict[str, any]
    ) -> Dict[str, any]:
        """Analyze and optimize query execution"""
        explain_query = f"EXPLAIN {query}"
        
        async with self.driver.session() as session:
            result = await session.run(explain_query, params)
            plan = result.plan
            
            return {
                "estimated_rows": plan.estimated_rows,
                "indexes_used": [
                    idx for idx in plan.identifiers
                    if idx.startswith('INDEX')
                ],
                "suggestions": self._generate_optimization_suggestions(plan)
            }
    
    def _generate_optimization_suggestions(
        self,
        plan: any
    ) -> List[str]:
        """Generate query optimization suggestions"""
        suggestions = []
        
        # Analyze plan operators
        if 'AllNodesScan' in str(plan):
            suggestions.append("Consider adding an index to avoid full node scan")
            
        if 'CartesianProduct' in str(plan):
            suggestions.append("Optimize query to avoid cartesian products")
            
        return suggestions
```

## Implementation Strategy
1. Schema Design
   - Define node labels and properties
   - Create relationship types
   - Set up constraints
   - Configure indexes

2. Query Optimization
   - Implement query patterns
   - Create index strategy
   - Set up performance monitoring
   - Configure caching

3. Integration
   - Implement language support
   - Set up historical tracking
   - Configure validation rules
   - Implement data lineage

4. Performance Tuning
   - Optimize indexes
   - Create query patterns
   - Set up monitoring
   - Configure benchmarks

## Acceptance Criteria
- [ ] Node labels and properties implemented
- [ ] Relationship types defined
- [ ] Constraints created and validated
- [ ] Indexes optimized for common queries
- [ ] Query patterns implemented
- [ ] Performance monitoring configured
- [ ] Language support integrated
- [ ] Historical tracking working
- [ ] Documentation completed
- [ ] Performance benchmarks met
- [ ] Test coverage complete
- [ ] Integration tests passing

## Dependencies
- Ticket 2.2: Graph Schema
- Ticket 2.3: Model Definitions
- Ticket 2.5: Hierarchical Node Structure
- Ticket 2.9: Multi-Language Support

## Estimated Hours
40

## Testing Requirements
- Schema Tests
  - Test node creation
  - Verify relationships
  - Check constraints
  - Validate indexes
- Query Tests
  - Test common patterns
  - Verify optimizations
  - Check performance
  - Validate caching
- Integration Tests
  - Test language support
  - Verify historical tracking
  - Test validation rules
  - Check data lineage
- Performance Tests
  - Measure query speed
  - Test concurrent access
  - Verify memory usage
  - Benchmark operations

## Documentation
- Graph model overview
- Index strategy guide
- Query optimization patterns
- Performance tuning guide
- Integration patterns
- Best practices
- Monitoring setup
- Troubleshooting guide

## Search Space Optimization
- Clear node hierarchy
- Logical relationship types
- Consistent property naming
- Standardized query patterns
- Organized index structure

## References
- Blueprint Section 3: Data Model & Graph Structure
- Blueprint Section 3.1: Hierarchical Node Modeling
- Blueprint Section 3.2: Data Model Consistency
- Blueprint Section 5: Data Quality and Validation
- Neo4j Best Practices
- Graph Database Patterns

## Notes
- Implements comprehensive model
- Ensures performance
- Optimizes queries
- Supports integration
- Maintains scalability 