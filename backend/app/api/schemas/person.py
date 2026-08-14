from pydantic import BaseModel, ConfigDict, Field


class PersonCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    rolle: str | None = None
    kontaktinfo: str | None = None
    notizen: str | None = None


class PersonUpdate(BaseModel):
    name: str | None = Field(default=None, min_length=1, max_length=200)
    rolle: str | None = None
    kontaktinfo: str | None = None
    notizen: str | None = None


class PersonRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    name: str
    rolle: str | None
    kontaktinfo: str | None
    notizen: str | None
