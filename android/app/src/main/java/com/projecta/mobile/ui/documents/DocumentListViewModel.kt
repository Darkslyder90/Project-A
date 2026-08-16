package com.projecta.mobile.ui.documents

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.dto.DocumentDto
import com.projecta.mobile.data.dto.DocumentStatus
import com.projecta.mobile.data.repository.DocumentRepository
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

private val ACTIVE_INDEXING_STATUSES = setOf(
    DocumentStatus.PENDING,
    DocumentStatus.PROCESSING,
    DocumentStatus.INDEXING,
)

data class DocumentListUiState(
    val isLoading: Boolean = true,
    val documents: List<DocumentDto> = emptyList(),
    val errorMessage: String? = null,
    val isReindexingAll: Boolean = false,
    val showReindexAllConfirm: Boolean = false,
)

// Schritt 4 (siehe Briefing): bewusst nur eine schlichte Auswahl-/Sprungliste
// ohne Filter/Vorschaubilder/Sortier-UI - dient nur dazu, ein Dokument fuer
// Bearbeiten/Loeschen/Reindex zu finden (siehe Briefing "Nicht enthalten").
// Schritt 7 ergaenzt "Gesamtes Projekt neu indexieren" - ruft serverseitig
// reprocess-all auf (einfache Variante, kein Blue-Green-Rebuild, siehe
// document_service.reprocess_all_documents) und pollt danach, bis kein
// Dokument mehr in Bearbeitung ist.
class DocumentListViewModel(
    private val projectId: Int,
    private val documentRepository: DocumentRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(DocumentListUiState())
    val uiState: StateFlow<DocumentListUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        _uiState.update { it.copy(isLoading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val result = documentRepository.listDocuments(projectId)) {
                is ApiResult.Success -> _uiState.update {
                    it.copy(isLoading = false, documents = sorted(result.data))
                }
                is ApiResult.Error -> _uiState.update { it.copy(isLoading = false, errorMessage = result.message) }
            }
        }
    }

    fun requestReindexAll() = _uiState.update { it.copy(showReindexAllConfirm = true) }
    fun dismissReindexAllConfirm() = _uiState.update { it.copy(showReindexAllConfirm = false) }

    fun reindexAll() {
        _uiState.update { it.copy(isReindexingAll = true, showReindexAllConfirm = false, errorMessage = null) }
        viewModelScope.launch {
            when (val result = documentRepository.reprocessAllDocuments(projectId)) {
                is ApiResult.Success -> {
                    _uiState.update { it.copy(documents = sorted(result.data)) }
                    pollUntilAllSettled()
                }
                is ApiResult.Error -> _uiState.update { it.copy(isReindexingAll = false, errorMessage = result.message) }
            }
        }
    }

    private suspend fun pollUntilAllSettled() {
        repeat(30) {
            delay(2000)
            when (val result = documentRepository.listDocuments(projectId)) {
                is ApiResult.Success -> {
                    val documents = sorted(result.data)
                    _uiState.update { it.copy(documents = documents) }
                    if (documents.none { it.status in ACTIVE_INDEXING_STATUSES }) {
                        _uiState.update { it.copy(isReindexingAll = false) }
                        return
                    }
                }
                is ApiResult.Error -> {
                    _uiState.update { it.copy(isReindexingAll = false, errorMessage = result.message) }
                    return
                }
            }
        }
        _uiState.update {
            it.copy(
                isReindexingAll = false,
                errorMessage = "Neuindexierung dauert ungewoehnlich lange - spaeter pruefen.",
            )
        }
    }

    private fun sorted(documents: List<DocumentDto>) = documents.sortedByDescending { it.aktualisiertAm }
}
