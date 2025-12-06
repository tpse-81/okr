from dataclasses import dataclass
from advanced_alchemy.extensions.litestar import base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


@dataclass
class UserProject(base.UUIDBase):
    """
    Association table for linking users and projects (many-to-many relationship)
    with additional attribute 'role'
    """

    __tablename__ = "user_project"
    # foreign keys
    user_id: Mapped[str] = mapped_column(ForeignKey("users.id"), primary_key=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id"), primary_key=True)
    # user role attribute
    role: Mapped[str]
