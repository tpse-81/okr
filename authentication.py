from dataclasses import dataclass
from typing import Annotated, Any
import typing
import re
import pyotp

from argon2.exceptions import VerifyMismatchError
from litestar import Response, post, patch
from litestar.connection import ASGIConnection
from litestar.exceptions import (
    ClientException,
    NotAuthorizedException,
    NotFoundException,
)
from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult

import jwt
from argon2 import PasswordHasher
from datetime import datetime, timezone, timedelta

from litestar.params import Body, Parameter
from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from responses import SuccessResponse
from config import config
from config import TOTP_ISSUER, TOTP_PENDING_PREFIX, TOTP_VALID_WINDOW, _BASE32_RE

API_KEY_HEADER = "Authorization"
JWT_ALGORITHM = "HS256"

# TODO: make configurable!
JWT_SECRET = "secretfortesting"
# how long tokens are valid. If the time has passed, users are automatically getting logged out
JWT_VALIDITY_DURATION_HOURS = 7 * 24  # 1 week


def _normalize_totp_code(code: str | None) -> str | None:
    """
    Normalize user-entered TOTP codes.

    Users often type codes with spaces or hyphens (e.g. "123 456" or "123-456").
    We strip whitespace and hyphens so verification works with these inputs.
    """
    if not code:
        return None
    return re.sub(r"[\s-]", "", code) or None


def _parse_totp_secret(raw: str | None) -> tuple[str | None, bool]:
    """
    Parse a stored TOTP secret value.

    Returns (secret, pending).
    - secret is normalized to upper-case base32 (or None if invalid / missing)
    - pending indicates whether the secret is still in "pending:" state
    """
    if not raw:
        return None, False
    pending = raw.startswith(TOTP_PENDING_PREFIX)
    secret = raw[len(TOTP_PENDING_PREFIX) :] if pending else raw
    secret = secret.replace(" ", "").upper()
    if not _BASE32_RE.fullmatch(secret):
        return None, pending
    return secret, pending


def verify_totp(secret: str, code: str) -> bool:
    return pyotp.TOTP(secret).verify(code, valid_window=TOTP_VALID_WINDOW)


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, user_email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(name=user_email, issuer_name=TOTP_ISSUER)


@dataclass
class JwtUser:
    id: str
    name: str
    email: str


class AuthenticationMiddleware(AbstractAuthenticationMiddleware):
    """
    Middleware that checks if the user has provided a valid jwt auth key as the 'Authentication' HTTP header.
    """

    async def authenticate_request(
        self, connection: ASGIConnection
    ) -> AuthenticationResult:
        auth_header = connection.headers.get(API_KEY_HEADER)
        if not auth_header:
            raise NotAuthorizedException()

        jwt_user = verify_jwt(auth_header)
        if not jwt_user:
            raise NotAuthorizedException()

        user_id = str(jwt_user.id)

        sqlalchemy_plugin = connection.app.plugins.get(SQLAlchemyPlugin)
        db_config = sqlalchemy_plugin.config[0]
        session_maker = db_config.create_session_maker()
        async with session_maker() as db_session:
            user_query = await db_session.execute(
                select(User).where(User.id == user_id)
            )
            user = user_query.scalar_one_or_none()

        if not user:
            raise NotAuthorizedException()

        return AuthenticationResult(user=user, auth=auth_header)


@dataclass
class LoginRequest:
    """
    Parameters sent by the user in order to login.
    """

    email: str
    password: str
    two_fa_code: str | None = None


@dataclass
class LoginResponse:
    jwt_token: str


@dataclass
class ChangePasswordRequest:
    old_password: str
    new_password: str


@post("/login")
async def login_handler(
    data: Annotated[LoginRequest, Body(title="Login Request")],
    db_session: AsyncSession,
) -> Response[LoginResponse]:
    """
    Login to the application.
    param data: the login data the user entered
    return: a JSON object containing the generated jwt token
    """
    user_query = await db_session.execute(select(User).where(User.email == data.email))
    user = user_query.scalar_one_or_none()

    if not user or not verify_password(user.password_hash, data.password):
        raise ClientException("invalid username or password")

    # TOTP 2FA: only required if user has a configured secret (and not pending)
    secret, pending = _parse_totp_secret(user.two_fa_secret)
    if secret and not pending:
        code = _normalize_totp_code(data.two_fa_code)
        if not code:
            raise ClientException("2FA code required")
        if not verify_totp(secret, code):
            raise ClientException("invalid 2FA code")

    jwt_token = create_jwt(user, config.jwt_config.validy_duration_hours)
    return Response(
        content=LoginResponse(jwt_token=jwt_token),
        headers={"Authorization": jwt_token},
    )


def create_jwt(user: User, validity_hours: int) -> str:
    jwt_user = JwtUser(id=str(user.id), name=user.name, email=user.email)

    jwt_payload = jwt_user.__dict__
    # set expiration time - automatically gets handled when `jwt.decode` is called
    jwt_payload["exp"] = datetime.now(tz=timezone.utc) + timedelta(hours=validity_hours)

    return jwt.encode(
        payload=jwt_payload, key=config.jwt_config.secret, algorithm=JWT_ALGORITHM
    )


