# Ticket 8.5: Implement Performance Testing Framework

## Priority
High

## Type
Testing

## Status
To Do

## Description
Implement a comprehensive performance testing framework for the Vitalyst Knowledge Graph system to ensure optimal performance, scalability, and reliability under various load conditions. The framework should validate system performance against the requirements specified in the blueprint, monitor resource utilization, and identify potential bottlenecks across all system components including Neo4j graph operations, API endpoints, and frontend rendering.

## Technical Details

1. Performance Testing Framework Setup
```typescript
// src/tests/performance/setup.ts
import { Options } from 'k6/options';
import { SharedArray } from 'k6/data';
import { check, sleep } from 'k6';
import { MetricsCollector } from './collectors/metrics';
import { Neo4jMetrics } from './collectors/neo4j';
import { ApiMetrics } from './collectors/api';

export const defaultOptions: Options = {
  stages: [
    { duration: '2m', target: 50 },  // Ramp up
    { duration: '5m', target: 50 },  // Steady load
    { duration: '2m', target: 100 }, // Peak load
    { duration: '1m', target: 0 },   // Scale down
  ],
  thresholds: {
    http_req_duration: ['p(95)<500'], // 95% of requests should be below 500ms
    http_req_failed: ['rate<0.01'],   // Error rate below 1%
    'neo4j_query_time': ['p(95)<100'] // Neo4j queries under 100ms
  }
};

// Test data setup
const testData = new SharedArray('test_data', () => {
  return generateTestData(1000); // Generate 1000 test nodes
});

export function setupMetricsCollector() {
  return new MetricsCollector({
    neo4j: new Neo4jMetrics(),
    api: new ApiMetrics()
  });
}
```

2. Graph Database Performance Tests
```typescript
// src/tests/performance/neo4j/graphOperations.test.ts
import { test } from 'k6/execution';
import { Options } from 'k6/options';
import { defaultOptions, setupMetricsCollector } from '../setup';

export const options: Options = {
  ...defaultOptions,
  scenarios: {
    graph_operations: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 20 },
        { duration: '3m', target: 20 },
        { duration: '1m', target: 0 }
      ]
    }
  }
};

export default function() {
  const metrics = setupMetricsCollector();
  
  // Test complex graph traversals
  metrics.measure('graph_traversal', () => {
    const query = `
      MATCH (f:Food)-[r:HAS_NUTRIENT]->(c:Content)-[r2:REFERS_TO]->(n:Nutrient)
      WHERE f.type = 'fruit' AND n.type = 'vitamin'
      RETURN f, c, n
      LIMIT 100
    `;
    const result = neo4j.run(query);
    check(result, {
      'traversal_successful': (r) => r !== null,
      'result_count': (r) => r.length > 0
    });
  });

  // Test vector search performance
  metrics.measure('vector_search', () => {
    const query = `
      CALL db.index.vector.queryNodes('nutrient_embeddings', 10, $embedding)
      YIELD node, score
      RETURN node, score
    `;
    const result = neo4j.run(query, { embedding: generateTestEmbedding() });
    check(result, {
      'search_successful': (r) => r !== null,
      'results_found': (r) => r.length === 10
    });
  });

  sleep(1);
}
```

3. API Endpoint Performance Tests
```typescript
// src/tests/performance/api/endpoints.test.ts
import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';
import { defaultOptions } from '../setup';

const errorRate = new Rate('errors');

export const options = {
  ...defaultOptions,
  scenarios: {
    api_endpoints: {
      executor: 'constant-vus',
      vus: 50,
      duration: '5m'
    }
  }
};

export default function() {
  // Test node creation performance
  const createNodeResult = http.post(`${__ENV.API_URL}/api/v1/nodes`, {
    name: 'Performance Test Node',
    type: 'test',
    validation_status: 'draft'
  });
  
  check(createNodeResult, {
    'status is 201': (r) => r.status === 201,
    'response time OK': (r) => r.timings.duration < 200
  }) || errorRate.add(1);

  // Test AI enrichment performance
  const enrichmentResult = http.post(`${__ENV.API_URL}/api/v1/ai/enrich`, {
    node_id: createNodeResult.json('id'),
    prompt: 'Enrich with nutritional information'
  });
  
  check(enrichmentResult, {
    'status is 200': (r) => r.status === 200,
    'enrichment time OK': (r) => r.timings.duration < 5000
  }) || errorRate.add(1);

  sleep(1);
}
```

