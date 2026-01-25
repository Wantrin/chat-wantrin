import json
import logging
import time
import uuid
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, WebSocket, WebSocketDisconnect
from pydantic import BaseModel

from open_webui.socket.main import sio

from open_webui.models.users import Users, UserResponse
from open_webui.models.orders import (
    Orders,
    OrderModel,
    OrderForm,
    OrderUpdateForm,
    OrderUserResponse,
    OrderListResponse,
    OrderStatusHistories,
    OrderStatusHistoryModel,
    OrderStatus,
)

from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.constants import ERROR_MESSAGES

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.chat import generate_chat_completion
from open_webui.utils.models import get_all_models
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

router = APIRouter()


############################
# Generate AI Summary for Order
############################


async def generate_order_ai_summary(
    request: Request,
    order: OrderModel,
    user: UserResponse,
    db: Session,
) -> Optional[str]:
    """
    Generate an AI summary for an order, similar to task summaries.
    """
    try:
        # Get available models
        await get_all_models(request, user=user)
        models = request.app.state.MODELS
        
        if not models:
            log.warning("No models available for order summary generation")
            return None
        
        # Get default model (first available model or from config)
        default_model_id = None
        if hasattr(request.app.state, 'config') and hasattr(request.app.state.config, 'DEFAULT_MODELS'):
            default_model_id = request.app.state.config.DEFAULT_MODELS
            if default_model_id and isinstance(default_model_id, str) and ',' in default_model_id:
                # If multiple models, use the first one
                default_model_id = default_model_id.split(',')[0].strip()
        
        if not default_model_id or default_model_id not in models:
            # Use first available model
            default_model_id = list(models.keys())[0] if models else None
        
        if not default_model_id:
            log.warning("No default model available for order summary generation")
            return None
        
        # Build order information for the prompt
        items_summary = "\n".join([
            f"- {item.get('name', 'Unknown')} x{item.get('quantity', 0)} ({item.get('price', 0)} {item.get('currency', 'EUR')} each)"
            for item in order.items
        ])
        
        shipping_address_str = (
            f"{order.shipping_address.get('street', '')}, "
            f"{order.shipping_address.get('postal_code', '')} {order.shipping_address.get('city', '')}, "
            f"{order.shipping_address.get('country', '')}"
        )
        if order.shipping_address.get('state'):
            shipping_address_str += f", {order.shipping_address.get('state')}"
        
        # Create system prompt for order summary
        system_prompt = """You are a helpful order management assistant. Your role is to provide a concise and informative summary of orders.

Generate a summary that includes:
1. A brief overview of the order
2. Key items and quantities
3. Customer information highlights
4. Shipping details
5. Any important notes or special requirements

Keep the summary concise (2-4 paragraphs), professional, and in French."""
        
        # Create user prompt with order details
        user_prompt = f"""Résumez cette commande de manière concise et informative:

**Informations de la commande:**
- ID: {order.id}
- Statut: {order.status}
- Client: {order.customer_name} ({order.customer_email})
{f"- Téléphone: {order.customer_phone}" if order.customer_phone else ""}

**Articles commandés:**
{items_summary}

**Adresse de livraison:**
{shipping_address_str}

**Totaux:**
- Sous-total: {order.subtotal} {order.currency}
- Frais de livraison: {order.shipping_cost} {order.currency}
- Total: {order.total} {order.currency}

{f"**Notes:** {order.notes}" if order.notes else ""}

Générez un résumé professionnel et concis de cette commande."""
        
        # Prepare chat completion request
        form_data = {
            "model": default_model_id,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "stream": False,
            "temperature": 0.7,
        }
        
        # Generate summary
        response = await generate_chat_completion(
            request=request,
            form_data=form_data,
            user=user,
            bypass_filter=True,  # Allow summary generation
            bypass_system_prompt=True,  # We provide our own system prompt
        )
        
        # Extract summary from response
        # Response can be a dict (OpenAI format) or other formats
        summary = None
        if isinstance(response, dict):
            # OpenAI format
            if "choices" in response and len(response["choices"]) > 0:
                summary = response["choices"][0].get("message", {}).get("content", "")
            # Ollama converted format
            elif "message" in response and "content" in response["message"]:
                summary = response["message"]["content"]
        
        if summary and summary.strip():
            return summary.strip()
        
        log.warning("Failed to extract summary from AI response")
        return None
        
    except Exception as e:
        log.exception(f"Error generating order AI summary: {e}")
        return None


