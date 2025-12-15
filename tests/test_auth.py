from litestar.status_codes import (
    HTTP_400_BAD_REQUEST,
)

from app import app
from models.user import User
from authentication import create_jwt, verify_jwt
from time import sleep

app.debug = True


def test_login_wrong_password(client, test_user):
    password = test_user["password"] + "randomstuff"
    response = client.post(
        "/login",
        json={
            "email": test_user["email"],
            "password": password,
            "two_fa_code": None,
        },
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "invalid username or password"


def test_login_non_existing_email(client):
    response = client.post(
        "/login",
        json={
            "email": "thisemail@doesnotexist.com",
            "password": "securepassword",
            "two_fa_code": None,
        },
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "invalid username or password"


def test_jwt_expiry_expired():
    user = User(name="", password_hash="", email="", two_fa_secret="")
    token = create_jwt(user, 0)

    sleep(0.001)  # wait 1ms for the token to expire

    assert verify_jwt(token) is None


def test_jwt_expiry_valid():
    user = User(name="", password_hash="", email="", two_fa_secret="")
    token = create_jwt(user, 1)

    sleep(0.001)  # wait some time

    # token should still be valid, because 1 hour has not yet passed
    assert verify_jwt(token) is not None
