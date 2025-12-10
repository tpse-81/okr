from sqlalchemy import Column, ForeignKey, Table
from advanced_alchemy.base import orm_registry


user_task = Table(
    """
    Association table for linking users and tasks (many-to-many relationship)
    where the combination of user_id and task_id is unique
    """

    "user_task",
    orm_registry.metadata,

    # column users_id contains the UUID of the project
    Column("user_id", ForeignKey("users.id", ondelete="CASCADE"), primary_key=True),

    # column task_id contains the UUID of the objective
    Column("task_id", ForeignKey("tasks.id", ondelete="CASCADE"), primary_key=True)
)