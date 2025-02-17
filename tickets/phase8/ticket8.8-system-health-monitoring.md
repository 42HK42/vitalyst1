# Ticket 8.8: Implement System Health Monitoring

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement a comprehensive system health monitoring infrastructure for the Vitalyst Knowledge Graph system. This includes setting up Prometheus and Grafana for metrics collection and visualization, implementing custom health checks for all system components, and establishing alerting mechanisms. The monitoring system should provide real-time insights into system performance, resource utilization, and operational health while adhering to the monitoring requirements specified in the blueprint.

## Technical Details

1. Health Check Implementation
```typescript
// src/monitoring/healthCheck.ts
import { Neo4jService } from '../services/neo4j';
import { AIService } from '../services/ai';
import { HealthStatus, ComponentHealth } from '../types';

export class HealthCheckService {
  private neo4j: Neo4jService;
  private aiService: AIService;
  
  constructor(neo4j: Neo4jService, aiService: AIService) {
    this.neo4j = neo4j;
    this.aiService = aiService;
  }

  async checkSystemHealth(): Promise<ComponentHealth> {
    const [dbHealth, aiHealth, apiHealth, cacheHealth] = await Promise.all([
      this.checkDatabaseHealth(),
      this.checkAIServiceHealth(),
      this.checkAPIHealth(),
      this.checkCacheHealth()
    ]);

    return {
      status: this.aggregateHealth([dbHealth, aiHealth, apiHealth, cacheHealth]),
      components: {
        database: dbHealth,
        aiService: aiHealth,
        api: apiHealth,
        cache: cacheHealth
      },
      timestamp: new Date().toISOString()
    };
  }

  private async checkDatabaseHealth(): Promise<HealthStatus> {
    try {
      const startTime = Date.now();
      const result = await this.neo4j.runHealthCheck();
      const responseTime = Date.now() - startTime;

      return {
        status: 'healthy',
        responseTime,
        details: {
          connections: result.connections,
          queryResponseTime: result.queryTime,
          memoryUsage: result.memoryUsage
        }
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        error: error.message,
        details: {
          lastSuccessfulCheck: this.getLastSuccessfulCheck('database')
        }
      };
    }
  }

  private async checkAIServiceHealth(): Promise<HealthStatus> {
    try {
      const status = await this.aiService.checkAvailability();
      return {
        status: status.available ? 'healthy' : 'degraded',
        details: {
          model: status.model,
          quotaRemaining: status.quota,
          lastFailure: status.lastFailure
        }
      };
    } catch (error) {
      return {
        status: 'unhealthy',
        error: error.message
      };
    }
  }
}
```

