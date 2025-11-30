from dataclasses import dataclass
from litestar import Litestar, get
from litestar.params import Parameter
from litestar.static_files import create_static_files_router
from litestar.exceptions import NotFoundException

# Importing the database models
from models.project import Project
from models.objective import Objective
from models.key_result import KeyResult
from models.user import User
from models.task import Task
from models.task import TaskState

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from litestar.plugins.sqlalchemy import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
)

from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin

import uuid
from typing import Any

# Import for password and hashing
import hashlib
import secrets


async def project_exists(db_session: AsyncSession, project_id: str) -> bool:
    result = await db_session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    return project is not None


# Maybe use bycrypt or argon
def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def generate_twofa_secret() -> str:
    """
    generates a random 2FA Token
    """
    return secrets.token_hex(16)


@dataclass
class SuccessResponse:
    message: str

    def __init__(self, message: str) -> None:
        self.message = message


@get("/hello")
async def hello_world(db_session: AsyncSession, db_engine: AsyncEngine) -> dict[str, str]:
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


@get("/projects")
async def get_projects(db_session: AsyncSession) -> list[Project]:
    """
    Get the list of projects.

    return: a JSON list of projects
    """
    return list(await db_session.scalars(select(Project)))


@get("/key_results")
async def get_key_results(db_session: AsyncSession) -> list[KeyResult]:
    """
    Get the list of key results.

    return: a JSON list of key results
    """
    return list(await db_session.scalars(select(KeyResult)))


@get("/objectives")
async def get_objectives(db_session: AsyncSession) -> list[Objective]:
    """
    Get the list of Objectives.

    return: a JSON list of objectives
    """
    return list(await db_session.scalars(select(Objective)))


@get("/key_results/{key_result_id:uuid}/tasks")
async def get_tasks_from_key_result(
    key_result_id: uuid, db_session: AsyncSession, db_engine: AsyncEngine
) -> list[Task]:
    """
    param key_result_id: the UUID of the key result whose tasks should be returned

    Gets the list of task for a given key result

    """

    result = await db_session.scalars(select(Task).where(Task.key_result_id == key_result_id))
    return list(result)



@get("/key_results/{key_result_id:uuid}/tasks/create")
async def create_task_for_key_result(
    key_result_id: uuid.UUID,
    db_session: AsyncSession,
    description: str = Parameter(),
    task_state: TaskState = Parameter(default=TaskState.OPEN),
) -> SuccessResponse:
    """
    Create a new task for a given key result.

    param key_result_id: the ID of the key result this task belongs to
    param description: the description of the key result
    param task_state: the state of the task can be ONLY one of the following: open", "planned", "in_progress", "done" or "cancelled"
    """

    # randomly generate a task id
    task_id = uuid.uuid4()

    task = Task(id=task_id, description=description, task_state=task_state, key_result_id=key_result_id)

    # create new database entry for key result with parameters
    db_session.add(task)
    await db_session.commit()

    return SuccessResponse("successfully created task")


@get("/projects/create")
async def create_project(
    db_session: AsyncSession,
    # all project parameters are mandatory, so enforce they're not unset
    name: str = Parameter(),
    deadline: int = Parameter(),
    creation_date: int = Parameter(),
) -> SuccessResponse:
    """
    Create a new project.

    param name: the name of the project to create
    param deadline: the deadline as UNIX timestamp
    param creation_date: the creation_date as UNIX timestamp
    return: whether the project was successfully created
    """

    # randomly generate a project id
    project_id = uuid.uuid4()
    project = Project(id=project_id, name=name, deadline=deadline, creation_date=creation_date)

    # create new database entry for project with parameters from URL
    db_session.add(project)
    await db_session.commit()

    return SuccessResponse("successfully created project")


@get("/users")
async def get_users(db_session: AsyncSession) -> list[dict[str, Any]]:
    """
    Get the list of users (without password hash and 2FA).

    return: a JSON list of users
    """
    users = list(await db_session.scalars(select(User)))
    return [
        {
            "id": str(user.id),
            "name": user.name,
            "email": user.email,
        }
        for user in users
    ]


@get("/users/create")
async def create_users(
    db_session: AsyncSession,
    db_engine: AsyncEngine,
    # all project parameters are mandatory, so enfore they are not unset
    name: str = Parameter(),
    email: str = Parameter(),
    password: str = Parameter(),
) -> SuccessResponse:
    """
    Create a new user.

    param name: user's name
    param email: user's email
    param password: users plain text password, will be stored in hash
    return: whether the user was successfully created
    """
    # randomly generate a user_id
    user_id = uuid.uuid4()
    password_hash = hash_password(password)
    two_fa_secret = generate_twofa_secret()
    user = User(
        id=user_id,
        name=name,
        email=email,
        password_hash=password_hash,
        two_fa_secret=two_fa_secret,
    )

    db_session.add(user)
    await db_session.commit()

    return SuccessResponse("successfully created user")


@get("/key_results/create")
async def create_key_result(
    db_session: AsyncSession,
    # all parameters are mandatory, so enforce they're not unset
    objective_id: str = Parameter(),
    description: str = Parameter(),
    start_value: float = Parameter(),
    end_value: float = Parameter(),
) -> SuccessResponse:
    """
    Create a new key result.

    param project_id: the ID of the project this key result belongs to
    param objective_id: the ID of the objective this key result belongs to
    param description: the description of the key result
    param start_value: the current value at the start of the OKR
    param end_value: the end value that is the goal of the key result
    """

    # randomly generate a key_result id
    key_result_id = uuid.uuid4()
    key_result = KeyResult(
        id=key_result_id,
        objective_id=objective_id,
        description=description,
        start_value=start_value,
        end_value=end_value,
    )

    # create new database entry for key result with parameters from URL
    db_session.add(key_result)
    await db_session.commit()

    return SuccessResponse("successfully created key result")


@get("/objectives/create")
async def create_objective(
    db_session: AsyncSession,
    # all project parameters are mandatory, so enforce they're not unset
    name: str = Parameter(),
    description: str = Parameter(),
    project_id: str = Parameter(),
) -> SuccessResponse:
    """
    Create a new objective.

    param name: the name of the objective to create
    param description: the description of the objective
    param project_id: the ID of the related project
    return: whether the objective was successfully created
    """

    # check if the project id exists
    if not await project_exists(db_session, project_id):
        raise NotFoundException("Project doesn't exist")

    # randomly generate a objective id
    objective_id = uuid.uuid4()
    objective = Objective(id=objective_id, name=name, description=description, project_id=project_id)

    # create new database entry for objective with parameters from URL
    db_session.add(objective)
    await db_session.commit()

    return SuccessResponse("successfully created object")


# Create a session config that is linked to an SQLite database.
session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///:memory:",
    session_config=session_config,
    create_all=True,
)

# Run the web app
app = Litestar(
    route_handlers=[
        hello_world,
        main_page,
        get_projects,
        create_project,
        get_objectives,
        create_objective,
        get_key_results,
        create_key_result,
        get_users,
        create_users,
        get_tasks_from_key_result,
        create_task_for_key_result,
        # make all files in the images folder available under the /images/{filename} path
        create_static_files_router(path="/images", directories=["images"]),
    ],
    debug=True,
    plugins=[SQLAlchemyPlugin(config=sqlalchemy_config)],
    openapi_config=OpenAPIConfig(
        title="OKR-Tool",
        version="0.1.0",
        path="/docs",
        render_plugins=[ScalarRenderPlugin()],
    ),
)
