package com.projecta.mobile.ui.documents

import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.projecta.mobile.data.dto.DocumentDto
import com.projecta.mobile.projectAApplication
import com.projecta.mobile.ui.common.label

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun DocumentListScreen(projectId: Int, onDocumentSelected: (Int) -> Unit) {
    val app = androidx.compose.ui.platform.LocalContext.current.projectAApplication()
    val viewModel: DocumentListViewModel = viewModel(
        key = "document-list-$projectId",
        factory = viewModelFactory {
            initializer { DocumentListViewModel(projectId, app.documentRepository) }
        },
    )
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    // Die ViewModel-Instanz ueberlebt den Wechsel zur Detailansicht und
    // zurueck (gleicher Tab-NavBackStackEntry, siehe ProjectShellScreen) -
    // ohne diesen Reload wuerde die Liste nach einem Loeschen/Bearbeiten
    // veraltete Daten zeigen.
    LaunchedEffect(Unit) { viewModel.load() }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Dokumente") },
                actions = {
                    IconButton(onClick = viewModel::requestReindexAll, enabled = !state.isReindexingAll) {
                        Icon(Icons.Filled.Refresh, contentDescription = "Gesamtes Projekt neu indexieren")
                    }
                },
            )
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            if (state.isReindexingAll) {
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    modifier = Modifier.fillMaxWidth().padding(16.dp),
                ) {
                    CircularProgressIndicator(modifier = Modifier.size(16.dp))
                    Text(
                        "Index wird aktualisiert …",
                        style = MaterialTheme.typography.bodySmall,
                        modifier = Modifier.padding(start = 8.dp),
                    )
                }
            }

            Box(modifier = Modifier.fillMaxSize()) {
                when {
                    state.isLoading -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))

                    state.errorMessage != null -> Column(
                        modifier = Modifier.fillMaxSize().padding(24.dp),
                    ) {
                        Text(state.errorMessage!!, color = MaterialTheme.colorScheme.error)
                        Button(onClick = viewModel::load, modifier = Modifier.padding(top = 16.dp)) {
                            Text("Erneut versuchen")
                        }
                    }

                    state.documents.isEmpty() -> Text(
                        "Noch keine Dokumente in diesem Projekt.",
                        modifier = Modifier.align(Alignment.Center).padding(24.dp),
                    )

                    else -> LazyColumn(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                        items(state.documents, key = { it.id }) { document ->
                            DocumentListItem(document, onClick = { onDocumentSelected(document.id) })
                        }
                    }
                }
            }
        }

        if (state.showReindexAllConfirm) {
            AlertDialog(
                onDismissRequest = viewModel::dismissReindexAllConfirm,
                title = { Text("Gesamtes Projekt neu indexieren?") },
                text = {
                    Text(
                        "Alle ${state.documents.size} Dokumente werden nacheinander neu verarbeitet. " +
                            "Der Chat bleibt waehrenddessen nutzbar.",
                    )
                },
                confirmButton = {
                    TextButton(onClick = viewModel::reindexAll) { Text("Neu indexieren") }
                },
                dismissButton = {
                    TextButton(onClick = viewModel::dismissReindexAllConfirm) { Text("Abbrechen") }
                },
            )
        }
    }
}

@Composable
private fun DocumentListItem(document: DocumentDto, onClick: () -> Unit) {
    Card(
        onClick = onClick,
        modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
    ) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(document.titel, style = MaterialTheme.typography.titleMedium)
            val meta = listOfNotNull(
                document.typ.label(),
                document.status.label(),
                document.dokumentdatum,
            ).joinToString(" · ")
            Text(meta, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}
