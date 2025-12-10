from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED
from litestar.testing import TestClient
import pytest

from app import app

app.debug = True

@pytest.fixture()
def client():
    with TestClient(app=app) as client:
        yield client


# ----------------
# Helper Functions
# ----------------

# Helper function: Creates a project
@pytest.fixture()
def create_project(client):
      def _create(name="P1"):
            result = client.get("/projects/create", params = {
                  "name": name,
                  "deadline": 10,
                  "creation_date": 1
            })
            assert result.status_code == HTTP_200_OK
            return client.get("/projects").json()[-1]["id"]
      return _create


# Helper function: Creates an objective
@pytest.fixture()
def create_objective(client, create_project):
    def _create(project_id = None, name = "O1"):
            if project_id is None:
                  project_id = create_project()
            
            result = client.get("/objectives/create", params = {
                  "name": name,
                  "description": "desc_obj",
                  "project_id": project_id
            })
            assert result.status_code == HTTP_200_OK

            return client.get("/objectives").json()[-1]["id"]
    return _create


# Helper function: Creates a key result
@pytest.fixture()
def create_key_result(client, create_objective):
      def _create(objective_id = None, description = "desc_kr"):
            if objective_id is None:
                  objective_id = create_objective()

            result = client.get("/key_results/create", params = {
                  "objective_id": objective_id,
                  "description": description,
                  "start_value": 15,
                  "end_value": 10
            })
            assert result.status_code == HTTP_200_OK

            return client.get("/key_results").json()[-1]["id"]
      return _create


# Helper function: Creates a task
@pytest.fixture()
def create_task(client, create_key_result):
      def _create(key_result_id = None, description = "desc_t", task_state = "open"):
            if key_result_id is None:
                  key_result_id = create_key_result()
            
            result = client.get(f"/key_results/{key_result_id}/tasks/create", params = {
                  "description": description,
                  "task_state": task_state
            })
            assert result.status_code == HTTP_200_OK

            return client.get(f"/key_results/{key_result_id}/tasks").json()[-1]["id"]
      return _create


# Helper function: Create a user
@pytest.fixture()
def create_user(client):
      def _create(name = "user"):
            result = client.get("/users/create", params = {
                  "name": name,
                  "email": "test@mail.com",
                  "password": "test_pass"
            })
            assert result.status_code == HTTP_200_OK

            return client.get("/users").json()[-1]["id"]
      return _create


# ---------------
# Test functions
# ---------------

# Test 1: Query objectives by project ID
def test_query_objectives_by_project(client, create_project, create_objective):
      # create a project
      p = create_project()

      # create 2 objectives for the same project
      o1 = create_objective(p, name="O1")
      o2 = create_objective(p, name="O2")

      # check if both objectives can be queried
      response = client.get(f"/projects/{p}/objectives")
      assert response.status_code == HTTP_200_OK

      data = response.json()
      assert len(data) == 2

      names = [o["name"] for o in data]
      assert "O1" in names
      assert "O2" in names


# Test 2: Query key results by objective ID
def test_query_key_results_by_objective(client, create_objective, create_key_result):
      # create an objective
      o = create_objective()

      # create 2 key results for the same objective
      kr1 = create_key_result(o)
      kr2 = create_key_result(o)

      # check if both key results can be queried
      response = client.get(f"objectives/{o}/key_results")
      assert response.status_code == HTTP_200_OK

      data = response.json()
      assert len(data) == 2

      krs = [k["id"] for k in data]
      assert kr1 in krs
      assert kr2 in krs


# Test 3: Query tasks by key result ID
def test_query_tasks_by_key_result(client, create_key_result, create_task):
      # create a key result
      kr = create_key_result()

      # create 2 tasks for the same key result
      t1 = create_task(kr)
      t2 = create_task(kr)

      # check if both tasks can be queried
      response = client.get(f"key_results/{kr}/tasks")
      assert response.status_code == HTTP_200_OK

      data = response.json()
      assert len(data) == 2

      ts = [t["id"] for t in data]
      assert t1 in ts
      assert t2 in ts


# Test 4: Query users by project ID
def test_query_users_by_project(client, create_project, create_user):
      # create a project
      p = create_project()

      # create 2 users
      u1 = create_user(name="U1")
      u2 = create_user(name="U2")

      # assign both users to the same project
      client.post(f"/projects/{p}/users/{u1}?role=lead")
      client.post(f"/projects/{p}/users/{u2}?role=member")

      # check if both users can be queried
      response = client.get(f"projects/{p}/users")
      assert response.status_code == HTTP_200_OK

      data = response.json()
      assert len(data) == 2

      us = [u["id"] for u in data]
      assert u1 in us
      assert u2 in us


# Test 5: Add user to project with role
def test_add_user_to_project(client, create_project, create_user):
      # create a project and a user independent from it
      p = create_project()
      u = create_user()

      # assign user to project
      response = client.post(f"/projects/{p}/users/{u}?role=member")
      assert response.status_code == HTTP_201_CREATED

      # check if the user was assigned correctly
      response = client.get(f"/projects/{p}/users")
      data = response.json()
      assert u in [u["id"] for u in data]


# Test 6: Link objective to project
def test_link_objective_to_project(client, create_project, create_objective):
      # create a project and an objective independent from it
      p = create_project()
      o = create_objective()

      # link the objective to the project
      response = client.post(f"/projects/{p}/objectives/{o}")
      assert response.status_code == HTTP_201_CREATED

      # check if the objective was assigned correctly
      response = client.get(f"/projects/{p}/objectives")
      data = response.json()
      assert o in [o["id"] for o in data]



