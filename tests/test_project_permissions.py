from litestar.status_codes import (
    HTTP_403_FORBIDDEN,
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_204_NO_CONTENT,
)
from litestar import Litestar
from litestar.testing import TestClient

from utils import (
    create_project,
    create_objective,
    create_key_result,
    create_task,
    create_user,
    login,
)

# deleting objectives and key results must not be explicitly tested because they use the same logic as tasks
# so if task permissions work, objectives and key results will also work fine


def test_project_write_permissions(auth_client: TestClient[Litestar]):
    project_id = create_project(auth_client)

    # create user u1 that's part of the project
    u1 = create_user(auth_client, name="permissions-test", password="pwtest")
    u1_token = login(auth_client, username="permissions-test", password="pwtest")
    response = auth_client.post(f"/projects/{project_id}/users/{u1}?role=member")
    assert response.status_code == HTTP_201_CREATED

    # login as a different user that's not part of the project
    _u2 = create_user(auth_client, name="permissions-test-2", password="pwtest")
    u2_token = login(auth_client, username="permissions-test-2", password="pwtest")

    # user is not part of the project, so it should fail
    response = auth_client.delete(
        f"/projects/{project_id}",
        cookies={
            "token": u2_token,
        },
    )
    assert response.status_code == HTTP_403_FORBIDDEN

    # user u2 is not part of the project, so this should fail
    response = auth_client.patch(
        f"/projects/{project_id}",
        json={"name": "newname", "deadline": "2027-08-13T10:05:00Z", "done": True},
        cookies={
            "token": u2_token,
        },
    )
    assert response.status_code == HTTP_403_FORBIDDEN

    # user u1 is only project member, so they shouldn't be able to modify the project
    response = auth_client.patch(
        f"/projects/{project_id}",
        json={"name": "newname", "deadline": "2027-08-13T10:05:00Z", "done": True},
        cookies={
            "token": u1_token,
        },
    )
    assert response.status_code == HTTP_403_FORBIDDEN

    # user u1 is only member in the project, so they should not be allowed to delete the project
    response = auth_client.delete(
        f"/projects/{project_id}", cookies={"token": u1_token}
    )
    assert response.status_code == HTTP_403_FORBIDDEN

    # project creator is automatically assigned the team lead role, so they can delete the project
    response = auth_client.delete(f"/projects/{project_id}")
    assert response.status_code == HTTP_204_NO_CONTENT


def test_task_write_permissions(auth_client: TestClient[Litestar]):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)
    key_result_id = create_key_result(auth_client, objective_id)
    task_id = create_task(auth_client, key_result_id)

    # create user u1 that's part of the project
    u1 = create_user(auth_client, name="task-permissions-test", password="pwtest")
    u1_token = login(auth_client, username="task-permissions-test", password="pwtest")
    response = auth_client.post(f"/projects/{project_id}/users/{u1}?role=member")
    assert response.status_code == HTTP_201_CREATED

    # login as a different user that's not part of the project
    _u2 = create_user(auth_client, name="task-permissions-test-2", password="pwtest")
    u2_token = login(auth_client, username="task-permissions-test-2", password="pwtest")

    # user is not part of the project, so it should fail
    response = auth_client.delete(
        f"/tasks/{task_id}",
        cookies={
            "token": u2_token,
        },
    )
    assert response.status_code == HTTP_403_FORBIDDEN

    # user u1 is part of the project, so they should be allowed to modify the task
    response = auth_client.patch(
        f"/tasks/{task_id}",
        json={
            "name": "newtitle",
            "description": "newdescription",
            "task_state": "done",
        },
        cookies={"token": u1_token},
    )
    assert response.status_code == HTTP_200_OK

    # user u1 is part of the project, so they should be allowed to delete the task
    response = auth_client.delete(f"/tasks/{task_id}", cookies={"token": u1_token})
    assert response.status_code == HTTP_204_NO_CONTENT
