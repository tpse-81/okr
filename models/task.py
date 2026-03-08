from dataclasses import dataclass
from advanced_alchemy.extensions.litestar import base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from uuid import UUID
from enum import Enum
from sqlalchemy import Enum as SAEnum


class TaskState(str, Enum):
    OPEN = "open"
    PLANNED = "planned"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    CANCELLED = "cancelled"


@dataclass
class Task(base.UUIDBase):
    """
    Data model of a Task that belongs to a Key Result.


    """

    __tablename__ = "tasks"
    # Primary Key
    id: Mapped[UUID] = mapped_column(primary_key=True)
    # Short title of the task (like Objective.name)
    name: Mapped[str]
    # Longer description (like Objective.description)
    description: Mapped[str] = mapped_column(default="", nullable=False)
    # Status: for example "open", "planned", "in_progress", "done" or "cancelled"
    task_state: Mapped[TaskState] = mapped_column(SAEnum(TaskState, name="task_state"))
    # Key Result connection
    key_result_id: Mapped[str] = mapped_column(
        ForeignKey("key_results.id", ondelete="CASCADE"), nullable=False
    )

    # methods required for using this in a `set`, see the `/dashboard` method
    def __eq__(self, other) -> bool:
        if not isinstance(other, Task):
            return False

        return self.id == other.id

    def __hash__(self) -> int:
        return hash(self.id)
