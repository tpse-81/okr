from litestar.status_codes import (
    HTTP_200_OK,
)

from app import app

app.debug = True


def create_project(client):
    project = client.get(
        "/projects/create",
        params={
            "name": "name",
            "deadline": 5,
            "creation_date": 5,
            "done": "false",
        },
    )
    assert project.status_code == HTTP_200_OK
    project = client.get("/projects")
    return project.json()[0].get("id")


def create_objective(client, project_id, name="name", description="description"):
    objective = client.get(
        "/objectives/create",
        params={
            "name": name,
            "description": description,
            "project_id": str(project_id),
        },
    )
    assert objective.status_code == HTTP_200_OK
    objective = client.get("/objectives")
    return objective.json()[0].get("id")


def create_key_result(client, project_id, objective_id):
    key_result = client.get(
        "/key_results/create",
        params={
            "project_id": project_id,
            "objective_id": objective_id,
            "description": "description",
            "start_value": 15,
            "end_value": 10,
        },
    )
    assert key_result.status_code == HTTP_200_OK
    key_result = client.get("/key_results")
    return key_result.json()[0].get("id")


def create_task(client, key_result_id):
    task = client.get(
        f"/key_results/{key_result_id}/tasks/create",
        params={"description": "description", "task_state": "open"},
    )
    assert task.status_code == HTTP_200_OK
    task = client.get(f"/key_results/{key_result_id}/tasks")
    return task.json()[0].get("id")


def create_user(client, name="name", email=None):
    email = email or f"{name.lower()}@test.com"
    user = client.get(
        "/users/create",
        params={
            "name": name,
            "email": email,
            "password": "testpassword123",
        },
    )
    assert user.status_code == HTTP_200_OK
    user = client.get("/users")
    return user.json()[-1]["id"]