############################
# CreateNewOrder
############################


@router.post("/create", response_model=Optional[OrderModel])
async def create_new_order(
    request: Request,
    form_data: OrderForm,
    db: Session = Depends(get_session),
):
    """
    Create a new order. User can be authenticated or None (guest order).
    Public endpoint - no authentication required.
    """
    # Try to get user if authenticated, but allow guest orders
    user = None
    try:
        # Try to get token from header or cookie
        auth_header = request.headers.get("Authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
        elif "token" in request.cookies:
            token = request.cookies.get("token")
        
        if token:
            from open_webui.utils.auth import decode_token
            from open_webui.models.users import Users
            try:
                data = decode_token(token)
                if data and "id" in data:
                    user = Users.get_user_by_id(data["id"], db=db)
            except:
                pass  # Invalid token, continue as guest
    except:
        pass  # Guest order is allowed
    
    try:
        order = Orders.insert_new_order(user.id if user else None, form_data, db=db)
        if order:
            # Create initial status history entry
            OrderStatusHistories.insert_status_history(
                order_id=order.id,
                status=order.status,
                notes="Order created",
                db=db,
            )
            await sio.emit(
                "order-events",
                order.model_dump(),
                to=f"shop:{order.shop_id}",
            )
        return order
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetOrderById
############################


@router.get("/{id}", response_model=Optional[OrderModel])
async def get_order_by_id(
    request: Request,
    id: str,
    db: Session = Depends(get_session),
):
    """
    Get an order by ID. 
    - For guest orders (user_id is None): public access
    - For authenticated orders: user must be the owner or admin
    """
    order = Orders.get_order_by_id(id, db=db)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Guest orders are publicly accessible
    if order.user_id is None:
        return order

    # For authenticated orders, check if user is authenticated
    user = None
    try:
        auth_header = request.headers.get("Authorization")
        token = None
        
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.replace("Bearer ", "")
        elif "token" in request.cookies:
            token = request.cookies.get("token")
        
        if token:
            from open_webui.utils.auth import decode_token
            from open_webui.models.users import Users
            try:
                data = decode_token(token)
                if data and "id" in data:
                    user = Users.get_user_by_id(data["id"], db=db)
            except:
                pass
    except:
        pass

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail=ERROR_MESSAGES.UNAUTHORIZED
        )

    # Check access: user must be owner or admin
    if user.role != "admin" and order.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    return order


############################
# GetOrdersByUserId
############################


