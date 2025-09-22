# Just commands for backend e-commerce diecast development
# Run `just` to see all available commands

# Set default shell
set shell := ["bash", "-c"]

# Variables
DOCKER_COMPOSE := "docker compose"
APP_CONTAINER := "backend"
DB_CONTAINER := "db"

# Show all available commands
default:
    @just --list

# 🚀 Development Commands

# Start development environment (build and run all services)
dev:
    @echo "🚀 Starting development environment..."
    @if [ ! -f .env ]; then \
        echo "📝 Creating .env from template..."; \
        cp .env.example .env; \
        echo "⚠️  Please update .env with your configuration!"; \
    fi
    {{DOCKER_COMPOSE}} up --build -d
    @echo "⏳ Waiting for services to start..."
    @sleep 15
    @echo "🗄️  Running database migrations..."
    {{DOCKER_COMPOSE}} exec {{APP_CONTAINER}} bash -c "cd /app && alembic upgrade head"
    @echo "✅ Development environment ready!"
    @echo ""
    @echo "🔗 Available services:"
    @echo "   📡 Backend API: http://localhost:8000"
    @echo "   📚 API Docs: http://localhost:8000/docs"
    @echo "   📖 ReDoc: http://localhost:8000/redoc"
    @echo "   🗄️  MinIO Console: http://localhost:9091 (minioadmin/minioadmin123)"
    @echo "   🐘 pgAdmin: http://localhost:8080 (admin@admin.com/admin)"

# Start without running migrations (for first time setup)
dev-no-migrate:
    @echo "🚀 Starting development environment (no migrations)..."
    @if [ ! -f .env ]; then \
        echo "📝 Creating .env from template..."; \
        cp .env.example .env; \
        echo "⚠️  Please update .env with your configuration!"; \
    fi
    {{DOCKER_COMPOSE}} up --build -d
    @echo "⏳ Waiting for services to start..."
    @sleep 15
    @echo "✅ Development environment ready!"
    @echo ""
    @echo "🔗 Available services:"
    @echo "   📡 Backend API: http://localhost:8000"
    @echo "   📚 API Docs: http://localhost:8000/docs"
    @echo "   📖 ReDoc: http://localhost:8000/redoc"
    @echo "   🗄️  MinIO Console: http://localhost:9091 (minioadmin/minioadmin123)"
    @echo "   🐘 pgAdmin: http://localhost:8080 (admin@admin.com/admin)"

# Stop all services
stop:
    @echo "🛑 Stopping all services..."
    {{DOCKER_COMPOSE}} down

# Restart all services
restart: stop dev

# Build without cache
build:
    @echo "🔨 Building containers..."
    {{DOCKER_COMPOSE}} build --no-cache

# 📊 Database Commands

# Run database migrations
migrate:
    @echo "🗄️  Running database migrations..."
    {{DOCKER_COMPOSE}} exec {{APP_CONTAINER}} bash -c "cd /app && alembic upgrade head"

# Create new migration
migration MESSAGE="auto migration":
    @echo "📝 Creating new migration: {{MESSAGE}}"
    {{DOCKER_COMPOSE}} exec {{APP_CONTAINER}} bash -c "cd /app && alembic revision --autogenerate -m '{{MESSAGE}}'"

# Reset database (WARNING: destroys all data)
db-reset:
    @echo "⚠️  WARNING: This will destroy all database data!"
    @read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
    {{DOCKER_COMPOSE}} exec {{DB_CONTAINER}} psql -U postgres -d postgres -c "DROP DATABASE IF EXISTS diecastdb;"
    {{DOCKER_COMPOSE}} exec {{DB_CONTAINER}} psql -U postgres -d postgres -c "CREATE DATABASE diecastdb;"
    @just migrate

# Open database shell
db-shell:
    @echo "🐘 Opening PostgreSQL shell..."
    {{DOCKER_COMPOSE}} exec {{DB_CONTAINER}} psql -U postgres -d diecastdb

# 🧪 Testing Commands

# Run all tests
test:
    @echo "🧪 Running tests..."
    {{DOCKER_COMPOSE}} exec {{APP_CONTAINER}} pytest

# Run tests with coverage
test-cov:
    @echo "🧪 Running tests with coverage..."
    {{DOCKER_COMPOSE}} exec {{APP_CONTAINER}} pytest --cov=app --cov-report=term-missing

# Run specific test file
test-file FILE:
    @echo "🧪 Running test file: {{FILE}}"
    {{DOCKER_COMPOSE}} exec {{APP_CONTAINER}} pytest tests/{{FILE}}

# 🔍 Development Tools

# View logs
logs SERVICE="":
    @if [ "{{SERVICE}}" = "" ]; then \
        {{DOCKER_COMPOSE}} logs -f; \
    else \
        {{DOCKER_COMPOSE}} logs -f {{SERVICE}}; \
    fi

# Open shell in backend container
shell:
    @echo "🐚 Opening shell in backend container..."
    {{DOCKER_COMPOSE}} exec {{APP_CONTAINER}} bash

# Check code formatting with ruff
lint:
    @echo "🔍 Checking code with ruff..."
    {{DOCKER_COMPOSE}} exec {{APP_CONTAINER}} ruff check app/

# Format code with ruff
format:
    @echo "✨ Formatting code with ruff..."
    {{DOCKER_COMPOSE}} exec {{APP_CONTAINER}} ruff format app/

