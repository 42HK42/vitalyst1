# Ticket 8.6: Implement Source Reliability System

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement a comprehensive source reliability system for the Vitalyst Knowledge Graph that tracks, validates, and scores the reliability of all data sources. This system will handle both initial data sources (@Tab_Vit_C_v7.csv, @Nahrungsmittel_Database2_real.csv) and dynamically added sources, including AI-generated content. The implementation must follow the hierarchical node modeling approach specified in the blueprint and maintain detailed source tracking for all data attributes.

## Technical Details

1. Source Reliability Model Implementation
```typescript
// src/models/sourceReliability.ts
import { BaseNode } from './baseNode';
import { ValidationStatus } from '../types';

interface SourceMetadata {
  url?: string;
  accessDate?: Date;
  version?: string;
  publisher?: string;
  lastVerified?: Date;
  verificationMethod?: string;
  aiGenerated: boolean;
  aiModel?: string;
}

interface ReliabilityMetrics {
  accuracyScore: number;     // 0-1 score based on validation history
  consistencyScore: number;  // 0-1 score based on data consistency checks
  freshnessScore: number;    // 0-1 score based on data age
  verificationScore: number; // 0-1 score based on verification status
  overallScore: number;      // Weighted average of all scores
}

export class SourceReliability extends BaseNode {
  sourceId: string;
  sourceType: 'csv' | 'api' | 'manual' | 'ai' | 'scientific_paper';
  metadata: SourceMetadata;
  metrics: ReliabilityMetrics;
  validationHistory: Array<{
    timestamp: Date;
    validator: string;
    status: ValidationStatus;
    notes: string;
  }>;
  
  constructor(data: Partial<SourceReliability>) {
    super();
    Object.assign(this, data);
    this.calculateScores();
  }

  private calculateScores(): void {
    // Calculate individual scores
    this.metrics.accuracyScore = this.calculateAccuracyScore();
    this.metrics.consistencyScore = this.calculateConsistencyScore();
    this.metrics.freshnessScore = this.calculateFreshnessScore();
    this.metrics.verificationScore = this.calculateVerificationScore();
    
    // Calculate weighted overall score
    this.metrics.overallScore = this.calculateOverallScore();
  }

  private calculateOverallScore(): number {
    const weights = {
      accuracy: 0.4,
      consistency: 0.2,
      freshness: 0.2,
      verification: 0.2
    };

    return (
      this.metrics.accuracyScore * weights.accuracy +
      this.metrics.consistencyScore * weights.consistency +
      this.metrics.freshnessScore * weights.freshness +
      this.metrics.verificationScore * weights.verification
    );
  }
}
```

2. Source Validation Service
```typescript
// src/services/sourceValidation.ts
import { Neo4jService } from '../services/neo4j';
import { SourceReliability } from '../models/sourceReliability';
import { ValidationResult } from '../types';

export class SourceValidationService {
  private neo4j: Neo4jService;
  
  constructor(neo4j: Neo4jService) {
    this.neo4j = neo4j;
  }

  async validateSource(sourceId: string): Promise<ValidationResult> {
    const source = await this.getSourceDetails(sourceId);
    const validationResults = await Promise.all([
      this.validateDataConsistency(source),
      this.validateDataFreshness(source),
      this.validateSourceMetadata(source),
      this.validateCrossReferences(source)
    ]);

    return this.aggregateValidationResults(validationResults);
  }

  async validateDataConsistency(source: SourceReliability): Promise<ValidationResult> {
    const query = `
      MATCH (n)-[:HAS_SOURCE]->(s:Source {id: $sourceId})
      WITH n, s
      MATCH (n)-[:HAS_ATTRIBUTE]->(a)
      RETURN n, collect(a) as attributes
    `;

    const result = await this.neo4j.run(query, { sourceId: source.sourceId });
    return this.checkConsistencyPatterns(result);
  }

  private async validateCrossReferences(source: SourceReliability): Promise<ValidationResult> {
    // Validate against other trusted sources
    const query = `
      MATCH (n1)-[:HAS_SOURCE]->(s1:Source {id: $sourceId})
      MATCH (n2)-[:HAS_SOURCE]->(s2:Source)
      WHERE s2.reliability_score > 0.8
      AND n1.type = n2.type
      RETURN n1, n2, abs(n1.value - n2.value) as difference
    `;

    const results = await this.neo4j.run(query, { sourceId: source.sourceId });
    return this.analyzeCrossReferenceResults(results);
  }
}
```

