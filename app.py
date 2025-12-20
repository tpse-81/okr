from dataclasses import dataclass
from litestar import Litestar, get, patch, post, delete
from litestar.openapi.spec import Components, SecurityScheme, Tag
from litestar.params import Parameter
from litestar.router import Router
from litestar.static_files import create_static_files_router
from litestar.exceptions import ClientException, NotFoundException
from litestar.config.cors import CORSConfig

# Importing the database models
from authentication import (
    AuthenticationMiddleware,
    generate_twofa_secret,
    hash_password,
    login_handler,
    change_password,
    get_new_token,
)
from dto.write_dto import (
    KeyResultWriteDTO,
    ObjectiveWriteDTO,
    ProjectWriteDTO,
    TaskWriteDTO,
)
from models.project import Project
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

from sqlalchemy import select, exists, and_
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import selectinload
from advanced_alchemy.extensions.litestar import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
)


from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin

import uuid

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


@get("/hello")
async def hello_world(
    db_session: AsyncSession, db_engine: AsyncEngine
) -> dict[str, str]:
    """
    Prints hello world.

    return: a JSON object
    """
    return {"hello": "world"}


@get("/", media_type="text/html", include_in_schema=False)
async def main_page() -> str:
    """
    Renders the main HTML page.

    return: a raw HTML string
    """
    with open("main.html", "r") as f:
        return f.read()


@get("/projects", return_dto=ProjectReadDTO)
async def get_projects(db_session: AsyncSession) -> list[Project]:
    """
    Get the list of projects.

    return: a JSON list of projects
    """
    return list(await db_session.scalars(select(Project)))


@get("/key_results", return_dto=KeyResultReadDTO)
async def get_key_results(db_session: AsyncSession) -> list[KeyResult]:
    """
    Get the list of key results.

    return: a JSON list of key results
    """
    return list(await db_session.scalars(select(KeyResult)))


@post("/key_results/{key_result_id:str}/delete")
async def delete_key_result(
    db_session: AsyncSession,
    key_result_id: str
) -> SuccessResponse:
    """
    Delete a key result and all its tasks

    param key_result_id: the ID of the key result to delete
    """
    key_result = await db_session.get(KeyResult, key_result_id)
    if key_result is None:
        raise NotFoundException("Key result not found")
    
    await db_session.delete(key_result)
    await db_session.commit()

    return SuccessResponse("Key result deleted successfully")


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


@post("/objectives/{objective_id:str}/delete")
async def delete_objective(
    db_session: AsyncSession,
    objective_id: str
) -> SuccessResponse:
    """
    Delete an objective and all its Key results and tasks

    param objective_id: the ID of the objective to delete
    """
    objective = await db_session.get(Objective, objective_id)
    if objective is None:
        raise NotFoundException("objective not found")
    
    await db_session.delete(objective)
    await db_session.commit()

    return SuccessResponse("objective deleted successfully")


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


@post("/tasks/{task_id:str}/delete")
async def delete_task(
    db_session: AsyncSession,
    task_id: str
) -> SuccessResponse:
    """
    Delete a single task

    param task_id: the ID of the task to delete
    """
    task = await db_session.get(Task, task_id)
    if task is None:
        raise NotFoundException("objective not found")
    
    await db_session.delete(task)
    await db_session.commit()

    return SuccessResponse("task deleted successfully")


@post("/key_results/{key_result_id:str}/tasks", dto=TaskWriteDTO, return_dto=None)
async def create_task_for_key_result(
    db_session: AsyncSession,
    data: Task,
    key_result_id: str = Parameter(),
) -> SuccessResponse:
    """
    Create a new task for a given key result.

    param key_result_id: the ID of the key result this task belongs to
    param description: the description of the key result
    param task_state: the state of the task can be ONLY one of the following: open", "planned", "in_progress", "done" or "cancelled"
    """

    # randomly generate a task id
    task_id = uuid.uuid4()

    task = Task(
        id=task_id,
        description=data.description,
        task_state=data.task_state,
        key_result_id=key_result_id,
    )

    # create new database entry for key result with parameters
    db_session.add(task)
    await db_session.commit()

    return SuccessResponse("successfully created task")


