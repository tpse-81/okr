from litestar import Litestar
import pytest
from litestar.status_codes import (
    HTTP_201_CREATED,
)
from litestar.testing import TestClient
from app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app=app) as client:
        yield client


@pytest.fixture(scope="module")
def test_user(client):
    response = client.post(
        "/users/create",
        json={
            "name": "Test User",
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == HTTP_201_CREATED
    return {
        "email": "test@example.com",
        "password": "testpassword123",
    }


@pytest.fixture(scope="module")
def auth_token(client, test_user):
    response = client.post(
        "/login",
        json={
            "email": test_user["email"],
            "password": test_user["password"],
            "two_fa_code": None,
        },
    )
    assert response.status_code == HTTP_201_CREATED
    return response.json()["jwt_token"]


@pytest.fixture
def auth_client(client, auth_token) -> TestClient[Litestar]:
    client.cookies.set("token", auth_token)
    return client