@router.get("/user/{user_id}", response_model=list[OrderModel])
async def get_orders_by_user_id(
    request: Request,
    user_id: str,
    page: Optional[int] = None,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Get orders for a specific user. User must be requesting their own orders or be admin.
    """
    if user.role != "admin" and user.id != user_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    limit = None
    skip = None
    if page is not None:
        limit = 60
        skip = (page - 1) * limit

    orders = Orders.get_orders_by_user_id(user_id, skip=skip, limit=limit, db=db)
    return orders


############################
# GetOrdersByShopId
############################


@router.get("/shop/{shop_id}", response_model=list[OrderModel])
async def get_orders_by_shop_id(
    request: Request,
    shop_id: str,
    page: Optional[int] = None,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Get orders for a specific shop. User must be the shop owner or admin.
    Supports both shop ID (UUID) and URL slug.
    """
    from open_webui.models.shops import Shops

    # Support both ID and URL slug
    shop = Shops.get_shop_by_id_or_url(shop_id, db=db)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Check access: user must be shop owner or admin
    if user.role != "admin" and shop.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    limit = None
    skip = None
    if page is not None:
        limit = 60
        skip = (page - 1) * limit

    # Use the actual shop ID (UUID) for querying orders
    orders = Orders.get_orders_by_shop_id(shop.id, skip=skip, limit=limit, db=db)
    return orders


############################
# UpdateOrderById
############################


@router.post("/{id}/update", response_model=Optional[OrderModel])
async def update_order_by_id(
    request: Request,
    id: str,
    form_data: OrderUpdateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Update an order. User must be shop owner or admin.
    """
    order = Orders.get_order_by_id(id, db=db)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    from open_webui.models.shops import Shops

    shop = Shops.get_shop_by_id(order.shop_id, db=db)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Check access: user must be shop owner or admin
    if user.role != "admin" and shop.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        # Get old order to check status change
        old_order = Orders.get_order_by_id(id, db=db)
        old_status = old_order.status if old_order else None
        
        order = Orders.update_order_by_id(id, form_data, db=db)
        if order:
            # Create status history entry if status changed
            if form_data.status and old_status and form_data.status != old_status:
                OrderStatusHistories.insert_status_history(
                    order_id=id,
                    status=form_data.status,
                    notes=f"Status changed from {old_status} to {form_data.status}",
                    db=db,
                )
                
                # Generate AI summary when order is processed (status changes to "processing" or "confirmed")
                if form_data.status in [OrderStatus.PROCESSING.value, OrderStatus.CONFIRMED.value]:
                    # Check if summary already exists
                    if not order.meta or "ai_summary" not in order.meta:
                        try:
                            summary = await generate_order_ai_summary(request, order, user, db)
                            if summary:
                                # Update order with AI summary in meta
                                summary_meta = order.meta.copy() if order.meta else {}
                                summary_meta["ai_summary"] = summary
                                Orders.update_order_by_id(
                                    id,
                                    OrderUpdateForm(meta=summary_meta),
                                    db=db,
                                )
                                # Reload order to get updated meta
                                order = Orders.get_order_by_id(id, db=db)
                                log.info(f"Generated AI summary for order {id}")
                        except Exception as e:
                            log.exception(f"Error generating AI summary for order {id}: {e}")
                            # Continue even if summary generation fails
            
            await sio.emit(
                "order-events",
                order.model_dump(),
                to=f"shop:{order.shop_id}",
            )
        return order
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetOrderStatusHistory
############################


@router.get("/{id}/status-history", response_model=list[OrderStatusHistoryModel])
async def get_order_status_history(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Get status history for an order. User must be shop owner, order owner, or admin.
    """
    order = Orders.get_order_by_id(id, db=db)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    from open_webui.models.shops import Shops

    shop = Shops.get_shop_by_id(order.shop_id, db=db)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Check access: user must be shop owner, order owner, or admin
    is_shop_owner = shop.user_id == user.id
    is_order_owner = order.user_id == user.id if order.user_id else False
    is_admin = user.role == "admin"

    if not (is_admin or is_shop_owner or is_order_owner):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    history = OrderStatusHistories.get_status_history_by_order_id(id, db=db)
    return history


############################
# DeleteOrderById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_order_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Delete an order. User must be shop owner or admin.
    """
    order = Orders.get_order_by_id(id, db=db)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    from open_webui.models.shops import Shops

    shop = Shops.get_shop_by_id(order.shop_id, db=db)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Check access: user must be shop owner or admin
    if user.role != "admin" and shop.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        result = Orders.delete_order_by_id(id, db=db)
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# Phone Call Management
############################


class PhoneCallForm(BaseModel):
    phone_number: str
    order_id: Optional[str] = None
    delivery_person_id: Optional[str] = None
    call_type: str  # "customer" or "delivery_person"
    context: Optional[dict] = None  # Additional context for the call


class PhoneCallResponse(BaseModel):
    call_id: str
    status: str
    message: str


############################
# SMS Management
############################


class SMSForm(BaseModel):
    phone_number: Optional[str] = None
    message: str
    delivery_person_id: Optional[str] = None
    send_to: str  # "customer" or "delivery_person" or "both"
    context: Optional[dict] = None


class SMSResponse(BaseModel):
    message_sid: Optional[str] = None
    status: str
    message: str
    sent_to: list[str] = []


@router.post("/{id}/send-sms", response_model=SMSResponse)
async def send_sms(
    request: Request,
    id: str,
    form_data: SMSForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Send SMS message to customer or delivery person for an order.
    """
    order = Orders.get_order_by_id(id, db=db)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    from open_webui.models.shops import Shops

    shop = Shops.get_shop_by_id(order.shop_id, db=db)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Check access: user must be shop owner or admin
    if user.role != "admin" and shop.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        # Determine recipients based on send_to
        recipients = []
        target_phones = []
        
        if form_data.send_to in ["customer", "both"]:
            if order.customer_phone:
                target_phones.append(order.customer_phone)
                recipients.append("customer")
            elif not form_data.phone_number:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customer phone number not available"
                )
        
        if form_data.send_to in ["delivery_person", "both"]:
            if form_data.delivery_person_id:
                from open_webui.models.delivery_persons import DeliveryPersons
                delivery_person = DeliveryPersons.get_delivery_person_by_id(
                    form_data.delivery_person_id, db=db
                )
                if delivery_person and delivery_person.phone:
                    target_phones.append(delivery_person.phone)
                    recipients.append("delivery_person")
                else:
                    raise HTTPException(
                        status_code=status.HTTP_400_BAD_REQUEST,
                        detail="Delivery person phone number not available"
                    )
            else:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Delivery person ID is required"
                )
        
        # Use provided phone number if no recipients found
        if not target_phones and form_data.phone_number:
            target_phones.append(form_data.phone_number)
            recipients.append("custom")
        
        if not target_phones:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No valid phone numbers found"
            )
        
        # Check if Twilio is enabled and configured
        twilio_message_sids = []
        twilio_error = None
        
        # First, check if Twilio is configured
        enable_twilio = getattr(request.app.state.config, "ENABLE_TWILIO", False)
        twilio_account_sid = getattr(request.app.state.config, "TWILIO_ACCOUNT_SID", "") or ""
        twilio_auth_token = getattr(request.app.state.config, "TWILIO_AUTH_TOKEN", "") or ""
        twilio_phone_number = getattr(request.app.state.config, "TWILIO_PHONE_NUMBER", "") or ""
        
        if not enable_twilio:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Twilio is not enabled. Please enable it in the configuration (ENABLE_TWILIO=True)."
            )
        
        if not twilio_account_sid or not twilio_auth_token or not twilio_phone_number:
            missing = []
            if not twilio_account_sid:
                missing.append("TWILIO_ACCOUNT_SID")
            if not twilio_auth_token:
                missing.append("TWILIO_AUTH_TOKEN")
            if not twilio_phone_number:
                missing.append("TWILIO_PHONE_NUMBER")
            
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Twilio credentials are missing. Please configure: {', '.join(missing)}"
            )
        
        # Try to send SMS
        try:
            from open_webui.utils.twilio_service import TwilioService
            
            twilio_service = TwilioService(
                account_sid=twilio_account_sid,
                auth_token=twilio_auth_token,
                phone_number=twilio_phone_number
            )
            
            # Build status callback URL
            base_url = str(request.base_url).rstrip('/')
            status_callback_url = f"{base_url}/api/v1/orders/{id}/twilio-sms-status"
            
            # Send SMS to all recipients
            for phone in target_phones:
                message_sid = twilio_service.send_sms(
                    to_phone=phone,
                    message=form_data.message,
                    status_callback_url=status_callback_url
                )
                if message_sid:
                    twilio_message_sids.append(message_sid)
                    log.info(f"Twilio SMS sent successfully: SID={message_sid}, To={phone}")
                else:
                    log.warning(f"Failed to send SMS to {phone}")
                    if not twilio_error:
                        twilio_error = f"Failed to send SMS to {phone}"
        except ImportError as e:
            log.error(f"Twilio library not available: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Twilio library is not installed. Please install it with: pip install twilio"
            )
        except Exception as e:
            log.exception(f"Error sending Twilio SMS: {e}")
            twilio_error = str(e)
            # Don't raise here - we'll return a failed status
        
        # Store SMS information in order meta
        if not order.meta:
            order.meta = {}
        if "sms_messages" not in order.meta:
            order.meta["sms_messages"] = []
        
        sms_record = {
            "message_sids": twilio_message_sids,
            "recipients": recipients,
            "phone_numbers": target_phones,
            "message": form_data.message,
            "sent_by": user.id,
            "sent_at": int(time.time_ns()),
            "status": "sent" if twilio_message_sids else "failed",
            "context": form_data.context or {}
        }
        
        order.meta["sms_messages"].append(sms_record)
        Orders.update_order_by_id(
            id,
            OrderUpdateForm(meta=order.meta),
            db=db
        )
        
        # Determine final status and message
        if twilio_message_sids:
            final_status = "sent"
            final_message = f"SMS sent successfully to {', '.join(recipients)}"
        else:
            final_status = "failed"
            if twilio_error:
                final_message = f"Failed to send SMS: {twilio_error}"
            else:
                final_message = f"Failed to send SMS to {', '.join(recipients)}. No message SID returned from Twilio."
        
        return SMSResponse(
            message_sid=twilio_message_sids[0] if twilio_message_sids else None,
            status=final_status,
            message=final_message,
            sent_to=target_phones if twilio_message_sids else []
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to send SMS: {str(e)}"
        )


