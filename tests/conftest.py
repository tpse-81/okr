from litestar.status_codes import HTTP_200_OK
import pytest


# ----------------
# Helper Functions
# ----------------


# Helper function: Creates a project
@pytest.fixture()
def create_project(client):
    def _create(name="P1"):
        result = client.get(
            "/projects/create",
            params={"name": name, "deadline": 10, "creation_date": 1},
        )
        assert result.status_code == HTTP_200_OK
        return client.get("/projects").json()[-1]["id"]

    return _create


# Helper function: Creates an objective
@pytest.fixture()
def create_objective(client, create_project):
    def _create(project_id=None, name="O1"):
        if project_id is None:
            project_id = create_project()

        result = client.get(
            "/objectives/create",
            params={"name": name, "description": "desc_obj", "project_id": project_id},
        )
        assert result.status_code == HTTP_200_OK

        return client.get("/objectives").json()[-1]["id"]

    return _create


# Helper function: Creates a key result
@pytest.fixture()
def create_key_result(client, create_objective):
    def _create(objective_id=None, description="desc_kr"):
        if objective_id is None:
            objective_id = create_objective()

        result = client.get(
            "/key_results/create",
            params={
                "objective_id": objective_id,
                "description": description,
                "start_value": 15,
                "end_value": 10,
            },
        )
        assert result.status_code == HTTP_200_OK

        return client.get("/key_results").json()[-1]["id"]

    return _create


# Helper function: Creates a task
@pytest.fixture()
def create_task(client, create_key_result):
    def _create(key_result_id=None, description="desc_t", task_state="open"):
        if key_result_id is None:
            key_result_id = create_key_result()

        result = client.get(
            f"/key_results/{key_result_id}/tasks/create",
            params={"description": description, "task_state": task_state},
        )
        assert result.status_code == HTTP_200_OK

        return client.get(f"/key_results/{key_result_id}/tasks").json()[-1]["id"]

    return _create


# Helper function: Create a user
@pytest.fixture()
def create_user(client):
    def _create(name="user"):
        result = client.get(
            "/users/create",
            params={"name": name, "email": "test@mail.com", "password": "test_pass"},
        )
        assert result.status_code == HTTP_200_OK

        return client.get("/users").json()[-1]["id"]

    return _create