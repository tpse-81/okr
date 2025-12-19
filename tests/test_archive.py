from litestar.status_codes import (
    HTTP_200_OK,
)
from utils import create_objective, create_project

from app import app

app.debug = True


def archived_project_ids(auth_client) -> set[str]:
    response = auth_client.get("/projects/archived")
    assert response.status_code == HTTP_200_OK
    return {p["id"] for p in response.json()}


def archived_objective_ids(auth_client) -> set[str]:
    response = auth_client.get("/objectives/archived")
    assert response.status_code == HTTP_200_OK
    return {o["id"] for o in response.json()}


def test_extend_project_deadline(auth_client):
    p_id = create_project(auth_client, "DeadlineP")

    # Set new deadline (from 5 to 100)
    response = auth_client.patch(f"/projects/{p_id}/deadline/extend?new_deadline=100")

    assert response.status_code == HTTP_200_OK

    response = auth_client.get("/projects")
    data = response.json()
    project = next(p for p in data if p["id"] == p_id)
    assert project["deadline"] == 100


def test_archive_toggle(auth_client):
    p = create_project(auth_client, name="P1")
    o = create_objective(auth_client, p, name="O1")

    # check if nothing is archived yet
    assert archived_project_ids(auth_client) == set()
    assert archived_objective_ids(auth_client) == set()

    # toggle P1 should make both archived
    response = auth_client.patch(f"/projects/{p}/archive_toggle")
    assert response.status_code == HTTP_200_OK
    assert archived_project_ids(auth_client) == {p}
    assert archived_objective_ids(auth_client) == {o}

    # toggle P1 again should make both not archived
    response = auth_client.patch(f"/projects/{p}/archive_toggle")
    assert response.status_code == HTTP_200_OK
    assert archived_project_ids(auth_client) == set()
    assert archived_objective_ids(auth_client) == set()

    """
    More complex tests run locally but cannot be built, e.g.

    p1 = create_project(auth_client, name="P1")
    p2 = create_project(auth_client, name="P2")

    response = auth_client.patch(f"/projects/{XYZ}/archive_toggle")

    will always toggle project P1 no matter what project_id you enter for XYZ
    
    """
