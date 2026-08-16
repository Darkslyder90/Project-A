package com.projecta.mobile.ui.create

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.dto.DocumentType
import com.projecta.mobile.data.dto.PersonDto
import com.projecta.mobile.data.repository.DocumentRepository
import com.projecta.mobile.data.repository.MeetingRepository
import com.projecta.mobile.data.repository.PersonRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class MeetingFormUiState(
    val isLoadingPeople: Boolean = true,
    val people: List<PersonDto> = emptyList(),
    val selectedPeopleIds: Set<Int> = emptySet(),
    val datum: String = "",
    val zusammenfassung: String = "",
    val transkript: String = "",
    val isSaving: Boolean = false,
    val errorMessage: String? = null,
    val savedDatum: String? = null,
)

// Das Backend erzeugt bei einem Meeting KEIN Protokoll-Dokument automatisch
// (siehe meeting_service.create_meeting - erwartet nur eine bereits
// existierende document_id). Die Automatik aus dem Mobile-Briefing wird
// deshalb hier client-seitig nachgebaut: erst Dokument (typ=meeting) aus dem
// Transkript-Text anlegen, danach das Meeting mit dessen document_id
// verknuepfen - zwei bestehende Endpunkte, kein neuer noetig.
class MeetingFormViewModel(
    private val projectId: Int,
    private val personRepository: PersonRepository,
    private val documentRepository: DocumentRepository,
    private val meetingRepository: MeetingRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(MeetingFormUiState())
    val uiState: StateFlow<MeetingFormUiState> = _uiState.asStateFlow()

    init {
        loadPeople()
    }

    fun loadPeople() {
        _uiState.update { it.copy(isLoadingPeople = true) }
        viewModelScope.launch {
            when (val result = personRepository.listPeople(projectId)) {
                is ApiResult.Success -> _uiState.update { it.copy(isLoadingPeople = false, people = result.data) }
                is ApiResult.Error -> _uiState.update { it.copy(isLoadingPeople = false, errorMessage = result.message) }
            }
        }
    }

    fun onDatumChange(value: String) = _uiState.update { it.copy(datum = value, savedDatum = null) }
    fun onZusammenfassungChange(value: String) = _uiState.update { it.copy(zusammenfassung = value, savedDatum = null) }
    fun onTranskriptChange(value: String) = _uiState.update { it.copy(transkript = value, savedDatum = null) }

    fun toggleParticipant(personId: Int) {
        _uiState.update {
            val updated = if (personId in it.selectedPeopleIds) {
                it.selectedPeopleIds - personId
            } else {
                it.selectedPeopleIds + personId
            }
            it.copy(selectedPeopleIds = updated)
        }
    }

    fun save() {
        val state = _uiState.value
        if (state.datum.isBlank()) {
            _uiState.update { it.copy(errorMessage = "Bitte ein Datum waehlen.") }
            return
        }
        _uiState.update { it.copy(isSaving = true, errorMessage = null) }
        viewModelScope.launch {
            var documentId: Int? = null
            if (state.transkript.isNotBlank()) {
                when (
                    val doc = documentRepository.createDocument(
                        projectId = projectId,
                        typ = DocumentType.MEETING,
                        titel = "Meeting ${state.datum}",
                        inhalt = state.transkript.trim(),
                        dokumentdatum = state.datum,
                    )
                ) {
                    is ApiResult.Success -> documentId = doc.data.id
                    is ApiResult.Error -> {
                        _uiState.update { it.copy(isSaving = false, errorMessage = doc.message) }
                        return@launch
                    }
                }
            }

            val result = meetingRepository.createMeeting(
                projectId = projectId,
                datum = state.datum,
                documentId = documentId,
                zusammenfassung = state.zusammenfassung.trim().ifBlank { null },
                teilnehmerIds = state.selectedPeopleIds.toList(),
            )
            when (result) {
                is ApiResult.Success -> _uiState.update {
                    MeetingFormUiState(isLoadingPeople = false, people = it.people, savedDatum = result.data.datum)
                }
                is ApiResult.Error -> _uiState.update { it.copy(isSaving = false, errorMessage = result.message) }
            }
        }
    }
}
