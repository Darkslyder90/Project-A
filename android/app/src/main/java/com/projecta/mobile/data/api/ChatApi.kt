package com.projecta.mobile.data.api

import com.projecta.mobile.data.dto.ChatConversationDetailDto
import com.projecta.mobile.data.dto.ChatConversationDto
import com.projecta.mobile.data.dto.SendMessageRequestDto
import com.projecta.mobile.data.dto.SendMessageResponseDto
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

interface ChatApi {
    @GET("api/projects/{projectId}/chat/conversations")
    suspend fun listConversations(@Path("projectId") projectId: Int): List<ChatConversationDto>

    @POST("api/projects/{projectId}/chat/conversations")
    suspend fun createConversation(@Path("projectId") projectId: Int): ChatConversationDto

    @GET("api/projects/{projectId}/chat/conversations/{conversationId}")
    suspend fun getConversation(
        @Path("projectId") projectId: Int,
        @Path("conversationId") conversationId: Int,
    ): ChatConversationDetailDto

    @POST("api/projects/{projectId}/chat/conversations/{conversationId}/messages")
    suspend fun sendMessage(
        @Path("projectId") projectId: Int,
        @Path("conversationId") conversationId: Int,
        @Body request: SendMessageRequestDto,
    ): SendMessageResponseDto
}
