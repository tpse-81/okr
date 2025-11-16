from dataclasses import dataclass
from litestar.plugins.sqlalchemy import base
from sqlalchemy.orm import Mapped
from uuid import UUID


@dataclass
class Project(base.UUIDBase):
    __tablename__ = "projects"
    id: Mapped[UUID]
    name: Mapped[str]
    creation_date: Mapped[int]
    deadline: Mapped[int]
