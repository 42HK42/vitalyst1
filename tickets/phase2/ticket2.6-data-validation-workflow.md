# Ticket 2.6: Data Validation Workflow

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive data validation workflow for the Vitalyst Knowledge Graph, including status transitions, validation rules, review processes, and validation history tracking for both primary nodes and subnodes. The implementation must ensure data quality, maintain audit trails, and support role-based validation workflows while following the blueprint specifications.

## Technical Details

1. Validation Status Management
```python
from enum import Enum
from typing import Optional, Dict, List
from datetime import datetime
from pydantic import BaseModel, validator
import uuid

class ValidationStatus(Enum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    IN_REVIEW = "in_review"
    APPROVED = "approved"
    REJECTED = "rejected"
    NEEDS_REVISION = "needs_revision"
    ARCHIVED = "archived"

class ValidationEvent(BaseModel):
    id: str = uuid.uuid4()
    status: ValidationStatus
    timestamp: datetime
    reviewer_id: Optional[str]
    comments: Optional[str]
    changes_requested: Optional[List[str]]
    metadata: Dict[str, any] = {}
    confidence_score: float
    
    @validator('confidence_score')
    def validate_confidence(cls, v):
        if not 0 <= v <= 1:
            raise ValueError('Confidence score must be between 0 and 1')
        return v

class ValidationManager:
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
        
    async def update_validation_status(
        self,
        node_id: str,
        new_status: ValidationStatus,
        reviewer_id: Optional[str] = None,
        comments: Optional[str] = None,
        changes_requested: Optional[List[str]] = None,
        confidence_score: float = 1.0
    ) -> ValidationEvent:
        """Update node validation status with event tracking"""
        try:
            event = ValidationEvent(
                status=new_status,
                timestamp=datetime.utcnow(),
                reviewer_id=reviewer_id,
                comments=comments,
                changes_requested=changes_requested,
                confidence_score=confidence_score
            )
            
            async with self.driver.session() as session:
                async with session.begin_transaction() as tx:
                    # Update node status
                    await tx.run("""
                    MATCH (n) WHERE n.id = $node_id
                    SET n.validation_status = $status,
                        n.last_reviewed_by = $reviewer_id,
                        n.last_reviewed_at = datetime()
                    """, {
                        "node_id": node_id,
                        "status": new_status.value,
                        "reviewer_id": reviewer_id
                    })
                    
                    # Create validation event
                    await tx.run("""
                    MATCH (n) WHERE n.id = $node_id
                    CREATE (v:ValidationEvent $event_props)
                    CREATE (n)-[:HAS_VALIDATION_EVENT]->(v)
                    """, {
                        "node_id": node_id,
                        "event_props": event.dict()
                    })
                    
                    # Propagate to subnodes if needed
                    if self._should_propagate_validation(new_status):
                        await self._propagate_validation_status(
                            tx, node_id, new_status, reviewer_id
                        )
                    
                    await tx.commit()
                    
                    self.logger.info(
                        f"Updated validation status for node {node_id}",
                        extra={"event": event.dict()}
                    )
                    
                    return event
                    
        except Exception as e:
            self.logger.error(
                f"Failed to update validation status: {str(e)}",
                extra={"node_id": node_id, "status": new_status.value}
            )
            raise

    async def _propagate_validation_status(
        self,
        tx,
        node_id: str,
        status: ValidationStatus,
        reviewer_id: str
    ) -> None:
        """Propagate validation status to subnodes"""
        await tx.run("""
        MATCH (n)-[:HAS_SUBNODE]->(s)
        WHERE n.id = $node_id
        SET s.validation_status = $status,
            s.propagated_from = $node_id,
            s.propagated_at = datetime(),
            s.propagated_by = $reviewer_id
        """, {
            "node_id": node_id,
            "status": status.value,
            "reviewer_id": reviewer_id
        })

    def _should_propagate_validation(
        self,
        status: ValidationStatus
    ) -> bool:
        """Determine if validation status should propagate"""
        return status in [
            ValidationStatus.APPROVED,
            ValidationStatus.REJECTED,
            ValidationStatus.ARCHIVED
        ]
```

2. Validation Rules Engine
```python
from typing import Dict, List, Type
from pydantic import BaseModel
import re

class ValidationRule(BaseModel):
    id: str
    name: str
    description: str
    severity: str  # error, warning, info
    node_types: List[str]
    validation_fn: callable
    error_message: str
    metadata: Dict[str, any] = {}

class ValidationResult(BaseModel):
    rule_id: str
    passed: bool
    severity: str
    message: str
    details: Optional[Dict[str, any]] = None
    timestamp: datetime = Field(default_factory=datetime.utcnow)

class ValidationRulesEngine:
    def __init__(self):
        self.rules: Dict[str, ValidationRule] = {}
        self.initialize_rules()
    
    def initialize_rules(self):
        """Initialize validation rules"""
        # Node-specific rules
        self.add_rule(
            ValidationRule(
                id="NUT_001",
                name="nutrient_required_fields",
                description="Validates required fields for nutrient nodes",
                severity="error",
                node_types=["Nutrient"],
                validation_fn=self._validate_nutrient_required_fields,
                error_message="Missing required nutrient fields"
            )
        )
        
        # Relationship rules
        self.add_rule(
            ValidationRule(
                id="REL_001",
                name="required_relationships",
                description="Validates required relationships",
                severity="error",
                node_types=["BaseNode"],
                validation_fn=self._validate_required_relationships,
                error_message="Missing required relationships"
            )
        )
        
        # Data quality rules
        self.add_rule(
            ValidationRule(
                id="DQ_001",
                name="data_quality_score",
                description="Validates data quality scores",
                severity="warning",
                node_types=["BaseNode"],
                validation_fn=self._validate_data_quality,
                error_message="Low data quality score"
            )
        )
    
    def add_rule(self, rule: ValidationRule):
        """Add new validation rule"""
        self.rules[rule.id] = rule
    
    async def validate_node(
        self,
        node: Dict,
        node_type: str
    ) -> List[ValidationResult]:
        """Validate node against applicable rules"""
        results = []
        
        for rule in self.rules.values():
            if node_type in rule.node_types:
                try:
                    passed, details = await rule.validation_fn(node)
                    results.append(
                        ValidationResult(
                            rule_id=rule.id,
                            passed=passed,
                            severity=rule.severity,
                            message=rule.error_message if not passed else "Passed",
                            details=details
                        )
                    )
                except Exception as e:
                    results.append(
                        ValidationResult(
                            rule_id=rule.id,
                            passed=False,
                            severity="error",
                            message=f"Validation error: {str(e)}"
                        )
                    )
        
        return results
    
    @staticmethod
    async def _validate_nutrient_required_fields(
        node: Dict
    ) -> Tuple[bool, Optional[Dict]]:
        """Validate required fields for nutrient nodes"""
        required_fields = [
            'name', 'vitID', 'chemical_formula',
            'molecular_weight', 'description'
        ]
        
        missing_fields = [
            field for field in required_fields
            if field not in node or not node[field]
        ]
        
        return (
            len(missing_fields) == 0,
            {"missing_fields": missing_fields} if missing_fields else None
        )
    
    @staticmethod
    async def _validate_required_relationships(
        node: Dict
    ) -> Tuple[bool, Optional[Dict]]:
        """Validate required relationships"""
        required_relationships = {
            'Nutrient': ['HAS_DETAILS'],
            'Food': ['HAS_METRICS', 'CONTAINS'],
            'Source': ['VERIFIES']
        }
        
        node_type = node.get('type')
        if node_type not in required_relationships:
            return True, None
            
        missing_relationships = [
            rel for rel in required_relationships[node_type]
            if rel not in node.get('relationships', [])
        ]
        
        return (
            len(missing_relationships) == 0,
            {"missing_relationships": missing_relationships} if missing_relationships else None
        )
```

3. Review Process Management
```python
class ReviewAssignment(BaseModel):
    id: str = uuid.uuid4()
    node_id: str
    reviewer_id: str
    assigned_at: datetime = Field(default_factory=datetime.utcnow)
    due_date: Optional[datetime]
    priority: str = "normal"
    status: str = "pending"
    metadata: Dict[str, any] = {}

class ReviewQueue:
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
    
    async def assign_reviewer(
        self,
        node_id: str,
        reviewer_id: str,
        due_date: Optional[datetime] = None,
        priority: str = "normal"
    ) -> ReviewAssignment:
        """Assign node for review"""
        assignment = ReviewAssignment(
            node_id=node_id,
            reviewer_id=reviewer_id,
            due_date=due_date,
            priority=priority
        )
        
        async with self.driver.session() as session:
            await session.run("""
            MATCH (n) WHERE n.id = $node_id
            CREATE (r:ReviewAssignment $assignment_props)
            CREATE (n)-[:HAS_REVIEW_ASSIGNMENT]->(r)
            SET n.validation_status = 'in_review'
            """, {
                "node_id": node_id,
                "assignment_props": assignment.dict()
            })
            
            self.logger.info(
                f"Created review assignment for node {node_id}",
                extra={"assignment": assignment.dict()}
            )
            
            return assignment
    
    async def get_reviewer_queue(
        self,
        reviewer_id: str
    ) -> List[Dict]:
        """Get review queue for reviewer"""
        async with self.driver.session() as session:
            result = await session.run("""
            MATCH (n)-[:HAS_REVIEW_ASSIGNMENT]->(r:ReviewAssignment)
            WHERE r.reviewer_id = $reviewer_id
              AND r.status = 'pending'
            RETURN n, r
            ORDER BY r.priority DESC, r.assigned_at ASC
            """, {
                "reviewer_id": reviewer_id
            })
            
            return [record.data() for record in await result.fetch()]
```

