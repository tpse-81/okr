from dataclasses import dataclass
from litestar.plugins.sqlalchemy import base
from sqlalchemy.orm import Mapped
from uuid import UUID


@dataclass
class KeyResult(base.UUIDBase):
    """
    Data model of an OKR key result.
    """

    __tablename__ = "key_results"
    # primary key
    id: Mapped[UUID]
    # Table columns/attributes
    objective_id: Mapped[str]
    description: Mapped[str]
    start_value: Mapped[float]
    end_value: Mapped[float]
