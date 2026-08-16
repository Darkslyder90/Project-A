package com.projecta.mobile.data.repository

import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.api.ApiSession
import com.projecta.mobile.data.api.apiCall
import com.projecta.mobile.data.dto.PersonCreateRequestDto
import com.projecta.mobile.data.dto.PersonDto

class PersonRepository(private val session: ApiSession) {

    suspend fun listPeople(projectId: Int): ApiResult<List<PersonDto>> =
        apiCall { session.personApi.listPeople(projectId) }

    suspend fun createPerson(
        projectId: Int,
        name: String,
        rolle: String?,
        kontaktinfo: String?,
        notizen: String?,
    ): ApiResult<PersonDto> = apiCall {
        session.personApi.createPerson(
            projectId,
            PersonCreateRequestDto(name = name, rolle = rolle, kontaktinfo = kontaktinfo, notizen = notizen),
        )
    }
}
