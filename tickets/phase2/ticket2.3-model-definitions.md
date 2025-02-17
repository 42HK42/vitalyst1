# Ticket 2.3: Create Model Definitions and JSON Schemas

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive TypeScript interfaces and JSON schemas for all node types, relationships, and validation rules in the Vitalyst Knowledge Graph. The implementation must ensure type safety, data validation, and schema consistency while following the blueprint specifications for data modeling and validation.

## Technical Details

1. Core Type Definitions
```typescript
// src/types/common.ts
export type UUID = string;
export type ISODateTime = string;
export type SemanticVersion = string;
export type ConfidenceScore = number; // 0.0 to 1.0

export enum ValidationStatus {
  DRAFT = 'draft',
  PENDING_REVIEW = 'pending_review',
  APPROVED = 'approved',
  REJECTED = 'rejected'
}

export enum FoodCategory {
  VEGETABLE = 'vegetable',
  FRUIT = 'fruit',
  GRAIN = 'grain',
  PROTEIN = 'protein',
  DAIRY = 'dairy',
  OTHER = 'other'
}

export interface ValidationEvent {
  status: ValidationStatus;
  timestamp: ISODateTime;
  validator: UUID;
  comments?: string;
}

export interface Metadata {
  source: string;
  confidence: ConfidenceScore;
  last_verified: ISODateTime;
  verification_method: string;
}

// src/types/nodes.ts
export interface BaseNode {
  id: UUID;
  version: SemanticVersion;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  created_by: UUID;
  updated_by: UUID;
  validation_status: ValidationStatus;
  validation_history: ValidationEvent[];
  metadata: Metadata;
}

export interface FoodNode extends BaseNode {
  name: string;
  scientific_name?: string;
  description: string;
  category: FoodCategory;
  subcategory?: string;
  seasonal_availability: string[];
  storage_conditions: string;
  preparation_methods: string[];
  allergens: string[];
  dietary_flags: string[];
  regional_variants: Array<{
    region: string;
    name: string;
    description: string;
  }>;
}

export interface NutrientNode extends BaseNode {
  vitID: string;
  name: string;
  chemical_formula: string;
  molecular_weight: number;
  description: string;
  bioavailability: ConfidenceScore;
  recommended_intake: {
    unit: string;
    daily_value: number;
    upper_limit: number;
    age_specific: Array<{
      age_range: string;
      value: number;
      gender: 'male' | 'female' | 'all';
    }>;
  };
  interactions: Array<{
    nutrient_id: UUID;
    effect: 'enhances' | 'inhibits';
    mechanism: string;
    evidence_level: 'high' | 'medium' | 'low';
  }>;
}

export interface ContentNode extends BaseNode {
  amount: number;
  unit: string;
  bioavailability?: ConfidenceScore;
  source_reliability: ConfidenceScore;
  measurement_method: string;
  measurement_date: ISODateTime;
  seasonal_variation?: Array<{
    season: string;
    adjustment_factor: number;
  }>;
}

export interface EnvironmentalMetricsNode extends BaseNode {
  co2_footprint: {
    value: number;
    unit: string;
    calculation_method: string;
    uncertainty: number;
  };
  water_usage: {
    value: number;
    unit: string;
    calculation_method: string;
    uncertainty: number;
  };
  land_use: {
    value: number;
    unit: string;
    calculation_method: string;
    uncertainty: number;
  };
  biodiversity_impact: {
    score: number;
    assessment_method: string;
    key_factors: string[];
  };
  transportation_impact: {
    average_distance: number;
    transport_method: string;
    co2_per_km: number;
  };
}

export interface SourceNode extends BaseNode {
  url: string;
  type: 'publication' | 'database' | 'expert' | 'other';
  title: string;
  authors: string[];
  publication_date: ISODateTime;
  doi?: string;
  citation: string;
  reliability_score: ConfidenceScore;
  verification_status: ValidationStatus;
  last_accessed: ISODateTime;
  access_method: string;
  license: string;
}

// src/types/relationships.ts
export interface BaseRelationship {
  id: UUID;
  created_at: ISODateTime;
  updated_at: ISODateTime;
  created_by: UUID;
}

export interface ContainsRelationship extends BaseRelationship {
  relationship_type: 'direct' | 'derived';
  confidence: ConfidenceScore;
  verification_status: ValidationStatus;
  last_verified: ISODateTime;
  verification_method: string;
}

export interface HasMetricsRelationship extends BaseRelationship {
  calculation_date: ISODateTime;
  calculation_method: string;
  confidence: ConfidenceScore;
  data_source: string;
}

export interface InteractsWithRelationship extends BaseRelationship {
  interaction_type: 'enhances' | 'inhibits';
  mechanism: string;
  evidence_level: 'high' | 'medium' | 'low';
  source_id: UUID;
  confidence: ConfidenceScore;
}

export interface VerifiedByRelationship extends BaseRelationship {
  verification_date: ISODateTime;
  verification_method: string;
  confidence: ConfidenceScore;
  verified_by: UUID;
}
```

