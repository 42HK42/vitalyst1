# Ticket 5.1: AI Provider Integration

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement a comprehensive AI provider integration system for the Vitalyst Knowledge Graph that securely manages multiple AI providers (OpenAI, Claude, etc.) through LangChain, with robust fallback mechanisms, intelligent provider selection, performance monitoring, and secure API key management. The system must handle rate limiting, cost optimization, response validation, and maintain detailed audit logs while following zero-trust security principles as specified in the blueprint.

## Technical Details
1. AI Provider Service Implementation
```typescript
// src/services/AIProviderService.ts
import { LangChain, OpenAI, Anthropic, HuggingFace } from 'langchain';
import { SecretManager } from './SecretManager';
import { RateLimiter } from './RateLimiter';
import { CostManager } from './CostManager';
import { PerformanceMonitor } from './PerformanceMonitor';
import { ResponseValidator } from './ResponseValidator';
import { AIResponse, Provider, ModelConfig } from '../types/ai';

interface ProviderConfig {
  name: Provider;
  models: ModelConfig[];
  rateLimits: {
    requestsPerMinute: number;
    tokensPerMinute: number;
    concurrentRequests: number;
  };
  costConfig: {
    costPerToken: number;
    costPerRequest: number;
  };
  timeout: number;
  retryConfig: {
    maxRetries: number;
    backoffFactor: number;
    initialDelay: number;
  };
}

export class AIProviderService {
  private providers: Map<Provider, any>;
  private secretManager: SecretManager;
  private rateLimiter: RateLimiter;
  private costManager: CostManager;
  private performanceMonitor: PerformanceMonitor;
  private responseValidator: ResponseValidator;
  private currentProvider: Provider;
  private providerConfigs: Map<Provider, ProviderConfig>;
  private ws: WebSocket;

  constructor() {
    this.providers = new Map();
    this.secretManager = new SecretManager();
    this.rateLimiter = new RateLimiter();
    this.costManager = new CostManager();
    this.performanceMonitor = new PerformanceMonitor('ai-providers');
    this.responseValidator = new ResponseValidator();
    this.initializeWebSocket();
    this.setupProviderConfigs();
  }

  private initializeWebSocket() {
    this.ws = new WebSocket('ws://localhost:8000/ws/ai-providers');
    this.ws.addEventListener('message', async (event) => {
      const update = JSON.parse(event.data);
      switch (update.type) {
        case 'provider_status':
          await this.handleProviderStatusUpdate(update.data);
          break;
        case 'model_update':
          await this.handleModelUpdate(update.data);
          break;
        case 'cost_alert':
          await this.handleCostAlert(update.data);
          break;
      }
    });
  }

  private setupProviderConfigs() {
    this.providerConfigs = new Map([
      ['openai', {
        name: 'openai',
        models: [
          { name: 'gpt-4', maxTokens: 8192, priority: 1 },
          { name: 'gpt-3.5-turbo', maxTokens: 4096, priority: 2 }
        ],
        rateLimits: {
          requestsPerMinute: 60,
          tokensPerMinute: 90000,
          concurrentRequests: 10
        },
        costConfig: {
          costPerToken: 0.00002,
          costPerRequest: 0.0001
        },
        timeout: 30000,
        retryConfig: {
          maxRetries: 3,
          backoffFactor: 1.5,
          initialDelay: 1000
        }
      }],
      ['anthropic', {
        name: 'anthropic',
        models: [
          { name: 'claude-2', maxTokens: 100000, priority: 1 },
          { name: 'claude-instant', maxTokens: 50000, priority: 2 }
        ],
        rateLimits: {
          requestsPerMinute: 50,
          tokensPerMinute: 150000,
          concurrentRequests: 5
        },
        costConfig: {
          costPerToken: 0.000015,
          costPerRequest: 0.0001
        },
        timeout: 60000,
        retryConfig: {
          maxRetries: 3,
          backoffFactor: 2,
          initialDelay: 2000
        }
      }]
    ]);
  }

  async initialize(): Promise<void> {
    try {
      this.performanceMonitor.startOperation('init');
      
      // Initialize providers
      const [openaiKey, claudeKey] = await Promise.all([
        this.secretManager.getSecret('OPENAI_API_KEY'),
        this.secretManager.getSecret('ANTHROPIC_API_KEY')
      ]);

      this.providers.set('openai', new OpenAI({
        apiKey: openaiKey,
        ...this.providerConfigs.get('openai')
      }));

      this.providers.set('anthropic', new Anthropic({
        apiKey: claudeKey,
        ...this.providerConfigs.get('anthropic')
      }));

      // Set initial provider
      this.currentProvider = await this.selectOptimalProvider();
      
      this.performanceMonitor.endOperation('init');
    } catch (error) {
      this.performanceMonitor.recordError('init', error);
      throw error;
    }
  }

  private async selectOptimalProvider(): Promise<Provider> {
    const metrics = await Promise.all(
      Array.from(this.providers.entries()).map(async ([name, provider]) => {
        const health = await this.checkProviderHealth(provider);
        const cost = this.costManager.getProviderCost(name);
        const performance = this.performanceMonitor.getProviderMetrics(name);
        
        return {
          name,
          score: this.calculateProviderScore(health, cost, performance)
        };
      })
    );

    return metrics.sort((a, b) => b.score - a.score)[0].name;
  }

  async enrichNode(
    nodeData: any,
    options: {
      priority?: 'speed' | 'quality' | 'cost';
      maxRetries?: number;
      timeout?: number;
    } = {}
  ): Promise<AIResponse> {
    const operationId = `enrich-${nodeData.id}`;
    this.performanceMonitor.startOperation(operationId);

    try {
      if (!this.rateLimiter.canMakeRequest(this.currentProvider)) {
        this.currentProvider = await this.selectOptimalProvider();
      }

      const provider = this.providers.get(this.currentProvider);
      const prompt = await this.generatePrompt(nodeData);
      const config = this.providerConfigs.get(this.currentProvider);

      // Track costs before request
      const costEstimate = this.costManager.estimateCost(prompt, this.currentProvider);
      await this.costManager.trackCost(this.currentProvider, costEstimate);

      const response = await this.executeWithRetry(
        async () => provider.complete(prompt),
        config.retryConfig
      );

      // Validate response
      const validationResult = await this.responseValidator.validate(response);
      if (!validationResult.isValid) {
        throw new Error(`Invalid response: ${validationResult.errors.join(', ')}`);
      }

      const processedResponse = this.processResponse(response);
      
      // Track actual costs
      const actualCost = this.costManager.calculateActualCost(
        response,
        this.currentProvider
      );
      await this.costManager.trackCost(this.currentProvider, actualCost);

      this.performanceMonitor.endOperation(operationId);
      return processedResponse;
    } catch (error) {
      this.performanceMonitor.recordError(operationId, error);
      
      if (this.shouldRetryWithFallback(error)) {
        return this.handleFailover(nodeData, options);
      }
      
      throw this.handleError(error);
    }
  }

  private async executeWithRetry<T>(
    operation: () => Promise<T>,
    retryConfig: {
      maxRetries: number;
      backoffFactor: number;
      initialDelay: number;
    }
  ): Promise<T> {
    let lastError: Error;
    let delay = retryConfig.initialDelay;

    for (let attempt = 0; attempt <= retryConfig.maxRetries; attempt++) {
      try {
        return await operation();
      } catch (error) {
        lastError = error;
        if (attempt === retryConfig.maxRetries) break;
        
        await new Promise(resolve => setTimeout(resolve, delay));
        delay *= retryConfig.backoffFactor;
      }
    }

    throw lastError;
  }

  private async handleFailover(
    nodeData: any,
    options: any
  ): Promise<AIResponse> {
    const previousProvider = this.currentProvider;
    this.currentProvider = await this.selectOptimalProvider();

    if (this.currentProvider === previousProvider) {
      throw new Error('No available fallback providers');
    }

    return this.enrichNode(nodeData, options);
  }

  private async generatePrompt(nodeData: any): Promise<string> {
    // Implement prompt generation logic based on node type and data
    return '';
  }

  private processResponse(response: any): AIResponse {
    return {
      enrichedData: response.choices[0].text,
      provider: this.currentProvider,
      confidence: this.calculateConfidence(response),
      metadata: {
        model: response.model,
        timestamp: new Date().toISOString(),
        processingTime: response.processingTime,
        tokenCount: response.usage.totalTokens
      }
    };
  }

  private calculateConfidence(response: any): number {
    // Implement confidence calculation based on response metrics
    return 0;
  }

  private shouldRetryWithFallback(error: any): boolean {
    const retryableErrors = [
      'rate_limit_exceeded',
      'server_error',
      'timeout',
      'invalid_response'
    ];
    return retryableErrors.includes(error.code);
  }

  private handleError(error: any): Error {
    const errorMap: Record<string, string> = {
      rate_limit_exceeded: 'Rate limit exceeded. Switching providers...',
      invalid_api_key: 'Invalid API key. Please check configuration.',
      server_error: 'Server error occurred. Retrying with fallback provider.',
      timeout: 'Request timed out. Switching providers...',
      invalid_response: 'Invalid response received. Retrying with fallback provider.'
    };

    const message = errorMap[error.code] || 'An unexpected error occurred';
    return new Error(message);
  }

  async getMetrics(): Promise<any> {
    return {
      providers: Object.fromEntries(
        await Promise.all(
          Array.from(this.providers.keys()).map(async provider => [
            provider,
            {
              performance: this.performanceMonitor.getProviderMetrics(provider),
              costs: await this.costManager.getProviderCosts(provider),
              rateLimits: this.rateLimiter.getProviderLimits(provider)
            }
          ])
        )
      ),
      current: this.currentProvider,
      globalMetrics: this.performanceMonitor.getGlobalMetrics()
    };
  }
}
```

