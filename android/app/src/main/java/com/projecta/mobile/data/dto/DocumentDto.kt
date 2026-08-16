package com.projecta.mobile.data.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Spiegelt backend/app/db/models/enums.py::DocumentType. "datei"/"bild"
// kommen erst mit dem Foto-Upload-Schritt dazu, siehe DocumentApi.
@Serializable
enum class DocumentType {
    @SerialName("meeting") MEETING,
    @SerialName("systemeinstellung") SYSTEMEINSTELLUNG,
    @SerialName("prozess") PROZESS,
    @SerialName("notiz") NOTIZ,
    @SerialName("datei") DATEI,
    @SerialName("bild") BILD,
    @SerialName("sonstiges") SONSTIGES,
}

// Nur die Typen, die im "Neu anlegen"-Formular ohne Datei/Bild sinnvoll sind
// (siehe backend/app/api/schemas/document.py::MANUAL_DOCUMENT_TYPES).
val MANUAL_DOCUMENT_TYPES = listOf(
    DocumentType.NOTIZ,
    DocumentType.PROZESS,
    DocumentType.SYSTEMEINSTELLUNG,
    DocumentType.SONSTIGES,
)

@Serializable
enum class DocumentStatus {
    @SerialName("pending") PENDING,
    @SerialName("processing") PROCESSING,
    @SerialName("review_required") REVIEW_REQUIRED,
    @SerialName("indexing") INDEXING,
    @SerialName("ready") READY,
    @SerialName("failed") FAILED,
}

@Serializable
data class DocumentCreateRequestDto(
    val typ: DocumentType,
    val titel: String,
    val inhalt: String,
    val dokumentdatum: String? = null,
)

@Serializable
data class DocumentReviewRequestDto(val inhalt: String)

// Alle Felder optional (PATCH-Semantik, siehe DocumentUpdate im Backend) -
// nur tatsaechlich geaenderte Felder werden vom Client befuellt, der Rest
// bleibt beim Default null und wird dank Json{encodeDefaults=false} gar nicht
// erst mitgeschickt (siehe ApiClientFactory).
@Serializable
data class DocumentUpdateRequestDto(
    val titel: String? = null,
    val inhalt: String? = null,
    val typ: DocumentType? = null,
    val dokumentdatum: String? = null,
)

@Serializable
data class DocumentDto(
    val id: Int,
    @SerialName("project_id") val projectId: Int,
    val typ: DocumentType,
    val titel: String,
    val inhalt: String? = null,
    @SerialName("ocr_text") val ocrText: String? = null,
    @SerialName("ki_analyse_rohtext") val kiAnalyseRohtext: String? = null,
    val status: DocumentStatus,
    val fehlermeldung: String? = null,
    val dokumentdatum: String? = null,
    val dateiname: String? = null,
    @SerialName("erstellt_am") val erstelltAm: String,
    @SerialName("aktualisiert_am") val aktualisiertAm: String,
    @SerialName("tag_ids") val tagIds: List<Int> = emptyList(),
)
