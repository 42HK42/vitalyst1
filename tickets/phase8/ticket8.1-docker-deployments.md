# Ticket 8.1: Finalize Docker Deployments

## Priority
High

## Type
Development

## Status
To Do

## Description
Refine and finalize Docker deployment configurations for the Vitalyst Knowledge Graph, ensuring seamless communication between services and proper environment scaling. The implementation must include production-ready Dockerfiles, optimized docker-compose configurations, comprehensive deployment documentation, and zero-trust security principles as specified in the blueprint.

## Technical Details
1. Production Dockerfile Implementation
```dockerfile
# Backend Dockerfile.prod
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Create non-root user
RUN useradd -m -r -s /bin/bash vitalyst && \
    chown -R vitalyst:vitalyst /app

USER vitalyst

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000"]

# Frontend Dockerfile.prod
FROM node:18-alpine as builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy application code
COPY . .

# Build application
RUN npm run build

# Production stage
FROM node:18-alpine

WORKDIR /app

# Copy built assets from builder
COPY --from=builder /app/dist ./dist
COPY --from=builder /app/package*.json ./

# Install production dependencies only
RUN npm ci --only=production

# Create non-root user
RUN addgroup -S vitalyst && \
    adduser -S vitalyst -G vitalyst && \
    chown -R vitalyst:vitalyst /app

USER vitalyst

EXPOSE 3000

CMD ["npm", "start"]
```

2. Docker Compose Configuration
```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.prod
    image: vitalyst/backend:${VERSION:-latest}
    restart: unless-stopped
    environment:
      - NODE_ENV=production
      - DATABASE_URL=${DATABASE_URL}
      - REDIS_URL=${REDIS_URL}
      - AUTH0_DOMAIN=${AUTH0_DOMAIN}
      - AUTH0_AUDIENCE=${AUTH0_AUDIENCE}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      replicas: 3
      update_config:
        parallelism: 1
        delay: 10s
      restart_policy:
        condition: on-failure
    networks:
      - vitalyst-network
    depends_on:
      - neo4j
      - redis

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.prod
    image: vitalyst/frontend:${VERSION:-latest}
    restart: unless-stopped
    environment:
      - NODE_ENV=production
      - API_URL=${API_URL}
      - AUTH0_DOMAIN=${AUTH0_DOMAIN}
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      replicas: 2
      update_config:
        parallelism: 1
        delay: 10s
    networks:
      - vitalyst-network
    depends_on:
      - backend

  neo4j:
    image: neo4j:5.9.0
    restart: unless-stopped
    environment:
      - NEO4J_AUTH=${NEO4J_AUTH}
      - NEO4J_dbms_memory_heap_max__size=4G
      - NEO4J_dbms_memory_pagecache_size=2G
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:7474 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 8G
    networks:
      - vitalyst-network

  redis:
    image: redis:7.0-alpine
    restart: unless-stopped
    command: redis-server --requirepass ${REDIS_PASSWORD}
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    deploy:
      resources:
        limits:
          memory: 1G
    networks:
      - vitalyst-network

networks:
  vitalyst-network:
    driver: overlay
    attachable: true

volumes:
  neo4j-data:
  neo4j-logs:
  redis-data:
```

