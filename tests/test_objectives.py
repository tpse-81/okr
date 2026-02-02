from litestar.testing import TestClient

from utils import create_project, create_objective
from litestar.status_codes import (
    HTTP_200_OK,
    HTTP_201_CREATED,
    HTTP_400_BAD_REQUEST,
    HTTP_401_UNAUTHORIZED,
)

from app import app


app.debug = True


def test_objective_check(auth_client):
    project_id = create_project(auth_client)
    params = {
        "name": "name",
        "description": "description",
    }

    response = auth_client.post(f"/projects/{project_id}/objectives", json=params)
    assert response.status_code == HTTP_201_CREATED
    assert response.json() == {"message": "successfully created objective"}

    response = auth_client.get("/objectives")
    assert response.status_code == HTTP_200_OK
    t = response.json()[0]
    assert t["description"] == "description"
    assert t["name"] == "name"


def test_empty_project_check(auth_client):
    response = auth_client.post("/projects/nonexistentid/objectives", json={"name": "name", "description": 5})
    assert response.status_code == HTTP_400_BAD_REQUEST

    response = auth_client.get("/objectives")
    assert response.status_code == HTTP_200_OK
    assert len(response.json()) == 1


def test_update_objective(auth_client):
    project_id = create_project(auth_client)
    objective_id = create_objective(auth_client, project_id)

    response = auth_client.patch(
        f"/objectives/{objective_id}", json={"name": "newname", "description": "newdescription"}
    )
    assert response.status_code == HTTP_200_OK

    response = auth_client.get("/objectives")
    assert response.status_code == HTTP_200_OK

    # check if new values have been saved
    objective = response.json()[-1]
    assert objective["name"] == "newname"
    assert objective["description"] == "newdescription"


def test_objective_check_unauthorized(auth_client):
    project_id = create_project(auth_client)
    with TestClient(app=app) as client:
        response = client.post(
            f"/projects/{project_id}/objectives",
            json={
                "name": "name",
                "description": "description",
            },
        )
        assert response.status_code == HTTP_401_UNAUTHORIZED
