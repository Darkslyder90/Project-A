package com.projecta.mobile.ui.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.projecta.mobile.data.api.ApiClientFactory
import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.api.ApiSession
import com.projecta.mobile.data.api.ProjectApi
import com.projecta.mobile.data.api.apiCall
import com.projecta.mobile.data.auth.CredentialStore
import com.projecta.mobile.data.auth.ServerCredentials
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.flow.update
import kotlinx.coroutines.launch

data class LoginUiState(
    val baseUrl: String = "",
    val username: String = "",
    val password: String = "",
    val isLoading: Boolean = false,
    val errorMessage: String? = null,
)

// Validiert Zugangsdaten VOR dem Speichern (echter Testrequest gegen
// /api/projects) - erst nach einer erfolgreichen Antwort gelten sie als
// "gueltig hinterlegt" im Sinne des Briefings, damit die App beim naechsten
// Start nicht optimistisch mit kaputten Zugangsdaten startet.
class LoginViewModel(
    private val credentialStore: CredentialStore,
    private val apiSession: ApiSession,
    prefillErrorMessage: String? = null,
) : ViewModel() {

    private val _uiState = MutableStateFlow(
        run {
            val saved = credentialStore.load()
            LoginUiState(
                baseUrl = saved?.baseUrl.orEmpty(),
                username = saved?.username.orEmpty(),
                errorMessage = prefillErrorMessage,
            )
        },
    )
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    fun onBaseUrlChange(value: String) = _uiState.update { it.copy(baseUrl = value, errorMessage = null) }
    fun onUsernameChange(value: String) = _uiState.update { it.copy(username = value, errorMessage = null) }
    fun onPasswordChange(value: String) = _uiState.update { it.copy(password = value, errorMessage = null) }

    fun login(onSuccess: () -> Unit) {
        val state = _uiState.value
        if (state.baseUrl.isBlank() || state.username.isBlank() || state.password.isBlank()) {
            _uiState.update { it.copy(errorMessage = "Bitte Server-URL, Nutzername und Passwort ausfuellen.") }
            return
        }

        val credentials = ServerCredentials(
            baseUrl = state.baseUrl.trim(),
            username = state.username.trim(),
            password = state.password,
        )

        _uiState.update { it.copy(isLoading = true, errorMessage = null) }
        viewModelScope.launch {
            val testApi = ApiClientFactory.create(credentials).create(ProjectApi::class.java)
            when (val result = apiCall { testApi.listProjects() }) {
                is ApiResult.Success -> {
                    apiSession.login(credentials)
                    _uiState.update { it.copy(isLoading = false) }
                    onSuccess()
                }
                is ApiResult.Error -> {
                    _uiState.update { it.copy(isLoading = false, errorMessage = result.message) }
                }
            }
        }
    }
}
