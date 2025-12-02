from dataclasses import dataclass


@dataclass
class SuccessResponse:
    message: str

    def __init__(self, message: str) -> None:
        self.message = message
