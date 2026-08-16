package com.projecta.mobile.data.repository

import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.api.ApiSession
import com.projecta.mobile.data.dto.ProjectDto
import com.projecta.mobile.data.api.apiCall

class ProjectRepository(private val session: ApiSession) {
    suspend fun listProjects(): ApiResult<List<ProjectDto>> = apiCall { session.projectApi.listProjects() }
}
