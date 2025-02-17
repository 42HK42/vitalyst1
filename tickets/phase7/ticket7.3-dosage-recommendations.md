# Ticket 7.3: Dosage Recommendation System

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive dosage recommendation system for the Vitalyst Knowledge Graph that incorporates WHO, EU-NRV, and DGE standards, provides age-specific dosage calculations, and handles special population group recommendations. The system must maintain accurate and up-to-date dosage information while supporting multiple recommendation sources, real-time updates, and detailed visualization capabilities as specified in the blueprint.

## Technical Details
1. Dosage Recommendation Service Implementation
```typescript
// src/services/dosage/recommendation.ts
import { 
  GraphService,
  ValidationService,
  CacheManager,
  MetricsCollector,
  Logger
} from '../services';
import {
  RecommendationResult,
  AgeGroup,
  SpecialGroup,
  RecommendationSource,
  DosageUnit,
  ValidationMetrics
} from '../types';
import { DateTime } from 'luxon';
import { Observable, Subject } from 'rxjs';
import { Redis } from 'ioredis';

export class DosageRecommendationService {
  private readonly cache: Redis;
  private readonly metrics: MetricsCollector;
  private readonly logger: Logger;
  private readonly updateSubject = new Subject<RecommendationUpdate>();

  constructor(
    private readonly graphService: GraphService,
    private readonly validator: ValidationService,
    config: RecommendationConfig
  ) {
    this.cache = new Redis(config.redis);
    this.metrics = new MetricsCollector('recommendations');
    this.logger = new Logger('recommendations');
  }

  get updates$(): Observable<RecommendationUpdate> {
    return this.updateSubject.asObservable();
  }

  async getRecommendation(params: {
    nutrientId: string;
    age: number;
    gender: 'male' | 'female';
    specialGroups?: SpecialGroup[];
    medicalConditions?: string[];
    source?: RecommendationSource;
    includeHistory?: boolean;
  }): Promise<RecommendationResult> {
    const operationId = `rec_${params.nutrientId}_${DateTime.now().toISO()}`;
    this.metrics.startOperation(operationId);

    try {
      // Check cache first
      const cached = await this.checkCache(params);
      if (cached) {
        return cached;
      }

      // Get base recommendation
      const baseRecommendation = await this.getBaseRecommendation(params);

      // Apply special group modifiers
      const modifiedRecommendation = await this.applyModifiers(
        baseRecommendation,
        params
      );

      // Add historical data if requested
      if (params.includeHistory) {
        modifiedRecommendation.history = await this.getRecommendationHistory(
          params.nutrientId
        );
      }

      // Cache result
      await this.cacheRecommendation(params, modifiedRecommendation);

      // Track metrics
      this.metrics.recordRecommendation(operationId, modifiedRecommendation);

      return modifiedRecommendation;

    } catch (error) {
      this.metrics.recordError(operationId, error);
      this.logger.error('Recommendation generation failed', {
        params,
        error: error.message
      });
      throw error;
    }
  }

  private async getBaseRecommendation(
    params: RecommendationParams
  ): Promise<BaseRecommendation> {
    const source = params.source || RecommendationSource.WHO;
    const ageGroup = this.getAgeGroup(params.age);

    // Get recommendation from graph database
    const recommendation = await this.graphService.getNutrientRecommendation({
      nutrientId: params.nutrientId,
      ageGroup: ageGroup.description,
      gender: params.gender,
      source: source
    });

    if (!recommendation) {
      throw new Error(
        `No recommendation found for nutrient ${params.nutrientId} ` +
        `in age group ${ageGroup.description}`
      );
    }

    return {
      value: recommendation.value,
      unit: recommendation.unit,
      source: source,
      confidence: recommendation.confidence,
      references: recommendation.references,
      lastUpdated: recommendation.lastUpdated
    };
  }

  private async applyModifiers(
    base: BaseRecommendation,
    params: RecommendationParams
  ): Promise<ModifiedRecommendation> {
    let modified = { ...base };
    const appliedModifiers: RecommendationModifier[] = [];

    // Apply special group modifiers
    if (params.specialGroups) {
      for (const group of params.specialGroups) {
        const modifier = await this.getSpecialGroupModifier(
          group,
          params.nutrientId
        );
        modified.value *= modifier.value;
        appliedModifiers.push(modifier);
      }
    }

    // Apply medical condition modifiers
    if (params.medicalConditions) {
      for (const condition of params.medicalConditions) {
        const modifier = await this.getMedicalConditionModifier(
          condition,
          params.nutrientId
        );
        modified.value *= modifier.value;
        appliedModifiers.push(modifier);
      }
    }

    return {
      ...modified,
      appliedModifiers,
      calculatedAt: DateTime.now().toISO()
    };
  }

  private async getSpecialGroupModifier(
    group: SpecialGroup,
    nutrientId: string
  ): Promise<RecommendationModifier> {
    switch (group) {
      case SpecialGroup.PREGNANCY:
        return this.getPregnancyModifier(nutrientId);
      case SpecialGroup.LACTATION:
        return this.getLactationModifier(nutrientId);
      case SpecialGroup.ATHLETES:
        return this.getAthleteModifier(nutrientId);
      default:
        return this.getDefaultModifier(group, nutrientId);
    }
  }

  private async getPregnancyModifier(
    nutrientId: string
  ): Promise<RecommendationModifier> {
    // Get detailed pregnancy stage modifiers
    const modifiers = {
      trimester_1: { value: 1.2, confidence: 0.9 },
      trimester_2: { value: 1.3, confidence: 0.9 },
      trimester_3: { value: 1.5, confidence: 0.9 }
    };

    return {
      type: 'pregnancy',
      value: modifiers.trimester_2.value, // Default to second trimester
      confidence: modifiers.trimester_2.confidence,
      details: modifiers
    };
  }

  private async getAthleteModifier(
    nutrientId: string
  ): Promise<RecommendationModifier> {
    // Get detailed athlete category modifiers
    const modifiers = {
      high_intensity: { value: 1.8, confidence: 0.85 },
      moderate_intensity: { value: 1.4, confidence: 0.9 },
      endurance: { value: 1.6, confidence: 0.85 }
    };

    return {
      type: 'athlete',
      value: modifiers.moderate_intensity.value, // Default to moderate
      confidence: modifiers.moderate_intensity.confidence,
      details: modifiers
    };
  }
}

2. Recommendation Data Models
```typescript
// src/types/recommendations.ts
export enum RecommendationSource {
  WHO = 'who',
  EU_NRV = 'eu_nrv',
  DGE = 'dge'
}

