import pytest
import asyncio
from typing import AsyncGenerator
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.db.base import Base
from app.db.session import get_session
from app.core.config import settings

# Test database URL (use different database for tests)
TEST_DATABASE_URL = settings.DATABASE_URL.replace("/diecastdb", "/test_diecastdb")

# Create test engine
test_engine = create_async_engine(TEST_DATABASE_URL, echo=False)
TestingSessionLocal = sessionmaker(
    test_engine, class_=AsyncSession, expire_on_commit=False
)


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def create_test_database():
    """Create test database tables."""
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with test_engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest.fixture
async def db_session(create_test_database) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async with TestingSessionLocal() as session:
        yield session


@pytest.fixture
async def client(db_session: AsyncSession) -> AsyncGenerator[AsyncClient, None]:
    """Create a test client."""
    
    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_session] = override_get_db
    
    async with AsyncClient(app=app, base_url="http://testserver") as ac:
        yield ac
    
    app.dependency_overrides.clear()


@pytest.fixture
async def admin_user(db_session: AsyncSession):
    """Create an admin user for testing."""
    from app.db.crud import user
    
    admin = await user.create(
        db_session,
        email="admin@test.com",
        password="testpassword123",
        full_name="Test Admin",
        is_admin=True
    )
    return admin


@pytest.fixture
async def regular_user(db_session: AsyncSession):
    """Create a regular user for testing."""
    from app.db.crud import user
    
    regular = await user.create(
        db_session,
        email="user@test.com", 
        password="testpassword123",
        full_name="Test User",
        is_admin=False
    )
    return regular


@pytest.fixture
async def auth_headers(client: AsyncClient, regular_user):
    """Get authentication headers for regular user."""
    login_data = {
        "email": "user@test.com",
        "password": "testpassword123"
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
async def admin_headers(client: AsyncClient, admin_user):
    """Get authentication headers for admin user."""
    login_data = {
        "email": "admin@test.com",
        "password": "testpassword123"
    }
    response = await client.post("/api/v1/auth/login", json=login_data)
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}