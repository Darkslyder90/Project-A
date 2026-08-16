package com.projecta.mobile.data.api

import com.projecta.mobile.data.dto.MeetingCreateRequestDto
import com.projecta.mobile.data.dto.MeetingDto
import retrofit2.http.Body
import retrofit2.http.POST
import retrofit2.http.Path

interface MeetingApi {
    @POST("api/projects/{projectId}/meetings")
    suspend fun createMeeting(
        @Path("projectId") projectId: Int,
        @Body request: MeetingCreateRequestDto,
    ): MeetingDto
}
