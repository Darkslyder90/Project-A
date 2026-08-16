package com.projecta.mobile.ui.documents

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Delete
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.projecta.mobile.data.dto.DocumentType
import com.projecta.mobile.projectAApplication
import com.projecta.mobile.ui.common.DatePickerField
import com.projecta.mobile.ui.common.label

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DocumentDetailScreen(projectId: Int, documentId: Int, onBack: () -> Unit) {
    val app = androidx.compose.ui.platform.LocalContext.current.projectAApplication()
    val viewModel: DocumentDetailViewModel = viewModel(
        key = "document-detail-$projectId-$documentId",
        factory = viewModelFactory {
            initializer { DocumentDetailViewModel(projectId, documentId, app.documentRepository) }
        },
    )
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(state.document?.titel ?: "Dokument") },
                navigationIcon = {
                    IconButton(onClick = onBack) {
                        Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Zurueck")
                    }
                },
                actions = {
                    if (state.document != null && !state.isEditing) {
                        val busy = state.isDeleting || state.isReindexing
                        IconButton(onClick = viewModel::reindex, enabled = !busy) {
                            Icon(Icons.Filled.Refresh, contentDescription = "Neu indexieren")
                        }
                        IconButton(onClick = viewModel::startEditing, enabled = !busy) {
                            Icon(Icons.Filled.Edit, contentDescription = "Bearbeiten")
                        }
                        IconButton(onClick = viewModel::requestDelete, enabled = !busy) {
                            Icon(Icons.Filled.Delete, contentDescription = "Loeschen")
                        }
                    }
                },
            )
        },
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when {
                state.isLoading || state.isDeleting -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))

                state.errorMessage != null && state.document == null -> Column(
                    modifier = Modifier.fillMaxSize().padding(24.dp),
                ) {
                    Text(state.errorMessage!!, color = MaterialTheme.colorScheme.error)
                    Button(onClick = viewModel::load, modifier = Modifier.padding(top = 16.dp)) {
                        Text("Erneut versuchen")
                    }
                }

                state.isEditing -> DocumentEditForm(state = state, viewModel = viewModel)

                state.document != null -> DocumentReadOnlyView(state = state)
            }
        }

        if (state.showDeleteConfirm) {
            AlertDialog(
                onDismissRequest = viewModel::dismissDeleteConfirm,
                title = { Text("Dokument loeschen?") },
                text = { Text("\"${state.document?.titel}\" wird unwiderruflich geloescht.") },
                confirmButton = {
                    TextButton(onClick = { viewModel.delete(onBack) }) { Text("Loeschen") }
                },
                dismissButton = {
                    TextButton(onClick = viewModel::dismissDeleteConfirm) { Text("Abbrechen") }
                },
            )
        }
    }
}

@Composable
private fun DocumentReadOnlyView(state: DocumentDetailUiState) {
    val document = state.document ?: return
    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        val meta = listOfNotNull(
            document.typ.label(),
            document.status.label(),
            document.dokumentdatum,
            document.dateiname,
        ).joinToString(" · ")
        Text(meta, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

        if (state.isReindexing) {
            Row(
                verticalAlignment = Alignment.CenterVertically,
                modifier = Modifier.padding(top = 12.dp),
            ) {
                CircularProgressIndicator(modifier = Modifier.size(16.dp))
                Text(
                    "Index wird aktualisiert …",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(start = 8.dp),
                )
            }
        }

        if (document.fehlermeldung != null) {
            Text(
                document.fehlermeldung,
                color = MaterialTheme.colorScheme.error,
                modifier = Modifier.padding(top = 12.dp),
            )
        }
        state.savedMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(top = 12.dp))
        }

        Text(
            document.inhalt ?: "(kein Inhalt)",
            style = MaterialTheme.typography.bodyMedium,
            modifier = Modifier.padding(top = 16.dp),
        )
    }
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun DocumentEditForm(state: DocumentDetailUiState, viewModel: DocumentDetailViewModel) {
    val original = state.document
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
            items(DocumentType.entries) { typ ->
                FilterChip(
                    selected = state.editTyp == typ,
                    onClick = { viewModel.onEditTypChange(typ) },
                    label = { Text(typ.label()) },
                )
            }
        }

        OutlinedTextField(
            value = state.editTitel,
            onValueChange = viewModel::onEditTitelChange,
            label = { Text("Titel") },
            singleLine = true,
            modifier = Modifier.fillMaxWidth(),
        )

        DatePickerField(
            label = "Dokumentdatum (optional)",
            value = state.editDokumentdatum,
            onValueChange = viewModel::onEditDokumentdatumChange,
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
        )

        OutlinedTextField(
            value = state.editInhalt,
            onValueChange = viewModel::onEditInhaltChange,
            label = { Text("Inhalt") },
            minLines = 8,
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
        )

        if (original != null && state.editInhalt.trim() != (original.inhalt ?: "").trim()) {
            Text(
                "Inhaltsänderung erkannt – das Dokument wird nach dem Speichern neu indexiert.",
                style = MaterialTheme.typography.bodySmall,
                modifier = Modifier.padding(top = 8.dp),
            )
        }

        state.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 12.dp))
        }

        Row(modifier = Modifier.fillMaxWidth().padding(top = 16.dp)) {
            Button(
                onClick = viewModel::save,
                enabled = !state.isSaving,
                modifier = Modifier.weight(1f),
            ) {
                if (state.isSaving) {
                    CircularProgressIndicator(modifier = Modifier.size(20.dp))
                } else {
                    Text("Speichern")
                }
            }
            OutlinedButton(
                onClick = viewModel::cancelEditing,
                enabled = !state.isSaving,
                modifier = Modifier.weight(1f).padding(start = 8.dp),
            ) {
                Text("Abbrechen")
            }
        }
    }
}
