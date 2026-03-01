from typing import TypeVar, Generic
from project_utils import (
    calculate_objective_progress,
)
from webauthn_handlers import (
    webauthn_authenticate,
    webauthn_register,
    webauthn_get_authentication_options,
    webauthn_get_registration_options,
    webauthn_remove_credentials,
    webauthn_is_configured,
)
import os
from dataclasses import dataclass

from litestar import Litestar, get
from litestar.openapi.spec import Components, SecurityScheme, Tag
from litestar.params import Parameter
from litestar.router import Router
from litestar.config.cors import CORSConfig

# Importing the database models
from authentication import (
    AuthenticationMiddleware,
    login_handler,
    change_password,
    totp_setup,
    totp_confirm,
    totp_disable,
    totp_is_configured,
    logout,
    reset_password,
)

from routes.permissions import (
    get_project_permissions,
    get_objective_permissions,
    get_key_result_permissions,
    get_task_permissions,
)

from routes.users import (
    create_user,
    get_me,
    get_users,
    promote_user_to_admin,
    delete_user,
)

from routes.key_results import (
    create_key_result,
    get_key_result,
    get_key_results_for_objective,
    update_key_result,
    update_key_result_current_value,
    delete_key_result,
    get_key_results,
    get_archived_key_results,
)

from routes.objectives import (
    create_objective,
    get_objective,
    get_objectives,
    get_archived_objectives,
    get_objective_children,
    get_objectives_for_project,
    delete_objective,
    add_objective_to_objective,
    update_objective,
    remove_objective_from_objective,
)

from routes.tasks import (
    create_task_for_key_result,
    get_task,
    get_tasks,
    get_archived_tasks,
    get_tasks_from_key_result,
    update_task,
    delete_task,
    get_tasks_for_user,
)

from routes.projects import (
    create_project,
    get_project,
    get_projects,
    update_project,
    get_user_role,
    get_archived_projects,
    get_users_for_project,
    get_projects_for_user_id,
    get_projects_for_user,
    change_user_role,
    change_project_deadline,
    add_user_to_project,
    add_objective_to_project,
    remove_objective_from_project,
    remove_user_from_project,
    unarchive_project,
    archive_project,
    delete_project,
)

from models.project import Project
from models.user import User


from dto.read_dto import (
    ProjectReadDTO,
)

import project_utils

from sqlalchemy import select, exists
from sqlalchemy.ext.asyncio import AsyncSession
from advanced_alchemy.extensions.litestar import (
    AsyncSessionConfig,
    SQLAlchemyAsyncConfig,
    SQLAlchemyPlugin,
)

from litestar.openapi import OpenAPIConfig
from litestar.openapi.plugins import ScalarRenderPlugin

import uuid

from config import config


@get(["/", "/health", "/healthz"], include_in_schema=False)
async def main_page() -> str:
    """
    Renders a short status message if the app is running.

    return: a raw text string
    """
    return "OK"


# https://docs.litestar.dev/2/usage/dto/1-abstract-dto.html#wrapping-return-data
# https://github.com/orgs/litestar-org/discussions/3586
ProjectTypeVar = TypeVar("ProjectTypeVar")
ObjectiveTypeVar = TypeVar("ObjectiveTypeVar")


@dataclass
class ProjectContainer(Generic[ProjectTypeVar, ObjectiveTypeVar]):
    project: ProjectTypeVar
    objectives: list[ObjectiveTypeVar]
    progress: float


@get("/dashboard", return_dto=ProjectReadDTO)
async def get_dashboard(
    db_session: AsyncSession, user_id: str | None = Parameter()
) -> list[ProjectContainer]:
    if user_id:
        projects = await get_projects_for_user(db_session, uuid.UUID(user_id))
    else:
        projects: list[Project] = list(await db_session.scalars(select(Project)))

    projects = [p for p in projects if not p.is_archived]

    projects_with_info = []
    for project in projects:
        objectives = await project_utils.get_objectives_for_project(
            db_session, str(project.id)
        )

        # build average progress across all objectives
        progress_per_objective = [
            await calculate_objective_progress(db_session, objective.id)
            for objective in objectives
        ]

        if objectives:
            progress = sum(progress_per_objective) / len(objectives)
        else:
            progress = 1.0

        project_container = ProjectContainer(
            project=project,
            objectives=objectives,
            progress=progress,
        )
        projects_with_info.append(project_container)

    return projects_with_info


