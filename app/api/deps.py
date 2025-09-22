from typing import Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_token
from app.db.session import get_session
from app.db import crud
from app.db.models import User

security = HTTPBearer()


async def get_db() -> AsyncSession:
    """Dependency to get database session"""
    async for session in get_session():
        yield session


async def get_current_user(
    db: AsyncSession = Depends(get_db),
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> User:
    """Get current authenticated user from JWT token"""
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        user_id = verify_token(credentials.credentials, token_type="access")
        if user_id is None:
            raise credentials_exception
    except Exception:
        raise credentials_exception
    
    user = await crud.user.get(db, id=user_id)
    if user is None:
        raise credentials_exception
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Inactive user"
        )
    
    return user


async def get_current_admin_user(
    current_user: User = Depends(get_current_user)
) -> User:
    """Dependency to require admin privileges"""
    
    if not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not enough permissions"
        )
    
    return current_user


async def get_current_user_optional(
    db: AsyncSession = Depends(get_db),
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
) -> Optional[User]:
    """Get current user if token is provided, otherwise return None"""
    
    if not credentials:
        return None
    
    try:
        user_id = verify_token(credentials.credentials, token_type="access")
        if user_id is None:
            return None
        
        user = await crud.user.get(db, id=user_id)
        if user and user.is_active:
            return user
    except Exception:
        pass
    
    return None