3. Deployment Script Implementation
```python
# src/scripts/deploy.py
import subprocess
import os
import sys
from typing import List, Dict
import yaml
import logging
from datetime import datetime

class DeploymentManager:
    def __init__(self):
        self.logger = self.setup_logger()
        self.env = os.getenv('DEPLOYMENT_ENV', 'production')
        self.stack_name = f"vitalyst-{self.env}"

    def setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('deployment')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger

    def deploy(self) -> bool:
        """Execute deployment process"""
        try:
            # Validate environment
            if not self.validate_environment():
                return False

            # Build images
            if not self.build_images():
                return False

            # Deploy stack
            if not self.deploy_stack():
                return False

            # Verify deployment
            if not self.verify_deployment():
                self.rollback()
                return False

            self.logger.info("Deployment completed successfully")
            return True

        except Exception as e:
            self.logger.error(f"Deployment failed: {str(e)}")
            self.rollback()
            return False

    def validate_environment(self) -> bool:
        """Validate deployment environment"""
        required_vars = [
            'DATABASE_URL',
            'REDIS_URL',
            'AUTH0_DOMAIN',
            'AUTH0_AUDIENCE',
            'NEO4J_AUTH',
            'REDIS_PASSWORD'
        ]

        missing_vars = [var for var in required_vars if not os.getenv(var)]
        
        if missing_vars:
            self.logger.error(
                f"Missing required environment variables: {', '.join(missing_vars)}"
            )
            return False

        return True

    def build_images(self) -> bool:
        """Build Docker images"""
        try:
            version = datetime.now().strftime('%Y%m%d_%H%M%S')
            os.environ['VERSION'] = version

            services = ['backend', 'frontend']
            for service in services:
                self.logger.info(f"Building {service} image...")
                result = subprocess.run([
                    'docker', 'compose',
                    '-f', 'docker-compose.prod.yml',
                    'build', service
                ], check=True)

                if result.returncode != 0:
                    self.logger.error(f"Failed to build {service} image")
                    return False

            return True

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Build failed: {str(e)}")
            return False

    def deploy_stack(self) -> bool:
        """Deploy Docker stack"""
        try:
            self.logger.info(f"Deploying stack {self.stack_name}...")
            result = subprocess.run([
                'docker', 'stack', 'deploy',
                '-c', 'docker-compose.prod.yml',
                self.stack_name
            ], check=True)

            return result.returncode == 0

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Stack deployment failed: {str(e)}")
            return False

    def verify_deployment(self) -> bool:
        """Verify deployment status"""
        try:
            # Check service health
            services = ['backend', 'frontend', 'neo4j', 'redis']
            for service in services:
                if not self.check_service_health(f"{self.stack_name}_{service}"):
                    self.logger.error(f"Service {service} is unhealthy")
                    return False

            # Verify connectivity
            if not self.verify_connectivity():
                return False

            return True

        except Exception as e:
            self.logger.error(f"Verification failed: {str(e)}")
            return False

    def rollback(self) -> None:
        """Rollback deployment"""
        try:
            self.logger.info("Rolling back deployment...")
            subprocess.run([
                'docker', 'stack', 'rm',
                self.stack_name
            ], check=True)

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Rollback failed: {str(e)}")
```

4. Security Configuration Implementation
```yaml
# security/container-security.yml
securityContext:
  runAsNonRoot: true
  runAsUser: 1000
  readOnlyRootFilesystem: true
  allowPrivilegeEscalation: false
  capabilities:
    drop: ["ALL"]

networkPolicy:
  ingress:
    - from:
        - podSelector:
            matchLabels:
              app: vitalyst
    - ports:
        - protocol: TCP
          port: 8000
```

5. Monitoring Configuration
```yaml
# monitoring/prometheus-rules.yml
groups:
  - name: container_alerts
    rules:
      - alert: ContainerHighCPU
        expr: container_cpu_usage_seconds_total > 0.8
        for: 5m
        labels:
          severity: warning
        annotations:
          description: "Container {{ $labels.container }} CPU usage above 80%"

      - alert: ContainerHighMemory
        expr: container_memory_usage_bytes > 0.85
        for: 5m
        labels:
          severity: warning
        annotations:
          description: "Container {{ $labels.container }} memory usage above 85%"

      - alert: ContainerRestarting
        expr: rate(container_restart_count[5m]) > 0
        for: 2m
        labels:
          severity: warning
        annotations:
          description: "Container {{ $labels.container }} restarting frequently"
```

6. Performance Optimization
```yaml
# performance/tuning.yml
resources:
  backend:
    limits:
      cpu: "2"
      memory: "4Gi"
    requests:
      cpu: "500m"
      memory: "1Gi"
  frontend:
    limits:
      cpu: "1"
      memory: "2Gi"
    requests:
      cpu: "200m"
      memory: "512Mi"
  neo4j:
    limits:
      cpu: "4"
      memory: "8Gi"
    requests:
      cpu: "2"
      memory: "4Gi"

caching:
  redis:
    maxmemory: "1gb"
    maxmemory-policy: "allkeys-lru"
    save:
      - seconds: 900
        changes: 1
      - seconds: 300
        changes: 10
      - seconds: 60
        changes: 10000
```