@router.post("/{id}/twilio-sms-status")
async def twilio_sms_status_webhook(
    request: Request,
    id: str,
    db: Session = Depends(get_session),
):
    """
    Webhook endpoint for Twilio SMS status updates.
    """
    try:
        form_data = await request.form()
        message_sid = form_data.get("MessageSid", "")
        message_status = form_data.get("MessageStatus", "")
        to_number = form_data.get("To", "")
        from_number = form_data.get("From", "")
        error_code = form_data.get("ErrorCode", "")
        error_message = form_data.get("ErrorMessage", "")
        
        log.info(f"Twilio SMS status update: MessageSid={message_sid}, Status={message_status}, To={to_number}, Error={error_code}")
        
        # Update order with SMS status
        order = Orders.get_order_by_id(id, db=db)
        if order and order.meta and "sms_messages" in order.meta:
            for sms_record in reversed(order.meta["sms_messages"]):
                if message_sid in sms_record.get("message_sids", []):
                    if "status_updates" not in sms_record:
                        sms_record["status_updates"] = []
                    sms_record["status_updates"].append({
                        "message_sid": message_sid,
                        "status": message_status,
                        "to": to_number,
                        "from": from_number,
                        "error_code": error_code,
                        "error_message": error_message,
                        "updated_at": int(time.time_ns())
                    })
                    sms_record["status"] = message_status
                    break
            
            Orders.update_order_by_id(
                id,
                OrderUpdateForm(meta=order.meta),
                db=db
            )
        
        return {"status": "ok"}
        
    except Exception as e:
        log.exception(f"Error handling Twilio SMS status webhook: {e}")
        return {"status": "error", "message": str(e)}


