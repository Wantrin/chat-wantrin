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
from sqlalchemy import BigInteger, Boolean, Column, String, Text, JSON
from sqlalchemy.dialects.postgresql import JSONB


from sqlalchemy import or_, func, select, and_, text, cast, or_, and_, func
from sqlalchemy.sql import exists

####################
# TaskItem DB Schema
####################


class TaskItem(Base):
    __tablename__ = "task_item"

    id = Column(Text, primary_key=True, unique=True)
    user_id = Column(Text)

    title = Column(Text)
    description = Column(Text, nullable=True)
    completed = Column(Boolean, default=False)
    data = Column(JSON, nullable=True)
    meta = Column(JSON, nullable=True)

    access_control = Column(JSON, nullable=True)

    created_at = Column(BigInteger)
    updated_at = Column(BigInteger)


class TaskItemModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    user_id: str

    title: str
    description: Optional[str] = None
    completed: bool = False
    data: Optional[dict] = None
    meta: Optional[dict] = None

    access_control: Optional[dict] = None

    created_at: int  # timestamp in epoch
    updated_at: int  # timestamp in epoch


####################
# Forms
####################


class TaskItemForm(BaseModel):
    title: str
    description: Optional[str] = None
    completed: Optional[bool] = False
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class TaskItemUpdateForm(BaseModel):
    title: Optional[str] = None
    description: Optional[str] = None
    completed: Optional[bool] = None
    data: Optional[dict] = None
    meta: Optional[dict] = None
    access_control: Optional[dict] = None


class TaskItemUserResponse(TaskItemModel):
    user: Optional[UserResponse] = None


class TaskItemItemResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    completed: bool = False
    data: Optional[dict] = None
    updated_at: int
    created_at: int
    user: Optional[UserResponse] = None


class TaskItemListResponse(BaseModel):
    items: list[TaskItemUserResponse]
    total: int


