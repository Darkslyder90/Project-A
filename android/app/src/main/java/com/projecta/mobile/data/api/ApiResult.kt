package com.projecta.mobile.data.api

import kotlinx.serialization.json.Json
import kotlinx.serialization.json.JsonPrimitive
import kotlinx.serialization.json.jsonObject
import retrofit2.HttpException
import java.io.IOException

// Einheitliches Ergebnis fuer alle Repository-Calls - siehe Briefing
// "Fehlerbehandlung": Netzwerkfehler und ungueltige Zugangsdaten muessen
// verstaendlich angezeigt werden koennen, nie ein Absturz.
sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()
    data class Error(val message: String, val isAuthError: Boolean = false) : ApiResult<Nothing>()
}

suspend fun <T> apiCall(block: suspend () -> T): ApiResult<T> {
    return try {
        ApiResult.Success(block())
    } catch (e: HttpException) {
        if (e.code() == 401) {
            AuthEventBus.notifyUnauthorized()
            ApiResult.Error("Zugangsdaten wurden vom Server abgelehnt.", isAuthError = true)
        } else {
            ApiResult.Error(extractDetailMessage(e) ?: "Server-Fehler (${e.code()}): ${e.message()}")
        }
    } catch (e: IOException) {
        ApiResult.Error("Server nicht erreichbar. Verbindung/Server-URL pruefen.")
    }
}

// Das Backend liefert Fehlertexte konsequent als {"detail": "<lesbare Meldung>"}
// (siehe backend/app/main.py::handle_app_error) - wird hier ausgelesen, damit
// z. B. Duplikat- oder Validierungsmeldungen 1:1 in der App ankommen statt nur
// "Server-Fehler (409)". Bei den nativen Pydantic-422-Fehlern ist "detail" eine
// Liste statt eines Strings - dann faellt dies zurueck auf null (generische
// Meldung im Aufrufer).
private fun extractDetailMessage(e: HttpException): String? {
    val body = e.response()?.errorBody()?.string() ?: return null
    return try {
        val detail = Json.parseToJsonElement(body).jsonObject["detail"] as? JsonPrimitive
        detail?.takeIf { it.isString }?.content
    } catch (_: Exception) {
        null
    }
}
