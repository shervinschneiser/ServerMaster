from pydantic import BaseModel, ConfigDict


class ServerCreate(BaseModel):
    name: str
    hostname: str
    description: str | None = None


class ServerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hostname: str
    description: str | None
