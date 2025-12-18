from dataclasses import dataclass
from advanced_alchemy.extensions.litestar import base
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy import ForeignKey
from uuid import UUID


@dataclass
class Objective(base.UUIDBase):
    __tablename__ = "objectives"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    name: Mapped[str]
    description: Mapped[str]

    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("objectives.id", ondelete="SET NULL"), nullable=True
    )

    # parent relationship (one parent)
    parent: Mapped["Objective | None"] = relationship(
        "Objective",
        back_populates="children",
        remote_side="Objective.id",
    )

    # children relationship (one‑to‑many children)
    children: Mapped[list["Objective"]] = relationship(
        "Objective",
        back_populates="parent",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