class TaskItemTable:
    def _has_permission(self, db, query, filter: dict, permission: str = "read"):
        group_ids = filter.get("group_ids", [])
        user_id = filter.get("user_id")
        dialect_name = db.bind.dialect.name

        conditions = []

        # Handle read_only permission separately
        if permission == "read_only":
            # For read_only, we want items where:
            # 1. User has explicit read permission (via groups or user-level)
            # 2. BUT does NOT have write permission
            # 3. Public items are NOT considered read_only

            read_conditions = []

            # Group-level read permission
            if group_ids:
                group_read_conditions = []
                for gid in group_ids:
                    if dialect_name == "sqlite":
                        group_read_conditions.append(
                            TaskItem.access_control["read"]["group_ids"].contains([gid])
                        )
                    elif dialect_name == "postgresql":
                        group_read_conditions.append(
                            cast(
                                TaskItem.access_control["read"]["group_ids"],
                                JSONB,
                            ).contains([gid])
                        )

                if group_read_conditions:
                    read_conditions.append(or_(*group_read_conditions))

            # Combine read conditions
            if read_conditions:
                has_read = or_(*read_conditions)
            else:
                # If no read conditions, return empty result
                return query.filter(False)

            # Now exclude items where user has write permission
            write_exclusions = []

            # Exclude items owned by user (they have implicit write)
            if user_id:
                write_exclusions.append(TaskItem.user_id != user_id)

            # Exclude items where user has explicit write permission via groups
            if group_ids:
                group_write_conditions = []
                for gid in group_ids:
                    if dialect_name == "sqlite":
                        group_write_conditions.append(
                            TaskItem.access_control["write"]["group_ids"].contains([gid])
                        )
                    elif dialect_name == "postgresql":
                        group_write_conditions.append(
                            cast(
                                TaskItem.access_control["write"]["group_ids"],
                                JSONB,
                            ).contains([gid])
                        )

                if group_write_conditions:
                    # User should NOT have write permission
                    write_exclusions.append(~or_(*group_write_conditions))

            # Exclude public items (items without access_control)
            write_exclusions.append(TaskItem.access_control.isnot(None))
            write_exclusions.append(cast(TaskItem.access_control, String) != "null")

            # Combine: has read AND does not have write AND not public
            if write_exclusions:
                query = query.filter(and_(has_read, *write_exclusions))
            else:
                query = query.filter(has_read)

            return query

        # Original logic for other permissions (read, write, etc.)
        # Public access conditions
        if group_ids or user_id:
            conditions.extend(
                [
                    TaskItem.access_control.is_(None),
                    cast(TaskItem.access_control, String) == "null",
                ]
            )

        # User-level permission (owner has all permissions)
        if user_id:
            conditions.append(TaskItem.user_id == user_id)

        # Group-level permission
        if group_ids:
            group_conditions = []
            for gid in group_ids:
                if dialect_name == "sqlite":
                    group_conditions.append(
                        TaskItem.access_control[permission]["group_ids"].contains([gid])
                    )
                elif dialect_name == "postgresql":
                    group_conditions.append(
                        cast(
                            TaskItem.access_control[permission]["group_ids"],
                            JSONB,
                        ).contains([gid])
                    )
            conditions.append(or_(*group_conditions))

        if conditions:
            query = query.filter(or_(*conditions))

        return query

    def insert_new_task_item(
        self, user_id: str, form_data: TaskItemForm, db: Optional[Session] = None
    ) -> Optional[TaskItemModel]:
        with get_db_context(db) as db:
            task_item = TaskItemModel(
                **{
                    "id": str(uuid.uuid4()),
                    "user_id": user_id,
                    **form_data.model_dump(),
                    "created_at": int(time.time_ns()),
                    "updated_at": int(time.time_ns()),
                }
            )

            new_task_item = TaskItem(**task_item.model_dump())

            db.add(new_task_item)
            db.commit()
            return task_item

    def get_task_items(
        self, skip: int = 0, limit: int = 50, db: Optional[Session] = None
    ) -> list[TaskItemModel]:
        with get_db_context(db) as db:
            query = db.query(TaskItem).order_by(TaskItem.updated_at.desc())
            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)
            task_items = query.all()
            return [TaskItemModel.model_validate(task_item) for task_item in task_items]

    def search_task_items(
        self,
        user_id: str,
        filter: dict = {},
        skip: int = 0,
        limit: int = 30,
        db: Optional[Session] = None,
    ) -> TaskItemListResponse:
        with get_db_context(db) as db:
            query = db.query(TaskItem, User).outerjoin(User, User.id == TaskItem.user_id)
            if filter:
                query_key = filter.get("query")
                if query_key:
                    # Normalize search by removing hyphens and spaces
                    normalized_query = query_key.replace("-", "").replace(" ", "")
                    query = query.filter(
                        or_(
                            func.replace(
                                func.replace(TaskItem.title, "-", ""), " ", ""
                            ).ilike(f"%{normalized_query}%"),
                            func.replace(
                                func.replace(
                                    TaskItem.description, "-", ""
                                ),
                                " ",
                                "",
                            ).ilike(f"%{normalized_query}%"),
                        )
                    )

                completed_filter = filter.get("completed")
                if completed_filter is not None:
                    query = query.filter(TaskItem.completed == completed_filter)

                view_option = filter.get("view_option")
                if view_option == "created":
                    query = query.filter(TaskItem.user_id == user_id)
                elif view_option == "shared":
                    query = query.filter(TaskItem.user_id != user_id)

                # Apply access control filtering
                if "permission" in filter:
                    permission = filter["permission"]
                else:
                    permission = "write"

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
                        query = query.order_by(TaskItem.title.asc())
                    else:
                        query = query.order_by(TaskItem.title.desc())
                elif order_by == "created_at":
                    if direction == "asc":
                        query = query.order_by(TaskItem.created_at.asc())
                    else:
                        query = query.order_by(TaskItem.created_at.desc())
                elif order_by == "updated_at":
                    if direction == "asc":
                        query = query.order_by(TaskItem.updated_at.asc())
                    else:
                        query = query.order_by(TaskItem.updated_at.desc())
                else:
                    query = query.order_by(TaskItem.updated_at.desc())

            else:
                query = query.order_by(TaskItem.updated_at.desc())

            # Count BEFORE pagination
            total = query.count()

            if skip:
                query = query.offset(skip)
            if limit:
                query = query.limit(limit)

            items = query.all()

            task_items = []
            for task_item, user in items:
                task_items.append(
                    TaskItemUserResponse(
                        **TaskItemModel.model_validate(task_item).model_dump(),
                        user=(
                            UserResponse(**UserModel.model_validate(user).model_dump())
                            if user
                            else None
                        ),
                    )
                )

            return TaskItemListResponse(items=task_items, total=total)

    def get_task_items_by_user_id(
        self,
        user_id: str,
        permission: str = "read",
        skip: int = 0,
        limit: int = 50,
        db: Optional[Session] = None,
    ) -> list[TaskItemModel]:
        with get_db_context(db) as db:
            user_group_ids = [
                group.id for group in Groups.get_groups_by_member_id(user_id, db=db)
            ]

            query = db.query(TaskItem).order_by(TaskItem.updated_at.desc())
            query = self._has_permission(
                db, query, {"user_id": user_id, "group_ids": user_group_ids}, permission
            )

            if skip is not None:
                query = query.offset(skip)
            if limit is not None:
                query = query.limit(limit)

            task_items = query.all()
            return [TaskItemModel.model_validate(task_item) for task_item in task_items]

    def get_task_item_by_id(
        self, id: str, db: Optional[Session] = None
    ) -> Optional[TaskItemModel]:
        with get_db_context(db) as db:
            task_item = db.query(TaskItem).filter(TaskItem.id == id).first()
            return TaskItemModel.model_validate(task_item) if task_item else None

    def update_task_item_by_id(
        self, id: str, form_data: TaskItemUpdateForm, db: Optional[Session] = None
    ) -> Optional[TaskItemModel]:
        with get_db_context(db) as db:
            task_item = db.query(TaskItem).filter(TaskItem.id == id).first()
            if not task_item:
                return None

            form_data = form_data.model_dump(exclude_unset=True)

            if "title" in form_data:
                task_item.title = form_data["title"]
            if "description" in form_data:
                task_item.description = form_data["description"]
            if "completed" in form_data:
                task_item.completed = form_data["completed"]
            if "data" in form_data:
                if task_item.data is None:
                    task_item.data = form_data["data"]
                else:
                    task_item.data = {**task_item.data, **form_data["data"]}
            if "meta" in form_data:
                if task_item.meta is None:
                    task_item.meta = form_data["meta"]
                else:
                    task_item.meta = {**task_item.meta, **form_data["meta"]}

            if "access_control" in form_data:
                task_item.access_control = form_data["access_control"]

            task_item.updated_at = int(time.time_ns())

            db.commit()
            return TaskItemModel.model_validate(task_item) if task_item else None

    def delete_task_item_by_id(self, id: str, db: Optional[Session] = None) -> bool:
        try:
            with get_db_context(db) as db:
                db.query(TaskItem).filter(TaskItem.id == id).delete()
                db.commit()
                return True
        except Exception:
            return False


TaskItems = TaskItemTable()
