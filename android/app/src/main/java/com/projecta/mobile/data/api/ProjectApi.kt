package com.projecta.mobile.data.api

import com.projecta.mobile.data.dto.ProjectDto
import retrofit2.http.GET

interface ProjectApi {
    @GET("api/projects")
    suspend fun listProjects(): List<ProjectDto>
}
