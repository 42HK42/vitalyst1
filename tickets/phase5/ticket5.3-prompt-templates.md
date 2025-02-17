# Ticket 5.3: Define Prompt Templates and Test AI Responses

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive prompt template system and AI response testing framework for the Vitalyst Knowledge Graph. The system must provide type-specific prompt templates, validate AI responses against expected schemas, support response simulation for testing, and ensure high-quality, consistent AI enrichment. The implementation must support multi-language templates, handle complex hierarchical data structures, and maintain optimal performance while following the blueprint specifications.

## Technical Details
1. Prompt Template System Implementation
```typescript
// src/services/PromptTemplateService.ts
import { TemplateEngine } from './TemplateEngine';
import { NodeType, PromptTemplate, PromptContext, TemplateVersion } from '../types';
import { PerformanceMonitor } from './monitoring/PerformanceMonitor';
import { AuditLogger } from './logging/AuditLogger';
import { TemplateCache } from './caching/TemplateCache';
import { LanguageService } from './i18n/LanguageService';

interface TemplateConfig {
  version: TemplateVersion;
  language: string;
  model: string;
  maxTokens: number;
  temperature: number;
  validationRules: any[];
}

export class PromptTemplateService {
  private templates: Map<string, Map<TemplateVersion, PromptTemplate>>;
  private engine: TemplateEngine;
  private cache: TemplateCache;
  private metrics: PerformanceMonitor;
  private auditLogger: AuditLogger;
  private languageService: LanguageService;

  constructor() {
    this.templates = new Map();
    this.engine = new TemplateEngine();
    this.cache = new TemplateCache();
    this.metrics = new PerformanceMonitor('prompt-templates');
    this.auditLogger = new AuditLogger('templates');
    this.languageService = new LanguageService();
    this.initializeTemplates();
  }

  private async initializeTemplates(): Promise<void> {
    // Initialize base templates
    await this.initializeNodeTemplates();
    await this.initializeRelationshipTemplates();
    await this.initializeValidationTemplates();
    await this.initializeEnrichmentTemplates();
    
    // Log template initialization
    this.auditLogger.logEvent({
      type: 'templates_initialized',
      count: this.getTemplateCount(),
      timestamp: new Date()
    });
  }

  private async initializeNodeTemplates(): Promise<void> {
    // Nutrient node templates
    const nutrientTemplates = new Map<TemplateVersion, PromptTemplate>();
    
    nutrientTemplates.set('1.0', {
      base: await this.loadTemplate('nutrient/base.v1.prompt'),
      followUp: await this.loadTemplate('nutrient/followup.v1.prompt'),
      revision: await this.loadTemplate('nutrient/revision.v1.prompt'),
      config: {
        version: '1.0',
        model: 'gpt-4',
        maxTokens: 2000,
        temperature: 0.7,
        validationRules: [
          {
            field: 'description',
            minLength: 100,
            maxLength: 1000,
            requiredKeywords: ['chemical', 'biological', 'function']
          },
          {
            field: 'chemicalProperties',
            required: ['formula', 'molecularWeight', 'structure'],
            validators: ['chemicalFormulaValidator', 'molecularWeightRange']
          }
        ]
      }
    });

    // Food node templates
    const foodTemplates = new Map<TemplateVersion, PromptTemplate>();
    
    foodTemplates.set('1.0', {
      base: await this.loadTemplate('food/base.v1.prompt'),
      followUp: await this.loadTemplate('food/followup.v1.prompt'),
      revision: await this.loadTemplate('food/revision.v1.prompt'),
      config: {
        version: '1.0',
        model: 'gpt-4',
        maxTokens: 2000,
        temperature: 0.7,
        validationRules: [
          {
            field: 'nutritionalComposition',
            required: ['macronutrients', 'micronutrients', 'energy'],
            validators: ['nutritionalCompleteness', 'valueRanges']
          },
          {
            field: 'environmentalMetrics',
            required: ['co2Footprint', 'waterUsage', 'landUse'],
            validators: ['metricRanges', 'dataCompleteness']
          }
        ]
      }
    });

    this.templates.set('nutrient', nutrientTemplates);
    this.templates.set('food', foodTemplates);
  }

  async generatePrompt(
    nodeType: NodeType,
    context: PromptContext,
    templateType: 'base' | 'followUp' | 'revision' = 'base',
    config: Partial<TemplateConfig> = {}
  ): Promise<string> {
    const operationId = `generate_prompt_${nodeType}_${templateType}`;
    this.metrics.startOperation(operationId);

    try {
      // Get template version
      const version = config.version || this.getLatestVersion(nodeType);
      const template = await this.getTemplate(nodeType, version, templateType);
      
      if (!template) {
        throw new Error(`No template found for node type: ${nodeType}, version: ${version}`);
      }

      // Merge configurations
      const mergedConfig = {
        ...template.config,
        ...config
      };

      // Get language-specific content
      const languageContent = await this.languageService.getContent(
        nodeType,
        context.language || 'en'
      );

      // Prepare context with language content
      const enrichedContext = {
        ...context,
        language: languageContent,
        schema: await this.getResponseSchema(nodeType, version),
        nodeData: this.formatNodeData(context.nodeData),
        config: mergedConfig
      };

      // Generate prompt
      const prompt = await this.engine.render(template[templateType], enrichedContext);
      
      // Cache generated prompt
      await this.cache.set(
        this.getCacheKey(nodeType, version, templateType, context),
        prompt
      );

      // Log generation
      this.auditLogger.logEvent({
        type: 'prompt_generated',
        nodeType,
        templateType,
        version,
        timestamp: new Date()
      });

      this.metrics.endOperation(operationId);
      return prompt;

    } catch (error) {
      this.metrics.recordError(operationId, error);
      throw error;
    }
  }

  private async getTemplate(
    nodeType: NodeType,
    version: TemplateVersion,
    templateType: string
  ): Promise<PromptTemplate | null> {
    // Try cache first
    const cacheKey = `template:${nodeType}:${version}:${templateType}`;
    const cached = await this.cache.get(cacheKey);
    if (cached) return cached;

    // Get from storage
    const templateVersions = this.templates.get(nodeType);
    if (!templateVersions) return null;

    const template = templateVersions.get(version);
    if (!template) return null;

    // Cache for future use
    await this.cache.set(cacheKey, template);
    return template;
  }

  private formatNodeData(data: any): string {
    return JSON.stringify(data, null, 2);
  }

  private getCacheKey(
    nodeType: NodeType,
    version: TemplateVersion,
    templateType: string,
    context: PromptContext
  ): string {
    return `prompt:${nodeType}:${version}:${templateType}:${context.language}`;
  }

  async getMetrics(): Promise<any> {
    return {
      templates: {
        count: this.getTemplateCount(),
        versions: this.getVersionMetrics(),
        usage: await this.getUsageMetrics()
      },
      performance: this.metrics.getMetrics(),
      cache: await this.cache.getMetrics()
    };
  }
}
```

