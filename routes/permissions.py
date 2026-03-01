from project_utils import (
    has_project_lead_permissions,
    has_weak_project_permissions,
    has_objective_write_permissions,
    has_key_result_write_permissions,
    has_task_write_permissions,
)
from dataclasses import dataclass

from litestar import get
from litestar.params import Parameter
from litestar.connection import Request

from sqlalchemy.ext.asyncio import AsyncSession


@dataclass
class ProjectPermissionsResponse:
    can_lead: bool
    can_write: bool


@dataclass
class PermissionsResponse:
    can_write: bool


@get("/projects/{project_id:str}/permissions")
async def get_project_permissions(
    db_session: AsyncSession,
    request: Request,
    project_id: str = Parameter(),
) -> ProjectPermissionsResponse:
    return ProjectPermissionsResponse(
        can_lead=await has_project_lead_permissions(
            db_session, request.user, project_id
        ),
        can_write=await has_weak_project_permissions(
            db_session, request.user, project_id
        ),
    )


@get("/objectives/{objective_id:str}/permissions")
async def get_objective_permissions(
    db_session: AsyncSession,
    request: Request,
    objective_id: str = Parameter(),
) -> PermissionsResponse:
    return PermissionsResponse(
        can_write=await has_objective_write_permissions(
            db_session, request.user, objective_id
        ),
    )


@get("/key_results/{key_result_id:str}/permissions")
async def get_key_result_permissions(
    db_session: AsyncSession,
    request: Request,
    key_result_id: str = Parameter(),
) -> PermissionsResponse:
    return PermissionsResponse(
        can_write=await has_key_result_write_permissions(
            db_session, request.user, key_result_id
        ),
    )


@get("/tasks/{task_id:str}/permissions")
async def get_task_permissions(
    db_session: AsyncSession,
    request: Request,
    task_id: str = Parameter(),
) -> PermissionsResponse:
    return PermissionsResponse(
        can_write=await has_task_write_permissions(db_session, request.user, task_id),
    )
