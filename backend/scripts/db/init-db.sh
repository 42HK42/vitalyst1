#!/bin/bash
set -e

# Load environment variables
source "$(dirname "$0")/../../config/${ENVIRONMENT:-development}/.env"

echo "Initializing Neo4j database..."

# Wait for Neo4j to be ready
MAX_RETRIES=30
RETRY_COUNT=0

while ! curl -s "http://localhost:7474" > /dev/null; do
    if [ $RETRY_COUNT -eq $MAX_RETRIES ]; then
        echo "Error: Neo4j not ready after $MAX_RETRIES attempts"
        exit 1
    fi
    echo "Waiting for Neo4j to be ready... ($RETRY_COUNT/$MAX_RETRIES)"
    sleep 2
    RETRY_COUNT=$((RETRY_COUNT + 1))
done

# Create constraints and indexes
cypher-shell -u "$NEO4J_USER" -p "$NEO4J_PASSWORD" << 'EOF'
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Node) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Food) REQUIRE n.id IS UNIQUE;
CREATE CONSTRAINT IF NOT EXISTS FOR (n:Nutrient) REQUIRE n.id IS UNIQUE;

CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.name);
CREATE INDEX IF NOT EXISTS FOR (n:Food) ON (n.name);
CREATE INDEX IF NOT EXISTS FOR (n:Nutrient) ON (n.name);
CREATE INDEX IF NOT EXISTS FOR (n:Node) ON (n.type);
EOF

echo "Database initialization completed successfully"
