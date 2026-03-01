from typing import cast
from dataclasses import dataclass

from litestar import get, patch, post, delete
from litestar.params import Parameter
from litestar.exceptions import (
    ClientException,
    NotFoundException,
    PermissionDeniedException,
)
from litestar.connection import Request

# Importing the database models
from authentication import (
    hash_password,
    get_user_by_name_or_mail,
)

from models.user import User


from dto.read_dto import (
    UserReadDTO,
)

from helpers import is_valid_email

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

import uuid

from responses import SuccessResponse


@dataclass
class CreateUserRequest:
    name: str
    email: str
    password: str


@post("/users/create")
async def create_user(
    db_session: AsyncSession, data: CreateUserRequest, request: Request
) -> SuccessResponse:
    """
    Create a new user.

    param data: the user data to create a new user from
    return: whether the user was successfully created
    """
    user = cast(User, request.user)
    if not user.is_admin:
        raise PermissionDeniedException("only admins may create new users")

    # check if there are any conflicts with existing users, e.g. if the username is already used by somebody else
    existing_user_clash = await get_user_by_name_or_mail(db_session, data.name)
    if not existing_user_clash:
        existing_user_clash = await get_user_by_name_or_mail(db_session, data.email)
    if existing_user_clash:
        raise ClientException("a user with this name or email already exists")

    if is_valid_email(data.name):
        raise ClientException("usernames must not be an e-mail addresses!")

    if not is_valid_email(data.email):
        raise ClientException("invalid email address")

    # randomly generate a user_id
    user_id = uuid.uuid4()
    password_hash = hash_password(data.password)
    user = User(
        id=user_id,
        name=data.name,
        email=data.email,
        password_hash=password_hash,
        two_fa_secret=None,
        is_admin=False,
        must_change_password=True,
    )

    db_session.add(user)
    await db_session.commit()

    return SuccessResponse("successfully created user")


@get("/me", return_dto=UserReadDTO)
async def get_me(request: Request) -> User:
    return request.user


@get("/users", return_dto=UserReadDTO)
async def get_users(db_session: AsyncSession) -> list[User]:
    """
    Get the list of users (without password hash and 2FA).

    return: a JSON list of users
    """
    return list(await db_session.scalars(select(User)))


@patch("/users/{user_id:str}/promote")
async def promote_user_to_admin(
    db_session: AsyncSession, request: Request, user_id: str = Parameter()
) -> SuccessResponse:
    """
    Promote an existing user to become an admin.
    Only the admin can call this to promote other users.
    There's no way for an admin to demote a user again, so this should be well-overthought.

    :param user_id: the id of the user to promote
    :return: a success response if the user was successfully promoted
    """
    actor = cast(User, request.user)
    if not actor.is_admin:
        raise PermissionDeniedException("only admins can promote other users to admin")

    user = await db_session.get(User, user_id)
    if not user:
        raise ClientException("user does not exist")

    user.is_admin = True
    await db_session.commit()

    return SuccessResponse("successfully promoted user to admin")


@delete("/users/{user_id:str}")
async def delete_user(db_session: AsyncSession, request: Request, user_id: str) -> None:
    """
    Delete a user and all related associations.
    To delete a user, the actor must be either
    - the admin (i.e. the admin deletes an other user account)
    - the same user that should be deleted (i.e. the user deletes itself)

    param user_id: the ID of the user to delete
    """
    user = await db_session.get(User, user_id)
    if user is None:
        raise NotFoundException("User not found")

    actor = cast(User, request.user)
    if not (actor.is_admin or actor.id == user.id):
        raise PermissionDeniedException("no permissions to delete user with given ID")

    if user.is_admin and actor.id != user.id:
        raise PermissionDeniedException(
            "admins may not reset the password of other admins"
        )

    await db_session.delete(user)
    await db_session.commit()
