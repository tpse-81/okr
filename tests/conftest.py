from litestar import Litestar
import pytest
from litestar.status_codes import (
    HTTP_201_CREATED,
)
from litestar.testing import TestClient
from app import app

import uuid


@pytest.fixture(scope="module")
def client():
    with TestClient(app=app) as client:
        yield client


@pytest.fixture(scope="module")
def test_user(client):
    name = f"test-user-{uuid.uuid4()}"
    response = client.post(
        "/users/create",
        json={
            "name": name,
            "email": "test@example.com",
            "password": "testpassword123",
        },
    )
    assert response.status_code == HTTP_201_CREATED
    return {
        "name": name,
        "password": "testpassword123",
    }


@pytest.fixture(scope="module")
def auth_token(client: TestClient, test_user):
    response = client.post(
        "/login",
        json={
            "name": test_user["name"],
            "password": test_user["password"],
            "two_fa_code": None,
        },
    )
    assert response.status_code == HTTP_201_CREATED
    return response.cookies.get("token")


@pytest.fixture
def auth_client(client, auth_token) -> TestClient[Litestar]:
    client.cookies.set("token", auth_token)
    return client
