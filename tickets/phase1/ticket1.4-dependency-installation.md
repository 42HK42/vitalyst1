# Ticket 1.4: Dependency Installation and Management

## Priority
High

## Type
Setup

## Status
To Do

## Description
Implement comprehensive dependency management system for the Vitalyst Knowledge Graph, including version control, security scanning, update policies, and development tooling. The implementation must ensure reproducible builds, secure dependencies, and efficient development workflow while maintaining compatibility across all services.

## Technical Details

1. Backend Dependencies
```txt
# requirements/base.txt
# Core Dependencies
fastapi==0.95.0
uvicorn[standard]==0.21.1
pydantic==2.0.0
python-jose[cryptography]==3.3.0
python-multipart==0.0.6
email-validator==2.0.0

# Database
neo4j==5.7.0
redis==4.5.4

# AI/ML
langchain==0.0.200
openai==0.27.8
anthropic==0.3.0
numpy==1.24.3
pandas==2.0.0

# Monitoring & Logging
prometheus-client==0.17.0
opentelemetry-api==1.18.0
opentelemetry-sdk==1.18.0
structlog==23.1.0
python-json-logger==2.0.7

# Security
cryptography==41.0.1
passlib[bcrypt]==1.7.4
python-jose[cryptography]==3.3.0

# Utilities
httpx==0.24.0
python-dotenv==1.0.0
pyyaml==6.0.1
tenacity==8.2.2

# requirements/dev.txt
-r base.txt

# Testing
pytest==7.3.1
pytest-cov==4.0.0
pytest-asyncio==0.21.0
pytest-mock==3.10.0
faker==18.10.1

# Linting & Formatting
black==23.3.0
isort==5.12.0
flake8==6.0.0
mypy==1.3.0
pylint==2.17.4

# Documentation
sphinx==7.0.1
sphinx-rtd-theme==1.2.2
mkdocs-material==9.1.15

# Debug Tools
ipython==8.14.0
debugpy==1.6.7
```

2. Frontend Dependencies
```json
{
  "name": "vitalyst-frontend",
  "version": "1.0.0",
  "private": true,
  "scripts": {
    "dev": "vite",
    "build": "tsc && vite build",
    "preview": "vite preview",
    "test": "vitest",
    "test:ci": "vitest run --coverage",
    "lint": "eslint src --ext ts,tsx",
    "lint:fix": "eslint src --ext ts,tsx --fix",
    "type-check": "tsc --noEmit",
    "format": "prettier --write \"src/**/*.{ts,tsx,css}\"",
    "prepare": "husky install"
  },
  "dependencies": {
    "react": "18.2.0",
    "react-dom": "18.2.0",
    "@remix-run/react": "1.19.1",
    "@remix-run/node": "1.19.1",
    "@tanstack/react-query": "4.29.12",
    "react-flow-renderer": "11.7.0",
    "@mantine/core": "6.0.0",
    "@mantine/hooks": "6.0.0",
    "@mantine/notifications": "6.0.0",
    "axios": "1.4.0",
    "date-fns": "2.30.0",
    "zod": "3.21.4",
    "immer": "10.0.2",
    "lodash": "4.17.21"
  },
  "devDependencies": {
    "@types/react": "18.2.8",
    "@types/react-dom": "18.2.4",
    "@types/node": "20.2.5",
    "@types/lodash": "4.14.195",
    "@typescript-eslint/eslint-plugin": "5.59.8",
    "@typescript-eslint/parser": "5.59.8",
    "@vitejs/plugin-react": "4.0.0",
    "@vitest/coverage-c8": "0.32.0",
    "eslint": "8.42.0",
    "eslint-config-prettier": "8.8.0",
    "eslint-plugin-react": "7.32.2",
    "eslint-plugin-react-hooks": "4.6.0",
    "husky": "8.0.3",
    "lint-staged": "13.2.2",
    "prettier": "2.8.8",
    "typescript": "5.1.3",
    "vite": "4.3.9",
    "vitest": "0.32.0",
    "jsdom": "22.1.0"
  },
  "lint-staged": {
    "src/**/*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ],
    "src/**/*.{css,scss}": [
      "prettier --write"
    ]
  }
}
```

3. Development Tools Configuration
```yaml
# .pre-commit-config.yaml
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v4.4.0
    hooks:
      - id: trailing-whitespace
      - id: end-of-file-fixer
      - id: check-yaml
      - id: check-added-large-files
      - id: check-json
      - id: check-merge-conflict

  - repo: https://github.com/psf/black
    rev: 23.3.0
    hooks:
      - id: black

  - repo: https://github.com/pycqa/isort
    rev: 5.12.0
    hooks:
      - id: isort

  - repo: https://github.com/pre-commit/mirrors-mypy
    rev: v1.3.0
    hooks:
      - id: mypy
        additional_dependencies: [types-all]

  - repo: local
    hooks:
      - id: eslint
        name: eslint
        entry: cd frontend && npm run lint
        language: system
        types: [file]
        files: \.(ts|tsx)$

      - id: typescript-check
        name: typescript-check
        entry: cd frontend && npm run type-check
        language: system
        types: [file]
        files: \.(ts|tsx)$
```