7. Deployment Strategy Implementation
```yaml
# deployment/strategy.yml
strategy:
  type: RollingUpdate
  rollingUpdate:
    maxSurge: 1
    maxUnavailable: 0
  minReadySeconds: 30
  revisionHistoryLimit: 10

readinessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 15
  periodSeconds: 10
  timeoutSeconds: 5
  successThreshold: 1
  failureThreshold: 3

livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 20
  timeoutSeconds: 5
  successThreshold: 1
  failureThreshold: 3
```

## Implementation Strategy
1. Security Hardening
   - Implement container security policies
   - Configure network policies
   - Set up secret management
   - Implement access controls
   - Configure audit logging

2. Performance Optimization
   - Configure resource limits
   - Implement caching strategy
   - Optimize container builds
   - Set up performance monitoring
   - Configure auto-scaling

3. Monitoring Integration
   - Set up Prometheus metrics
   - Configure Grafana dashboards
   - Implement alert rules
   - Set up log aggregation
   - Configure tracing

4. Deployment Automation
   - Implement rolling updates
   - Configure health checks
   - Set up rollback procedures
   - Implement blue-green deployments
   - Configure CI/CD integration

## Acceptance Criteria
- [ ] Production-ready Dockerfile implementations with security hardening
- [ ] Optimized docker-compose configuration with resource management
- [ ] Service health checks and comprehensive monitoring
- [ ] Environment-specific configurations with proper isolation
- [ ] Automated deployment scripts with rollback capabilities
- [ ] Resource allocation and auto-scaling configuration
- [ ] Zero-trust security implementation with audit logging
- [ ] Performance optimization with caching strategy
- [ ] Monitoring integration with alerting
- [ ] Deployment strategies with zero-downtime updates
- [ ] Comprehensive documentation and runbooks
- [ ] Disaster recovery procedures
- [ ] Load testing and performance benchmarks
- [ ] Security scanning and compliance checks

## Dependencies
- Ticket 3.1: Backend Setup
- Ticket 4.1: Frontend Setup
- Ticket 8.2: Monitoring & Logging
- Ticket 8.3: CI/CD Pipelines
- Ticket 3.3: Zero-Trust Security

## Estimated Hours
40

## Testing Requirements
- Security Tests:
  - Test container isolation
  - Verify network policies
  - Validate access controls
  - Test secret management
  - Verify audit logging
  - Test compliance requirements

- Performance Tests:
  - Measure container startup
  - Test resource utilization
  - Verify scaling efficiency
  - Benchmark caching
  - Test under load
  - Measure latency

- Integration Tests:
  - Test service communication
  - Verify monitoring integration
  - Test deployment strategies
  - Validate rollbacks
  - Test auto-scaling
  - Verify zero-downtime updates

- Disaster Recovery Tests:
  - Test backup procedures
  - Verify restore operations
  - Test failover scenarios
  - Validate data consistency
  - Test recovery time
  - Verify service resilience

## Documentation
- Deployment Architecture
  - Container architecture
  - Network topology
  - Security measures
  - Monitoring setup
  - Scaling strategy

- Operational Procedures
  - Deployment guide
  - Scaling procedures
  - Backup and restore
  - Incident response
  - Performance tuning

- Security Documentation
  - Security policies
  - Access controls
  - Audit procedures
  - Compliance requirements
  - Incident handling

- Monitoring Guide
  - Metrics collection
  - Dashboard setup
  - Alert configuration
  - Log aggregation
  - Performance monitoring

## Search Space Optimization
- Clear Container Organization
  - Service-based structure
  - Environment separation
  - Consistent naming
  - Logical grouping
  - Version control

- Configuration Management
  - Environment configs
  - Security policies
  - Resource limits
  - Monitoring rules
  - Deployment strategies

- Documentation Structure
  - Architecture docs
  - Operation guides
  - Security policies
  - Monitoring setup
  - Troubleshooting

## References
- Blueprint Section 9: Frameworks, Deployment, Security & Monitoring
- Blueprint Section 6: Security Requirements
- Blueprint Section 8: Monitoring and Logging
- Docker Security Best Practices
- Kubernetes Deployment Patterns
- Zero-Trust Architecture Guidelines
- Container Monitoring Best Practices
- Performance Optimization Guides

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the Docker deployment configuration as specified in the blueprint, with particular attention to:
- Zero-trust security implementation
- Comprehensive monitoring integration
- Resource optimization and scaling
- Deployment automation and reliability
- Performance optimization and caching
- Service resilience and recovery
- Documentation and operational procedures