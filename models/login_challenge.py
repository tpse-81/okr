from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from advanced_alchemy.extensions.litestar import base
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column


@dataclass
class LoginChallenge(base.UUIDBase):
    """
    Data model for a pending 2FA login challenge (email one-time code).
    """
    __tablename__ = "login_challenges"

    id: Mapped[UUID] = mapped_column(primary_key=True)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)

    code_hash: Mapped[str]
    expires_at: Mapped[datetime] # stored as UTC (naive datetime)
    attempts: Mapped[int] = mapped_column(default=0)