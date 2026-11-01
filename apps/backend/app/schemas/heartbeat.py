from datetime import datetime

from pydantic import BaseModel


class HeartbeatResponse(BaseModel):
    status: str
    server_id: int
    last_seen_at: datetime