2. Metrics Collection
```typescript
// src/monitoring/metrics.ts
import { Counter, Gauge, Histogram } from 'prom-client';
import { MetricsConfig } from '../config';
import { BackupMonitor } from '../backup/backupMonitor';
import { GraphMetricsCollector } from '../graph/graphMetrics';

export class MetricsCollector {
  private static instance: MetricsCollector;
  private backupMonitor: BackupMonitor;
  private graphMetrics: GraphMetricsCollector;
  
  // API Metrics
  private apiRequestCounter: Counter;
  private apiLatencyHistogram: Histogram;
  private activeConnections: Gauge;
  
  // Database Metrics
  private dbQueryCounter: Counter;
  private dbQueryLatency: Histogram;
  private dbConnectionPool: Gauge;
  
  // AI Service Metrics
  private aiRequestCounter: Counter;
  private aiLatencyHistogram: Histogram;
  private aiQuotaGauge: Gauge;

  // Add backup metrics
  private backupMetrics = {
    backupDuration: new Histogram({
      name: 'backup_duration_seconds',
      help: 'Backup operation duration',
      labelNames: ['type']
    }),
    backupSize: new Gauge({
      name: 'backup_size_bytes',
      help: 'Backup size in bytes',
      labelNames: ['type']
    }),
    restoreDuration: new Histogram({
      name: 'restore_duration_seconds',
      help: 'Restore operation duration'
    })
  };

  // Add graph-specific metrics
  private graphMetrics = {
    nodeCount: new Gauge({
      name: 'graph_node_count',
      help: 'Total number of nodes by type',
      labelNames: ['type']
    }),
    relationshipCount: new Gauge({
      name: 'graph_relationship_count',
      help: 'Total number of relationships by type',
      labelNames: ['type']
    }),
    pathLength: new Histogram({
      name: 'graph_path_length',
      help: 'Path length distribution',
      labelNames: ['pattern_name']
    })
  };

  constructor() {
    // Initialize API metrics
    this.apiRequestCounter = new Counter({
      name: 'api_requests_total',
      help: 'Total number of API requests',
      labelNames: ['method', 'endpoint', 'status']
    });

    this.apiLatencyHistogram = new Histogram({
      name: 'api_request_duration_seconds',
      help: 'API request duration in seconds',
      labelNames: ['method', 'endpoint'],
      buckets: MetricsConfig.latencyBuckets
    });

    // Initialize Database metrics
    this.dbQueryCounter = new Counter({
      name: 'db_queries_total',
      help: 'Total number of database queries',
      labelNames: ['type', 'status']
    });

    this.dbQueryLatency = new Histogram({
      name: 'db_query_duration_seconds',
      help: 'Database query duration in seconds',
      labelNames: ['type'],
      buckets: MetricsConfig.latencyBuckets
    });

    // Initialize AI metrics
    this.aiRequestCounter = new Counter({
      name: 'ai_requests_total',
      help: 'Total number of AI service requests',
      labelNames: ['model', 'operation', 'status']
    });
  }

  recordAPIMetrics(method: string, endpoint: string, duration: number, status: number): void {
    this.apiRequestCounter.inc({ method, endpoint, status: status.toString() });
    this.apiLatencyHistogram.observe({ method, endpoint }, duration);
  }

  recordDBMetrics(queryType: string, duration: number, status: string): void {
    this.dbQueryCounter.inc({ type: queryType, status });
    this.dbQueryLatency.observe({ type: queryType }, duration);
  }
}
```

3. Prometheus Configuration
```yaml
# prometheus/prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'vitalyst_api'
    static_configs:
      - targets: ['localhost:3000']
    metrics_path: '/metrics'
    scheme: 'http'

  - job_name: 'neo4j'
    static_configs:
      - targets: ['localhost:2004']
    metrics_path: '/metrics'
    
  - job_name: 'node_exporter'
    static_configs:
      - targets: ['localhost:9100']

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['localhost:9093']
```

4. Grafana Dashboard Configuration
```typescript
// src/monitoring/dashboards/systemHealth.ts
export const systemHealthDashboard = {
  title: 'System Health Overview',
  panels: [
    {
      title: 'API Response Times',
      type: 'graph',
      gridPos: { x: 0, y: 0, w: 12, h: 8 },
      targets: [{
        expr: 'histogram_quantile(0.95, sum(rate(api_request_duration_seconds_bucket[5m])) by (le))',
        legendFormat: '95th percentile'
      }]
    },
    {
      title: 'Database Query Times',
      type: 'graph',
      gridPos: { x: 12, y: 0, w: 12, h: 8 },
      targets: [{
        expr: 'histogram_quantile(0.95, sum(rate(db_query_duration_seconds_bucket[5m])) by (le))',
        legendFormat: '95th percentile'
      }]
    },
    {
      title: 'AI Service Performance',
      type: 'graph',
      gridPos: { x: 0, y: 8, w: 12, h: 8 },
      targets: [{
        expr: 'rate(ai_requests_total{status="success"}[5m])',
        legendFormat: 'Successful requests/s'
      }]
    },
    {
      title: 'Backup Health',
      type: 'graph',
      gridPos: { x: 0, y: 16, w: 12, h: 8 },
      targets: [{
        expr: 'backup_duration_seconds',
        legendFormat: 'Backup Duration'
      }]
    },
    {
      title: 'Graph Health',
      type: 'graph',
      gridPos: { x: 12, y: 16, w: 12, h: 8 },
      targets: [{
        expr: 'graph_node_count',
        legendFormat: 'Node Count by Type'
      }]
    }
  ]
};
```

