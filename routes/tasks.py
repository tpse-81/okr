from project_utils import (
    has_key_result_write_permissions,
    has_task_write_permissions,
)

from litestar import get, patch, post, delete
from litestar.params import Parameter
from litestar.exceptions import (
    NotFoundException,
    PermissionDeniedException,
)
from litestar.connection import Request

# Importing the database models

from dto.write_dto import (
    TaskWriteDTO,
)
from models.task import Task
from models.key_result import KeyResult
from models.project import Project
from models.user_project import UserProject
from models.project_objective import project_objective
from models.objective import Objective


from dto.read_dto import (
    TaskReadDTO,
)

import project_utils

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import uuid

from responses import SuccessResponse


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

    if not await project_utils.key_result_exists(db_session, key_result_id):
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


@get("/users/{user_id:str}/tasks", return_dto=TaskReadDTO)
async def get_tasks_for_user(
    db_session: AsyncSession,
    user_id: str = Parameter(),
) -> list[Task]:
    """
    Get all tasks for a given user.

    Tasks are retrieved by traversing the chain:
    UserProject -> Project -> project_objective -> Objective -> KeyResult -> Task

    param user_id: the ID of the user whose tasks are returned
    return: a JSON list of tasks belonging to projects the user participates in
    """
    stmt = (
        select(Task)
        .join(KeyResult, Task.key_result_id == KeyResult.id)
        .join(Objective, KeyResult.objective_id == Objective.id)
        .join(project_objective, project_objective.c.objective_id == Objective.id)
        .join(Project, project_objective.c.project_id == Project.id)
        .join(UserProject, UserProject.project_id == Project.id)
        .where(UserProject.user_id == user_id)
        .distinct()
    )

    result = await db_session.execute(stmt)
    return list(result.scalars().all())


@get("/tasks", return_dto=TaskReadDTO)
async def get_tasks(db_session: AsyncSession) -> list[Task]:
    """
    param key_result_id: the UUID of the key result whose tasks should be returned

    Gets the list of task for a given key result

    """

    result = await db_session.scalars(select(Task))
    return list(result)


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
    return list(result.scalars().all())


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
