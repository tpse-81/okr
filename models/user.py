from dataclasses import dataclass
from litestar.plugins.sqlalchemy import base
from sqlalchemy.orm import Mapped
from uuid import UUID


@dataclass
class User(base.UUIDBase):
    """
    Data model of an OKR user.
    """

    __tablename__ = "users"
    # primary key
    id: Mapped[UUID]
    # Table columns/attributes
    name: Mapped[str]
    email: Mapped[str]
    password_hash: Mapped[str]
    two_fa_secret: Mapped[str]
