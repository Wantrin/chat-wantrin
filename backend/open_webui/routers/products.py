import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel

from open_webui.socket.main import sio

from open_webui.models.groups import Groups
from open_webui.models.users import Users, UserResponse
from open_webui.models.products import (
    ProductListResponse,
    Products,
    ProductModel,
    ProductForm,
    ProductUpdateForm,
    ProductUserResponse,
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
# GetProducts
############################


class ProductItemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    price: float
    image_url: Optional[str]
    stock: int
    category: Optional[str]
    updated_at: int
    created_at: int
    user: Optional[UserResponse] = None


@router.get("/", response_model=list[ProductItemResponse])
async def get_products(
    request: Request,
    page: Optional[int] = None,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.products", request.app.state.config.USER_PERMISSIONS, db=db
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

    products = Products.get_products_by_user_id(user.id, "read", skip=skip, limit=limit, db=db)
    if not products:
        return []

    user_ids = list(set(product.user_id for product in products))
    users = {user.id: user for user in Users.get_users_by_user_ids(user_ids, db=db)}

    return [
        ProductUserResponse(
            **{
                **product.model_dump(),
                "user": UserResponse(**users[product.user_id].model_dump()),
            }
        )
        for product in products
        if product.user_id in users
    ]


@router.get("/search", response_model=ProductListResponse)
async def search_products(
    request: Request,
    query: Optional[str] = None,
    category: Optional[str] = None,
    currency: Optional[str] = None,
    shop_id: Optional[str] = None,
    view_option: Optional[str] = None,
    permission: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.products", request.app.state.config.USER_PERMISSIONS, db=db
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
    if category:
        filter["category"] = category
    if currency:
        filter["currency"] = currency
    if shop_id:
        filter["shop_id"] = shop_id
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

        # When shop_id is specified, show all accessible products in that shop
        # (public products + user's products + shared products)
        # When shop_id is not specified, only show user's products and accessible products
        if shop_id:
            # For shop pages, show all accessible products (public + user's + shared)
            # The _has_permission method will handle showing public products and user's products
            filter["user_id"] = user.id
        elif view_option == "shared":
            # For "shared" view, don't add user_id (handled in search_products)
            pass
        else:
            # Default: show user's products and accessible products
            filter["user_id"] = user.id

    return Products.search_products(user.id, filter, skip=skip, limit=limit, db=db)


############################
# CreateNewProduct
############################


@router.post("/create", response_model=Optional[ProductModel])
async def create_new_product(
    request: Request,
    form_data: ProductForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.products", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    try:
        product = Products.insert_new_product(user.id, form_data, db=db)
        return product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetProductById
############################


class ProductResponse(ProductModel):
    write_access: bool = False


@router.get("/{id}", response_model=Optional[ProductResponse])
async def get_product_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.products", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    product = Products.get_product_by_id(id, db=db)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != product.user_id
        and (
            not has_access(
                user.id, type="read", access_control=product.access_control, db=db
            )
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    write_access = (
        user.role == "admin"
        or (user.id == product.user_id)
        or has_access(
            user.id,
            type="write",
            access_control=product.access_control,
            strict=False,
            db=db,
        )
    )

    return ProductResponse(**product.model_dump(), write_access=write_access)


############################
# UpdateProductById
############################


@router.post("/{id}/update", response_model=Optional[ProductModel])
async def update_product_by_id(
    request: Request,
    id: str,
    form_data: ProductUpdateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.products", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    product = Products.get_product_by_id(id, db=db)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != product.user_id
        and not has_access(
            user.id, type="write", access_control=product.access_control, db=db
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
            "sharing.public_products",
            request.app.state.config.USER_PERMISSIONS,
            db=db,
        )
    ):
        form_data.access_control = {}

    try:
        product = Products.update_product_by_id(id, form_data, db=db)
        await sio.emit(
            "product-events",
            product.model_dump(),
            to=f"product:{product.id}",
        )

        return product
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteProductById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_product_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.products", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    product = Products.get_product_by_id(id, db=db)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != product.user_id
        and not has_access(
            user.id, type="write", access_control=product.access_control, db=db
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        product = Products.delete_product_by_id(id, db=db)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# Public Product Endpoints (No Authentication Required)
############################

# IMPORTANT: More specific routes must be defined BEFORE parameterized routes
# Otherwise FastAPI will match /public/search as /public/{id} with id="search"

@router.get("/public/search", response_model=ProductListResponse)
async def search_public_products(
    request: Request,
    query: Optional[str] = None,
    category: Optional[str] = None,
    currency: Optional[str] = None,
    shop_id: Optional[str] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    db: Session = Depends(get_session),
):
    """
    Public endpoint to search for public products.
    Only returns products that are public (access_control is None).
    """
    limit = None
    skip = None
    if page is not None:
        limit = 60
        skip = (page - 1) * limit

    filter = {}
    if query:
        filter["query"] = query
    if category:
        filter["category"] = category
    if currency:
        filter["currency"] = currency
    if shop_id:
        filter["shop_id"] = shop_id
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    # Only show public products (access_control is None)
    # We'll use None as user_id to indicate public access
    filter["permission"] = "read"

    # Get all public products (user_id=None means public access only)
    result = Products.search_products(None, filter, skip=skip, limit=limit, db=db)
    
    return result


@router.get("/public/{id}", response_model=Optional[ProductModel])
async def get_public_product_by_id(
    request: Request,
    id: str,
    db: Session = Depends(get_session),
):
    """
    Public endpoint to get a product by ID.
    Only returns products that are public (access_control is None).
    """
    product = Products.get_product_by_id(id, db=db)
    if not product:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Only return public products (access_control is None)
    if product.access_control is not None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    return product
