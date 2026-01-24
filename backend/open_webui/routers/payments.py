import json
import logging
import os
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.socket.main import sio

from open_webui.models.users import Users, UserResponse
from open_webui.models.orders import (
    Orders,
    OrderModel,
    OrderUpdateForm,
    OrderStatusHistories,
    OrderStatus,
)

from open_webui.constants import ERROR_MESSAGES

from open_webui.utils.auth import get_verified_user
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

router = APIRouter()

# Try to import Stripe
try:
    import stripe
    STRIPE_AVAILABLE = True
except ImportError:
    STRIPE_AVAILABLE = False
    log.warning("Stripe not installed. Install with: pip install stripe")

# Try to import PayPal SDK
try:
    from paypalrestsdk import configure, Payment
    PAYPAL_AVAILABLE = True
except ImportError:
    PAYPAL_AVAILABLE = False
    log.warning("PayPal SDK not installed. Install with: pip install paypalrestsdk")


############################
# Payment Forms
############################


class PaymentIntentRequest(BaseModel):
    order_id: str


class PaymentIntentResponse(BaseModel):
    client_secret: str
    payment_intent_id: str


class ConfirmPaymentRequest(BaseModel):
    payment_intent_id: str
    order_id: str


class PayPalOrderRequest(BaseModel):
    order_id: str


class PayPalOrderResponse(BaseModel):
    order_id: str  # PayPal order ID
    approval_url: Optional[str] = None


class ConfirmPayPalRequest(BaseModel):
	paypal_order_id: str
	order_id: str
	payer_id: Optional[str] = None


############################
# Stripe Payment Intent
############################


@router.post("/stripe/create-intent", response_model=PaymentIntentResponse)
async def create_stripe_payment_intent(
    request: Request,
    form_data: PaymentIntentRequest,
    db: Session = Depends(get_session),
):
    """
    Create a Stripe payment intent for an order.
    Public endpoint - no authentication required (for guest orders).
    """
    if not STRIPE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured. Please install stripe: pip install stripe"
        )

    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
    if not stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STRIPE_SECRET_KEY not configured"
        )

    # Get order
    order = Orders.get_order_by_id(form_data.order_id, db=db)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check if order is already paid
    if order.status == OrderStatus.CONFIRMED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already confirmed"
        )

    try:
        stripe.api_key = stripe_secret_key

        # Convert amount to cents
        amount_cents = int(order.total * 100)

        intent = stripe.PaymentIntent.create(
            amount=amount_cents,
            currency=order.currency.lower(),
            metadata={
                "order_id": order.id,
                "shop_id": order.shop_id,
            },
            automatic_payment_methods={
                "enabled": True,
            },
        )

        return PaymentIntentResponse(
            client_secret=intent.client_secret,
            payment_intent_id=intent.id
        )
    except Exception as e:
        log.exception(f"Error creating Stripe payment intent: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create payment intent: {str(e)}"
        )


############################
# Stripe Webhook
############################