3. Source Tracking Implementation
```typescript
// src/services/sourceTracking.ts
import { Neo4jService } from '../services/neo4j';
import { SourceReliability } from '../models/sourceReliability';

export class SourceTrackingService {
  private neo4j: Neo4jService;

  constructor(neo4j: Neo4jService) {
    this.neo4j = neo4j;
  }

  async trackAttributeSource(
    nodeId: string,
    attributePath: string,
    source: SourceReliability
  ): Promise<void> {
    const query = `
      MATCH (n {id: $nodeId})
      MERGE (s:Source {id: $sourceId})
      SET s += $sourceProperties
      MERGE (n)-[:HAS_SOURCE {
        attribute: $attributePath,
        timestamp: datetime(),
        confidence: $confidence
      }]->(s)
    `;

    await this.neo4j.run(query, {
      nodeId,
      sourceId: source.sourceId,
      sourceProperties: this.formatSourceProperties(source),
      attributePath,
      confidence: source.metrics.overallScore
    });
  }

  async getAttributeLineage(
    nodeId: string,
    attributePath: string
  ): Promise<Array<SourceReliability>> {
    const query = `
      MATCH (n {id: $nodeId})-[r:HAS_SOURCE]->(s:Source)
      WHERE r.attribute = $attributePath
      RETURN s, r
      ORDER BY r.timestamp DESC
    `;

    const result = await this.neo4j.run(query, {
      nodeId,
      attributePath
    });

    return result.records.map(record => 
      new SourceReliability(record.get('s').properties)
    );
  }
}
```

4. AI Source Reliability Handler
```typescript
// src/services/aiSourceReliability.ts
import { SourceReliability } from '../models/sourceReliability';
import { AIModel } from '../types';

export class AISourceReliabilityHandler {
  async evaluateAISource(
    content: any,
    model: AIModel,
    prompt: string
  ): Promise<SourceReliability> {
    const metadata = {
      aiGenerated: true,
      aiModel: model.name,
      version: model.version,
      accessDate: new Date(),
      verificationMethod: 'ai_confidence_scoring'
    };

    const metrics = await this.calculateAIReliabilityMetrics(
      content,
      model,
      prompt
    );

    return new SourceReliability({
      sourceType: 'ai',
      metadata,
      metrics
    });
  }

  private async calculateAIReliabilityMetrics(
    content: any,
    model: AIModel,
    prompt: string
  ): Promise<ReliabilityMetrics> {
    // Calculate AI-specific reliability metrics
    const baseConfidence = model.getConfidenceScore(content);
    const promptQuality = this.evaluatePromptQuality(prompt);
    const modelReliability = this.getModelReliabilityScore(model);

    return {
      accuracyScore: baseConfidence * modelReliability,
      consistencyScore: this.evaluateContentConsistency(content),
      freshnessScore: 1.0, // AI-generated content is always fresh
      verificationScore: promptQuality * modelReliability,
      overallScore: 0 // Will be calculated by SourceReliability class
    };
  }
}
```

