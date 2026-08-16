package com.projecta.mobile.ui.create

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.projecta.mobile.projectAApplication

@Composable
fun PersonFormScreen(projectId: Int) {
    val app = androidx.compose.ui.platform.LocalContext.current.projectAApplication()
    val viewModel: PersonFormViewModel = viewModel(
        key = "person-form-$projectId",
        factory = viewModelFactory {
            initializer { PersonFormViewModel(projectId, app.personRepository) }
        },
    )
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        OutlinedTextField(
            value = state.name,
            onValueChange = viewModel::onNameChange,
            label = { Text("Name") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )
        OutlinedTextField(
            value = state.rolle,
            onValueChange = viewModel::onRolleChange,
            label = { Text("Rolle") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
        )
        OutlinedTextField(
            value = state.kontaktinfo,
            onValueChange = viewModel::onKontaktinfoChange,
            label = { Text("Kontaktinfo") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
        )
        OutlinedTextField(
            value = state.notizen,
            onValueChange = viewModel::onNotizenChange,
            label = { Text("Notizen") },
            minLines = 3,
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
        )

        state.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 12.dp))
        }
        state.savedName?.let {
            Text(
                "\"$it\" gespeichert.",
                color = MaterialTheme.colorScheme.primary,
                modifier = Modifier.padding(top = 12.dp),
            )
        }

        Button(
            onClick = viewModel::save,
            enabled = !state.isSaving,
            modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
        ) {
            if (state.isSaving) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp))
            } else {
                Text("Speichern")
            }
        }
    }
}