2. JSON Schema Definitions
```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "definitions": {
    "UUID": {
      "type": "string",
      "pattern": "^[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$"
    },
    "ISODateTime": {
      "type": "string",
      "format": "date-time"
    },
    "SemanticVersion": {
      "type": "string",
      "pattern": "^(0|[1-9]\\d*)\\.(0|[1-9]\\d*)\\.(0|[1-9]\\d*)(?:-((?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*)(?:\\.(?:0|[1-9]\\d*|\\d*[a-zA-Z-][0-9a-zA-Z-]*))*))?(?:\\+([0-9a-zA-Z-]+(?:\\.[0-9a-zA-Z-]+)*))?$"
    },
    "ConfidenceScore": {
      "type": "number",
      "minimum": 0.0,
      "maximum": 1.0
    },
    "ValidationStatus": {
      "type": "string",
      "enum": ["draft", "pending_review", "approved", "rejected"]
    },
    "ValidationEvent": {
      "type": "object",
      "required": ["status", "timestamp", "validator"],
      "properties": {
        "status": { "$ref": "#/definitions/ValidationStatus" },
        "timestamp": { "$ref": "#/definitions/ISODateTime" },
        "validator": { "$ref": "#/definitions/UUID" },
        "comments": { "type": "string" }
      }
    },
    "Metadata": {
      "type": "object",
      "required": ["source", "confidence", "last_verified", "verification_method"],
      "properties": {
        "source": { "type": "string" },
        "confidence": { "$ref": "#/definitions/ConfidenceScore" },
        "last_verified": { "$ref": "#/definitions/ISODateTime" },
        "verification_method": { "type": "string" }
      }
    },
    "BaseNode": {
      "type": "object",
      "required": [
        "id",
        "version",
        "created_at",
        "updated_at",
        "created_by",
        "updated_by",
        "validation_status",
        "validation_history",
        "metadata"
      ],
      "properties": {
        "id": { "$ref": "#/definitions/UUID" },
        "version": { "$ref": "#/definitions/SemanticVersion" },
        "created_at": { "$ref": "#/definitions/ISODateTime" },
        "updated_at": { "$ref": "#/definitions/ISODateTime" },
        "created_by": { "$ref": "#/definitions/UUID" },
        "updated_by": { "$ref": "#/definitions/UUID" },
        "validation_status": { "$ref": "#/definitions/ValidationStatus" },
        "validation_history": {
          "type": "array",
          "items": { "$ref": "#/definitions/ValidationEvent" }
        },
        "metadata": { "$ref": "#/definitions/Metadata" }
      }
    }
  }
}
```

