import json
import time
import uuid
from typing import Optional

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, get_db, get_db_context
from open_webui.models.users import User, UserModel, Users, UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON, Float, ForeignKey

####################
# DeliveryPerson DB Schema
####################


class DeliveryPerson(Base):
    __tablename__ = "delivery_person"

    id = Column(Text, primary_key=True, unique=True)
    shop_id = Column(Text, nullable=False)  # Delivery person belongs to a shop
    user_id = Column(Text, nullable=True)  # Optional: link to user account

    # Delivery person information
    name = Column(Text, nullable=False)
    email = Column(Text, nullable=True)
    phone = Column(Text, nullable=True)
    vehicle_type = Column(Text, nullable=True)  # e.g., "car", "bike", "van", "truck"
    vehicle_plate = Column(Text, nullable=True)  # License plate number
    
    # Status
    is_active = Column(Boolean, default=True)
    
    # Additional information
    notes = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class DeliveryPersonModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    shop_id: str
    user_id: Optional[str] = None

    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_plate: Optional[str] = None
    
    is_active: bool = True
    
    notes: Optional[str] = None
    meta: Optional[dict] = None

    created_at: int
    updated_at: int


####################
# Forms
####################


class DeliveryPersonForm(BaseModel):
    shop_id: str
    user_id: Optional[str] = None
    name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_plate: Optional[str] = None
    is_active: bool = True
    notes: Optional[str] = None
    meta: Optional[dict] = None


class DeliveryPersonUpdateForm(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    vehicle_type: Optional[str] = None
    vehicle_plate: Optional[str] = None
    is_active: Optional[bool] = None
    notes: Optional[str] = None
    meta: Optional[dict] = None


class DeliveryPersonUserResponse(DeliveryPersonModel):
    user: Optional[UserResponse] = None


class DeliveryPersonListResponse(BaseModel):
    items: list[DeliveryPersonUserResponse]
    total: int


####################
# Table Operations
####################


class DeliveryPersonTable:
    def insert_new_delivery_person(
        self, form_data: DeliveryPersonForm, db: Optional[Session] = None
    ) -> Optional[DeliveryPersonModel]:
        with get_db_context(db) as db:
            delivery_person = DeliveryPersonModel(
                **{
                    "id": str(uuid.uuid4()),
                    "shop_id": form_data.shop_id,
                    "user_id": form_data.user_id,
                    "name": form_data.name,
                    "email": form_data.email,
                    "phone": form_data.phone,
                    "vehicle_type": form_data.vehicle_type,
                    "vehicle_plate": form_data.vehicle_plate,
                    "is_active": form_data.is_active,
                    "notes": form_data.notes,
                    "meta": form_data.meta,
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )

            new_delivery_person = DeliveryPerson(**delivery_person.model_dump())
            db.add(new_delivery_person)
            db.commit()
            return delivery_person

    def get_delivery_persons_by_shop_id(
        self,
        shop_id: str,
        skip: int = 0,
        limit: int = 50,
        active_only: bool = False,
        db: Optional[Session] = None,
    ) -> list[DeliveryPersonModel]:
        with get_db_context(db) as db:
            query = db.query(DeliveryPerson).filter(DeliveryPerson.shop_id == shop_id)
            if active_only:
                query = query.filter(DeliveryPerson.is_active == True)
            query = query.order_by(DeliveryPerson.created_at.desc())
            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)
            delivery_persons = query.all()
            return [DeliveryPersonModel.model_validate(dp) for dp in delivery_persons]

    def get_delivery_person_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[DeliveryPersonModel]:
        with get_db_context(db) as db:
            delivery_person = db.query(DeliveryPerson).filter(DeliveryPerson.id == id).first()
            return DeliveryPersonModel.model_validate(delivery_person) if delivery_person else None

    def update_delivery_person_by_id(
        self, id: str, form_data: DeliveryPersonUpdateForm, db: Optional[Session] = None
    ) -> Optional[DeliveryPersonModel]:
        with get_db_context(db) as db:
            delivery_person = db.query(DeliveryPerson).filter(DeliveryPerson.id == id).first()
            if not delivery_person:
                return None

            form_data = form_data.model_dump(exclude_unset=True)

            if "name" in form_data:
                delivery_person.name = form_data["name"]
            if "email" in form_data:
                delivery_person.email = form_data["email"]
            if "phone" in form_data:
                delivery_person.phone = form_data["phone"]
            if "vehicle_type" in form_data:
                delivery_person.vehicle_type = form_data["vehicle_type"]
            if "vehicle_plate" in form_data:
                delivery_person.vehicle_plate = form_data["vehicle_plate"]
            if "is_active" in form_data:
                delivery_person.is_active = form_data["is_active"]
            if "notes" in form_data:
                delivery_person.notes = form_data["notes"]
            if "meta" in form_data:
                delivery_person.meta = {**delivery_person.meta, **form_data["meta"]} if delivery_person.meta else form_data["meta"]

            delivery_person.updated_at = int(time.time_ns())

            db.commit()
            return DeliveryPersonModel.model_validate(delivery_person) if delivery_person else None

    def delete_delivery_person_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(DeliveryPerson).filter(DeliveryPerson.id == id).delete()
                db.commit()
                return True
        except Exception:
            return False


DeliveryPersons = DeliveryPersonTable()
