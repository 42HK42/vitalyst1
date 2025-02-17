# Ticket 7.1: Finalize CSV Import Scripts

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive CSV import scripts for the Vitalyst Knowledge Graph that handle data from multiple sources (@Tab_Vit_C_v7.csv and @Nahrungsmittel_Database2_real.csv), with robust error handling, detailed logging, and data validation. The system must maintain data integrity and traceability while capturing all source details and history as specified in the blueprint. The implementation should support incremental updates, handle large datasets efficiently, and provide detailed audit trails.

## Technical Details
1. CSV Import Service Implementation
```typescript
// src/services/csv_import.ts
import { 
  DataValidator, 
  GraphService, 
  HistoryTracker, 
  PerformanceMonitor,
  AuditLogger,
  BatchProcessor,
  ValidationQueue,
  ImportCache
} from '../services';
import { 
  ImportConfig, 
  ImportStats, 
  ValidationResult,
  ImportMetrics,
  DataSource
} from '../types';
import { 
  createReadStream, 
  createWriteStream,
  promises as fs 
} from 'fs';
import { parse } from 'csv-parse';
import { Transform } from 'stream';
import { DateTime } from 'luxon';
import { chunk } from 'lodash';

export class CSVImportService {
  private readonly batchSize = 1000;
  private readonly validator: DataValidator;
  private readonly graphService: GraphService;
  private readonly historyTracker: HistoryTracker;
  private readonly metrics: PerformanceMonitor;
  private readonly auditLogger: AuditLogger;
  private readonly batchProcessor: BatchProcessor;
  private readonly validationQueue: ValidationQueue;
  private readonly importCache: ImportCache;

  constructor(config: ImportConfig) {
    this.validator = new DataValidator();
    this.graphService = new GraphService();
    this.historyTracker = new HistoryTracker();
    this.metrics = new PerformanceMonitor('csv-import');
    this.auditLogger = new AuditLogger('import');
    this.batchProcessor = new BatchProcessor(this.batchSize);
    this.validationQueue = new ValidationQueue();
    this.importCache = new ImportCache();
  }

  async importData(
    source: DataSource,
    filePath: string,
    options: ImportOptions = {}
  ): Promise<ImportStats> {
    const operationId = `import_${source}_${DateTime.now().toISO()}`;
    this.metrics.startOperation(operationId);

    try {
      // Validate file existence and format
      await this.validateFile(filePath);

      // Initialize import session
      const sessionId = await this.initializeImportSession(source, filePath);

      // Process file in batches using streams
      const importStats = await this.processCsvStream(
        filePath,
        source,
        sessionId,
        options
      );

      // Validate relationships and data consistency
      await this.validateImportedData(sessionId);

      // Generate import report
      const report = await this.generateImportReport(sessionId, importStats);

      // Log successful import
      await this.auditLogger.logEvent({
        type: 'import_completed',
        source,
        sessionId,
        stats: importStats,
        timestamp: DateTime.now().toISO()
      });

      this.metrics.endOperation(operationId);
      return importStats;

    } catch (error) {
      this.metrics.recordError(operationId, error);
      await this.handleImportError(error, source, filePath);
      throw error;
    }
  }

  private async processCsvStream(
    filePath: string,
    source: DataSource,
    sessionId: string,
    options: ImportOptions
  ): Promise<ImportStats> {
    const stats: ImportStats = {
      total: 0,
      processed: 0,
      success: 0,
      failed: 0,
      warnings: 0,
      skipped: 0,
      relationships: 0
    };

    const parser = createReadStream(filePath)
      .pipe(parse({ columns: true, skip_empty_lines: true }));

    const transformer = new Transform({
      objectMode: true,
      async transform(chunk, encoding, callback) {
        try {
          // Validate and transform data
          const validationResult = await this.validator.validateRow(
            chunk,
            source
          );

          if (validationResult.isValid) {
            // Transform data according to source type
            const transformedData = await this.transformData(
              chunk,
              source,
              validationResult
            );

            // Add to validation queue
            await this.validationQueue.add({
              data: transformedData,
              source,
              sessionId,
              validation: validationResult
            });

            stats.success++;
          } else {
            stats.failed++;
            await this.logValidationError(chunk, validationResult, sessionId);
          }

          stats.processed++;
          callback(null, { chunk, validationResult });
        } catch (error) {
          stats.failed++;
          await this.handleProcessingError(error, chunk, sessionId);
          callback(error);
        }
      }
    });

    // Process in batches
    for await (const batch of this.batchProcessor.process(transformer)) {
      await this.processBatch(batch, sessionId, stats);
    }

    return stats;
  }

  private async processBatch(
    batch: any[],
    sessionId: string,
    stats: ImportStats
  ): Promise<void> {
    try {
      // Create nodes and relationships in transaction
      await this.graphService.transaction(async (tx) => {
        for (const item of batch) {
          if (item.validationResult.isValid) {
            // Create or update node
            const nodeId = await this.createNode(item.data, tx);

            // Create relationships
            const relationshipCount = await this.createRelationships(
              nodeId,
              item.data,
              tx
            );

            stats.relationships += relationshipCount;

            // Track history
            await this.historyTracker.recordImport({
              nodeId,
              sessionId,
              data: item.data,
              validation: item.validationResult
            });
          }
        }
      });

      // Update cache
      await this.importCache.setBatch(batch.map(item => ({
        id: item.data.id,
        hash: item.data.hash,
        timestamp: DateTime.now().toISO()
      })));

    } catch (error) {
      await this.handleBatchError(error, batch, sessionId);
      throw error;
    }
  }

  private async validateImportedData(
    sessionId: string
  ): Promise<ValidationResult[]> {
    const results = await this.validator.validateImportedData(sessionId);
    
    // Log validation results
    await this.auditLogger.logEvent({
      type: 'import_validation_completed',
      sessionId,
      results,
      timestamp: DateTime.now().toISO()
    });

    return results;
  }

  private async generateImportReport(
    sessionId: string,
    stats: ImportStats
  ): Promise<ImportReport> {
    const report = {
      sessionId,
      timestamp: DateTime.now().toISO(),
      stats,
      metrics: await this.getMetrics(),
      validation: await this.validationQueue.getResults(sessionId),
      errors: await this.getImportErrors(sessionId)
    };

    // Save report
    await fs.writeFile(
      `reports/import_${sessionId}.json`,
      JSON.stringify(report, null, 2)
    );

    return report;
  }

  private async getMetrics(): Promise<ImportMetrics> {
    return {
      performance: this.metrics.getMetrics(),
      memory: process.memoryUsage(),
      cache: await this.importCache.getMetrics(),
      validation: await this.validationQueue.getMetrics(),
      database: await this.graphService.getMetrics()
    };
  }
}

2. Data Validation Implementation
```typescript
// src/services/validation.ts
import { 
  ValidationRule,
  ValidationResult,
  DataSource,
  SchemaValidator,
  RelationshipValidator,
  ConsistencyValidator
} from '../types';
import { z } from 'zod';

