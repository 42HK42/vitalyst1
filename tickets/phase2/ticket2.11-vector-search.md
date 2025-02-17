# Ticket 2.11: Vector Search Integration

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive vector search capabilities for the Vitalyst Knowledge Graph, including embedding generation, index management, similarity search, and performance optimization. The system must support efficient semantic search across multiple node types while maintaining performance and integrating with the existing graph model as specified in the blueprint.

## Technical Details

1. Vector Search Models
```python
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Union, Literal
from datetime import datetime
import numpy as np
from enum import Enum

class EmbeddingDimension(int, Enum):
    SMALL = 384    # For lightweight models
    MEDIUM = 768   # For medium-sized models
    LARGE = 1536   # For large models (e.g., GPT embeddings)

class SimilarityMetric(str, Enum):
    COSINE = "cosine"
    EUCLIDEAN = "euclidean"
    DOT_PRODUCT = "dot"

class VectorIndex(BaseModel):
    name: str
    node_label: str
    property_name: str = "embedding"
    dimension: EmbeddingDimension
    similarity_metric: SimilarityMetric
    metadata: Dict[str, any] = {}
    created_at: datetime = Field(default_factory=datetime.utcnow)

class SearchResult(BaseModel):
    node_id: str
    score: float
    distance: float
    node_type: str
    metadata: Dict[str, any] = {}
```

2. Vector Search Manager Implementation
```python
class VectorSearchManager:
    def __init__(self, driver, logger, embedding_service):
        self.driver = driver
        self.logger = logger
        self.embedding_service = embedding_service
        
    async def create_vector_indexes(self) -> None:
        """Create vector indexes for supported node types"""
        try:
            indexes = [
                VectorIndex(
                    name="nutrientVectors",
                    node_label="Nutrient",
                    dimension=EmbeddingDimension.LARGE,
                    similarity_metric=SimilarityMetric.COSINE
                ),
                VectorIndex(
                    name="foodVectors",
                    node_label="Food",
                    dimension=EmbeddingDimension.LARGE,
                    similarity_metric=SimilarityMetric.COSINE
                )
            ]
            
            async with self.driver.session() as session:
                for index in indexes:
                    await session.run("""
                    CALL db.index.vector.createNodeIndex(
                        $name,
                        $label,
                        $property,
                        $dimension,
                        $metric
                    )
                    """, {
                        "name": index.name,
                        "label": index.node_label,
                        "property": index.property_name,
                        "dimension": index.dimension,
                        "metric": index.similarity_metric
                    })
                    
                    self.logger.info(
                        f"Created vector index {index.name}",
                        extra={"index": index.dict()}
                    )
                    
        except Exception as e:
            self.logger.error(f"Failed to create vector indexes: {str(e)}")
            raise
    
    async def generate_and_store_embeddings(
        self,
        node_type: str,
        batch_size: int = 100
    ) -> Dict[str, any]:
        """Generate and store embeddings for nodes"""
        try:
            stats = {
                "processed": 0,
                "failed": 0,
                "total_time": 0
            }
            
            async with self.driver.session() as session:
                # Get nodes without embeddings
                result = await session.run(f"""
                MATCH (n:{node_type})
                WHERE n.embedding IS NULL
                RETURN n
                """)
                
                nodes = await result.fetch()
                
                # Process in batches
                for i in range(0, len(nodes), batch_size):
                    batch = nodes[i:i + batch_size]
                    
                    # Generate embeddings
                    embeddings = await self.embedding_service.generate_embeddings(
                        [node["n"] for node in batch]
                    )
                    
                    # Store embeddings
                    for node, embedding in zip(batch, embeddings):
                        try:
                            await session.run(f"""
                            MATCH (n:{node_type})
                            WHERE n.id = $node_id
                            SET n.embedding = $embedding,
                                n.embedding_updated = datetime()
                            """, {
                                "node_id": node["n"]["id"],
                                "embedding": embedding.tolist()
                            })
                            
                            stats["processed"] += 1
                            
                        except Exception as e:
                            self.logger.error(
                                f"Failed to store embedding: {str(e)}",
                                extra={"node_id": node["n"]["id"]}
                            )
                            stats["failed"] += 1
            
            return stats
            
        except Exception as e:
            self.logger.error(f"Failed to generate embeddings: {str(e)}")
            raise
    
    async def search_similar_nodes(
        self,
        query_text: str,
        node_type: str,
        limit: int = 10,
        min_score: float = 0.7,
        include_metadata: bool = True
    ) -> List[SearchResult]:
        """Search for similar nodes using vector similarity"""
        try:
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(
                query_text
            )
            
            # Perform similarity search
            async with self.driver.session() as session:
                result = await session.run("""
                CALL db.index.vector.queryNodes(
                    $index_name,
                    $embedding,
                    $limit
                ) YIELD node, score
                WHERE score >= $min_score
                RETURN node, score
                ORDER BY score DESC
                """, {
                    "index_name": f"{node_type.lower()}Vectors",
                    "embedding": query_embedding.tolist(),
                    "limit": limit,
                    "min_score": min_score
                })
                
                records = await result.fetch()
                
                return [
                    SearchResult(
                        node_id=record["node"]["id"],
                        score=record["score"],
                        distance=1 - record["score"],
                        node_type=node_type,
                        metadata=record["node"] if include_metadata else {}
                    )
                    for record in records
                ]
                
        except Exception as e:
            self.logger.error(
                f"Failed to perform similarity search: {str(e)}",
                extra={"query": query_text, "node_type": node_type}
            )
            raise
```

