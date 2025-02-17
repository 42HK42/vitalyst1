# Ticket 3.2: Implement Core API Endpoints

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive core API endpoints for the Vitalyst Knowledge Graph that provide secure, efficient, and well-documented access to the graph database. The implementation must include proper validation, error handling, rate limiting, and monitoring while following the blueprint specifications for API development and zero-trust principles.

## Technical Details

1. Food Node Endpoint Implementation
```python
# src/api/v1/endpoints/foods.py
from fastapi import APIRouter, Depends, HTTPException, Path, Query
from typing import Optional, List
from datetime import datetime
from src.models.food import FoodNode, FoodCreate, FoodUpdate
from src.services.graph import GraphService
from src.services.validation import ValidationService
from src.api.dependencies import get_current_user, require_permissions
from src.utils.monitoring import track_operation
from src.utils.logging import get_logger

router = APIRouter(prefix="/api/v1/foods", tags=["foods"])
logger = get_logger(__name__)

@router.get("/{food_id}", response_model=FoodNode)
async def get_food(
    food_id: str = Path(..., description="The ID of the food node"),
    include_relationships: bool = Query(False, description="Include related nodes"),
    current_user = Depends(get_current_user),
    graph: GraphService = Depends(),
) -> FoodNode:
    """
    Retrieve a food node by its identifier.
    
    Returns a complete JSON response with all relevant fields and optionally includes relationships.
    """
    try:
        with track_operation("get_food", {"food_id": food_id}):
            node = await graph.get_food_node(
                food_id,
                include_relationships=include_relationships
            )
            if not node:
                raise HTTPException(status_code=404, detail="Food node not found")
            return node
    except Exception as e:
        logger.error(f"Error retrieving food node: {str(e)}", 
            extra={"food_id": food_id, "user_id": current_user.id}
        )
        raise

@router.post("", response_model=FoodNode, status_code=201)
async def create_food(
    food: FoodCreate,
    current_user = Depends(get_current_user),
    graph: GraphService = Depends(),
    validation: ValidationService = Depends(),
) -> FoodNode:
    """
    Create a new food node with validation.
    """
    try:
        with track_operation("create_food"):
            # Validate food data
            await validation.validate_food_data(food)
            
            # Create node with metadata
            node = await graph.create_food_node({
                **food.dict(),
                "created_by": current_user.id,
                "created_at": datetime.utcnow(),
                "version": "1.0.0",
                "validation_status": "draft"
            })
            
            logger.info("Food node created", 
                extra={
                    "node_id": node.id,
                    "user_id": current_user.id
                }
            )
            return node
    except Exception as e:
        logger.error(f"Error creating food node: {str(e)}", 
            extra={"user_id": current_user.id}
        )
        raise
```

2. Content Node Endpoint Implementation
```python
# src/api/v1/endpoints/contents.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional
from datetime import datetime
from src.models.content import ContentNode, ContentCreate
from src.services.graph import GraphService
from src.services.validation import ValidationService
from src.services.enrichment import EnrichmentService
from src.api.dependencies import get_current_user, require_permissions
from src.utils.monitoring import track_operation
from src.utils.logging import get_logger

router = APIRouter(prefix="/api/v1/contents", tags=["contents"])
logger = get_logger(__name__)

@router.post("", response_model=ContentNode, status_code=201)
async def create_content(
    content: ContentCreate,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    graph: GraphService = Depends(),
    validation: ValidationService = Depends(),
    enrichment: EnrichmentService = Depends(),
) -> ContentNode:
    """
    Create a new content node linking food with nutrient data.
    
    Includes automatic validation and optional AI enrichment.
    """
    try:
        with track_operation("create_content"):
            # Validate relationships exist
            await validation.validate_relationships(
                food_id=content.food_id,
                nutrient_id=content.nutrient_id
            )
            
            # Create content node
            node = await graph.create_content_node({
                **content.dict(),
                "created_by": current_user.id,
                "created_at": datetime.utcnow(),
                "version": "1.0.0",
                "validation_status": "draft"
            })
            
            # Schedule background enrichment
            background_tasks.add_task(
                enrichment.enrich_content_node,
                node.id
            )
            
            logger.info("Content node created", 
                extra={
                    "node_id": node.id,
                    "user_id": current_user.id
                }
            )
            return node
    except Exception as e:
        logger.error(f"Error creating content node: {str(e)}", 
            extra={"user_id": current_user.id}
        )
        raise
```

3. AI Enrichment Endpoint Implementation
```python
# src/api/v1/endpoints/enrichment.py
from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from typing import Optional
from src.models.enrichment import EnrichmentRequest, EnrichmentResponse
from src.services.ai import AIService
from src.services.graph import GraphService
from src.api.dependencies import get_current_user, require_permissions
from src.utils.monitoring import track_operation
from src.utils.logging import get_logger
from src.utils.rate_limiting import rate_limit

router = APIRouter(prefix="/api/v1/ai", tags=["ai"])
logger = get_logger(__name__)

@router.post("/enrich", response_model=EnrichmentResponse)
@rate_limit(max_requests=10, window_seconds=60)
async def enrich_node(
    request: EnrichmentRequest,
    background_tasks: BackgroundTasks,
    current_user = Depends(get_current_user),
    permissions = Depends(require_permissions(["enrich"])),
    graph: GraphService = Depends(),
    ai_service: AIService = Depends(),
) -> EnrichmentResponse:
    """
    Trigger AI enrichment for a node with fallback mechanisms.
    """
    try:
        with track_operation("enrich_node", {"node_id": request.node_id}):
            # Verify node exists
            node = await graph.get_node(request.node_id)
            if not node:
                raise HTTPException(status_code=404, detail="Node not found")
            
            # Update node status
            await graph.update_node_status(
                request.node_id,
                "enriching",
                current_user.id
            )
            
            # Schedule enrichment task
            task_id = await ai_service.schedule_enrichment(
                node_id=request.node_id,
                prompt=request.prompt,
                user_id=current_user.id
            )
            
            logger.info("Enrichment scheduled", 
                extra={
                    "node_id": request.node_id,
                    "task_id": task_id,
                    "user_id": current_user.id
                }
            )
            
            return EnrichmentResponse(
                task_id=task_id,
                status="scheduled",
                message="Enrichment task scheduled successfully"
            )
    except Exception as e:
        logger.error(f"Error scheduling enrichment: {str(e)}", 
            extra={
                "node_id": request.node_id,
                "user_id": current_user.id
            }
        )
        raise
```

