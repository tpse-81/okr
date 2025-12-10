from sqlalchemy import Column, ForeignKey, Table
from advanced_alchemy.base import orm_registry


project_objective = Table(
    """
    Association table for linking projects and objectives (many-to-many relationship)
    where the combination of project_id and objective_id is unique
    """
    "project_objective",
    orm_registry.metadata,
    # column project_id contains the UUID of the project
    Column(
        "project_id", ForeignKey("projects.id", ondelete="CASCADE"), primary_key=True
    ),
    # column objective_id contains the UUID of the objective
    Column(
        "objective_id",
        ForeignKey("objectives.id", ondelete="CASCADE"),
        primary_key=True,
    ),
)
