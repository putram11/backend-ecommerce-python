#!/bin/bash

# Development startup script
echo "Starting development environment..."

# Copy .env.example to .env if it doesn't exist
if [ ! -f .env ]; then
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo "Please update .env with your actual configuration values!"
fi

# Start Docker containers
echo "Starting Docker containers..."
docker-compose up --build -d

echo "Waiting for services to start..."
sleep 10

# Run database migrations
echo "Running database migrations..."
docker-compose exec backend bash -c "cd /app && alembic upgrade head"

echo "Development environment is ready!"
echo ""
echo "Services available at:"
echo "  Backend API: http://localhost:8000"
echo "  API Docs: http://localhost:8000/docs"
echo "  ReDoc: http://localhost:8000/redoc"
echo "  MinIO Console: http://localhost:9001"
echo "  pgAdmin: http://localhost:8080"
echo ""
echo "To view logs: docker-compose logs -f backend"
echo "To stop: docker-compose down"