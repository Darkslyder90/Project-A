package com.projecta.mobile.ui.documents

import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue

// Haelt lokal fest, ob gerade die Liste oder ein einzelnes Dokument gezeigt
// wird - bewusst kein eigener NavHost fuer diesen einen Sprung (siehe
// Briefing: Dokumentliste ist nur Sprungziel, keine eigene Navigationsebene).
@Composable
fun DocumentsTabScreen(projectId: Int) {
    var selectedDocumentId by remember { mutableStateOf<Int?>(null) }

    val documentId = selectedDocumentId
    if (documentId == null) {
        DocumentListScreen(projectId = projectId, onDocumentSelected = { selectedDocumentId = it })
    } else {
        DocumentDetailScreen(
            projectId = projectId,
            documentId = documentId,
            onBack = { selectedDocumentId = null },
        )
    }
}