@post("/projects", dto=ProjectWriteDTO, return_dto=None)
async def create_project(
    db_session: AsyncSession,
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
        creation_date=data.creation_date,
        done=data.done,
    )

    # create new database entry for project with parameters from URL
    db_session.add(project)
    await db_session.commit()

    return SuccessResponse("successfully created project")


@post("/projects/{project_id:str}/delete")
async def delete_project(
    db_session: AsyncSession,
    project_id: str,
) -> SuccessResponse:
    """
    Delete a project and automatically delete all objectives
    that are not linked to any other project.

    param project_id: the ID of the project to delete
    """

    project = await db_session.get(Project, project_id)
    if project is None:
        raise NotFoundException("Project not found")
    
    objectives_for_project = await db_session.scalars(
        select(Objective)
        .join(project_objective)
        .where(project_objective.c.project_id == project_id)
    )
    objectives_for_project = list(objectives_for_project)

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
    
    await db_session.delete(project)
    await db_session.commit()

    return SuccessResponse("project deleted successfully")


@get("/users", return_dto=UserReadDTO)
async def get_users(db_session: AsyncSession) -> list[User]:
    """
    Get the list of users (without password hash and 2FA).

    return: a JSON list of users
    """
    return list(await db_session.scalars(select(User)))


@dataclass
class CreateUserRequest:
    name: str
    email: str
    password: str


# TODO: replace with path "/users" once this route is part of the authentication router group
@post("/users/create")
async def create_user(
    db_session: AsyncSession, data: CreateUserRequest
) -> SuccessResponse:
    """
    Create a new user.

    param data: the user data to create a new user from
    return: whether the user was successfully created
    """
    # randomly generate a user_id
    user_id = uuid.uuid4()
    password_hash = hash_password(data.password)
    two_fa_secret = generate_twofa_secret()
    user = User(
        id=user_id,
        name=data.name,
        email=data.email,
        password_hash=password_hash,
        two_fa_secret=two_fa_secret,
    )

    db_session.add(user)
    await db_session.commit()

    return SuccessResponse("successfully created user")


@post("/key_results", dto=KeyResultWriteDTO, return_dto=None)
async def create_key_result(
    db_session: AsyncSession,
    # all parameters are mandatory, so enforce they're not unset
    data: KeyResult,
) -> SuccessResponse:
    """
    Create a new key result.

    param data: the key result to create
    return: a JSON object containing a success message
    """
    if not data.objective_id:
        raise ClientException("invalid objective id")

    if not await objective_exists(db_session, data.objective_id):
        raise NotFoundException("Objective doesn't exist")

    # randomly generate a key_result id
    key_result_id = uuid.uuid4()
    key_result = KeyResult(
        id=key_result_id,
        objective_id=data.objective_id,
        description=data.description,
        start_value=data.start_value,
        end_value=data.end_value,
    )

    # create new database entry for key result with parameters from URL
    db_session.add(key_result)
    await db_session.commit()

    return SuccessResponse("successfully created key result")


