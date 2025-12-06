from litestar.dto import DTOConfig
from advanced_alchemy.extensions.litestar import SQLAlchemyDTO

from models.project import Project
from models.objective import Objective
from models.key_result import KeyResult
from models.task import Task
from models.user import User


class ProjectReadDTO(SQLAlchemyDTO[Project]):
    """
    DTO used for serializing Project models for read operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(exclude={"objectives"})


class ObjectiveReadDTO(SQLAlchemyDTO[Objective]):
    """
    DTO used for serializing Objective models for read operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(exclude={"parent_id", "children"})


class KeyResultReadDTO(SQLAlchemyDTO[KeyResult]):
    """
    DTO used for serializing KeyResult models for read operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(exclude={"objective_id", "objective"})


class TaskReadDTO(SQLAlchemyDTO[Task]):
    """
    DTO used for serializing Task models for read operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(exclude={"key_result_id"})


class UserReadDTO(SQLAlchemyDTO[User]):
    """
    DTO used for serializing User models for read operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(exclude={"password_hash", "two_fa_secret", "projects", "tasks"})
