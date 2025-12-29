from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_404_NOT_FOUND,
    HTTP_400_BAD_REQUEST,
)

from utils import (
    create_objective,
    create_project,
    create_user,
    app,
    create_key_result,
    create_task,
)

app.debug = True


# Test 1: Query objectives by project ID
def test_query_objectives_by_project(auth_client):
    # create a project
    p = create_project(auth_client)

    # create 2 objectives for the same project
    create_objective(auth_client, p, name="O1")
    create_objective(auth_client, p, name="O2")

    # check if both objectives can be queried
    response = auth_client.get(f"/projects/{p}/objectives")
    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert len(data) == 2

    names = [o["name"] for o in data]
    assert "O1" in names
    assert "O2" in names


# Test 2: Query key results by objective ID
def test_query_key_results_by_objective(auth_client):
    p = create_project(auth_client)
    # create an objective
    o = create_objective(auth_client, p)

    # create 2 key results for the same objective
    kr1 = create_key_result(auth_client, p, o)
    kr2 = create_key_result(auth_client, p, o)

    # check if both key results can be queried
    response = auth_client.get(f"objectives/{o}/key_results")
    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert len(data) == 2

    krs = [k["id"] for k in data]
    assert kr1 in krs
    assert kr2 in krs


# Test 3: Query tasks by key result ID
def test_query_tasks_by_key_result(auth_client):
    p = create_project(auth_client)
    # create an objective
    o = create_objective(auth_client, p)

    # create 2 key results for the same objective
    kr = create_key_result(auth_client, p, o)

    # create 2 tasks for the same key result
    t1 = create_task(auth_client, kr)
    t2 = create_task(auth_client, kr)

    # check if both tasks can be queried
    response = auth_client.get(f"key_results/{kr}/tasks")
    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert len(data) == 2

    ts = [t["id"] for t in data]
    assert t1 in ts
    assert t2 in ts


# Test 4: Query users by project ID
def test_query_users_by_project(auth_client):
    p = create_project(auth_client)

    # create 2 users
    u1 = create_user(auth_client, name="U1")
    u2 = create_user(auth_client, name="U2")

    # assign both users to the same project
    auth_client.post(f"/projects/{p}/users/{u1}?role=leader")
    auth_client.post(f"/projects/{p}/users/{u2}?role=member")

    # check if both users can be queried
    response = auth_client.get(f"projects/{p}/users")
    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert len(data) == 2

    us = [u["id"] for u in data]
    assert u1 in us
    assert u2 in us


# Test 5: Add user to project with role
def test_add_user_to_project(auth_client):
    p = create_project(auth_client)
    u = create_user(auth_client, name="U1")

    # assign user to project
    response = auth_client.post(f"/projects/{p}/users/{u}?role=member")
    assert response.status_code == HTTP_201_CREATED

    # check if the user was assigned correctly
    response = auth_client.get(f"/projects/{p}/users")
    data = response.json()
    assert u in [u["id"] for u in data]


# Test 6: Link objective to project
def test_link_objective_to_project(auth_client):
    # create a project and an objective independent from it
    p = create_project(auth_client)
    o = create_objective(auth_client, p)

    # link the objective to the project
    response = auth_client.post(f"/projects/{p}/objectives/{o}")
    assert response.status_code == HTTP_201_CREATED

    # check if the objective was assigned correctly
    response = auth_client.get(f"/projects/{p}/objectives")
    data = response.json()
    assert o in [o["id"] for o in data]


# Test 7: Link objective to objective
def test_link_objective_to_objective(auth_client):
    project_id = create_project(auth_client)
    parent_id = create_objective(auth_client, project_id)
    child_id = create_objective(auth_client, project_id)

    response = auth_client.post(f"/objectives/{parent_id}/children/{child_id}")
    assert response.status_code == 201

    response = auth_client.get("/objectives")
    objectives = response.json()
    assert child_id in [child_id["id"] for child_id in objectives]


def test_link_objective_to_objective_parent_not_found(auth_client):
    non_existing_parent_id = "00000000-0000-0000-0000-000000000000"
    project_id = create_project(auth_client)
    child_id = create_objective(auth_client, project_id)

    response = auth_client.post(
        f"/objectives/{non_existing_parent_id}/children/{child_id}"
    )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert "Objective not found" in response.text


def test_link_objective_to_objective_child_not_found(auth_client):
    project_id = create_project(auth_client)
    parent_id = create_objective(auth_client, project_id)
    non_existing_child_id = "00000000-0000-0000-0000-000000000000"

    response = auth_client.post(
        f"/objectives/{parent_id}/children/{non_existing_child_id}"
    )

    assert response.status_code == HTTP_404_NOT_FOUND
    assert "Objective not found" in response.text


def test_link_objective_to_itself(auth_client):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id, name="Objective Self Link")

    response = auth_client.post(f"/objectives/{objective_id}/children/{objective_id}")

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert response.json()["detail"] == "The objectives are the same"


def test_cyclical_linking(auth_client):
    project_id = create_project(auth_client)
    parent_id = create_objective(auth_client, project_id, name="Parent")
    child_id = create_objective(auth_client, project_id, name="Child")
    grandchild_id = create_objective(auth_client, project_id, name="Grandchild")

    # link parent -> child
    response = auth_client.post(f"/objectives/{parent_id}/children/{child_id}")
    assert response.status_code == HTTP_201_CREATED

    # link child -> grandchild
    response = auth_client.post(f"/objectives/{child_id}/children/{grandchild_id}")
    assert response.status_code == HTTP_201_CREATED

    # attempt to link grandchild -> parent (cycle)
    response = auth_client.post(f"/objectives/{grandchild_id}/children/{parent_id}")

    assert response.status_code == HTTP_400_BAD_REQUEST
    assert (
        response.json()["detail"]
        == "Linking these objectives would create a cyclical relationship"
    )
