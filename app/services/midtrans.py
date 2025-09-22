import base64
from typing import Dict, Any, Optional
import httpx
from loguru import logger

from ..core.config import settings


class MidtransService:
    def __init__(self):
        self.server_key = settings.MIDTRANS_SERVER_KEY
        self.client_key = settings.MIDTRANS_CLIENT_KEY
        self.is_production = settings.MIDTRANS_IS_PRODUCTION
        self.api_url = settings.midtrans_api_url
        self.snap_url = f"{self.api_url}/v2/charge" if self.is_production else f"{self.api_url}/v2/charge"
        
        # Create auth header
        auth_string = f"{self.server_key}:"
        auth_bytes = auth_string.encode('ascii')
        auth_header = base64.b64encode(auth_bytes).decode('ascii')
        
        self.headers = {
            "Accept": "application/json",
            "Content-Type": "application/json",
            "Authorization": f"Basic {auth_header}"
        }
    
    async def create_snap_transaction(
        self,
        order_id: str,
        gross_amount: float,
        customer_details: Dict[str, Any],
        item_details: list,
        callbacks: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """Create Snap transaction and get token"""
        
        # Prepare transaction data
        transaction_data = {
            "transaction_details": {
                "order_id": order_id,
                "gross_amount": int(gross_amount)  # Midtrans expects integer (in cents/smallest currency unit)
            },
            "customer_details": customer_details,
            "item_details": item_details,
            "credit_card": {
                "secure": True
            }
        }
        
        # Add callbacks if provided
        if callbacks:
            transaction_data.update(callbacks)
        
        # Default callbacks
        if not callbacks:
            transaction_data["callbacks"] = {
                "finish": f"{settings.FRONTEND_URL}/payment/success",
                "unfinish": f"{settings.FRONTEND_URL}/payment/pending",
                "error": f"{settings.FRONTEND_URL}/payment/error"
            }
        
        try:
            snap_url = f"{self.api_url}/v1/payment-links"
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    snap_url,
                    headers=self.headers,
                    json=transaction_data,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Created Snap transaction for order {order_id}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error creating Snap transaction: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to create payment: HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error creating Snap transaction: {e}")
            raise Exception("Payment service unavailable")
        except Exception as e:
            logger.error(f"Unexpected error creating Snap transaction: {e}")
            raise Exception("Failed to create payment")
    
    async def get_transaction_status(self, order_id: str) -> Dict[str, Any]:
        """Get transaction status from Midtrans"""
        
        try:
            status_url = f"{self.api_url}/v2/{order_id}/status"
            
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    status_url,
                    headers=self.headers,
                    timeout=30.0
                )
                
                response.raise_for_status()
                result = response.json()
                
                logger.info(f"Retrieved status for transaction {order_id}: {result.get('transaction_status')}")
                return result
                
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error getting transaction status: {e.response.status_code} - {e.response.text}")
            raise Exception(f"Failed to get transaction status: HTTP {e.response.status_code}")
        except httpx.RequestError as e:
            logger.error(f"Request error getting transaction status: {e}")
            raise Exception("Payment service unavailable")
        except Exception as e:
            logger.error(f"Unexpected error getting transaction status: {e}")
            raise Exception("Failed to get transaction status")
    
    async def handle_notification(self, notification_data: Dict[str, Any]) -> Dict[str, Any]:
        """Process notification from Midtrans webhook"""
        
        try:
            order_id = notification_data.get("order_id")
            
            if not order_id:
                raise ValueError("Missing order_id in notification")
            
            # Verify notification by getting status from Midtrans API
            # This is more secure than trusting the webhook payload directly
            verified_status = await self.get_transaction_status(order_id)
            
            # Map Midtrans status to our internal status
            payment_status = self._map_transaction_status(
                verified_status.get("transaction_status"),
                verified_status.get("fraud_status", "accept")
            )
            
            result = {
                "order_id": order_id,
                "transaction_id": verified_status.get("transaction_id"),
                "payment_type": verified_status.get("payment_type"),
                "transaction_status": verified_status.get("transaction_status"),
                "fraud_status": verified_status.get("fraud_status"),
                "payment_status": payment_status,
                "gross_amount": verified_status.get("gross_amount"),
                "transaction_time": verified_status.get("transaction_time"),
                "raw_notification": notification_data,
                "verified_data": verified_status
            }
            
            logger.info(f"Processed notification for order {order_id}: {payment_status}")
            return result
            
        except Exception as e:
            logger.error(f"Error processing notification: {e}")
            raise Exception(f"Failed to process payment notification: {str(e)}")
    
    def _map_transaction_status(self, transaction_status: str, fraud_status: str) -> str:
        """Map Midtrans transaction status to internal payment status"""
        
        if transaction_status == "settlement":
            if fraud_status == "accept":
                return "settlement"
            else:
                return "pending"  # Needs manual review
        elif transaction_status == "pending":
            return "pending"
        elif transaction_status == "capture":
            if fraud_status == "accept":
                return "capture"
            else:
                return "pending"
        elif transaction_status == "deny":
            return "deny"
        elif transaction_status == "cancel":
            return "cancel"
        elif transaction_status == "expire":
            return "expire"
        elif transaction_status == "failure":
            return "failure"
        else:
            return "pending"  # Unknown status, treat as pending
    
    def prepare_customer_details(self, user, shipping_address: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare customer details for Midtrans"""
        
        return {
            "first_name": user.full_name.split()[0] if user.full_name else "Customer",
            "last_name": " ".join(user.full_name.split()[1:]) if len(user.full_name.split()) > 1 else "",
            "email": user.email,
            "phone": shipping_address.get("phone", ""),
            "billing_address": {
                "first_name": shipping_address.get("full_name", "").split()[0] if shipping_address.get("full_name") else "Customer",
                "last_name": " ".join(shipping_address.get("full_name", "").split()[1:]) if shipping_address.get("full_name") and len(shipping_address.get("full_name").split()) > 1 else "",
                "email": user.email,
                "phone": shipping_address.get("phone", ""),
                "address": shipping_address.get("address", ""),
                "city": shipping_address.get("city", ""),
                "postal_code": shipping_address.get("postal_code", ""),
                "country_code": "IDN"  # Assuming Indonesia
            },
            "shipping_address": {
                "first_name": shipping_address.get("full_name", "").split()[0] if shipping_address.get("full_name") else "Customer",
                "last_name": " ".join(shipping_address.get("full_name", "").split()[1:]) if shipping_address.get("full_name") and len(shipping_address.get("full_name").split()) > 1 else "",
                "email": user.email,
                "phone": shipping_address.get("phone", ""),
                "address": shipping_address.get("address", ""),
                "city": shipping_address.get("city", ""),
                "postal_code": shipping_address.get("postal_code", ""),
                "country_code": "IDN"
            }
        }
    
    def prepare_item_details(self, order_items) -> list:
        """Prepare item details for Midtrans"""
        
        items = []
        for item in order_items:
            items.append({
                "id": item.sku_snapshot,
                "price": int(float(item.price_snapshot)),  # Convert to integer (smallest currency unit)
                "quantity": item.quantity,
                "name": item.name_snapshot[:50]  # Midtrans has character limit
            })
        
        return items


# Create global Midtrans service instance
midtrans_service = MidtransService()