package com.projecta.mobile.ui.common

import com.projecta.mobile.data.dto.DocumentStatus
import com.projecta.mobile.data.dto.DocumentType

fun DocumentType.label(): String = when (this) {
    DocumentType.NOTIZ -> "Notiz"
    DocumentType.PROZESS -> "Prozessbeschreibung"
    DocumentType.SYSTEMEINSTELLUNG -> "Systemeinstellung"
    DocumentType.SONSTIGES -> "Sonstiges"
    DocumentType.MEETING -> "Meeting"
    DocumentType.DATEI -> "Datei"
    DocumentType.BILD -> "Bild"
    DocumentType.EMAIL -> "E-Mail"
}

fun DocumentStatus.label(): String = when (this) {
    DocumentStatus.PENDING -> "Wartet"
    DocumentStatus.PROCESSING -> "Wird verarbeitet"
    DocumentStatus.REVIEW_REQUIRED -> "Pruefung noetig"
    DocumentStatus.INDEXING -> "Wird indexiert"
    DocumentStatus.READY -> "Fertig"
    DocumentStatus.FAILED -> "Fehlgeschlagen"
}
