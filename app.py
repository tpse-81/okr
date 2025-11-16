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

session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string="sqlite+aiosqlite:///test.sqlite", session_config=session_config, create_all=True
)  # Create 'async_session' dependency.

async def on_startup(app: Litestar) -> None:
    # async with sqlalchemy_config.get_session() as session:
    #     statement = select(func.count()).select_from(Project)
    #     count = await session.execute(statement)


@get("/")
async def hello_world(db_session: AsyncSession, db_engine: AsyncEngine) -> dict[str, str]:
    """
        Prints hello world.

        return: a JSON object
    """
    return {"hello": "world"}


@get("/peter", media_type="text/html")
async def hello_peter() -> str:
    with open("main.html", "r") as f:
        # return {"name": "peter"}
        return f.read()


@get("/projects")
async def get_projects(db_session: AsyncSession, db_engine: AsyncEngine) -> list[Project]:
    return list(await db_session.scalars(select(Project)))


@get("/create")
async def create_project(
    db_session: AsyncSession,
    db_engine: AsyncEngine,
    name: str | None = Parameter(default=None),
    deadline: int | None = Parameter(default=None),
    creation_date: int | None = Parameter(default=None),
) -> str:
    if name is None or deadline is None or creation_date is None:
        return "Fehlerhafte Anfrage"

    # randomly generate a project id
    project_id = uuid.uuid4()
    project = Project(id=project_id, name=name, deadline=deadline, creation_date=creation_date)

    # create new database entry for project with parameters from URL
    db_session.add(project)

    await db_session.commit()

    return "Projekt erstellt"


@get("/images/{filename:str}")
async def serve_image(filename: str) -> File:
    return File(
        path=Path("images") / filename,
    )


app = Litestar(
    route_handlers=[hello_world, hello_peter, serve_image, get_projects, create_project],
    on_startup=[on_startup],
    debug=True,
    plugins=[SQLAlchemyPlugin(config=sqlalchemy_config)],
)
