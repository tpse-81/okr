import uuid

from litestar import Litestar
from litestar.testing import TestClient

from utils import create_objective, create_project
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_401_UNAUTHORIZED,
)

from app import app

app.debug = True


def test_key_result_check(auth_client: TestClient[Litestar]):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)

    params = {
        "project_id": str(project_id),
        "objective_id": str(objective_id),
        "description": "description",
        "start_value": 5,
        "end_value": 5,
    }
    response = auth_client.post("/key_results", json=params)
    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {"message": "successfully created key result"}

    response = auth_client.get("/key_results")
    assert response.status_code == HTTP_200_OK
    t = response.json()[0]
    assert t["project_id"] == str(project_id)
    assert t["description"] == "description"
    assert t["start_value"] == 5
    assert t["end_value"] == 5
    assert len(response.json()) == 1


def test_empty_key_result_check(auth_client):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)

    params = {
        "project_id": str(project_id),
        "objective_id": str(objective_id),
        "description": "description",
        "start_value": None,
        "end_value": 5,
    }
    response = auth_client.post("/key_results", json=params)
    assert response.status_code == HTTP_400_BAD_REQUEST

    params = {
        "project_id": None,
        "objective_id": str(objective_id),
        "description": "description",
        "start_value": 5,
        "end_value": 5,
    }
    response = auth_client.post("/key_results", json=params)
    assert response.status_code == HTTP_400_BAD_REQUEST

    response = auth_client.get("/key_results")
    assert response.status_code == HTTP_200_OK
    assert len(response.json()) == 1


def test_key_result_with_fake_project(auth_client):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)
    fake_id = uuid.uuid4()

    params = {
        "project_id": str(fake_id),
        "objective_id": str(objective_id),
        "description": "description",
        "start_value": 5,
        "end_value": 5,
    }
    response = auth_client.post("/key_results", json=params)
    assert response.status_code == HTTP_404_NOT_FOUND


def test_key_result_check_unauthorized(auth_client):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)
    with TestClient(app=app) as client:
        response = client.post(
            "/key_results",
            json={
                "project_id": str(project_id),
                "objective_id": str(objective_id),
                "description": "description",
                "start_value": 5,
                "end_value": 5,
            },
        )
        assert response.status_code == HTTP_401_UNAUTHORIZED
