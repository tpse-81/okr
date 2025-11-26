from dataclasses import dataclass
from litestar import Litestar, get
from litestar.params import Parameter
from litestar.static_files import create_static_files_router
from litestar.exceptions import NotFoundException

from models.project import Project
from models.objective import Objective
from models.key_result import KeyResult

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


async def project_exists(db_session: AsyncSession, project_id: str) -> bool:
    result = await db_session.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    return project is not None


@dataclass
class SuccessResponse:
    message: str

    def __init__(self, message: str) -> None:
        self.message = message


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
    project = Project(
        id=project_id, name=name, deadline=deadline, creation_date=creation_date
    )

    # create new database entry for project with parameters from URL
    db_session.add(project)
    await db_session.commit()

    return SuccessResponse("successfully created project")


@get("/key_results/create")
async def create_key_result(
    db_session: AsyncSession,
    db_engine: AsyncEngine,
    # all parameters are mandatory, so enforce they're not unset
    project_id: int = Parameter(),
    objective_id: int = Parameter(),
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
        project_id=project_id,
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
    objective = Objective(
        id=objective_id, name=name, description=description, project_id=project_id
    )

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
