from utils import (
    create_project,
    create_objective,
    create_key_result,
    create_task,
    create_user,
    login,
)
from litestar.status_codes import (
    HTTP_204_NO_CONTENT,
    HTTP_404_NOT_FOUND,
    HTTP_403_FORBIDDEN,
)

import uuid

from app import app


app.debug = True


# Test1: delete project
def test_delete_project(auth_client):
    p = create_project(auth_client)

    # delete the project
    response = auth_client.delete(f"/projects/{p}")
    assert response.status_code == HTTP_204_NO_CONTENT

    response = auth_client.get("/projects")
    pids = {p["id"] for p in response.json()}
    assert p not in pids


# Test 2: delete objective
def test_delete_objective(auth_client):
    p1 = create_project(auth_client)
    p2 = create_project(auth_client)
    o1 = create_objective(auth_client, p1)
    o2 = create_objective(auth_client, p1)

    # link o1 to p2
    auth_client.post(f"/projects/{p2}/objectives/{o1}")

    # deleting p1 should only delete o2
    auth_client.delete(f"/projects/{p1}")

    response = auth_client.get("/objectives")
    oids = {o["id"] for o in response.json()}
    assert o1 in oids
    assert o2 not in oids

    # delete o1
    response = auth_client.delete(f"/objectives/{o1}")
    assert response.status_code == HTTP_204_NO_CONTENT

    response = auth_client.get("/objectives")
    oids = {o["id"] for o in response.json()}
    assert oids == set()


# Test 3: delete key results
def test_delete_key_results(auth_client):
    p = create_project(auth_client)
    o = create_objective(auth_client, p)
    k1 = create_key_result(auth_client, o)
    k2 = create_key_result(auth_client, o)

    # delete k1 manually
    response = auth_client.delete(f"/key_results/{k1}")
    assert response.status_code == HTTP_204_NO_CONTENT

    response = auth_client.get("/key_results")
    kids = {k["id"] for k in response.json()}
    assert k1 not in kids
    assert k2 in kids

    # deleting o should automatically delete k2
    auth_client.delete(f"/objectives/{o}")

    response = auth_client.get("/key_results")
    kids = {k["id"] for k in response.json()}
    assert kids == set()


# Test 4: delete tasks
def test_delete_tasks(auth_client):
    p = create_project(auth_client)
    o = create_objective(auth_client, p)
    k = create_key_result(auth_client, o)
    t1 = create_task(auth_client, k)
    t2 = create_task(auth_client, k)

    # delete t1 manually
    response = auth_client.delete(f"/tasks/{t1}")
    assert response.status_code == HTTP_204_NO_CONTENT

    response = auth_client.get(f"/key_results/{k}/tasks")
    tids = {t["id"] for t in response.json()}
    assert t1 not in tids
    assert t2 in tids

    # deleting k should automatically delete t2
    auth_client.delete(f"/key_results/{k}")

    # This test only works because get_tasks_from_key_result does not check if the key result exists
    response = auth_client.get(f"/key_results/{k}/tasks")
    kids = {k["id"] for k in response.json()}
    assert kids == set()


# Test 5: delete empty bodies
def test_delete_empty(auth_client):
    non_existing_id = uuid.uuid4()

    response = auth_client.delete(f"/projects/{non_existing_id}")
    assert response.status_code == HTTP_404_NOT_FOUND

    response = auth_client.delete(f"/objectives/{non_existing_id}")
    assert response.status_code == HTTP_404_NOT_FOUND

    response = auth_client.delete(f"/key_results/{non_existing_id}")
    assert response.status_code == HTTP_404_NOT_FOUND

    response = auth_client.delete(f"/tasks/{non_existing_id}")
    assert response.status_code == HTTP_404_NOT_FOUND

    response = auth_client.delete(f"/users/{non_existing_id}")
    assert response.status_code == HTTP_404_NOT_FOUND


# Test 6: delete linked objective
def test_delete_linked_objective(auth_client):
    p1 = create_project(auth_client)
    p2 = create_project(auth_client)
    o1 = create_objective(auth_client, p1)
    o2 = create_objective(auth_client, p2)
    o3 = create_objective(auth_client, p2)

    # link o2 (child) to o1 (parent) and o3 to o2
    auth_client.post(f"/objectives/{o1}/children/{o2}")
    auth_client.post(f"/objectives/{o2}/children/{o3}")

    # archive p2
    auth_client.patch(f"/projects/{p2}/archive?archive_reason=on_break")

    # delete o2
    auth_client.delete(f"/objectives/{o2}")

    # o3 should still be alive
    response = auth_client.get("/objectives")
    oids = {o["id"] for o in response.json()}
    assert o1 in oids
    assert o2 not in oids
    assert o3 in oids

    # check if o3 is still unarchived and thus connected to o1
    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 not in archived_ids
    assert o3 not in archived_ids


# Test 7: delete user
def test_delete_user(auth_client):
    u = create_user(auth_client, name="U1", password="testpassword123")

    # no permissions to delete other user because the current user is not the admin
    response = auth_client.delete(f"/users/{u}")
    assert response.status_code == HTTP_403_FORBIDDEN

    # user deletes its own account: should work successfully
    response = auth_client.delete(
        f"/users/{u}",
        cookies={
            "token": login(auth_client, username="U1", password="testpassword123")
        },
    )
    assert response.status_code == HTTP_204_NO_CONTENT

    # make sure the user is really deleted now
    response = auth_client.get("/users")
    uids = {user["id"] for user in response.json()}
    assert u not in uids
