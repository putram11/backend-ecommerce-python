#!/bin/bash

# Initial migration script for database setup
echo "Setting up database migrations..."

# Initialize Alembic if not already done
if [ ! -d "app/db/migrations/versions" ]; then
    echo "Initializing Alembic..."
    cd app && alembic init db/migrations
fi

# Create initial migration
echo "Creating initial migration..."
cd app && alembic revision --autogenerate -m "Initial migration: create all tables"

# Run migrations
echo "Running migrations..."
cd app && alembic upgrade head

echo "Database setup complete!"