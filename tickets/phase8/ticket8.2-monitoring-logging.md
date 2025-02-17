# Ticket 8.2: Setup Monitoring and Logging Tools

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive monitoring and logging system for the Vitalyst Knowledge Graph that integrates Prometheus for metrics collection, Grafana for visual dashboards, and structured JSON logging. The system must provide real-time insights into application performance, resource utilization, and system health as specified in the blueprint.

## Technical Details
1. Prometheus Integration Implementation
```python
# src/monitoring/prometheus_metrics.py
from prometheus_client import Counter, Histogram, Gauge, Info
from prometheus_client.exposition import generate_latest
from fastapi import FastAPI, Response
from typing import Dict
import time

class PrometheusMetrics:
    def __init__(self, app: FastAPI):
        self.app = app
        self.setup_metrics()
        self.setup_routes()

    def setup_metrics(self):
        # Request metrics
        self.request_counter = Counter(
            'http_requests_total',
            'Total HTTP requests',
            ['method', 'endpoint', 'status']
        )
        self.request_latency = Histogram(
            'http_request_duration_seconds',
            'HTTP request latency',
            ['method', 'endpoint']
        )

        # Resource metrics
        self.memory_usage = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes'
        )
        self.cpu_usage = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage'
        )

        # Business metrics
        self.node_count = Gauge(
            'graph_nodes_total',
            'Total number of nodes in the graph',
            ['type']
        )
        self.enrichment_counter = Counter(
            'ai_enrichments_total',
            'Total AI enrichment operations',
            ['status']
        )
        self.validation_gauge = Gauge(
            'validation_queue_size',
            'Number of items in validation queue'
        )

        # Version info
        self.version_info = Info(
            'application_info',
            'Application version information'
        )

    def setup_routes(self):
        @self.app.get("/metrics")
        async def metrics():
            return Response(
                generate_latest(),
                media_type="text/plain"
            )

    async def track_request(
        self,
        method: str,
        endpoint: str,
        status: int,
        duration: float
    ):
        """Track HTTP request metrics"""
        self.request_counter.labels(
            method=method,
            endpoint=endpoint,
            status=status
        ).inc()
        
        self.request_latency.labels(
            method=method,
            endpoint=endpoint
        ).observe(duration)

    async def update_resource_metrics(
        self,
        memory: float,
        cpu: float
    ):
        """Update resource utilization metrics"""
        self.memory_usage.set(memory)
        self.cpu_usage.set(cpu)

    async def update_graph_metrics(
        self,
        node_counts: Dict[str, int]
    ):
        """Update graph-related metrics"""
        for node_type, count in node_counts.items():
            self.node_count.labels(type=node_type).set(count)

    async def track_enrichment(self, status: str):
        """Track AI enrichment operations"""
        self.enrichment_counter.labels(status=status).inc()

    async def update_validation_queue(self, size: int):
        """Update validation queue size"""
        self.validation_gauge.set(size)
```

2. Grafana Dashboard Implementation
```yaml
# src/monitoring/dashboards/system_health.json
{
  "dashboard": {
    "id": null,
    "title": "Vitalyst System Health",
    "tags": ["vitalyst", "production"],
    "timezone": "browser",
    "panels": [
      {
        "title": "HTTP Request Rate",
        "type": "graph",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "rate(http_requests_total[5m])",
            "legendFormat": "{{method}} {{endpoint}}"
          }
        ]
      },
      {
        "title": "Request Latency",
        "type": "heatmap",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "rate(http_request_duration_seconds_bucket[5m])",
            "format": "heatmap"
          }
        ]
      },
      {
        "title": "Resource Usage",
        "type": "gauge",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "cpu_usage_percent",
            "legendFormat": "CPU Usage"
          },
          {
            "expr": "memory_usage_bytes / 1024 / 1024",
            "legendFormat": "Memory Usage (MB)"
          }
        ]
      },
      {
        "title": "Graph Metrics",
        "type": "stat",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "graph_nodes_total",
            "legendFormat": "{{type}} Nodes"
          }
        ]
      },
      {
        "title": "AI Enrichment Success Rate",
        "type": "gauge",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "sum(rate(ai_enrichments_total{status='success'}[5m])) / sum(rate(ai_enrichments_total[5m]))",
            "legendFormat": "Success Rate"
          }
        ]
      }
    ]
  }
}
```

