from dataclasses import dataclass
from litestar.plugins.sqlalchemy import base
from sqlalchemy.orm import Mapped, relationship, mapped_column
from sqlalchemy import ForeignKey
from uuid import UUID


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
    project_id: Mapped[str]

    # foreign key to parent Objective
    parent_id: Mapped[UUID | None] = mapped_column(
        ForeignKey("objectives.id", ondelete="SET NULL"),
        nullable=True
        )
    
    # 1:N relationship with Objective children
    children: Mapped[list["Objective"]] = relationship(
        "Objective",
        cascade="all, delete-orphan",
        lazy="selectin"
    )

   