export enum SpecialGroup {
  PREGNANCY = 'pregnancy',
  LACTATION = 'lactation',
  ATHLETES = 'athletes',
  ELDERLY = 'elderly',
  CHILDREN = 'children'
}

export interface AgeGroup {
  minAge: number;
  maxAge?: number;
  gender?: 'male' | 'female';
  description: string;
}

export interface BaseRecommendation {
  value: number;
  unit: DosageUnit;
  source: RecommendationSource;
  confidence: number;
  references: string[];
  lastUpdated: string;
}

export interface ModifiedRecommendation extends BaseRecommendation {
  appliedModifiers: RecommendationModifier[];
  calculatedAt: string;
  history?: RecommendationHistory[];
}

export interface RecommendationModifier {
  type: string;
  value: number;
  confidence: number;
  details?: Record<string, any>;
}

export interface RecommendationHistory {
  timestamp: string;
  value: number;
  source: RecommendationSource;
  reason?: string;
}
```

3. Recommendation Visualization Service
```typescript
// src/services/dosage/visualization.ts
import { ChartGenerator } from '../utils/charts';
import { 
  RecommendationResult,
  VisualizationType,
  ChartOptions
} from '../types';

export class RecommendationVisualizationService {
  constructor(
    private readonly chartGenerator: ChartGenerator
  ) {}

  async generateVisualizations(
    recommendation: RecommendationResult,
    options: ChartOptions = {}
  ): Promise<RecommendationVisuals> {
    return {
      dosageChart: await this.generateDosageChart(recommendation, options),
      comparisonChart: await this.generateComparisonChart(recommendation, options),
      historyChart: await this.generateHistoryChart(recommendation, options),
      modifierImpactChart: await this.generateModifierImpactChart(recommendation, options)
    };
  }

  private async generateDosageChart(
    recommendation: RecommendationResult,
    options: ChartOptions
  ): Promise<ChartData> {
    // Generate dosage visualization with confidence intervals
    return this.chartGenerator.createDosageChart(recommendation, options);
  }

