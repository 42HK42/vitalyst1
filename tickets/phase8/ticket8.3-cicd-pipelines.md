# Ticket 8.3: Configure CI/CD Pipelines

## Priority
High

## Type
Development

## Status
To Do

## Description
Implement comprehensive CI/CD pipelines for the Vitalyst Knowledge Graph using GitHub Actions to automate testing, building, and deployment processes. The system must include automated regression testing, support rollback capabilities, and maintain high code quality standards as specified in the blueprint.

## Technical Details
1. GitHub Actions Workflow Implementation
```yaml
# .github/workflows/main.yml
name: Vitalyst CI/CD Pipeline

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]

env:
  REGISTRY: ghcr.io
  BACKEND_IMAGE: vitalyst-backend
  FRONTEND_IMAGE: vitalyst-frontend

jobs:
  validate-architecture:
    name: Validate Architecture
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Validate Service Boundaries
        run: |
          python scripts/validate_architecture.py
          
      - name: Check Dependency Graph
        run: |
          python scripts/analyze_dependencies.py

  test:
    name: Run Tests
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.11'
          cache: 'pip'

      - name: Set up Node.js
        uses: actions/setup-node@v3
        with:
          node-version: '18'
          cache: 'npm'

      - name: Install backend dependencies
        run: |
          cd backend
          pip install -r requirements.txt
          pip install -r requirements-dev.txt

      - name: Run backend tests
        run: |
          cd backend
          pytest --cov=src --cov-report=xml

      - name: Install frontend dependencies
        run: |
          cd frontend
          npm ci

      - name: Run frontend tests
        run: |
          cd frontend
          npm run test:ci

      - name: Upload coverage reports
        uses: codecov/codecov-action@v3
        with:
          files: ./backend/coverage.xml,./frontend/coverage/coverage-final.json

  lint:
    name: Code Quality
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run backend linting
        uses: rickstaa/action-black@v1
        with:
          path: "backend"

      - name: Run frontend linting
        run: |
          cd frontend
          npm ci
          npm run lint
          npm run type-check

  security:
    name: Security Scan
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Run dependency scan
        uses: snyk/actions/python@master
        with:
          args: --severity-threshold=high

      - name: Run container scan
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: 'fs'
          ignore-unfixed: true
          format: 'sarif'
          output: 'trivy-results.sarif'

      - name: OWASP Check
        uses: dependency-check/Dependency-Check_Action@main
        with:
          project: 'Vitalyst'
          path: '.'
          format: 'HTML'
          
      - name: Secret Scanning
        uses: trufflesecurity/trufflehog-actions-scan@master
        with:
          path: "."
          
      - name: License Compliance
        uses: fossas/fossa-action@v1
        with:
          api-key: ${{ secrets.FOSSA_API_KEY }}

  documentation:
    name: Generate Documentation
    needs: [test, lint, security]
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      
      - name: Generate API Documentation
        run: |
          cd backend
          python -m sphinx.cmd.build -b html docs/source docs/build
          
      - name: Upload Documentation
        uses: actions/upload-artifact@v3
        with:
          name: documentation
          path: backend/docs/build

  build:
    name: Build and Push
    needs: [test, lint, security]
    runs-on: ubuntu-latest
    if: github.event_name == 'push'
    steps:
      - uses: actions/checkout@v3

      - name: Set up Docker Buildx
        uses: docker/setup-buildx-action@v2

      - name: Login to Container Registry
        uses: docker/login-action@v2
        with:
          registry: ${{ env.REGISTRY }}
          username: ${{ github.actor }}
          password: ${{ secrets.GITHUB_TOKEN }}

      - name: Build and push backend
        uses: docker/build-push-action@v4
        with:
          context: ./backend
          file: ./backend/Dockerfile.prod
          push: true
          tags: ${{ env.REGISTRY }}/${{ github.repository_owner }}/${{ env.BACKEND_IMAGE }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

      - name: Build and push frontend
        uses: docker/build-push-action@v4
        with:
          context: ./frontend
          file: ./frontend/Dockerfile.prod
          push: true
          tags: ${{ env.REGISTRY }}/${{ github.repository_owner }}/${{ env.FRONTEND_IMAGE }}:${{ github.sha }}
          cache-from: type=gha
          cache-to: type=gha,mode=max

  performance:
    name: Performance Monitoring
    runs-on: ubuntu-latest
    needs: [build]
    steps:
      - name: Run Performance Tests
        run: |
          k6 run performance/load-tests.js
          
      - name: Analyze Performance Results
        uses: actions/github-script@v6
        with:
          script: |
            const results = require('./performance-results.json')
            // Add performance analysis logic

  deploy:
    name: Deploy
    needs: [build, performance]
    runs-on: ubuntu-latest
    if: github.ref == 'refs/heads/main'
    environment: production
    steps:
      - uses: actions/checkout@v3

      - name: Configure AWS credentials
        uses: aws-actions/configure-aws-credentials@v2
        with:
          aws-access-key-id: ${{ secrets.AWS_ACCESS_KEY_ID }}
          aws-secret-access-key: ${{ secrets.AWS_SECRET_ACCESS_KEY }}
          aws-region: eu-central-1

      - name: Update deployment configuration
        run: |
          VERSION=${{ github.sha }}
          envsubst < k8s/deployment.template.yml > k8s/deployment.yml

      - name: Deploy Canary
        if: github.ref == 'refs/heads/main'
        run: |
          kubectl apply -f k8s/canary/
          
      - name: Monitor Deployment Health
        run: |
          python scripts/monitor_deployment.py
          
      - name: Verify Deployment
        run: |
          if ! python scripts/verify_deployment.py; then
            kubectl rollout undo deployment/vitalyst
          fi

      - name: Deploy to Kubernetes
        uses: azure/k8s-deploy@v1
        with:
          manifests: |
            k8s/deployment.yml
          images: |
            ${{ env.REGISTRY }}/${{ github.repository_owner }}/${{ env.BACKEND_IMAGE }}:${{ github.sha }}
            ${{ env.REGISTRY }}/${{ github.repository_owner }}/${{ env.FRONTEND_IMAGE }}:${{ github.sha }}
```