3. Structured Logging Implementation
```python
# src/logging/structured_logger.py
import logging
import json
from datetime import datetime
from typing import Any, Dict, Optional
import traceback
import sys

class StructuredLogger:
    def __init__(
        self,
        service_name: str,
        log_level: str = "INFO"
    ):
        self.service_name = service_name
        self.logger = logging.getLogger(service_name)
        self.logger.setLevel(getattr(logging, log_level))
        
        # Configure JSON formatter
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(self.JsonFormatter())
        self.logger.addHandler(handler)

    class JsonFormatter(logging.Formatter):
        def format(self, record: logging.LogRecord) -> str:
            log_data = {
                "timestamp": datetime.utcnow().isoformat(),
                "level": record.levelname,
                "service": record.name,
                "message": record.getMessage(),
                "logger": record.name
            }

            # Add extra fields if available
            if hasattr(record, "extra"):
                log_data.update(record.extra)

            # Add exception info if available
            if record.exc_info:
                log_data["exception"] = {
                    "type": record.exc_info[0].__name__,
                    "message": str(record.exc_info[1]),
                    "stacktrace": traceback.format_exception(
                        *record.exc_info
                    )
                }

            # Add request info if available
            if hasattr(record, "request"):
                log_data["request"] = {
                    "method": record.request.get("method"),
                    "path": record.request.get("path"),
                    "ip": record.request.get("ip"),
                    "user_agent": record.request.get("user_agent")
                }

            return json.dumps(log_data)

    def log(
        self,
        level: str,
        message: str,
        extra: Optional[Dict[str, Any]] = None
    ):
        """Log a message with optional extra data"""
        log_method = getattr(self.logger, level.lower())
        log_method(message, extra=extra or {})

    def info(self, message: str, **kwargs):
        self.log("INFO", message, kwargs)

    def error(self, message: str, **kwargs):
        self.log("ERROR", message, kwargs)

    def warning(self, message: str, **kwargs):
        self.log("WARNING", message, kwargs)

    def debug(self, message: str, **kwargs):
        self.log("DEBUG", message, kwargs)

    def request_log(
        self,
        request: Dict[str, Any],
        response: Dict[str, Any],
        duration: float
    ):
        """Log HTTP request details"""
        self.info(
            f"HTTP {request['method']} {request['path']}",
            request={
                "method": request["method"],
                "path": request["path"],
                "ip": request.get("ip"),
                "user_agent": request.get("user_agent")
            },
            response={
                "status": response["status"],
                "duration": duration
            }
        )
```

4. Alert Configuration Implementation
```yaml
# src/monitoring/alerts/rules.yml
groups:
  - name: application_alerts
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{status=~"5.."}[5m]) / rate(http_requests_total[5m]) > 0.05
        for: 5m
        labels:
          severity: critical
        annotations:
          description: "Error rate above 5% for 5 minutes"

      - alert: HighLatency
        expr: histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[5m])) > 1
        for: 5m
        labels:
          severity: warning
        annotations:
          description: "95th percentile latency above 1s"

      - alert: HighMemoryUsage
        expr: memory_usage_bytes / 1024 / 1024 / 1024 > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          description: "Memory usage above 85%"

      - alert: HighCPUUsage
        expr: cpu_usage_percent > 80
        for: 5m
        labels:
          severity: warning
        annotations:
          description: "CPU usage above 80%"

      - alert: LowValidationRate
        expr: validation_queue_size > 100
        for: 10m
        labels:
          severity: warning
        annotations:
          description: "Validation queue size above 100 for 10 minutes"

      - alert: AIEnrichmentFailures
        expr: rate(ai_enrichments_total{status="failed"}[5m]) > 0
        for: 5m
        labels:
          severity: warning
        annotations:
          description: "AI enrichment failures detected"
```

