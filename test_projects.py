from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST
from litestar.testing import TestClient

from app import app

app.debug = True


def test_project_check():
    with TestClient(app=app) as client:
        response = client.get("/projects/create?name=name&deadline=5&creation_date=10")
        assert response.status_code == HTTP_200_OK
        assert response.json() == {"message": "successfully created project"}

        response = client.get("/projects")
        assert response.status_code == HTTP_200_OK
        t = response.json()[0]
        assert t["creation_date"] == 10
        assert t["name"] == "name"
        assert t["deadline"] == 5


def test_empty_project_check():
    with TestClient(app=app) as client:
        response = client.get("/projects/create?name=name&deadline=5&creation_date=")
        assert response.status_code == HTTP_400_BAD_REQUEST

        response = client.get("/projects")
        assert response.status_code == HTTP_200_OK
        assert len(response.json()) == 0
