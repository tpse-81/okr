from litestar.testing import TestClient
from litestar.status_codes import (
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_200_OK,
)

from app import app
from models.user import User
from authentication import create_jwt, verify_jwt
from time import sleep
from utils import create_user, login

app.debug = True


def test_create_invalid_user(client):
    # username is an email
    response = client.post(
        "/users/create",
        json={
            "name": "foo@bar.com",
            "email": "example@test.com",
            "password": "testpassword123",
        },
        cookies={
            "token": login(client, "admin", "password"),
        },
    )
    assert response.status_code == HTTP_400_BAD_REQUEST

    # invalid email address
    response = client.post(
        "/users/create",
        json={
            "name": "foobar",
            "email": "email-without-at-sign",
            "password": "testpassword123",
        },
        cookies={
            "token": login(client, "admin", "password"),
        },
    )
    assert response.status_code == HTTP_400_BAD_REQUEST


def test_login_wrong_password(client, test_user):
    password = test_user["name"] + "randomstuff"
    response = client.post(
        "/login",
        json={
            "name": test_user["name"],
            "password": password,
            "two_fa_code": None,
        },
    )

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "invalid username or password"


def test_login_non_existing_name(client):
    response = client.post(
        "/login",
        json={
            "name": "thisnamedoesnotexist",
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


def test_not_username_but_email(client, test_user):
    response = client.post(
        "/login",
        json={
            "name": "test@example.com",
            "password": "testpassword123",
            "two_fa_code": None,
        },
    )

    assert response.status_code == HTTP_201_CREATED


def test_change_password(client: TestClient, test_user):
    token = login(client, username=test_user["name"], password=test_user["password"])
    response = client.patch(
        "/users/password/change",
        json={"old_password": test_user["password"], "new_password": "newpassword"},
        cookies={
            "token": token,
        },
    )
    assert response.status_code == HTTP_200_OK

    login(client, username=test_user["name"], password="newpassword")


def test_reset_password(client: TestClient):
    u = create_user(client, name="reset-test", email="reset@password.com")
    response = client.patch(
        f"/users/{u}/password/reset",
        json={"new_password": "newpassword"},
        cookies={"token": login(client, "admin", "password")},
    )
    assert response.status_code == HTTP_200_OK

    login(client, username="reset-test", password="newpassword")