5. Source Reliability Dashboard Components
```typescript
// src/components/SourceReliabilityDashboard.tsx
import React from 'react';
import { SourceReliability } from '../models/sourceReliability';
import { ReliabilityChart } from './ReliabilityChart';
import { SourceLineage } from './SourceLineage';

interface Props {
  nodeId: string;
  attributePath: string;
}

export const SourceReliabilityDashboard: React.FC<Props> = ({
  nodeId,
  attributePath
}) => {
  const [sourceHistory, setSourceHistory] = useState<SourceReliability[]>([]);
  const [selectedSource, setSelectedSource] = useState<SourceReliability | null>(null);

  useEffect(() => {
    loadSourceHistory();
  }, [nodeId, attributePath]);

  return (
    <div className="source-reliability-dashboard">
      <ReliabilityChart
        sources={sourceHistory}
        onSourceSelect={setSelectedSource}
      />
      {selectedSource && (
        <SourceLineage
          source={selectedSource}
          attributePath={attributePath}
        />
      )}
      <SourceMetricsPanel source={selectedSource} />
      <ValidationHistoryTimeline source={selectedSource} />
    </div>
  );
};
```

6. Source Reliability Metrics Calculation
```typescript
// src/services/metrics/reliabilityCalculator.ts
export class ReliabilityCalculator {
  calculateSourceMetrics(source: SourceReliability): ReliabilityMetrics {
    return {
      accuracyScore: this.calculateAccuracyScore(source),
      consistencyScore: this.calculateConsistencyScore(source),
      freshnessScore: this.calculateFreshnessScore(source),
      verificationScore: this.calculateVerificationScore(source),
      authorityScore: this.calculateAuthorityScore(source),
      crossReferenceScore: this.calculateCrossReferenceScore(source),
      overallScore: 0 // Calculated after individual scores
    };
  }

  private calculateAuthorityScore(source: SourceReliability): number {
    const factors = {
      domainAuthority: this.getDomainAuthority(source),
      contentType: this.getContentTypeScore(source),
      authorityIndicators: this.getAuthorityIndicators(source)
    };
    return Object.values(factors).reduce((acc, val) => acc * val, 1);
  }

  private calculateCrossReferenceScore(source: SourceReliability): number {
    return this.analyzeReferencedSources(source.metadata.references || []);
  }
}
```

7. Historical Data Tracking
```typescript
// src/services/history/sourceHistoryTracker.ts
export class SourceHistoryTracker {
  async trackSourceChange(
    sourceId: string,
    change: {
      type: 'update' | 'validation' | 'enrichment',
      data: any,
      user: string
    }
  ): Promise<void> {
    const historyEntry = {
      timestamp: new Date(),
      sourceId,
      changeType: change.type,
      userData: change.user,
      previousState: await this.getCurrentState(sourceId),
      newState: change.data
    };

    await this.neo4j.run(`
      MATCH (s:Source {id: $sourceId})
      CREATE (h:HistoryEntry $historyData)
      CREATE (s)-[:HAS_HISTORY]->(h)
    `, {
      sourceId,
      historyData: historyEntry
    });
  }

  async getSourceHistory(sourceId: string): Promise<Array<HistoryEntry>> {
    const result = await this.neo4j.run(`
      MATCH (s:Source {id: $sourceId})-[:HAS_HISTORY]->(h:HistoryEntry)
      RETURN h
      ORDER BY h.timestamp DESC
    `, { sourceId });

    return result.records.map(record => record.get('h').properties);
  }
}
```

8. Automated Validation Scheduler
```typescript
// src/services/scheduler/validationScheduler.ts
export class ValidationScheduler {
  constructor(
    private sourceValidation: SourceValidationService,
    private notificationService: NotificationService
  ) {}

  async scheduleValidation(source: SourceReliability): Promise<void> {
    const schedule = this.calculateValidationSchedule(source);
    
    await this.scheduler.schedule({
      sourceId: source.sourceId,
      nextValidation: schedule.nextValidation,
      frequency: schedule.frequency,
      callback: async () => {
        const result = await this.sourceValidation.validateSource(source.sourceId);
        if (result.status === 'failed') {
          await this.notificationService.notifyValidationFailure(source, result);
        }
      }
    });
  }

  private calculateValidationSchedule(source: SourceReliability): ValidationSchedule {
    const baseFrequency = this.getBaseFrequency(source.sourceType);
    const riskFactor = this.calculateRiskFactor(source);
    
    return {
      nextValidation: this.calculateNextValidation(baseFrequency, riskFactor),
      frequency: this.adjustFrequency(baseFrequency, riskFactor)
    };
  }
}
```

