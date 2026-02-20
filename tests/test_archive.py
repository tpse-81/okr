from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from utils import create_objective, create_project, create_key_result, create_task

import uuid

from app import app

app.debug = True


def test_archive_project(auth_client):
    p1 = create_project(auth_client)
    p2 = create_project(auth_client)
    o1 = create_objective(auth_client, p1)
    o2 = create_objective(auth_client, p1)

    # link o1 to p2
    auth_client.post(f"/projects/{p2}/objectives/{o1}")

    # create key results + tasks for both objectives
    kr1 = create_key_result(auth_client, o1)
    kr2 = create_key_result(auth_client, o2)
    t1 = create_task(auth_client, kr1)
    t2 = create_task(auth_client, kr2)

    # check if nothing is archived yet
    response = auth_client.get("/projects/archived")
    assert response.status_code == HTTP_200_OK
    archived_ids = {p["id"] for p in response.json()}
    assert p1 not in archived_ids
    assert p2 not in archived_ids

    response = auth_client.get("objectives/archived")
    assert response.status_code == HTTP_200_OK
    archived_ids = {o["id"] for o in response.json()}
    assert o1 not in archived_ids
    assert o2 not in archived_ids

    response = auth_client.get("/key_results/archived")
    assert response.status_code == HTTP_200_OK
    archived_kr_ids = {kr["id"] for kr in response.json()}
    assert kr1 not in archived_kr_ids
    assert kr2 not in archived_kr_ids

    response = auth_client.get("/tasks/archived")
    assert response.status_code == HTTP_200_OK
    archived_task_ids = {t["id"] for t in response.json()}
    assert t1 not in archived_task_ids
    assert t2 not in archived_task_ids

    # archive p1
    response = auth_client.patch(f"/projects/{p1}/archive?archive_reason=on_break")
    assert response.status_code == HTTP_200_OK

    # only p1 and o2 should be archived
    response = auth_client.get("/projects/archived")
    archived_ids = {p["id"] for p in response.json()}
    assert p1 in archived_ids
    assert p2 not in archived_ids

    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 not in archived_ids
    assert o2 in archived_ids

    # only kr2 / t2 should be archived now
    response = auth_client.get("/key_results/archived")
    assert response.status_code == HTTP_200_OK
    archived_kr_ids = {kr["id"] for kr in response.json()}
    assert kr1 not in archived_kr_ids
    assert kr2 in archived_kr_ids

    response = auth_client.get("/tasks/archived")
    assert response.status_code == HTTP_200_OK
    archived_task_ids = {t["id"] for t in response.json()}
    assert t1 not in archived_task_ids
    assert t2 in archived_task_ids

    # archive p2
    auth_client.patch(f"/projects/{p2}/archive?archive_reason=on_break")

    # everything should be archived
    response = auth_client.get("/projects/archived")
    archived_ids = {p["id"] for p in response.json()}
    assert p1 in archived_ids
    assert p2 in archived_ids

    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 in archived_ids
    assert o2 in archived_ids

    response = auth_client.get("/key_results/archived")
    archived_kr_ids = {kr["id"] for kr in response.json()}
    assert kr1 in archived_kr_ids
    assert kr2 in archived_kr_ids

    response = auth_client.get("/tasks/archived")
    archived_task_ids = {t["id"] for t in response.json()}
    assert t1 in archived_task_ids
    assert t2 in archived_task_ids

    # unarchive p2
    response = auth_client.patch(
        f"/projects/{p2}/unarchive?new_deadline=2025-08-13T10:05:00Z"
    )
    assert response.status_code == HTTP_200_OK

    # p2 and o1 should be unarchived again
    response = auth_client.get("/projects/archived")
    archived_ids = {p["id"] for p in response.json()}
    assert p1 in archived_ids
    assert p2 not in archived_ids

    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 not in archived_ids
    assert o2 in archived_ids

    # kr1/t1 active, kr2/t2 still archived
    response = auth_client.get("/key_results/archived")
    archived_kr_ids = {kr["id"] for kr in response.json()}
    assert kr1 not in archived_kr_ids
    assert kr2 in archived_kr_ids

    response = auth_client.get("/tasks/archived")
    archived_task_ids = {t["id"] for t in response.json()}
    assert t1 not in archived_task_ids
    assert t2 in archived_task_ids

    # unarchive p1
    response = auth_client.patch(
        f"/projects/{p1}/unarchive?new_deadline=2025-10-13T10:05:00Z"
    )
    assert response.status_code == HTTP_200_OK

    # Everything should be unarchived
    response = auth_client.get("/projects/archived")
    archived_ids = {p["id"] for p in response.json()}
    assert p1 not in archived_ids
    assert p2 not in archived_ids

    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 not in archived_ids
    assert o2 not in archived_ids

    response = auth_client.get("/key_results/archived")
    archived_kr_ids = {kr["id"] for kr in response.json()}
    assert kr1 not in archived_kr_ids
    assert kr2 not in archived_kr_ids

    response = auth_client.get("/tasks/archived")
    archived_task_ids = {t["id"] for t in response.json()}
    assert t1 not in archived_task_ids
    assert t2 not in archived_task_ids


