from dataclasses import dataclass
import secrets
from typing import Annotated, Any
from argon2.exceptions import VerifyMismatchError
from litestar import Response, post
from litestar.connection import ASGIConnection
from litestar.exceptions import ClientException, NotAuthorizedException
from litestar.middleware import AbstractAuthenticationMiddleware, AuthenticationResult

import jwt
from argon2 import PasswordHasher
from datetime import datetime, timezone, timedelta

from litestar.params import Body
from advanced_alchemy.extensions.litestar import SQLAlchemyPlugin
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from models.user import User

API_KEY_HEADER = "Authorization"
JWT_ALGORITHM = "HS256"

# TODO: make configurable!
JWT_SECRET = "secretfortesting"
# how long tokens are valid - if the time has
# passed, users are automatically getting logged out
JWT_VALIDITY_DURATION_HOURS = 7 * 24  # 1 week


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
    # TODO: 2fa is not yet implemented, so the code is ignored
    two_fa_code: str | None


@dataclass
class LoginResponse:
    jwt_token: str


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
    user_query = await db_session.execute(select(User).where(User.email == data.email.strip().lower()))
    user = user_query.scalar_one_or_none()

    if not user or not verify_password(user.password_hash, data.password):
        raise ClientException("invalid username or password")

    # TODO: verify 2FA code

    jwt_token = create_jwt(user, JWT_VALIDITY_DURATION_HOURS)
    return Response(
        content=LoginResponse(jwt_token=jwt_token),
        headers={"Authorization": jwt_token},
    )


def create_jwt(user: User, validity_hours: int) -> str:
    jwt_user = JwtUser(id=str(user.id), name=user.name, email=user.email)

    jwt_payload = jwt_user.__dict__
    # set expiration time - automatically gets handled when `jwt.decode` is called
    jwt_payload["exp"] = datetime.now(tz=timezone.utc) + timedelta(hours=validity_hours)

    return jwt.encode(payload=jwt_payload, key=JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_jwt(jwt_token: str) -> JwtUser | None:
    try:
        user_info: dict[str, Any] = jwt.decode(
            jwt_token, JWT_SECRET, algorithms=[JWT_ALGORITHM]
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


def generate_twofa_secret() -> str:
    """
    generates a random 2FA Token
    """
    return secrets.token_hex(16)
