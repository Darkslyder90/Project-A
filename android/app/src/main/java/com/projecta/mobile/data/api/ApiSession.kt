package com.projecta.mobile.data.api

import com.projecta.mobile.data.auth.CredentialStore
import com.projecta.mobile.data.auth.ServerCredentials
import retrofit2.Retrofit

// Zentraler Zugriffspunkt auf den aktuell konfigurierten Retrofit-Client.
// Baut sich bei Bedarf aus den persistierten Zugangsdaten neu auf (z. B. nach
// Prozess-Neustart) - siehe Briefing "Auth": keine wiederholte Anmeldung
// noetig, solange gueltige Zugangsdaten hinterlegt sind.
class ApiSession(private val credentialStore: CredentialStore) {

    private var retrofit: Retrofit? = null

    fun isConfigured(): Boolean = credentialStore.load() != null

    fun login(credentials: ServerCredentials) {
        credentialStore.save(credentials)
        retrofit = ApiClientFactory.create(credentials)
    }

    fun logout() {
        credentialStore.clear()
        retrofit = null
    }

    val projectApi: ProjectApi get() = retrofitOrThrow().create(ProjectApi::class.java)
    val chatApi: ChatApi get() = retrofitOrThrow().create(ChatApi::class.java)
    val documentApi: DocumentApi get() = retrofitOrThrow().create(DocumentApi::class.java)
    val personApi: PersonApi get() = retrofitOrThrow().create(PersonApi::class.java)
    val meetingApi: MeetingApi get() = retrofitOrThrow().create(MeetingApi::class.java)

    private fun retrofitOrThrow(): Retrofit {
        retrofit?.let { return it }
        val credentials = credentialStore.load()
            ?: error("Keine Zugangsdaten hinterlegt - ApiSession vor Nutzung ueber login() konfigurieren")
        return ApiClientFactory.create(credentials).also { retrofit = it }
    }
}
