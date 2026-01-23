import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel

from open_webui.socket.main import sio

from open_webui.models.groups import Groups
from open_webui.models.users import Users, UserResponse
from open_webui.models.shops import (
    ShopListResponse,
    Shops,
    ShopModel,
    ShopForm,
    ShopUpdateForm,
    ShopUserResponse,
)

from open_webui.config import (
    BYPASS_ADMIN_ACCESS_CONTROL,
    ENABLE_ADMIN_CHAT_ACCESS,
    ENABLE_ADMIN_EXPORT,
)
from open_webui.constants import ERROR_MESSAGES

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.utils.access_control import has_access, has_permission
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

router = APIRouter()

############################
# GetShops
############################


class ShopItemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    image_url: Optional[str]
    updated_at: int
    created_at: int
    user: Optional[UserResponse] = None


@router.get("/", response_model=list[ShopItemResponse])
async def get_shops(
    request: Request,
    page: Optional[int] = None,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.shops", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    limit = None
    skip = None
    if page is not None:
        limit = 60
        skip = (page - 1) * limit

    shops = Shops.get_shops_by_user_id(user.id, "read", skip=skip, limit=limit, db=db)
    if not shops:
        return []

    user_ids = list(set(shop.user_id for shop in shops))
    users = {user.id: user for user in Users.get_users_by_user_ids(user_ids, db=db)}

    return [
        ShopUserResponse(
            **{
                **shop.model_dump(),
                "user": UserResponse(**users[shop.user_id].model_dump()),
            }
        )
        for shop in shops
        if shop.user_id in users
    ]


@router.get("/search", response_model=ShopListResponse)
async def search_shops(
    request: Request,
    query: Optional[str] = None,
    view_option: Optional[str] = None,
    permission: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.shops", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    limit = None
    skip = None
    if page is not None:
        limit = 60
        skip = (page - 1) * limit

    filter = {}
    if query:
        filter["query"] = query
    if view_option:
        filter["view_option"] = view_option
    if permission:
        filter["permission"] = permission
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    if not user.role == "admin" or not BYPASS_ADMIN_ACCESS_CONTROL:
        groups = Groups.get_groups_by_member_id(user.id, db=db)
        if groups:
            filter["group_ids"] = [group.id for group in groups]

        filter["user_id"] = user.id

    return Shops.search_shops(user.id, filter, skip=skip, limit=limit, db=db)


############################
# CreateNewShop
############################


@router.post("/create", response_model=Optional[ShopModel])
async def create_new_shop(
    request: Request,
    form_data: ShopForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.shops", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    try:
        shop = Shops.insert_new_shop(user.id, form_data, db=db)
        return shop
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetShopById
############################


class ShopResponse(ShopModel):
    write_access: bool = False


@router.get("/{identifier}", response_model=Optional[ShopResponse])
async def get_shop_by_id_or_url(
    request: Request,
    identifier: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.shops", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    shop = Shops.get_shop_by_id_or_url(identifier, db=db)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != shop.user_id
        and (
            not has_access(
                user.id, type="read", access_control=shop.access_control, db=db
            )
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    write_access = (
        user.role == "admin"
        or (user.id == shop.user_id)
        or has_access(
            user.id,
            type="write",
            access_control=shop.access_control,
            strict=False,
            db=db,
        )
    )

    return ShopResponse(**shop.model_dump(), write_access=write_access)


############################
# UpdateShopById
############################


@router.post("/{identifier}/update", response_model=Optional[ShopModel])
async def update_shop_by_id_or_url(
    request: Request,
    identifier: str,
    form_data: ShopUpdateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.shops", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    shop = Shops.get_shop_by_id_or_url(identifier, db=db)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != shop.user_id
        and not has_access(
            user.id, type="write", access_control=shop.access_control, db=db
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    # Check if user can share publicly
    if (
        user.role != "admin"
        and form_data.access_control == None
        and not has_permission(
            user.id,
            "sharing.public_shops",
            request.app.state.config.USER_PERMISSIONS,
            db=db,
        )
    ):
        form_data.access_control = {}

    try:
        shop = Shops.update_shop_by_id(shop.id, form_data, db=db)
        await sio.emit(
            "shop-events",
            shop.model_dump(),
            to=f"shop:{shop.id}",
        )

        return shop
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteShopById
############################


@router.delete("/{identifier}/delete", response_model=bool)
async def delete_shop_by_id_or_url(
    request: Request,
    identifier: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.shops", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    shop = Shops.get_shop_by_id_or_url(identifier, db=db)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != shop.user_id
        and not has_access(
            user.id, type="write", access_control=shop.access_control, db=db
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        shop = Shops.delete_shop_by_id(shop.id, db=db)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# Public Shop Endpoints (No Authentication Required)
############################


@router.get("/public/search", response_model=ShopListResponse)
async def search_public_shops(
    request: Request,
    query: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    db: Session = Depends(get_session),
):
    """
    Public endpoint to search for public shops.
    Only returns shops that are public (access_control is None).
    """
    limit = None
    skip = None
    if page is not None:
        limit = 60
        skip = (page - 1) * limit

    filter = {}
    if query:
        filter["query"] = query
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    # Only show public shops (access_control is None)
    # We'll use a dummy user_id and let the search filter handle public access
    filter["user_id"] = None  # This will be handled specially in search_shops
    filter["permission"] = "read"

    # Get all public shops (user_id=None means public access only)
    result = Shops.search_shops(None, filter, skip=skip, limit=limit, db=db)
    
    return result


@router.get("/public/{identifier}", response_model=Optional[ShopModel])
async def get_public_shop_by_id_or_url(
    request: Request,
    identifier: str,
    db: Session = Depends(get_session),
):
    """
    Public endpoint to get a shop by ID or URL slug.
    Only returns shops that are public (access_control is None).
    """
    shop = Shops.get_shop_by_id_or_url(identifier, db=db)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Only return public shops (access_control is None)
    if shop.access_control is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return shop