@router.post("/stripe/webhook")
async def stripe_webhook(
    request: Request,
    db: Session = Depends(get_session),
):
    """
    Handle Stripe webhook events.
    Public endpoint (but protected by Stripe signature verification).
    """
    if not STRIPE_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Stripe is not configured"
        )

    stripe_secret_key = os.getenv("STRIPE_SECRET_KEY")
    webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET")

    if not stripe_secret_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="STRIPE_SECRET_KEY not configured"
        )

    if not webhook_secret:
        log.warning("STRIPE_WEBHOOK_SECRET not configured. Webhook signature verification disabled.")
        # In production, you should always verify webhook signatures
        # For development, we'll allow it but log a warning

    try:
        payload = await request.body()
        sig_header = request.headers.get("stripe-signature")

        if webhook_secret and sig_header:
            try:
                event = stripe.Webhook.construct_event(
                    payload, sig_header, webhook_secret
                )
            except ValueError as e:
                log.error(f"Invalid payload: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid payload"
                )
            except stripe.error.SignatureVerificationError as e:
                log.error(f"Invalid signature: {e}")
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Invalid signature"
                )
        else:
            # For development without webhook secret, parse JSON directly
            event = json.loads(payload.decode('utf-8'))
            log.warning("Processing webhook without signature verification (development mode)")

        # Handle the event
        if event.get("type") == "payment_intent.succeeded":
            payment_intent = event["data"]["object"]
            order_id = payment_intent.get("metadata", {}).get("order_id")

            if order_id:
                order = Orders.get_order_by_id(order_id, db=db)
                if order:
                    # Update order status to confirmed
                    Orders.update_order_by_id(
                        order_id,
                        OrderUpdateForm(status=OrderStatus.CONFIRMED.value),
                        db=db
                    )

                    # Create status history entry
                    OrderStatusHistories.insert_status_history(
                        order_id=order_id,
                        status=OrderStatus.CONFIRMED.value,
                        notes=f"Payment confirmed via Stripe (Payment Intent: {payment_intent.get('id')})",
                        db=db,
                    )

                    # Emit socket event
                    updated_order = Orders.get_order_by_id(order_id, db=db)
                    if updated_order:
                        await sio.emit(
                            "order-events",
                            updated_order.model_dump(),
                            to=f"shop:{order.shop_id}",
                        )

                    log.info(f"Order {order_id} confirmed via Stripe webhook")
        elif event.get("type") == "payment_intent.payment_failed":
            payment_intent = event["data"]["object"]
            order_id = payment_intent.get("metadata", {}).get("order_id")

            if order_id:
                log.warning(f"Payment failed for order {order_id}")

        return {"status": "success"}
    except Exception as e:
        log.exception(f"Error processing Stripe webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )


############################
# PayPal Create Order
############################


@router.post("/paypal/create-order", response_model=PayPalOrderResponse)
async def create_paypal_order(
    request: Request,
    form_data: PayPalOrderRequest,
    db: Session = Depends(get_session),
):
    """
    Create a PayPal order for payment.
    Public endpoint - no authentication required (for guest orders).
    """
    if not PAYPAL_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PayPal SDK is not configured. Please install paypalrestsdk: pip install paypalrestsdk"
        )

    paypal_client_id = os.getenv("PAYPAL_CLIENT_ID")
    paypal_client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
    paypal_mode = os.getenv("PAYPAL_MODE", "sandbox")  # sandbox or live

    if not paypal_client_id or not paypal_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PayPal credentials not configured (PAYPAL_CLIENT_ID and PAYPAL_CLIENT_SECRET required)"
        )

    # Get order
    order = Orders.get_order_by_id(form_data.order_id, db=db)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    # Check if order is already paid
    if order.status == OrderStatus.CONFIRMED.value:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Order is already confirmed"
        )

    try:
        # Configure PayPal
        configure({
            "mode": paypal_mode,
            "client_id": paypal_client_id,
            "client_secret": paypal_client_secret
        })

        # Create PayPal payment
        payment = Payment({
            "intent": "sale",
            "payer": {
                "payment_method": "paypal"
            },
            "redirect_urls": {
                "return_url": os.getenv("PAYPAL_RETURN_URL", "http://localhost:5173/public/orders"),
                "cancel_url": os.getenv("PAYPAL_CANCEL_URL", "http://localhost:5173/public/cart")
            },
            "transactions": [{
                "item_list": {
                    "items": [
                        {
                            "name": item.get("name", "Item"),
                            "sku": item.get("product_id", ""),
                            "price": str(item.get("price", 0)),
                            "currency": item.get("currency", "EUR"),
                            "quantity": item.get("quantity", 1)
                        }
                        for item in order.items
                    ]
                },
                "amount": {
                    "total": str(order.total),
                    "currency": order.currency
                },
                "description": f"Order {order.id}",
                "custom": order.id
            }]
        })

        if payment.create():
            # Store PayPal payment ID in order meta
            order_meta = order.meta.copy() if order.meta else {}
            order_meta["paypal_payment_id"] = payment.id
            Orders.update_order_by_id(
                form_data.order_id,
                OrderUpdateForm(meta=order_meta),
                db=db
            )

            # Find approval URL
            approval_url = None
            for link in payment.links:
                if link.rel == "approval_url":
                    approval_url = link.href
                    break

            return PayPalOrderResponse(
                order_id=payment.id,
                approval_url=approval_url
            )
        else:
            error_details = payment.error if hasattr(payment, 'error') else "Unknown error"
            log.error(f"PayPal payment creation failed: {error_details}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create PayPal payment: {error_details}"
            )
    except Exception as e:
        log.exception(f"Error creating PayPal payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create PayPal payment: {str(e)}"
        )