2. Response Validation Implementation
```typescript
// src/services/ResponseValidationService.ts
import { Schema } from 'ajv';
import { NodeType, AIResponse, ValidationResult, ValidationRule } from '../types';
import { SchemaValidator } from '../utils/SchemaValidator';
import { PerformanceMonitor } from './monitoring/PerformanceMonitor';
import { AuditLogger } from './logging/AuditLogger';

export class ResponseValidationService {
  private validator: SchemaValidator;
  private schemas: Map<string, Map<string, Schema>>;
  private metrics: PerformanceMonitor;
  private auditLogger: AuditLogger;

  constructor() {
    this.validator = new SchemaValidator();
    this.schemas = new Map();
    this.metrics = new PerformanceMonitor('response-validation');
    this.auditLogger = new AuditLogger('validation');
    this.initializeSchemas();
  }

  private async initializeSchemas(): Promise<void> {
    // Load and initialize schemas for different node types and versions
    await this.loadNodeSchemas();
    await this.loadRelationshipSchemas();
    await this.loadValidationSchemas();
  }

  private async loadNodeSchemas(): Promise<void> {
    // Nutrient schemas
    const nutrientSchemas = new Map<string, Schema>();
    nutrientSchemas.set('1.0', {
      type: 'object',
      required: ['description', 'chemicalProperties', 'biologicalRoles'],
      properties: {
        description: {
          type: 'string',
          minLength: 100,
          maxLength: 1000,
          pattern: '.*(?:chemical|biological|function).*'
        },
        chemicalProperties: {
          type: 'object',
          required: ['formula', 'molecularWeight', 'structure'],
          properties: {
            formula: { 
              type: 'string',
              pattern: '^[A-Z][a-z0-9]*(?:[A-Z][a-z0-9]*)*$'
            },
            molecularWeight: {
              type: 'number',
              minimum: 0,
              maximum: 10000
            },
            structure: {
              type: 'string',
              minLength: 1
            }
          }
        },
        biologicalRoles: {
          type: 'array',
          minItems: 1,
          items: {
            type: 'object',
            required: ['role', 'mechanism', 'evidence'],
            properties: {
              role: { type: 'string', minLength: 10 },
              mechanism: { type: 'string', minLength: 20 },
              evidence: { type: 'string', minLength: 10 }
            }
          }
        }
      }
    });

    this.schemas.set('nutrient', nutrientSchemas);
  }

  async validateResponse(
    nodeType: NodeType,
    response: AIResponse,
    version: string = '1.0'
  ): Promise<ValidationResult> {
    const operationId = `validate_response_${nodeType}`;
    this.metrics.startOperation(operationId);

    try {
      const schema = await this.getSchema(nodeType, version);
      if (!schema) {
        throw new Error(`No schema found for node type: ${nodeType}, version: ${version}`);
      }

      const validationResult = await this.validator.validate(schema, response);
      const warnings = this.generateWarnings(response, nodeType);
      const suggestions = this.generateSuggestions(response, nodeType);

      const result = {
        isValid: validationResult.valid,
        errors: validationResult.errors,
        warnings,
        suggestions,
        metrics: {
          completeness: this.calculateCompleteness(response, schema),
          quality: this.calculateQualityScore(response, nodeType),
          confidence: this.calculateConfidence(validationResult)
        }
      };

      // Log validation result
      await this.auditLogger.logValidation({
        type: 'response_validation',
        nodeType,
        version,
        result,
        timestamp: new Date()
      });

      this.metrics.endOperation(operationId);
      return result;

    } catch (error) {
      this.metrics.recordError(operationId, error);
      throw error;
    }
  }

  private calculateCompleteness(response: any, schema: Schema): number {
    const requiredFields = this.getRequiredFields(schema);
    const presentFields = requiredFields.filter(field => 
      this.hasField(response, field)
    );
    return presentFields.length / requiredFields.length;
  }

  private calculateQualityScore(response: any, nodeType: NodeType): number {
    const qualityMetrics = {
      contentLength: this.evaluateContentLength(response),
      detailLevel: this.evaluateDetailLevel(response),
      consistency: this.evaluateConsistency(response),
      relevance: this.evaluateRelevance(response, nodeType)
    };

    return Object.values(qualityMetrics).reduce((sum, score) => sum + score, 0) / 4;
  }

  private calculateConfidence(validationResult: any): number {
    const errorSeverity = validationResult.errors?.reduce(
      (sum: number, error: any) => sum + this.getErrorSeverity(error),
      0
    ) || 0;

    return Math.max(0, 1 - (errorSeverity / 10));
  }

  async getMetrics(): Promise<any> {
    return {
      operations: this.metrics.getGlobalMetrics(),
      validations: {
        total: await this.getTotalValidations(),
        success_rate: await this.getSuccessRate(),
        average_confidence: await this.getAverageConfidence(),
        error_distribution: await this.getErrorDistribution()
      },
      performance: {
        average_duration: this.metrics.getAverageOperationDuration(),
        p95_duration: this.metrics.getP95OperationDuration(),
        error_rate: this.metrics.getErrorRate()
      }
    };
  }
}
```

