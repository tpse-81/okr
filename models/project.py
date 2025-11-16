from dataclasses import dataclass
from litestar.plugins.sqlalchemy import base
from sqlalchemy.orm import Mapped
from uuid import UUID


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
