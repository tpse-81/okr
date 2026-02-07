from dataclasses import dataclass
from advanced_alchemy.extensions.litestar import base
from sqlalchemy.orm import Mapped, relationship, mapped_column
from uuid import UUID
from models.user_project import UserProject
from models.task import Task
from models.user_task import user_task


@dataclass
class User(base.UUIDBase):
    """
    Data model of an OKR user.
    """

    __tablename__ = "users"
    # primary key
    id: Mapped[UUID] = mapped_column(primary_key=True)
    # Table columns/attributes
    name: Mapped[str] = mapped_column(nullable=False, unique=True)
    email: Mapped[str]
    password_hash: Mapped[str]
    two_fa_secret: Mapped[str]
    is_admin: Mapped[bool] = mapped_column(default=False, nullable=False)

    # N->N relationship with Project
    projects: Mapped[list["UserProject"]] = relationship(
        "UserProject", cascade="all, delete-orphan", lazy="selectin"
    )

    # N->N relationship with Task
    tasks: Mapped[list["Task"]] = relationship(
        "Task", secondary=user_task, lazy="selectin"
    )
