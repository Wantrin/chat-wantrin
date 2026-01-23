import json
import logging
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel

from open_webui.models.users import Users, UserResponse
from open_webui.models.delivery_persons import (
    DeliveryPersons,
    DeliveryPersonModel,
    DeliveryPersonForm,
    DeliveryPersonUpdateForm,
    DeliveryPersonUserResponse,
    DeliveryPersonListResponse,
)
from open_webui.models.shops import Shops

from open_webui.config import BYPASS_ADMIN_ACCESS_CONTROL
from open_webui.constants import ERROR_MESSAGES

from open_webui.utils.auth import get_admin_user, get_verified_user
from open_webui.internal.db import get_session
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

router = APIRouter()

############################
# CreateNewDeliveryPerson
############################


@router.post("/create", response_model=Optional[DeliveryPersonModel])
async def create_new_delivery_person(
    request: Request,
    form_data: DeliveryPersonForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Create a new delivery person. User must be shop owner or admin.
    """
    shop = Shops.get_shop_by_id(form_data.shop_id, db=db)
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
        delivery_person = DeliveryPersons.insert_new_delivery_person(form_data, db=db)
        return delivery_person
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetDeliveryPersonById
############################


@router.get("/{id}", response_model=Optional[DeliveryPersonModel])
async def get_delivery_person_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Get a delivery person by ID. User must be shop owner or admin.
    """
    delivery_person = DeliveryPersons.get_delivery_person_by_id(id, db=db)
    if not delivery_person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    shop = Shops.get_shop_by_id(delivery_person.shop_id, db=db)
    if not shop:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    # Check access: user must be shop owner or admin
    if user.role != "admin" and shop.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    return delivery_person


############################
# GetDeliveryPersonsByShopId
############################


@router.get("/shop/{shop_id}", response_model=list[DeliveryPersonModel])
async def get_delivery_persons_by_shop_id(
    request: Request,
    shop_id: str,
    active_only: Optional[bool] = False,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Get delivery persons for a specific shop. User must be the shop owner or admin.
    """
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

    delivery_persons = DeliveryPersons.get_delivery_persons_by_shop_id(
        shop_id, active_only=active_only, db=db
    )
    return delivery_persons


############################
# UpdateDeliveryPersonById
############################


@router.post("/{id}/update", response_model=Optional[DeliveryPersonModel])
async def update_delivery_person_by_id(
    request: Request,
    id: str,
    form_data: DeliveryPersonUpdateForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Update a delivery person. User must be shop owner or admin.
    """
    delivery_person = DeliveryPersons.get_delivery_person_by_id(id, db=db)
    if not delivery_person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    shop = Shops.get_shop_by_id(delivery_person.shop_id, db=db)
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
        delivery_person = DeliveryPersons.update_delivery_person_by_id(
            id, form_data, db=db
        )
        return delivery_person
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteDeliveryPersonById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_delivery_person_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    """
    Delete a delivery person. User must be shop owner or admin.
    """
    delivery_person = DeliveryPersons.get_delivery_person_by_id(id, db=db)
    if not delivery_person:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    shop = Shops.get_shop_by_id(delivery_person.shop_id, db=db)
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
        result = DeliveryPersons.delete_delivery_person_by_id(id, db=db)
        return result
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )
