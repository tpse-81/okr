from typing import cast, TypeVar, Generic
from project_utils import (
    check_value_within_bounds,
    get_projects_for_user,
    calculate_objective_progress,
    get_user_role_for_project,
    has_project_lead_permissions,
    has_weak_project_permissions,
    has_objective_write_permissions,
    has_key_result_write_permissions,
    has_task_write_permissions,
)
from webauthn_handlers import (
    webauthn_authenticate,
    webauthn_register,
    webauthn_get_authentication_options,
    webauthn_get_registration_options,
    webauthn_remove_credentials,
    webauthn_is_configured,
)
import os
from dataclasses import dataclass
from datetime import datetime, timezone

from litestar import Litestar, get, patch, post, delete
from litestar.openapi.spec import Components, SecurityScheme, Tag
from litestar.params import Parameter
from litestar.router import Router
from litestar.exceptions import (
    ClientException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.config.cors import CORSConfig
from litestar.connection import Request

# Importing the database models
from authentication import (
    AuthenticationMiddleware,
    hash_password,
    login_handler,
    change_password,
    totp_setup,
    totp_confirm,
    totp_disable,
    totp_is_configured,
    logout,
    get_user_by_name_or_mail,
    reset_password,
)

from dto.write_dto import (
    KeyResultWriteDTO,
    KeyResultWriteUpdateDTO,
    KeyResultCurrentValueUpdateDTO,
    ObjectiveWriteDTO,
    ProjectWriteDTO,
    TaskWriteDTO,
)
from models.project import Project, ArchiveReason
from models.objective import Objective
from models.key_result import KeyResult
from models.user import User
from models.task import Task
from models.project_objective import project_objective
from models.user_project import UserProject, UserRole


from dto.read_dto import (
    ProjectReadDTO,
    ObjectiveReadDTO,
    KeyResultReadDTO,
    TaskReadDTO,
    UserReadDTO,
)

import project_utils
from helpers import is_valid_email

from sqlalchemy import select, exists, and_, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from advanced_alchemy.extensions.litestar import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
)


from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin

import uuid

from config import config
from responses import SuccessResponse, UserRoleResponse


async def project_exists(db_session: AsyncSession, project_id: str) -> bool:
    result = await db_session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    return project is not None


async def objective_exists(db_session: AsyncSession, objective_id: str) -> bool:
    result = await db_session.execute(
        select(Objective).where(Objective.id == objective_id)
    )
    objective = result.scalar_one_or_none()
    return objective is not None


async def key_result_exists(db_session: AsyncSession, key_result_id: str) -> bool:
    result = await db_session.execute(
        select(KeyResult).where(KeyResult.id == key_result_id)
    )
    key_result = result.scalar_one_or_none()
    return key_result is not None


@get(["/", "/health", "/healthz"], include_in_schema=False)
async def main_page() -> str:
    """
    Renders a short status message if the app is running.

    return: a raw text string
    """
    return "OK"


# https://docs.litestar.dev/2/usage/dto/1-abstract-dto.html#wrapping-return-data
# https://github.com/orgs/litestar-org/discussions/3586
ProjectTypeVar = TypeVar("ProjectTypeVar")
ObjectiveTypeVar = TypeVar("ObjectiveTypeVar")


@dataclass
class ProjectContainer(Generic[ProjectTypeVar, ObjectiveTypeVar]):
    project: ProjectTypeVar
    objectives: list[ObjectiveTypeVar]
    progress: float


@get("/dashboard", return_dto=ProjectReadDTO)
async def get_dashboard(
    db_session: AsyncSession, user_id: str | None = Parameter()
) -> list[ProjectContainer]:
    if user_id:
        projects = await get_projects_for_user(db_session, uuid.UUID(user_id))
    else:
        projects: list[Project] = list(await db_session.scalars(select(Project)))

    projects = [p for p in projects if not p.is_archived]

    projects_with_info = []
    for project in projects:
        objectives = await project_utils.get_objectives_for_project(
            db_session, str(project.id)
        )

        # build average progress across all objectives
        progress_per_objective = [
            await calculate_objective_progress(db_session, objective.id)
            for objective in objectives
        ]

        if objectives:
            progress = sum(progress_per_objective) / len(objectives)
        else:
            progress = 1.0

        project_container = ProjectContainer(
            project=project,
            objectives=objectives,
            progress=progress,
        )
        projects_with_info.append(project_container)

    return projects_with_info


@get("/projects", return_dto=ProjectReadDTO)
async def get_projects(db_session: AsyncSession) -> list[Project]:
    """
    Get the list of projects.

    return: a JSON list of projects
    """
    return list(await db_session.scalars(select(Project)))


@get("/users/{user_id:str}/projects", return_dto=ProjectReadDTO)
async def get_projects_for_user_id(
    db_session: AsyncSession, user_id: str = Parameter()
) -> list[Project]:
    """
    Get the list of projects for a given user.

    param user_id: the ID of the user whose projects are returned
    return: a JSON list of projects for a user
    """
    return await get_projects_for_user(db_session, uuid.UUID(user_id))


@get("/projects/{project_id:str}", return_dto=ProjectReadDTO)
async def get_project(db_session: AsyncSession, project_id: str) -> Project:
    """
    Get the project with the given ID.

    param project_id: the ID of the project to return
    """
    project = await db_session.get(Project, project_id)
    if project is None:
        raise NotFoundException("project not found")

    return project


@get("/key_results", return_dto=KeyResultReadDTO)
async def get_key_results(db_session: AsyncSession) -> list[KeyResult]:
    """
    Get the list of key results.

    return: a JSON list of key results
    """
    return list(await db_session.scalars(select(KeyResult)))


@get("/key_results/{key_result_id:str}", return_dto=KeyResultReadDTO)
async def get_key_result(db_session: AsyncSession, key_result_id: str) -> KeyResult:
    """
    Get the key result with the given ID.

    param key_result_id: the ID of the key_result to return
    """
    key_result = await db_session.get(KeyResult, key_result_id)
    if key_result is None:
        raise NotFoundException("key_result not found")

    return key_result


@delete("/key_results/{key_result_id:str}")
async def delete_key_result(db_session: AsyncSession, key_result_id: str) -> None:
    """
    Delete a key result and all its tasks

    param key_result_id: the ID of the key result to delete
    """
    key_result = await db_session.get(KeyResult, key_result_id)
    if key_result is None:
        raise NotFoundException("Key result not found")

    await db_session.delete(key_result)
    await db_session.commit()


@get("/objectives/{objective_id:str}", return_dto=ObjectiveReadDTO)
async def get_objective(db_session: AsyncSession, objective_id: str) -> Objective:
    """
    Get the objective with the given ID.

    param objective_id: the ID of the objective to return
    """
    objective = await db_session.get(Objective, objective_id)
    if objective is None:
        raise NotFoundException("objective not found")

    return objective


@get("/objectives", return_dto=ObjectiveReadDTO)
async def get_objectives(db_session: AsyncSession) -> list[Objective]:
    """
    Get the list of Objectives.

    return: a JSON list of objectives
    """
    stmt = select(Objective).options(
        selectinload(Objective.children)  # eagerly load Objective children
    )  # eagerly load Objective children
    result = await db_session.execute(stmt)
    objectives = result.scalars().all()  # list of all Objectives
    return list(objectives)


@delete("/objectives/{objective_id:str}")
async def delete_objective(
    db_session: AsyncSession, request: Request, objective_id: str
) -> None:
    """
    Delete an objective and all its Key results and tasks

    param objective_id: the ID of the objective to delete
    """
    objective = await db_session.get(Objective, objective_id)
    if objective is None:
        raise NotFoundException("objective not found")

    if not await has_objective_write_permissions(
        db_session, request.user, objective_id
    ):
        raise PermissionDeniedException("no permissions to modify this objective")

    await db_session.refresh(objective, attribute_names=["children"])

    children = objective.children

    for child in children:
        child.parent_id = objective.parent_id

    # check if children need to be change archive status after losing parent
    await project_utils.archive_objective_including_children(db_session, children)
    await project_utils.unarchive_objective_including_children(db_session, children)

    await db_session.delete(objective)
    await db_session.commit()


@get("/tasks", return_dto=TaskReadDTO)
async def get_tasks(db_session: AsyncSession) -> list[Task]:
    """
    param key_result_id: the UUID of the key result whose tasks should be returned

    Gets the list of task for a given key result

    """

    result = await db_session.scalars(select(Task))
    return list(result)


@get("/tasks/{task_id:str}", return_dto=TaskReadDTO)
async def get_task(db_session: AsyncSession, task_id: str) -> Task:
    """
    Get the task with the given ID.

    param task_id: the ID of the task to return
    """
    task = await db_session.get(Task, task_id)
    if task is None:
        raise NotFoundException("task not found")

    return task


@get("/key_results/{key_result_id:str}/tasks", return_dto=TaskReadDTO)
async def get_tasks_from_key_result(
    key_result_id: str, db_session: AsyncSession
) -> list[Task]:
    """
    param key_result_id: the UUID of the key result whose tasks should be returned

    Gets the list of task for a given key result

    """

    result = await db_session.scalars(
        select(Task).where(Task.key_result_id == key_result_id)
    )
    return list(result)


@delete("/tasks/{task_id:str}")
async def delete_task(db_session: AsyncSession, request: Request, task_id: str) -> None:
    """
    Delete a single task

    param task_id: the ID of the task to delete
    """
    task = await db_session.get(Task, task_id)
    if task is None:
        raise NotFoundException("task not found")

    if not await has_task_write_permissions(db_session, request.user, task_id):
        raise PermissionDeniedException("no permissions to modify this task")

    await db_session.delete(task)
    await db_session.commit()


@delete("/users/{user_id:str}")
async def delete_user(db_session: AsyncSession, request: Request, user_id: str) -> None:
    """
    Delete a user and all related associations.
    To delete a user, the actor must be either
    - the admin (i.e. the admin deletes an other user account)
    - the same user that should be deleted (i.e. the user deletes itself)

    param user_id: the ID of the user to delete
    """
    user = await db_session.get(User, user_id)
    if user is None:
        raise NotFoundException("User not found")

    actor = cast(User, request.user)
    if not (actor.is_admin or actor.id == user.id):
        raise PermissionDeniedException("no permissions to delete user with given ID")

    if user.is_admin and actor.id != user.id:
        raise PermissionDeniedException(
            "admins may not reset the password of other admins"
        )

    await db_session.delete(user)
    await db_session.commit()


@post("/key_results/{key_result_id:str}/tasks", dto=TaskWriteDTO, return_dto=None)
async def create_task_for_key_result(
    db_session: AsyncSession,
    data: Task,
    request: Request,
    key_result_id: str = Parameter(),
) -> SuccessResponse:
    """
    Create a new task for a given key result.

    param key_result_id: the ID of the key result this task belongs to
    param description: the description of the key result
    param task_state: the state of the task can be ONLY one of the following: open", "planned", "in_progress", "done" or "cancelled"
    """

    if not await key_result_exists(db_session, key_result_id):
        raise NotFoundException("key result not found")

    if not await has_key_result_write_permissions(
        db_session, request.user, key_result_id
    ):
        raise PermissionDeniedException("no permissions to modify this key result")

    # randomly generate a task id
    task_id = uuid.uuid4()

    task = Task(
        id=task_id,
        name=data.name,
        description=data.description,
        task_state=data.task_state,
        key_result_id=key_result_id,
    )

    # create new database entry for key result with parameters
    db_session.add(task)
    await db_session.commit()

    return SuccessResponse("successfully created task")


@patch("/tasks/{task_id:str}", dto=TaskWriteDTO, return_dto=TaskReadDTO)
async def update_task(
    db_session: AsyncSession,
    request: Request,
    # all project parameters are mandatory, so enforce they're not unset
    data: Task,
    task_id: str = Parameter(),
) -> Task:
    """
    Update an existing task.

    param data: the updated task information to store
    param task_id: the ID of the task
    return: the updated task
    """

    task = await db_session.execute(select(Task).where(Task.id == task_id))
    task = task.scalar_one_or_none()
    if task is None:
        raise NotFoundException("task doesn't exist")

    if not await has_task_write_permissions(db_session, request.user, task_id):
        raise PermissionDeniedException("no permissions to modify this task")

    task.name = data.name
    task.description = data.description
    task.task_state = data.task_state

    # commit updated task to database
    await db_session.commit()

    return task


@post("/projects", dto=ProjectWriteDTO, return_dto=None)
async def create_project(
    db_session: AsyncSession,
    request: Request,
    # all project parameters are mandatory, so enforce they're not unset
    data: Project,
) -> SuccessResponse:
    """
    Create a new project.

    param data: the project information to store
    return: whether the project was successfully created
    """

    # randomly generate a project id
    project_id = uuid.uuid4()
    project = Project(
        id=project_id,
        name=data.name,
        deadline=data.deadline,
        creation_date=datetime.now(tz=timezone.utc),
        done=data.done,
        icon=data.icon,
    )

    # create new database entry for project with parameters from URL
    db_session.add(project)
    await db_session.commit()

    creator_id = str(request.user.id)

    db_session.add(
        UserProject(
            project_id=str(project_id),
            user_id=creator_id,
            role=UserRole.LEADER,
        )
    )
    await db_session.commit()

    return SuccessResponse("successfully created project")


@patch("/projects/{project_id:str}", dto=ProjectWriteDTO, return_dto=ProjectReadDTO)
async def update_project(
    db_session: AsyncSession,
    request: Request,
    # all project parameters are mandatory, so enforce they're not unset
    data: Project,
    project_id: str = Parameter(),
) -> Project:
    """
    Update an existing project.

    param data: the updated project information to store
    param project_id: the ID of the project
    return: the updated project
    """

    project = await db_session.execute(select(Project).where(Project.id == project_id))
    project = project.scalar_one_or_none()
    if project is None:
        raise NotFoundException("project doesn't exist")

    if not await has_project_lead_permissions(db_session, request.user, project_id):
        raise PermissionDeniedException("no permissions to update this project")

    project.name = data.name
    project.deadline = data.deadline
    project.done = data.done
    project.icon = data.icon

    # commit updated project to database
    await db_session.commit()

    return project


@delete("/projects/{project_id:str}")
async def delete_project(
    db_session: AsyncSession,
    request: Request,
    project_id: str = Parameter(),
) -> None:
    """
    Delete a project and automatically delete all objectives
    that are not linked to any other project.

    param project_id: the ID of the project to delete
    """

    project = await db_session.get(Project, project_id)
    if not project:
        raise NotFoundException("Project not found")

    if not await has_project_lead_permissions(db_session, request.user, project_id):
        raise PermissionDeniedException("no permissions to delete this project")

    # make the project archived for the archive_check logic
    project.is_archived = True

    objectives_for_project = await project_utils.get_objectives_for_project(
        db_session, project_id
    )
    remaining_objectives: list[Objective] = []

    for objective in objectives_for_project:
        has_other_project = await db_session.scalar(
            select(
                exists().where(
                    and_(
                        project_objective.c.objective_id == objective.id,
                        project_objective.c.project_id != project_id,
                    )
                )
            )
        )
        if not has_other_project:
            await db_session.delete(objective)
        else:
            remaining_objectives.append(objective)

    await db_session.flush()

    # deleting a project may force the remaining objectives to become archived
    await project_utils.archive_objective_including_children(
        db_session, remaining_objectives
    )

    await db_session.execute(sa_delete(Project).where(Project.id == project_id))
    await db_session.commit()


@get("/users", return_dto=UserReadDTO)
async def get_users(db_session: AsyncSession) -> list[User]:
    """
    Get the list of users (without password hash and 2FA).

    return: a JSON list of users
    """
    return list(await db_session.scalars(select(User)))


@get("/me", return_dto=UserReadDTO)
async def get_me(request: Request) -> User:
    return request.user


@dataclass
class CreateUserRequest:
    name: str
    email: str
    password: str


@post("/users/create")
async def create_user(
    db_session: AsyncSession, data: CreateUserRequest, request: Request
) -> SuccessResponse:
    """
    Create a new user.

    param data: the user data to create a new user from
    return: whether the user was successfully created
    """
    user = cast(User, request.user)
    if not user.is_admin:
        raise PermissionDeniedException("only admins may create new users")

    # check if there are any conflicts with existing users, e.g. if the username is already used by somebody else
    existing_user_clash = await get_user_by_name_or_mail(db_session, data.name)
    if not existing_user_clash:
        existing_user_clash = await get_user_by_name_or_mail(db_session, data.email)
    if existing_user_clash:
        raise ClientException("a user with this name or email already exists")

    if is_valid_email(data.name):
        raise ClientException("usernames must not be an e-mail addresses!")

    if not is_valid_email(data.email):
        raise ClientException("invalid email address")

    # randomly generate a user_id
    user_id = uuid.uuid4()
    password_hash = hash_password(data.password)
    user = User(
        id=user_id,
        name=data.name,
        email=data.email,
        password_hash=password_hash,
        two_fa_secret=None,
        is_admin=False,
        must_change_password=True,
    )

    db_session.add(user)
    await db_session.commit()

    return SuccessResponse("successfully created user")


@patch("/users/{user_id:str}/promote")
async def promote_user_to_admin(
    db_session: AsyncSession, request: Request, user_id: str = Parameter()
) -> SuccessResponse:
    """
    Promote an existing user to become an admin.
    Only the admin can call this to promote other users.
    There's no way for an admin to demote a user again, so this should be well-overthought.

    :param user_id: the id of the user to promote
    :return: a success response if the user was successfully promoted
    """
    actor = cast(User, request.user)
    if not actor.is_admin:
        raise PermissionDeniedException("only admins can promote other users to admin")

    user = await db_session.get(User, user_id)
    if not user:
        raise ClientException("user does not exist")

    user.is_admin = True
    await db_session.commit()

    return SuccessResponse("successfully promoted user to admin")


@post(
    "/objectives/{objective_id:str}/key_results", dto=KeyResultWriteDTO, return_dto=None
)
async def create_key_result(
    db_session: AsyncSession,
    # all parameters are mandatory, so enforce they're not unset
    request: Request,
    data: KeyResult,
    objective_id: str = Parameter(),
) -> SuccessResponse:
    """
    Create a new key result.

    param data: the key result to create
    return: a JSON object containing a success message
    """
    if not objective_id:
        raise ClientException("invalid objective id")

    if not await objective_exists(db_session, objective_id):
        raise NotFoundException("Objective doesn't exist")

    if not await has_objective_write_permissions(
        db_session, request.user, objective_id
    ):
        raise PermissionDeniedException("no permissions to modify this objective")

    # randomly generate a key_result id
    key_result_id = uuid.uuid4()
    key_result = KeyResult(
        id=key_result_id,
        objective_id=objective_id,
        description=data.description,
        current_value=data.start_value,
        start_value=data.start_value,
        end_value=data.end_value,
    )

    # create new database entry for key result with parameters from URL
    db_session.add(key_result)
    await db_session.commit()

    return SuccessResponse("successfully created key result")


@patch(
    "/key_results/{key_result_id:str}",
    dto=KeyResultWriteUpdateDTO,
    return_dto=KeyResultReadDTO,
)
async def update_key_result(
    db_session: AsyncSession,
    # all project parameters are mandatory, so enforce they're not unset
    request: Request,
    data: KeyResult,
    key_result_id: str = Parameter(),
) -> KeyResult:
    """
    Update an key_result.

    param data: the update key result information to store
    param key_result_id: the ID of the key result to update
    return: the updated key result
    """

    key_result = await db_session.execute(
        select(KeyResult).where(KeyResult.id == key_result_id)
    )
    key_result = key_result.scalar_one_or_none()
    if key_result is None:
        raise NotFoundException("key result doesn't exist")

    if not await has_key_result_write_permissions(
        db_session, request.user, key_result_id
    ):
        raise PermissionDeniedException("no permissions to modify this key result")

    if not (
        check_value_within_bounds(data.current_value, data.start_value, data.end_value)
    ):
        raise ClientException("current value is out of bounds")

    key_result.description = data.description
    key_result.start_value = data.start_value
    key_result.current_value = data.current_value
    key_result.end_value = data.end_value

    # commit updated key result to database
    await db_session.commit()

    return key_result


@patch(
    "/key_results/{key_result_id:str}/current",
    dto=KeyResultCurrentValueUpdateDTO,
    return_dto=KeyResultReadDTO,
)
async def update_key_result_current_value(
    db_session: AsyncSession,
    request: Request,
    data: KeyResult,
    key_result_id: str = Parameter(),
) -> KeyResult:
    """
    Update the current_value of a key_result.

    param data: the new current value to store
    param key_result_id: the ID of the key result to update
    return: the key result with the updated current value
    """
    key_result = await db_session.execute(
        select(KeyResult).where(KeyResult.id == key_result_id)
    )
    key_result = key_result.scalar_one_or_none()
    if not key_result:
        raise NotFoundException("key result doesn't exist")

    if not await has_key_result_write_permissions(
        db_session, request.user, key_result_id
    ):
        raise PermissionDeniedException("no permissions to modify this key result")

    if not (
        check_value_within_bounds(
            data.current_value, key_result.start_value, key_result.end_value
        )
    ):
        raise ClientException("current value is out of bounds")

    key_result.current_value = data.current_value
    await db_session.commit()
    await db_session.refresh(key_result)
    return key_result


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


@post("/projects/{project_id:str}/objectives", dto=ObjectiveWriteDTO, return_dto=None)
async def create_objective(
    db_session: AsyncSession,
    request: Request,
    data: Objective,
    project_id: str = Parameter(),
) -> SuccessResponse:
    """
    Create a new objective.

    param data: the objective to create
    return: whether the objective was successfully created
    """
    if not project_id:
        raise ClientException("invalid id")
    # check if the project id exists
    project = await db_session.get(Project, project_id)
    if project is None:
        raise NotFoundException("Project doesn't exist")

    if not await has_weak_project_permissions(db_session, request.user, project_id):
        raise PermissionDeniedException(
            "no permissions to create an objective for this project"
        )

    # randomly generate a objective id
    objective_id = uuid.uuid4()
    objective = Objective(id=objective_id, name=data.name, description=data.description)

    # add the new objective to the project's list of objectives
    project.objectives.append(objective)

    # create new database entry for objective with parameters from URL
    db_session.add(objective)
    await db_session.commit()

    return SuccessResponse("successfully created objective")


@patch(
    "/objectives/{objective_id:str}", dto=ObjectiveWriteDTO, return_dto=ObjectiveReadDTO
)
async def update_objective(
    db_session: AsyncSession,
    # all project parameters are mandatory, so enforce they're not unset
    request: Request,
    data: Objective,
    objective_id: str = Parameter(),
) -> Objective:
    """
    Update an objective.

    param data: the update objective information to store
    param objective_id: the ID of the objective to update
    return: the updated objective
    """

    objective = await db_session.execute(
        select(Objective).where(Objective.id == objective_id)
    )
    objective = objective.scalar_one_or_none()
    if objective is None:
        raise NotFoundException("objective doesn't exist")

    if not await has_objective_write_permissions(
        db_session, request.user, objective_id
    ):
        raise PermissionDeniedException("no permissions to modify this objective")

    objective.name = data.name
    objective.description = data.description

    # commit updated objective to database
    await db_session.commit()

    return objective


@get("/projects/{project_id:str}/objectives", return_dto=ObjectiveReadDTO)
async def get_objectives_for_project(
    db_session: AsyncSession,
    project_id: str = Parameter(),
) -> list[Objective]:
    """ "
    Query objectives by project ID.

    param project_id: the ID of the project for which to retrieve objectives
    return: a JSON list of objectives related to the given project
    """

    return await project_utils.get_objectives_for_project(db_session, project_id)


@get("/objectives/{objective_id:str}/key_results", return_dto=KeyResultReadDTO)
async def get_key_results_for_objective(
    db_session: AsyncSession,
    objective_id: str = Parameter(),
) -> list[KeyResult]:
    """
    Query key results by objective ID.

    param objective_id: the ID of the objective for which to retrieve key results
    return: a JSON list of key results related to the given objective
    """

    return await project_utils.get_key_results_for_objective(
        db_session, uuid.UUID(objective_id)
    )


@get("/projects/{project_id:str}/users", return_dto=UserReadDTO)
async def get_users_for_project(
    db_session: AsyncSession,
    request: Request,
    project_id: str = Parameter(),
) -> list[User]:
    """
    Query users by project ID

    param project_id: the ID of the project for which to retrieve users
    return: a JSON list of users related to the given project
    """

    # retrieve all users related to the project
    users = await db_session.scalars(
        select(User)
        .join(UserProject)
        .where(
            UserProject.project_id == project_id,
        )
    )

    return list(users)


@post("/projects/{project_id:str}/users/{user_id:str}")
async def add_user_to_project(
    db_session: AsyncSession,
    request: Request,
    project_id: str = Parameter(),
    user_id: str = Parameter(),
    role: UserRole = Parameter(),
) -> SuccessResponse:
    """
    Add a user with a role to a project.

    param project_id: ID of the project
    param user_id: ID of the user
    role: role of the user in the project
    return: whether the user was successfully assigned to the project with a role
    """

    # check if user exists
    user = await db_session.get(User, user_id)
    if not user:
        raise NotFoundException("User not found")

    # check if project exists
    project = await db_session.get(Project, project_id)
    if not project:
        raise NotFoundException("Project not found")

    # permissions:
    # - admin can add anyone with any project role
    # - leader can add members and leaders in projects they lead

    if not await has_project_lead_permissions(
        db_session, request.user, project_id=project_id
    ):
        raise PermissionDeniedException()

    # check if user already in project
    already_in_project = await db_session.scalar(
        select(
            exists().where(
                and_(
                    UserProject.user_id == user_id, UserProject.project_id == project_id
                )
            )
        )
    )
    if already_in_project:
        raise ClientException(
            status_code=409, detail="User already assigned to this project"
        )

    # create new entry
    user_project = UserProject(project_id=project_id, user_id=user_id, role=role)

    # add the project+role the the users list of userprojects
    user.projects.append(user_project)

    await db_session.commit()

    return SuccessResponse(
        message=f"User {user.name} added to project {project.name} with role {role}"
    )


@delete("/projects/{project_id:str}/users/{user_id:str}")
async def remove_user_from_project(
    db_session: AsyncSession,
    project_id: str = Parameter(),
    user_id: str = Parameter(),
) -> None:
    """
    Remove a user from a project.

    param project_id: the ID of the project
    param user_id: the ID of the user
    """

    # check if project exists
    project = await db_session.get(Project, project_id)
    if not project:
        raise NotFoundException("Project not found")

    # check if user exists
    user = await db_session.get(User, user_id)
    if not user:
        raise NotFoundException("User not found")

    # load the UserProject entry (association row)
    stmt = select(UserProject).where(
        and_(
            UserProject.project_id == project_id,
            UserProject.user_id == user_id,
        )
    )
    result = await db_session.execute(stmt)
    user_project = result.scalars().one_or_none()

    if user_project is None:
        raise NotFoundException("User is not assigned to this project")

    # remove the relation
    await db_session.delete(user_project)
    await db_session.commit()


@post("/projects/{project_id:str}/objectives/{objective_id:str}")
async def add_objective_to_project(
    db_session: AsyncSession,
    request: Request,
    project_id: str = Parameter(),
    objective_id: str = Parameter(),
) -> SuccessResponse:
    """
    Add an objective to a project

    param project_id: the ID of the project
    param objective_id: the ID of the objective
    """

    # check if project exists
    project = await db_session.get(Project, project_id)
    if not project:
        raise NotFoundException("Project not found")

    # check if objective exists
    objective = await db_session.get(Objective, objective_id)
    if not objective:
        raise NotFoundException("Objective not found")

    if not has_weak_project_permissions(db_session, request.user, project_id):
        raise PermissionDeniedException(
            "no permissions to modify linked objectives for this project"
        )

    # link the objective to the project (if already linked nothing happens)
    if objective not in project.objectives:
        project.objectives.append(objective)

    # if the project was archived, the objective archive status won't be changed, so only this one check is necessary
    if not project.is_archived:
        await project_utils.unarchive_objective_including_children(
            db_session, [objective]
        )

    await db_session.commit()

    return SuccessResponse(
        message=f"Objective {objective.name} successfully linked with project {project.name}"
    )


@delete("/projects/{project_id:str}/objectives/{objective_id:str}")
async def remove_objective_from_project(
    db_session: AsyncSession,
    request: Request,
    project_id: str = Parameter(),
    objective_id: str = Parameter(),
    confirm_orphan: bool = Parameter(default=False, query="confirm_orphan"),
) -> None:
    """
    Remove an objective from a project

    param project_id: the ID of the project
    param objective_id: the ID of the objective
    param confirm_orphan: if true, allows unlinking even if this is the last project associated  with the objective
    """

    # check if project exists
    project = await db_session.get(Project, project_id)
    if not project:
        raise NotFoundException("Project not found")

    # check if objective exists
    objective = await db_session.get(Objective, objective_id)
    if not objective:
        raise NotFoundException("Objective not found")

    if not has_weak_project_permissions(db_session, request.user, project_id):
        raise PermissionDeniedException(
            "no permissions to modify linked objectives for this project"
        )

    # check if unlinking would remove last project link
    if not confirm_orphan:
        stmt = (
            select(func.count())
            .select_from(project_objective)
            .where(project_objective.c.objective_id == objective_id)
        )

        link_count: int = await db_session.scalar(stmt) or 0

        # if objective currently only has 1 link and confirm_orphan not set -> Warning
        if link_count == 1:
            raise ClientException(
                status_code=409,
                detail="Unlink would remove last project for objective. Set confirm_orphan=true to proceed.",
            )

    if objective in project.objectives:
        project.objectives.remove(objective)

    await project_utils.archive_objective_including_children(db_session, [objective])

    await db_session.commit()


@patch("/projects/{project_id:str}/users/{user_id:str}/role")
async def change_user_role(
    db_session: AsyncSession,
    request: Request,
    project_id: str = Parameter(),
    user_id: str = Parameter(),
    role: UserRole = Parameter(),
) -> SuccessResponse:
    """
    Changes the role of a user in a project

    param project_id: the ID of the project
    param user_id: the ID of the user
    param role: the new role that will be changed into
    return: whether the role was successfully changed
    """
    actor = cast(User, request.user)

    # check if project exists
    project = await db_session.get(Project, project_id)
    if not project:
        raise NotFoundException("Project not found")

    # check if user exists
    user = await db_session.get(User, user_id)
    if not user:
        raise NotFoundException("User not found")

    # load the UserProject-entry
    stmt = select(UserProject).where(
        UserProject.project_id == project_id, UserProject.user_id == user_id
    )
    result = await db_session.execute(stmt)
    user_project = result.scalars().one_or_none()

    if not user_project:
        raise NotFoundException("User is not assigned to this project")

    # permissions:
    # admin: everything
    # teamlead: only member -> teamlead (no demotions)
    if not actor.is_admin:
        if not await has_project_lead_permissions(
            db_session, actor, project_id=project_id
        ):
            raise PermissionDeniedException()

        # teamlead restrictions
        if user.is_admin:
            raise PermissionDeniedException()

        # teamlead can only set role to TEAMLEAD (promotion)
        if role != UserRole.LEADER:
            raise PermissionDeniedException()

        # allow no-op: leader -> leader
        if user_project.role == UserRole.LEADER:
            return SuccessResponse("Role successfully updated")

    # change the role
    user_project.role = role

    await db_session.commit()

    return SuccessResponse("Role successfully updated")


@get("/projects/{project_id:str}/users/{user_id:str}/role")
async def get_user_role(
    db_session: AsyncSession, project_id: str = Parameter(), user_id: str = Parameter()
) -> UserRoleResponse:
    """
    Gets the role for a user in a project

    param project_id: the ID of the project
    param user_id: the ID of the user
    return: the role of the user in the project
    """
    # check if project exists
    role = await get_user_role_for_project(db_session, project_id, user_id)
    if not role:
        raise NotFoundException("User is not part of the project")

    return UserRoleResponse(role)


@post("/objectives/{parent_objective_id:str}/children/{objective_id:str}")
async def add_objective_to_objective(
    db_session: AsyncSession,
    request: Request,
    parent_objective_id: str = Parameter(),
    objective_id: str = Parameter(),
) -> SuccessResponse:
    """
    Ling a child objective to a parent objective

    param parent_objective_id: the ID of the parent objective
    objective_id: the ID of the child objective
    """
    parent = await db_session.get(Objective, parent_objective_id)
    child = await db_session.get(Objective, objective_id)

    if not parent or not child:
        raise NotFoundException("Objective not found")

    if not has_objective_write_permissions(
        db_session, request.user, parent_objective_id
    ):
        raise PermissionDeniedException(
            "no permissions to add child objectives to this parent objective"
        )

    current = parent
    while current.parent_id is not None:
        if current.parent_id == child.id:
            raise ClientException(
                status_code=400,
                detail="Linking these objectives would create a cyclical relationship",
            )

        current = await db_session.get(Objective, current.parent_id)
        if current is None:
            break

    # check if parent objective = objective
    if objective_id == parent_objective_id:
        raise ClientException(
            status_code=400,
            detail="The objectives are the same",
        )

    if child.parent_id != parent_objective_id:
        child.parent_id = parent_objective_id
        await db_session.flush()

    if not parent.is_archived:
        await project_utils.unarchive_objective_including_children(db_session, [child])
    else:
        await project_utils.archive_objective_including_children(db_session, [child])

    await db_session.commit()

    return SuccessResponse("Objective linked successfully")


@delete("/objectives/{parent_objective_id:str}/children/{objective_id:str}")
async def remove_objective_from_objective(
    db_session: AsyncSession,
    request: Request,
    parent_objective_id: str = Parameter(),
    objective_id: str = Parameter(),
) -> None:
    """
    Remove a child objective from a parent objective

    param parent_objective_id: the ID of the parent objective
    objective_id: the ID of the child objective
    """

    parent = await db_session.get(Objective, parent_objective_id)
    child = await db_session.get(Objective, objective_id)

    if not parent or not child:
        raise NotFoundException("Objective not found")

    if not has_objective_write_permissions(
        db_session, request.user, parent_objective_id
    ):
        raise PermissionDeniedException(
            "no permissions to remove child objectives from this parent objective"
        )

    if child.parent_id != parent.id:
        raise ClientException(
            "The given parent is not the actual parent of this objective"
        )

    child.parent_id = None

    # check if child need to be change archive status after losing parent
    await project_utils.archive_objective_including_children(db_session, [child])

    await db_session.commit()


@patch("projects/{project_id:str}/archive")
async def archive_project(
    db_session: AsyncSession,
    project_id: str = Parameter(),
    archive_reason: ArchiveReason = Parameter(),
) -> SuccessResponse:
    """
    Archives a project

    param project_id: the ID of the project
    param archive_reason: the reason for archiving
    """

    # check if project exists
    project = await db_session.get(Project, project_id)
    if not project:
        raise NotFoundException("Project not found")

    project.is_archived = True
    project.archive_reason = archive_reason

    # check if associated objectives and their children need to be archived
    objectives = await project_utils.get_objectives_for_project(db_session, project_id)
    await project_utils.archive_objective_including_children(db_session, objectives)

    await db_session.commit()

    return SuccessResponse(message=f"Project {project.name} is archived")


@patch("projects/{project_id:str}/unarchive")
async def unarchive_project(
    db_session: AsyncSession,
    project_id: str = Parameter(),
    new_deadline: datetime = Parameter(),
) -> SuccessResponse:
    """
    Unarchives a project

    param project_id: the ID of the project
    param archive_reason: the reason for archiving
    """

    # check if project exists
    project = await db_session.get(Project, project_id)
    if not project:
        raise NotFoundException("Project not found")

    project.is_archived = False
    project.archive_reason = None
    await project_utils.change_project_deadline(db_session, project_id, new_deadline)

    # unarchive all linked objectives and their children
    objectives = await project_utils.get_objectives_for_project(db_session, project_id)
    await project_utils.unarchive_objective_including_children(db_session, objectives)

    await db_session.commit()

    return SuccessResponse(message=f"Project {project.name} is unarchived")


@get("/projects/archived", return_dto=ProjectReadDTO)
async def get_archived_projects(db_session: AsyncSession) -> list[Project]:
    """
    Returns a list of all archived projects
    """
    stmt = select(Project).where(Project.is_archived.is_(True))
    result = await db_session.execute(stmt)
    return result.scalars().all()


@get("/objectives/archived", return_dto=ObjectiveReadDTO)
async def get_archived_objectives(db_session: AsyncSession) -> list[Objective]:
    """
    Returns a list of all archived projects
    """
    stmt = select(Objective).where(Objective.is_archived.is_(True))
    result = await db_session.execute(stmt)
    return result.scalars().all()


@get("/key_results/archived", return_dto=KeyResultReadDTO)
async def get_archived_key_results(db_session: AsyncSession) -> list[KeyResult]:
    """
    KeyResults are archived if their parent Objective is archived
    """
    stmt = (
        select(KeyResult)
        .join(Objective, KeyResult.objective_id == Objective.id)
        .where(Objective.is_archived.is_(True))
    )
    result = await db_session.execute(stmt)
    return result.scalars().all()


@get("/tasks/archived", return_dto=TaskReadDTO)
async def get_archived_tasks(db_session: AsyncSession) -> list[Task]:
    """
    Tasks are archived if their KeyResult's parent Objective is archived
    """
    stmt = (
        select(Task)
        .join(KeyResult, Task.key_result_id == KeyResult.id)
        .join(Objective, KeyResult.objective_id == Objective.id)
        .where(Objective.is_archived.is_(True))
    )
    result = await db_session.execute(stmt)
    return result.scalars().all()


@patch("/projects/{project_id:str}/deadline/extend")
async def change_project_deadline(
    db_session: AsyncSession,
    project_id: str = Parameter(),
    new_deadline: datetime = Parameter(),
) -> SuccessResponse:
    """
    Extends the project deadline

    param project_id: the ID of the project
    param new_deadline: the new deadline of the project
    """

    return await project_utils.change_project_deadline(
        db_session, project_id, new_deadline
    )


@get("/objectives/{parent_id:str}/children", return_dto=ObjectiveReadDTO)
async def get_objective_children(
    db_session: AsyncSession, parent_id: str = Parameter()
) -> list[Objective]:
    """
    Returns all the children of an objective

    param parent_id: the ID of the parent objective
    """
    stmt = select(Objective).where(Objective.parent_id == parent_id)
    result = await db_session.execute(stmt)
    return result.scalars().all()


# during test execution, data is written into memory and not
# into the actual persistent database file!
is_pytest_active = "PYTEST_VERSION" in os.environ
database_url = (
    "sqlite+aiosqlite:///:memory:" if is_pytest_active else config.database_url
)
# Create a session config that is linked to an SQLite database.
session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string=database_url,
    session_config=session_config,
    create_all=True,
)

cors_config = CORSConfig(
    allow_origins=config.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# requires user to provide a valid auth token
authenticated_router = Router(
    path="/",
    route_handlers=[
        get_me,
        get_dashboard,
        get_project_permissions,
        get_objective_permissions,
        get_key_result_permissions,
        get_task_permissions,
        get_projects,
        get_project,
        create_project,
        update_project,
        get_objectives,
        get_objective,
        create_objective,
        update_objective,
        get_key_results,
        get_key_result,
        create_key_result,
        update_key_result,
        update_key_result_current_value,
        get_users,
        get_tasks,
        get_task,
        get_tasks_from_key_result,
        create_task_for_key_result,
        update_task,
        get_objectives_for_project,
        get_key_results_for_objective,
        get_users_for_project,
        add_user_to_project,
        remove_user_from_project,
        add_objective_to_project,
        remove_objective_from_project,
        change_user_role,
        get_user_role,
        add_objective_to_objective,
        remove_objective_from_objective,
        change_password,
        reset_password,
        totp_setup,
        totp_confirm,
        totp_disable,
        totp_is_configured,
        delete_project,
        delete_objective,
        delete_key_result,
        delete_task,
        archive_project,
        unarchive_project,
        get_archived_projects,
        get_archived_objectives,
        change_project_deadline,
        delete_user,
        logout,
        webauthn_register,
        webauthn_get_registration_options,
        webauthn_remove_credentials,
        webauthn_is_configured,
        create_user,
        promote_user_to_admin,
        get_projects_for_user_id,
        get_objective_children,
        get_archived_key_results,
        get_archived_tasks,
    ],
    middleware=[AuthenticationMiddleware],
    tags=["authenticated"],
    security=[{"ApiKeyAuth": []}],
)

# can be accessed without login
public_router = Router(
    path="/",
    route_handlers=[
        main_page,
        login_handler,
        webauthn_authenticate,
        webauthn_get_authentication_options,
    ],
    tags=["public"],
)


async def create_admin_user(app: Litestar):
    """
    Create the admin user configured in the `config` file.

    If a user with the given admin username already exists, no admin user is created.
    """
    sqlalchemy_plugin = app.plugins.get(SQLAlchemyPlugin)
    db_config = sqlalchemy_plugin.config[0]
    session_maker = db_config.create_session_maker()
    async with session_maker() as db_session:
        admin_exists = await db_session.scalar(
            select(exists(User).where(User.name == config.admin.username))
        )

        if not admin_exists:
            user_id = uuid.uuid4()
            user = User(
                id=user_id,
                name=config.admin.username,
                email=config.admin.email,
                password_hash=config.admin.password_hash,
                two_fa_secret="",
                is_admin=True,
            )

            db_session.add(user)
            await db_session.commit()


# Run the web app
app = Litestar(
    debug=True,
    route_handlers=[public_router, authenticated_router],
    plugins=[SQLAlchemyPlugin(config=sqlalchemy_config)],
    openapi_config=OpenAPIConfig(
        title="OKR-Tool",
        version="0.1.0",
        path="/docs",
        render_plugins=[ScalarRenderPlugin()],
        tags=[
            Tag(
                name="public",
                description="This endpoint is for use without authentication",
            ),
            Tag(
                name="authenticated",
                description="This endpoint is for authenticated users",
            ),
        ],
        components=Components(
            security_schemes={
                "ApiKeyAuth": SecurityScheme(
                    type="apiKey", security_scheme_in="header", name="Authorization"
                )
            },
        ),
    ),
    cors_config=cors_config,
    on_startup=[create_admin_user],
)
