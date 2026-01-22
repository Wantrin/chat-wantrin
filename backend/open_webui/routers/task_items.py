import json
import logging
from typing import Optional


from fastapi import APIRouter, Depends, HTTPException, Request, status, BackgroundTasks
from pydantic import BaseModel

from open_webui.socket.main import sio

from open_webui.models.groups import Groups
from open_webui.models.users import Users, UserResponse
from open_webui.models.task_items import (
    TaskItemListResponse,
    TaskItems,
    TaskItemModel,
    TaskItemForm,
    TaskItemUpdateForm,
    TaskItemUserResponse,
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
# GetTaskItems
############################


class TaskItemItemResponse(BaseModel):
    id: str
    title: str
    description: Optional[str] = None
    completed: bool = False
    data: Optional[dict] = None
    updated_at: int
    created_at: int
    user: Optional[UserResponse] = None


@router.get("/", response_model=list[TaskItemItemResponse])
async def get_task_items(
    request: Request,
    page: Optional[int] = None,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.task_items", request.app.state.config.USER_PERMISSIONS, db=db
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

    task_items = TaskItems.get_task_items_by_user_id(user.id, "read", skip=skip, limit=limit, db=db)
    if not task_items:
        return []

    user_ids = list(set(task_item.user_id for task_item in task_items))
    users = {user.id: user for user in Users.get_users_by_user_ids(user_ids, db=db)}

    return [
        TaskItemUserResponse(
            **{
                **task_item.model_dump(),
                "user": UserResponse(**users[task_item.user_id].model_dump()),
            }
        )
        for task_item in task_items
        if task_item.user_id in users
    ]


@router.get("/search", response_model=TaskItemListResponse)
async def search_task_items(
    request: Request,
    query: Optional[str] = None,
    view_option: Optional[str] = None,
    permission: Optional[str] = None,
    completed: Optional[bool] = None,
    order_by: Optional[str] = None,
    direction: Optional[str] = None,
    page: Optional[int] = 1,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.task_items", request.app.state.config.USER_PERMISSIONS, db=db
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
    if completed is not None:
        filter["completed"] = completed
    if order_by:
        filter["order_by"] = order_by
    if direction:
        filter["direction"] = direction

    if not user.role == "admin" or not BYPASS_ADMIN_ACCESS_CONTROL:
        groups = Groups.get_groups_by_member_id(user.id, db=db)
        if groups:
            filter["group_ids"] = [group.id for group in groups]

        filter["user_id"] = user.id

    return TaskItems.search_task_items(user.id, filter, skip=skip, limit=limit, db=db)


############################
# CreateNewTaskItem
############################


@router.post("/create", response_model=Optional[TaskItemModel])
async def create_new_task_item(
    request: Request,
    form_data: TaskItemForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.task_items", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    try:
        task_item = TaskItems.insert_new_task_item(user.id, form_data, db=db)
        return task_item
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# GetTaskItemById
############################


class TaskItemResponse(TaskItemModel):
    write_access: bool = False


@router.get("/{id}", response_model=Optional[TaskItemResponse])
async def get_task_item_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.task_items", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    task_item = TaskItems.get_task_item_by_id(id, db=db)
    if not task_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != task_item.user_id
        and (
            not has_access(
                user.id, type="read", access_control=task_item.access_control, db=db
            )
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    write_access = (
        user.role == "admin"
        or (user.id == task_item.user_id)
        or has_access(
            user.id,
            type="write",
            access_control=task_item.access_control,
            strict=False,
            db=db,
        )
    )

    return TaskItemResponse(**task_item.model_dump(), write_access=write_access)


############################
# UpdateTaskItemById
############################


@router.post("/{id}/update", response_model=Optional[TaskItemModel])
async def update_task_item_by_id(
    request: Request,
    id: str,
    form_data: TaskItemForm,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.task_items", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    task_item = TaskItems.get_task_item_by_id(id, db=db)
    if not task_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != task_item.user_id
        and not has_access(
            user.id, type="write", access_control=task_item.access_control, db=db
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
            "sharing.public_task_items",
            request.app.state.config.USER_PERMISSIONS,
            db=db,
        )
    ):
        form_data.access_control = {}

    try:
        update_form = TaskItemUpdateForm(**form_data.model_dump())
        task_item = TaskItems.update_task_item_by_id(id, update_form, db=db)
        await sio.emit(
            "task-item-events",
            task_item.model_dump(),
            to=f"task_item:{task_item.id}",
        )

        return task_item
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )


############################
# DeleteTaskItemById
############################


@router.delete("/{id}/delete", response_model=bool)
async def delete_task_item_by_id(
    request: Request,
    id: str,
    user=Depends(get_verified_user),
    db: Session = Depends(get_session),
):
    if user.role != "admin" and not has_permission(
        user.id, "features.task_items", request.app.state.config.USER_PERMISSIONS, db=db
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=ERROR_MESSAGES.UNAUTHORIZED,
        )

    task_item = TaskItems.get_task_item_by_id(id, db=db)
    if not task_item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=ERROR_MESSAGES.NOT_FOUND
        )

    if user.role != "admin" and (
        user.id != task_item.user_id
        and not has_access(
            user.id, type="write", access_control=task_item.access_control, db=db
        )
    ):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail=ERROR_MESSAGES.DEFAULT()
        )

    try:
        task_item = TaskItems.delete_task_item_by_id(id, db=db)
        return True
    except Exception as e:
        log.exception(e)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail=ERROR_MESSAGES.DEFAULT()
        )
