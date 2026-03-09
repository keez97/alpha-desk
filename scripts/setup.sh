#!/bin/bash
# AlphaDesk Factor Backtester - Local Development Setup
# This script initializes PostgreSQL, runs migrations, and installs dependencies

set -e

echo "================================"
echo "AlphaDesk Setup Script"
echo "================================"
echo ""

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if docker-compose is available
if ! command -v docker-compose &> /dev/null; then
    echo "WARNING: docker-compose not found. Trying 'docker compose'..."
    if ! docker compose version &> /dev/null; then
        echo "ERROR: Docker Compose is not available."
        exit 1
    fi
    DOCKER_COMPOSE="docker compose"
else
    DOCKER_COMPOSE="docker-compose"
fi

echo "Step 1: Starting PostgreSQL container..."
$DOCKER_COMPOSE up -d postgres pgadmin
echo "Waiting for PostgreSQL to be ready..."
sleep 5

echo ""
echo "Step 2: Running database migrations..."
cd "$(dirname "$0")/../backend"
if command -v alembic &> /dev/null; then
    alembic upgrade head
else
    echo "WARNING: Alembic not found. Install dependencies first with: pip install -r requirements.txt"
fi

echo ""
echo "Step 3: Installing Python dependencies..."
pip install -r requirements.txt

echo ""
echo "Step 4: Installing frontend dependencies..."
cd ../frontend
npm install

echo ""
echo "================================"
echo "Setup Complete!"
echo "================================"
echo ""
echo "PostgreSQL Database:"
echo "  Host: localhost"
echo "  Port: 5432"
echo "  Database: alphadesk"
echo "  User: alphadesk"
echo "  Password: alphadesk_dev"
echo ""
echo "pgAdmin:"
echo "  URL: http://localhost:5050"
echo "  Email: admin@alphadesk.dev"
echo "  Password: admin"
echo ""
echo "Next steps:"
echo "  1. Copy .env.example to .env and update any API keys"
echo "  2. Run: ./scripts/run_dev.sh"
echo ""
