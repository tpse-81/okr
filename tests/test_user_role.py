from litestar.status_codes import HTTP_200_OK, HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND


from utils import create_project, create_user, app

import uuid

app.debug = True


# Test 1: Assign role to user, change role and then get role
def test_set_and_get_user_role(auth_client):
    p = create_project(auth_client)
    u = create_user(auth_client)

    # assign user to project with role member
    auth_client.post(f"/projects/{p}/users/{u}?role=member")

    # change user role to lead
    response = auth_client.patch(f"/projects/{p}/users/{u}/role?role=leader")
    assert response.status_code == HTTP_200_OK

    # get user role
    response = auth_client.get(f"/projects/{p}/users/{u}/role")
    assert response.status_code == HTTP_200_OK

    data = response.json()
    assert data == {"role": "leader"}


# Test 2: user not in project
def test_role_user_not_in_project(auth_client):
    p = create_project(auth_client)
    u = create_user(auth_client)

    # get user role from project
    response = auth_client.get(f"/projects/{p}/users/{u}/role")

    assert response.status_code == HTTP_404_NOT_FOUND

    # change user role to member from None (should not work since user is not assigned to project yet)
    response = auth_client.patch(f"/projects/{p}/users/{u}/role?role=member")
    assert response.status_code == HTTP_404_NOT_FOUND


# Test 3: project does not exist
def test_role_project_not_exist(auth_client):
    non_existing_project = str(uuid.uuid4())
    u = create_user(auth_client)

    # change user role to lead
    response = auth_client.patch(
        f"/projects/{non_existing_project}/users/{u}/role?role=leader"
    )
    assert response.status_code == HTTP_404_NOT_FOUND

    # get user role from project
    response = auth_client.get(f"/projects/{non_existing_project}/users/{u}/role")

    assert response.status_code == HTTP_404_NOT_FOUND


# Test 4: role does not exist
def test_invalid_role(auth_client):
    p = create_project(auth_client)
    u = create_user(auth_client)

    # assign user to project with role member
    auth_client.post(f"/projects/{p}/users/{u}?role=member")

    # change user role to not_real
    response = auth_client.patch(f"/projects/{p}/users/{u}/role?role=not_real")
    assert response.status_code == HTTP_400_BAD_REQUEST


# Test 5: user does not exist
def test_user_not_exist(auth_client):
    p = create_project(auth_client)
    non_existing_user = str(uuid.uuid4())

    # change user role to lead
    response = auth_client.patch(
        f"/projects/{p}/users/{non_existing_user}/role?role=leader"
    )
    assert response.status_code == HTTP_404_NOT_FOUND

    # get user role from project
    response = auth_client.get(f"/projects/{p}/users/{non_existing_user}/role")

    assert response.status_code == HTTP_404_NOT_FOUND
