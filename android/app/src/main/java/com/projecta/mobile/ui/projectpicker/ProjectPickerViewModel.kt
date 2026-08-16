package com.projecta.mobile.ui.projectpicker

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.dto.ProjectDto
import com.projecta.mobile.data.repository.ProjectRepository
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class ProjectPickerUiState(
    val isLoading: Boolean = true,
    val projects: List<ProjectDto> = emptyList(),
    val errorMessage: String? = null,
)

class ProjectPickerViewModel(private val projectRepository: ProjectRepository) : ViewModel() {

    private val _uiState = MutableStateFlow(ProjectPickerUiState())
    val uiState: StateFlow<ProjectPickerUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun load() {
        _uiState.update { it.copy(isLoading = true, errorMessage = null) }
        viewModelScope.launch {
            when (val result = projectRepository.listProjects()) {
                is ApiResult.Success -> _uiState.update {
                    it.copy(isLoading = false, projects = result.data)
                }
                is ApiResult.Error -> _uiState.update {
                    it.copy(isLoading = false, errorMessage = result.message)
                }
            }
        }
    }
}