@router.post("/{id}/initiate-phone-call", response_model=PhoneCallResponse)
async def initiate_phone_call(
    request: Request,
    id: str,
    form_data: PhoneCallForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Initiate a phone call with speech-to-speech AI for order management.
    Can call either the customer or the delivery person.
    """
    order = Orders.get_order_by_id(id, db=db)
    if not order:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    from open_webui.models.shops import Shops

    shop = Shops.get_shop_by_id(order.shop_id, db=db)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Check access: user must be shop owner or admin
    if user.role != "admin" and shop.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        # Validate phone number
        if not form_data.phone_number or not form_data.phone_number.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number is required"
            )

        # Get phone number based on call type
        target_phone = form_data.phone_number
        if form_data.call_type == "customer":
            if not order.customer_phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Customer phone number not available"
                )
            target_phone = order.customer_phone
        elif form_data.call_type == "delivery_person":
            if not form_data.delivery_person_id:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Delivery person ID is required"
                )
            from open_webui.models.delivery_persons import DeliveryPersons
            delivery_person = DeliveryPersons.get_delivery_person_by_id(
                form_data.delivery_person_id, db=db
            )
            if not delivery_person or not delivery_person.phone:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Delivery person phone number not available"
                )
            target_phone = delivery_person.phone

        # Initiate phone call via Twilio if configured
        call_id = str(uuid.uuid4())
        twilio_call_sid = None
        
        # Check if Twilio is enabled and configured
        try:
            enable_twilio = getattr(request.app.state.config, "ENABLE_TWILIO", False)
            twilio_account_sid = getattr(request.app.state.config, "TWILIO_ACCOUNT_SID", "") or ""
            twilio_auth_token = getattr(request.app.state.config, "TWILIO_AUTH_TOKEN", "") or ""
            twilio_phone_number = getattr(request.app.state.config, "TWILIO_PHONE_NUMBER", "") or ""
            
            if enable_twilio and twilio_account_sid and twilio_auth_token and twilio_phone_number:
                from open_webui.utils.twilio_service import TwilioService
                
                twilio_service = TwilioService(
                    account_sid=twilio_account_sid,
                    auth_token=twilio_auth_token,
                    phone_number=twilio_phone_number
                )
                
                # Build webhook URL for Twilio callbacks
                # This should point to your server's webhook endpoint
                base_url = str(request.base_url).rstrip('/')
                webhook_url = f"{base_url}/api/v1/orders/{id}/twilio-voice"
                
                # Build Media Streams WebSocket URL
                # Convert http/https to ws/wss
                ws_protocol = 'wss' if base_url.startswith('https') else 'ws'
                ws_base = base_url.replace('http://', 'ws://').replace('https://', 'wss://')
                media_stream_url = f"{ws_base}/api/v1/orders/{id}/twilio-media-stream?call_id={call_id}"
                
                # Determine AI provider from context or default to OpenAI
                ai_provider = form_data.context.get('ai_provider', 'openai') if form_data.context else 'openai'
                
                # Make the actual phone call with Media Streams enabled
                twilio_call_sid = twilio_service.make_call(
                    to_phone=target_phone,
                    webhook_url=webhook_url,
                    call_id=call_id,
                    context=form_data.context,
                    enable_media_streams=True,
                    media_stream_url=media_stream_url
                )
                
                if twilio_call_sid:
                    log.info(f"Twilio call initiated successfully: {twilio_call_sid}")
                else:
                    log.warning("Twilio call initiation failed, but continuing with call record")
            else:
                log.info("Twilio not configured or disabled, skipping real phone call")
        except ImportError as e:
            log.warning(f"Twilio library not available: {e}. Install with: pip install twilio")
        except Exception as e:
            log.exception(f"Error initiating Twilio call: {e}")
            # Continue without Twilio - the call will still be recorded
        
        # Store call information in order meta
        if not order.meta:
            order.meta = {}
        if "phone_calls" not in order.meta:
            order.meta["phone_calls"] = []
        
        call_record = {
            "call_id": call_id,
            "phone_number": target_phone,
            "call_type": form_data.call_type,
            "initiated_by": user.id,
            "initiated_at": int(time.time_ns()),
            "status": "initiated",
            "context": form_data.context or {},
            "twilio_call_sid": twilio_call_sid
        }
        
        order.meta["phone_calls"].append(call_record)
        Orders.update_order_by_id(
            id,
            OrderUpdateForm(meta=order.meta),
            db=db
        )
        
        return PhoneCallResponse(
            call_id=call_id,
            status="initiated",
            message=f"Phone call initiated to {target_phone}" + (f" (Twilio SID: {twilio_call_sid})" if twilio_call_sid else " (Note: Twilio not configured - call is simulated)")
        )
        
    except HTTPException:
        raise
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Failed to initiate phone call: {str(e)}"
        )


@router.post("/{id}/twilio-voice")
async def twilio_voice_webhook(
    request: Request,
    id: str,
    db: Session = Depends(get_session),
):
    """
    Webhook endpoint for Twilio voice calls.
    This receives TwiML instructions when a call is answered.
    Activates Media Streams for real-time AI conversation.
    """
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid", "")
        from_number = form_data.get("From", "")
        to_number = form_data.get("To", "")
        call_status = form_data.get("CallStatus", "")
        call_id = request.query_params.get("call_id", "")
        
        log.info(f"Twilio webhook received: CallSid={call_sid}, Status={call_status}, From={from_number}, To={to_number}")
        
        # Get the order to update call status
        order = Orders.get_order_by_id(id, db=db)
        if order and order.meta and "phone_calls" in order.meta:
            # Update the latest call record with Twilio status
            for call_record in reversed(order.meta["phone_calls"]):
                if call_record.get("call_id") == call_id or call_record.get("twilio_call_sid") == call_sid or call_record.get("status") == "initiated":
                    call_record["twilio_call_sid"] = call_sid
                    call_record["status"] = call_status
                    call_record["from_number"] = from_number
                    call_record["to_number"] = to_number
                    break
            
            Orders.update_order_by_id(
                id,
                OrderUpdateForm(meta=order.meta),
                db=db
            )
        
        # Build Media Streams WebSocket URL
        base_url = str(request.base_url).rstrip('/')
        ws_protocol = 'wss' if base_url.startswith('https') else 'ws'
        ws_base = base_url.replace('http://', 'ws://').replace('https://', 'wss://')
        media_stream_url = f"{ws_base}/api/v1/orders/{id}/twilio-media-stream?call_sid={call_sid}&call_id={call_id}"
        
        # Get AI configuration from call context
        ai_provider = 'openai'  # Default
        ai_config = {}
        if order and order.meta and "phone_calls" in order.meta:
            for call_record in reversed(order.meta["phone_calls"]):
                if call_record.get("call_id") == call_id:
                    context = call_record.get("context", {})
                    ai_provider = context.get("ai_provider", "openai")
                    break
        
        # Get AI API keys from config
        try:
            if ai_provider == 'openai':
                openai_keys = getattr(request.app.state.config, "OPENAI_API_KEYS", None)
                if openai_keys and hasattr(openai_keys, 'value') and openai_keys.value:
                    ai_config = {
                        "api_key": openai_keys.value[0] if isinstance(openai_keys.value, list) else openai_keys.value,
                        "model": "gpt-realtime",
                        "voice": "alloy",
                        "instructions": "You are a helpful assistant for order management."
                    }
            elif ai_provider == 'gemini':
                gemini_key = getattr(request.app.state.config, "GEMINI_API_KEY", None)
                if gemini_key and hasattr(gemini_key, 'value') and gemini_key.value:
                    ai_config = {
                        "api_key": gemini_key.value,
                        "model": "gemini-2.5-flash-native-audio-preview-12-2025",
                        "system_instruction": "You are a helpful assistant for order management."
                    }
        except Exception as e:
            log.warning(f"Failed to get AI config: {e}")
        
        # Return TwiML with Media Streams enabled
        from fastapi.responses import Response
        
        if ai_config:
            # Enable Media Streams for AI conversation
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Start>
        <Stream url="{media_stream_url}" />
    </Start>
    <Say voice="alice" language="fr-FR">
        Bonjour, je suis votre assistant vocal. Comment puis-je vous aider?
    </Say>
    <Pause length="30"/>
</Response>'''
        else:
            # Fallback if AI not configured
            twiml = f'''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice" language="fr-FR">
        Bonjour, je suis un assistant vocal pour la gestion de commandes. 
        La configuration de l'intelligence artificielle n'est pas disponible pour le moment.
    </Say>
    <Hangup/>
</Response>'''
        
        return Response(content=twiml, media_type="application/xml")
        
    except Exception as e:
        log.exception(f"Error handling Twilio webhook: {e}")
        # Return error TwiML
        from fastapi.responses import Response
        twiml = '''<?xml version="1.0" encoding="UTF-8"?>
<Response>
    <Say voice="alice">Sorry, an error occurred.</Say>
    <Hangup/>
</Response>'''
        return Response(content=twiml, media_type="application/xml")


@router.post("/{id}/twilio-status")
async def twilio_status_webhook(
    request: Request,
    id: str,
    db: Session = Depends(get_session),
):
    """
    Webhook endpoint for Twilio call status updates.
    """
    try:
        form_data = await request.form()
        call_sid = form_data.get("CallSid", "")
        call_status = form_data.get("CallStatus", "")
        call_duration = form_data.get("CallDuration", "0")
        
        log.info(f"Twilio status update: CallSid={call_sid}, Status={call_status}, Duration={call_duration}")
        
        # Update order with call status
        order = Orders.get_order_by_id(id, db=db)
        if order and order.meta and "phone_calls" in order.meta:
            for call_record in order.meta["phone_calls"]:
                if call_record.get("twilio_call_sid") == call_sid:
                    call_record["status"] = call_status
                    call_record["duration"] = int(call_duration) if call_duration.isdigit() else 0
                    break
            
            Orders.update_order_by_id(
                id,
                OrderUpdateForm(meta=order.meta),
                db=db
            )
        
        return {"status": "ok"}
        
    except Exception as e:
        log.exception(f"Error handling Twilio status webhook: {e}")
        return {"status": "error", "message": str(e)}


@router.websocket("/{id}/twilio-media-stream")
async def twilio_media_stream_websocket(
    websocket: WebSocket,
    id: str,
):
    """
    WebSocket endpoint for Twilio Media Streams.
    Connects phone call audio to AI Realtime APIs.
    """
    await websocket.accept()
    
    call_sid = None
    try:
        # Get call_sid and call_id from query params
        call_sid = websocket.query_params.get("call_sid", "")
        call_id = websocket.query_params.get("call_id", "")
        
        if not call_sid:
            log.error("No call_sid provided for Media Stream")
            await websocket.close()
            return
        
        log.info(f"Media Stream WebSocket connected: call_sid={call_sid}, call_id={call_id}")
        
        # Get order and call context
        from open_webui.internal.db import SessionLocal
        db = SessionLocal()
        try:
            order = Orders.get_order_by_id(id, db=db)
            ai_provider = 'openai'  # Default
            ai_config = {}
            
            if order and order.meta and "phone_calls" in order.meta:
                for call_record in reversed(order.meta["phone_calls"]):
                    if call_record.get("call_id") == call_id or call_record.get("twilio_call_sid") == call_sid:
                        context = call_record.get("context", {})
                        ai_provider = context.get("ai_provider", "openai")
                        break
            
            # Get AI configuration from app state
            # Note: We need to access app state differently in WebSocket
            # For now, get from environment or pass via context
            try:
                from open_webui.config import OPENAI_API_KEYS, GEMINI_API_KEY
                app_state = None  # WebSocket doesn't have direct access to app.state
                if ai_provider == 'openai':
                    openai_keys = OPENAI_API_KEYS
                    if openai_keys and hasattr(openai_keys, 'value') and openai_keys.value:
                        api_key = openai_keys.value[0] if isinstance(openai_keys.value, list) else openai_keys.value
                        ai_config = {
                            "api_key": api_key,
                            "model": "gpt-realtime",
                            "voice": "alloy",
                            "instructions": "You are a helpful assistant for order management."
                        }
                elif ai_provider == 'gemini':
                    gemini_key = GEMINI_API_KEY
                    if gemini_key and hasattr(gemini_key, 'value') and gemini_key.value:
                        ai_config = {
                            "api_key": gemini_key.value,
                            "model": "gemini-2.5-flash-native-audio-preview-12-2025",
                            "system_instruction": "You are a helpful assistant for order management."
                        }
            except Exception as e:
                log.warning(f"Failed to get AI config: {e}")
            
            if not ai_config:
                log.error("AI configuration not available")
                await websocket.close()
                return
            
            # Create and register bridge
            from open_webui.utils.twilio_media_streams import (
                TwilioMediaStreamBridge,
                register_bridge,
                unregister_bridge
            )
            
            bridge = TwilioMediaStreamBridge(
                call_sid=call_sid,
                ai_provider=ai_provider,
                ai_config=ai_config
            )
            
            register_bridge(call_sid, bridge)
            
            # Connect bridge to Twilio Media Stream
            await bridge.connect_twilio(websocket)
            
        finally:
            db.close()
        
    except WebSocketDisconnect:
        log.info(f"Media Stream WebSocket disconnected: call_sid={call_sid}")
    except Exception as e:
        log.exception(f"Error in Media Stream WebSocket: {e}")
    finally:
        # Cleanup
        if call_sid:
            try:
                from open_webui.utils.twilio_media_streams import unregister_bridge
                unregister_bridge(call_sid)
            except:
                pass
