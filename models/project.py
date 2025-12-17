from dataclasses import dataclass
from datetime import datetime

from advanced_alchemy.extensions.litestar import base
from sqlalchemy.orm import Mapped, relationship, mapped_column
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
    id: Mapped[UUID] = mapped_column(primary_key=True)
    # Table columns/attributes
    name: Mapped[str]
    creation_date: Mapped[datetime]
    deadline: Mapped[datetime]
    archive_on: Mapped[bool] = mapped_column(
        default=False,
        nullable=False
    )

    # N->N relationship with Objective
    objectives: Mapped[list["Objective"]] = relationship(
        "Objective", secondary=project_objective, lazy="selectin"
    )

    done: Mapped[bool]

    # Base64-Encoded raw bytes of the image
    icon: Mapped[str | None]