4. Dependency Update Strategy
```python
# scripts/update_dependencies.py
from typing import Dict, List
import subprocess
import json
import toml
from pathlib import Path

class DependencyManager:
    def __init__(self):
        self.backend_dir = Path("backend")
        self.frontend_dir = Path("frontend")
        
    def check_updates(self) -> Dict[str, List[str]]:
        """Check for available updates in both backend and frontend"""
        updates = {
            "backend": self.check_pip_updates(),
            "frontend": self.check_npm_updates()
        }
        return updates
        
    def update_dependencies(self, dry_run: bool = True) -> None:
        """Update dependencies with safety checks"""
        if not dry_run:
            self.backup_dependency_files()
            
        # Update backend dependencies
        self.update_pip_dependencies(dry_run)
        
        # Update frontend dependencies
        self.update_npm_dependencies(dry_run)
        
        # Run tests to verify updates
        if not dry_run:
            self.verify_updates()
            
    def verify_updates(self) -> bool:
        """Run tests to verify dependency updates"""
        try:
            # Run backend tests
            subprocess.run(["pytest"], cwd=self.backend_dir, check=True)
            
            # Run frontend tests
            subprocess.run(["npm", "test"], cwd=self.frontend_dir, check=True)
            
            return True
        except subprocess.CalledProcessError:
            self.rollback_updates()
            return False
```

5. Security Scanning Implementation
```python
# scripts/security_scan.py
import subprocess
from pathlib import Path
from typing import Dict, List

class SecurityScanner:
    def __init__(self):
        self.backend_dir = Path("backend")
        self.frontend_dir = Path("frontend")
        
    async def scan_dependencies(self) -> Dict[str, List[str]]:
        """Scan dependencies for security vulnerabilities"""
        results = {
            "backend": await self.scan_python_deps(),
            "frontend": await self.scan_npm_deps()
        }
        return results
        
    async def scan_python_deps(self) -> List[str]:
        """Scan Python dependencies using safety"""
        try:
            result = subprocess.run(
                ["safety", "check"],
                cwd=self.backend_dir,
                capture_output=True,
                text=True
            )
            return self.parse_safety_output(result.stdout)
        except subprocess.CalledProcessError as e:
            return [f"Scan failed: {str(e)}"]
            
    async def scan_npm_deps(self) -> List[str]:
        """Scan npm dependencies using npm audit"""
        try:
            result = subprocess.run(
                ["npm", "audit", "--json"],
                cwd=self.frontend_dir,
                capture_output=True,
                text=True
            )
            return self.parse_npm_audit(result.stdout)
        except subprocess.CalledProcessError as e:
            return [f"Scan failed: {str(e)}"]
```

## Implementation Strategy
1. Dependency Setup
   - Install and configure backend dependencies
   - Install and configure frontend dependencies
   - Set up development tools
   - Configure pre-commit hooks

2. Version Management
   - Implement version pinning strategy
   - Configure dependency update workflow
   - Set up compatibility checking
   - Implement security scanning

3. CI/CD Integration
   - Configure dependency caching
   - Set up automated updates
   - Implement security scanning
   - Configure build optimization

## Acceptance Criteria
- [ ] Backend dependencies installed and verified
- [ ] Frontend dependencies installed and verified
- [ ] Development tools configured and tested
- [ ] Pre-commit hooks implemented
- [ ] Security scanning configured
- [ ] Dependency update workflow established
- [ ] Version pinning strategy implemented
- [ ] CI/CD integration completed
- [ ] Documentation updated
- [ ] All tests passing with new dependencies

## Dependencies
- Ticket 1.1: Repository Setup
- Ticket 1.2: Directory Structure
- Ticket 1.3: Environment Config

## Estimated Hours
15

## Testing Requirements
- Dependency Tests
  - Verify clean installation
  - Test version compatibility
  - Validate build process
- Security Tests
  - Run vulnerability scans
  - Test dependency updates
  - Verify version pinning
- Integration Tests
  - Test pre-commit hooks
  - Verify CI/CD integration
  - Test build caching
- Performance Tests
  - Measure build times
  - Test dependency resolution
  - Verify caching efficiency

## Documentation
- Dependency management guide
- Version update procedures
- Security scanning guide
- Build optimization guide
- Development workflow documentation
- Troubleshooting procedures

## Search Space Optimization
- Clear dependency categorization
- Structured version management
- Consistent tool configuration
- Standardized update procedures
- Organized security scanning

## References
- Blueprint Section 2: Architecture and Module Overview
- Blueprint Section 7: Development Plan & TDD
- Blueprint Section 9: Security & Monitoring
- Blueprint Section 4: Development Standards

## Notes
- Implements comprehensive dependency management
- Ensures security through scanning
- Supports efficient development workflow
- Maintains build reproducibility
- Optimizes for development experience 