# Check and fix code
fix:
    @echo "🔧 Fixing code issues..."
    {{DOCKER_COMPOSE}} exec {{APP_CONTAINER}} ruff check --fix app/

# 📦 Admin Commands

# Create admin user (interactive)
create-admin:
    @echo "👤 Creating admin user..."
    {{DOCKER_COMPOSE}} exec {{APP_CONTAINER}} python -c \
    'import asyncio; \
    from app.db.session import AsyncSessionLocal; \
    from app.db.crud import user; \
    async def create_admin(): \
        async with AsyncSessionLocal() as db: \
            email = input("Admin email: "); \
            password = input("Admin password: "); \
            full_name = input("Full name: "); \
            existing = await user.get_by_email(db, email=email); \
            if existing: \
                print("❌ User already exists"); \
                return; \
            admin = await user.create(db, email=email, password=password, full_name=full_name, is_admin=True); \
            print(f"✅ Admin user created: {admin.email}"); \
    asyncio.run(create_admin())'

# 🧹 Cleanup Commands

# Clean up Docker resources
clean:
    @echo "🧹 Cleaning up Docker resources..."
    {{DOCKER_COMPOSE}} down -v --remove-orphans
    docker system prune -f

# Remove all containers and volumes (DANGER!)
nuke:
    @echo "💥 WARNING: This will remove ALL containers and volumes!"
    @read -p "Are you sure? (y/N): " confirm && [ "$$confirm" = "y" ]
    {{DOCKER_COMPOSE}} down -v --remove-orphans
    docker system prune -a -f --volumes

# 📈 Monitoring Commands

# Show container status
status:
    @echo "📊 Container status:"
    {{DOCKER_COMPOSE}} ps

# Show resource usage
stats:
    @echo "📈 Resource usage:"
    docker stats --no-stream

# Health check
health:
    @echo "🏥 Health check:"
    @echo "Backend API:"
    @curl -s http://localhost:8000/health | grep -q "healthy" && echo "✅ Backend healthy" || echo "❌ Backend not accessible"
    @echo "\nMinIO:"
    @curl -s http://localhost:9091 > /dev/null && echo "✅ MinIO ready" || echo "❌ MinIO not accessible"
    @echo "\nDatabase:"
    @docker compose exec -T db psql -U postgres -d diecastdb -c "SELECT 1;" > /dev/null 2>&1 && echo "✅ Database ready" || echo "❌ Database not accessible"

# 🔄 Utility Commands

# Show environment info
env-info:
    @echo "🔧 Environment Information:"
    @echo "Docker Compose version:"
    @{{DOCKER_COMPOSE}} --version
    @echo ""
    @echo "Docker version:"
    @docker --version
    @echo ""
    @echo "Services status:"
    @{{DOCKER_COMPOSE}} ps

# Generate new JWT secret
jwt-secret:
    @echo "🔑 New JWT Secret Key:"
    @python -c "import secrets; print(secrets.token_urlsafe(32))"

# Show API endpoints
endpoints:
    @echo "🔗 API Endpoints:"
    @echo "Authentication:"
    @echo "  POST /api/v1/auth/register - User registration"
    @echo "  POST /api/v1/auth/login - User login"
    @echo "  GET  /api/v1/auth/me - Current user info"
    @echo ""
    @echo "Products:"
    @echo "  GET  /api/v1/products - List products"
    @echo "  POST /api/v1/products - Create product (admin)"
    @echo "  GET  /api/v1/products/{id} - Get product"
    @echo ""
    @echo "Images:"
    @echo "  POST /api/v1/products/{id}/images - Upload images (admin)"
    @echo ""
    @echo "Cart & Orders:"
    @echo "  GET  /api/v1/cart - Get cart"
    @echo "  POST /api/v1/cart/items - Add to cart"
    @echo "  POST /api/v1/orders - Create order"
    @echo ""
    @echo "Payments:"
    @echo "  POST /api/v1/payments/create - Create payment"
    @echo "  GET  /api/v1/payments/status/{id} - Payment status"

# 🎯 Quick Start Commands

# First time setup
setup:
    @echo "🎯 First time setup..."
    @if [ ! -f .env ]; then \
        cp .env.example .env; \
        echo "📝 Created .env file - please update with your configuration"; \
    fi
    @echo "🔨 Building containers..."
    {{DOCKER_COMPOSE}} build
    @echo "🚀 Starting services..."
    {{DOCKER_COMPOSE}} up -d
    @echo "⏳ Waiting for services..."
    @sleep 15
    @echo "🗄️  Setting up database..."
    {{DOCKER_COMPOSE}} exec {{APP_CONTAINER}} bash -c "cd /app && alembic upgrade head"
    @echo "✅ Setup complete!"
    @echo ""
    @echo "Next steps:"
    @echo "1. Update .env with your Midtrans keys"
    @echo "2. Visit http://localhost:8000/docs for API documentation"
    @echo "3. Run 'just create-admin' to create an admin user"

# Full development start (for daily use)
start: dev

# Production build (optimized)
prod-build:
    @echo "🏭 Building for production..."
    {{DOCKER_COMPOSE}} -f docker-compose.yml -f docker-compose.prod.yml build

# Backup database
backup:
    @echo "💾 Creating database backup..."
    @mkdir -p backups
    {{DOCKER_COMPOSE}} exec {{DB_CONTAINER}} pg_dump -U postgres diecastdb > backups/backup_$(date +%Y%m%d_%H%M%S).sql
    @echo "✅ Backup created in backups/ directory"