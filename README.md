# Vitalyst Knowledge Graph

A comprehensive knowledge management system for nutritional data, integrating advanced data modeling with AI-powered enrichment capabilities.

---

## 📋 Table of Contents
1. [Overview](#overview)
2. [Key Features](#key-features)
3. [Technology Stack](#technology-stack)
4. [Project Structure](#project-structure)
5. [Getting Started](#getting-started)
6. [Development](#development)
7. [Documentation](#documentation)
8. [Contributing](#contributing)
9. [License](#license)

---

## 🔍 Overview

Vitalyst is a sophisticated knowledge graph system designed to manage and analyze nutritional data. It combines traditional data management with cutting-edge AI technologies to provide rich, interconnected nutritional information.

### Development Status
- ✅ Phase 1: Foundation Setup (Completed)
  - Repository and infrastructure setup
  - Environment configuration
  - Docker and CI/CD implementation
- 🚧 Phase 2: Backend Development (In Progress)
- 📅 Phase 3: AI Integration (Planned)
- 📅 Phase 4: Frontend Development (Planned)
- 📅 Phase 5: Testing & Optimization (Planned)

## ⭐ Key Features

- 📊 Graph-based data modeling with Neo4j
- 🤖 AI-powered content enrichment using multiple providers (OpenAI, Anthropic, Perplexity)
- 🌐 Multi-language support
- ✅ Advanced source reliability tracking
- 🌱 Comprehensive environmental impact monitoring
- 🔄 Real-time data validation and verification
- 📈 Interactive visualization capabilities

## 🛠 Technology Stack

### Backend
- Python 3.12+ (Latest stable)
- FastAPI 0.110.0 (Latest)
- Neo4j 5.18.0 (Latest)
- LangChain 0.1.11 (Latest)
- Redis 7.2.4 (Latest stable)
- SQLAlchemy 2.0.27 (Latest)
- Alembic 1.13.1 (Latest)
- OpenTelemetry 1.23.0 (Latest)
- Sentry SDK 1.40.4 (Latest)
- Prometheus Client 0.20.0 (Latest)

### Frontend
- Node.js 20 LTS (Latest LTS)
- React 18.2.0 (Latest stable)
- Remix 2.7.2 (Latest stable)
- TypeScript 5.3.3 (Latest stable)
- React Flow 11.10.1 (Latest)
- TailwindCSS 3.4.1 (Latest)
- Vitest 1.3.1 (Latest)

### Infrastructure
- Docker 25.0.2 (Latest stable)
- Docker Compose 2.24.5 (Latest)
- Kubernetes 1.29.2 (Latest stable)
- Redis 7.2.4 (Latest stable)
- Elasticsearch 8.12.1 (Latest)
- Logstash 8.12.1 (Latest)
- Kibana 8.12.1 (Latest)
- Prometheus 2.45.3 (Latest)
- Grafana 10.3.3 (Latest)
- Sentry 23.12.1 (Latest)
- GitHub Actions (Latest)
- AWS EKS (Latest)
- Snyk Security Scanner (Latest)
- Trivy Container Scanner (Latest)
- CodeQL Analysis (Latest)

## 📁 Project Structure

The project follows a modular, layered architecture designed for scalability and maintainability:

```bash
/Vitalyst
├── backend/                 # FastAPI backend application
│   ├── src/                # Source code
│   │   ├── api/           # API layer
│   │   │   └── v1/        # API version 1
│   │   │       ├── endpoints/  # Route handlers and API endpoints
│   │   │       ├── middleware/ # Request/response middleware (auth, logging)
│   │   │       └── schemas/    # Request/response validation schemas
│   │   ├── models/         # Data models
│   │   │   ├── nodes/      # Node entity models (Food, Nutrient, etc.)
│   │   │   ├── relationships/ # Relationship models between nodes
│   │   │   └── validators/  # Custom model validators
│   │   ├── services/       # Business logic
│   │   │   ├── graph/      # Neo4j database operations
│   │   │   ├── auth/       # Authentication and authorization
│   │   │   ├── ai/         # AI-powered content enrichment
│   │   │   └── validation/ # Data validation services
│   │   ├── utils/          # Utilities
│   │   │   ├── logging/    # Logging configuration and handlers
│   │   │   ├── metrics/    # Performance and usage metrics
│   │   │   └── helpers/    # Common helper functions
│   │   └── tests/          # Test suites
│   │       ├── unit/       # Unit tests for individual components
│   │       ├── integration/ # Integration tests between components
│   │       └── e2e/        # End-to-end API tests
│   ├── config/             # Configuration management
│   │   ├── development/    # Development environment settings
│   │   ├── production/     # Production environment settings
│   │   ├── test/          # Test environment settings
│   │   ├── security/       # Security configurations
│   │   │   ├── certs/     # SSL/TLS certificates
│   │   │   ├── keys/      # API and encryption keys
│   │   │   └── policies/  # Security policies (CORS, rate limits)
│   │   ├── monitoring/    # Monitoring configuration
│   │   │   ├── grafana/   # Grafana dashboards and settings
│   │   │   └── prometheus/ # Prometheus rules and alerts
│   │   └── logging/       # Logging configuration
│   │       └── fluentd/   # Log aggregation setup
│   ├── docs/               # Documentation
│   │   ├── api/           # API documentation and OpenAPI specs
│   │   ├── models/        # Data model documentation
│   │   └── deployment/    # Deployment and operations guides
│   ├── scripts/           # Utility scripts
│   │   ├── db/           # Database management scripts
│   │   ├── deployment/   # Deployment automation scripts
│   │   └── validation/   # Data validation scripts
│   ├── Dockerfile        # Backend Docker configuration
│   ├── requirements.txt  # Python dependencies
│   ├── pyproject.toml   # Python project configuration
│   └── setup.cfg        # Python setup configuration
├── frontend/               # React/Remix frontend
│   ├── src/
│   │   ├── components/     # React components
│   │   ├── routes/         # Remix routes
│   │   ├── hooks/         # Custom hooks
│   │   ├── services/      # API services
│   │   ├── styles/        # CSS styles
│   │   ├── utils/         # Utilities
│   │   └── root.tsx       # Root component
│   ├── public/            # Static assets
│   ├── Dockerfile         # Frontend Docker configuration
│   ├── package.json       # Node.js dependencies
│   ├── tsconfig.json      # TypeScript configuration
│   ├── postcss.config.js  # PostCSS configuration
│   ├── tailwind.config.js # Tailwind CSS configuration
│   └── .eslintrc.js       # ESLint configuration
├── monitoring/            # Monitoring configuration
│   ├── grafana/          # Grafana dashboards
│   │   ├── dashboards/   # Dashboard definitions
│   │   └── provisioning/ # Grafana provisioning
│   └── prometheus/       # Prometheus configuration
│       └── prometheus.yml # Prometheus configuration
├── docker/               # Docker configurations and scripts
├── docs/                 # Project documentation
├── scripts/              # Utility scripts
├── tickets/              # Project tickets and planning
├── keys/                 # API keys (gitignored)
├── Vorlage/             # Templates and examples
├── .env.example         # Environment variables template
├── .gitignore           # Git ignore rules
├── .gitmessage          # Git commit message template
├── .cursorrules         # Cursor IDE rules
├── docker-compose.yml   # Docker Compose configuration
├── phasedplan.md        # Project phase planning
├── blueprint.md         # Project blueprint
├── CHANGELOG.md         # Project changelog
├── CONTRIBUTING.md      # Contribution guidelines
├── LICENSE             # MIT License
├── README.md           # Project documentation
└── SECURITY.md         # Security policy

### Key Directories

The project is organized into several key areas:

#### Backend Core (`/backend/src/`)
- `api/`: REST API endpoints and middleware
- `models/`: Data models for nodes and relationships
- `services/`: Core business logic implementation
- `utils/`: Shared utility functions

#### Configuration (`/backend/config/`)
- `development/, production/, test/`: Environment-specific settings
- `security/`: Certificates, keys, and security policies
- `monitoring/`: Grafana dashboards and Prometheus rules
- `logging/`: Log aggregation and management

#### Documentation (`/backend/docs/`)
- `api/`: API documentation and OpenAPI specs
- `models/`: Data model documentation
- `deployment/`: Deployment and operations guides

#### Infrastructure
- `monitoring/`: System monitoring and metrics
- `docker/`: Container configurations
- `scripts/`: Utility and automation scripts

## 🚀 Getting Started

### Prerequisites

See [backend/requirements.txt](backend/requirements.txt) for Python dependencies.

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/42HK42/vitalyst1.git
cd vitalyst1
```

2. **Set up environment:**
```bash
cp config/env/.env.example .env  # Configure your .env
make setup  # Installs all dependencies
```

3. **Start development environment:**
```bash
make dev  # Starts all services
```

## 📖 Documentation

Comprehensive documentation is available in the following locations:

- `/backend/docs/api/`: API specifications and usage
- `/backend/docs/models/`: System architecture and data models
- `/backend/docs/deployment/`: Development, deployment, and operations guides

For security policies and procedures, see [SECURITY.md](SECURITY.md).

## 📄 License

This software is proprietary and confidential. All rights reserved.
See [LICENSE](LICENSE) file for the full terms and conditions.

For licensing inquiries, please contact: legal@42hk42.com

## 👨‍💻 Development

### Backend Development
```bash
cd backend
source .venv/bin/activate
python -m src.main
```

### Frontend Development
```bash
cd frontend
npm run dev
```

### Docker Development
```bash
# Start all services
docker-compose up -d

# View logs
docker-compose logs -f

# Rebuild services
docker-compose build

# Stop all services
docker-compose down
```

## 🧪 Testing

```bash
# Backend tests
cd backend
pytest src/tests/unit
pytest src/tests/integration
pytest src/tests/e2e

# Frontend tests
cd frontend
npm test
```

## 🔒 Security

See [SECURITY.md](SECURITY.md) for security policies and procedures.

## 📄 License

This software is proprietary and confidential. All rights reserved.
See [LICENSE](LICENSE) file for the full terms and conditions.

For licensing inquiries, please contact: legal@42hk42.com
