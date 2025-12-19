from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from responses import SuccessResponse

from litestar.params import Parameter
from litestar.exceptions import NotFoundException

from models.project import Project
from models.objective import Objective
from models.project_objective import project_objective


async def get_objectives_for_project(
    db_session: AsyncSession, project_id: str
) -> list[Objective]:
    """
    Fetch all objectives for a given project ID

    param project_id: the ID of the project
    return: list of Objective objects linked to the project
    """

    stmt = (
        select(Objective)
        .join(project_objective)
        .where(project_objective.c.project_id == project_id)
        .options(
            selectinload(Objective.children)
        )  # eagerly load all Objective children
    )
    result = await db_session.execute(stmt)
    return result.scalars().all()  # list of all Objectives


async def change_project_deadline(
    db_session: AsyncSession,
    project_id: str = Parameter(),
    new_deadline: int = Parameter(),
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
