from project_utils import (
    has_weak_project_permissions,
    has_objective_write_permissions,
)

from litestar import get, patch, post, delete
from litestar.params import Parameter
from litestar.exceptions import (
    ClientException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.connection import Request

# Importing the database models

from dto.write_dto import (
    ObjectiveWriteDTO,
)
from models.project import Project
from models.objective import Objective


from dto.read_dto import (
    ObjectiveReadDTO,
)

import project_utils

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload


import uuid

from responses import SuccessResponse


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


@get("/objectives/archived", return_dto=ObjectiveReadDTO)
async def get_archived_objectives(db_session: AsyncSession) -> list[Objective]:
    """
    Returns a list of all archived projects
    """
    stmt = select(Objective).where(Objective.is_archived.is_(True))
    result = await db_session.execute(stmt)
    return result.scalars().all()


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
