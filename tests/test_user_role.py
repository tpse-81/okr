from litestar.status_codes import HTTP_200_OK, HTTP_201_CREATED, HTTP_404_NOT_FOUND


# Test 1: Assign role to user, change role and then get role
def test_set_and_get_user_role(client, create_project, create_user):
    # create a project
    p = create_project("Project1")

    # create a user
    u = create_user("User1")

    # assign user to project with role member
    client.post(f"/projects/{p}/users/{u}?role=member")

    # change user role to lead
    response = client.post(f"/projects/{p}/users/{u}/role?role=lead")
    assert response.status_code == HTTP_201_CREATED

    # get user role
    response = client.get(f"/projects/{p}/users/{u}/role")
    assert response.status_code == HTTP_200_OK

    assert response.text == "lead"


# Test 2: user not in project
def test_get_role_user_not_in_project(client, create_project, create_user):
    #create a project
    p = create_project("Project2")

    # create a user
    u = create_user("User2")

    # get user role from project
    response = client.get(f"/projects/{p}/users/{u}/role")

    assert response.status_code == HTTP_200_OK
    assert response.json() is None