  private async generateComparisonChart(
    recommendation: RecommendationResult,
    options: ChartOptions
  ): Promise<ChartData> {
    // Generate comparison across different sources (WHO, EU-NRV, DGE)
    return this.chartGenerator.createComparisonChart(recommendation, options);
  }
}
```

## Implementation Strategy
1. Core Recommendation System
   - Implement recommendation service
   - Set up source integration
   - Configure caching system
   - Implement monitoring

2. Special Population Support
   - Create pregnancy stage modifiers
   - Implement athlete categories
   - Add medical condition adjustments
   - Configure age-specific calculations

3. Visualization System
   - Implement recommendation charts
   - Create comparison tools
   - Set up historical tracking
   - Add interactive visualizations

4. Performance Optimization
   - Implement caching
   - Set up batch processing
   - Configure memory management
   - Optimize calculations

## Acceptance Criteria
- [ ] WHO, EU-NRV, and DGE recommendation integration with versioning
- [ ] Age-specific dosage calculations with confidence intervals
- [ ] Comprehensive special population group support
- [ ] Medical condition adjustments
- [ ] Multiple source handling with priority system
- [ ] Real-time recommendation updates
- [ ] Caching system implementation
- [ ] Visualization support with comparisons
- [ ] Historical tracking and versioning
- [ ] Performance optimization
- [ ] Comprehensive documentation
- [ ] Unit conversion support
- [ ] Validation and verification system
- [ ] Alert system for updates

## Dependencies
- Ticket 7.1: CSV Import Scripts
- Ticket 7.2: Data Verification
- Ticket 2.7: CSV-Specific Models
- Ticket 3.3: Zero-Trust Security

## Estimated Hours
35

## Testing Requirements
- Unit Tests:
  - Test dosage calculations
  - Verify age group logic
  - Test special group modifiers
  - Validate unit conversions
  - Test caching system
  - Verify visualization generation
  - Test update handling
  - Validate source integration

- Integration Tests:
  - Test recommendation updates
  - Verify source integration
  - Test data consistency
  - Validate visualization system
  - Test caching integration
  - Verify real-time updates
  - Test alert system
  - Validate metrics collection

- Performance Tests:
  - Test calculation speed
  - Measure cache efficiency
  - Verify memory usage
  - Test concurrent requests
  - Validate batch processing
  - Test visualization generation
  - Verify scalability

- Source Tests:
  - Test WHO guidelines integration
  - Verify EU-NRV standards
  - Test DGE recommendations
  - Validate source updates
  - Test version handling
  - Verify priority system
  - Test source conflicts
  - Validate data consistency

## Documentation
- Recommendation system overview
- Source integration guide
- Calculation methodology
- Special group handling
- Medical condition adjustments
- Update procedures
- Validation rules
- Caching strategy
- Visualization guide
- Performance optimization
- Error handling procedures
- API documentation
- Monitoring setup
- Troubleshooting guide

## Search Space Optimization
- Clear service hierarchy
  - Recommendation service
  - Visualization service
  - Cache manager
  - Metrics collector
  - Update manager

- Consistent naming patterns
  - get* for retrievals
  - calculate* for computations
  - apply* for modifications
  - generate* for creation
  - validate* for validation

- Standardized interfaces
  - RecommendationResult
  - ModificationResult
  - VisualizationData
  - ValidationMetrics

- Logical file organization
  - services/
    - dosage/
      - recommendation/
      - visualization/
      - modifiers/
      - sources/
  - types/
  - utils/
  - monitoring/

- Well-documented utilities
  - Calculation helpers
  - Unit conversions
  - Visualization tools
  - Validation utilities

- Organized test structure
  - unit/
    - recommendation/
    - visualization/
    - modifiers/
    - sources/
  - integration/
  - performance/
  - e2e/

## References
- **Phasedplan.md:** Phase 7, Ticket 7.3
- **Blueprint.md:** Sections on Dosage Recommendations
- WHO Nutrient Guidelines
- EU-NRV Documentation
- DGE Standards
- Performance Optimization Guidelines
- Visualization Best Practices
- Caching Strategies

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the dosage recommendation system as specified in the blueprint, with particular attention to:
- Comprehensive recommendation system
- Enhanced source integration
- Special population support
- Medical condition handling
- Real-time updates
- Performance optimization
- Visualization support
- Error handling
- Security measures
- Documentation standards
``` 