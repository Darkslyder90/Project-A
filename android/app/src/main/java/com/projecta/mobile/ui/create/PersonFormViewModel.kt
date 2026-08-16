package com.projecta.mobile.ui.create

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.repository.PersonRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class PersonFormUiState(
    val name: String = "",
    val rolle: String = "",
    val kontaktinfo: String = "",
    val notizen: String = "",
    val isSaving: Boolean = false,
    val errorMessage: String? = null,
    val savedName: String? = null,
)

class PersonFormViewModel(
    private val projectId: Int,
    private val personRepository: PersonRepository,
) : ViewModel() {

    private val _uiState = MutableStateFlow(PersonFormUiState())
    val uiState: StateFlow<PersonFormUiState> = _uiState.asStateFlow()

    fun onNameChange(value: String) = _uiState.update { it.copy(name = value, savedName = null) }
    fun onRolleChange(value: String) = _uiState.update { it.copy(rolle = value, savedName = null) }
    fun onKontaktinfoChange(value: String) = _uiState.update { it.copy(kontaktinfo = value, savedName = null) }
    fun onNotizenChange(value: String) = _uiState.update { it.copy(notizen = value, savedName = null) }

    fun save() {
        val state = _uiState.value
        if (state.name.isBlank()) {
            _uiState.update { it.copy(errorMessage = "Name darf nicht leer sein.") }
            return
        }
        _uiState.update { it.copy(isSaving = true, errorMessage = null) }
        viewModelScope.launch {
            val result = personRepository.createPerson(
                projectId = projectId,
                name = state.name.trim(),
                rolle = state.rolle.trim().ifBlank { null },
                kontaktinfo = state.kontaktinfo.trim().ifBlank { null },
                notizen = state.notizen.trim().ifBlank { null },
            )
            when (result) {
                is ApiResult.Success -> _uiState.update { PersonFormUiState(savedName = result.data.name) }
                is ApiResult.Error -> _uiState.update { it.copy(isSaving = false, errorMessage = result.message) }
            }
        }
    }
}
