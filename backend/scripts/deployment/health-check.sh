#!/bin/bash
set -e

# Load environment variables
source "$(dirname "$0")/../../config/${ENVIRONMENT:-development}/.env"

# Check API health
echo "Checking API health..."
if curl -f "http://localhost:${PORT}/health" > /dev/null 2>&1; then
    echo "✅ API is healthy"
else
    echo "❌ API health check failed"
    exit 1
fi

# Check Neo4j connection
echo "Checking Neo4j connection..."
if curl -f "http://localhost:7474" > /dev/null 2>&1; then
    echo "✅ Neo4j is healthy"
else
    echo "❌ Neo4j health check failed"
    exit 1
fi

# Check Redis connection
echo "Checking Redis connection..."
if redis-cli -h "$REDIS_HOST" -p "$REDIS_PORT" ping > /dev/null 2>&1; then
    echo "✅ Redis is healthy"
else
    echo "❌ Redis health check failed"
    exit 1
fi

# Check Prometheus
echo "Checking Prometheus..."
if curl -f "http://localhost:9090/-/healthy" > /dev/null 2>&1; then
    echo "✅ Prometheus is healthy"
else
    echo "❌ Prometheus health check failed"
    exit 1
fi

# Check Grafana
echo "Checking Grafana..."
if curl -f "http://localhost:3000/api/health" > /dev/null 2>&1; then
    echo "✅ Grafana is healthy"
else
    echo "❌ Grafana health check failed"
    exit 1
fi

echo "All services are healthy! 🚀"
