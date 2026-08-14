"""Importiert alle ORM-Modelle, damit Alembic-Autogenerate und Base.metadata
sie kennen. Reihenfolge ist wegen der Foreign-Key-Abhaengigkeiten nicht relevant -
SQLAlchemy loest das ueber die Mapper-Registry auf.
"""

from app.db.models.api_usage_log import ApiUsageLog
from app.db.models.app_settings import AppSettings
from app.db.models.chat import ChatConversation, ChatMessage
from app.db.models.chunk import Chunk
from app.db.models.document import Document, DocumentTag
from app.db.models.index_metadata import IndexMetadata
from app.db.models.meeting import Meeting, MeetingParticipant
from app.db.models.person import Person
from app.db.models.project import Project
from app.db.models.tag import Tag
from app.db.models.task import Task, TaskDocument

__all__ = [
    "ApiUsageLog",
    "AppSettings",
    "ChatConversation",
    "ChatMessage",
    "Chunk",
    "Document",
    "DocumentTag",
    "IndexMetadata",
    "Meeting",
    "MeetingParticipant",
    "Person",
    "Project",
    "Tag",
    "Task",
    "TaskDocument",
]