2. Deployment Configuration Implementation
```yaml
# k8s/deployment.template.yml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitalyst-backend
spec:
  replicas: 3
  selector:
    matchLabels:
      app: vitalyst-backend
  template:
    metadata:
      labels:
        app: vitalyst-backend
    spec:
      containers:
      - name: backend
        image: ${REGISTRY}/${REPOSITORY_OWNER}/${BACKEND_IMAGE}:${VERSION}
        ports:
        - containerPort: 8000
        env:
        - name: DATABASE_URL
          valueFrom:
            secretKeyRef:
              name: vitalyst-secrets
              key: database-url
        livenessProbe:
          httpGet:
            path: /health
            port: 8000
          initialDelaySeconds: 30
          periodSeconds: 10
        resources:
          limits:
            cpu: "1"
            memory: "2Gi"
          requests:
            cpu: "500m"
            memory: "1Gi"
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: vitalyst-frontend
spec:
  replicas: 2
  selector:
    matchLabels:
      app: vitalyst-frontend
  template:
    metadata:
      labels:
        app: vitalyst-frontend
    spec:
      containers:
      - name: frontend
        image: ${REGISTRY}/${REPOSITORY_OWNER}/${FRONTEND_IMAGE}:${VERSION}
        ports:
        - containerPort: 3000
        env:
        - name: API_URL
          value: "https://api.vitalyst.io"
        livenessProbe:
          httpGet:
            path: /health
            port: 3000
          initialDelaySeconds: 30
          periodSeconds: 10
```

