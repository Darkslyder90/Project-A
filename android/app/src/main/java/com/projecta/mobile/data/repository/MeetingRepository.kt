package com.projecta.mobile.data.repository

import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.api.ApiSession
import com.projecta.mobile.data.api.apiCall
import com.projecta.mobile.data.dto.MeetingCreateRequestDto
import com.projecta.mobile.data.dto.MeetingDto

class MeetingRepository(private val session: ApiSession) {

    suspend fun createMeeting(
        projectId: Int,
        datum: String,
        documentId: Int?,
        zusammenfassung: String?,
        teilnehmerIds: List<Int>,
    ): ApiResult<MeetingDto> = apiCall {
        session.meetingApi.createMeeting(
            projectId,
            MeetingCreateRequestDto(
                datum = datum,
                documentId = documentId,
                zusammenfassung = zusammenfassung,
                teilnehmerIds = teilnehmerIds,
            ),
        )
    }
}