4. Validation Metrics and Reporting
```python
class ValidationMetrics:
    def __init__(self, driver, logger):
        self.driver = driver
        self.logger = logger
    
    async def get_validation_stats(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Get validation statistics for time period"""
        async with self.driver.session() as session:
            result = await session.run("""
            MATCH (n)-[:HAS_VALIDATION_EVENT]->(e:ValidationEvent)
            WHERE e.timestamp >= $start_date
              AND e.timestamp <= $end_date
            RETURN e.status as status,
                   count(e) as count,
                   avg(e.confidence_score) as avg_confidence
            """, {
                "start_date": start_date,
                "end_date": end_date
            })
            
            return {
                record["status"]: {
                    "count": record["count"],
                    "avg_confidence": record["avg_confidence"]
                }
                for record in await result.fetch()
            }
    
    async def get_reviewer_metrics(
        self,
        reviewer_id: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """Get metrics for specific reviewer"""
        async with self.driver.session() as session:
            result = await session.run("""
            MATCH (n)-[:HAS_VALIDATION_EVENT]->(e:ValidationEvent)
            WHERE e.reviewer_id = $reviewer_id
              AND e.timestamp >= $start_date
              AND e.timestamp <= $end_date
            RETURN count(e) as total_reviews,
                   avg(e.confidence_score) as avg_confidence,
                   collect(distinct e.status) as status_types
            """, {
                "reviewer_id": reviewer_id,
                "start_date": start_date,
                "end_date": end_date
            })
            
            return await result.single()
```

## Implementation Strategy
1. Validation Framework Setup
   - Implement validation status management
   - Create validation rules engine
   - Set up review process
   - Configure metrics collection

2. Integration with Node Structure
   - Implement node validation
   - Set up relationship validation
   - Configure validation propagation
   - Implement validation history

3. Review Process Implementation
   - Create review queue management
   - Set up reviewer assignment
   - Implement review workflow
   - Configure notifications

4. Metrics and Reporting
   - Implement validation metrics
   - Create reporting system
   - Set up dashboards
   - Configure alerts

## Acceptance Criteria
- [ ] Validation status management implemented
- [ ] Validation rules engine working
- [ ] Review process functioning
- [ ] Validation history tracking
- [ ] Status transitions working
- [ ] Validation propagation implemented
- [ ] Review queue management working
- [ ] Metrics collection functioning
- [ ] Documentation completed
- [ ] Performance benchmarks met
- [ ] Test coverage complete
- [ ] Integration tests passing

## Dependencies
- Ticket 2.2: Graph Schema
- Ticket 2.3: Model Definitions
- Ticket 2.5: Hierarchical Node Structure

## Estimated Hours
35

## Testing Requirements
- Validation Framework Tests
  - Test status transitions
  - Verify validation rules
  - Check validation history
  - Test propagation logic
- Review Process Tests
  - Test queue management
  - Verify reviewer assignment
  - Test review workflow
  - Validate notifications
- Integration Tests
  - Test node validation
  - Verify relationship validation
  - Test validation propagation
  - Check history tracking
- Performance Tests
  - Measure validation speed
  - Test concurrent reviews
  - Verify queue performance
  - Benchmark metrics collection

## Documentation
- Validation framework overview
- Validation rules guide
- Review process documentation
- Metrics and reporting guide
- Integration patterns
- Performance tuning
- Troubleshooting procedures
- Best practices

## Search Space Optimization
- Clear validation hierarchy
- Logical rule organization
- Consistent status patterns
- Standardized review process
- Organized metrics collection

## References
- Blueprint Section 8: Roles, Workflows & Validation
- Blueprint Section 3.2: Data Model Consistency
- Blueprint Section 3.1: Hierarchical Node Modeling
- Neo4j Documentation
- Graph Database Best Practices

## Notes
- Implements comprehensive validation
- Ensures data quality
- Optimizes review process
- Supports metrics collection
- Maintains audit trail 