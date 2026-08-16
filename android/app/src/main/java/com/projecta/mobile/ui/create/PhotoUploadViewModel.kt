package com.projecta.mobile.ui.create

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
import java.io.File

data class PhotoUploadUiState(
    val imageFile: File? = null,
    val titel: String = "",
    val forceDuplicate: Boolean = false,
    val isUploading: Boolean = false,
    val isProcessing: Boolean = false,
    val document: DocumentDto? = null,
    val reviewInhalt: String = "",
    val isConfirming: Boolean = false,
    val errorMessage: String? = null,
    val savedMessage: String? = null,
)

// Foto-Upload (siehe Briefing Punkt 3): nutzt denselben Ingestion-Endpoint wie
// das Web inkl. KI-Analyse/Review-Schritt. Nach dem Upload steht das Dokument
// zunaechst auf "pending" - der eigentliche OCR/Vision-Task laeuft
// asynchron im Backend (siehe DocumentTaskRunner), daher wird der Status hier
// gepollt statt einmalig gelesen.
class PhotoUploadViewModel(
    private val projectId: Int,
    private val documentRepository: DocumentRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(PhotoUploadUiState())
    val uiState: StateFlow<PhotoUploadUiState> = _uiState.asStateFlow()

    fun onImageSelected(file: File) {
        _uiState.update {
            PhotoUploadUiState(imageFile = file, titel = it.titel)
        }
    }

    fun onUnsupportedImageFormat() {
        _uiState.update { it.copy(errorMessage = "Bildformat wird nicht unterstuetzt - nur JPG oder PNG.") }
    }

    fun onTitelChange(value: String) = _uiState.update { it.copy(titel = value) }
    fun onForceDuplicateChange(value: Boolean) = _uiState.update { it.copy(forceDuplicate = value) }
    fun onReviewInhaltChange(value: String) = _uiState.update { it.copy(reviewInhalt = value) }

    fun upload() {
        val state = _uiState.value
        val file = state.imageFile ?: return

        _uiState.update { it.copy(isUploading = true, errorMessage = null) }
        viewModelScope.launch {
            val result = documentRepository.uploadImage(
                projectId = projectId,
                imageFile = file,
                titel = state.titel.trim().ifBlank { null },
                force = state.forceDuplicate,
            )
            when (result) {
                is ApiResult.Success -> {
                    _uiState.update { it.copy(isUploading = false, document = result.data) }
                    pollUntilReviewOrDone(result.data.id)
                }
                is ApiResult.Error -> _uiState.update { it.copy(isUploading = false, errorMessage = result.message) }
            }
        }
    }

    private fun pollUntilReviewOrDone(documentId: Int) {
        _uiState.update { it.copy(isProcessing = true) }
        viewModelScope.launch {
            repeat(30) {
                delay(2000)
                when (val result = documentRepository.getDocument(projectId, documentId)) {
                    is ApiResult.Success -> {
                        val document = result.data
                        _uiState.update { it.copy(document = document) }
                        when (document.status) {
                            DocumentStatus.REVIEW_REQUIRED -> {
                                _uiState.update {
                                    it.copy(
                                        isProcessing = false,
                                        reviewInhalt = document.kiAnalyseRohtext ?: document.ocrText ?: "",
                                    )
                                }
                                return@launch
                            }
                            DocumentStatus.READY -> {
                                _uiState.update {
                                    it.copy(isProcessing = false, savedMessage = "Bild verarbeitet und indexiert.")
                                }
                                return@launch
                            }
                            DocumentStatus.FAILED -> {
                                _uiState.update {
                                    it.copy(
                                        isProcessing = false,
                                        errorMessage = document.fehlermeldung ?: "Verarbeitung fehlgeschlagen.",
                                    )
                                }
                                return@launch
                            }
                            else -> Unit // pending/processing/indexing - weiter pollen
                        }
                    }
                    is ApiResult.Error -> {
                        _uiState.update { it.copy(isProcessing = false, errorMessage = result.message) }
                        return@launch
                    }
                }
            }
            _uiState.update {
                it.copy(
                    isProcessing = false,
                    errorMessage = "Verarbeitung dauert ungewoehnlich lange - spaeter im Web-Frontend pruefen.",
                )
            }
        }
    }

    fun confirmReview() {
        val document = _uiState.value.document ?: return
        _uiState.update { it.copy(isConfirming = true, errorMessage = null) }
        viewModelScope.launch {
            val result = documentRepository.confirmReview(projectId, document.id, _uiState.value.reviewInhalt.trim())
            when (result) {
                is ApiResult.Success -> _uiState.update {
                    PhotoUploadUiState(savedMessage = "Bestaetigt und gespeichert.")
                }
                is ApiResult.Error -> _uiState.update { it.copy(isConfirming = false, errorMessage = result.message) }
            }
        }
    }
}
