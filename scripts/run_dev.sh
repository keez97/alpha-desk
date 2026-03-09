#!/bin/bash
# AlphaDesk Factor Backtester - Development Run Script
# Starts backend and frontend servers in parallel

set -e

PROJECT_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
echo "================================"
echo "AlphaDesk Development Server"
echo "================================"
echo ""
echo "Project Root: $PROJECT_ROOT"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Cleanup function to kill background processes on exit
cleanup() {
    echo ""
    echo -e "${YELLOW}Shutting down servers...${NC}"
    kill $(jobs -p) 2>/dev/null || true
    echo -e "${GREEN}Servers stopped.${NC}"
}

trap cleanup EXIT

# Check if .env exists
if [ ! -f "$PROJECT_ROOT/.env" ]; then
    echo -e "${RED}ERROR: .env file not found${NC}"
    echo "Please copy .env.example to .env and fill in your API keys:"
    echo "  cp .env.example .env"
    exit 1
fi

# Check if Docker containers are running
echo "Checking PostgreSQL connection..."
if ! docker ps | grep -q alphadesk-postgres; then
    echo -e "${YELLOW}PostgreSQL container not running. Starting it...${NC}"
    docker-compose up -d postgres
    sleep 3
fi

echo ""
echo -e "${GREEN}Starting Backend (FastAPI)...${NC}"
cd "$PROJECT_ROOT/backend"
uvicorn backend.main:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend PID: $BACKEND_PID"

sleep 2

echo ""
echo -e "${GREEN}Starting Frontend (Vite)...${NC}"
cd "$PROJECT_ROOT/frontend"
npm run dev &
FRONTEND_PID=$!
echo "Frontend PID: $FRONTEND_PID"

echo ""
echo "================================"
echo "Servers Running"
echo "================================"
echo -e "${GREEN}Backend:  http://localhost:8000${NC}"
echo -e "${GREEN}Docs:     http://localhost:8000/docs${NC}"
echo -e "${GREEN}Frontend: http://localhost:5173${NC}"
echo ""
echo "Press Ctrl+C to stop all servers"
echo ""

# Wait for background processes
wait