############################
# PayPal Confirm Payment
############################


@router.post("/paypal/confirm")
async def confirm_paypal_payment(
    request: Request,
    form_data: ConfirmPayPalRequest,
    db: Session = Depends(get_session),
):
    """
    Confirm a PayPal payment after user approval.
    Public endpoint - no authentication required (for guest orders).
    """
    if not PAYPAL_AVAILABLE:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PayPal SDK is not configured"
        )

    paypal_client_id = os.getenv("PAYPAL_CLIENT_ID")
    paypal_client_secret = os.getenv("PAYPAL_CLIENT_SECRET")
    paypal_mode = os.getenv("PAYPAL_MODE", "sandbox")

    if not paypal_client_id or not paypal_client_secret:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="PayPal credentials not configured"
        )

    # Get order
    order = Orders.get_order_by_id(form_data.order_id, db=db)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Order not found"
        )

    try:
        # Configure PayPal
        configure({
            "mode": paypal_mode,
            "client_id": paypal_client_id,
            "client_secret": paypal_client_secret
        })

        # Execute payment
        payment = Payment.find(form_data.paypal_order_id)
        
        payer_id = form_data.payer_id or request.query_params.get("PayerID")
        if not payer_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Payer ID is required"
            )

        if payment.execute({"payer_id": payer_id}):
            # Update order status to confirmed
            Orders.update_order_by_id(
                form_data.order_id,
                OrderUpdateForm(status=OrderStatus.CONFIRMED.value),
                db=db
            )

            # Create status history entry
            OrderStatusHistories.insert_status_history(
                order_id=form_data.order_id,
                status=OrderStatus.CONFIRMED.value,
                notes=f"Payment confirmed via PayPal (Payment ID: {payment.id})",
                db=db,
            )

            # Emit socket event
            updated_order = Orders.get_order_by_id(form_data.order_id, db=db)
            if updated_order:
                await sio.emit(
                    "order-events",
                    updated_order.model_dump(),
                    to=f"shop:{order.shop_id}",
                )

            log.info(f"Order {form_data.order_id} confirmed via PayPal")
            return {"status": "success", "order_id": form_data.order_id}
        else:
            error_details = payment.error if hasattr(payment, 'error') else "Unknown error"
            log.error(f"PayPal payment execution failed: {error_details}")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Payment execution failed: {error_details}"
            )
    except Exception as e:
        log.exception(f"Error confirming PayPal payment: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to confirm payment: {str(e)}"
        )


############################
# PayPal Webhook (for IPN)
############################


@router.post("/paypal/webhook")
async def paypal_webhook(
    request: Request,
    db: Session = Depends(get_session),
):
    """
    Handle PayPal webhook/IPN events.
    Public endpoint (but should be protected by PayPal IPN verification).
    """
    # PayPal IPN verification is more complex and requires additional setup
    # For now, this is a placeholder
    # In production, you should verify the IPN message with PayPal
    
    try:
        payload = await request.body()
        # Parse and verify IPN message
        # This is a simplified version - in production, verify with PayPal
        
        log.info("PayPal webhook received (verification not implemented)")
        return {"status": "received"}
    except Exception as e:
        log.exception(f"Error processing PayPal webhook: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Webhook processing failed: {str(e)}"
        )
