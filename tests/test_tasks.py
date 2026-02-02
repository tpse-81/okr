import uuid

from litestar import Litestar
from litestar.testing import TestClient

from utils import create_objective, create_project, create_key_result
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_404_NOT_FOUND,
    HTTP_204_NO_CONTENT,
)

from app import app

app.debug = True


def test_task(auth_client: TestClient[Litestar]):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)
    key_result_id = create_key_result(auth_client, objective_id)

    params = {"description": "description", "task_state": "open"}
    response = auth_client.post(f"/key_results/{key_result_id}/tasks", json=params)
    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {"message": "successfully created task"}

    response = auth_client.get(f"/key_results/{key_result_id}/tasks")
    assert response.status_code == HTTP_200_OK
    t = response.json()[0]
    assert t["description"] == "description"
    assert len(response.json()) == 1

    response = auth_client.get("/tasks")
    assert response.status_code == HTTP_200_OK
    t = response.json()[0]
    assert t["description"] == "description"
    assert len(response.json()) == 1


def test_empty_task(auth_client):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)
    key_result_id = create_key_result(auth_client, objective_id)

    params = {"description": None, "task_state": "open"}
    response = auth_client.post(f"/key_results/{key_result_id}/tasks", json=params)
    assert response.status_code == HTTP_400_BAD_REQUEST

    params = {"description": "description", "task_state": "foobar"}
    response = auth_client.post(f"/key_results/{key_result_id}/tasks", json=params)
    assert response.status_code == HTTP_400_BAD_REQUEST


def test_task_with_fake_key_result(auth_client):
    fake_id = uuid.uuid4()

    params = {"description": "description", "task_state": "open"}
    response = auth_client.post(f"/key_results/{fake_id}/tasks", json=params)
    assert response.status_code == HTTP_404_NOT_FOUND


def test_delete_task(auth_client):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)
    key_result_id = create_key_result(auth_client, objective_id)

    params = {"description": "description", "task_state": "open"}
    response = auth_client.post(f"/key_results/{key_result_id}/tasks", json=params)
    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {"message": "successfully created task"}

    # check if task was successfully created
    response = auth_client.get(f"/key_results/{key_result_id}/tasks")
    assert response.status_code == HTTP_200_OK
    assert len(response.json()) == 1

    task_id = response.json()[0]["id"]
    response = auth_client.delete(f"/tasks/{task_id}")
    assert response.status_code == HTTP_204_NO_CONTENT

    # check if the task was really deleted
    response = auth_client.get(f"/key_results/{key_result_id}/tasks")
    assert response.status_code == HTTP_200_OK
    assert len(response.json()) == 0

    
def test_update_task(auth_client):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)
    key_result_id = create_key_result(auth_client, objective_id)
    task_id = create_task(auth_client, key_result_id)

    response = auth_client.patch(
        f"/tasks/{task_id}",
        json={"description": "newdescription", "task_state": "done"},
    )
    assert response.status_code == HTTP_200_OK

    response = auth_client.get(f"/key_results/{key_result_id}/tasks")
    assert response.status_code == HTTP_200_OK

    # check if new values have been saved
    task = response.json()[-1]
    assert task["description"] == "newdescription"
    assert task["task_state"] == "done"
