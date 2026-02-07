import uuid

import pyotp
import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_400_BAD_REQUEST

from app import app

app.debug = True


def _create_user(client, email: str, password: str) -> None:
    response = client.post(
        "/users/create",
        json={"name": "TOTP Test User", "email": email, "password": password},
    )
    assert response.status_code == HTTP_201_CREATED


def _login(client, email: str, password: str, two_fa_code: str | None) -> str:
    response = client.post(
        "/login",
        json={"email": email, "password": password, "two_fa_code": two_fa_code},
    )
    assert response.status_code == HTTP_201_CREATED
    return response.json()["jwt_token"]


def _get_user_id(auth_client, email: str) -> str:
    response = auth_client.get("/users")
    assert response.status_code == HTTP_200_OK
    for user in response.json():
        if user.get("email") == email:
            return user["id"]
    pytest.fail(f"user with email {email!r} not found")


@pytest.fixture()
def totp_enabled_user(client):
    email = f"totp-{uuid.uuid4()}@example.com"
    password = "testpassword123"

    _create_user(client, email=email, password=password)

    token = _login(client, email=email, password=password, two_fa_code=None)
    client.headers.update({"Authorization": token})

    user_id = _get_user_id(client, email=email)

    setup_response = client.post(f"/users/{user_id}/2fa/totp/setup")
    assert setup_response.status_code == HTTP_200_OK
    secret = setup_response.json()["secret"]

    confirm_code = pyotp.TOTP(secret).now()
    confirm_response = client.post(
        f"/users/{user_id}/2fa/totp/confirm", json={"code": confirm_code}
    )
    assert confirm_response.status_code == HTTP_200_OK
    assert confirm_response.json()["message"] == "TOTP 2FA enabled"

    yield {
        "email": email,
        "password": password,
        "user_id": user_id,
        "token": token,
        "secret": secret,
    }

    # wichtig: Header wieder sauber machen (client ist module-scoped)
    client.headers.pop("Authorization", None)


def test_enable_totp_requires_code_on_login(client, totp_enabled_user):
    response = client.post(
        "/login",
        json={
            "email": totp_enabled_user["email"],
            "password": totp_enabled_user["password"],
            "two_fa_code": None,
        },
    )
    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "2FA code required"


def test_login_with_totp(client, totp_enabled_user):
    code = pyotp.TOTP(totp_enabled_user["secret"]).now()
    response = client.post(
        "/login",
        json={
            "email": totp_enabled_user["email"],
            "password": totp_enabled_user["password"],
            "two_fa_code": code,
        },
    )
    assert response.status_code == HTTP_201_CREATED
    assert "jwt_token" in response.json()


def test_disable_totp_allows_login_without_code(client, totp_enabled_user):
    client.headers.update({"Authorization": totp_enabled_user["token"]})

    disable_code = pyotp.TOTP(totp_enabled_user["secret"]).now()
    response = client.post(
        f"/users/{totp_enabled_user['user_id']}/2fa/totp/disable",
        json={"code": disable_code},
    )
    assert response.status_code == HTTP_200_OK
    assert response.json()["message"] == "TOTP 2FA disabled"

    # finaler Login ohne 2FA-Code: sicher ohne Auth-Header testen
    client.headers.pop("Authorization", None)
    response = client.post(
        "/login",
        json={
            "email": totp_enabled_user["email"],
            "password": totp_enabled_user["password"],
            "two_fa_code": None,
        },
    )
    assert response.status_code == HTTP_201_CREATED
