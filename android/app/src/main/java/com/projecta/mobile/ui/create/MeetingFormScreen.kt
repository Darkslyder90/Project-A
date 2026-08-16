package com.projecta.mobile.ui.create

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ExperimentalLayoutApi
import androidx.compose.foundation.layout.FlowRow
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
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
import com.projecta.mobile.projectAApplication
import com.projecta.mobile.ui.common.DatePickerField

@OptIn(ExperimentalMaterial3Api::class, ExperimentalLayoutApi::class)
@Composable
fun MeetingFormScreen(projectId: Int) {
    val app = androidx.compose.ui.platform.LocalContext.current.projectAApplication()
    val viewModel: MeetingFormViewModel = viewModel(
        key = "meeting-form-$projectId",
        factory = viewModelFactory {
            initializer {
                MeetingFormViewModel(
                    projectId,
                    app.personRepository,
                    app.documentRepository,
                    app.meetingRepository,
                )
            }
        },
    )
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        DatePickerField(
            label = "Datum",
            value = state.datum,
            onValueChange = viewModel::onDatumChange,
            modifier = Modifier.fillMaxWidth(),
        )

        Text(
            "Teilnehmer",
            style = MaterialTheme.typography.labelLarge,
            modifier = Modifier.padding(top = 16.dp, bottom = 8.dp),
        )
        if (state.people.isEmpty() && !state.isLoadingPeople) {
            Text(
                "Noch keine Personen in diesem Projekt angelegt.",
                style = MaterialTheme.typography.bodySmall,
            )
        } else {
            FlowRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                state.people.forEach { person ->
                    FilterChip(
                        selected = person.id in state.selectedPeopleIds,
                        onClick = { viewModel.toggleParticipant(person.id) },
                        label = { Text(person.name) },
                    )
                }
            }
        }

        OutlinedTextField(
            value = state.zusammenfassung,
            onValueChange = viewModel::onZusammenfassungChange,
            label = { Text("Zusammenfassung (optional)") },
            minLines = 2,
            modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
        )

        OutlinedTextField(
            value = state.transkript,
            onValueChange = viewModel::onTranskriptChange,
            label = { Text("Transkript / Protokoll (optional)") },
            minLines = 6,
            modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
        )

        state.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 12.dp))
        }
        state.savedDatum?.let {
            Text(
                "Meeting vom $it gespeichert.",
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