export class DataValidator {
  private readonly schemaValidator: SchemaValidator;
  private readonly relationshipValidator: RelationshipValidator;
  private readonly consistencyValidator: ConsistencyValidator;

  constructor() {
    this.schemaValidator = new SchemaValidator();
    this.relationshipValidator = new RelationshipValidator();
    this.consistencyValidator = new ConsistencyValidator();
  }

  async validateRow(
    data: any,
    source: DataSource
  ): Promise<ValidationResult> {
    const results = await Promise.all([
      this.validateSchema(data, source),
      this.validateRelationships(data, source),
      this.validateConsistency(data, source)
    ]);

    return this.mergeValidationResults(results);
  }

  private async validateSchema(
    data: any,
    source: DataSource
  ): Promise<ValidationResult> {
    const schema = this.getSourceSchema(source);
    return await this.schemaValidator.validate(data, schema);
  }

  private async validateRelationships(
    data: any,
    source: DataSource
  ): Promise<ValidationResult> {
    const rules = this.getRelationshipRules(source);
    return await this.relationshipValidator.validate(data, rules);
  }

  private async validateConsistency(
    data: any,
    source: DataSource
  ): Promise<ValidationResult> {
    const rules = this.getConsistencyRules(source);
    return await this.consistencyValidator.validate(data, rules);
  }

  private getSourceSchema(source: DataSource): z.ZodSchema {
    switch (source) {
      case 'vitamin':
        return this.getVitaminSchema();
      case 'food':
        return this.getFoodSchema();
      default:
        throw new Error(`Unknown data source: ${source}`);
    }
  }

  private getVitaminSchema(): z.ZodSchema {
    return z.object({
      vitID: z.string().regex(/^VIT_[A-Z0-9]+$/),
      name: z.object({
        de: z.string(),
        en: z.string().optional()
      }),
      chemical_formula: z.string(),
      molecular_weight: z.object({
        value: z.number().positive(),
        unit: z.string(),
        uncertainty: z.number().min(0).max(1).optional()
      }),
      // ... additional schema definitions
    });
  }

  private getFoodSchema(): z.ZodSchema {
    return z.object({
      name: z.object({
        de: z.string(),
        en: z.string().optional()
      }),
      category: z.array(z.string()),
      environmental_metrics: z.object({
        co2_footprint: z.object({
          value: z.number().nonnegative(),
          unit: z.string(),
          source: z.string(),
          uncertainty: z.number().min(0).max(1).optional()
        }),
        water_consumption: z.object({
          value: z.number().nonnegative(),
          unit: z.string(),
          source: z.string(),
          uncertainty: z.number().min(0).max(1).optional()
        })
      }),
      // ... additional schema definitions
    });
  }
}

