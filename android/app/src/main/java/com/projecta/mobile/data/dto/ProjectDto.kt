package com.projecta.mobile.data.dto

import kotlinx.serialization.SerialName
import kotlinx.serialization.Serializable

// Spiegelt backend/app/api/schemas/project.py::ProjectRead 1:1.
@Serializable
data class ProjectDto(
    val id: Int,
    val name: String,
    val beschreibung: String? = null,
    @SerialName("erstellt_am") val erstelltAm: String,
)
