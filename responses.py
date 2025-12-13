from dataclasses import dataclass
from models.user_project import UserRole


@dataclass
class SuccessResponse:
    message: str

    def __init__(self, message: str) -> None:
        self.message = message


@dataclass
class UserRoleResponse:
    role: UserRole