## Search Space Organization
```
src/
├── models/
│   ├── source/
│   │   ├── reliability.ts
│   │   ├── metadata.ts
│   │   └── validation.ts
│   └── metrics/
│       ├── reliability.ts
│       └── calculation.ts
├── services/
│   ├── validation/
│   │   ├── sourceValidation.ts
│   │   └── crossReference.ts
│   ├── tracking/
│   │   ├── sourceTracking.ts
│   │   └── historyTracking.ts
│   ├── metrics/
│   │   ├── reliabilityCalculator.ts
│   │   └── metricsCollector.ts
│   └── scheduler/
│       ├── validationScheduler.ts
│       └── notificationService.ts
├── components/
│   └── reliability/
│       ├── dashboard/
│       ├── charts/
│       └── history/
└── utils/
    ├── validation/
    ├── metrics/
    └── scheduling/
```

## Additional Implementation Notes
1. Implement comprehensive validation rules for each source type
2. Set up automated cross-reference validation with trusted sources
3. Configure real-time monitoring and alerting for reliability issues
4. Implement caching strategy for frequently accessed reliability metrics
5. Set up batch processing for large-scale source validation
6. Configure automated backup of source validation history
7. Implement performance optimization for reliability calculations
8. Set up comprehensive logging and audit trails
9. Configure automated testing for all reliability components
10. Implement fallback strategies for validation failures

## Enhanced Dependencies
- Neo4j database with vector search capabilities
- Frontend visualization libraries (D3.js, Chart.js)
- AI model integration for content validation
- Monitoring system (Prometheus + Grafana)
- Caching system (Redis)
- Message queue for async processing
- Notification service
- Scheduler service

## Extended Acceptance Criteria
1. All data attributes have tracked sources with complete lineage
2. Source reliability scores are automatically calculated and updated
3. Source validation history is maintained with full audit trails
4. AI-generated content is properly tracked and scored with confidence metrics
5. Source reliability dashboard provides comprehensive insights
6. Cross-reference validation is implemented with trusted source matching
7. Source lineage is traceable for all attributes with complete history
8. Automated validation scheduling is operational
9. Real-time monitoring and alerting is functional
10. Performance benchmarks are met for all operations
11. Comprehensive test coverage is achieved
12. Documentation is complete and up-to-date

## Testing Strategy
1. Unit Tests
   - Test reliability calculations
   - Verify validation rules
   - Test history tracking
   - Validate scheduling logic

2. Integration Tests
   - Test source validation workflow
   - Verify cross-reference validation
   - Test notification system
   - Validate history tracking

3. Performance Tests
   - Test concurrent validations
   - Measure calculation speed
   - Verify caching effectiveness
   - Test batch processing

4. End-to-End Tests
   - Test complete validation workflow
   - Verify dashboard functionality
   - Test notification delivery
   - Validate scheduler operation

## Documentation Requirements
1. Source Reliability System Overview
2. Validation Rules Documentation
3. Metrics Calculation Guide
4. History Tracking Specification
5. Scheduler Configuration Guide
6. Performance Optimization Tips
7. Troubleshooting Procedures
8. API Documentation
9. Dashboard User Guide
10. Maintenance Procedures

## Dependencies
- Neo4j database with vector search capabilities
- Frontend visualization libraries
- AI model integration
- Monitoring and alerting system

## Acceptance Criteria
1. All data attributes have tracked sources
2. Source reliability scores are automatically calculated
3. Source validation history is maintained
4. AI-generated content is properly tracked and scored
5. Source reliability dashboard provides clear insights
6. Cross-reference validation is implemented
7. Source lineage is traceable for all attributes