3. Response Simulation Implementation
```typescript
// src/services/ResponseSimulationService.ts
import { NodeType, AIResponse, SimulationOptions } from '../types';
import { faker } from '@faker-js/faker';
import { PerformanceMonitor } from './monitoring/PerformanceMonitor';
import { AuditLogger } from './logging/AuditLogger';

export class ResponseSimulationService {
  private metrics: PerformanceMonitor;
  private auditLogger: AuditLogger;
  private simulators: Map<string, Function>;

  constructor() {
    this.metrics = new PerformanceMonitor('response-simulation');
    this.auditLogger = new AuditLogger('simulation');
    this.initializeSimulators();
  }

  private initializeSimulators(): void {
    this.simulators = new Map([
      ['nutrient', this.simulateNutrientResponse.bind(this)],
      ['food', this.simulateFoodResponse.bind(this)]
    ]);
  }

  async simulateResponse(
    nodeType: NodeType,
    options: SimulationOptions = {}
  ): Promise<AIResponse> {
    const operationId = `simulate_response_${nodeType}`;
    this.metrics.startOperation(operationId);

    try {
      const simulator = this.simulators.get(nodeType);
      if (!simulator) {
        throw new Error(`No simulator found for node type: ${nodeType}`);
      }

      const response = await simulator(options);

      // Log simulation
      await this.auditLogger.logEvent({
        type: 'response_simulated',
        nodeType,
        options,
        timestamp: new Date()
      });

      this.metrics.endOperation(operationId);
      return response;

    } catch (error) {
      this.metrics.recordError(operationId, error);
      throw error;
    }
  }

  private async simulateNutrientResponse(
    options: SimulationOptions
  ): Promise<AIResponse> {
    const chemicalElements = ['C', 'H', 'O', 'N', 'P', 'S'];
    const roles = [
      'Enzyme Cofactor',
      'Antioxidant',
      'Structural Component',
      'Energy Transfer',
      'Signaling Molecule'
    ];

    return {
      description: this.generateScientificDescription(options),
      chemicalProperties: {
        formula: this.generateChemicalFormula(chemicalElements),
        molecularWeight: faker.number.float({ 
          min: 100,
          max: 1000,
          precision: 0.01
        }),
        structure: this.generateSMILES()
      },
      biologicalRoles: Array.from(
        { length: faker.number.int({ min: 2, max: 5 }) },
        () => ({
          role: faker.helpers.arrayElement(roles),
          mechanism: this.generateMechanism(),
          evidence: this.generateEvidence()
        })
      ),
      interactions: this.generateInteractions(),
      sources: this.generateSources(),
      confidence: faker.number.float({ min: 0.7, max: 1, precision: 0.01 })
    };
  }

  private generateScientificDescription(options: SimulationOptions): string {
    const templates = [
      "A vital {{type}} that plays a crucial role in {{process}}. Research has shown its significance in {{function}}, particularly through its interaction with {{target}}. Studies have demonstrated its effectiveness in {{application}}, with a mechanism involving {{mechanism}}.",
      "An essential {{type}} involved in {{process}}. It functions primarily by {{mechanism}}, leading to {{outcome}}. Recent studies have highlighted its role in {{function}}, particularly in relation to {{target}}."
    ];

    const template = faker.helpers.arrayElement(templates);
    return this.fillTemplate(template, {
      type: options.type || faker.science.chemicalElement().name,
      process: faker.science.chemicalElement().symbol,
      function: faker.science.chemicalElement().name,
      target: faker.science.chemicalElement().symbol,
      application: faker.science.chemicalElement().name,
      mechanism: faker.science.chemicalElement().symbol,
      outcome: faker.science.chemicalElement().name
    });
  }

  private generateChemicalFormula(elements: string[]): string {
    return elements
      .slice(0, faker.number.int({ min: 2, max: 4 }))
      .map(element => `${element}${faker.number.int({ min: 1, max: 20 })}`)
      .join('');
  }

  private generateSMILES(): string {
    const patterns = [
      'CC(=O)O',
      'C1=CC=CC=C1',
      'C(C(=O)O)N',
      'OC(=O)CCC(=O)O'
    ];
    return faker.helpers.arrayElement(patterns);
  }

  async getMetrics(): Promise<any> {
    return {
      operations: this.metrics.getGlobalMetrics(),
      simulations: {
        total: await this.getTotalSimulations(),
        distribution: await this.getTypeDistribution(),
        quality_metrics: await this.getQualityMetrics()
      },
      performance: {
        average_duration: this.metrics.getAverageOperationDuration(),
        p95_duration: this.metrics.getP95OperationDuration(),
        error_rate: this.metrics.getErrorRate()
      }
    };
  }
}
```

