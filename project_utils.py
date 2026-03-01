from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists

from responses import SuccessResponse

from litestar.exceptions import NotFoundException, ClientException

from models.project import Project
from models.objective import Objective
from models.key_result import KeyResult
from models.user import User
from models.user_project import UserProject, UserRole
from models.project_objective import project_objective
from models.task import Task

from collections import deque

from datetime import datetime


async def get_objectives_for_project(
    db_session: AsyncSession, project_id: str
) -> list[Objective]:
    """
    Fetch all objectives for a given project ID

    param project_id: the ID of the project
    return: list of Objective objects linked to the project
    """

    stmt = await db_session.scalars(
        select(Objective)
        .join(project_objective)
        .where(project_objective.c.project_id == project_id)
    )

    return list(stmt)  # list of all Objectives


async def change_project_deadline(
    db_session: AsyncSession,
    project_id: str,
    new_deadline: datetime,
) -> SuccessResponse:
    """
    Extends the project deadline

    param project_id: the ID of the project
    param new_deadline: the new deadline of the project
    """

    # check if project exists
    project = await db_session.get(Project, project_id)
    if not project:
        raise NotFoundException("Project not found")

    project.deadline = new_deadline

    await db_session.commit()

    return SuccessResponse(message=f"Deadline of {project.name} was extended")


async def archive_objective_including_children(
    db_session: AsyncSession,
    objectives: list[Objective],
) -> None:
    """
    Checks if objectives should be archived after changes to a project they belong to.
    Also checks their children objectives recursively and checks if they need to be archived

    param objectives: list of Objective objects
    """

    queue = deque(objectives)
    visited: set[str] = set()

    while queue:
        objective = queue.popleft()

        # to avoid cycles / duplication
        if str(objective.id) in visited:
            continue

        # force parent objectives to be handled first
        if objective.parent_id is not None:
            parent = await db_session.get(Objective, objective.parent_id)

            # if parent hasn't been checked yet, put it ahead and restart the loop
            if parent is not None and str(parent.id) not in visited:
                queue.appendleft(objective)
                queue.appendleft(parent)
                continue

        visited.add(str(objective.id))

        await db_session.refresh(objective, attribute_names=["children"])

        # parent override: if parent exists and is not archived, then child must stay unarchived
        if objective.parent_id is not None:
            if parent and not parent.is_archived:
                objective.is_archived = False
                for child in objective.children:
                    queue.append(child)
                continue

        # check if any unarchived project is linked
        active_project_exists = await db_session.scalar(
            select(
                exists().where(
                    project_objective.c.objective_id == objective.id,
                    project_objective.c.project_id == Project.id,
                    Project.is_archived.is_(False),
                )
            )
        )

        if not active_project_exists:
            objective.is_archived = True

        # after the objective gets archived, we have to look at its children (and recursively all children of them as well)
        for child in objective.children:
            queue.append(child)


async def unarchive_objective_including_children(
    db_session: AsyncSession,
    objectives: list[Objective],
) -> None:
    """
    Unarchives all objectives, after changes to a project they belong to.
    Also unarchives all their children recursively.

    param objectives: list of Objective objects
    """

    queue = deque(objectives)
    visited: set[str] = set()

    while queue:
        objective = queue.popleft()

        # to avoid cycles / duplication
        if str(objective.id) in visited:
            continue
        visited.add(str(objective.id))

        objective.is_archived = False

        await db_session.refresh(objective, attribute_names=["children"])
        # after the objective gets unarchived, we have to look at its children (and recursively all children of them as well)
        for child in objective.children:
            queue.append(child)


async def get_key_results_for_objective(
    db_session: AsyncSession,
    objective_id: UUID,
) -> list[KeyResult]:
    """
    Get all key results for a given objective ID.

    param objective_id: the ID of the objective for which to retrieve key results
    return: a list of key results related to the given objective
    """

    # retrieve all key results related to the objective
    key_results = await db_session.scalars(
        select(KeyResult).where(KeyResult.objective_id == objective_id)
    )

    return list(key_results)


async def get_projects_for_user(
    db_session: AsyncSession, user_id: UUID
) -> list[Project]:
    """
    Get all projects for the given user.

    param user_id: the id of the user to filter for
    return: a list of all projects where the current user is participating
    """
    stmt = select(Project).join(UserProject).where(UserProject.user_id == user_id)
    result = await db_session.execute(stmt)
    return list(result.scalars().all())


