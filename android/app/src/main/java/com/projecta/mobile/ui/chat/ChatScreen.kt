package com.projecta.mobile.ui.chat

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material.icons.filled.Send
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import com.projecta.mobile.data.dto.ChatMessageDto
import com.projecta.mobile.data.dto.ChatSourceSnapshotDto
import com.projecta.mobile.projectAApplication

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ChatScreen(projectId: Int, onOpenDocument: (Int) -> Unit) {
    val app = androidx.compose.ui.platform.LocalContext.current.projectAApplication()
    val viewModel: ChatViewModel = viewModel(
        key = "chat-$projectId",
        factory = viewModelFactory {
            initializer { ChatViewModel(projectId, app.chatRepository) }
        },
    )
    val state by viewModel.uiState.collectAsStateWithLifecycle()
    var menuExpanded by remember { mutableStateOf(false) }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text(state.selectedConversationTitel ?: "Chat") },
                actions = {
                    if (state.conversations.size > 1) {
                        IconButton(onClick = { menuExpanded = true }) {
                            Icon(Icons.Filled.MoreVert, contentDescription = "Unterhaltung waehlen")
                        }
                        DropdownMenu(expanded = menuExpanded, onDismissRequest = { menuExpanded = false }) {
                            state.conversations.forEach { conversation ->
                                DropdownMenuItem(
                                    text = { Text(conversation.titel ?: "Unterhaltung #${conversation.id}") },
                                    onClick = {
                                        menuExpanded = false
                                        viewModel.selectConversation(conversation.id)
                                    },
                                )
                            }
                        }
                    }
                },
            )
        },
        bottomBar = {
            Surface(tonalElevation = 3.dp) {
                Row(
                    modifier = Modifier.fillMaxWidth().padding(12.dp),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    OutlinedTextField(
                        value = state.messageDraft,
                        onValueChange = viewModel::onMessageDraftChange,
                        placeholder = { Text("Nachricht schreiben …") },
                        enabled = !state.isSending,
                        modifier = Modifier.weight(1f),
                    )
                    IconButton(
                        onClick = viewModel::sendMessage,
                        enabled = !state.isSending && state.messageDraft.isNotBlank(),
                    ) {
                        if (state.isSending) {
                            CircularProgressIndicator(modifier = Modifier.size(20.dp))
                        } else {
                            Icon(Icons.Filled.Send, contentDescription = "Senden")
                        }
                    }
                }
            }
        },
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize().padding(padding)) {
            when {
                state.isLoading -> CircularProgressIndicator(modifier = Modifier.align(Alignment.Center))

                state.errorMessage != null -> Text(
                    state.errorMessage!!,
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.align(Alignment.Center).padding(24.dp),
                )

                state.messages.isEmpty() -> Text(
                    "Noch keine Nachrichten. Schreib unten eine Frage, um die Unterhaltung zu starten.",
                    modifier = Modifier.align(Alignment.Center).padding(24.dp),
                )

                else -> LazyColumn(
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(16.dp),
                    verticalArrangement = Arrangement.spacedBy(12.dp),
                ) {
                    items(state.messages, key = { it.id }) { message ->
                        ChatMessageBubble(message, onOpenDocument = onOpenDocument)
                    }
                }
            }
        }
    }
}

@Composable
private fun ChatMessageBubble(message: ChatMessageDto, onOpenDocument: (Int) -> Unit) {
    val isUser = message.rolle == "user"
    Column(
        modifier = Modifier.fillMaxWidth(),
        horizontalAlignment = if (isUser) Alignment.End else Alignment.Start,
    ) {
        Card(
            modifier = Modifier.widthIn(max = 320.dp),
            colors = CardDefaults.cardColors(
                containerColor = if (isUser) {
                    MaterialTheme.colorScheme.primary
                } else {
                    MaterialTheme.colorScheme.surface
                },
            ),
        ) {
            Text(
                message.text,
                modifier = Modifier.padding(12.dp),
                color = if (isUser) MaterialTheme.colorScheme.onPrimary else MaterialTheme.colorScheme.onSurface,
            )
        }
        if (!isUser && !message.quellen.isNullOrEmpty()) {
            Column(modifier = Modifier.padding(top = 4.dp, start = 4.dp, end = 4.dp)) {
                message.quellen.forEach { source ->
                    SourceLine(source, onClick = { onOpenDocument(source.documentId) })
                }
            }
        }
    }
}

@Composable
private fun SourceLine(source: ChatSourceSnapshotDto, onClick: () -> Unit) {
    val parts = listOfNotNull(
        source.documentTitel,
        source.dokumentdatum,
        source.abschnitt,
    ).joinToString(" · ")
    // Geloeschte Quellen sind nicht antippbar (Detailansicht wuerde ohnehin
    // nur einen 404-Fehler zeigen) - bleiben rein informativ.
    val modifier = if (source.geloescht) Modifier else Modifier.clickable(onClick = onClick)
    Text(
        text = if (source.geloescht) "$parts (geloescht)" else parts,
        style = MaterialTheme.typography.labelSmall,
        color = if (source.geloescht) {
            MaterialTheme.colorScheme.onSurfaceVariant
        } else {
            MaterialTheme.colorScheme.primary
        },
        modifier = modifier.padding(vertical = 2.dp),
    )
}
