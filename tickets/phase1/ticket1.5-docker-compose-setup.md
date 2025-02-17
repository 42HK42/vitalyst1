# Ticket 1.5: Docker & Compose Setup

## Priority
High

## Type
Setup

## Status
To Do

## Description
Implement comprehensive Docker and Docker Compose configurations for the Vitalyst Knowledge Graph, supporting both development and production environments. The implementation must ensure secure, scalable, and efficient containerization while maintaining optimal development experience and following zero-trust security principles.

## Technical Details

1. Development Dockerfile Implementations
```dockerfile
# backend/Dockerfile.dev
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements/dev.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=development

# Start development server with hot reload
CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# frontend/Dockerfile.dev
FROM node:18-alpine

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm ci

# Copy application code
COPY . .

# Start development server
CMD ["npm", "run", "dev"]
```

2. Production Dockerfile Implementations
```dockerfile
# backend/Dockerfile.prod
FROM python:3.11-slim as builder

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Install Python dependencies
COPY requirements/base.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Production stage
FROM python:3.11-slim

WORKDIR /app

# Copy only necessary files from builder
COPY --from=builder /app /app
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

# Create non-root user
RUN useradd -m -r -s /bin/bash vitalyst && \
    chown -R vitalyst:vitalyst /app

USER vitalyst

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Set environment variables
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1
ENV FLASK_ENV=production

EXPOSE 8000

CMD ["uvicorn", "src.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]

# frontend/Dockerfile.prod
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
FROM nginx:alpine

# Copy built assets
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD wget -q --spider http://localhost:3000/health || exit 1

EXPOSE 3000

CMD ["nginx", "-g", "daemon off;"]
```

3. Development Docker Compose Configuration
```yaml
# docker-compose.dev.yml
version: '3.8'

services:
  backend:
    build:
      context: ./backend
      dockerfile: Dockerfile.dev
    volumes:
      - ./backend:/app
      - backend-deps:/app/node_modules
    ports:
      - "8000:8000"
    environment:
      - NODE_ENV=development
      - PYTHONPATH=/app
      - PYTHONUNBUFFERED=1
    depends_on:
      neo4j:
        condition: service_healthy
      redis:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    networks:
      - vitalyst-network

  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile.dev
    volumes:
      - ./frontend:/app
      - frontend-deps:/app/node_modules
    ports:
      - "3000:3000"
    environment:
      - NODE_ENV=development
      - VITE_API_URL=http://localhost:8000
    depends_on:
      backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-q", "--spider", "http://localhost:3000/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - vitalyst-network

  neo4j:
    image: neo4j:5.7
    environment:
      - NEO4J_AUTH=neo4j/password
      - NEO4J_dbms_memory_heap_max__size=2G
      - NEO4J_dbms_memory_pagecache_size=1G
    ports:
      - "7474:7474"
      - "7687:7687"
    volumes:
      - neo4j-data:/data
      - neo4j-logs:/logs
    healthcheck:
      test: ["CMD-SHELL", "wget -q --spider http://localhost:7474 || exit 1"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - vitalyst-network

  redis:
    image: redis:7.0-alpine
    command: redis-server --requirepass ${REDIS_PASSWORD}
    ports:
      - "6379:6379"
    volumes:
      - redis-data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 30s
      timeout: 10s
      retries: 3
    networks:
      - vitalyst-network

  prometheus:
    image: prom/prometheus:v2.44.0
    volumes:
      - ./monitoring/prometheus:/etc/prometheus
      - prometheus-data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
    ports:
      - "9090:9090"
    networks:
      - vitalyst-network

  grafana:
    image: grafana/grafana:9.5.2
    volumes:
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning
      - grafana-data:/var/lib/grafana
    environment:
      - GF_SECURITY_ADMIN_PASSWORD=${GRAFANA_PASSWORD}
    ports:
      - "3001:3000"
    depends_on:
      - prometheus
    networks:
      - vitalyst-network

networks:
  vitalyst-network:
    driver: bridge

volumes:
  backend-deps:
  frontend-deps:
  neo4j-data:
  neo4j-logs:
  redis-data:
  prometheus-data:
  grafana-data:
```

