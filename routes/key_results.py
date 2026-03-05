from project_utils import (
    check_value_within_bounds,
    has_objective_write_permissions,
    has_key_result_write_permissions,
)

from litestar import get, patch, post, delete
from litestar.params import Parameter
from litestar.exceptions import (
    ClientException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.connection import Request

from dto.write_dto import (
    KeyResultWriteDTO,
    KeyResultWriteUpdateDTO,
    KeyResultCurrentValueUpdateDTO,
)
from models.key_result import KeyResult
from models.objective import Objective


from dto.read_dto import KeyResultReadDTO, ObjectiveReadDTO

import project_utils

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import uuid

from responses import SuccessResponse


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

    if not await project_utils.objective_exists(db_session, objective_id):
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


@get("/key_results/{key_result_id:str}/objective", return_dto=ObjectiveReadDTO)
async def get_related_objective_for_key_result(
    db_session: AsyncSession, key_result_id: str
) -> Objective:
    """
    Get the objective that belongs to the key result with the given ID.

    param key_result_id: the ID of the key result to search for
    """
    stmt = (
        select(Objective)
        .join(KeyResult, KeyResult.objective_id == Objective.id)
        .where(KeyResult.id == key_result_id)
    )
    objective = (await db_session.execute(stmt)).scalar_one_or_none()
    if objective is None:
        raise NotFoundException("key result or parent objective not found")

    return objective


@get("/key_results", return_dto=KeyResultReadDTO)
async def get_key_results(db_session: AsyncSession) -> list[KeyResult]:
    """
    Get the list of key results.

    return: a JSON list of key results
    """
    return list(await db_session.scalars(select(KeyResult)))


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
    return list(result.scalars().all())


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
