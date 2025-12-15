from litestar.dto import DTOConfig
from advanced_alchemy.extensions.litestar import SQLAlchemyDTO

from models.project import Project
from models.objective import Objective
from models.key_result import KeyResult
from models.task import Task
from models.user import User


class ProjectWriteDTO(SQLAlchemyDTO[Project]):
    """
    DTO used for serializing Project models for write operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(exclude={"id", "objectives"})


class ObjectiveWriteDTO(SQLAlchemyDTO[Objective]):
    """
    DTO used for serializing Objective models for write operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(exclude={"id", "parent_id", "children"})


class KeyResultWriteDTO(SQLAlchemyDTO[KeyResult]):
    """
    DTO used for serializing KeyResult models for write operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(exclude={"id", "objective"})


class TaskWriteDTO(SQLAlchemyDTO[Task]):
    """
    DTO used for serializing Task models for write operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(exclude={"id", "key_result_id"})


class UserWriteDTO(SQLAlchemyDTO[User]):
    """
    DTO used for serializing User models for write operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(
        exclude={"id", "password_hash", "two_fa_secret", "projects", "tasks"}
    )