4. Test Suite Implementation
```typescript
// src/tests/promptTemplates.test.ts
import { describe, it, expect, beforeEach, jest } from 'vitest';
import { PromptTemplateService } from '../services/PromptTemplateService';
import { ResponseValidationService } from '../services/ResponseValidationService';
import { ResponseSimulationService } from '../services/ResponseSimulationService';
import { NodeType, PromptTemplate, ValidationResult } from '../types';

describe('Prompt Template System', () => {
  let templateService: PromptTemplateService;
  let validationService: ResponseValidationService;
  let simulationService: ResponseSimulationService;

  beforeEach(() => {
    templateService = new PromptTemplateService();
    validationService = new ResponseValidationService();
    simulationService = new ResponseSimulationService();
  });

  describe('Template Generation', () => {
    it('generates valid prompts for nutrient nodes', async () => {
      const prompt = await templateService.generatePrompt('nutrient', {
        nodeData: {
          name: 'Vitamin C',
          type: 'nutrient'
        }
      });

      expect(prompt).toContain('scientific description');
      expect(prompt).toContain('chemical properties');
      expect(prompt).toMatchSnapshot();
    });

    it('handles multi-language templates', async () => {
      const prompt = await templateService.generatePrompt('nutrient', {
        nodeData: {
          name: 'Vitamin C',
          type: 'nutrient'
        },
        language: 'de'
      });

      expect(prompt).toContain('wissenschaftliche Beschreibung');
      expect(prompt).toMatchSnapshot();
    });
  });

  describe('Response Validation', () => {
    it('validates AI responses against schema', async () => {
      const response = await simulationService.simulateResponse('nutrient');
      const result = await validationService.validateResponse('nutrient', response);

      expect(result.isValid).toBe(true);
      expect(result.errors).toHaveLength(0);
      expect(result.metrics.completeness).toBeGreaterThan(0.9);
    });

    it('handles invalid responses appropriately', async () => {
      const invalidResponse = {
        description: 'Too short'
      };

      const result = await validationService.validateResponse('nutrient', invalidResponse);

      expect(result.isValid).toBe(false);
      expect(result.errors).toHaveLength(2);
      expect(result.suggestions).toHaveLength(2);
    });
  });

  describe('Performance & Metrics', () => {
    it('maintains performance under load', async () => {
      const startTime = Date.now();
      const promises = Array.from({ length: 100 }, () =>
        templateService.generatePrompt('nutrient', {
          nodeData: {
            name: 'Vitamin C',
            type: 'nutrient'
          }
        })
      );

      await Promise.all(promises);
      const duration = Date.now() - startTime;
      expect(duration).toBeLessThan(5000); // 5 seconds max
    });

    it('tracks and reports metrics accurately', async () => {
      const metrics = await templateService.getMetrics();
      expect(metrics.templates.count).toBeGreaterThan(0);
      expect(metrics.performance.error_rate).toBeLessThan(0.01);
    });
  });
});
```