3. Rollback Script Implementation
```python
# src/scripts/rollback.py
import subprocess
import logging
from typing import Optional
from datetime import datetime

class DeploymentRollback:
    def __init__(self):
        self.logger = self.setup_logger()

    def setup_logger(self) -> logging.Logger:
        logger = logging.getLogger('rollback')
        logger.setLevel(logging.INFO)
        
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        
        return logger

    async def rollback_deployment(
        self,
        deployment_name: str,
        version: Optional[str] = None
    ) -> bool:
        """Rollback deployment to previous or specific version"""
        try:
            if version:
                return await self.rollback_to_version(deployment_name, version)
            else:
                return await self.rollback_to_previous(deployment_name)

        except Exception as e:
            self.logger.error(f"Rollback failed: {str(e)}")
            return False

    async def rollback_to_previous(self, deployment_name: str) -> bool:
        """Rollback to previous deployment version"""
        try:
            # Get deployment history
            result = subprocess.run([
                'kubectl', 'rollout', 'history',
                f'deployment/{deployment_name}',
                '--output=json'
            ], capture_output=True, text=True, check=True)

            history = json.loads(result.stdout)
            if len(history['revisions']) < 2:
                self.logger.error("No previous revision available")
                return False

            previous_revision = history['revisions'][-2]['revision']

            # Perform rollback
            return await self.execute_rollback(
                deployment_name,
                previous_revision
            )

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Failed to get deployment history: {str(e)}")
            return False

    async def rollback_to_version(
        self,
        deployment_name: str,
        version: str
    ) -> bool:
        """Rollback to specific version"""
        try:
            # Update deployment configuration
            result = subprocess.run([
                'kubectl', 'set', 'image',
                f'deployment/{deployment_name}',
                f'{deployment_name}=${REGISTRY}/${REPOSITORY_OWNER}/${deployment_name}:{version}'
            ], check=True)

            if result.returncode != 0:
                self.logger.error("Failed to update deployment image")
                return False

            # Verify rollback
            return await self.verify_rollback(deployment_name)

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Rollback failed: {str(e)}")
            return False

    async def verify_rollback(self, deployment_name: str) -> bool:
        """Verify rollback success"""
        try:
            # Wait for rollout to complete
            result = subprocess.run([
                'kubectl', 'rollout', 'status',
                f'deployment/{deployment_name}',
                '--timeout=300s'
            ], check=True)

            if result.returncode != 0:
                self.logger.error("Rollback verification failed")
                return False

            # Verify pod health
            return await self.verify_pod_health(deployment_name)

        except subprocess.CalledProcessError as e:
            self.logger.error(f"Verification failed: {str(e)}")
            return False
```

## Acceptance Criteria
- [ ] GitHub Actions workflow implementation
- [ ] Automated testing pipeline
- [ ] Container build and push automation
- [ ] Kubernetes deployment configuration
- [ ] Rollback mechanism implementation
- [ ] Security scanning integration
- [ ] Performance testing automation
- [ ] Documentation generation
- [ ] Architecture validation
- [ ] Dependency analysis
- [ ] Canary deployment support
- [ ] Health monitoring integration
- [ ] Automated rollback procedures
- [ ] Performance benchmarking
- [ ] Security compliance verification
- [ ] License compliance checking
- [ ] Secret scanning implementation
- [ ] Documentation automation

## Dependencies
- Ticket 8.1: Docker Deployments
- Ticket 8.2: Monitoring and Logging
- Ticket 3.1: Backend Setup
- Ticket 4.1: Frontend Setup

## Estimated Hours
25

## Testing Requirements
- Unit Tests:
  - Test deployment scripts
  - Verify rollback logic
  - Test configuration generation
  - Validate environment setup
- Integration Tests:
  - Test complete pipeline
  - Verify deployment process
  - Test rollback procedures
- Security Tests:
  - Test secrets handling
  - Verify access controls
  - Validate secure communication
- Performance Tests:
  - Measure deployment speed
  - Test scaling behavior
  - Verify resource usage

## Documentation
- CI/CD pipeline overview
- Deployment process guide
- Rollback procedures
- Security measures
- Environment configuration
- Troubleshooting guide

## References
- **Phasedplan.md:** Phase 8, Ticket 8.3
- **Blueprint.md:** Sections on CI/CD and Deployment
- GitHub Actions Documentation
- Kubernetes Deployment Patterns
- Container Security Guidelines

### Adherence to Phasedplan and Blueprint Guidelines
This ticket implements the CI/CD pipeline configuration as specified in the blueprint, with particular attention to:
- Automated testing and deployment
- Security scanning integration
- Container build optimization
- Deployment automation
- Rollback capabilities
- Performance monitoring
``` 