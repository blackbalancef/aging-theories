# Aging Research Service 🧬

> AI-powered agentic service for discovering, analyzing, and organizing scientific research on aging theories

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-green.svg)](https://fastapi.tiangolo.com/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-14+-blue.svg)](https://www.postgresql.org/)
[![Redis](https://img.shields.io/badge/Redis-7+-red.svg)](https://redis.io/)

## Overview

This service automates the discovery and analysis of scientific papers about aging theories. It uses AI agents to:
- **Discover** papers from PubMed, PMC, and other sources
- **Classify** papers by their relevance to aging research
- **Extract** aging theories mentioned in papers
- **Analyze** full-text PDFs using a comprehensive 9-question framework
- **Organize** everything in PostgreSQL with advanced search capabilities

## Key Features

### 🤖 AI Agents
- **Discovery Agent**: Searches academic databases and web sources using Crawl4AI
- **Analysis Agent**: Deep analysis of papers with PDF parsing and theory extraction
- Both agents use LangChain tools and Nebius AI Studio models

### 📚 Multi-Source Search
- PubMed / PMC integration with NCBI API
- Web crawling capabilities via Crawl4AI
- Extensible architecture for adding more sources

### 🧠 Automatic Theory Classification
- AI-powered extraction of aging theories from papers
- Smart matching with existing theories using LLM
- Theory categories: genetic, cellular, molecular, nutritional, systemic, evolutionary
- Evidence level assessment (weak, moderate, strong)

### 📊 RESTful API
- Articles management and search
- Theory classification and statistics
- Discovery queue management
- Cost tracking for AI model usage
- Source/database statistics

### ⚡ Asynchronous Architecture
- Redis task queue for background processing
- Multiple concurrent workers
- PostgreSQL with async SQLAlchemy
- FastAPI for high-performance API

### 📥 Data Export
- Export articles, analyses, and theories to CSV
- Customizable filters and limits
- Full dataset export with relationships
- Compatible with Excel, Google Sheets, and data analysis tools

## Architecture

```
┌─────────────────────┐
│   FastAPI Server    │
│   (app.py)          │
└──────────┬──────────┘
           │
    ┌──────┴──────┐
    │             │
┌───▼────┐   ┌───▼────────┐
│Discovery│   │  Analysis   │
│ Agent   │   │   Agent     │
│         │   │  (Worker)   │
└────┬────┘   └─────┬──────┘
     │              │
     │   ┌──────────▼─────┐
     │   │  Redis Queue    │
     │   │  (Task Queue)   │
     │   └────────────────┘
     │
┌────▼─────────────────┐
│    PostgreSQL DB     │
│  - Articles          │
│  - Analyses          │
│  - Theories          │
│  - Article-Theories  │
│  - Costs             │
└──────────────────────┘
```

## Getting Started

### Prerequisites
- Python 3.10+
- PostgreSQL 14+
- Redis 7+
- Docker & Docker Compose (recommended)

### Installation

1. **Clone the repository**
```bash
git clone https://github.com/blackbalancef/aging-theories.git
cd aging-theories
```

2. **Install uv (modern Python package manager)**
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

3. **Install dependencies**
```bash
uv sync
```

4. **Set up environment variables**
```bash
cp env.example .env
# Edit .env with your configuration
```

Required environment variables:
```env
# NCBI API (PubMed/PMC)
NCBI_EMAIL=your@email.com
NCBI_API_KEY=your_ncbi_api_key

# Nebius AI Studio
NEBIUS_API_KEY=your_nebius_key
LLM_DEFAULT_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct

# Database
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/aging_research

# Redis
REDIS_URL=redis://localhost:6379/0
```

5. **Start services with Docker Compose**
```bash
docker-compose up -d
```

This starts:
- PostgreSQL on port 5432
- Redis on port 6379

6. **Run database migrations**
```bash
uv run alembic upgrade head
```

7. **Start the API server**
```bash
uv run python app.py
```

API will be available at `http://localhost:8000`

Interactive docs at `http://localhost:8000/docs`

8. **Start analysis workers** (in separate terminals)
```bash
# Start worker 1
uv run python agents/analysis_agent_worker.py

# Start worker 2
uv run python agents/analysis_agent_worker.py

# Start worker 3
uv run python agents/analysis_agent_worker.py
```

## Usage

### Discover Papers

Start discovery process:
```bash
curl -X POST "http://localhost:8000/api/discover" \
  -H "Content-Type: application/json" \
  -d '{
    "query": "mitochondrial aging theory",
    "max_results": 50
  }'
```

### List Articles

Get all discovered articles:
```bash
curl "http://localhost:8000/api/articles"
```

Search articles:
```bash
curl "http://localhost:8000/api/articles/search?q=telomeres"
```

### View Analysis

Get article analysis:
```bash
curl "http://localhost:8000/api/articles/{article_id}/analysis"
```

### Theory Statistics

Get theory statistics:
```bash
curl "http://localhost:8000/api/theories/stats/summary"
```

List all theories:
```bash
curl "http://localhost:8000/api/theories"
```

Search theories:
```bash
curl "http://localhost:8000/api/theories/search?q=mitochondria"
```

### Queue Status

Check analysis queue:
```bash
curl "http://localhost:8000/api/queue/status"
```

### Cost Tracking

View AI model usage costs:
```bash
curl "http://localhost:8000/api/costs"
```

### Export Data to CSV

Export articles to CSV:
```bash
curl "http://localhost:8000/api/export/articles" -o articles.csv
```

Export analyses to CSV:
```bash
curl "http://localhost:8000/api/export/analyses" -o analyses.csv
```

Export theories to CSV:
```bash
curl "http://localhost:8000/api/export/theories" -o theories.csv
```

Export article-theory relationships:
```bash
curl "http://localhost:8000/api/export/article-theories" -o article_theories.csv
```

Export full dataset (articles + analyses + theories):
```bash
curl "http://localhost:8000/api/export/full" -o full_dataset.csv
```

## API Endpoints

### Articles
- `POST /api/discover` - Start discovery process
- `GET /api/articles` - List all articles
- `GET /api/articles/search` - Search articles
- `GET /api/articles/{id}` - Get article details
- `GET /api/articles/{id}/analysis` - Get article analysis

### Theories
- `GET /api/theories` - List all aging theories
- `GET /api/theories/search` - Search theories
- `GET /api/theories/{id}` - Get theory details
- `GET /api/theories/{id}/articles` - Get articles for theory
- `GET /api/theories/stats/summary` - Theory statistics
- `GET /api/articles/{id}/theories` - Get theories for article

### Queue & Status
- `GET /api/queue/status` - Queue statistics
- `GET /api/sources` - Database source statistics
- `GET /api/costs` - AI model usage costs
- `GET /health` - Service health check

### Export (CSV)
- `GET /api/export/articles` - Export articles to CSV
- `GET /api/export/analyses` - Export analyses to CSV
- `GET /api/export/theories` - Export theories to CSV
- `GET /api/export/article-theories` - Export article-theory links to CSV
- `GET /api/export/full` - Export complete dataset to CSV

## Project Structure

```
hackaton/
├── agents/                    # AI agents
│   ├── discovery_agent.py     # Discovery agent
│   ├── analysis_agent.py      # Analysis agent
│   ├── analysis_agent_worker.py  # Worker process
│   └── tools/                 # LangChain tools
│       ├── web_search_tool.py
│       ├── crawl4ai_tool.py
│       ├── database_tool.py
│       ├── pdf_parser_tool.py
│       └── theory_extraction_tool.py
├── api/                       # FastAPI routes
│   ├── routes/
│   │   ├── articles.py
│   │   ├── theories.py
│   │   ├── discovery.py
│   │   ├── queue.py
│   │   ├── sources.py
│   │   └── costs.py
│   └── schemas.py             # Pydantic models
├── db/                        # Database layer
│   ├── models.py              # SQLAlchemy models
│   ├── database.py            # DB connection
│   └── repository.py          # Data access layer
├── task_queue/                # Redis task queue
│   ├── redis_client.py
│   └── task_queue.py
├── services/                  # Business logic
│   ├── discovery_service.py
│   ├── analysis_service.py
│   ├── analysis_worker.py
│   ├── theory_classification_service.py
│   └── pdf_parser.py
├── crawlers/                  # Source-specific crawlers
│   ├── base.py
│   ├── pubmed.py
│   └── pmc.py
├── prompts/                   # AI prompt templates (Jinja2)
│   ├── discovery_agent_system.j2
│   ├── analysis_agent_system.j2
│   ├── theory_extraction.j2
│   ├── aging_theory_analysis.j2
│   └── article_classififcation.j2
├── alembic/                   # Database migrations
├── app.py                     # FastAPI application
├── config.py                  # Configuration
├── docker-compose.yml         # Docker services
└── pyproject.toml            # Dependencies (uv)
```

## Configuration

### AI Models

The service uses Nebius AI Studio (open-source LLM models):

- Default: `meta-llama/Meta-Llama-3.1-8B-Instruct`
- Available: `Meta-Llama-3.1-70B-Instruct`, `Meta-Llama-3.1-405B-Instruct`

Configure in `.env`:
```env
LLM_DEFAULT_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
DISCOVERY_LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
ANALYSIS_LLM_MODEL=meta-llama/Meta-Llama-3.1-70B-Instruct
THEORY_LLM_MODEL=meta-llama/Meta-Llama-3.1-8B-Instruct
```

### Worker Configuration

```env
MAX_CONCURRENT_ANALYSES=3      # Concurrent analysis workers
WORKER_POLL_INTERVAL=5         # Seconds between queue polls
PDF_STORAGE_PATH=data/pdfs     # PDF storage directory
```

## Development

### Database Migrations

Create new migration:
```bash
uv run alembic revision --autogenerate -m "description"
```

Apply migrations:
```bash
uv run alembic upgrade head
```

Rollback migration:
```bash
uv run alembic downgrade -1
```

### Adding Dependencies

```bash
uv add package-name
```

### Code Style

- Use async functions where possible
- Use loguru for logging (not print)
- Follow PEP 8 style guidelines

## API Keys Setup

### NCBI API Key (PubMed/PMC)

1. Create account at https://account.ncbi.nlm.nih.gov/
2. Sign in → Account Settings
3. API Key Management → Create API Key
4. Copy key to `.env`

Benefits:
- 10 requests/second (vs 3 without key)
- Required for large-scale retrieval

### Nebius AI Studio

1. Get API key from https://nebius.ai/
2. Add to `.env` as `NEBIUS_API_KEY`

## Cost Tracking

The service tracks AI model usage costs automatically:

- Input/output tokens per model
- Cost per request
- Total costs by model
- Costs by endpoint/agent

Nebius pricing (per 1M tokens):
- Llama-3.1-8B: $0.10 input, $0.10 output
- Llama-3.1-70B: $0.80 input, $0.80 output
- Llama-3.1-405B: $4.00 input, $4.00 output

## Limitations

- NCBI API rate limits: 10 req/sec with key, 3 req/sec without
- Redis required for task queue functionality
- PDF parsing depends on article availability
- Theory extraction quality depends on abstract/full-text availability

## Contributing

We welcome contributions!

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License.

## Acknowledgments

- NCBI for PubMed and PMC access
- Nebius AI Studio for LLM infrastructure
- LangChain for agent framework
- Crawl4AI for web crawling capabilities

## Team

Made with ❤️ by **bioloshki team**:
- Mariia BAI
- Ivan MATVEEV

For the [HackAging: Theories of Aging Challenge](https://www.hackaging.ai/challenges/aging-theories/)

## Contact

- Open an issue for bug reports
- Contact maintainers for questions
- GitHub: [blackbalancef/aging-theories](https://github.com/blackbalancef/aging-theories)

---

**Status**: Active Development | **Version**: 1.0.0 | **Last Updated**: October 2025
