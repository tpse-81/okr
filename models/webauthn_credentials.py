from uuid import UUID
from sqlalchemy import ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from advanced_alchemy.extensions.litestar import base


class WebauthnCredentials(base.DefaultBase):
    """
    Database container for storing Webauthn credentials.

    The values and their definitions are listed at https://duo-labs.github.io/py_webauthn/registration.html.
    """

    __tablename__ = "webauthn_credentials"

    credential_id: Mapped[str] = mapped_column(primary_key=True)
    credential_public_key: Mapped[str]
    sign_count: Mapped[int]
    credential_device_type: Mapped[str]
    credential_backed_up: Mapped[bool]
    credential_transports: Mapped[str]

    # Reference to parent
    user_id: Mapped[UUID | None] = mapped_column(ForeignKey("users.id"))
    user = relationship("User", back_populates="webauthn")
