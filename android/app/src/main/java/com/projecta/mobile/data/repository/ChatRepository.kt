package com.projecta.mobile.data.repository

import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.api.ApiSession
import com.projecta.mobile.data.api.apiCall
import com.projecta.mobile.data.dto.ChatConversationDetailDto
import com.projecta.mobile.data.dto.ChatConversationDto
import com.projecta.mobile.data.dto.SendMessageRequestDto
import com.projecta.mobile.data.dto.SendMessageResponseDto

class ChatRepository(private val session: ApiSession) {

    suspend fun listConversations(projectId: Int): ApiResult<List<ChatConversationDto>> =
        apiCall { session.chatApi.listConversations(projectId) }

    suspend fun createConversation(projectId: Int): ApiResult<ChatConversationDto> =
        apiCall { session.chatApi.createConversation(projectId) }

    suspend fun getConversation(projectId: Int, conversationId: Int): ApiResult<ChatConversationDetailDto> =
        apiCall { session.chatApi.getConversation(projectId, conversationId) }

    suspend fun sendMessage(projectId: Int, conversationId: Int, query: String): ApiResult<SendMessageResponseDto> =
        apiCall { session.chatApi.sendMessage(projectId, conversationId, SendMessageRequestDto(query)) }
}
