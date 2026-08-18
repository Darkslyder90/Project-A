package com.projecta.mobile.ui.documents

import androidx.compose.runtime.Composable

// Liste vs. Detailansicht ("welches Dokument ist gerade offen?") wird von
// aussen hereingereicht statt lokal gehalten (siehe ProjectShellScreen) -
// damit auch eine Quellenangabe im Chat direkt ein Dokument hier oeffnen
// kann, nicht nur ein Tap in der Liste selbst.
@Composable
fun DocumentsTabScreen(
    projectId: Int,
    selectedDocumentId: Int?,
    onDocumentSelected: (Int?) -> Unit,
) {
    if (selectedDocumentId == null) {
        DocumentListScreen(projectId = projectId, onDocumentSelected = { onDocumentSelected(it) })
    } else {
        DocumentDetailScreen(
            projectId = projectId,
            documentId = selectedDocumentId,
            onBack = { onDocumentSelected(null) },
        )
    }
}