3. Type Guards and Validation
```typescript
// src/utils/typeGuards.ts
import { BaseNode, FoodNode, NutrientNode } from '../types/nodes';

export function isBaseNode(node: any): node is BaseNode {
  return (
    typeof node === 'object' &&
    typeof node.id === 'string' &&
    typeof node.version === 'string' &&
    typeof node.created_at === 'string' &&
    typeof node.updated_at === 'string' &&
    typeof node.created_by === 'string' &&
    typeof node.updated_by === 'string' &&
    typeof node.validation_status === 'string' &&
    Array.isArray(node.validation_history) &&
    typeof node.metadata === 'object'
  );
}

export function isFoodNode(node: any): node is FoodNode {
  return (
    isBaseNode(node) &&
    typeof node.name === 'string' &&
    typeof node.description === 'string' &&
    typeof node.category === 'string' &&
    Array.isArray(node.seasonal_availability) &&
    typeof node.storage_conditions === 'string' &&
    Array.isArray(node.preparation_methods) &&
    Array.isArray(node.allergens) &&
    Array.isArray(node.dietary_flags) &&
    Array.isArray(node.regional_variants)
  );
}

// Additional type guards for other node types...
```

4. Schema Validation Utilities
```typescript
// src/utils/schemaValidation.ts
import Ajv from 'ajv';
import addFormats from 'ajv-formats';
import { schemas } from '../schemas';

const ajv = new Ajv({ allErrors: true });
addFormats(ajv);

export function validateNode(node: any, type: string): boolean {
  const validate = ajv.compile(schemas[type]);
  return validate(node);
}

export function getValidationErrors(node: any, type: string): string[] {
  const validate = ajv.compile(schemas[type]);
  if (!validate(node)) {
    return validate.errors?.map(error => error.message) ?? [];
  }
  return [];
}
```

## Implementation Strategy
1. Type Definition Setup
   - Create base types
   - Define node interfaces
   - Implement relationship types
   - Set up validation types

2. Schema Implementation
   - Create JSON schemas
   - Define validation rules
   - Set up type guards
   - Implement utilities

3. Validation Setup
   - Implement type guards
   - Create validation utilities
   - Set up error handling
   - Test validation rules

## Acceptance Criteria
- [ ] All node types defined with TypeScript interfaces
- [ ] All relationship types defined with interfaces
- [ ] Comprehensive JSON schemas created
- [ ] Type guards implemented for all types
- [ ] Validation utilities created
- [ ] Schema documentation generated
- [ ] Migration utilities implemented
- [ ] Test coverage complete
- [ ] Performance benchmarks met
- [ ] Integration tests passing
- [ ] Documentation completed
- [ ] Error handling implemented

## Dependencies
- Ticket 2.1: Neo4j Deployment
- Ticket 2.2: Graph Schema

## Estimated Hours
20

## Testing Requirements
- Type Tests
  - Test interface definitions
  - Verify type guards
  - Validate schema types
  - Check type inference
- Schema Tests
  - Test JSON schemas
  - Verify validation rules
  - Check error messages
  - Test schema updates
- Integration Tests
  - Test with database
  - Verify data conversion
  - Check error handling
  - Test migrations
- Performance Tests
  - Measure validation speed
  - Test type checking
  - Verify memory usage
  - Benchmark operations

## Documentation
- Type system overview
- Schema documentation
- Validation patterns
- Migration guides
- Error handling
- Best practices
- Performance guidelines
- Integration examples

## Search Space Optimization
- Clear type hierarchy
- Logical schema organization
- Consistent naming patterns
- Standardized validation rules
- Organized utility functions

## References
- Blueprint Section 2: Architecture and Module Overview
- Blueprint Section 3: Data Model & Graph Structure
- Blueprint Section 4: JSON Schema Definitions
- Blueprint Section 5: Data Validation & Quality
- TypeScript Documentation
- JSON Schema Specifications

## Notes
- Implements comprehensive types
- Ensures type safety
- Optimizes validation
- Supports migrations
- Maintains consistency 