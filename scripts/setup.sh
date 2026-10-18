#!/bin/bash
# Hannibal V2 Setup Script
# This script sets up the database and seeds demo data

set -e

echo "=== Hannibal V2 Setup ==="

# Check if Python packages are installed
echo "Checking Python packages..."
pip install --quiet fastapi uvicorn sqlmodel pgvector psycopg2-binary minio redis httpx 2>&1 | tail -1
echo "Packages installed."

# Try to connect to PostgreSQL
echo "Checking PostgreSQL..."
if docker ps | grep -q postgres; then
    echo "Docker PostgreSQL is running"
    # Wait for PostgreSQL to be ready
    for i in {1..30}; do
        if docker exec $(docker ps | grep postgres | awk '{print $1}') pg_isready -U hannibal 2>/dev/null; then
            echo "PostgreSQL is ready"
            break
        fi
        sleep 1
    done
else
    echo "No Docker PostgreSQL found - installing directly"
    # Try to install PostgreSQL
    apt-get update -qq 2>/dev/null && apt-get install -y -qq postgresql postgresql-contrib 2>&1 | tail -1
fi

# Create database user and database
echo "Setting up database..."
su - postgres -c "psql -c \"SELECT 1\" 2>/dev/null" || echo "Cannot connect as postgres user"

# Initialize the database tables
echo "Initializing database tables..."
python3 -c "
from apps.api.app.main import app, engine, create_db_and_tables
create_db_and_tables()
print('Database tables created successfully')
"

# Seed demo data
echo "Seeding demo data..."
python3 scripts/seed-demo-data.py

echo ""
echo "=== Setup Complete ==="
echo "Hannibal V2 is ready to run:"
echo "  API:  uvicorn apps.api.app.main:app --host 0.0.0.0 --port 8000"
echo "  Web:  cd apps/web && npm run dev"
echo ""
echo "Test the API:"
echo "  curl http://localhost:8000/"
echo "  curl -X POST http://localhost:8000/information-collector/extract"