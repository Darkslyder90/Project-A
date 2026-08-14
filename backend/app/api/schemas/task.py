from datetime import date

from pydantic import BaseModel, ConfigDict, Field

from app.db.models.enums import TaskStatus


class TaskCreate(BaseModel):
    titel: str = Field(min_length=1, max_length=300)
    beschreibung: str | None = None
    status: TaskStatus = TaskStatus.OFFEN
    zugewiesen_an: int | None = None
    faellig_am: date | None = None
    dokument_ids: list[int] = Field(default_factory=list)


class TaskUpdate(BaseModel):
    titel: str | None = Field(default=None, min_length=1, max_length=300)
    beschreibung: str | None = None
    status: TaskStatus | None = None
    zugewiesen_an: int | None = None
    faellig_am: date | None = None


class TaskRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    project_id: int
    titel: str
    beschreibung: str | None
    status: TaskStatus
    zugewiesen_an: int | None
    faellig_am: date | None
    dokument_ids: list[int]