3. Import Cache Implementation
```typescript
// src/services/import_cache.ts
import { Redis } from 'ioredis';
import { ImportCacheEntry, ImportCacheMetrics } from '../types';

export class ImportCache {
  private readonly redis: Redis;
  private readonly prefix = 'import:';
  private readonly ttl = 60 * 60 * 24; // 24 hours

  constructor() {
    this.redis = new Redis({
      keyPrefix: this.prefix,
      // ... Redis configuration
    });
  }

  async setBatch(entries: ImportCacheEntry[]): Promise<void> {
    const pipeline = this.redis.pipeline();
    
    for (const entry of entries) {
      pipeline.hset(
        entry.id,
        {
          hash: entry.hash,
          timestamp: entry.timestamp
        }
      );
      pipeline.expire(entry.id, this.ttl);
    }

    await pipeline.exec();
  }

  async getMetrics(): Promise<ImportCacheMetrics> {
    const keys = await this.redis.keys(`${this.prefix}*`);
    const memory = await this.redis.info('memory');
    
    return {
      entries: keys.length,
      memory_usage: parseInt(memory.split('\r\n')
        .find(line => line.startsWith('used_memory:'))
        ?.split(':')[1] || '0'
      ),
      hit_rate: await this.calculateHitRate()
    };
  }
}
```

## Implementation Strategy
1. Core Import System
   - Implement streaming CSV processor
   - Set up batch processing
   - Configure validation pipeline
   - Implement caching system

2. Data Validation
   - Create schema validators
   - Implement relationship validation
   - Set up consistency checks
   - Configure validation queue

3. Performance Optimization
   - Implement batch processing
   - Set up caching system
   - Configure memory management
   - Optimize database operations

4. Error Handling & Recovery
   - Implement error tracking
   - Set up recovery mechanisms
   - Configure rollback procedures
   - Implement retry logic

5. Monitoring & Reporting
   - Set up performance monitoring
   - Implement audit logging
   - Create reporting system
   - Configure alerts

## Acceptance Criteria
- [ ] Robust CSV import implementation for both data sources
- [ ] Comprehensive error handling and logging
- [ ] Data validation with schema checks
- [ ] Source details and history tracking
- [ ] Import statistics and reporting
- [ ] Performance optimization for large datasets
- [ ] Data integrity verification
- [ ] Rollback capability for failed imports
- [ ] Batch processing implementation
- [ ] Caching system working
- [ ] Memory optimization complete
- [ ] Monitoring system implemented

## Dependencies
- Ticket 2.7: CSV-Specific Models
- Ticket 2.8: Historical Data Tracking
- Ticket 2.12: Data Migration
- Ticket 3.3: Zero-Trust Security

## Estimated Hours
40

## Testing Requirements
- Unit Tests:
  - Test data validation
  - Verify history tracking
  - Test error handling
  - Validate schema checks
  - Test caching system
  - Verify batch processing
  - Test memory management
  - Validate retry logic

- Integration Tests:
  - Test full import flow
  - Verify data integrity
  - Test rollback functionality
  - Validate batch operations
  - Test cache integration
  - Verify monitoring system
  - Test alert triggers
  - Validate reporting

- Performance Tests:
  - Test large dataset handling
  - Measure import speed
  - Verify memory usage
  - Test concurrent imports
  - Validate batch performance
  - Measure cache efficiency
  - Test recovery times
  - Verify scalability

- Data Quality Tests:
  - Validate data transformations
  - Verify source tracking
  - Test history accuracy
  - Validate relationships
  - Test consistency rules
  - Verify data integrity
  - Test schema validation
  - Validate audit trails

## Documentation
- Import process guide
- Data validation rules
- Error handling procedures
- History tracking details
- Performance optimization tips
- Rollback procedures
- Batch processing guide
- Caching system overview
- Monitoring setup
- Alert configuration
- Recovery procedures
- Troubleshooting guide

## Search Space Optimization
- Clear service hierarchy
- Consistent naming patterns
- Standardized interfaces
- Logical file organization
- Well-documented utilities
- Organized test structure
- Clear error handling
- Consistent logging patterns
- Standardized metrics
- Organized validation rules
- Structured cache design
- Modular batch processing

## References
- **Phasedplan.md:** Phase 7, Ticket 7.1
- **Blueprint.md:** Sections on Data Import and Integration
- Pandas Documentation
- Neo4j Import Guidelines
- Data Validation Best Practices
- Stream Processing Patterns
- Batch Processing Guidelines
- Caching Strategies
- Memory Management Best Practices
- Performance Monitoring Standards

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the CSV import functionality as specified in the blueprint, with particular attention to:
- Robust error handling
- Comprehensive logging
- Data validation
- History tracking
- Performance optimization
- Data integrity
- Batch processing
- Caching system
- Memory management
- Monitoring integration
- Security measures
- Scalability support
``` 