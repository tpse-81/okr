from dataclasses import dataclass
from pathlib import Path
from litestar import Litestar, get
from litestar.response import File
from litestar.params import Parameter
from litestar.static_files import create_static_files_router

#Importieren der Databases
from models.project import Project
from models.user import User

from sqlalchemy import ForeignKey, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from litestar.plugins.sqlalchemy import AsyncSessionConfig, SQLAlchemyAsyncConfig, SQLAlchemyPlugin, base

from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin

import uuid


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
async def get_projects(db_session: AsyncSession, db_engine: AsyncEngine) -> list[Project]:
    """
    Get the list of projects.

    return: a JSON list of projects
    """
    return list(await db_session.scalars(select(Project)))


@get("/projects/create")
async def create_project(
    db_session: AsyncSession,
    db_engine: AsyncEngine,
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
async def get_users(db_session: AsyncSession, db_engine: AsyncEngine) -> list[User]:
    """
    Get the list of users.

    return: a JSON list of users
    """
    return list(await db_session.scalars(select(User)))

@get("/users/create")
async def create_users(
    db_session: AsyncSession,
    db_engine: AsyncEngine,
    # all project parameters are mandatory, so enfore they are not unset 
    name: str = Parameter(),
    email: str = Parameter(),
    nextcloud_token: str = Parameter(),
) -> SuccessResponse:
    """
    Create a new user.

    param name: user's name
    param email: user's email
    param nextcloud_token: token for Nextcloud access
    return: whether the user was successfully created
    """
    #randomly generate a user_id 
    user_id = uuid.uuid4()
    user = User(id=user_id, name=name, email=email, nextcloud_token=nextcloud_token)

    db_session.add(user)
    await db_session.commit()

    return SuccessResponse("successfully created user")


# Create a session config that is linked to an SQLite database.
session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", session_config=session_config, create_all=True
)

# Run the web app
app = Litestar(
    route_handlers=[
        hello_world,
        main_page,
        get_projects,
        create_project,
        get_users,
        create_users,
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
