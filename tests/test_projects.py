from datetime import datetime, timezone
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
)
from litestar.testing import TestClient

from app import app

from utils import create_project


def test_project_check(auth_client):
    response = auth_client.post(
        "/projects",
        json={
            "name": "Testprojekt",
            "deadline": "2025-08-13T10:05:00Z",
            "done": False,
        },
    )

    assert response.status_code == HTTP_201_CREATED
    assert response.json()["message"] == "successfully created project"

    response = auth_client.get("/projects")
    assert response.status_code == HTTP_200_OK

    project = response.json()[0]
    assert project["name"] == "Testprojekt"
    assert project["deadline"] == "2025-08-13T10:05:00Z"

    # check if the automatically set creation date is set to approximately
    # the current time
    parsed_date = datetime.fromisoformat(project["creation_date"])
    date_offset = parsed_date - datetime.now(timezone.utc)
    assert date_offset.total_seconds() < 1


def test_empty_project_check(auth_client):
    response = auth_client.post(
        "/projects",
        params={
            "name": "Testprojekt",
            "deadline": "2025",  # invalid date
            "done": False,
        },
    )

    assert response.status_code == HTTP_400_BAD_REQUEST


def test_change_project_deadline(auth_client):
    p_id = create_project(auth_client)

    # Set new deadline (from 5 to 100)
    response = auth_client.patch(f"/projects/{p_id}/deadline/extend?new_deadline=100")

    assert response.status_code == HTTP_200_OK

    response = auth_client.get("/projects")
    data = response.json()
    project = next(p for p in data if p["id"] == p_id)
    assert project["deadline"] == 100


def test_project_check_unauthorized():
    with TestClient(app=app) as client:
        response = client.post(
            "/projects",
            json={
                "name": "Testprojekt",
                "deadline": "2025-08-13T10:05:00Z",
                "done": False,
            },
        )
        assert response.status_code == HTTP_401_UNAUTHORIZED
