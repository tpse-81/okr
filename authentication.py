from webauthn_handlers import try_authenticate_user
from enum import Enum
from dataclasses import dataclass
from typing import Annotated, Any
import typing
import re
import pyotp

from argon2.exceptions import VerifyMismatchError
from litestar import Response, post, patch
from litestar.connection import ASGIConnection, Request
from litestar.exceptions import (
    ClientException,
    NotAuthorizedException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult

import jwt
from argon2 import PasswordHasher
from datetime import datetime, timezone, timedelta

from litestar.params import Body, Parameter
from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User
from responses import SuccessResponse
from config import config
from dto.read_dto import UserReadDTO

_BASE32_RE = re.compile(r"^[A-Z2-7]+=*$")


JWT_ALGORITHM = "HS256"
AUTH_COOKIE_NAME = "token"
TOTP_PENDING_PREFIX = "pending:"

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
    return pyotp.TOTP(secret).verify(
        code, valid_window=config.twofa_config.totp_valid_window
    )


def generate_totp_secret() -> str:
    return pyotp.random_base32()


def totp_provisioning_uri(secret: str, user_email: str) -> str:
    return pyotp.TOTP(secret).provisioning_uri(
        name=user_email, issuer_name=config.twofa_config.app_name
    )


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
        token = connection.cookies.get(AUTH_COOKIE_NAME)

        # fallback to headers for compatibility with OpenAPI docs at `/docs`
        if not token:
            token = connection.headers.get(AUTH_COOKIE_NAME)

        if not token:
            raise NotAuthorizedException()

        jwt_user = verify_jwt(token)
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

        return AuthenticationResult(user=user, auth=token)


@dataclass
class LoginRequest:
    """
    Parameters sent by the user in order to login.
    """

    name: str
    password: str
    two_fa_code: str | None = None
    # TODO: 2fa is not yet implemented, so the code is ignored
    webauthn_response: dict[str, Any] | None = None


@dataclass
class ChangePasswordRequest:
    old_password: str
    new_password: str


class TwoFaType(str, Enum):
    WEBAUTHN = "webauthn"
    TOTP = "totp"


@dataclass
class TwoFaRequiredResponse:
    type: TwoFaType
    user_id: str


async def get_user_by_name_or_mail(db_session: AsyncSession, query: str) -> User | None:
    """
    Get a user by their name (case-insensitive).

    This method tries to find a user with the given username first.
    If there's none, it falls back to searching a user whose email equals the query.

    param query: the username or email to search for
    return: the user for the given query, or `None` if no such user exists
    """
    user_query = await db_session.execute(
        select(User).where(func.lower(User.name) == func.lower(query))
    )
    user = user_query.scalar_one_or_none()
    if user:
        return user

    # fallback to email
    user_query = await db_session.execute(
        select(User).where(func.lower(User.email) == func.lower(query))
    )
    return user_query.scalar_one_or_none()


@post("/login", return_dto=UserReadDTO)
async def login_handler(
    data: Annotated[LoginRequest, Body(title="Login Request")], db_session: AsyncSession
) -> Response[User]:
    """
    Login to the application.
    If 2FA is required but not provided, a HTTP 403 "Not Authorized" error will be returned.

    param data: the login data the user entered
    return: a JSON object containing the generated jwt token
    """
    user = await get_user_by_name_or_mail(db_session, data.name)
    if user is None or not verify_password(user.password_hash, data.password):
        raise ClientException("invalid username or password")

    # TOTP 2FA: only required if user has a configured secret (and not pending)
    secret, pending = _parse_totp_secret(user.two_fa_secret)
    if secret and not pending:
        code = _normalize_totp_code(data.two_fa_code)
        if not code:
            raise PermissionDeniedException(
                extra=TwoFaRequiredResponse(TwoFaType.TOTP, str(user.id)).__dict__,
            )
        if not verify_totp(secret, code):
            raise ClientException("invalid 2FA code")

    # user has Webauthn set up -> needs to be validated as well
    if user.webauthn:
        if not data.webauthn_response:
            raise PermissionDeniedException(
                extra=TwoFaRequiredResponse(TwoFaType.WEBAUTHN, str(user.id)).__dict__,
            )

        try_authenticate_user(str(user.id), user.webauthn, data.webauthn_response)

    jwt_token = create_jwt(user, config.jwt_config.validy_duration_hours)
    response = Response(content=user)
    is_local = config.twofa_config.app_url in ("localhost", "127.0.0.1")
    response.set_cookie(
        key=AUTH_COOKIE_NAME,
        value=jwt_token,
        max_age=config.jwt_config.validy_duration_hours * (24 * 7),
        samesite="lax",
        secure=not is_local,  # https needed, except for localhost
        httponly=True,  # True, so that cookies cant be read by javascript
    )
    return response


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
    request: Request,
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

    actor = request.user

    # Only the admin or the user can change the password
    if not actor.is_admin and str(actor.id) != user_id:
        raise PermissionDeniedException("Not allowed")

    # verify old password
    if not actor.is_admin:
        if not verify_password(user.password_hash, data.old_password):
            raise NotAuthorizedException("Old password is incorrect")

    # hash and store new password
    user.password_hash = hash_password(data.new_password)
    await db_session.commit()

    return SuccessResponse("password successfully changed")


def _ensure_self_or_admin(request: Request, user_id: str) -> None:
    u = request.user
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
    request: Request,
    db_session: AsyncSession,
    user_id: str = Parameter(),
) -> Response:
    _ensure_self_or_admin(request, user_id)

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
    request: Request,
    db_session: AsyncSession,
    user_id: str = Parameter(),
    data: TotpCodeRequest = Body(title="TOTP Confirm Request"),
) -> SuccessResponse:
    _ensure_self_or_admin(request, user_id)

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
    request: Request,
    db_session: AsyncSession,
    user_id: str = Parameter(),
    data: TotpCodeRequest = Body(title="TOTP Disable Request"),
) -> SuccessResponse:
    _ensure_self_or_admin(request, user_id)

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


@post("/logout")
async def logout() -> Response[None]:
    response = Response(None)

    response.delete_cookie(
        key=AUTH_COOKIE_NAME,
    )

    return response
