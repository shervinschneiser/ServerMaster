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
