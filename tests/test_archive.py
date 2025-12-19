from litestar.status_codes import HTTP_200_OK, HTTP_404_NOT_FOUND
from utils import create_objective, create_project

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

    # unarchive p2
    response = auth_client.patch(f"/projects/{p2}/unarchive?new_deadline=10")
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

    # unarchive p1
    response = auth_client.patch(f"/projects/{p1}/unarchive?new_deadline=5")
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


def test_archive_project_not_exist(auth_client):
    non_existing_project = str(uuid.uuid4())

    # archive the project
    response = auth_client.patch(
        f"/projects/{non_existing_project}/archive?archive_reason=on_break"
    )
    assert response.status_code == HTTP_404_NOT_FOUND

    # unarchive the project
    response = auth_client.patch(
        f"/projects/{non_existing_project}/unarchive?new_deadline=5"
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


def test_link_archived_objective_to_unarchived_objective(auth_client):
    p1 = create_project(auth_client)
    p2 = create_project(auth_client)
    o1 = create_objective(auth_client, p1)
    o2 = create_objective(auth_client, p2)

    # archive p1 and o1 by proxy
    auth_client.patch(f"/projects/{p1}/archive?archive_reason=on_break")

    # make sure o1 is archived
    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 in archived_ids
    assert o2 not in archived_ids

    # linking o1 to o2 should make o1 unarchived
    response = auth_client.post(f"/objectives/{o2}/children/{o1}")

    response = auth_client.get("objectives/archived")
    archived_ids = {o["id"] for o in response.json()}
    assert o1 not in archived_ids
    assert o2 not in archived_ids
