# Ticket 2.2: Define Graph Schema & Subnodes

## Priority
High

## Type
Database

## Status
To Do

## Description
Implement comprehensive graph schema and data model for the Vitalyst Knowledge Graph, including core node types, relationships, validation rules, and metadata tracking. The implementation must ensure data integrity, support versioning, and optimize query performance while following the blueprint specifications for hierarchical node modeling.

## Technical Details

1. Core Node Types and Properties
```cypher
// Base Node Type with Comprehensive Properties
CREATE CONSTRAINT IF NOT EXISTS FOR (n:BaseNode)
REQUIRE (n.id, n.version, n.created_at, n.updated_at, n.created_by) IS NODE KEY;

CREATE (n:BaseNode {
  id: string,                    // UUID v4
  version: string,               // Semantic version
  created_at: datetime(),        // Creation timestamp
  updated_at: datetime(),        // Last update timestamp
  created_by: string,            // User ID
  updated_by: string,            // User ID
  validation_status: string,     // enum: draft, pending_review, approved, rejected
  validation_history: [{         // Array of validation events
    status: string,
    timestamp: datetime(),
    validator: string,
    comments: string
  }],
  metadata: {                    // Extensible metadata
    source: string,
    confidence: float,
    last_verified: datetime(),
    verification_method: string
  }
});

// Food Node Type
CREATE (f:Food:BaseNode {
  name: string,                  // Required, unique
  scientific_name: string,       // Optional
  description: string,           // Required
  category: string,              // Required, enum
  subcategory: string,          // Optional
  seasonal_availability: [string], // Array of months
  storage_conditions: string,    // Required
  preparation_methods: [string], // Array of methods
  allergens: [string],          // Array of allergens
  dietary_flags: [string],      // Array of dietary flags
  regional_variants: [{         // Array of regional variants
    region: string,
    name: string,
    description: string
  }]
});

// Nutrient Node Type
CREATE (n:Nutrient:BaseNode {
  vitID: string,                // Required, unique
  name: string,                 // Required
  chemical_formula: string,     // Required
  molecular_weight: float,      // Required
  description: string,          // Required
  bioavailability: float,       // Required (0-1)
  recommended_intake: {         // Structured intake recommendations
    unit: string,
    daily_value: float,
    upper_limit: float,
    age_specific: [{
      age_range: string,
      value: float,
      gender: string
    }]
  },
  interactions: [{             // Array of interactions
    nutrient_id: string,
    effect: string,
    mechanism: string,
    evidence_level: string
  }]
});

// Content Node Type (Relationship Properties)
CREATE (c:Content {
  amount: float,               // Required
  unit: string,               // Required
  bioavailability: float,     // Optional (0-1)
  source_reliability: float,  // Required (0-1)
  measurement_method: string, // Required
  measurement_date: datetime(), // Required
  seasonal_variation: [{      // Optional seasonal variations
    season: string,
    adjustment_factor: float
  }]
});

// Environmental Metrics Node
CREATE (em:EnvironmentalMetrics:BaseNode {
  co2_footprint: {
    value: float,
    unit: string,
    calculation_method: string,
    uncertainty: float
  },
  water_usage: {
    value: float,
    unit: string,
    calculation_method: string,
    uncertainty: float
  },
  land_use: {
    value: float,
    unit: string,
    calculation_method: string,
    uncertainty: float
  },
  biodiversity_impact: {
    score: float,
    assessment_method: string,
    key_factors: [string]
  },
  transportation_impact: {
    average_distance: float,
    transport_method: string,
    co2_per_km: float
  }
});

// Source Node Type
CREATE (s:Source:BaseNode {
  url: string,                // Required, unique
  type: string,              // Required (publication, database, etc.)
  title: string,             // Required
  authors: [string],         // Required for publications
  publication_date: datetime(), // Required
  doi: string,               // Optional
  citation: string,          // Required
  reliability_score: float,  // Required (0-1)
  verification_status: string, // Required
  last_accessed: datetime(), // Required
  access_method: string,     // Required
  license: string           // Required
});
```

2. Relationship Types and Properties
```cypher
// Core Relationships with Properties
CREATE (f:Food)-[r:CONTAINS]->(c:Content)-[n:NUTRIENT_TYPE]->(nt:Nutrient)
WHERE r {
  relationship_type: 'direct',  // direct/derived
  confidence: float,           // 0-1
  verification_status: string,
  last_verified: datetime(),
  verification_method: string
};

CREATE (f:Food)-[r:HAS_METRICS]->(em:EnvironmentalMetrics)
WHERE r {
  calculation_date: datetime(),
  calculation_method: string,
  confidence: float,
  data_source: string
};

CREATE (n:Nutrient)-[r:INTERACTS_WITH]->(n2:Nutrient)
WHERE r {
  interaction_type: string,    // enhances/inhibits
  mechanism: string,
  evidence_level: string,
  source_id: string,
  confidence: float
};

CREATE (n:BaseNode)-[r:VERIFIED_BY]->(s:Source)
WHERE r {
  verification_date: datetime(),
  verification_method: string,
  confidence: float,
  verified_by: string
};
```

