from dataclasses import dataclass
from litestar.plugins.sqlalchemy import base
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
    #Primary Key
    id: Mapped[UUID]
    #Description of the Task
    description: Mapped[str]
    # Status: for example "open", "planned", "in_progress", "done" or "cancelled"
    state: Mapped[TaskState] = mapped_column(
    SAEnum(TaskState, name="task_state")
    )
    #Key Result connection
    key_result_id: Mapped[UUID] = mapped_column(ForeignKey("key_results.id", ondelete="CASCADE"))