package com.projecta.mobile.ui.create

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.dto.DocumentType
import com.projecta.mobile.data.repository.DocumentRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class DocumentFormUiState(
    val typ: DocumentType = DocumentType.NOTIZ,
    val titel: String = "",
    val inhalt: String = "",
    val isSaving: Boolean = false,
    val errorMessage: String? = null,
    val savedTitel: String? = null,
)

class DocumentFormViewModel(
    private val projectId: Int,
    private val documentRepository: DocumentRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(DocumentFormUiState())
    val uiState: StateFlow<DocumentFormUiState> = _uiState.asStateFlow()

    fun onTypChange(typ: DocumentType) = _uiState.update { it.copy(typ = typ, savedTitel = null) }
    fun onTitelChange(value: String) = _uiState.update { it.copy(titel = value, savedTitel = null) }
    fun onInhaltChange(value: String) = _uiState.update { it.copy(inhalt = value, savedTitel = null) }

    fun save() {
        val state = _uiState.value
        if (state.titel.isBlank() || state.inhalt.isBlank()) {
            _uiState.update { it.copy(errorMessage = "Titel und Inhalt duerfen nicht leer sein.") }
            return
        }
        _uiState.update { it.copy(isSaving = true, errorMessage = null) }
        viewModelScope.launch {
            val result = documentRepository.createDocument(
                projectId = projectId,
                typ = state.typ,
                titel = state.titel.trim(),
                inhalt = state.inhalt.trim(),
            )
            when (result) {
                is ApiResult.Success -> _uiState.update { DocumentFormUiState(savedTitel = result.data.titel) }
                is ApiResult.Error -> _uiState.update { it.copy(isSaving = false, errorMessage = result.message) }
            }
        }
    }
}
