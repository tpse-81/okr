import uuid

from litestar import Litestar
from litestar.testing import TestClient

from utils import create_objective, create_project, create_key_result
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
        "description": "description",
        "start_value": 5,
        "end_value": 5,
    }
    response = auth_client.post(f"/objectives/{objective_id}/key_results", json=params)
    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {"message": "successfully created key result"}

    response = auth_client.get("/key_results")
    assert response.status_code == HTTP_200_OK
    t = response.json()[0]
    assert t["description"] == "description"
    assert t["start_value"] == 5
    assert t["end_value"] == 5
    assert len(response.json()) == 1


def test_empty_key_result_check(auth_client):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)

    params = {
        "description": "description",
        "start_value": None,
        "end_value": 5,
    }
    response = auth_client.post(f"/objectives/{objective_id}/key_results", json=params)
    assert response.status_code == HTTP_400_BAD_REQUEST

    params = {
        "description": None,
        "start_value": 5,
        "end_value": 5,
    }
    response = auth_client.post(f"/objectives/{objective_id}/key_results", json=params)
    assert response.status_code == HTTP_400_BAD_REQUEST

    response = auth_client.get("/key_results")
    assert response.status_code == HTTP_200_OK
    assert len(response.json()) == 1


def test_key_result_with_fake_objective(auth_client):
    fake_id = uuid.uuid4()

    params = {
        "description": "description",
        "start_value": 5,
        "end_value": 5,
    }
    response = auth_client.post(f"/objectives/{fake_id}/key_results", json=params)
    assert response.status_code == HTTP_404_NOT_FOUND


def test_update_key_result(auth_client):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)
    key_result_id = create_key_result(auth_client, objective_id)

    response = auth_client.patch(
        f"/key_results/{key_result_id}",
        json={"description": "newdescription", "start_value": 8, "end_value": 11},
    )
    assert response.status_code == HTTP_200_OK

    response = auth_client.get("/key_results")
    assert response.status_code == HTTP_200_OK

    # check if new values have been saved
    key_result = response.json()[-1]
    assert key_result["description"] == "newdescription"
    assert key_result["start_value"] == 8
    assert key_result["end_value"] == 11


def test_key_result_check_unauthorized(auth_client):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)
    with TestClient(app=app) as client:
        response = client.post(
            f"/objectives/{objective_id}/key_results",
            json={
                "objective_id": str(objective_id),
                "description": "description",
                "start_value": 5,
                "end_value": 5,
            },
        )
        assert response.status_code == HTTP_401_UNAUTHORIZED