@post("/projects/{project_id:str}/objectives", dto=ObjectiveWriteDTO, return_dto=None)
async def create_objective(
    db_session: AsyncSession, data: Objective, project_id: str = Parameter()
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

    # randomly generate a objective id
    objective_id = uuid.uuid4()
    objective = Objective(id=objective_id, name=data.name, description=data.description)

    # add the new objective to the project's list of objectives
    project.objectives.append(objective)

    # create new database entry for objective with parameters from URL
    db_session.add(objective)
    await db_session.commit()

    return SuccessResponse("successfully created objective")


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

    stmt = (
        select(Objective)
        .join(project_objective)
        .where(project_objective.c.project_id == project_id)
        .options(
            selectinload(Objective.children)
        )  # eagerly load all Objective children
    )
    result = await db_session.execute(stmt)
    objectives = result.scalars().all()  # list of all Objectives

    return list(objectives)


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

    # retrieve all key results related to the objective
    key_results = await db_session.scalars(
        select(KeyResult).where(KeyResult.objective_id == objective_id)
    )

    return list(key_results)


@get("/projects/{project_id:str}/users", return_dto=UserReadDTO)
async def get_users_for_project(
    db_session: AsyncSession,
    project_id: str = Parameter(),
) -> list[User]:
    """
    Query users by project ID

    param project_id: the ID of the project for which to retrieve users
    return: a JSON list of users related to the given project
    """

    # retrieve all users related to the project
    users = await db_session.scalars(
        select(User).join(UserProject).where(UserProject.project_id == project_id)
    )

    return list(users)


@post("/projects/{project_id:str}/users/{user_id:str}")
async def add_user_to_project(
    db_session: AsyncSession,
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
        raise NotFoundException("User already assigned to this project")

    # create new entry
    user_project = UserProject(project_id=project_id, user_id=user_id, role=role)

    # add the project+role the the users list of userprojects
    user.projects.append(user_project)

    await db_session.commit()

    return SuccessResponse(
        message=f"User {user.name} added to project {project.name} with role {role}"
    )


@post("projects/{project_id:str}/objectives/{objective_id:str}")
async def add_objective_to_project(
    db_session: AsyncSession,
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

    # link the objective to the project (if already linked nothing happens)
    if objective not in project.objectives:
        project.objectives.append(objective)

    await db_session.commit()

    return SuccessResponse(
        message=f"Objective {objective.name} successfully linked with project {project.name}"
    )


@patch("/projects/{project_id:str}/users/{user_id:str}/role")
async def change_user_role(
    db_session: AsyncSession,
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
    role = await db_session.scalar(stmt)
    if not role:
        raise NotFoundException("User is not part of the project")

    return UserRoleResponse(role)


@post("/objectives/{parent_objective_id:str}/children/{objective_id:str}")
async def add_objective_to_objective(
    db_session: AsyncSession,
    parent_objective_id: str = Parameter(),
    objective_id: str = Parameter(),
) -> SuccessResponse:
    parent = await db_session.get(Objective, parent_objective_id)
    child = await db_session.get(Objective, objective_id)

    if not parent or not child:
        raise NotFoundException("Objective not found")

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
        await db_session.commit()

    return SuccessResponse("Objective linked successfully")


# Create a session config that is linked to an SQLite database.
session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///:memory:",
    session_config=session_config,
    create_all=True,
)

cors_config = CORSConfig(allow_origins=["*"])
# requires user to provide a valid auth token
authenticated_router = Router(
    path="/",
    route_handlers=[
        get_projects,
        create_project,
        get_objectives,
        create_objective,
        get_key_results,
        create_key_result,
        get_users,
        get_tasks_from_key_result,
        create_task_for_key_result,
        get_objectives_for_project,
        get_key_results_for_objective,
        get_users_for_project,
        add_user_to_project,
        add_objective_to_project,
        change_user_role,
        get_user_role,
        add_objective_to_objective,
        change_password,
        get_new_token,
        delete_project,
        delete_objective,
        delete_key_result,
        delete_task,  
    ],
    middleware=[AuthenticationMiddleware],
    tags=["authenticated"],
    security=[{"ApiKeyAuth": []}],
)

# can be accessed without login
public_router = Router(
    path="/",
    route_handlers=[
        hello_world,
        main_page,
        login_handler,
        # make all files in the images folder available under the /images/{filename} path
        create_static_files_router(path="/images", directories=["images"]),
        # TODO: creating users should not be possible without authentication!
        create_user,
    ],
    tags=["public"],
)

# Run the web app
app = Litestar(
    route_handlers=[public_router, authenticated_router],
    debug=True,
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
)
