from litestar.status_codes import HTTP_200_OK
from utils import create_project, create_objective, create_key_result, create_task


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
