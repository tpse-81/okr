from dataclasses import dataclass
from litestar.plugins.sqlalchemy import base
from sqlalchemy.orm import Mapped, relationship
from uuid import UUID
from models.user_project import UserProject


@dataclass
class User(base.UUIDBase):
    """
    Data model of an OKR user.
    """

    __tablename__ = "users"
    # primary key
    id: Mapped[UUID]
    # Table columns/attributes
    name: Mapped[str]
    email: Mapped[str]
    password_hash: Mapped[str]
    two_fa_secret: Mapped[str]

    # N->N relationship with Project
    projects: Mapped[list["UserProject"]] = relationship(
        "UserProject",
        cascade="all, delete-orphan",
        lazy="selectin"
    )
