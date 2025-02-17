# Ticket 2.1: Deploy Neo4j Database

## Priority
High

## Type
Infrastructure

## Status
To Do

## Description
Deploy and configure a production-ready Neo4j database cluster with high availability, automated backups, comprehensive monitoring, and security hardening. The implementation must follow zero-trust security principles and ensure data integrity while maintaining optimal performance as specified in the blueprint.

## Technical Details

1. Neo4j Docker Compose Configuration
```yaml
# docker-compose.yml
version: '3.8'

services:
  neo4j-core:
    image: neo4j:5.7-enterprise
    container_name: neo4j-core
    environment:
      # Core Configuration
      NEO4J_AUTH: ${NEO4J_USER}/${NEO4J_PASSWORD}
      NEO4J_ACCEPT_LICENSE_AGREEMENT: 'yes'
      NEO4J_server_memory_heap_initial__size: 2G
      NEO4J_server_memory_heap_max__size: 4G
      NEO4J_server_memory_pagecache_size: 2G
      
      # Security Configuration
      NEO4J_dbms_security_procedures_unrestricted: "apoc.*"
      NEO4J_dbms_security_auth__enabled: "true"
      NEO4J_dbms_ssl_policy_bolt_enabled: "true"
      NEO4J_dbms_ssl_policy_bolt_base__directory: "/ssl/bolt"
      NEO4J_dbms_ssl_policy_https_enabled: "true"
      NEO4J_dbms_ssl_policy_https_base__directory: "/ssl/https"
      
      # Clustering Configuration
      NEO4J_causal__clustering_initial__discovery__members: neo4j-core:5000,neo4j-replica-1:5000,neo4j-replica-2:5000
      NEO4J_causal__clustering_minimum__core__cluster__size__at__formation: 3
      NEO4J_causal__clustering_minimum__core__cluster__size__at__runtime: 2
      
      # Monitoring Configuration
      NEO4J_metrics_enabled: "true"
      NEO4J_metrics_prometheus_enabled: "true"
      NEO4J_metrics_jmx_enabled: "true"
      
      # Backup Configuration
      NEO4J_dbms_backup_enabled: "true"
      NEO4J_dbms_backup_address: 0.0.0.0:6362
    ports:
      - "7474:7474"  # HTTP
      - "7473:7473"  # HTTPS
      - "7687:7687"  # Bolt
      - "6362:6362"  # Backup
    volumes:
      - neo4j_data:/data
      - neo4j_logs:/logs
      - neo4j_plugins:/plugins
      - neo4j_ssl:/ssl
      - neo4j_metrics:/metrics
    networks:
      - neo4j_network
    healthcheck:
      test: ["CMD-SHELL", "wget --no-verbose --tries=1 --spider http://localhost:7474/browser/ || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 60s
    deploy:
      resources:
        limits:
          cpus: '4'
          memory: 8G
        reservations:
          cpus: '2'
          memory: 4G

  neo4j-replica-1:
    image: neo4j:5.7-enterprise
    container_name: neo4j-replica-1
    # Similar configuration as core with replica-specific settings
    depends_on:
      - neo4j-core

  neo4j-replica-2:
    image: neo4j:5.7-enterprise
    container_name: neo4j-replica-2
    # Similar configuration as core with replica-specific settings
    depends_on:
      - neo4j-core

  neo4j-backup:
    image: alpine:latest
    container_name: neo4j-backup
    volumes:
      - neo4j_backups:/backups
    command: |
      /bin/sh -c "
        while true; do
          neo4j-admin backup --backup-dir=/backups/\$(date +%Y%m%d) --name=graph.db
          find /backups -mtime +7 -type d -exec rm -rf {} +
          sleep 86400
        done
      "
    depends_on:
      - neo4j-core

  prometheus:
    image: prom/prometheus:latest
    container_name: neo4j-prometheus
    volumes:
      - ./prometheus.yml:/etc/prometheus/prometheus.yml
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
    ports:
      - "9090:9090"

  grafana:
    image: grafana/grafana:latest
    container_name: neo4j-grafana
    environment:
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD}
    volumes:
      - grafana_data:/var/lib/grafana
      - ./grafana/provisioning:/etc/grafana/provisioning
    ports:
      - "3000:3000"
    depends_on:
      - prometheus

volumes:
  neo4j_data:
  neo4j_logs:
  neo4j_plugins:
  neo4j_ssl:
  neo4j_metrics:
  neo4j_backups:
  prometheus_data:
  grafana_data:

networks:
  neo4j_network:
    driver: overlay
    attachable: true
```

2. Database Schema and Constraints
```cypher
// Core Constraints
CREATE CONSTRAINT IF NOT EXISTS FOR (n:BaseNode) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:BaseNode) REQUIRE n.created_at IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:BaseNode) REQUIRE n.updated_at IS NOT NULL;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:BaseNode) REQUIRE n.version IS NOT NULL;

// Type-specific Constraints
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Food) REQUIRE n.name IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Nutrient) REQUIRE n.vitID IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Source) REQUIRE n.url IS UNIQUE;

// Indexes for Performance
CREATE INDEX IF NOT EXISTS FOR (n:BaseNode) ON (n.type);
CREATE INDEX IF NOT EXISTS FOR (n:BaseNode) ON (n.status);
CREATE INDEX IF NOT EXISTS FOR (n:Food) ON (n.category);
CREATE INDEX IF NOT EXISTS FOR (n:Nutrient) ON (n.group);
CREATE INDEX IF NOT EXISTS FOR (n:Source) ON (n.reliability);

// Full-text Indexes
CALL db.index.fulltext.createNodeIndex(
  'nodeSearch',
  ['Food', 'Nutrient'],
  ['name', 'description']
);
```