3. Embedding Service Implementation
```python
class EmbeddingService:
    def __init__(self, model_name: str, cache_service, logger):
        self.model_name = model_name
        self.cache_service = cache_service
        self.logger = logger
        
    async def generate_embedding(
        self,
        text: str,
        use_cache: bool = True
    ) -> np.ndarray:
        """Generate embedding for single text"""
        if use_cache:
            cached = await self.cache_service.get_embedding(text)
            if cached is not None:
                return cached
        
        try:
            embedding = await self._generate_embedding(text)
            
            if use_cache:
                await self.cache_service.store_embedding(text, embedding)
            
            return embedding
            
        except Exception as e:
            self.logger.error(
                f"Failed to generate embedding: {str(e)}",
                extra={"text": text[:100]}
            )
            raise
    
    async def generate_embeddings(
        self,
        texts: List[str],
        use_cache: bool = True
    ) -> List[np.ndarray]:
        """Generate embeddings for multiple texts"""
        results = []
        cache_misses = []
        cache_miss_indices = []
        
        if use_cache:
            # Check cache first
            for i, text in enumerate(texts):
                cached = await self.cache_service.get_embedding(text)
                if cached is not None:
                    results.append(cached)
                else:
                    cache_misses.append(text)
                    cache_miss_indices.append(i)
        else:
            cache_misses = texts
            cache_miss_indices = list(range(len(texts)))
        
        if cache_misses:
            try:
                # Generate embeddings for cache misses
                new_embeddings = await self._generate_embeddings(cache_misses)
                
                # Store in cache
                if use_cache:
                    for text, embedding in zip(cache_misses, new_embeddings):
                        await self.cache_service.store_embedding(text, embedding)
                
                # Merge results
                for idx, embedding in zip(cache_miss_indices, new_embeddings):
                    results.insert(idx, embedding)
                
            except Exception as e:
                self.logger.error(
                    f"Failed to generate embeddings: {str(e)}",
                    extra={"texts": [t[:100] for t in cache_misses]}
                )
                raise
        
        return results
```

4. Performance Optimization
```python
class VectorSearchOptimizer:
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        
    async def analyze_index_performance(
        self,
        index_name: str
    ) -> Dict[str, any]:
        """Analyze vector index performance"""
        query = """
        CALL db.index.vector.stats($index_name)
        YIELD *
        RETURN *
        """
        
        async with self.driver.session() as session:
            result = await session.run(query, {"index_name": index_name})
            stats = await result.single()
            
            return {
                "size": stats["size"],
                "dimension": stats["dimension"],
                "metric": stats["metric"],
                "build_time": stats["buildTime"],
                "search_time": stats["searchTime"],
                "memory_usage": stats["memoryUsage"]
            }
    
    async def optimize_index_parameters(
        self,
        index_name: str,
        sample_queries: List[str]
    ) -> Dict[str, any]:
        """Optimize index parameters for performance"""
        # Implementation for parameter optimization
        pass
```

## Implementation Strategy
1. Vector Search Setup
   - Implement vector models
   - Create index management
   - Set up embedding service
   - Configure caching

2. Embedding Generation
   - Implement text processing
   - Create embedding generation
   - Set up batch processing
   - Configure error handling

3. Search Implementation
   - Create search patterns
   - Implement similarity metrics
   - Set up result ranking
   - Configure performance

4. Integration
   - Implement node type support
   - Set up data synchronization
   - Configure monitoring
   - Implement reporting

## Acceptance Criteria
- [ ] Vector models implemented
- [ ] Index management working
- [ ] Embedding generation functioning
- [ ] Similarity search implemented
- [ ] Batch processing working
- [ ] Caching system configured
- [ ] Performance optimization completed
- [ ] Error handling implemented
- [ ] Documentation completed
- [ ] Performance benchmarks met
- [ ] Test coverage complete
- [ ] Integration tests passing

## Dependencies
- Ticket 2.10: Neo4j Graph Model
- Ticket 2.3: Model Definitions
- Ticket 2.8: Historical Tracking

## Estimated Hours
35

## Testing Requirements
- Model Tests
  - Test vector operations
  - Verify embeddings
  - Check similarity metrics
  - Validate caching
- Search Tests
  - Test similarity search
  - Verify ranking
  - Check performance
  - Validate results
- Integration Tests
  - Test node type support
  - Verify data sync
  - Test monitoring
  - Check reporting
- Performance Tests
  - Measure search speed
  - Test batch processing
  - Verify memory usage
  - Benchmark operations

## Documentation
- Vector search overview
- Index management guide
- Embedding generation guide
- Performance tuning guide
- Integration patterns
- Best practices
- Monitoring setup
- Troubleshooting guide

## Search Space Optimization
- Clear vector hierarchy
- Logical index organization
- Consistent embedding patterns
- Standardized search operations
- Organized caching strategy

## References
- Blueprint Section 3: Data Model & Graph Structure
- Blueprint Section 9: Frameworks, Deployment, Security & Monitoring
- Blueprint Section 3.2: Data Model Consistency
- Blueprint Section 5: Data Quality and Validation
- Neo4j Vector Search Documentation
- Embedding Model Best Practices

## Notes
- Implements comprehensive search
- Ensures performance
- Optimizes embeddings
- Supports integration
- Maintains scalability 