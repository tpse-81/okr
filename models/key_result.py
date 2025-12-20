from dataclasses import dataclass
from advanced_alchemy.extensions.litestar import base
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy import ForeignKey
from uuid import UUID
from models.objective import Objective


@dataclass
class KeyResult(base.UUIDBase):
    """
    Data model of an OKR key result.
    """

    __tablename__ = "key_results"
    # primary key
    id: Mapped[UUID] = mapped_column(primary_key=True)
    # Table columns/attributes
    objective_id: Mapped[str] = mapped_column(
        ForeignKey("objectives.id", ondelete="CASCADE"), nullable=False
    )
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id",ondelete="CASCADE"))
    description: Mapped[str]
    start_value: Mapped[float]
    end_value: Mapped[float]

    # N->1 relationship with Objective
    objective: Mapped["Objective"] = relationship("Objective", lazy="selectin")
