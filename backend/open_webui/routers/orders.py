import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
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