4. Model Definitions
```python
# src/models/food.py
from pydantic import BaseModel, Field
from typing import Optional, List, Dict
from datetime import datetime

class FoodBase(BaseModel):
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    category: str = Field(..., regex="^[a-zA-Z_]+$")
    subcategory: Optional[str] = Field(None, regex="^[a-zA-Z_]+$")
    seasonal_availability: Optional[List[str]] = Field(default_factory=list)
    storage_conditions: Optional[str]
    preparation_methods: Optional[List[str]] = Field(default_factory=list)
    allergens: Optional[List[str]] = Field(default_factory=list)
    dietary_flags: Optional[List[str]] = Field(default_factory=list)

class FoodCreate(FoodBase):
    pass

class FoodUpdate(FoodBase):
    pass

class FoodNode(FoodBase):
    id: str
    version: str
    created_at: datetime
    updated_at: Optional[datetime]
    created_by: str
    updated_by: Optional[str]
    validation_status: str
    validation_history: List[Dict]
    metadata: Dict

    class Config:
        orm_mode = True
```

5. Error Handling Implementation
```python
# src/api/errors.py
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from src.utils.logging import get_logger
from typing import Any, Dict

logger = get_logger(__name__)

class APIError(HTTPException):
    def __init__(
        self,
        status_code: int,
        detail: str,
        error_code: str,
        extra: Dict[str, Any] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.error_code = error_code
        self.extra = extra or {}

async def api_error_handler(
    request: Request,
    exc: APIError
) -> JSONResponse:
    """Handle API-specific errors with proper logging and monitoring"""
    logger.error(f"API Error: {exc.detail}",
        extra={
            "error_code": exc.error_code,
            "status_code": exc.status_code,
            "path": request.url.path,
            "method": request.method,
            **exc.extra
        }
    )
    
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": exc.detail,
            "error_code": exc.error_code,
            "request_id": request.state.request_id
        }
    )
```

## Implementation Strategy
1. Endpoint Development
   - Implement core endpoints with validation
   - Add error handling and logging
   - Configure rate limiting
   - Set up monitoring

2. Data Validation
   - Implement input validation
   - Add relationship validation
   - Set up data consistency checks
   - Configure validation rules

3. Error Handling
   - Implement error types
   - Add error logging
   - Set up monitoring
   - Configure error responses

4. Performance Optimization
   - Add response caching
   - Implement query optimization
   - Configure connection pooling
   - Set up performance monitoring

## Acceptance Criteria
- [ ] All core endpoints implemented with proper validation
- [ ] Error handling and logging working for all endpoints
- [ ] Rate limiting configured and tested
- [ ] Input validation implemented for all endpoints
- [ ] Relationship validation working
- [ ] Monitoring integration complete
- [ ] Performance metrics collected
- [ ] Documentation generated
- [ ] All tests passing
- [ ] Security measures implemented
- [ ] Logging format validated
- [ ] Error responses standardized
- [ ] API versioning implemented

## Dependencies
- Ticket 3.1: Backend Setup
- Ticket 2.2: Graph Schema
- Ticket 2.13: Performance Optimization
- Ticket 2.14: Graph Monitoring

## Estimated Hours
25

## Testing Requirements
- Unit Tests
  - Test endpoint functionality
  - Verify input validation
  - Check error handling
  - Validate responses
- Integration Tests
  - Test database interactions
  - Verify relationship handling
  - Check enrichment flow
  - Test rate limiting
- Performance Tests
  - Measure response times
  - Test concurrent requests
  - Verify caching
  - Check memory usage
- Security Tests
  - Verify authentication
  - Test authorization
  - Check input sanitization
  - Validate rate limiting

## Documentation
- API endpoint specifications
- Input validation rules
- Error handling patterns
- Rate limiting configuration
- Monitoring integration
- Performance considerations
- Security measures
- Testing procedures
- Deployment guide
- Troubleshooting guide

## Search Space Optimization
- Clear endpoint organization
- Consistent error handling
- Standardized validation patterns
- Organized monitoring metrics
- Structured logging format

## References
- Blueprint Section 3: API und Datenimport
- Blueprint Section 9: Frameworks, Deployment, Security & Monitoring
- Blueprint Section 4: Development Standards
- FastAPI Documentation
- Neo4j Python Driver Documentation
- Prometheus Python Client

## Notes
- Implements comprehensive API endpoints
- Ensures data validation
- Optimizes performance
- Maintains security
- Supports monitoring 