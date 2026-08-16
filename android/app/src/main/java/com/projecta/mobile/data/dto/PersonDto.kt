package com.projecta.mobile.data.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

@Serializable
data class PersonCreateRequestDto(
    val name: String,
    val rolle: String? = null,
    val kontaktinfo: String? = null,
    val notizen: String? = null,
)

@Serializable
data class PersonDto(
    val id: Int,
    @SerialName("project_id") val projectId: Int,
    val name: String,
    val rolle: String? = null,
    val kontaktinfo: String? = null,
    val notizen: String? = null,
)
