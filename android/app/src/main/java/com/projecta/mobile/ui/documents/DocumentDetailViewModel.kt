package com.projecta.mobile.ui.documents

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.dto.DocumentDto
import com.projecta.mobile.data.dto.DocumentStatus
import com.projecta.mobile.data.dto.DocumentType
import com.projecta.mobile.data.dto.DocumentUpdateRequestDto
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

data class DocumentDetailUiState(
    val isLoading: Boolean = true,
    val document: DocumentDto? = null,
    val errorMessage: String? = null,
    val isEditing: Boolean = false,
    val editTyp: DocumentType = DocumentType.NOTIZ,
    val editTitel: String = "",
    val editInhalt: String = "",
    val editDokumentdatum: String = "",
    val isSaving: Boolean = false,
    val savedMessage: String? = null,
    val showDeleteConfirm: Boolean = false,
    val isDeleting: Boolean = false,
    val isReindexing: Boolean = false,
)

// Schritt 5/6/7 (siehe Briefing): aus der reinen Leseansicht wird bei Bedarf
// ein editierbares Formular; Loeschen und Neu-Indexieren kommen auf demselben
// Screen dazu. PATCH schickt nur tatsaechlich geaenderte Felder (siehe
// DocumentUpdateRequestDto), analog zur Web-Bearbeitung.
class DocumentDetailViewModel(
    private val projectId: Int,
    private val documentId: Int,
    private val documentRepository: DocumentRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(DocumentDetailUiState())
    val uiState: StateFlow<DocumentDetailUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        _uiState.update { it.copy(isLoading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val result = documentRepository.getDocument(projectId, documentId)) {
                is ApiResult.Success -> _uiState.update { it.copy(isLoading = false, document = result.data) }
                is ApiResult.Error -> _uiState.update { it.copy(isLoading = false, errorMessage = result.message) }
            }
        }
    }

    fun startEditing() {
        val document = _uiState.value.document ?: return
        _uiState.update {
            it.copy(
                isEditing = true,
                editTyp = document.typ,
                editTitel = document.titel,
                editInhalt = document.inhalt ?: "",
                editDokumentdatum = document.dokumentdatum ?: "",
                savedMessage = null,
                errorMessage = null,
            )
        }
    }

    fun cancelEditing() = _uiState.update { it.copy(isEditing = false, errorMessage = null) }

    fun onEditTypChange(typ: DocumentType) = _uiState.update { it.copy(editTyp = typ) }
    fun onEditTitelChange(value: String) = _uiState.update { it.copy(editTitel = value) }
    fun onEditInhaltChange(value: String) = _uiState.update { it.copy(editInhalt = value) }
    fun onEditDokumentdatumChange(value: String) = _uiState.update { it.copy(editDokumentdatum = value) }

    fun save() {
        val state = _uiState.value
        val original = state.document ?: return
        if (state.editTitel.isBlank() || state.editInhalt.isBlank()) {
            _uiState.update { it.copy(errorMessage = "Titel und Inhalt duerfen nicht leer sein.") }
            return
        }

        val request = DocumentUpdateRequestDto(
            titel = state.editTitel.trim().takeIf { it != original.titel },
            inhalt = state.editInhalt.trim().takeIf { it != (original.inhalt ?: "") },
            typ = state.editTyp.takeIf { it != original.typ },
            dokumentdatum = state.editDokumentdatum.takeIf {
                it.isNotBlank() && it != (original.dokumentdatum ?: "")
            },
        )

        _uiState.update { it.copy(isSaving = true, errorMessage = null) }
        viewModelScope.launch {
            when (val result = documentRepository.updateDocument(projectId, documentId, request)) {
                is ApiResult.Success -> _uiState.update {
                    it.copy(isSaving = false, isEditing = false, document = result.data, savedMessage = "Gespeichert.")
                }
                is ApiResult.Error -> _uiState.update { it.copy(isSaving = false, errorMessage = result.message) }
            }
        }
    }

    fun requestDelete() = _uiState.update { it.copy(showDeleteConfirm = true) }
    fun dismissDeleteConfirm() = _uiState.update { it.copy(showDeleteConfirm = false) }

    // Blockiert serverseitig, wenn das Dokument ein Meeting-Pflichtprotokoll
    // ist (siehe document_service.delete_document) - die Fehlermeldung kommt
    // 1:1 vom Server ueber ApiResult.Error und wird hier nur angezeigt, kein
    // eigenes Regelwissen ueber Meetings noetig. Task-Verknuepfungen werden
    // serverseitig automatisch mitentfernt (kein Nutzerhinweis noetig).
    fun delete(onDeleted: () -> Unit) {
        val document = _uiState.value.document ?: return
        _uiState.update { it.copy(isDeleting = true, showDeleteConfirm = false, errorMessage = null) }
        viewModelScope.launch {
            when (val result = documentRepository.deleteDocument(projectId, document.id)) {
                is ApiResult.Success -> onDeleted()
                is ApiResult.Error -> _uiState.update { it.copy(isDeleting = false, errorMessage = result.message) }
            }
        }
    }

    // "Neu indexieren" (siehe Briefing Punkt 7) - stoesst den Reprocess an und
    // pollt danach denselben Status wie beim Foto-Review (siehe
    // PhotoUploadViewModel), bis das Dokument die Indexierung verlassen hat.
    fun reindex() {
        _uiState.update { it.copy(isReindexing = true, errorMessage = null, savedMessage = null) }
        viewModelScope.launch {
            when (val result = documentRepository.reprocessDocument(projectId, documentId)) {
                is ApiResult.Success -> {
                    _uiState.update { it.copy(document = result.data) }
                    pollUntilSettled()
                }
                is ApiResult.Error -> _uiState.update { it.copy(isReindexing = false, errorMessage = result.message) }
            }
        }
    }

    private suspend fun pollUntilSettled() {
        repeat(30) {
            delay(2000)
            when (val result = documentRepository.getDocument(projectId, documentId)) {
                is ApiResult.Success -> {
                    val document = result.data
                    _uiState.update { it.copy(document = document) }
                    if (document.status !in ACTIVE_INDEXING_STATUSES) {
                        _uiState.update {
                            it.copy(
                                isReindexing = false,
                                savedMessage = if (document.status == DocumentStatus.READY) "Neu indexiert." else null,
                                errorMessage = document.fehlermeldung,
                            )
                        }
                        return
                    }
                }
                is ApiResult.Error -> {
                    _uiState.update { it.copy(isReindexing = false, errorMessage = result.message) }
                    return
                }
            }
        }
        _uiState.update {
            it.copy(isReindexing = false, errorMessage = "Indexierung dauert ungewoehnlich lange - spaeter pruefen.")
        }
    }
}
