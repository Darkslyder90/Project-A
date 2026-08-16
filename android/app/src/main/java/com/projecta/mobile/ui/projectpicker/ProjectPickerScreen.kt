package com.projecta.mobile.ui.projectpicker

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
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
import com.projecta.mobile.data.dto.ProjectDto
import com.projecta.mobile.projectAApplication

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ProjectPickerScreen(onProjectSelected: (ProjectDto) -> Unit) {
    val app = androidx.compose.ui.platform.LocalContext.current.projectAApplication()
    val viewModel: ProjectPickerViewModel = viewModel(
        factory = viewModelFactory {
            initializer { ProjectPickerViewModel(app.projectRepository) }
        },
    )
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Scaffold(
        topBar = { TopAppBar(title = { Text("Projekt waehlen") }) },
    ) { padding ->
        Box(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding),
        ) {
            when {
                state.isLoading -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))

                state.errorMessage != null -> Column(
                    modifier = Modifier.fillMaxSize().padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                ) {
                    Text(state.errorMessage!!, color = MaterialTheme.colorScheme.error)
                    Button(onClick = viewModel::load, modifier = Modifier.padding(top = 16.dp)) {
                        Text("Erneut versuchen")
                    }
                }

                state.projects.isEmpty() -> Text(
                    "Keine Projekte vorhanden.",
                    modifier = Modifier.align(Alignment.Center),
                )

                else -> LazyColumn(modifier = Modifier.fillMaxSize().padding(16.dp)) {
                    items(state.projects, key = { it.id }) { project ->
                        Card(
                            onClick = { onProjectSelected(project) },
                            modifier = Modifier.fillMaxWidth().padding(vertical = 6.dp),
                        ) {
                            Column(modifier = Modifier.padding(16.dp)) {
                                Text(project.name, style = MaterialTheme.typography.titleMedium)
                                project.beschreibung?.let {
                                    Text(it, style = MaterialTheme.typography.bodySmall)
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}
