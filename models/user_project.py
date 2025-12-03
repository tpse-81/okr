from dataclasses import dataclass
from litestar.plugins.sqlalchemy import base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID


@dataclass
class UserProject(base.UUIDBase):
    """
    Association table for linking users and projects (many-to-many relationship)
    with additional attribute 'role'
    """

    __tablename__ = "user_project"
    # primary key
    id: Mapped[UUID] = mapped_column(primary_key=True)
    # foreign keys
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), nullable=False)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), nullable=False)
    # user role attribute
    role: Mapped[str]

    

