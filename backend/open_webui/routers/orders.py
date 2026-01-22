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
)

from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.constants import ERROR_MESSAGES

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

router = APIRouter()

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
    """
    from open_webui.models.shops import Shops

    shop = Shops.get_shop_by_id(shop_id, db=db)
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

    orders = Orders.get_orders_by_shop_id(shop_id, skip=skip, limit=limit, db=db)
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
        order = Orders.update_order_by_id(id, form_data, db=db)
        if order:
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