4. Frontend Performance Tests
```typescript
// src/tests/performance/frontend/rendering.test.ts
import { chromium } from 'playwright';
import { PerformanceObserver } from 'perf_hooks';
import { defaultOptions } from '../setup';

export default async function() {
  const browser = await chromium.launch();
  const page = await browser.newPage();
  
  // Measure graph rendering performance
  await page.goto('/dashboard');
  
  const metrics = await page.evaluate(() => {
    const observer = new PerformanceObserver((list) => {
      const entries = list.getEntries();
      return {
        fcp: entries.find(e => e.name === 'first-contentful-paint').startTime,
        lcp: entries.find(e => e.name === 'largest-contentful-paint').startTime,
        cls: entries.find(e => e.name === 'cumulative-layout-shift').value
      };
    });
    
    observer.observe({ entryTypes: ['paint', 'layout-shift'] });
  });
  
  check(metrics, {
    'FCP under 1s': (m) => m.fcp < 1000,
    'LCP under 2.5s': (m) => m.lcp < 2500,
    'CLS under 0.1': (m) => m.cls < 0.1
  });

  // Test graph interaction performance
  const interactionMetrics = await page.evaluate(async () => {
    const start = performance.now();
    await window.testGraph.zoomToFit();
    await window.testGraph.fitView();
    return performance.now() - start;
  });
  
  check(interactionMetrics, {
    'Graph interactions under 100ms': (m) => m < 100
  });

  await browser.close();
}
```

5. Load Testing and Monitoring Integration
```typescript
// src/tests/performance/monitoring/integration.ts
import { PrometheusClient } from './clients/prometheus';
import { GrafanaClient } from './clients/grafana';
import { defaultOptions } from '../setup';

export class PerformanceMonitoring {
  private prometheus: PrometheusClient;
  private grafana: GrafanaClient;
  
  constructor() {
    this.prometheus = new PrometheusClient(process.env.PROMETHEUS_URL);
    this.grafana = new GrafanaClient(process.env.GRAFANA_URL);
  }

  async captureMetrics(testRun: string) {
    const metrics = await Promise.all([
      this.prometheus.queryRange('http_request_duration_seconds', {
        start: testRun.startTime,
        end: testRun.endTime,
        step: '15s'
      }),
      this.prometheus.queryRange('neo4j_query_execution_time', {
        start: testRun.startTime,
        end: testRun.endTime,
        step: '15s'
      }),
      this.prometheus.queryRange('node{type="memory_usage"}', {
        start: testRun.startTime,
        end: testRun.endTime,
        step: '15s'
      })
    ]);

    await this.grafana.createDashboard({
      title: `Performance Test Results - ${testRun.id}`,
      metrics,
      annotations: testRun.events
    });

    return metrics;
  }
}
```

6. Multi-Language Performance Tests
```typescript
// src/tests/performance/i18n/languagePerformance.test.ts
import { test } from 'k6/execution';
import { Options } from 'k6/options';
import { defaultOptions, setupMetricsCollector } from '../setup';

export const options: Options = {
  ...defaultOptions,
  scenarios: {
    language_switching: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '1m', target: 20 },
        { duration: '3m', target: 20 },
        { duration: '1m', target: 0 }
      ]
    }
  }
};

export default function() {
  const metrics = setupMetricsCollector();
  
  // Test language switching performance
  metrics.measure('language_switch', () => {
    const languages = ['en', 'de', 'es'];
    languages.forEach(lang => {
      const result = http.get(`${__ENV.API_URL}/api/v1/content?lang=${lang}`);
      check(result, {
        'status is 200': (r) => r.status === 200,
        'switch time OK': (r) => r.timings.duration < 100
      });
    });
  });

  // Test multi-language content loading
  metrics.measure('content_load', () => {
    const result = http.get(`${__ENV.API_URL}/api/v1/content/multilang`);
    check(result, {
      'status is 200': (r) => r.status === 200,
      'load time OK': (r) => r.timings.duration < 200
    });
  });
}
```

7. AI Enrichment Performance Tests
```typescript
// src/tests/performance/ai/enrichmentPerformance.test.ts
import { test } from 'k6/execution';
import { Options } from 'k6/options';
import { defaultOptions, setupMetricsCollector } from '../setup';

export const options: Options = {
  ...defaultOptions,
  scenarios: {
    ai_enrichment: {
      executor: 'constant-vus',
      vus: 10,
      duration: '5m'
    }
  }
};

export default function() {
  const metrics = setupMetricsCollector();
  
  // Test AI service failover performance
  metrics.measure('ai_failover', () => {
    const result = http.post(`${__ENV.API_URL}/api/v1/ai/enrich`, {
      node_id: 'test-node',
      force_failover: true
    });
    check(result, {
      'failover time OK': (r) => r.timings.duration < 1000,
      'status is 200': (r) => r.status === 200
    });
  });

  // Test concurrent AI enrichment
  metrics.measure('concurrent_enrichment', () => {
    const requests = Array(5).fill(null).map(() => ({
      method: 'POST',
      url: `${__ENV.API_URL}/api/v1/ai/enrich`,
      body: JSON.stringify({ node_id: `test-node-${Date.now()}` })
    }));
    
    const responses = http.batch(requests);
    check(responses, {
      'all successful': (rs) => rs.every(r => r.status === 200),
      'batch time OK': (rs) => Math.max(...rs.map(r => r.timings.duration)) < 5000
    });
  });
}
```

