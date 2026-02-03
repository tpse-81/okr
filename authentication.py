from dataclasses import dataclass
import secrets
from typing import Annotated, Any

from argon2.exceptions import VerifyMismatchError
from litestar import Response, post, patch
from litestar.connection import ASGIConnection
from litestar.datastructures import Cookie
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

API_KEY_HEADER = "Authorization"
JWT_ALGORITHM = "HS256"


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

    # TODO: verify 2FA code

    jwt_token = create_jwt(user, config.jwt_config.validy_duration_hours)
    response = Response(content=LoginResponse(jwt_token=jwt_token))
    response.set_cookie(
        key="token",
        value=jwt_token,
        max_age=604800, # 1 Week maybe change to 1 day later
        samesite="lax",
        secure=True, #https benötigt, außer bei localhjost
        httponly=False, #TODO später auf True ändern
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


def generate_twofa_secret() -> str:
    """
    generates a random 2FA Token
    """
    return secrets.token_hex(16)


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


@post("/users/{user_id:str}/auth_token")
async def get_new_token(
    db_session: AsyncSession,
    user_id: str = Parameter(),
) -> SuccessResponse:
    """
    Change a user's token.
    """

    # load user
    user_query = await db_session.execute(select(User).where(User.id == user_id))
    user = user_query.scalar_one_or_none()
    if not user:
        raise NotFoundException("User not found")

    user.two_fa_secret = generate_twofa_secret()
    await db_session.commit()

    return SuccessResponse("new 2FA token generated")
