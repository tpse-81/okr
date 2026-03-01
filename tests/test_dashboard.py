from litestar.status_codes import HTTP_200_OK
from litestar.testing import TestClient
from utils import (
    create_project,
    create_objective,
    create_key_result,
    create_user,
    create_task,
)


def test_dashboard(auth_client: TestClient):
    p = create_project(auth_client)
    user_id = auth_client.get("/me").json()["id"]

    o1 = create_objective(auth_client, p)

    # key result with 33.33% progress
    k1 = create_key_result(auth_client, o1, start_value=15, end_value=0)
    response = auth_client.patch(
        f"/key_results/{k1}/current",
        json={"current_value": 10},
    )
    assert response.status_code == HTTP_200_OK

    # key result with 33.33% progress
    k2 = create_key_result(auth_client, o1, start_value=0, end_value=30)
    response = auth_client.patch(
        f"/key_results/{k2}/current",
        json={"current_value": 10},
    )
    assert response.status_code == HTTP_200_OK

    o2 = create_objective(auth_client, p)
    # key result with 0% progress
    k3 = create_key_result(auth_client, o2, start_value=0, end_value=1)
    t1 = create_task(auth_client, k3)
    t2 = create_task(auth_client, k3)

    response = auth_client.get("/dashboard", params={"user_id": user_id})
    dashboard = response.json()
    assert len(dashboard["projects"]) == 1

    # check if the dashboard properly returned a list of all tasks
    assert len(dashboard["tasks"]) != 0
    task_ids = [task["id"] for task in dashboard["tasks"]]
    assert t1 in task_ids
    assert t2 in task_ids

    project = dashboard["projects"][-1]
    assert len(project["objectives"]) == 2
    # o1: 33.333%, o2: 0% -> avg: 16.666666
    assert project["progress"] == 1.0 / 6.0


def test_dashboard_no_progress(auth_client: TestClient):
    p = create_project(auth_client)

    o1 = create_objective(auth_client, p)

    # key result with same start and end value -> 100% progress
    _k1 = create_key_result(auth_client, o1, start_value=0, end_value=0)

    response = auth_client.get("/dashboard")
    dashboard = response.json()

    project = dashboard["projects"][-1]
    assert len(project["objectives"]) == 1
    assert project["progress"] == 1.0


def test_dashboard_user_with_no_projects(auth_client: TestClient):
    p = create_project(auth_client)
    o1 = create_objective(auth_client, p)
    _k1 = create_key_result(auth_client, o1)

    # create new user that is not linked to any project
    u2 = create_user(auth_client)
    response = auth_client.get("/dashboard", params={"user_id": u2})
    dashboard = response.json()
    assert len(dashboard["projects"]) == 0
