from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class EmailWatchConfigUpdate(BaseModel):
    outlook_ordner_id: str = Field(min_length=1)
    outlook_ordner_name: str = Field(min_length=1, max_length=300)
    aktiv: bool = True
    polling_intervall_minuten: int = Field(default=10, ge=1, le=1440)


class EmailWatchConfigRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    project_id: int
    outlook_ordner_id: str
    outlook_ordner_name: str
    aktiv: bool
    polling_intervall_minuten: int
    letzte_abfrage_am: datetime | None
    letzter_fehler: str | None


class MailFolderRead(BaseModel):
    id: str
    name: str


class OAuthLoginUrlRead(BaseModel):
    authorization_url: str


class OAuthStatusRead(BaseModel):
    connected: bool
    account_email: str | None
    access_token_expires_am: datetime | None
