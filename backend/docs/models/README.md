# Data Models

## Overview
Documentation for the Vitalyst Knowledge Graph data models and their relationships.

## Node Models

### Food Node
Represents food items in the knowledge graph.
```python
class FoodNode(BaseNode):
    name: str
    type: str
    description: Optional[str]
    nutrition: Dict[str, Any]
    source: Optional[str]
    source_reliability: float
```

### Nutrient Node
Represents nutrients, vitamins, and minerals.
```python
class NutrientNode(BaseNode):
    name: str
    type: str
    description: Optional[str]
    recommended_intake: Dict[str, float]
    deficiency_symptoms: List[str]
    source: Optional[str]
```

## Relationship Models

### Contains
Represents the relationship between food and nutrients.
```python
class ContainsRelationship(BaseRelationship):
    amount: float
    unit: str
    source: Optional[str]
    confidence: float
```

### Interacts
Represents interactions between nutrients.
```python
class InteractsRelationship(BaseRelationship):
    interaction_type: str
    effect: str
    source: Optional[str]
    strength: float
```

## Validation Models
See [Validators](validators/README.md) for details on validation rules and models.

## Graph Schema
See [Graph Schema](graph-schema.md) for the complete Neo4j graph schema.
