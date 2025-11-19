from dataclasses import dataclass
from litestar.plugins.sqlalchemy import base
from sqlalchemy.orm import Mapped
from uuid import UUID


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
