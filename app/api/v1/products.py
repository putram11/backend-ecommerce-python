from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from slugify import slugify
import secrets

from ..api.deps import get_db, get_current_admin_user, get_current_user_optional
from ..db import crud
from ..schemas import (
    Product, ProductCreate, ProductUpdate, ProductListResponse,
    ProductList
)

router = APIRouter()


@router.get("/", response_model=ProductListResponse)
async def read_products(
    page: int = Query(default=1, ge=1),
    per_page: int = Query(default=20, ge=1, le=100),
    search: Optional[str] = Query(default=None),
    category: Optional[UUID] = Query(default=None),
    min_price: Optional[float] = Query(default=None, ge=0),
    max_price: Optional[float] = Query(default=None, ge=0),
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """
    Get products with pagination, search, and filters.
    Public endpoint - shows only published products unless user is admin.
    """
    
    # Only show published products for non-admin users
    is_published = None if (current_user and current_user.is_admin) else True
    
    skip = (page - 1) * per_page
    
    products = await crud.product.get_multi(
        db,
        skip=skip,
        limit=per_page,
        search=search,
        category_id=str(category) if category else None,
        min_price=min_price,
        max_price=max_price,
        is_published=is_published
    )
    
    # Convert to ProductList format with primary image
    product_list = []
    for product in products:
        primary_image = None
        if product.images:
            # Find primary image or use first one
            primary_image = next(
                (img for img in product.images if img.is_primary),
                product.images[0] if product.images else None
            )
        
        product_item = ProductList(
            id=product.id,
            sku=product.sku,
            name=product.name,
            price=product.price,
            stock=product.stock,
            is_published=product.is_published,
            brand=product.brand,
            category=product.category,
            primary_image=primary_image
        )
        product_list.append(product_item)
    
    # For simplicity, we're not doing a separate count query here
    # In production, you might want to add a count method to CRUD
    total = len(product_list)  # This is approximate
    pages = (total + per_page - 1) // per_page
    
    return ProductListResponse(
        items=product_list,
        total=total,
        page=page,
        per_page=per_page,
        pages=pages
    )


@router.get("/{product_id}", response_model=Product)
async def read_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """Get product by ID"""
    
    product = await crud.product.get(db, id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if user can view unpublished products
    if not product.is_published and (not current_user or not current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return product


@router.get("/sku/{sku}", response_model=Product)
async def read_product_by_sku(
    sku: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user_optional)
):
    """Get product by SKU"""
    
    product = await crud.product.get_by_sku(db, sku=sku)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Check if user can view unpublished products
    if not product.is_published and (not current_user or not current_user.is_admin):
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    return product


@router.post("/", response_model=Product)
async def create_product(
    product_in: ProductCreate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """Create new product (admin only)"""
    
    # Generate SKU if not provided
    if not product_in.sku:
        # Generate SKU from product name + random string
        base_sku = slugify(product_in.name[:20], separator="-").upper()
        random_suffix = secrets.token_hex(3).upper()
        sku = f"{base_sku}-{random_suffix}"
    else:
        sku = product_in.sku
    
    # Check if SKU already exists
    existing_product = await crud.product.get_by_sku(db, sku=sku)
    if existing_product:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product with this SKU already exists"
        )
    
    # Verify category exists if provided
    if product_in.category_id:
        category = await crud.category.get(db, id=product_in.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )
    
    product_data = product_in.model_dump()
    product_data["sku"] = sku
    
    product = await crud.product.create(db, **product_data)
    return product


@router.put("/{product_id}", response_model=Product)
async def update_product(
    product_id: UUID,
    product_update: ProductUpdate,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """Update product (admin only)"""
    
    product = await crud.product.get(db, id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    # Verify category exists if being updated
    if product_update.category_id:
        category = await crud.category.get(db, id=product_update.category_id)
        if not category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category not found"
            )
    
    # Update only provided fields
    update_data = product_update.model_dump(exclude_unset=True)
    
    product = await crud.product.update(db, db_obj=product, **update_data)
    return product


@router.delete("/{product_id}")
async def delete_product(
    product_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """Delete product (admin only)"""
    
    product = await crud.product.get(db, id=product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    await db.delete(product)
    await db.commit()
    
    return {"detail": "Product deleted successfully"}