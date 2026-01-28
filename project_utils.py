from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, exists

from responses import SuccessResponse

from litestar.params import Parameter
from litestar.exceptions import NotFoundException

from models.project import Project
from models.objective import Objective
from models.project_objective import project_objective

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
    project_id: str = Parameter(),
    new_deadline: datetime = Parameter(),
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