## Performance Baselines and Metrics
```typescript
// src/tests/performance/baselines.ts
export const performanceBaselines = {
  api: {
    p95ResponseTime: 500,  // 95th percentile response time in ms
    errorRate: 0.01,       // 1% error rate threshold
    rps: 100              // Requests per second
  },
  neo4j: {
    queryTime: 100,        // Query execution time in ms
    connectionPool: 50,    // Minimum available connections
    cacheHitRate: 0.8     // 80% cache hit rate
  },
  frontend: {
    fcp: 1000,            // First Contentful Paint in ms
    lcp: 2500,            // Largest Contentful Paint in ms
    cls: 0.1,             // Cumulative Layout Shift
    tti: 3000             // Time to Interactive in ms
  },
  ai: {
    enrichmentTime: 5000,  // AI enrichment time in ms
    failoverTime: 1000,    // Failover response time in ms
    concurrentLimit: 20    // Maximum concurrent requests
  }
};
```

## Business Metrics Correlation
```typescript
// src/tests/performance/business/correlation.ts
export class BusinessMetricsCorrelation {
  async correlatePerformanceWithBusiness(): Promise<CorrelationReport> {
    const performanceMetrics = await this.getPerformanceMetrics();
    const businessMetrics = await this.getBusinessMetrics();
    
    return {
      userEngagement: this.correlateEngagement(performanceMetrics, businessMetrics),
      dataQuality: this.correlateDataQuality(performanceMetrics, businessMetrics),
      systemEfficiency: this.correlateEfficiency(performanceMetrics, businessMetrics)
    };
  }

  private correlateEngagement(perf: Metrics, business: Metrics): CorrelationResult {
    return {
      responseTimeImpact: this.calculateImpact(
        perf.responseTime,
        business.userRetention
      ),
      availabilityImpact: this.calculateImpact(
        perf.uptime,
        business.activeUsers
      )
    };
  }
}
```

## Test Data Generation Patterns
```typescript
// src/tests/performance/data/generators.ts
export class TestDataGenerator {
  generateRealisticDataset(size: number): TestData {
    return {
      nodes: this.generateNodes(size),
      relationships: this.generateRelationships(size),
      properties: this.generateProperties(size)
    };
  }

  private generateNodes(count: number): Node[] {
    return Array(count).fill(null).map((_, i) => ({
      id: `node-${i}`,
      type: this.randomType(),
      properties: this.generateNodeProperties()
    }));
  }

  private generateRelationships(count: number): Relationship[] {
    return Array(count).fill(null).map((_, i) => ({
      source: `node-${Math.floor(Math.random() * count)}`,
      target: `node-${Math.floor(Math.random() * count)}`,
      type: this.randomRelationType()
    }));
  }
}
```

## Search Space Organization
```
src/tests/performance/
├── api/                 # API performance tests
├── neo4j/              # Database performance tests
├── frontend/           # UI performance tests
├── ai/                 # AI service performance tests
├── i18n/               # Multi-language performance tests
├── business/           # Business metrics correlation
├── data/               # Test data generation
└── baselines/          # Performance baselines
```

## Implementation Notes
1. Performance tests should be integrated into the CI/CD pipeline but run separately from unit and integration tests.
2. Test data should be generated to match production patterns and volumes.
3. Monitor and collect metrics for:
   - API response times
   - Neo4j query execution times
   - Graph rendering performance
   - Memory usage and CPU utilization
   - Network latency and throughput
4. Implement proper test data cleanup to prevent database growth.
5. Store historical performance data for trend analysis.
6. Configure alerting for performance regression.

## Dependencies
- k6 for load testing
- Playwright for frontend performance testing
- Prometheus for metrics collection
- Grafana for visualization
- Custom metrics collectors
- Test data generators

## Acceptance Criteria
1. System handles specified concurrent user load
2. API endpoints respond within defined SLA
3. Neo4j queries perform within acceptable limits
4. Frontend renders and updates efficiently
5. Resource utilization remains within bounds
6. Performance metrics are properly collected and visualized
7. Historical performance data is maintained
8. Automated alerts trigger on performance regression