2. Cost Management Implementation
```typescript
// src/services/CostManager.ts
import { Provider } from '../types/ai';

interface CostConfig {
  costPerToken: number;
  costPerRequest: number;
  budgetLimits: {
    daily: number;
    monthly: number;
  };
}

export class CostManager {
  private costs: Map<Provider, number>;
  private configs: Map<Provider, CostConfig>;
  private budgetAlerts: Set<(alert: any) => void>;

  constructor() {
    this.costs = new Map();
    this.configs = new Map();
    this.budgetAlerts = new Set();
    this.initializeConfigs();
  }

  private initializeConfigs() {
    this.configs.set('openai', {
      costPerToken: 0.00002,
      costPerRequest: 0.0001,
      budgetLimits: {
        daily: 10,
        monthly: 200
      }
    });

    this.configs.set('anthropic', {
      costPerToken: 0.000015,
      costPerRequest: 0.0001,
      budgetLimits: {
        daily: 10,
        monthly: 200
      }
    });
  }

  estimateCost(prompt: string, provider: Provider): number {
    const config = this.configs.get(provider);
    const tokenCount = this.estimateTokenCount(prompt);
    return (tokenCount * config.costPerToken) + config.costPerRequest;
  }

  async trackCost(provider: Provider, cost: number): Promise<void> {
    const currentCost = this.costs.get(provider) || 0;
    const newCost = currentCost + cost;
    this.costs.set(provider, newCost);

    const config = this.configs.get(provider);
    if (newCost >= config.budgetLimits.daily) {
      this.notifyBudgetAlert({
        provider,
        level: 'daily',
        current: newCost,
        limit: config.budgetLimits.daily
      });
    }
  }

  private notifyBudgetAlert(alert: any): void {
    this.budgetAlerts.forEach(callback => callback(alert));
  }

  onBudgetAlert(callback: (alert: any) => void): void {
    this.budgetAlerts.add(callback);
  }

  async getProviderCosts(provider: Provider): Promise<any> {
    return {
      current: this.costs.get(provider) || 0,
      limits: this.configs.get(provider).budgetLimits
    };
  }
}
```

