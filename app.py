from pathlib import Path
from litestar import Litestar, get
from litestar.response import File
from litestar.params import Parameter

from models.project import Project

from sqlalchemy import ForeignKey, func, select
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Mapped, mapped_column, relationship
from litestar.plugins.sqlalchemy import AsyncSessionConfig, SQLAlchemyAsyncConfig, SQLAlchemyPlugin, base

import uuid


@get("/hello")
async def hello_world(db_session: AsyncSession, db_engine: AsyncEngine) -> dict[str, str]:
    """
    Prints hello world.

    return: a JSON object
    """
    return {"hello": "world"}


@get("/", media_type="text/html")
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


@get("/create")
async def create_project(
    db_session: AsyncSession,
    db_engine: AsyncEngine,
    name: str | None = Parameter(default=None),
    deadline: int | None = Parameter(default=None),
    creation_date: int | None = Parameter(default=None),
) -> dict[str, str]:
    """
    Create a new project.

    param name: the name of the project to create
    param deadline: the deadline as UNIX timestamp
    param creation_date: the creation_date as UNIX timestamp
    return: whether the project was successfully created
    """

    # all project parameters are mandatory, so enforce they're not unset
    if name is None or deadline is None or creation_date is None:
        return {"message": "Failed to create project"}

    # randomly generate a project id
    project_id = uuid.uuid4()
    project = Project(id=project_id, name=name, deadline=deadline, creation_date=creation_date)

    # create new database entry for project with parameters from URL
    db_session.add(project)
    await db_session.commit()

    return {"message": "Project created"}


@get("/images/{filename:str}")
async def serve_images(filename: str) -> File:
    """
    Serve the static image for the given filename

    returns: the binary file as byte stream
    """
    return File(
        path=Path("images") / filename,
    )


# Create a session config that is linked to an SQLite database.
session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", session_config=session_config, create_all=True
)

# Run the web app
app = Litestar(
    route_handlers=[hello_world, main_page, serve_images, get_projects, create_project],
    debug=True,
    plugins=[SQLAlchemyPlugin(config=sqlalchemy_config)],
)