# during test execution, data is written into memory and not
# into the actual persistent database file!
is_pytest_active = "PYTEST_VERSION" in os.environ
database_url = (
    "sqlite+aiosqlite:///:memory:" if is_pytest_active else config.database_url
)
# Create a session config that is linked to an SQLite database.
session_config = AsyncSessionConfig(expire_on_commit=False)
sqlalchemy_config = SQLAlchemyAsyncConfig(
    connection_string=database_url,
    session_config=session_config,
    create_all=True,
)

cors_config = CORSConfig(
    allow_origins=config.cors_allow_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# requires user to provide a valid auth token
authenticated_router = Router(
    path="/",
    route_handlers=[
        create_user,
        get_me,
        get_dashboard,
        get_users,
        get_users_for_project,
        get_user_role,
        get_projects_for_user_id,
        delete_user,
        add_user_to_project,
        remove_user_from_project,
        change_user_role,
        change_password,
        reset_password,
        totp_setup,
        totp_confirm,
        totp_disable,
        totp_is_configured,
        logout,
        webauthn_register,
        webauthn_get_registration_options,
        webauthn_remove_credentials,
        webauthn_is_configured,
        promote_user_to_admin,
        create_project,
        get_projects,
        get_project,
        get_archived_projects,
        update_project,
        change_project_deadline,
        archive_project,
        unarchive_project,
        delete_project,
        get_objectives_for_project,
        add_objective_to_project,
        remove_objective_from_project,
        create_objective,
        get_objectives,
        get_objective,
        get_archived_objectives,
        get_objective_children,
        update_objective,
        delete_objective,
        add_objective_to_objective,
        remove_objective_from_objective,
        create_key_result,
        get_key_results,
        get_key_result,
        get_key_results_for_objective,
        update_key_result,
        update_key_result_current_value,
        delete_key_result,
        create_task_for_key_result,
        get_tasks,
        get_task,
        get_tasks_for_user,
        get_tasks_from_key_result,
        update_task,
        delete_task,
        get_project_permissions,
        get_objective_permissions,
        get_key_result_permissions,
        get_task_permissions,
        get_archived_tasks,
        get_archived_key_results,
    ],
    middleware=[AuthenticationMiddleware],
    tags=["authenticated"],
    security=[{"ApiKeyAuth": []}],
)

# can be accessed without login
public_router = Router(
    path="/",
    route_handlers=[
        main_page,
        login_handler,
        webauthn_authenticate,
        webauthn_get_authentication_options,
    ],
    tags=["public"],
)


async def create_admin_user(app: Litestar):
    """
    Create the admin user configured in the `config` file.

    If a user with the given admin username already exists, no admin user is created.
    """
    sqlalchemy_plugin = app.plugins.get(SQLAlchemyPlugin)
    db_config = sqlalchemy_plugin.config[0]
    session_maker = db_config.create_session_maker()
    async with session_maker() as db_session:
        admin_exists = await db_session.scalar(
            select(exists(User).where(User.name == config.admin.username))
        )

        if not admin_exists:
            user_id = uuid.uuid4()
            user = User(
                id=user_id,
                name=config.admin.username,
                email=config.admin.email,
                password_hash=config.admin.password_hash,
                two_fa_secret="",
                is_admin=True,
            )

            db_session.add(user)
            await db_session.commit()


# Run the web app
app = Litestar(
    debug=True,
    route_handlers=[public_router, authenticated_router],
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
    on_startup=[create_admin_user],
)
