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

## 📁 Project Structure

```
/Vitalyst
├── backend/                 # FastAPI backend application
│   ├── src/
│   │   ├── api/            # API endpoints
│   │   ├── models/         # Pydantic models
│   │   ├── services/       # Business logic
│   │   ├── utils/          # Utilities
│   │   ├── tests/          # Test suites
│   │   └── main.py         # Application entry point
│   ├── Dockerfile          # Backend Docker configuration
│   ├── requirements.txt    # Python dependencies
│   ├── pyproject.toml     # Python project configuration
│   └── setup.cfg          # Python setup configuration
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
```

## 🚀 Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20 LTS
- Docker 25.0.2 & Docker Compose 2.24.5
- Neo4j 5.18.0

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/42HK42/vitalyst1.git
cd vitalyst1
```

2. **Set up environment variables:**
```bash
cp config/env/.env.example .env
# Edit .env with your configuration
```

3. **Install backend dependencies:**
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # or `.venv\Scripts\activate` on Windows
pip install -r requirements.txt
```

4. **Install frontend dependencies:**
```bash
cd frontend
npm install
```

5. **Start the development environment:**
```bash
docker-compose up -d
```

## 👨‍💻 Development

### Branch Protection
⚠️ **Note:** Branch protection rules are currently pending setup. They will be implemented in a future update to enforce:
- Pull request reviews before merging
- Status checks to pass before merging
- Branch updates before merging
- Linear history
- Signed commits

### Development Workflow
1. Create feature branch from main
2. Implement changes following TDD
3. Run tests and linting
4. Submit PR for review
5. Merge after approval

### Running Tests

```bash
# Backend tests
cd backend
pytest

# Frontend tests
cd frontend
npm test
```

### Code Quality

```bash
# Backend
cd backend
black .
flake8
mypy .

# Frontend
cd frontend
npm run lint
npm run format
```

## 📚 Documentation

- [Architecture Overview](docs/architecture/README.md)
- [API Documentation](docs/api/README.md)
- [Development Guide](docs/development/README.md)
- [Deployment Guide](docs/deployment/README.md)

## 🤝 Contributing

Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct and development process.

## 🔒 Security

For security concerns, please read our [Security Policy](SECURITY.md).

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Neo4j for graph database technology
- OpenAI, Anthropic, and Perplexity for AI capabilities
- The open-source community for various tools and libraries

## 📊 Project Status

- **Current Version:** 1.0.0-alpha
- **Status:** Active Development
