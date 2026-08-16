package com.projecta.mobile.data.auth

import android.content.Context
import android.content.SharedPreferences
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey

data class ServerCredentials(
    val baseUrl: String,
    val username: String,
    val password: String,
)

// Persistiert Server-URL + Basic-Auth-Zugangsdaten verschluesselt (Android
// Keystore-gestuetzt via EncryptedSharedPreferences) - siehe Briefing "Auth":
// einmalig beim ersten Start eingeben, danach automatisch bei jedem Request
// mitschicken, keine wiederholte Anmeldung noetig.
class CredentialStore(context: Context) {

    private val prefs: SharedPreferences by lazy {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()

        EncryptedSharedPreferences.create(
            context,
            "project_a_credentials",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    fun load(): ServerCredentials? {
        val baseUrl = prefs.getString(KEY_BASE_URL, null) ?: return null
        val username = prefs.getString(KEY_USERNAME, null) ?: return null
        val password = prefs.getString(KEY_PASSWORD, null) ?: return null
        return ServerCredentials(baseUrl, username, password)
    }

    fun save(credentials: ServerCredentials) {
        prefs.edit()
            .putString(KEY_BASE_URL, credentials.baseUrl)
            .putString(KEY_USERNAME, credentials.username)
            .putString(KEY_PASSWORD, credentials.password)
            .apply()
    }

    fun clear() {
        prefs.edit().clear().apply()
    }

    private companion object {
        const val KEY_BASE_URL = "base_url"
        const val KEY_USERNAME = "username"
        const val KEY_PASSWORD = "password"
    }
}