3. Performance Monitoring Implementation
```typescript
// src/services/PerformanceMonitor.ts
interface OperationMetrics {
  startTime: number;
  endTime?: number;
  duration?: number;
  success: boolean;
  error?: Error;
}

export class PerformanceMonitor {
  private operations: Map<string, OperationMetrics>;
  private providerMetrics: Map<string, any>;

  constructor(private serviceName: string) {
    this.operations = new Map();
    this.providerMetrics = new Map();
  }

  startOperation(operationId: string): void {
    this.operations.set(operationId, {
      startTime: performance.now(),
      success: false
    });
  }

  endOperation(operationId: string): void {
    const operation = this.operations.get(operationId);
    if (operation) {
      operation.endTime = performance.now();
      operation.duration = operation.endTime - operation.startTime;
      operation.success = true;
    }
  }

  recordError(operationId: string, error: Error): void {
    const operation = this.operations.get(operationId);
    if (operation) {
      operation.endTime = performance.now();
      operation.duration = operation.endTime - operation.startTime;
      operation.success = false;
      operation.error = error;
    }
  }

  getProviderMetrics(provider: string): any {
    return this.providerMetrics.get(provider) || {
      totalRequests: 0,
      successfulRequests: 0,
      failedRequests: 0,
      averageLatency: 0
    };
  }

  getGlobalMetrics(): any {
    const operations = Array.from(this.operations.values());
    return {
      totalOperations: operations.length,
      successfulOperations: operations.filter(op => op.success).length,
      failedOperations: operations.filter(op => !op.success).length,
      averageLatency: this.calculateAverageLatency(operations)
    };
  }

  private calculateAverageLatency(operations: OperationMetrics[]): number {
    const completedOperations = operations.filter(op => op.duration);
    if (completedOperations.length === 0) return 0;
    
    const totalDuration = completedOperations.reduce(
      (sum, op) => sum + op.duration,
      0
    );
    return totalDuration / completedOperations.length;
  }
}
```