5. Alert Configuration
```typescript
// src/monitoring/alerts.ts
import { AlertManager } from './alertManager';
import { AlertRule, AlertSeverity } from '../types';

export class AlertConfiguration {
  private alertManager: AlertManager;

  constructor() {
    this.alertManager = new AlertManager();
    this.configureSystemAlerts();
  }

  private configureSystemAlerts(): void {
    // API Performance Alerts
    this.alertManager.addRule({
      name: 'high_api_latency',
      expr: 'histogram_quantile(0.95, sum(rate(api_request_duration_seconds_bucket[5m])) by (le)) > 1',
      severity: AlertSeverity.WARNING,
      annotations: {
        summary: 'High API latency detected',
        description: '95th percentile of API response time is above 1 second'
      }
    });

    // Database Health Alerts
    this.alertManager.addRule({
      name: 'database_connection_issues',
      expr: 'neo4j_connections_available < 5',
      severity: AlertSeverity.CRITICAL,
      annotations: {
        summary: 'Low database connections available',
        description: 'Neo4j connection pool is running low'
      }
    });

    // AI Service Alerts
    this.alertManager.addRule({
      name: 'ai_service_errors',
      expr: 'rate(ai_requests_total{status="error"}[5m]) > 0.1',
      severity: AlertSeverity.WARNING,
      annotations: {
        summary: 'High AI service error rate',
        description: 'AI service is experiencing elevated error rates'
      }
    });
  }

  private configureBackupAlerts(): void {
    this.alertManager.addRule({
      name: 'backup_failure',
      expr: 'increase(backup_failures_total[24h]) > 0',
      severity: AlertSeverity.CRITICAL,
      annotations: {
        summary: 'Backup failure detected',
        description: 'A backup operation has failed in the last 24 hours'
      }
    });
  }

  private configureGraphAlerts(): void {
    this.alertManager.addRule({
      name: 'high_node_growth_rate',
      expr: 'rate(graph_node_count[1h]) > 1000',
      severity: AlertSeverity.WARNING,
      annotations: {
        summary: 'High node growth rate detected',
        description: 'Node creation rate exceeds 1000 per hour'
      }
    });
  }
}
```

## Implementation Notes
1. Set up comprehensive health checks for all system components
2. Configure Prometheus for metrics collection
3. Create Grafana dashboards for visualization
4. Implement alerting rules and notifications
5. Monitor system resource utilization
6. Track custom business metrics
7. Implement logging integration

## Dependencies
- Prometheus
- Grafana
- Node Exporter
- AlertManager
- Logging infrastructure
- Metrics collection libraries

## Acceptance Criteria
1. All system components report health status
2. Metrics are collected and stored in Prometheus
3. Grafana dashboards provide clear system insights
4. Alerts are properly configured and triggered
5. Resource utilization is tracked
6. Custom business metrics are monitored
7. System provides early warning of potential issues

## Search Space Organization
```
src/
├── monitoring/
│   ├── core/
│   │   ├── healthCheck.ts
│   │   ├── metrics.ts
│   │   └── alerts.ts
│   ├── components/
│   │   ├── api/
│   │   │   ├── apiMetrics.ts
│   │   │   └── apiHealth.ts
│   │   ├── database/
│   │   │   ├── dbMetrics.ts
│   │   │   └── dbHealth.ts
│   │   ├── ai/
│   │   │   ├── aiMetrics.ts
│   │   │   └── aiHealth.ts
│   │   └── cache/
│   │       ├── cacheMetrics.ts
│   │       └── cacheHealth.ts
│   ├── integrations/
│   │   ├── backup/
│   │   │   ├── backupMetrics.ts
│   │   │   └── backupHealth.ts
│   │   └── graph/
│   │       ├── graphMetrics.ts
│   │       └── graphHealth.ts
│   └── visualization/
│       ├── dashboards/
│       │   ├── system.ts
│       │   ├── performance.ts
│       │   └── business.ts
│       └── alerts/
│           ├── rules.ts
│           └── notifications.ts
└── types/
    ├── metrics.ts
    ├── health.ts
    └── alerts.ts
```

## Additional Implementation Notes
12. Implement backup monitoring integration
13. Add graph-specific health checks
14. Optimize search space organization
15. Enhance visualization components

## Extended Dependencies
- Backup monitoring system
- Graph metrics collector
- Enhanced visualization tools
- Advanced alerting system

## Additional Acceptance Criteria
8. Backup monitoring metrics are collected
9. Graph health metrics are tracked
10. Search space is optimally organized
11. Advanced visualizations are implemented
