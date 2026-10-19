from pydantic import BaseModel, ConfigDict, Field, field_validator


class ServerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=100)
    hostname: str = Field(min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "hostname")
    @classmethod
    def reject_blank_values(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value


class ServerUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=100)
    hostname: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = Field(default=None, max_length=2000)

    @field_validator("name", "hostname")
    @classmethod
    def reject_blank_values(cls, value: str | None) -> str | None:
        if value is None:
            return value

        value = value.strip()
        if not value:
            raise ValueError("Value cannot be blank")
        return value


class ServerResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    hostname: str
    description: str | None
