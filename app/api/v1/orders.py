from typing import List
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from decimal import Decimal
import secrets
import datetime

from ..api.deps import get_db, get_current_user, get_current_admin_user
from ..db import crud
from ..db.models import OrderItem, Order as OrderModel, OrderStatus
from ..schemas import Order, OrderCreate

router = APIRouter()


def generate_order_number() -> str:
    """Generate unique order number"""
    timestamp = datetime.datetime.now().strftime('%Y%m%d')
    random_part = secrets.token_hex(4).upper()
    return f"ORD-{timestamp}-{random_part}"


@router.post("/", response_model=Order)
async def create_order(
    order_data: OrderCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create new order from cart or custom items"""
    
    if not order_data.items:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order must have at least one item"
        )
    
    # Calculate total amount and prepare order items
    total_amount = Decimal('0')
    order_items_data = []
    
    async with db.begin():  # Use transaction for inventory management
        for item in order_data.items:
            # Get product
            product = await crud.product.get(db, id=item.product_id)
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product {item.product_id} not found"
                )
            
            if not product.is_published:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Product {product.name} is not available"
                )
            
            # Check stock and reserve
            if product.stock < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient stock for {product.name}. Available: {product.stock}"
                )
            
            # Decrease stock atomically
            success = await crud.product.decrease_stock(
                db, product_id=str(product.id), quantity=item.quantity
            )
            if not success:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Could not reserve stock for {product.name}"
                )
            
            # Calculate item total
            item_total = product.price * item.quantity
            total_amount += item_total
            
            # Prepare order item data
            order_items_data.append({
                "product_id": product.id,
                "sku_snapshot": product.sku,
                "name_snapshot": product.name,
                "quantity": item.quantity,
                "price_snapshot": product.price
            })
        
        # Create order
        order_number = generate_order_number()
        order = await crud.order.create(
            db,
            user_id=current_user.id,
            order_number=order_number,
            total_amount=total_amount,
            status=OrderStatus.PENDING,
            shipping_address=order_data.shipping_address.model_dump(),
            notes=order_data.notes
        )
        
        # Create order items
        for item_data in order_items_data:
            order_item = OrderItem(
                order_id=order.id,
                **item_data
            )
            db.add(order_item)
        
        await db.commit()
        await db.refresh(order)
    
    return order


@router.get("/", response_model=List[Order])
async def get_user_orders(
    skip: int = 0,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get current user's orders"""
    
    # For simplicity, we'll get orders manually
    # In production, you might want to add this to CRUD
    from sqlalchemy import select
    from sqlalchemy.orm import selectinload
    
    result = await db.execute(
        select(OrderModel)
        .options(
            selectinload(OrderModel.items).selectinload(OrderItem.product),
            selectinload(OrderModel.payments)
        )
        .where(OrderModel.user_id == current_user.id)
        .offset(skip)
        .limit(limit)
        .order_by(OrderModel.created_at.desc())
    )
    
    orders = result.scalars().all()
    return orders


@router.get("/{order_id}", response_model=Order)
async def get_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get specific order by ID"""
    
    order = await crud.order.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user owns this order or is admin
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this order"
        )
    
    return order


@router.get("/number/{order_number}", response_model=Order)
async def get_order_by_number(
    order_number: str,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get order by order number"""
    
    order = await crud.order.get_by_order_number(db, order_number=order_number)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user owns this order or is admin
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to view this order"
        )
    
    return order


@router.put("/{order_id}/status")
async def update_order_status(
    order_id: UUID,
    new_status: str,
    db: AsyncSession = Depends(get_db),
    current_admin = Depends(get_current_admin_user)
):
    """Update order status (admin only)"""
    
    # Validate status
    valid_statuses = [status.value for status in OrderStatus]
    if new_status not in valid_statuses:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid status. Valid options: {valid_statuses}"
        )
    
    order = await crud.order.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Update status
    order.status = new_status
    await db.commit()
    
    return {"detail": f"Order status updated to {new_status}"}


@router.put("/{order_id}/cancel")
async def cancel_order(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Cancel order (user can cancel their own pending orders)"""
    
    order = await crud.order.get(db, id=order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check ownership
    if order.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to cancel this order"
        )
    
    # Check if order can be cancelled
    if order.status not in [OrderStatus.PENDING, OrderStatus.PENDING_PAYMENT]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot cancel order with status: {order.status}"
        )
    
    # Restore stock for cancelled items
    async with db.begin():
        for item in order.items:
            product = await crud.product.get(db, id=item.product_id)
            if product:
                product.stock += item.quantity
        
        # Update order status
        order.status = OrderStatus.CANCELED
        await db.commit()
    
    return {"detail": "Order cancelled successfully"}