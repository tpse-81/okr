#!/usr/bin/env python3
"""
Maintenance script for managing users, resetting passwords and generating password hashes.

Run './maintenance_script.py' to see the help message.
"""

import uuid

from authentication import hash_password
import sys

from sqlalchemy.orm import Session

from config import config
from sqlalchemy import create_engine, select, func

from models.user import User


def create_user(db_session: Session, username: str, email: str, password: str):
    """
    Create a new user with the given username, email and password.
    """
    user_id = uuid.uuid4()
    password_hash = hash_password(password)
    user = User(
        id=user_id,
        name=username,
        email=email,
        password_hash=password_hash,
        two_fa_secret=None,
        is_admin=False,
    )

    db_session.add(user)
    db_session.commit()


def delete_user(db_session: Session, username: str):
    """
    Delete the user with the given username.
    """
    stmt = select(User).where(func.lower(User.name) == func.lower(username))
    user = db_session.scalars(stmt).one_or_none()
    if user is None:
        raise ValueError("user doesn't exist")

    db_session.delete(user)
    db_session.commit()


def reset_password(db_session: Session, username: str, new_password: str):
    """
    Reset the password of the user with the given username.
    """
    stmt = select(User).where(func.lower(User.name) == func.lower(username))
    user = db_session.scalars(stmt).one_or_none()
    if user is None:
        raise ValueError("user doesn't exist")

    user.password_hash = hash_password(new_password)

    # also reset 2fa because the user likely also lost these credentials
    user.two_fa_secret = None
    if user.webauthn:
        db_session.delete(user.webauthn)

    db_session.commit()


if __name__ == "__main__":
    # the script doesn't run async, so the aiosqlite extension is not needed
    db_connection_url = config.database_url.replace("+aiosqlite", "")
    engine = create_engine(db_connection_url)

    if len(sys.argv) <= 1:
        print(
            """
Usage:
- `./maintenance_script.py hash-password "<password>"`
- `./maintenance_script.py add-user "<username>" "<email>" "<password>"`
- `./maintenance_script.py delete-user "<username>"
- `./maintenance_script.py reset-password "<username>" "<password>"`
""".strip()
        )
        sys.exit(0)

    # first arg is the script name, so skip it
    command = sys.argv[1]
    args = sys.argv[2:]

    with Session(engine) as db_session:
        match command:
            case "add-user":
                assert len(args) == 3, f"expected to get 3 arguments, got {len(args)}"
                create_user(db_session, *args)
            case "reset-password":
                assert len(args) == 2, f"expected to get 2 arguments, got {len(args)}"
                reset_password(db_session, *args)
            case "delete-user":
                assert len(args) == 1, f"expected to get 1 argument, got {len(args)}"
                delete_user(db_session, *args)
            case "hash-password":
                assert len(args) == 1, f"expected to get 1 argument, got {len(args)}"
                print(hash_password(*args))
            case _:
                raise ValueError(f"unknown command '{command}'")
