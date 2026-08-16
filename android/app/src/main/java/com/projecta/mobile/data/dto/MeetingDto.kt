package com.projecta.mobile.data.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class MeetingCreateRequestDto(
    val datum: String,
    @SerialName("document_id") val documentId: Int? = null,
    val zusammenfassung: String? = null,
    @SerialName("teilnehmer_ids") val teilnehmerIds: List<Int> = emptyList(),
)

@Serializable
data class MeetingDto(
    val id: Int,
    @SerialName("project_id") val projectId: Int,
    val datum: String,
    @SerialName("document_id") val documentId: Int? = null,
    val zusammenfassung: String? = null,
    @SerialName("teilnehmer_ids") val teilnehmerIds: List<Int> = emptyList(),
)
