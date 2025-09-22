from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from ..api.deps import get_db, get_current_user
from ..db import crud
from ..schemas import Cart, CartItemCreate

router = APIRouter()


@router.get("/", response_model=Cart)
async def get_cart(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get current user's cart"""
    
    cart = await crud.cart.get_or_create_for_user(db, str(current_user.id))
    return cart


@router.post("/items")
async def add_to_cart(
    item: CartItemCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Add item to cart"""
    
    # Verify product exists and is available
    product = await crud.product.get(db, id=item.product_id)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product not found"
        )
    
    if not product.is_published:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Product is not available"
        )
    
    if product.stock < item.quantity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {product.stock}"
        )
    
    # Get or create user's cart
    cart = await crud.cart.get_or_create_for_user(db, str(current_user.id))
    
    # Add item to cart
    cart_item = await crud.cart.add_item(
        db,
        cart_id=str(cart.id),
        product_id=str(item.product_id),
        quantity=item.quantity,
        price=float(product.price)
    )
    
    return {"detail": "Item added to cart", "cart_item_id": str(cart_item.id)}


@router.put("/items/{cart_item_id}")
async def update_cart_item(
    cart_item_id: UUID,
    quantity: int,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Update cart item quantity"""
    
    if quantity <= 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Quantity must be greater than 0"
        )
    
    # Get user's cart
    cart = await crud.cart.get_or_create_for_user(db, str(current_user.id))
    
    # Find cart item
    cart_item = None
    for item in cart.items:
        if item.id == cart_item_id:
            cart_item = item
            break
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    # Verify stock availability
    product = await crud.product.get(db, id=cart_item.product_id)
    if not product or product.stock < quantity:
        available_stock = product.stock if product else 0
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Insufficient stock. Available: {available_stock}"
        )
    
    # Update quantity
    cart_item.quantity = quantity
    await db.commit()
    
    return {"detail": "Cart item updated"}


@router.delete("/items/{cart_item_id}")
async def remove_from_cart(
    cart_item_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Remove item from cart"""
    
    # Get user's cart
    cart = await crud.cart.get_or_create_for_user(db, str(current_user.id))
    
    # Find cart item
    cart_item = None
    for item in cart.items:
        if item.id == cart_item_id:
            cart_item = item
            break
    
    if not cart_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Cart item not found"
        )
    
    # Remove item
    await db.delete(cart_item)
    await db.commit()
    
    return {"detail": "Item removed from cart"}


@router.delete("/")
async def clear_cart(
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Clear all items from cart"""
    
    # Get user's cart
    cart = await crud.cart.get_or_create_for_user(db, str(current_user.id))
    
    # Delete all items
    for item in cart.items:
        await db.delete(item)
    
    await db.commit()
    
    return {"detail": "Cart cleared"}