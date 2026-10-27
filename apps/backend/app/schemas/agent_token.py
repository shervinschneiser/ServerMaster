from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AgentTokenResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    server_id: int
    created_at: datetime


class AgentTokenIssuedResponse(AgentTokenResponse):
    token: str
