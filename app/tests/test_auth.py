from httpx import AsyncClient


class TestAuth:
    """Test authentication endpoints."""
    
    async def test_register_user(self, client: AsyncClient):
        """Test user registration."""
        user_data = {
            "email": "newuser@test.com",
            "password": "testpassword123",
            "full_name": "New Test User"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == user_data["email"]
        assert data["user"]["full_name"] == user_data["full_name"]
        assert not data["user"]["is_admin"]
    
    async def test_register_duplicate_email(self, client: AsyncClient, regular_user):
        """Test registration with duplicate email."""
        user_data = {
            "email": "user@test.com",  # Already exists from fixture
            "password": "testpassword123", 
            "full_name": "Duplicate User"
        }
        
        response = await client.post("/api/v1/auth/register", json=user_data)
        assert response.status_code == 400
        assert "already exists" in response.json()["detail"]
    
    async def test_login_valid_credentials(self, client: AsyncClient, regular_user):
        """Test login with valid credentials."""
        login_data = {
            "email": "user@test.com",
            "password": "testpassword123"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 200
        
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["user"]["email"] == login_data["email"]
    
    async def test_login_invalid_credentials(self, client: AsyncClient, regular_user):
        """Test login with invalid credentials."""
        login_data = {
            "email": "user@test.com",
            "password": "wrongpassword"
        }
        
        response = await client.post("/api/v1/auth/login", json=login_data)
        assert response.status_code == 401
        assert "Incorrect email or password" in response.json()["detail"]
    
    async def test_get_current_user(self, client: AsyncClient, auth_headers):
        """Test getting current user info."""
        response = await client.get("/api/v1/auth/me", headers=auth_headers)
        assert response.status_code == 200
        
        data = response.json()
        assert data["email"] == "user@test.com"
        assert data["full_name"] == "Test User"
        assert not data["is_admin"]
    
    async def test_get_current_user_no_auth(self, client: AsyncClient):
        """Test getting current user without authentication."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 403  # No auth header provided
    
    async def test_refresh_token(self, client: AsyncClient, regular_user):
        """Test refresh token functionality."""
        # First login to get tokens
        login_data = {
            "email": "user@test.com", 
            "password": "testpassword123"
        }
        
        login_response = await client.post("/api/v1/auth/login", json=login_data)
        refresh_token = login_response.json()["refresh_token"]
        
        # Use refresh token to get new access token
        refresh_data = {"refresh_token": refresh_token}
        response = await client.post("/api/v1/auth/refresh", json=refresh_data)
        
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"