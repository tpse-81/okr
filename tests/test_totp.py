import uuid

import pyotp
import pytest
from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_403_FORBIDDEN

from app import app
from tests.utils import create_user

app.debug = True


def login_request(client, username: str, password: str, two_fa_code: str | None = None):
    return client.post(
        "/login",
        json={"name": username, "password": password, "two_fa_code": two_fa_code},
    )


@pytest.fixture()
def totp_enabled_user(client):
    # unique user to avoid UNIQUE(name) constraint
    name = f"totp-{uuid.uuid4()}"
    email = f"{name}@example.com"
    password = "testpassword123"

    user_id = create_user(client, name=name, email=email, password=password)

    # first login (no 2FA yet) to get token
    login_resp = login_request(client, username=name, password=password)
    assert login_resp.status_code == HTTP_201_CREATED
    jwt_token = login_resp.json().get("jwt_token") or login_resp.cookies.get("token")
    assert jwt_token, "No JWT token returned (neither JSON nor cookie)"

    # enable totp (auth via cookie)
    setup_resp = client.post(
        f"/users/{user_id}/2fa/totp/setup",
        cookies={"token": jwt_token},
    )
    assert setup_resp.status_code in (HTTP_200_OK, HTTP_201_CREATED)
    secret = setup_resp.json()["secret"]

    confirm_resp = client.post(
        f"/users/{user_id}/2fa/totp/confirm",
        json={"code": pyotp.TOTP(secret).now()},
        cookies={"token": jwt_token},
    )
    assert confirm_resp.status_code in (HTTP_200_OK, HTTP_201_CREATED)
    assert confirm_resp.json()["message"] == "TOTP 2FA enabled"

    yield {
        "user_id": user_id,
        "name": name,
        "email": email,
        "password": password,
        "jwt_token": jwt_token,
        "secret": secret,
    }

    # cleanup: best effort disable again (so tests are isolated)
    try:
        client.post(
            f"/users/{user_id}/2fa/totp/disable",
            json={"code": pyotp.TOTP(secret).now()},
            cookies={"token": jwt_token},
        )
    except Exception:
        pass


def test_enable_totp_requires_code_on_login(client, totp_enabled_user):
    resp = login_request(
        client,
        username=totp_enabled_user["name"],
        password=totp_enabled_user["password"],
        two_fa_code=None,
    )
    assert resp.status_code == HTTP_403_FORBIDDEN

    payload = resp.json()

    # backend provides the real info via "extra"
    extra = payload.get("extra", {})
    assert extra, f"Expected extra payload, got: {payload}"
    assert extra["totp_supported"]


def test_login_with_totp(client, totp_enabled_user):
    resp = login_request(
        client,
        username=totp_enabled_user["name"],
        password=totp_enabled_user["password"],
        two_fa_code=pyotp.TOTP(totp_enabled_user["secret"]).now(),
    )
    assert resp.status_code == HTTP_201_CREATED
    assert resp.json().get("jwt_token") or resp.cookies.get("token")


def test_disable_totp_allows_login_without_code(client, totp_enabled_user):
    disable_resp = client.post(
        f"/users/{totp_enabled_user['user_id']}/2fa/totp/disable",
        json={"code": pyotp.TOTP(totp_enabled_user["secret"]).now()},
        cookies={"token": totp_enabled_user["jwt_token"]},
    )
    assert disable_resp.status_code in (HTTP_200_OK, HTTP_201_CREATED)
    assert disable_resp.json()["message"] == "TOTP 2FA disabled"

    resp = login_request(
        client,
        username=totp_enabled_user["name"],
        password=totp_enabled_user["password"],
        two_fa_code=None,
    )
    assert resp.status_code == HTTP_201_CREATED
    assert resp.json().get("jwt_token") or resp.cookies.get("token")
