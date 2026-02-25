from litestar.testing import TestClient
import uuid

from litestar.status_codes import HTTP_201_CREATED, HTTP_200_OK
from app import app

app.debug = True


def create_project(client):
    project = client.post(
        "/projects",
        json={
            "name": "name",
            "deadline": 5,
            "creation_date": 5,
            "done": False,
        },
    )
    assert project.status_code == HTTP_201_CREATED
    project = client.get("/projects")
    return project.json()[-1].get("id")


def create_objective(client, project_id, name="name", description="description"):
    objective = client.post(
        f"/projects/{project_id}/objectives",
        json={
            "name": name,
            "description": description,
        },
    )
    assert objective.status_code == HTTP_201_CREATED
    objective = client.get("/objectives")
    return objective.json()[-1].get("id")


def create_key_result(client, objective_id, start_value=15, end_value=10):
    key_result = client.post(
        f"/objectives/{objective_id}/key_results",
        json={
            "description": "description",
            "start_value": start_value,
            "end_value": end_value,
        },
    )
    assert key_result.status_code == HTTP_201_CREATED
    key_result = client.get("/key_results")
    return key_result.json()[-1].get("id")


def create_task(client, key_result_id):
    task = client.post(
        f"/key_results/{key_result_id}/tasks",
        json={"name": "title", "description": "description", "task_state": "open"},
    )
    assert task.status_code == HTTP_201_CREATED
    task = client.get(f"/key_results/{key_result_id}/tasks")
    return task.json()[-1].get("id")


def login(client: TestClient, username, password) -> str:
    response = client.post("/login", json={"name": username, "password": password})
    assert response.status_code == HTTP_201_CREATED
    return response.cookies["token"]


def create_user(client, name=None, email=None, password=None):
    admin_cookies = {
        "token": login(client, "admin", "password"),
    }

    if name is None:
        name = f"test-user-{uuid.uuid4()}"
    email = email or f"{name.lower()}@test.com"
    user = client.post(
        "/users/create",
        json={
            "name": name,
            "email": email,
            "password": password or "testpassword123",

        },
        cookies=admin_cookies,
    )
    assert user.status_code == HTTP_201_CREATED
    user = client.get("/users", cookies=admin_cookies)
    assert user.status_code == HTTP_200_OK
    return user.json()[-1]["id"]