def verify_jwt(jwt_token: str) -> JwtUser | None:
    try:
        user_info: dict[str, Any] = jwt.decode(
            jwt_token, config.jwt_config.secret, algorithms=[JWT_ALGORITHM]
        )
    except jwt.DecodeError:
        return None
    except jwt.ExpiredSignatureError:
        # possible TODO: inform user that session has expired
        return None

    # the expiration time is not part of the user info
    # hence it must be removed in order to create a JwtUser
    del user_info["exp"]
    jwt_user: JwtUser = JwtUser(**user_info)

    return jwt_user


def hash_password(password: str) -> str:
    """
    Hashes the password using Argon2
    """
    hasher = PasswordHasher()
    return hasher.hash(password)


def verify_password(password_hash: str, password: str) -> bool:
    """
    Verify the password with the given Argon2 Hash.

    param password: the password to check against
    param password_hash: the argon2 hash of the password
    return: whether the password is correct
    """
    pw_hasher = PasswordHasher()
    try:
        # guaranteed to crash if the password is invalid, so we don't need to handle the return type (always true)
        _ = pw_hasher.verify(password_hash, password)
        return True
    except VerifyMismatchError:
        return False


@patch("/users/{user_id:str}/password/change")
async def change_password(
    db_session: AsyncSession,
    user_id: str = Parameter(),
    data: ChangePasswordRequest = Body(title="Change Password Request"),
) -> SuccessResponse:
    """
    Change a user's password.

    param user_id: ID of the user whose password should be changed
    param data: old and new password
    """

    # load user
    user_query = await db_session.execute(select(User).where(User.id == user_id))
    user = user_query.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    # verify old password
    if not verify_password(user.password_hash, data.old_password):
        raise NotAuthorizedException("Old password is incorrect")

    # hash and store new password
    user.password_hash = hash_password(data.new_password)
    await db_session.commit()

    return SuccessResponse("password successfully changed")


def _ensure_self_or_admin(connection: ASGIConnection, user_id: str) -> None:
    u = connection.user
    if not u:
        raise NotAuthorizedException()
    u = typing.cast(User, u)
    if str(u.id) != user_id and not u.is_admin:
        raise NotAuthorizedException()


@dataclass
class TotpSetupResponse:
    secret: str
    otpauth_uri: str


@dataclass
class TotpCodeRequest:
    code: str


@post("/users/{user_id:str}/2fa/totp/setup")
async def totp_setup(
    connection: ASGIConnection,
    db_session: AsyncSession,
    user_id: str = Parameter(),
) -> Response:
    _ensure_self_or_admin(connection, user_id)

    user_query = await db_session.execute(select(User).where(User.id == user_id))
    user = user_query.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    secret = generate_totp_secret()
    user.two_fa_secret = TOTP_PENDING_PREFIX + secret
    await db_session.commit()

    uri = totp_provisioning_uri(secret, user.email)
    return Response(content=TotpSetupResponse(secret=secret, otpauth_uri=uri))


@post("/users/{user_id:str}/2fa/totp/confirm")
async def totp_confirm(
    connection: ASGIConnection,
    db_session: AsyncSession,
    user_id: str = Parameter(),
    data: TotpCodeRequest = Body(title="TOTP Confirm Request"),
) -> SuccessResponse:
    _ensure_self_or_admin(connection, user_id)

    user_query = await db_session.execute(select(User).where(User.id == user_id))
    user = user_query.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    secret, pending = _parse_totp_secret(user.two_fa_secret)
    if not secret or not pending:
        raise ClientException("no pending TOTP setup")

    code = _normalize_totp_code(data.code)
    if not code or not verify_totp(secret, code):
        raise ClientException("invalid 2FA code")

    user.two_fa_secret = secret
    await db_session.commit()
    return SuccessResponse("TOTP 2FA enabled")


@post("/users/{user_id:str}/2fa/totp/disable")
async def totp_disable(
    connection: ASGIConnection,
    db_session: AsyncSession,
    user_id: str = Parameter(),
    data: TotpCodeRequest = Body(title="TOTP Disable Request"),
) -> SuccessResponse:
    _ensure_self_or_admin(connection, user_id)

    user_query = await db_session.execute(select(User).where(User.id == user_id))
    user = user_query.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    secret, pending = _parse_totp_secret(user.two_fa_secret)
    if not secret:
        return SuccessResponse("TOTP 2FA already disabled")

    if pending:
        user.two_fa_secret = ""
        await db_session.commit()
        return SuccessResponse("pending TOTP setup cleared")

    code = _normalize_totp_code(data.code)
    if not code or not verify_totp(secret, code):
        raise ClientException("invalid 2FA code")

    user.two_fa_secret = ""
    await db_session.commit()
    return SuccessResponse("TOTP 2FA disabled")
