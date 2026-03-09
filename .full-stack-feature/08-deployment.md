# 08. Deployment & Infrastructure Configuration

## Overview

AlphaDesk Factor Backtester is configured as a **localhost development project** with proper local infrastructure setup. No cloud deployment is needed at this stage.

## Architecture

### Stack
- **Backend**: FastAPI (Python 3.10+)
- **Frontend**: React 18 + Vite
- **Database**: PostgreSQL 16 (migrating from SQLite)
- **Admin UI**: pgAdmin 4
- **ORM**: SQLModel
- **Migrations**: Alembic

### Services Topology
```
┌─────────────────────────────────────────┐
│         Development Machine             │
├─────────────────────────────────────────┤
│                                         │
│  ┌─────────────────┐                   │
│  │   Frontend      │                   │
│  │   (Vite Dev)    │                   │
│  │  :5173          │                   │
│  └────────┬────────┘                   │
│           │ HTTP                       │
│           ▼                            │
│  ┌─────────────────┐                   │
│  │   Backend       │                   │
│  │   (FastAPI)     │                   │
│  │  :8000          │                   │
│  └────────┬────────┘                   │
│           │ TCP                        │
│           ▼                            │
│  ┌─────────────────┐  ┌─────────────┐ │
│  │   PostgreSQL    │  │   pgAdmin   │ │
│  │   :5432         │  │   :5050     │ │
│  └─────────────────┘  └─────────────┘ │
│                                         │
└─────────────────────────────────────────┘
```

## Infrastructure Files

### 1. `docker-compose.yml` (Root Level)
Defines Docker services for local development:

**Services:**
- **postgres:16** - PostgreSQL database
  - Database: `alphadesk`
  - User: `alphadesk`
  - Password: `alphadesk_dev`
  - Port: `5432`
  - Volumes: Named volume `pgdata` for persistence
  - Health checks enabled

- **pgadmin** - Database administration UI
  - URL: `http://localhost:5050`
  - Email: `admin@alphadesk.dev`
  - Password: `admin`
  - Port: `5050`

**Network:** `alphadesk-network` (bridge)

**Usage:**
```bash
# Start all services
docker-compose up -d

# Start specific service
docker-compose up -d postgres

# Stop all services
docker-compose down

# View logs
docker-compose logs -f postgres
```

### 2. `.env.example` (Root Level)
Template for environment variables. Users should copy to `.env`:

```bash
cp .env.example .env
# Then fill in your API keys
```

**Key Variables:**
- `DATABASE_URL` - PostgreSQL connection string
- `ANTHROPIC_API_KEY` - Anthropic API key for Claude integration
- `OPENROUTER_API_KEY` - OpenRouter API key (optional)
- `FDS_API_KEY` - Financial Data Service API key
- `CLAUDE_MODEL` - Model identifier
- `CACHE_TTL_HOURS` - Cache time-to-live

### 3. `requirements.txt` (Backend)
Python dependencies with PostgreSQL support:

**New Dependencies:**
- `psycopg2-binary==2.9.9` - PostgreSQL adapter for Python
- `alembic==1.13.1` - Database migration tool

**Existing Dependencies:**
- FastAPI, Uvicorn, SQLModel
- yfinance, pandas, numpy, scipy
- APScheduler for scheduling

**Installation:**
```bash
cd backend
pip install -r requirements.txt
```

### 4. `scripts/setup.sh` (Shell Script)
Automated setup script for fresh installation:

**What it does:**
1. Checks Docker/docker-compose availability
2. Starts PostgreSQL and pgAdmin containers
3. Runs Alembic migrations
4. Installs Python dependencies
5. Installs frontend dependencies

**Usage:**
```bash
./scripts/setup.sh
```

**Prerequisites:**
- Docker and Docker Compose installed
- Python 3.10+ installed
- Node.js 18+ installed

### 5. `scripts/run_dev.sh` (Shell Script)
Development server launcher:

**What it does:**
1. Validates `.env` file exists
2. Ensures PostgreSQL container is running
3. Starts FastAPI backend (port 8000)
4. Starts Vite frontend dev server (port 5173)
5. Provides colored terminal output
6. Graceful shutdown on Ctrl+C

**Usage:**
```bash
./scripts/run_dev.sh
```

**Server URLs:**
- Backend API: `http://localhost:8000`
- API Docs: `http://localhost:8000/docs`
- Frontend: `http://localhost:5173`
- Database: `localhost:5432`

### 6. `scripts/seed_data.py` (Python Script)
Database seeding script:

**Loads:**
1. **Fama-French 5-Factor Model**
   - Market Risk (Mkt-RF)
   - Size (SMB)
   - Value (HML)
   - Profitability (RMW)
   - Investment (CMA)

2. **Sample Securities**
   - Top 50 S&P 500 companies
   - Company metadata (name, sector, industry)
   - Fetched from yfinance

3. **Price History**
   - 250 trading days of OHLCV data
   - Automatically fetched from Yahoo Finance

**Usage:**
```bash
python scripts/seed_data.py
```

