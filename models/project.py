from dataclasses import dataclass
from litestar.plugins.sqlalchemy import base
from sqlalchemy.orm import Mapped, relationship
from uuid import UUID
from models.objective import Objective
from models.project_objective import project_objective


@dataclass
class Project(base.UUIDBase):
    """
    Data model of an OKR project.
    """

    __tablename__ = "projects"
    # primary key
    id: Mapped[UUID]
    # Table columns/attributes
    name: Mapped[str]
    creation_date: Mapped[int]
    deadline: Mapped[int]
    # Many-to-many relationship with Objective
    objectives: Mapped[list["Objective"]] = relationship(
        secondary=project_objective,
        back_populates="projects",
        lazy="selectin"
    )
