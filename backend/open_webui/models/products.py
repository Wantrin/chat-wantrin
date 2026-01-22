import json
import time
import uuid
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
# Product DB Schema
####################


class Product(Base):
    __tablename__ = "product"

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text)
    shop_id = Column(Text, nullable=False)

    name = Column(Text)
    description = Column(Text, nullable=True)
    price = Column(Float)
    image_url = Column(Text, nullable=True)
    image_urls = Column(JSON, nullable=True)
    stock = Column(BigInteger, default=0)
    category = Column(Text, nullable=True)
    currency = Column(Text, nullable=True)
    meta = Column(JSON, nullable=True)

    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class ProductModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str
    shop_id: str

    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    image_urls: list[str] = []
    stock: int = 0
    category: Optional[str] = None
    currency: Optional[str] = None
    meta: Optional[dict] = None

    access_control: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class ProductForm(BaseModel):
    name: str
    description: Optional[str] = None
    price: float
    image_url: Optional[str] = None
    image_urls: Optional[list[str]] = None
    stock: int = 0
    category: Optional[str] = None
    currency: Optional[str] = None
    shop_id: str
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class ProductUpdateForm(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    price: Optional[float] = None
    image_url: Optional[str] = None
    image_urls: Optional[list[str]] = None
    stock: Optional[int] = None
    category: Optional[str] = None
    currency: Optional[str] = None
    shop_id: Optional[str] = None  # Peut être modifié mais doit toujours avoir une valeur
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class ProductUserResponse(ProductModel):
    user: Optional[UserResponse] = None


class ProductItemResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    price: float
    image_url: Optional[str]
    image_urls: Optional[list[str]] = None
    stock: int
    category: Optional[str]
    updated_at: int
    created_at: int
    user: Optional[UserResponse] = None


class ProductListResponse(BaseModel):
    items: list[ProductUserResponse]
    total: int


class ProductTable:
    def _normalize_image_urls(self, image_urls: Optional[list[str]], image_url: Optional[str]) -> list[str]:
        # Prefer explicit list; fallback to legacy single image_url
        if image_urls is not None:
            return [u for u in image_urls if u]
        if image_url:
            return [image_url]
        return []

    def _has_permission(self, db, query, filter: dict, permission: str = "read"):
        group_ids = filter.get("group_ids", [])
        user_id = filter.get("user_id")
        shop_id = filter.get("shop_id")
        dialect_name = db.bind.dialect.name

        conditions = []

        # Public access conditions - always show public products
        # If shop_id is specified, show all public products in that shop
        # Otherwise, show public products that user can access
        conditions.extend(
            [
                Product.access_control.is_(None),
                cast(Product.access_control, String) == "null",
            ]
        )

        # User-level permission (owner has all permissions)
        if user_id:
            conditions.append(Product.user_id == user_id)

        # Group-level permission
        if group_ids:
            group_conditions = []
            for gid in group_ids:
                if dialect_name == "sqlite":
                    group_conditions.append(
                        Product.access_control[permission]["group_ids"].contains([gid])
                    )
                elif dialect_name == "postgresql":
                    group_conditions.append(
                        cast(
                            Product.access_control[permission]["group_ids"],
                            JSONB,
                        ).contains([gid])
                    )
            if group_conditions:
                conditions.append(or_(*group_conditions))

        if conditions:
            query = query.filter(or_(*conditions))

        return query

    def insert_new_product(
        self, user_id: str, form_data: ProductForm, db: Optional[Session] = None
    ) -> Optional[ProductModel]:
        with get_db_context(db) as db:
            image_urls = self._normalize_image_urls(form_data.image_urls, form_data.image_url)
            if len(image_urls) == 0:
                raise ValueError("At least one product image is required")
            product = ProductModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    **form_data.model_dump(exclude={"image_urls"}),
                    "image_urls": image_urls,
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )

            new_product = Product(**product.model_dump())

            db.add(new_product)
            db.commit()
            return product

    def get_products(
        self, skip: int = 0, limit: int = 50, db: Optional[Session] = None
    ) -> list[ProductModel]:
        with get_db_context(db) as db:
            query = db.query(Product).order_by(Product.updated_at.desc())
            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)
            products = query.all()
            return [ProductModel.model_validate(product) for product in products]

    def search_products(
        self,
        user_id: Optional[str],
        filter: dict = {},
        skip: int = 0,
        limit: int = 30,
        db: Optional[Session] = None,
    ) -> ProductListResponse:
        with get_db_context(db) as db:
            query = db.query(Product, User).outerjoin(User, User.id == Product.user_id)
            if filter:
                query_key = filter.get("query")
                if query_key:
                    query = query.filter(
                        or_(
                            Product.name.ilike(f"%{query_key}%"),
                            Product.description.ilike(f"%{query_key}%"),
                            Product.category.ilike(f"%{query_key}%"),
                        )
                    )

                category = filter.get("category")
                if category:
                    query = query.filter(Product.category == category)

                currency = filter.get("currency")
                if currency:
                    try:
                        query = query.filter(Product.currency == currency)
                    except Exception:
                        # Column might not exist yet if migration hasn't been run
                        # In this case, we'll just skip the currency filter
                        pass

                shop_id = filter.get("shop_id")
                if shop_id:
                    query = query.filter(Product.shop_id == shop_id)

                view_option = filter.get("view_option")
                if view_option == "created" and user_id:
                    query = query.filter(Product.user_id == user_id)
                elif view_option == "shared" and user_id:
                    query = query.filter(Product.user_id != user_id)
                # If view_option is None or "all", don't filter by user_id here
                # The _has_permission method will handle showing accessible products

                # Apply access control filtering
                if "permission" in filter:
                    permission = filter["permission"]
                else:
                    permission = "read"

                # For public access (user_id is None), only show public products
                if user_id is None:
                    query = query.filter(
                        or_(
                            Product.access_control.is_(None),
                            cast(Product.access_control, String) == "null",
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
                        query = query.order_by(Product.name.asc())
                    else:
                        query = query.order_by(Product.name.desc())
                elif order_by == "price":
                    if direction == "asc":
                        query = query.order_by(Product.price.asc())
                    else:
                        query = query.order_by(Product.price.desc())
                elif order_by == "created_at":
                    if direction == "asc":
                        query = query.order_by(Product.created_at.asc())
                    else:
                        query = query.order_by(Product.created_at.desc())
                elif order_by == "updated_at":
                    if direction == "asc":
                        query = query.order_by(Product.updated_at.asc())
                    else:
                        query = query.order_by(Product.updated_at.desc())
                else:
                    query = query.order_by(Product.updated_at.desc())

            else:
                query = query.order_by(Product.updated_at.desc())

            # Count BEFORE pagination
            total = query.count()

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            items = query.all()

            products = []
            for product, user in items:
                try:
                    product_model = ProductModel.model_validate(product)
                except Exception:
                    # If currency column doesn't exist yet, create a dict without it
                    product_dict = {
                        "id": product.id,
                        "user_id": product.user_id,
                        "shop_id": product.shop_id,
                        "name": product.name,
                        "description": product.description,
                        "price": product.price,
                        "image_url": product.image_url,
                        "image_urls": product.image_urls or [],
                        "stock": product.stock or 0,
                        "category": product.category,
                        "currency": getattr(product, 'currency', None),  # Safe access
                        "meta": product.meta,
                        "access_control": product.access_control,
                        "created_at": product.created_at,
                        "updated_at": product.updated_at,
                    }
                    product_model = ProductModel(**product_dict)
                
                products.append(
                    ProductUserResponse(
                        **product_model.model_dump(),
                        user=(
                            UserResponse(**UserModel.model_validate(user).model_dump())
                            if user
                            else None
                        ),
                    )
                )

            return ProductListResponse(items=products, total=total)

    def get_products_by_user_id(
        self,
        user_id: str,
        permission: str = "read",
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[ProductModel]:
        with get_db_context(db) as db:
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
            ]

            query = db.query(Product).order_by(Product.updated_at.desc())
            query = self._has_permission(
                db, query, {"user_id": user_id, "group_ids": user_group_ids}, permission
            )

            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)

            products = query.all()
            return [ProductModel.model_validate(product) for product in products]

    def get_product_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[ProductModel]:
        with get_db_context(db) as db:
            product = db.query(Product).filter(Product.id == id).first()
            if not product:
                return None
            try:
                return ProductModel.model_validate(product)
            except Exception as e:
                # If currency column doesn't exist yet, create a dict without it
                product_dict = {
                    "id": product.id,
                    "user_id": product.user_id,
                    "shop_id": product.shop_id,
                    "name": product.name,
                    "description": product.description,
                    "price": product.price,
                    "image_url": product.image_url,
                    "image_urls": product.image_urls or [],
                    "stock": product.stock or 0,
                    "category": product.category,
                    "currency": getattr(product, 'currency', None),  # Safe access
                    "meta": product.meta,
                    "access_control": product.access_control,
                    "created_at": product.created_at,
                    "updated_at": product.updated_at,
                }
                return ProductModel(**product_dict)

    def update_product_by_id(
        self, id: str, form_data: ProductUpdateForm, db: Optional[Session] = None
    ) -> Optional[ProductModel]:
        with get_db_context(db) as db:
            product = db.query(Product).filter(Product.id == id).first()
            if not product:
                return None

            form_data = form_data.model_dump(exclude_unset=True)

            if "name" in form_data:
                product.name = form_data["name"]
            if "description" in form_data:
                product.description = form_data["description"]
            if "price" in form_data:
                product.price = form_data["price"]
            if "image_url" in form_data:
                product.image_url = form_data["image_url"]
            if "image_urls" in form_data:
                # if explicitly provided, it wins; else keep existing
                product.image_urls = [u for u in (form_data["image_urls"] or []) if u]
            if "stock" in form_data:
                product.stock = form_data["stock"]
            if "category" in form_data:
                product.category = form_data["category"]
            if "currency" in form_data:
                product.currency = form_data["currency"]
            if "shop_id" in form_data:
                product.shop_id = form_data["shop_id"]
            if "meta" in form_data:
                product.meta = {**product.meta, **form_data["meta"]} if product.meta else form_data["meta"]

            if "access_control" in form_data:
                product.access_control = form_data["access_control"]

            product.updated_at = int(time.time_ns())

            db.commit()
            # Backfill runtime if legacy image_url exists but image_urls missing
            if (not product.image_urls) and product.image_url:
                product.image_urls = [product.image_url]
                db.commit()
            if not product.image_urls:
                raise ValueError("At least one product image is required")
            return ProductModel.model_validate(product) if product else None

    def delete_product_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(Product).filter(Product.id == id).delete()
                db.commit()
                return True
        except Exception:
            return False


Products = ProductTable()
