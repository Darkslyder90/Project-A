package com.projecta.mobile.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.dto.ChatConversationDto
import com.projecta.mobile.data.dto.ChatMessageDto
import com.projecta.mobile.data.repository.ChatRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ChatUiState(
    val isLoading: Boolean = true,
    val conversations: List<ChatConversationDto> = emptyList(),
    val selectedConversationId: Int? = null,
    val selectedConversationTitel: String? = null,
    val messages: List<ChatMessageDto> = emptyList(),
    val messageDraft: String = "",
    val isSending: Boolean = false,
    val errorMessage: String? = null,
)

// Schritt 2 (siehe Briefing-Reihenfolge): Senden kommt hinzu. Kein lokales
// Caching/keine eigene Nachrichten-Zusammensetzung (siehe Briefing
// "Kein eigenes Datenmodell") - nach dem Senden wird die Unterhaltung immer
// frisch vom Server nachgeladen statt die neue Nachricht lokal anzuhaengen.
class ChatViewModel(
    private val projectId: Int,
    private val chatRepository: ChatRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    init {
        loadConversations()
    }

    fun loadConversations() {
        viewModelScope.launch { refreshConversations() }
    }

    fun selectConversation(conversationId: Int) {
        viewModelScope.launch { loadConversationDetail(conversationId) }
    }

    fun onMessageDraftChange(value: String) {
        _uiState.update { it.copy(messageDraft = value) }
    }

    fun sendMessage() {
        val query = _uiState.value.messageDraft.trim()
        if (query.isBlank() || _uiState.value.isSending) return

        _uiState.update { it.copy(isSending = true, errorMessage = null) }
        viewModelScope.launch {
            var conversationId = _uiState.value.selectedConversationId
            if (conversationId == null) {
                when (val created = chatRepository.createConversation(projectId)) {
                    is ApiResult.Success -> conversationId = created.data.id
                    is ApiResult.Error -> {
                        _uiState.update { it.copy(isSending = false, errorMessage = created.message) }
                        return@launch
                    }
                }
            }

            when (val result = chatRepository.sendMessage(projectId, conversationId!!, query)) {
                is ApiResult.Success -> {
                    _uiState.update { it.copy(messageDraft = "") }
                    refreshConversations()
                }
                is ApiResult.Error -> _uiState.update { it.copy(errorMessage = result.message) }
            }
            _uiState.update { it.copy(isSending = false) }
        }
    }

    private suspend fun refreshConversations() {
        _uiState.update { it.copy(isLoading = true, errorMessage = null) }
        when (val result = chatRepository.listConversations(projectId)) {
            is ApiResult.Success -> {
                val conversations = result.data.sortedByDescending { it.zuletztAktualisiertAm }
                _uiState.update { it.copy(conversations = conversations) }
                val mostRecent = conversations.firstOrNull()
                if (mostRecent != null) {
                    loadConversationDetail(mostRecent.id)
                } else {
                    _uiState.update { it.copy(isLoading = false) }
                }
            }
            is ApiResult.Error -> _uiState.update { it.copy(isLoading = false, errorMessage = result.message) }
        }
    }

    private suspend fun loadConversationDetail(conversationId: Int) {
        _uiState.update { it.copy(isLoading = true, errorMessage = null, selectedConversationId = conversationId) }
        when (val result = chatRepository.getConversation(projectId, conversationId)) {
            is ApiResult.Success -> _uiState.update {
                it.copy(
                    isLoading = false,
                    selectedConversationTitel = result.data.titel,
                    messages = result.data.nachrichten,
                )
            }
            is ApiResult.Error -> _uiState.update { it.copy(isLoading = false, errorMessage = result.message) }
        }
    }
}
