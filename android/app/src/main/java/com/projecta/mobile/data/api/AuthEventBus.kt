package com.projecta.mobile.data.api

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.asSharedFlow

// Globaler Kanal fuer "Zugangsdaten wurden vom Server abgelehnt" (401) -
// jeder Screen loest bei einem 401 denselben Reflex aus (siehe apiCall):
// zurueck zum Login-Screen mit Fehlermeldung, statt dass jedes ViewModel das
// selbst verdrahten muss (siehe Briefing "Auth").
object AuthEventBus {
    private val _unauthorized = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val unauthorized = _unauthorized.asSharedFlow()

    suspend fun notifyUnauthorized() {
        _unauthorized.emit(Unit)
    }
}