3. Indexes and Constraints
```cypher
// Node Uniqueness Constraints
CREATE CONSTRAINT IF NOT EXISTS FOR (f:Food) REQUIRE f.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Nutrient) REQUIRE n.vitID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (s:Source) REQUIRE s.url IS UNIQUE;

// Property Existence Constraints
CREATE CONSTRAINT IF NOT EXISTS FOR (n:BaseNode) REQUIRE n.validation_status IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (f:Food) REQUIRE f.category IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Nutrient) REQUIRE n.chemical_formula IS NOT NULL;

// Composite Indexes
CREATE INDEX food_category_name IF NOT EXISTS FOR (f:Food) ON (f.category, f.name);
CREATE INDEX nutrient_bioavailability IF NOT EXISTS FOR (n:Nutrient) ON (n.bioavailability);
CREATE INDEX content_reliability IF NOT EXISTS FOR (c:Content) ON (c.source_reliability);

// Full-text Indexes
CALL db.index.fulltext.createNodeIndex(
  'foodSearch',
  ['Food'],
  ['name', 'description', 'scientific_name']
);

CALL db.index.fulltext.createNodeIndex(
  'nutrientSearch',
  ['Nutrient'],
  ['name', 'description', 'chemical_formula']
);
```

4. Validation Rules
```cypher
// Property Value Validation
CREATE CONSTRAINT IF NOT EXISTS FOR (n:BaseNode)
ASSERT n.validation_status IN ['draft', 'pending_review', 'approved', 'rejected'];

CREATE CONSTRAINT IF NOT EXISTS FOR (f:Food)
ASSERT f.category IN ['vegetable', 'fruit', 'grain', 'protein', 'dairy', 'other'];

CREATE CONSTRAINT IF NOT EXISTS FOR (n:Nutrient)
ASSERT 0.0 <= n.bioavailability <= 1.0;

// Relationship Validation
CREATE CONSTRAINT IF NOT EXISTS FOR ()-[r:CONTAINS]->()
ASSERT r.confidence >= 0.0 AND r.confidence <= 1.0;

// Date Validation
CREATE CONSTRAINT IF NOT EXISTS FOR (n:BaseNode)
ASSERT n.created_at <= n.updated_at;
```

5. Query Optimization
```cypher
// Common Query Patterns
// Find foods by nutrient content
MATCH (f:Food)-[:CONTAINS]->(c:Content)-[:NUTRIENT_TYPE]->(n:Nutrient)
WHERE n.vitID = $vitID AND c.amount >= $minAmount
RETURN f
ORDER BY c.amount DESC;

// Find nutrient interactions
MATCH (n1:Nutrient)-[r:INTERACTS_WITH]->(n2:Nutrient)
WHERE n1.vitID = $vitID
RETURN n2, r.interaction_type, r.mechanism
ORDER BY r.evidence_level DESC;

// Find environmental impact
MATCH (f:Food)-[r:HAS_METRICS]->(em:EnvironmentalMetrics)
WHERE f.category = $category
RETURN f.name, em.co2_footprint.value, em.water_usage.value
ORDER BY em.co2_footprint.value DESC;
```

## Implementation Strategy
1. Schema Setup
   - Create base node types
   - Define relationships
   - Set up constraints
   - Create indexes

2. Data Validation
   - Implement validation rules
   - Set up property constraints
   - Configure relationship validation
   - Test data integrity

3. Query Optimization
   - Create composite indexes
   - Set up full-text search
   - Optimize common queries
   - Test performance

## Acceptance Criteria
- [ ] Base node structure implemented with all properties
- [ ] Relationship types defined with properties
- [ ] Constraints created and validated
- [ ] Indexes optimized for common queries
- [ ] Full-text search configured
- [ ] Validation rules implemented
- [ ] Query patterns optimized
- [ ] Documentation completed
- [ ] Performance benchmarks met
- [ ] Data integrity verified
- [ ] Migration strategy documented
- [ ] Test coverage complete

## Dependencies
- Ticket 2.1: Neo4j Deployment

## Estimated Hours
25

## Testing Requirements
- Schema Tests
  - Verify node creation
  - Test relationship creation
  - Validate constraints
  - Check property rules
- Performance Tests
  - Measure query performance
  - Test index effectiveness
  - Verify search performance
  - Benchmark common patterns
- Data Integrity Tests
  - Test validation rules
  - Verify relationship constraints
  - Check property constraints
  - Test update procedures
- Migration Tests
  - Test data migration
  - Verify schema updates
  - Check constraint violations
  - Validate index rebuilds

## Documentation
- Schema overview
- Data model documentation
- Query optimization guide
- Index strategy
- Validation rules
- Migration procedures
- Performance guidelines
- Best practices

## Search Space Optimization
- Clear node hierarchy
- Logical property organization
- Consistent relationship patterns
- Standardized validation rules
- Organized index structure

## References
- Blueprint Section 2: Architecture and Module Overview
- Blueprint Section 3: Data Model & Graph Structure
- Blueprint Section 5: Data Validation & Quality
- Neo4j Schema Design Best Practices
- Graph Data Modeling Guidelines

## Notes
- Implements comprehensive schema
- Ensures data integrity
- Optimizes query performance
- Supports versioning
- Maintains audit trail 