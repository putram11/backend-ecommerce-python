from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from slugify import slugify

from ..api.deps import get_db, get_current_admin_user
from ..db import crud
from ..schemas import Category, CategoryCreate

router = APIRouter()


@router.get("/", response_model=List[Category])
async def read_categories(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db)
):
    """Get all categories (public endpoint)"""
    
    categories = await crud.category.get_multi(db, skip=skip, limit=limit)
    return categories


@router.get("/{category_id}", response_model=Category)
async def read_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db)
):
    """Get category by ID"""
    
    category = await crud.category.get(db, id=category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.get("/slug/{slug}", response_model=Category)
async def read_category_by_slug(
    slug: str,
    db: AsyncSession = Depends(get_db)
):
    """Get category by slug"""
    
    category = await crud.category.get_by_slug(db, slug=slug)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    return category


@router.post("/", response_model=Category)
async def create_category(
    category_in: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """Create new category (admin only)"""
    
    # Check if category name already exists
    existing_category = await crud.category.get_by_slug(db, slug=category_in.slug)
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this slug already exists"
        )
    
    # Auto-generate slug from name if not provided or validate provided slug
    if not category_in.slug:
        slug = slugify(category_in.name)
    else:
        slug = category_in.slug
    
    # Verify slug is unique
    existing_category = await crud.category.get_by_slug(db, slug=slug)
    if existing_category:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Category with this slug already exists"
        )
    
    category = await crud.category.create(
        db,
        name=category_in.name,
        slug=slug,
        description=category_in.description
    )
    return category


@router.put("/{category_id}", response_model=Category)
async def update_category(
    category_id: UUID,
    category_update: CategoryCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """Update category (admin only)"""
    
    category = await crud.category.get(db, id=category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check if new slug conflicts with existing category
    if category_update.slug != category.slug:
        existing_category = await crud.category.get_by_slug(db, slug=category_update.slug)
        if existing_category and existing_category.id != category_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category with this slug already exists"
            )
    
    # Update category
    for field, value in category_update.model_dump().items():
        setattr(category, field, value)
    
    await db.commit()
    await db.refresh(category)
    
    return category


@router.delete("/{category_id}")
async def delete_category(
    category_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """Delete category (admin only)"""
    
    category = await crud.category.get(db, id=category_id)
    if not category:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Category not found"
        )
    
    # Check if category has products
    products = await crud.product.get_multi(
        db, category_id=str(category_id), limit=1
    )
    if products:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete category that has products. Remove products first."
        )
    
    await db.delete(category)
    await db.commit()
    
    return {"detail": "Category deleted successfully"}