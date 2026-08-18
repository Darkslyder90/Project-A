import enum


class DocumentType(str, enum.Enum):
    MEETING = "meeting"
    SYSTEMEINSTELLUNG = "systemeinstellung"
    PROZESS = "prozess"
    NOTIZ = "notiz"
    DATEI = "datei"
    BILD = "bild"
    SONSTIGES = "sonstiges"
    EMAIL = "email"


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    REVIEW_REQUIRED = "review_required"
    INDEXING = "indexing"
    READY = "ready"
    FAILED = "failed"


class TaskStatus(str, enum.Enum):
    OFFEN = "offen"
    IN_ARBEIT = "in_arbeit"
    ERLEDIGT = "erledigt"


class ChatRole(str, enum.Enum):
    USER = "user"
    ASSISTANT = "assistant"


class ApiUsagePurpose(str, enum.Enum):
    CHAT = "chat"
    IMAGE_ANALYSIS = "image_analysis"
    DOCUMENT_SUMMARY = "document_summary"


class RebuildStatus(str, enum.Enum):
    IDLE = "idle"
    REBUILDING = "rebuilding"
    FAILED = "failed"
