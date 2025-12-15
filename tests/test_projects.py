from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
)
from litestar.testing import TestClient

from app import app


def test_project_check(auth_client):
    response = auth_client.post(
        "/projects",
        json={
            "name": "Testprojekt",
            "deadline": 5,
            "creation_date": 10,
            "done": False,
        },
    )

    assert response.status_code == HTTP_201_CREATED
    assert response.json()["message"] == "successfully created project"

    response = auth_client.get("/projects")
    assert response.status_code == HTTP_200_OK

    project = response.json()[0]
    assert project["name"] == "Testprojekt"
    assert project["deadline"] == 5
    assert project["creation_date"] == 10


def test_empty_project_check(auth_client):
    response = auth_client.post(
        "/projects",
        params={
            "name": "Testprojekt",
            "deadline": 5,
            "creation_date": "",  # invalid
            "done": False,
        },
    )

    assert response.status_code == HTTP_400_BAD_REQUEST


def test_project_check_unauthorized():
    with TestClient(app=app) as client:
        response = client.post(
            "/projects",
            json={
                "name": "Testprojekt",
                "deadline": 5,
                "creation_date": 10,
                "done": False,
            },
        )
        assert response.status_code == HTTP_401_UNAUTHORIZED