5. Performance Monitoring Implementation
```python
# src/monitoring/performance.py
from typing import Dict, List, Optional
import psutil
import time
from prometheus_client import Histogram, Gauge

class PerformanceMonitor:
    def __init__(self):
        # CPU metrics
        self.cpu_usage = Gauge(
            'cpu_usage_percent',
            'CPU usage percentage',
            ['core']
        )
        self.cpu_load = Gauge(
            'cpu_load_average',
            'CPU load average',
            ['interval']
        )

        # Memory metrics
        self.memory_usage = Gauge(
            'memory_usage_bytes',
            'Memory usage in bytes',
            ['type']
        )
        self.memory_allocation = Histogram(
            'memory_allocation_bytes',
            'Memory allocation sizes',
            ['service'],
            buckets=[1024, 10*1024, 100*1024, 1024*1024]
        )

        # Disk metrics
        self.disk_usage = Gauge(
            'disk_usage_bytes',
            'Disk usage in bytes',
            ['mount', 'type']
        )
        self.disk_io = Gauge(
            'disk_io_operations',
            'Disk I/O operations',
            ['operation']
        )

        # Network metrics
        self.network_io = Gauge(
            'network_io_bytes',
            'Network I/O in bytes',
            ['interface', 'direction']
        )
        self.network_connections = Gauge(
            'network_connections',
            'Active network connections',
            ['state']
        )

    async def collect_metrics(self):
        """Collect all performance metrics"""
        # CPU metrics
        for i, percentage in enumerate(psutil.cpu_percent(percpu=True)):
            self.cpu_usage.labels(core=f'core_{i}').set(percentage)

        load1, load5, load15 = psutil.getloadavg()
        self.cpu_load.labels(interval='1m').set(load1)
        self.cpu_load.labels(interval='5m').set(load5)
        self.cpu_load.labels(interval='15m').set(load15)

        # Memory metrics
        memory = psutil.virtual_memory()
        self.memory_usage.labels(type='total').set(memory.total)
        self.memory_usage.labels(type='available').set(memory.available)
        self.memory_usage.labels(type='used').set(memory.used)

        # Disk metrics
        for partition in psutil.disk_partitions():
            usage = psutil.disk_usage(partition.mountpoint)
            self.disk_usage.labels(
                mount=partition.mountpoint,
                type='total'
            ).set(usage.total)
            self.disk_usage.labels(
                mount=partition.mountpoint,
                type='used'
            ).set(usage.used)

        # Network metrics
        network = psutil.net_io_counters()
        self.network_io.labels(
            interface='all',
            direction='bytes_sent'
        ).set(network.bytes_sent)
        self.network_io.labels(
            interface='all',
            direction='bytes_recv'
        ).set(network.bytes_recv)
```

6. Log Aggregation Implementation
```python
# src/logging/aggregator.py
from elasticsearch import AsyncElasticsearch
from typing import Dict, List
import json
import asyncio

class LogAggregator:
    def __init__(
        self,
        es_client: AsyncElasticsearch,
        index_prefix: str = "vitalyst-logs"
    ):
        self.es = es_client
        self.index_prefix = index_prefix
        self.buffer = []
        self.buffer_size = 100
        self.flush_interval = 5  # seconds

    async def start(self):
        """Start the log aggregation process"""
        asyncio.create_task(self._periodic_flush())

    async def add_log(self, log_entry: Dict):
        """Add a log entry to the buffer"""
        self.buffer.append({
            "@timestamp": log_entry.get("timestamp", datetime.utcnow().isoformat()),
            "service": log_entry.get("service", "unknown"),
            "level": log_entry.get("level", "INFO"),
            "message": log_entry.get("message"),
            "metadata": log_entry.get("metadata", {}),
            "trace_id": log_entry.get("trace_id"),
            "span_id": log_entry.get("span_id")
        })

        if len(self.buffer) >= self.buffer_size:
            await self.flush()

    async def flush(self):
        """Flush the log buffer to Elasticsearch"""
        if not self.buffer:
            return

        try:
            # Prepare bulk request
            bulk_data = []
            for log in self.buffer:
                bulk_data.extend([
                    {"index": {"_index": f"{self.index_prefix}-{datetime.now():%Y.%m.%d}"}},
                    log
                ])

            # Send bulk request
            await self.es.bulk(body=bulk_data)
            self.buffer.clear()

        except Exception as e:
            logger.error(f"Failed to flush logs: {str(e)}")

    async def _periodic_flush(self):
        """Periodically flush the log buffer"""
        while True:
            await asyncio.sleep(self.flush_interval)
            await self.flush()
```

