from httpx import ASGITransport, AsyncClient

from app.main import app


async def test_create_server() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.post(
            "/servers",
            json={
                "name": "Test Server",
                "hostname": "test-server.local",
                "description": "Test server",
            },
        )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == "Test Server"
    assert data["hostname"] == "test-server.local"
    assert data["description"] == "Test server"
    assert isinstance(data["id"], int)


async def test_get_server() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/servers",
            json={
                "name": "Detail Test Server",
                "hostname": "detail-test.local",
            },
        )
        assert create_response.status_code == 201

        server_id = create_response.json()["id"]
        response = await client.get(f"/servers/{server_id}")

    assert response.status_code == 200

    data = response.json()

    assert data["id"] == server_id
    assert data["name"] == "Detail Test Server"
    assert data["hostname"] == "detail-test.local"


async def test_get_server_not_found() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.get("/servers/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Server not found"}


async def test_delete_server() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/servers",
            json={
                "name": "Delete Test Server",
                "hostname": "delete-test.local",
            },
        )
        assert create_response.status_code == 201

        server_id = create_response.json()["id"]
        delete_response = await client.delete(f"/servers/{server_id}")
        get_response = await client.get(f"/servers/{server_id}")

    assert delete_response.status_code == 204
    assert get_response.status_code == 404


async def test_delete_server_not_found() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.delete("/servers/999999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Server not found"}


async def test_update_server() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        create_response = await client.post(
            "/servers",
            json={
                "name": "Before Update",
                "hostname": "update-test.local",
                "description": "Original description",
            },
        )
        assert create_response.status_code == 201
        server_id = create_response.json()["id"]

        update_response = await client.patch(
            f"/servers/{server_id}",
            json={"name": "After Update"},
        )

    assert update_response.status_code == 200
    data = update_response.json()
    assert data["name"] == "After Update"
    assert data["hostname"] == "update-test.local"
    assert data["description"] == "Original description"


async def test_update_server_not_found() -> None:
    transport = ASGITransport(app=app)

    async with AsyncClient(
        transport=transport,
        base_url="http://test",
    ) as client:
        response = await client.patch(
            "/servers/999999",
            json={"name": "Updated Name"},
        )

    assert response.status_code == 404
    assert response.json() == {"detail": "Server not found"}
