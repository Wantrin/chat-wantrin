import json
import time
import uuid
import re
from typing import Optional
from functools import lru_cache

from sqlalchemy.orm import Session
from open_webui.internal.db import Base, get_db, get_db_context
from open_webui.models.groups import Groups
from open_webui.utils.access_control import has_access
from open_webui.models.users import User, UserModel, Users, UserResponse

from pydantic import BaseModel, ConfigDict
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON, Float
from sqlalchemy.dialects.postgresql import JSONB

from sqlalchemy import or_, func, select, and_, text, cast
from sqlalchemy.sql import exists

####################
# Shop DB Schema
####################


class Shop(Base):
    __tablename__ = "shop"

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text)

    name = Column(Text)
    description = Column(Text, nullable=True)
    image_url = Column(Text, nullable=True)
    url = Column(Text, nullable=True, unique=True)  # URL slug for public access
    primary_color = Column(Text, nullable=True)  # Primary brand color (hex code)
    secondary_color = Column(Text, nullable=True)  # Secondary brand color (hex code)
    meta = Column(JSON, nullable=True)

    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ShopModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    primary_color: Optional[str] = None  # Primary brand color (hex code, e.g., #3B82F6)
    secondary_color: Optional[str] = None  # Secondary brand color (hex code, e.g., #F97316)
    meta: Optional[dict] = None

    access_control: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class ShopForm(BaseModel):
    name: str
    description: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    primary_color: Optional[str] = None  # Primary brand color (hex code, e.g., #3B82F6)
    secondary_color: Optional[str] = None  # Secondary brand color (hex code, e.g., #F97316)
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class ShopUpdateForm(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    image_url: Optional[str] = None
    url: Optional[str] = None
    primary_color: Optional[str] = None  # Primary brand color (hex code, e.g., #3B82F6)
    secondary_color: Optional[str] = None  # Secondary brand color (hex code, e.g., #F97316)
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class ShopUserResponse(ShopModel):
    user: Optional[UserResponse] = None


class ShopItemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    image_url: Optional[str]
    updated_at: int
    created_at: int
    user: Optional[UserResponse] = None


class ShopListResponse(BaseModel):
    items: list[ShopUserResponse]
    total: int


def generate_slug(name: str) -> str:
    """Generate a URL-friendly slug from a shop name."""
    if not name:
        return ""
    # Convert to lowercase
    slug = name.lower().strip()
    # Replace spaces and special characters with hyphens
    slug = re.sub(r'[^\w\s-]', '', slug)
    slug = re.sub(r'[-\s]+', '-', slug)
    # Remove leading/trailing hyphens
    slug = slug.strip('-')
    return slug


def sanitize_url(url: str) -> str:
    """Sanitize a user-provided URL slug by removing spaces and invalid characters."""
    if not url:
        return ""
    # Remove all spaces
    url = url.replace(' ', '-')
    # Convert to lowercase
    url = url.lower().strip()
    # Remove invalid characters (keep only alphanumeric and hyphens)
    url = re.sub(r'[^a-z0-9-]', '', url)
    # Replace multiple consecutive hyphens with single hyphen
    url = re.sub(r'-+', '-', url)
    # Remove leading/trailing hyphens
    url = url.strip('-')
    return url


def make_unique_slug(base_slug: str, db: Session, exclude_id: Optional[str] = None) -> str:
    """Make a slug unique by appending a number if needed."""
    slug = base_slug
    counter = 1
    while True:
        query = db.query(Shop).filter(Shop.url == slug)
        if exclude_id:
            query = query.filter(Shop.id != exclude_id)
        existing = query.first()
        if not existing:
            return slug
        slug = f"{base_slug}-{counter}"
        counter += 1


class ShopTable:
    def _has_permission(self, db, query, filter: dict, permission: str = "read"):
        group_ids = filter.get("group_ids", [])
        user_id = filter.get("user_id")
        dialect_name = db.bind.dialect.name

        conditions = []

        # Public access conditions
        if group_ids or user_id:
            conditions.extend(
                [
                    Shop.access_control.is_(None),
                    cast(Shop.access_control, String) == "null",
                ]
            )

        # User-level permission (owner has all permissions)
        if user_id:
            conditions.append(Shop.user_id == user_id)

        # Group-level permission
        if group_ids:
            group_conditions = []
            for gid in group_ids:
                if dialect_name == "sqlite":
                    group_conditions.append(
                        Shop.access_control[permission]["group_ids"].contains([gid])
                    )
                elif dialect_name == "postgresql":
                    group_conditions.append(
                        cast(
                            Shop.access_control[permission]["group_ids"],
                            JSONB,
                        ).contains([gid])
                    )
            conditions.append(or_(*group_conditions))

        if conditions:
            query = query.filter(or_(*conditions))

        return query

    def insert_new_shop(
        self, user_id: str, form_data: ShopForm, db: Optional[Session] = None
    ) -> Optional[ShopModel]:
        with get_db_context(db) as db:
            form_dict = form_data.model_dump()
            
            # Generate URL slug if not provided
            if not form_dict.get("url"):
                base_slug = generate_slug(form_dict["name"])
                form_dict["url"] = make_unique_slug(base_slug, db)
            else:
                # Sanitize and ensure provided URL is unique
                sanitized_url = sanitize_url(form_dict["url"])
                if sanitized_url:
                    form_dict["url"] = make_unique_slug(sanitized_url, db)
                else:
                    # If sanitization results in empty, generate from name
                    base_slug = generate_slug(form_dict["name"])
                    form_dict["url"] = make_unique_slug(base_slug, db)
            
            shop = ShopModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    **form_dict,
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )

            new_shop = Shop(**shop.model_dump())

            db.add(new_shop)
            db.commit()
            return shop

    def get_shops(
        self, skip: int = 0, limit: int = 50, db: Optional[Session] = None
    ) -> list[ShopModel]:
        with get_db_context(db) as db:
            query = db.query(Shop).order_by(Shop.updated_at.desc())
            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)
            shops = query.all()
            return [ShopModel.model_validate(shop) for shop in shops]

    def search_shops(
        self,
        user_id: Optional[str],
        filter: dict = {},
        skip: int = 0,
        limit: int = 30,
        db: Optional[Session] = None,
    ) -> ShopListResponse:
        with get_db_context(db) as db:
            query = db.query(Shop, User).outerjoin(User, User.id == Shop.user_id)
            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(
                        or_(
                            Shop.name.ilike(f"%{query_key}%"),
                            Shop.description.ilike(f"%{query_key}%"),
                        )
                    )

                view_option = filter.get("view_option")
                if view_option == "created" and user_id:
                    query = query.filter(Shop.user_id == user_id)
                elif view_option == "shared" and user_id:
                    query = query.filter(Shop.user_id != user_id)

                # Apply access control filtering
                if "permission" in filter:
                    permission = filter["permission"]
                else:
                    permission = "read"

                # For public access (user_id is None), only show public shops
                if user_id is None:
                    query = query.filter(
                        or_(
                            Shop.access_control.is_(None),
                            cast(Shop.access_control, String) == "null",
                        )
                    )
                else:
                    query = self._has_permission(
                        db,
                        query,
                        filter,
                        permission=permission,
                    )

                order_by = filter.get("order_by")
                direction = filter.get("direction")

                if order_by == "name":
                    if direction == "asc":
                        query = query.order_by(Shop.name.asc())
                    else:
                        query = query.order_by(Shop.name.desc())
                elif order_by == "created_at":
                    if direction == "asc":
                        query = query.order_by(Shop.created_at.asc())
                    else:
                        query = query.order_by(Shop.created_at.desc())
                elif order_by == "updated_at":
                    if direction == "asc":
                        query = query.order_by(Shop.updated_at.asc())
                    else:
                        query = query.order_by(Shop.updated_at.desc())
                else:
                    query = query.order_by(Shop.updated_at.desc())

            else:
                query = query.order_by(Shop.updated_at.desc())

            # Count BEFORE pagination
            total = query.count()

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            items = query.all()

            shops = []
            for shop, user in items:
                shops.append(
                    ShopUserResponse(
                        **ShopModel.model_validate(shop).model_dump(),
                        user=(
                            UserResponse(**UserModel.model_validate(user).model_dump())
                            if user
                            else None
                        ),
                    )
                )

            return ShopListResponse(items=shops, total=total)

    def get_shops_by_user_id(
        self,
        user_id: str,
        permission: str = "read",
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[ShopModel]:
        with get_db_context(db) as db:
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
            ]

            query = db.query(Shop).order_by(Shop.updated_at.desc())
            query = self._has_permission(
                db, query, {"user_id": user_id, "group_ids": user_group_ids}, permission
            )

            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)

            shops = query.all()
            return [ShopModel.model_validate(shop) for shop in shops]

    def get_shop_by_id(
        self, shop_id: str, db: Optional[Session] = None
    ) -> Optional[ShopModel]:
        with get_db_context(db) as db:
            shop = db.query(Shop).filter(Shop.id == shop_id).first()
            return ShopModel.model_validate(shop) if shop else None

    def get_shop_by_url(
        self, url: str, db: Optional[Session] = None
    ) -> Optional[ShopModel]:
        """Get a shop by its URL slug."""
        with get_db_context(db) as db:
            shop = db.query(Shop).filter(Shop.url == url).first()
            return ShopModel.model_validate(shop) if shop else None

    def get_shop_by_id_or_url(
        self, identifier: str, db: Optional[Session] = None
    ) -> Optional[ShopModel]:
        """Get a shop by either its ID or URL slug."""
        # Try by ID first (UUID format)
        if len(identifier) == 36 and identifier.count('-') == 4:
            shop = self.get_shop_by_id(identifier, db=db)
            if shop:
                return shop
        # Try by URL
        return self.get_shop_by_url(identifier, db=db)

    def update_shop_by_id(
        self, shop_id: str, form_data: ShopUpdateForm, db: Optional[Session] = None
    ) -> Optional[ShopModel]:
        with get_db_context(db) as db:
            shop = db.query(Shop).filter(Shop.id == shop_id).first()
            if not shop:
                return None

            # Get all fields that were explicitly set (not using exclude_unset to catch url even if empty)
            form_data_dict = form_data.model_dump(exclude_unset=True)
            
            # Check if url was explicitly provided by checking the original model
            # This handles the case where url might be an empty string
            url_was_provided = form_data.url is not None or "url" in form_data_dict

            if "name" in form_data_dict:
                shop.name = form_data_dict["name"]
            if "description" in form_data_dict:
                shop.description = form_data_dict["description"]
            if "image_url" in form_data_dict:
                shop.image_url = form_data_dict["image_url"]
            if "primary_color" in form_data_dict:
                shop.primary_color = form_data_dict["primary_color"]
            if "secondary_color" in form_data_dict:
                shop.secondary_color = form_data_dict["secondary_color"]
            
            # Handle URL update
            if url_was_provided:
                # Get the URL value - prefer from dict if present, otherwise from model
                provided_url = form_data_dict.get("url") if "url" in form_data_dict else form_data.url
                
                # If URL is provided and not empty after stripping, use it
                if provided_url and provided_url.strip():
                    # User provided a URL - sanitize it and make it unique
                    sanitized_url = sanitize_url(provided_url)
                    if sanitized_url:
                        shop.url = make_unique_slug(sanitized_url, db, exclude_id=shop_id)
                    else:
                        # If sanitization results in empty string, generate from name
                        if "name" in form_data_dict:
                            base_slug = generate_slug(form_data_dict["name"])
                        else:
                            base_slug = generate_slug(shop.name)
                        if base_slug:
                            shop.url = make_unique_slug(base_slug, db, exclude_id=shop_id)
                elif provided_url == "":
                    # URL is explicitly set to empty string - regenerate from name
                    if "name" in form_data_dict:
                        base_slug = generate_slug(form_data_dict["name"])
                    else:
                        base_slug = generate_slug(shop.name)
                    if base_slug:
                        shop.url = make_unique_slug(base_slug, db, exclude_id=shop_id)
                # If provided_url is None, don't change the existing URL
            
            if "meta" in form_data_dict:
                shop.meta = {**shop.meta, **form_data_dict["meta"]} if shop.meta else form_data_dict["meta"]

            if "access_control" in form_data_dict:
                shop.access_control = form_data_dict["access_control"]

            shop.updated_at = int(time.time_ns())

            db.commit()
            db.refresh(shop)  # Refresh to get the latest data from database
            return ShopModel.model_validate(shop) if shop else None

    def delete_shop_by_id(self, shop_id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(Shop).filter(Shop.id == shop_id).delete()
                db.commit()
                return True
        except Exception:
            return False


Shops = ShopTable()
