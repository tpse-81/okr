from typing import cast
from project_utils import (
    get_projects_for_user,
    get_user_role_for_project,
    has_project_lead_permissions,
    has_weak_project_permissions,
)
from datetime import datetime, timezone

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
    ProjectWriteDTO,
)
from models.project import Project, ArchiveReason
from models.objective import Objective
from models.user import User
from models.project_objective import project_objective
from models.user_project import UserProject, UserRole


from dto.read_dto import (
    ProjectReadDTO,
    UserReadDTO,
)

import project_utils

from sqlalchemy import select, exists, and_, func, delete as sa_delete
from sqlalchemy.ext.asyncio import AsyncSession

import uuid

from responses import SuccessResponse, UserRoleResponse


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


@get("/projects/archived", return_dto=ProjectReadDTO)
async def get_archived_projects(db_session: AsyncSession) -> list[Project]:
    """
    Returns a list of all archived projects
    """
    stmt = select(Project).where(Project.is_archived.is_(True))
    result = await db_session.execute(stmt)
    return result.scalars().all()


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