3. Security Configuration
```yaml
# config/neo4j.conf
dbms.security.auth_enabled=true
dbms.security.procedures.unrestricted=apoc.*
dbms.security.procedures.whitelist=apoc.coll.*,apoc.load.*
dbms.ssl.policy.bolt.enabled=true
dbms.ssl.policy.bolt.client_auth=REQUIRE
dbms.ssl.policy.https.enabled=true
dbms.connector.bolt.tls_level=REQUIRED

# RBAC Configuration
CALL dbms.security.createRole('reader', 'Reader role for read-only access')
CALL dbms.security.createRole('editor', 'Editor role for data modification')
CALL dbms.security.createRole('admin', 'Admin role for full access')

CALL dbms.security.addRoleToUser('reader', 'neo4j_reader')
CALL dbms.security.addRoleToUser('editor', 'neo4j_editor')
CALL dbms.security.addRoleToUser('admin', 'neo4j_admin')

GRANT MATCH {*} ON GRAPH * NODES * TO reader
GRANT MATCH {*} ON GRAPH * RELATIONSHIPS * TO reader
GRANT CREATE, DELETE ON GRAPH * TO editor
GRANT ALL ON GRAPH * TO admin
```

4. Monitoring Configuration
```yaml
# prometheus.yml
global:
  scrape_interval: 15s
  evaluation_interval: 15s

scrape_configs:
  - job_name: 'neo4j'
    static_configs:
      - targets: ['neo4j-core:2004', 'neo4j-replica-1:2004', 'neo4j-replica-2:2004']
    metrics_path: /metrics
    scheme: http

# Grafana Dashboard Definition
{
  "dashboard": {
    "id": null,
    "title": "Neo4j Metrics",
    "panels": [
      {
        "title": "Active Transactions",
        "type": "graph",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "neo4j_active_transactions"
          }
        ]
      },
      {
        "title": "Memory Usage",
        "type": "gauge",
        "datasource": "Prometheus",
        "targets": [
          {
            "expr": "neo4j_memory_usage_bytes"
          }
        ]
      }
    ]
  }
}
```

5. Backup Strategy Implementation
```bash
#!/bin/bash
# scripts/backup.sh

# Full backup
neo4j-admin backup \
  --backup-dir=/backups/$(date +%Y%m%d) \
  --name=graph.db \
  --check-consistency=true \
  --verify=true

# Cleanup old backups (keep last 7 days)
find /backups -mtime +7 -type d -exec rm -rf {} +

# Verify backup
neo4j-admin check-consistency \
  --backup=/backups/$(date +%Y%m%d)/graph.db \
  --verbose

# Upload to remote storage
aws s3 sync /backups s3://vitalyst-backups/neo4j/
```

## Implementation Strategy
1. Infrastructure Setup
   - Deploy Neo4j cluster
   - Configure high availability
   - Set up monitoring
   - Implement backup system

2. Security Implementation
   - Configure SSL/TLS
   - Set up RBAC
   - Implement audit logging
   - Configure network security

3. Data Management
   - Create constraints
   - Set up indexes
   - Configure backup schedule
   - Implement monitoring alerts

## Acceptance Criteria
- [ ] Neo4j cluster deployed and operational
- [ ] High availability configured and tested
- [ ] Security measures implemented
- [ ] SSL/TLS encryption enabled
- [ ] RBAC configured and tested
- [ ] Monitoring system operational
- [ ] Backup system configured
- [ ] Performance tuning completed
- [ ] Constraints and indexes created
- [ ] Documentation completed
- [ ] Disaster recovery tested
- [ ] Alerts configured and tested

## Dependencies
- Ticket 1.3: Environment Configuration
- Ticket 1.5: Docker & Compose Setup
- Ticket 1.6: CI/CD Initial Setup

## Estimated Hours
30

## Testing Requirements
- Infrastructure Tests
  - Test cluster deployment
  - Verify high availability
  - Test failover scenarios
  - Validate backup/restore
- Security Tests
  - Test SSL/TLS encryption
  - Verify RBAC permissions
  - Test network security
  - Validate audit logging
- Performance Tests
  - Test query performance
  - Verify index effectiveness
  - Measure backup impact
  - Test concurrent access
- Integration Tests
  - Test monitoring integration
  - Verify alert triggers
  - Test backup automation
  - Validate metrics collection

## Documentation
- Deployment architecture
- Security configuration
- Backup procedures
- Monitoring setup
- Performance tuning
- Disaster recovery
- Troubleshooting guide

## Search Space Optimization
- Clear configuration structure
- Logical service organization
- Consistent naming conventions
- Standardized security patterns
- Organized monitoring metrics

## References
- Blueprint Section 2: Architecture and Module Overview
- Blueprint Section 3: Data Model & Graph Structure
- Blueprint Section 9: Security & Monitoring
- Neo4j Enterprise Documentation
- Docker Swarm Documentation

## Notes
- Implements high availability
- Ensures data security
- Supports automated backups
- Maintains performance
- Optimizes for reliability 