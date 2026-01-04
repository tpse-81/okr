from dataclasses import dataclass
import secrets
from typing import Annotated, Any

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

import os
import uuid
import asyncio
import hmac
import hashlib
import smtplib
from email.message import EmailMessage


from sqlalchemy import delete as sa_delete
from models.login_challenge import LoginChallenge

API_KEY_HEADER = "Authorization"
JWT_ALGORITHM = "HS256"

# TODO: make configurable!
JWT_SECRET = "secretfortesting"
# how long tokens are valid. If the time has passed, users are automatically getting logged out
JWT_VALIDITY_DURATION_HOURS = 7 * 24  # 1 week

# 2FA Settings
TWOFA_CODE_TTL_MINUTES = 10
TWOFA_MAX_ATTEMPTS = 5
OTP_SECRET = os.environ.get("OTP_SECRET", JWT_SECRET)

# SMTP settings (Email)
SMTP_HOST = os.environ.get("SMTP_HOST")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER")
SMTP_PASS = os.environ.get("SMTP_PASS")
SMTP_FROM = os.environ.get("SMTP_FROM", SMTP_USER or "no-reply@example.com")

DEV_PRINT_2FA = os.environ.get("DEV_PRINT_2FA", "true").lower() == "true"

def _hash_2fa_code(challenge_id: str, code: str) -> str:
    # HMAC: even when someone sees the DB the OTP_SECRET cannot be offline bruteforced
    msg = f"{challenge_id}:{code}".encode("utf-8")
    return hmac.new(OTP_SECRET.encode("utf-8"), msg, hashlib.sha256).hexdigest()


def _send_email_sync(to_email: str, subject: str, body: str) -> None:
    if not SMTP_HOST:
        raise RuntimeError("SMTP_HOST is not configured")

    msg = EmailMessage()
    msg["From"] = SMTP_FROM
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.set_content(body)

    with smtplib.SMTP(SMTP_HOST, SMTP_PORT) as server:
        server.starttls()
        if SMTP_USER and SMTP_PASS:
            server.login(SMTP_USER, SMTP_PASS)
        server.send_message(msg)


async def send_2fa_email(to_email: str, code: str) -> None:
    subject = "Dein Login-Code"
    body = f"Dein 2FA-Code lautet: {code}\n\nEr ist {TWOFA_CODE_TTL_MINUTES} Minuten gültig."
    if SMTP_HOST:
        await asyncio.to_thread(_send_email_sync, to_email, subject, body)
    else:
        # Dev-Fallback: damit du testen kannst, ohne SMTP einzurichten
        if DEV_PRINT_2FA:
            print(f"[DEV] 2FA code for {to_email}: {code}")
        else:
            raise ClientException("E-Mail Versand ist nicht konfiguriert (SMTP_* fehlt)")


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
    two_fa_code: str | None


@dataclass
class LoginResponse:
    jwt_token: str

@dataclass
class LoginTwoFaRequiredResponse:
    requires_2fa: bool
    challenge_id: str

@dataclass
class ChangePasswordRequest:
    old_password: str
    new_password: str

@dataclass
class TwoFaVerifyRequest:
    challenge_id: str
    code: str    


@post("/login")
async def login_handler(
    data: Annotated[LoginRequest, Body(title="Login Request")],
    db_session: AsyncSession,
) -> Response:
    """
    Login to the application.

    param data: the login data the user entered

    return: a JSON object containing the generated jwt token or a 2FA challenge_id if 2FA is required
    """
    user_query = await db_session.execute(select(User).where(User.email == data.email))
    user = user_query.scalar_one_or_none()

    if not user or not verify_password(user.password_hash, data.password):
        raise ClientException("invalid username or password")

    # TODO: verify 2FA code
    # If 2FA is enabled, do not issue a JWT yet. Instead create a login challenge and send a one-time code. 
    # The client must then call POST /login/2fa with challenge_id + code to obtain a JWT
    if getattr(user, "two_fa_enabled", True):
        await db_session.execute(
            sa_delete(LoginChallenge).where(LoginChallenge.user_id == user.id)
        )

        challenge_id = uuid.uuid4()
        code = f"{secrets.randbelow(1_000_000):06d}"  # 000000 - 999999

        expires_at = datetime.utcnow() + timedelta(
            minutes=TWOFA_CODE_TTL_MINUTES
        )
        code_hash = _hash_2fa_code(str(challenge_id), code)

        challenge = LoginChallenge(
            id=challenge_id,
            user_id=user.id,
            code_hash=code_hash,
            expires_at=expires_at,
            attempts=0,
        )

        db_session.add(challenge)
        await db_session.commit()

        await send_2fa_email(user.email, code)

        return Response(
            content=LoginTwoFaRequiredResponse(
                requires_2fa=True,
                challenge_id=str(challenge_id),
            )
        )


    jwt_token = create_jwt(user, JWT_VALIDITY_DURATION_HOURS)
    return Response(
        content=LoginResponse(jwt_token=jwt_token),
        headers={"Authorization": jwt_token},
    )

@post("/login/2fa")
async def verify_twofa_handler(
    data: Annotated[TwoFaVerifyRequest, Body(title="2FA Verify Request")],
    db_session: AsyncSession,
) -> Response[LoginResponse]:
    """
    Verify a 2FA login challenge.

    param data: challenge_id and the 6-digit code sent via email
    return: a JSON object containing the generated jwt token
    """
    try:
        challenge_uuid = uuid.UUID(data.challenge_id)
    except ValueError:
        raise ClientException("Invalid challenge_id format")

    challenge = await db_session.get(LoginChallenge, challenge_uuid)

    if not challenge:
        raise NotFoundException("2FA challenge not found")

    now = datetime.utcnow()
    if challenge.expires_at < now:
        await db_session.delete(challenge)
        await db_session.commit()
        raise ClientException("2FA code expired")

    if challenge.attempts >= TWOFA_MAX_ATTEMPTS:
        await db_session.delete(challenge)
        await db_session.commit()
        raise ClientException("Too many attempts")

    expected_hash = _hash_2fa_code(str(challenge_uuid), data.code)
    if not hmac.compare_digest(expected_hash, challenge.code_hash):
        challenge.attempts += 1
        await db_session.commit()
        raise ClientException("Invalid 2FA code")

    user = await db_session.get(User, challenge.user_id)
    if not user:
        raise NotFoundException("User not found")

    await db_session.delete(challenge)
    await db_session.commit()

    jwt_token = create_jwt(user, JWT_VALIDITY_DURATION_HOURS)
    return Response(content=LoginResponse(jwt_token=jwt_token), headers={"Authorization": jwt_token})


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
