from dataclasses import dataclass
from advanced_alchemy.extensions.litestar import base
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy import ForeignKey
from uuid import UUID
from models.key_result import KeyResult


@dataclass
class Objective(base.UUIDBase):
    """
    Data model of an OKR objective.
    """

    __tablename__ = "objectives"
    # primary key
    id: Mapped[UUID] = mapped_column(primary_key=True)
    # Table columns/attributes
    name: Mapped[str]
    description: Mapped[str]
    is_archived: Mapped[bool] = mapped_column(default=False, nullable=False)

    # foreign key to parent Objective
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("objectives.id", ondelete="SET NULL"), nullable=True
    )

    # 1-> N relationship with Objective children
    children: Mapped[list["Objective"]] = relationship("Objective", lazy="selectin")

    # 1 -> N Objective -> KeyResult
    key_results: Mapped[list["KeyResult"]] = relationship(
        "KeyResult", cascade="all, delete-orphan", lazy="selectin"
    )