**Features:**
- Idempotent (won't duplicate data)
- Error handling and progress reporting
- Batch commits for performance

## Database Migration Strategy

### Alembic Configuration
Located at `/alembic.ini` with migration scripts in `/alembic/versions/`

**Migration workflow:**
```bash
# Create a new migration
alembic revision --autogenerate -m "description"

# View pending migrations
alembic current

# Apply all pending migrations
alembic upgrade head

# Rollback to previous version
alembic downgrade -1
```

### Current Migrations
- PostgreSQL schema definition with all models
- Indexes for performance optimization
- Foreign key constraints

## Setup Instructions

### Initial Setup (First Time)
```bash
# 1. Clone the repository
git clone https://github.com/keez97/alpha-desk.git
cd alpha-desk

# 2. Run automated setup
./scripts/setup.sh

# 3. Configure environment
cp .env.example .env
# Edit .env and fill in your API keys

# 4. (Optional) Seed initial data
python scripts/seed_data.py

# 5. Start development servers
./scripts/run_dev.sh
```

### Quick Start (After First Setup)
```bash
# Start PostgreSQL
docker-compose up -d

# Run development servers
./scripts/run_dev.sh
```

### Stopping Services
```bash
# Stop all Docker services
docker-compose down

# Or just press Ctrl+C in dev server terminal
```

## Development Workflow

### File Structure
```
alpha-desk/
├── docker-compose.yml          # Docker services
├── .env                        # Local config (git-ignored)
├── .env.example                # Config template
├── alembic.ini                 # Migration config
├── scripts/
│   ├── setup.sh               # Initial setup
│   ├── run_dev.sh             # Run dev servers
│   └── seed_data.py           # Populate test data
├── backend/
│   ├── requirements.txt        # Python deps
│   ├── alembic/               # Database versions
│   └── main.py                # FastAPI app
├── frontend/
│   ├── package.json           # Node deps
│   └── vite.config.js         # Vite config
└── .full-stack-feature/
    └── 08-deployment.md       # This file
```

### Working with Database

**Connect to PostgreSQL:**
```bash
# Using psql
psql -h localhost -U alphadesk -d alphadesk

# Using pgAdmin
# Visit: http://localhost:5050
```

**View Migrations:**
```bash
alembic current  # Current version
alembic history  # All applied migrations
```

**Create New Migration:**
```bash
cd backend
alembic revision --autogenerate -m "Add new_column to users"
# Edit migration file if needed
alembic upgrade head
```

### Environment Variables

**Required:**
- `DATABASE_URL` - PostgreSQL connection string
- `ANTHROPIC_API_KEY` - For Claude API calls

**Optional:**
- `OPENROUTER_API_KEY` - For alternative LLM endpoints
- `FDS_API_KEY` - Financial data service
- `CACHE_TTL_HOURS` - Default: 4
- `CLAUDE_MODEL` - Default: claude-sonnet-4-20250514

### Troubleshooting

**PostgreSQL won't start:**
```bash
# Check if port 5432 is already in use
lsof -i :5432

# Remove old containers
docker-compose down -v
docker-compose up -d postgres
```

**Database migration conflicts:**
```bash
# View current state
alembic current

# Downgrade if needed
alembic downgrade -1

# Re-run setup
./scripts/setup.sh
```

**Frontend/Backend connection issues:**
```bash
# Verify FastAPI is running
curl http://localhost:8000/docs

# Check frontend dev server
curl http://localhost:5173

# View backend logs
docker-compose logs -f postgres
```

**Python dependency conflicts:**
```bash
# Create fresh virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r backend/requirements.txt
```

## Security Considerations

### Development Only
- Default database password is `alphadesk_dev` - **NOT PRODUCTION SAFE**
- pgAdmin credentials hardcoded - **FOR LOCAL ONLY**
- CORS likely permissive for dev - **CONFIGURE FOR PRODUCTION**

### Before Production
1. Use strong, randomly generated passwords
2. Enable SSL/TLS for database connections
3. Configure firewall rules
4. Set up proper authentication/authorization
5. Enable database backups
6. Use environment-specific configs
7. Implement rate limiting
8. Add API authentication tokens

## Performance Notes

### Database
- PostgreSQL 16 with connection pooling ready
- Alembic-managed schema with indexes
- Named volume for data persistence

### Frontend
- Vite dev server with HMR (Hot Module Replacement)
- Optimized build configuration

### Backend
- FastAPI with automatic API documentation
- SQLModel for type-safe ORM
- APScheduler for background tasks

## Next Steps

1. **Configure API Keys**: Edit `.env` with your keys
2. **Review Database Schema**: Check `alembic/versions/` for migrations
3. **Explore API**: Visit `http://localhost:8000/docs` after setup
4. **Check Frontend**: Open `http://localhost:5173` after setup
5. **Monitor Database**: Use pgAdmin at `http://localhost:5050`

## References

- **Docker Compose**: https://docs.docker.com/compose/
- **Alembic**: https://alembic.sqlalchemy.org/
- **FastAPI**: https://fastapi.tiangolo.com/
- **SQLModel**: https://sqlmodel.tiangolo.com/
- **React 18**: https://react.dev/
- **Vite**: https://vitejs.dev/