4. Production Docker Compose Configuration
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
      resources:
        limits:
          cpus: '1'
          memory: 2G
        reservations:
          cpus: '0.5'
          memory: 1G
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
      resources:
        limits:
          cpus: '0.5'
          memory: 1G
        reservations:
          cpus: '0.25'
          memory: 512M
    networks:
      - vitalyst-network
    depends_on:
      - backend

  neo4j:
    image: neo4j:5.7
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

5. Nginx Configuration for Frontend
```nginx
# frontend/nginx.conf
server {
    listen 3000;
    server_name localhost;

    root /usr/share/nginx/html;
    index index.html;

    # Security headers
    add_header X-Frame-Options "SAMEORIGIN";
    add_header X-XSS-Protection "1; mode=block";
    add_header X-Content-Type-Options "nosniff";
    add_header Referrer-Policy "strict-origin-when-cross-origin";
    add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline' 'unsafe-eval'; style-src 'self' 'unsafe-inline';";

    # Gzip compression
    gzip on;
    gzip_vary on;
    gzip_min_length 10240;
    gzip_proxied expired no-cache no-store private auth;
    gzip_types text/plain text/css text/xml text/javascript application/x-javascript application/xml;
    gzip_disable "MSIE [1-6]\.";

    location / {
        try_files $uri $uri/ /index.html;
        expires -1;
    }

    location /static/ {
        expires 1y;
        add_header Cache-Control "public, no-transform";
    }

    location /health {
        access_log off;
        return 200 'healthy\n';
    }
}
```

## Implementation Strategy
1. Development Environment Setup
   - Configure development Dockerfiles
   - Set up development compose file
   - Configure hot reload
   - Set up volume mounts

2. Production Environment Setup
   - Configure production Dockerfiles
   - Set up production compose file
   - Configure scaling
   - Set up monitoring

3. Security Implementation
   - Configure health checks
   - Set up resource limits
   - Implement security headers
   - Configure networks

## Acceptance Criteria
- [ ] Development environment Dockerfiles created and tested
- [ ] Production environment Dockerfiles created and tested
- [ ] Development docker-compose.yml configured and working
- [ ] Production docker-compose.yml configured and working
- [ ] Health checks implemented for all services
- [ ] Resource limits configured appropriately
- [ ] Volume mounts set up correctly
- [ ] Hot reload working in development
- [ ] Security configurations implemented
- [ ] Monitoring setup completed
- [ ] All services communicate correctly
- [ ] Documentation updated

## Dependencies
- Ticket 1.3: Environment Config
- Ticket 1.4: Dependency Installation

## Estimated Hours
20

## Testing Requirements
- Development Tests
  - Test hot reload functionality
  - Verify volume mounts
  - Test service communication
- Production Tests
  - Test scaling behavior
  - Verify resource limits
  - Test health checks
- Security Tests
  - Verify network isolation
  - Test security headers
  - Validate access controls
- Performance Tests
  - Measure startup times
  - Test under load
  - Verify resource usage

## Documentation
- Docker setup guide
- Environment configuration
- Service architecture
- Scaling guidelines
- Security implementation
- Monitoring setup
- Troubleshooting guide

## Search Space Optimization
- Clear service organization
- Environment-specific configurations
- Consistent naming conventions
- Logical resource grouping
- Standardized security patterns

## References
- Blueprint Section 9: Frameworks, Deployment, Security & Monitoring
- Blueprint Section 2: Architecture and Module Overview
- Blueprint Section 6: Security Requirements
- Blueprint Section 8: Monitoring and Logging

## Notes
- Implements comprehensive containerization
- Ensures security through isolation
- Supports efficient development
- Maintains production readiness
- Optimizes for scalability 