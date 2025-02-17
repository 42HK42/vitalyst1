# Deployment Guide

## Overview
This guide covers deployment procedures for the Vitalyst Knowledge Graph system.

## Prerequisites
- Docker 25.0.2+
- Docker Compose 2.24.5+
- Access to container registry
- SSL certificates
- Environment configuration files

## Environment Setup

### Configuration Files
Each environment has its own configuration in `/backend/config/{environment}`:
- `development/` - Local development
- `production/` - Production deployment
- `test/` - Testing environment

### Environment Variables
Copy the appropriate .env file:
```bash
# Development
cp config/development/.env.example config/development/.env

# Production
cp config/production/.env.example config/production/.env
```

## Deployment Process

### 1. Build Images
```bash
docker-compose build
```

### 2. Database Setup
```bash
# Initialize Neo4j
docker-compose up -d neo4j
scripts/db/init-db.sh

# Run migrations
scripts/db/migrate.sh
```

### 3. Start Services
```bash
docker-compose up -d
```

### 4. Verify Deployment
```bash
# Check service health
scripts/deployment/health-check.sh

# Verify API
curl http://localhost:8000/health
```

## Monitoring

### Logs
- Application logs: `/var/log/vitalyst/app.log`
- Access logs: `/var/log/vitalyst/access.log`
- Error logs: `/var/log/vitalyst/error.log`

### Metrics
- Prometheus: `http://localhost:9090`
- Grafana: `http://localhost:3000`

## Backup & Recovery

### Database Backup
```bash
scripts/db/backup.sh
```

### Recovery
```bash
scripts/db/restore.sh <backup-file>
```

## Security

### SSL/TLS
- Certificates stored in `/etc/vitalyst/certs/`
- Auto-renewal via Let's Encrypt

### Firewall
- Only necessary ports exposed (80, 443, 7687)
- Internal services not accessible from outside

## Troubleshooting
See [Troubleshooting Guide](troubleshooting.md) for common issues and solutions.
