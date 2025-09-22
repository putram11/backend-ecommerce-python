from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID

from app.api.deps import get_db, get_current_user
from app.db import crud
from app.db.models import OrderStatus
from app.schemas import PaymentCreate, PaymentResponse
from app.services.midtrans import midtrans_service

router = APIRouter()


@router.post("/create", response_model=PaymentResponse)
async def create_payment(
    payment_data: PaymentCreate,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Create Midtrans Snap transaction for order"""
    
    # Get order
    order = await crud.order.get(db, id=payment_data.order_id)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )
    
    # Check if user owns this order
    if order.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to create payment for this order"
        )
    
    # Check if order is in correct status
    if order.status not in [OrderStatus.PENDING, OrderStatus.PENDING_PAYMENT]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot create payment for order with status: {order.status}"
        )
    
    # Check if payment already exists for this order
    existing_payments = [p for p in order.payments if p.transaction_status in ['pending', 'settlement']]
    if existing_payments:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Payment already exists for this order"
        )
    
    try:
        # Prepare customer details
        customer_details = midtrans_service.prepare_customer_details(
            current_user, 
            order.shipping_address or {}
        )
        
        # Prepare item details
        item_details = midtrans_service.prepare_item_details(order.items)
        
        # Create Snap transaction
        snap_response = await midtrans_service.create_snap_transaction(
            order_id=order.order_number,
            gross_amount=float(order.total_amount),
            customer_details=customer_details,
            item_details=item_details
        )
        
        # Create payment record
        await crud.payment.create(
            db,
            order_id=order.id,
            midtrans_transaction_id=snap_response.get("order_id", order.order_number),
            payment_type="snap",
            transaction_status="pending",
            amount=order.total_amount,
            raw_payload=snap_response
        )
        
        # Update order status
        order.status = OrderStatus.PENDING_PAYMENT
        await db.commit()
        
        return PaymentResponse(
            snap_token=snap_response.get("token", ""),
            redirect_url=snap_response.get("redirect_url", ""),
            order_id=order.id
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment: {str(e)}"
        )


@router.get("/status/{order_id}")
async def get_payment_status(
    order_id: UUID,
    db: AsyncSession = Depends(get_db),
    current_user = Depends(get_current_user)
):
    """Get payment status for order"""
    
    # Get order
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
            detail="Not authorized to view payment status for this order"
        )
    
    # Get latest payment
    if not order.payments:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No payment found for this order"
        )
    
    latest_payment = max(order.payments, key=lambda p: p.created_at)
    
    try:
        # Get fresh status from Midtrans
        midtrans_status = await midtrans_service.get_transaction_status(
            order.order_number
        )
        
        # Update payment record with latest status
        latest_payment.transaction_status = midtrans_status.get("transaction_status", "pending")
        latest_payment.raw_payload = midtrans_status
        
        await db.commit()
        
        return {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "order_status": order.status,
            "payment_status": latest_payment.transaction_status,
            "payment_type": latest_payment.payment_type,
            "amount": float(latest_payment.amount),
            "transaction_time": midtrans_status.get("transaction_time"),
            "settlement_time": midtrans_status.get("settlement_time")
        }
        
    except Exception as e:
        # Return cached status if Midtrans API fails
        return {
            "order_id": str(order.id),
            "order_number": order.order_number,
            "order_status": order.status,
            "payment_status": latest_payment.transaction_status,
            "payment_type": latest_payment.payment_type,
            "amount": float(latest_payment.amount),
            "error": f"Could not fetch fresh status: {str(e)}"
        }