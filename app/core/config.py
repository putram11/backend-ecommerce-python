from typing import List
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True)
    
    # App Configuration
    APP_HOST: str = Field(default="0.0.0.0")
    APP_PORT: int = Field(default=8000)
    PYTHON_ENV: str = Field(default="development")
    
    # Database Configuration
    DATABASE_URL: str = Field(...)
    
    # MinIO / S3 Configuration
    MINIO_ENDPOINT: str = Field(...)
    MINIO_ACCESS_KEY: str = Field(...)
    MINIO_SECRET_KEY: str = Field(...)
    MINIO_BUCKET: str = Field(default="diecast")
    S3_USE_SSL: bool = Field(default=False)
    
    # JWT Configuration
    JWT_SECRET_KEY: str = Field(...)
    JWT_ACCESS_TOKEN_EXPIRES_MINUTES: int = Field(default=60)
    JWT_REFRESH_TOKEN_EXPIRES_DAYS: int = Field(default=30)
    JWT_ALGORITHM: str = Field(default="HS256")
    
    # CORS Configuration
    FRONTEND_URL: str = Field(default="http://localhost:3000")
    ALLOW_ALL_ORIGINS: bool = Field(default=False)
    
    # Midtrans Configuration
    MIDTRANS_SERVER_KEY: str = Field(...)
    MIDTRANS_CLIENT_KEY: str = Field(...)
    MIDTRANS_IS_PRODUCTION: bool = Field(default=False)
    
    # Frontend Configuration
    FRONTEND_URL: str = Field(default="http://localhost:3000")
    
    # Admin Configuration
    ADMIN_EMAIL: str = Field(default="admin@localhost")
    
    # CORS Origins
    
    @property
    def ALLOWED_ORIGINS(self) -> List[str]:
        if self.ALLOW_ALL_ORIGINS:
            return ["*"]
        return ["http://localhost:3000", "http://127.0.0.1:3000", self.FRONTEND_URL]    @property
    def midtrans_base_url(self) -> str:
        if self.MIDTRANS_IS_PRODUCTION:
            return "https://app.midtrans.com"
        return "https://app.sandbox.midtrans.com"
    
    @property
    def midtrans_api_url(self) -> str:
        if self.MIDTRANS_IS_PRODUCTION:
            return "https://api.midtrans.com"
        return "https://api.sandbox.midtrans.com"


settings = Settings()