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

    config = DTOConfig(
        exclude={"id", "creation_date", "is_archived", "archive_reason", "objectives"}
    )


class ObjectiveWriteDTO(SQLAlchemyDTO[Objective]):
    """
    DTO used for serializing Objective models for write operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(
        exclude={"id", "is_archived", "parent_id", "children", "key_results"}
    )


class KeyResultWriteDTO(SQLAlchemyDTO[KeyResult]):
    """
    DTO used for serializing KeyResult models for write operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(
        exclude={"id", "objective_id", "objective", "tasks", "current_value"}
    )


class KeyResultCurrentValueUpdateDTO(SQLAlchemyDTO[KeyResult]):
    """
    DTO used for updating only the current_value of a KeyResult
    """

    config = DTOConfig(
        exclude={
            "id",
            "objective_id",
            "objective",
            "tasks",
            "description",
            "start_value",
            "end_value",
        }
    )


class KeyResultWriteUpdateDTO(SQLAlchemyDTO[KeyResult]):
    """
    DTO used for serializing KeyResult models for write operations (limits output and prevents recursive relationships)
    """

    config = DTOConfig(exclude={"id", "objective_id", "objective", "tasks"})


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
