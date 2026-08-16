package com.projecta.mobile.data.api

import com.projecta.mobile.data.dto.PersonCreateRequestDto
import com.projecta.mobile.data.dto.PersonDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface PersonApi {
    @GET("api/projects/{projectId}/people")
    suspend fun listPeople(@Path("projectId") projectId: Int): List<PersonDto>

    @POST("api/projects/{projectId}/people")
    suspend fun createPerson(
        @Path("projectId") projectId: Int,
        @Body request: PersonCreateRequestDto,
    ): PersonDto
}
