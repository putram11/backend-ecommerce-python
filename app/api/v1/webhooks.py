from fastapi import APIRouter, Depends, Request
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ..api.deps import get_db
from ..db import crud
from ..db.models import OrderStatus
from ..services.midtrans import midtrans_service

router = APIRouter()


@router.post("/midtrans")
async def midtrans_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Handle Midtrans payment notification webhook"""
    
    try:
        # Get raw notification data
        notification_data = await request.json()
        
        logger.info(f"Received Midtrans notification: {notification_data}")
        
        # Process notification through Midtrans service
        processed_notification = await midtrans_service.handle_notification(notification_data)
        
        order_number = processed_notification["order_id"]
        payment_status = processed_notification["payment_status"]
        
        # Find order by order number
        order = await crud.order.get_by_order_number(db, order_number=order_number)
        if not order:
            logger.warning(f"Order not found for notification: {order_number}")
            return {"status": "error", "message": "Order not found"}
        
        # Find or create payment record
        payment = await crud.payment.get_by_midtrans_id(
            db, 
            midtrans_id=processed_notification["transaction_id"]
        )
        
        if not payment:
            # Create new payment record
            payment = await crud.payment.create(
                db,
                order_id=order.id,
                midtrans_transaction_id=processed_notification["transaction_id"],
                payment_type=processed_notification["payment_type"],
                transaction_status=processed_notification["transaction_status"],
                amount=order.total_amount,
                raw_payload=processed_notification["verified_data"]
            )
        else:
            # Update existing payment record
            payment.transaction_status = processed_notification["transaction_status"]
            payment.raw_payload = processed_notification["verified_data"]
        
        # Update order status based on payment status
        await _update_order_status(db, order, payment_status)
        
        await db.commit()
        
        logger.info(f"Successfully processed notification for order {order_number}: {payment_status}")
        
        return {"status": "success", "message": "Notification processed"}
        
    except Exception as e:
        logger.error(f"Error processing Midtrans notification: {e}")
        
        # Don't return 500 error to Midtrans, they will keep retrying
        # Instead log the error and return success to stop retries
        return {"status": "error", "message": str(e)}


async def _update_order_status(db: AsyncSession, order, payment_status: str):
    """Update order status based on payment status"""
    
    if payment_status in ["settlement", "capture"]:
        # Payment successful
        if order.status in [OrderStatus.PENDING, OrderStatus.PENDING_PAYMENT]:
            order.status = OrderStatus.PAID
            logger.info(f"Order {order.order_number} marked as PAID")
    
    elif payment_status in ["deny", "cancel", "expire", "failure"]:
        # Payment failed/cancelled
        if order.status == OrderStatus.PENDING_PAYMENT:
            order.status = OrderStatus.CANCELED
            
            # Restore inventory
            for item in order.items:
                product = await crud.product.get(db, id=item.product_id)
                if product:
                    product.stock += item.quantity
                    logger.info(f"Restored {item.quantity} stock for product {product.sku}")
            
            logger.info(f"Order {order.order_number} cancelled due to payment failure")
    
    elif payment_status == "pending":
        # Payment pending - keep current status unless it's PENDING
        if order.status == OrderStatus.PENDING:
            order.status = OrderStatus.PENDING_PAYMENT
    
    # Add more status mappings as needed
    else:
        logger.warning(f"Unknown payment status for order {order.order_number}: {payment_status}")


# Additional webhook endpoints for other payment providers can be added here
# For example:
# @router.post("/paypal")
# @router.post("/stripe")