## Implementation Strategy
1. Metrics Collection
   - Implement Prometheus integration
   - Set up custom metrics
   - Configure resource monitoring
   - Implement business metrics
   - Set up performance tracking

2. Logging System
   - Implement structured logging
   - Set up log aggregation
   - Configure log rotation
   - Implement audit logging
   - Set up log analysis

3. Monitoring Setup
   - Configure Grafana dashboards
   - Set up alerting rules
   - Implement health checks
   - Configure performance monitoring
   - Set up system metrics

4. Integration
   - Implement service monitoring
   - Set up distributed tracing
   - Configure error tracking
   - Implement audit trails
   - Set up security monitoring

## Acceptance Criteria
- [ ] Prometheus metrics collection implemented and verified
- [ ] Grafana dashboards configured and functional
- [ ] JSON-formatted logging system operational
- [ ] Resource utilization monitoring active
- [ ] API metrics tracking implemented
- [ ] Business metrics collection working
- [ ] Alert configuration and notification system active
- [ ] Performance monitoring and tracking operational
- [ ] Log aggregation and analysis working
- [ ] Distributed tracing implemented
- [ ] Health check system operational
- [ ] Security monitoring active
- [ ] Documentation completed
- [ ] All monitoring tests passing

## Dependencies
- Ticket 8.1: Docker Deployments
- Ticket 3.1: Backend Setup
- Ticket 4.1: Frontend Setup
- Ticket 3.3: Zero-Trust Security

## Estimated Hours
35

## Testing Requirements
- Metrics Tests
  - Test metrics collection
  - Verify metric accuracy
  - Test custom metrics
  - Validate business metrics
  - Check performance metrics

- Logging Tests
  - Test log formatting
  - Verify log aggregation
  - Test log rotation
  - Validate audit logging
  - Check log analysis

- Monitoring Tests
  - Test alert triggers
  - Verify dashboard updates
  - Test health checks
  - Validate system metrics
  - Check distributed tracing

- Integration Tests
  - Test service monitoring
  - Verify error tracking
  - Test audit trails
  - Validate security monitoring
  - Check performance tracking

- Load Tests
  - Test high-volume logging
  - Verify metrics under load
  - Test alert responsiveness
  - Validate system performance
  - Check resource utilization

## Documentation
- Monitoring Architecture
  - System overview
  - Component integration
  - Data flow diagrams
  - Security considerations
  - Scaling guidelines

- Metrics Guide
  - Available metrics
  - Custom metrics
  - Collection methods
  - Performance impact
  - Best practices

- Logging Guide
  - Log format specification
  - Aggregation setup
  - Analysis tools
  - Retention policies
  - Security measures

- Alert Configuration
  - Alert rules
  - Notification setup
  - Escalation procedures
  - Response guidelines
  - Maintenance procedures

- Operations Guide
  - Monitoring procedures
  - Troubleshooting steps
  - Performance tuning
  - Capacity planning
  - Disaster recovery

## Search Space Optimization
- Clear Metric Organization
  - System metrics
  - Business metrics
  - Performance metrics
  - Security metrics
  - Custom metrics

- Structured Logging Hierarchy
  - Application logs
  - Access logs
  - Audit logs
  - Error logs
  - Performance logs

- Monitoring Categories
  - System health
  - Application performance
  - Business operations
  - Security events
  - Resource utilization

- Alert Classification
  - Critical alerts
  - Warning alerts
  - Information alerts
  - Security alerts
  - Performance alerts

## References
- Blueprint Section 9: Frameworks, Deployment, Security & Monitoring
- Blueprint Section 8: Monitoring and Logging
- Blueprint Section 6: Security Requirements
- Prometheus Documentation
- Grafana Best Practices
- ELK Stack Documentation
- Distributed Tracing Guidelines
- Zero-Trust Monitoring Patterns

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the monitoring and logging system as specified in the blueprint, with particular attention to:
- Comprehensive metrics collection
- Visual dashboard implementation
- Structured logging system
- Performance monitoring
- Resource tracking
- Alert configuration
- Security monitoring
- Distributed tracing
- Audit logging
- System health monitoring 