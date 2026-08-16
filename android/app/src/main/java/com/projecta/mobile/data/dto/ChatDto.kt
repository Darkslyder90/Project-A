package com.projecta.mobile.data.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Spiegelt backend/app/api/schemas/chat.py 1:1.

@Serializable
data class ChatConversationDto(
    val id: Int,
    @SerialName("project_id") val projectId: Int,
    val titel: String? = null,
    @SerialName("erstellt_am") val erstelltAm: String,
    @SerialName("zuletzt_aktualisiert_am") val zuletztAktualisiertAm: String,
)

@Serializable
data class ChatSourceSnapshotDto(
    @SerialName("source_id") val sourceId: String,
    @SerialName("document_id") val documentId: Int,
    @SerialName("document_titel") val documentTitel: String,
    val dokumentdatum: String? = null,
    val abschnitt: String? = null,
    @SerialName("text_ausschnitt") val textAusschnitt: String,
    val geloescht: Boolean = false,
)

@Serializable
data class ChatMessageDto(
    val id: Int,
    @SerialName("conversation_id") val conversationId: Int,
    val rolle: String,
    val text: String,
    val quellen: List<ChatSourceSnapshotDto>? = null,
    @SerialName("erstellt_am") val erstelltAm: String,
)

@Serializable
data class ChatConversationDetailDto(
    val id: Int,
    @SerialName("project_id") val projectId: Int,
    val titel: String? = null,
    @SerialName("erstellt_am") val erstelltAm: String,
    @SerialName("zuletzt_aktualisiert_am") val zuletztAktualisiertAm: String,
    val nachrichten: List<ChatMessageDto>,
)

@Serializable
data class SendMessageRequestDto(val query: String)

@Serializable
data class SendMessageResponseDto(
    val conversation: ChatConversationDto,
    val nachricht: ChatMessageDto,
)
