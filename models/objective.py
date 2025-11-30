from dataclasses import dataclass
from litestar.plugins.sqlalchemy import base
from sqlalchemy.orm import Mapped, relationship
from uuid import UUID
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from models.project import Project
from models.project_objective import project_objective


@dataclass
class Objective(base.UUIDBase):
    """
    Data model of an OKR objective.
    """

    __tablename__ = "objectives"
    # primary key
    id: Mapped[UUID]
    # Table columns/attributes
    name: Mapped[str]
    description: Mapped[str]
    project_id: Mapped[str]
    # Many-to-many relationship with Project
    projects: Mapped[list["Project"]] = relationship(
        secondary=project_objective,
        back_populates="objectives",
        lazy="selectin"
    )
