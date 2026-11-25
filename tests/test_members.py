import pytest

pytestmark = pytest.mark.integration


def test_members_full_crud_lifecycle(client, assert_problem):
    assert client.get("/members").json() == []
    created = client.post("/members", json={"name": " Ayesha ", "email": " AYESHA@example.com "})
    assert created.status_code == 201
    member = created.json()
    url = created.headers["Location"]
    assert url == f"/members/{member['id']}"
    assert member == {"id": member["id"], "name": "Ayesha", "email": "ayesha@example.com"}
    fetched = client.get(url)
    assert fetched.status_code == 200
    assert fetched.json() == member
    listed = client.get("/members")
    assert listed.status_code == 200
    assert listed.json() == [member]

    updated = client.put(url, json={"name": "Ayesha Rahman", "email": "reader@example.com"})
    assert updated.status_code == 200
    assert updated.json() == {"id": member["id"], "name": "Ayesha Rahman", "email": "reader@example.com"}
    assert client.get(url).json() == updated.json()
    deleted = client.delete(url)
    assert deleted.status_code == 204
    assert deleted.content == b""
    assert_problem(client.get(url), 404)
    assert client.get("/members").json() == []


def test_duplicate_email_create_and_update_are_conflicts(client, make_member, assert_problem):
    first = make_member()
    assert_problem(client.post("/members", json={"name": "Another", "email": first["email"].upper()}), 409)
    second = make_member(name="Second", email="second@example.com")
    url = f"/members/{second['id']}"
    assert_problem(client.put(url, json={"name": "Changed", "email": first["email"]}), 409)
    assert client.get(url).json() == second
    assert len(client.get("/members").json()) == 2


def test_member_can_keep_their_own_email(client, make_member):
    member = make_member()
    response = client.put(f"/members/{member['id']}", json={"name": "New name", "email": member["email"]})
    assert response.status_code == 200
    assert response.json()["name"] == "New name"


@pytest.mark.parametrize("payload,field", [
    ({"name": " ", "email": "reader@example.com"}, "name"),
    ({"name": "x" * 121, "email": "reader@example.com"}, "name"),
    ({"name": "Reader", "email": "invalid"}, "email"),
    ({"name": "Reader", "email": "a b@example.com"}, "email"),
    ({"name": "Reader", "email": "x" * 255}, "email"),
])
def test_member_validation(client, payload, field, assert_problem):
    body = assert_problem(client.post("/members", json=payload), 422)
    assert f"/{field}" in {error["pointer"] for error in body["errors"]}
    assert client.get("/members").json() == []


@pytest.mark.parametrize("method", ["get", "put", "delete"])
def test_missing_member_operations(client, method, assert_problem):
    kwargs = {}
    if method == "put":
        kwargs["json"] = {"name": "Reader", "email": "reader@example.com"}
    assert_problem(client.request(method, "/members/999", **kwargs), 404)


def test_invalid_member_update_is_not_saved(client, make_member, assert_problem):
    member = make_member()
    url = f"/members/{member['id']}"
    assert_problem(client.put(url, json={"name": "Changed", "email": "invalid"}), 422)
    assert client.get(url).json() == member
