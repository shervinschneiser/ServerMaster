from datetime import UTC, datetime

from app.schemas.heartbeat import HeartbeatResponse


def test_heartbeat_response_schema() -> None:
    now = datetime.now(UTC)

    response = HeartbeatResponse(
        status="ok",
        server_id=1,
        last_seen_at=now,
    )

    assert response.status == "ok"
    assert response.server_id == 1
    assert response.last_seen_at == now