## Implementation Strategy
1. Provider Integration
   - Implement provider interfaces
   - Set up API key management
   - Configure provider selection
   - Implement fallback mechanisms

2. Cost Management
   - Implement cost tracking
   - Set up budget alerts
   - Configure usage limits
   - Implement optimization

3. Performance Monitoring
   - Set up metrics collection
   - Implement latency tracking
   - Configure error monitoring
   - Set up real-time alerts

4. Security & Validation
   - Implement API key rotation
   - Set up response validation
   - Configure audit logging
   - Implement rate limiting

## Acceptance Criteria
- [ ] Multiple AI provider integration
- [ ] Secure API key management
- [ ] Intelligent provider selection
- [ ] Robust fallback mechanisms
- [ ] Cost tracking and optimization
- [ ] Performance monitoring
- [ ] Response validation
- [ ] Error handling
- [ ] Rate limiting
- [ ] Audit logging
- [ ] Documentation
- [ ] Unit tests
- [ ] Integration tests
- [ ] Performance tests

## Dependencies
- Ticket 3.3: Zero-Trust Security
- Ticket 3.2: Core API Endpoints
- Ticket 5.2: AI Enrichment Business Logic

## Estimated Hours
35

## Testing Requirements
- Unit Tests:
  - Test provider integration
  - Verify fallback mechanisms
  - Test cost tracking
  - Validate response handling
  - Test rate limiting
  - Verify error handling

- Integration Tests:
  - Test provider switching
  - Verify cost optimization
  - Test performance monitoring
  - Validate audit logging
  - Test security measures
  - Verify API key rotation

- Performance Tests:
  - Measure response times
  - Test concurrent requests
  - Verify memory usage
  - Test provider failover
  - Monitor cost efficiency
  - Validate optimization

- Security Tests:
  - Test API key security
  - Verify rate limiting
  - Test audit logging
  - Validate access controls
  - Test key rotation
  - Verify secure storage

## Documentation
- Provider integration guide
- Cost management overview
- Performance monitoring setup
- Security implementation
- API key management
- Error handling procedures
- Testing guidelines
- Deployment guide
- Monitoring guide
- Troubleshooting guide

## Search Space Optimization
- Clear provider hierarchy
- Consistent naming patterns
- Standardized interfaces
- Logical file organization
- Well-documented utilities
- Organized test structure
- Clear state management
- Consistent error handling
- Standardized metrics
- Organized security patterns

## References
- **Phasedplan.md:** Phase 5, Ticket 5.1
- **Blueprint.md:** Sections on AI Integration
- LangChain Documentation
- OpenAI API Guidelines
- Anthropic API Documentation
- Security Best Practices

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the AI provider integration system as specified in the blueprint, with particular attention to:
- Comprehensive integration
- Cost optimization
- Performance monitoring
- Security measures
- Error handling
- Documentation standards
- Testing coverage
- Audit logging
- Provider management
- User experience
``` 