## Implementation Strategy
1. Template System Development
   - Implement base template engine
   - Create node-specific templates
   - Set up multi-language support
   - Configure template versioning

2. Validation System
   - Implement schema validation
   - Create validation rules
   - Set up quality metrics
   - Configure confidence scoring

3. Simulation System
   - Implement response simulation
   - Create type-specific simulators
   - Set up test data generation
   - Configure simulation options

4. Performance & Monitoring
   - Implement metrics collection
   - Set up performance monitoring
   - Configure caching
   - Implement audit logging

## Acceptance Criteria
- [ ] Comprehensive template system
- [ ] Multi-language support
- [ ] Template versioning
- [ ] Schema validation
- [ ] Response simulation
- [ ] Performance optimization
- [ ] Caching system
- [ ] Audit logging
- [ ] Documentation
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance tests

## Dependencies
- Ticket 5.1: AI Provider Integration
- Ticket 5.2: AI Enrichment Business Logic
- Ticket 3.2: Core API Endpoints

## Estimated Hours
35

## Testing Requirements
- Unit Tests:
  - Test template generation
  - Verify schema validation
  - Test response simulation
  - Validate multi-language support
  - Test template versioning
  - Verify caching
  - Test metrics collection

- Integration Tests:
  - Test template workflow
  - Verify validation chain
  - Test simulation integration
  - Validate performance monitoring
  - Test audit logging
  - Verify error handling

- Performance Tests:
  - Measure template generation
  - Test concurrent operations
  - Verify memory usage
  - Test cache effectiveness
  - Monitor resource usage
  - Validate optimization

- Validation Tests:
  - Test schema validation
  - Verify quality metrics
  - Test confidence scoring
  - Validate data integrity
  - Test edge cases
  - Verify error handling

## Documentation
- Template system overview
- Validation framework guide
- Simulation system guide
- Performance optimization
- Caching strategy
- Monitoring setup
- Error handling procedures
- Testing guidelines
- API reference
- Configuration guide

## Search Space Optimization
- Clear template hierarchy
- Consistent naming patterns
- Standardized interfaces
- Logical file organization
- Well-documented utilities
- Organized test structure
- Clear state management
- Consistent error handling
- Standardized metrics
- Organized validation rules

## References
- **Phasedplan.md:** Phase 5, Ticket 5.3
- **Blueprint.md:** Sections on AI Integration
- LangChain Documentation
- Schema Validation Best Practices
- Performance Optimization Guidelines
- Testing Standards

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the prompt templates and testing system as specified in the blueprint, with particular attention to:
- Comprehensive template system
- Multi-language support
- Template versioning
- Schema validation
- Response simulation
- Performance optimization
- Caching strategy
- Audit logging
- Quality assurance
- User experience