async def calculate_objective_progress(
    db_session: AsyncSession, objective_id: UUID
) -> float:
    """
    Calculate the progress for an objective by averaging the progress of its key results.

    param objective_id: the ID of the objective to build the progress for
    return: the progress as float, between 0 and 1
    """
    key_results = await get_key_results_for_objective(db_session, objective_id)
    if not key_results:
        return 1.0

    # build average over all key results
    total = sum(calculate_key_result_progress(key_result) for key_result in key_results)
    return total / len(key_results)


def calculate_key_result_progress(key_result: KeyResult) -> float:
    """
    Calculate the progress for a key result.

    param key_result: the key result to build the progress for
    return: the progress as float, between 0 and 1
    """
    diff_target = abs(key_result.end_value - key_result.start_value)
    diff_current = abs(key_result.current_value - key_result.start_value)

    # prevent division by zero by defaulting to a progress of 1 (done)
    if diff_target == 0:
        return 1
    return float(diff_current) / float(diff_target)


def check_value_within_bounds(value, a, b):
    low = min(a, b)
    high = max(a, b)

    return low <= value <= high


async def get_user_role_for_project(
    db_session: AsyncSession, project_id: str, user_id: str
) -> UserRole | None:
    """
    Gets the role for a user in a project

    param project_id: the ID of the project
    param user_id: the ID of the user
    return: the role of the user in the project
    """
    # check if project exists
    project = await db_session.get(Project, project_id)
    if not project:
        raise NotFoundException("Project not found")

    # check if user exists
    user = await db_session.get(User, user_id)
    if not user:
        raise NotFoundException("User not found")

    stmt = select(UserProject.role).where(
        UserProject.user_id == user_id, UserProject.project_id == project_id
    )
    return await db_session.scalar(stmt)


async def has_project_lead_permissions(
    db_session: AsyncSession, user: User, project_id: str
) -> bool:
    """Return True if the current user may act as project leader for this project."""
    if user.is_admin:
        return True

    actor_role = await get_user_role_for_project(
        db_session, project_id=project_id, user_id=str(user.id)
    )
    return actor_role == UserRole.LEADER


async def has_weak_project_permissions(
    db_session: AsyncSession, user: User, project_id: str
) -> bool:
    """Return True if the current user has permissions to do low-impact actions on the project.

    E.g., such low-impact actions would be creating, updating, deleting objectives and key result ...
    For permissions to modify projects, see `has_project_lead_permissions` instead.
    """
    if user.is_admin:
        return True

    actor_role = await get_user_role_for_project(
        db_session, project_id=project_id, user_id=str(user.id)
    )
    return actor_role is not None


async def has_objective_write_permissions(
    db_session: AsyncSession, user: User, objective_id: str
) -> bool:
    """
    Check whether a user has permissions for modifying this objective.

    That's true if the user participates in any project that is related to this objective.
    """
    current_objective_id = objective_id

    # recursively go over the current objective and all its parent objectives
    while current_objective_id is not None:
        current_objective = await db_session.get(Objective, current_objective_id)

        # this case should never happen, i.e. that means that a parent objective no longer exists
        # if that's the case, we just ignore the error here because that means we found the root parent
        # object, so there's no chance that the user has write permissions anyways
        if current_objective is None:
            return False

        projects_stmt = (
            select(Project)
            .join(project_objective)
            .where(project_objective.c.objective_id == current_objective_id)
        )
        related_projects = await db_session.scalars(projects_stmt)

        # check if the user participates in any of the projects linked to the objective
        for project in related_projects:
            if await has_weak_project_permissions(db_session, user, str(project.id)):
                return True

        # continue to search for write permissions in parent objective
        current_objective_id = current_objective.parent_id

    return False


async def has_key_result_write_permissions(
    db_session: AsyncSession, user: User, key_result_id: str
) -> bool:
    """
    Check whether a user has permissions for modifying this key result.

    That's true if the user participates in any project that is related to this key result.
    """
    key_result = await db_session.get(KeyResult, key_result_id)
    if key_result is None:
        raise ClientException("key result does not exist")

    return await has_objective_write_permissions(
        db_session, user, key_result.objective_id
    )


async def has_task_write_permissions(
    db_session: AsyncSession, user: User, task_id: str
) -> bool:
    """
    Check whether a user has permissions for modifying this task.

    That's true if the user participates in any project that is related to this task.
    """
    task = await db_session.get(Task, task_id)
    if task is None:
        raise ClientException("task does not exist")

    return await has_key_result_write_permissions(db_session, user, task.key_result_id)


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
