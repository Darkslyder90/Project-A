package com.projecta.mobile.ui.create

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
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
import com.projecta.mobile.data.dto.MANUAL_DOCUMENT_TYPES
import com.projecta.mobile.projectAApplication
import com.projecta.mobile.ui.common.label

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DocumentFormScreen(projectId: Int) {
    val app = androidx.compose.ui.platform.LocalContext.current.projectAApplication()
    val viewModel: DocumentFormViewModel = viewModel(
        key = "document-form-$projectId",
        factory = viewModelFactory {
            initializer { DocumentFormViewModel(projectId, app.documentRepository) }
        },
    )
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        Text("Typ", style = MaterialTheme.typography.labelLarge)
        LazyRow(
            horizontalArrangement = Arrangement.spacedBy(8.dp),
            modifier = Modifier.padding(top = 8.dp, bottom = 16.dp),
        ) {
            items(MANUAL_DOCUMENT_TYPES) { typ ->
                FilterChip(
                    selected = state.typ == typ,
                    onClick = { viewModel.onTypChange(typ) },
                    label = { Text(typ.label()) },
                )
            }
        }

        OutlinedTextField(
            value = state.titel,
            onValueChange = viewModel::onTitelChange,
            label = { Text("Titel") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )

        OutlinedTextField(
            value = state.inhalt,
            onValueChange = viewModel::onInhaltChange,
            label = { Text("Inhalt") },
            minLines = 6,
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
        )

        state.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 12.dp))
        }
        state.savedTitel?.let {
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