def test_archive_project_not_exist(auth_client):
    non_existing_project = str(uuid.uuid4())

    # archive the project
    response = auth_client.patch(
        f"/projects/{non_existing_project}/archive?archive_reason=on_break"
    )
    assert response.status_code == HTTP_404_NOT_FOUND

    # unarchive the project
    response = auth_client.patch(
        f"/projects/{non_existing_project}/unarchive?new_deadline=2025-08-13T10:05:00Z"
    )
    assert response.status_code == HTTP_404_NOT_FOUND


def test_link_archived_objective_to_unarchived_project(auth_client):
    p1 = create_project(auth_client)
    p2 = create_project(auth_client)
    o1 = create_objective(auth_client, p1)

    # archive p1 and o1 by proxy
    auth_client.patch(f"/projects/{p1}/archive?archive_reason=on_break")

    # make sure o1 is archived
    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 in archived_ids

    # linking o1 to p2 should make o1 unarchived
    auth_client.post(f"/projects/{p2}/objectives/{o1}")

    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 not in archived_ids


def test_delete_project_unarchived_objective(auth_client):
    p1 = create_project(auth_client)
    p2 = create_project(auth_client)
    p3 = create_project(auth_client)
    o1 = create_objective(auth_client, p1)
    o2 = create_objective(auth_client, p3)

    # link o2 to o1
    auth_client.post(f"/objectives/{o1}/children/{o2}")

    # link o1 to p2
    auth_client.post(f"/projects/{p2}/objectives/{o1}")

    # archive p2 and p3
    auth_client.patch(f"/projects/{p2}/archive?archive_reason=on_break")
    auth_client.patch(f"/projects/{p3}/archive?archive_reason=on_break")

    # only p2 and p3 should be archived
    response = auth_client.get("/projects/archived")
    archived_ids = {p["id"] for p in response.json()}
    assert p1 not in archived_ids
    assert p2 in archived_ids
    assert p3 in archived_ids

    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 not in archived_ids
    assert o2 not in archived_ids

    # deleting p1 should archive o1 and o2
    auth_client.delete(f"/projects/{p1}")

    response = auth_client.get("/projects/archived")
    archived_ids = {p["id"] for p in response.json()}
    assert p2 in archived_ids

    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 in archived_ids
    assert o2 in archived_ids


def test_link_archived_objective_to_unarchived_objective(auth_client):
    p1 = create_project(auth_client)
    p2 = create_project(auth_client)
    o1 = create_objective(auth_client, p1)
    o2 = create_objective(auth_client, p2)
    o3 = create_objective(auth_client, p1)

    # link o3 to o1
    auth_client.post(f"/objectives/{o1}/children/{o3}")

    # archive p1 and o1, o3 by proxy
    auth_client.patch(f"/projects/{p1}/archive?archive_reason=on_break")

    # make sure o1 and o3 are archived
    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 in archived_ids
    assert o2 not in archived_ids
    assert o3 in archived_ids

    # linking o1 to o2 should make o1 and o3 unarchived (o3 -> o1 -> o2)
    auth_client.post(f"/objectives/{o2}/children/{o1}")

    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 not in archived_ids
    assert o2 not in archived_ids
    assert o3 not in archived_ids


def test_delete_parent_objective(auth_client):
    p1 = create_project(auth_client)
    p2 = create_project(auth_client)
    o1 = create_objective(auth_client, p1)
    o2 = create_objective(auth_client, p2)

    # link o2 to o1
    auth_client.post(f"/objectives/{o1}/children/{o2}")

    # archive p2
    auth_client.patch(f"/projects/{p2}/archive?archive_reason=on_break")

    # only p2 should be archived
    response = auth_client.get("/projects/archived")
    archived_ids = {p["id"] for p in response.json()}
    assert p1 not in archived_ids
    assert p2 in archived_ids

    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 not in archived_ids
    assert o2 not in archived_ids

    # delete o1
    auth_client.delete(f"/objectives/{o1}")

    # o2 should be unarchived now
    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o2 not in archived_ids
