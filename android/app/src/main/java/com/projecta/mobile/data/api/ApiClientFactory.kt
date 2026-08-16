package com.projecta.mobile.data.api

import com.jakewharton.retrofit2.converter.kotlinx.serialization.asConverterFactory
import com.projecta.mobile.data.auth.BasicAuthInterceptor
import com.projecta.mobile.data.auth.ServerCredentials
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.logging.HttpLoggingInterceptor
import retrofit2.Retrofit
import java.util.concurrent.TimeUnit

private val json = Json {
    ignoreUnknownKeys = true
    coerceInputValues = true
}

// Baut pro (Server-URL, Zugangsdaten)-Kombination einen frischen Retrofit-
// Client - Server-URL ist laut Briefing bewusst konfigurierbar, kein
// Hardcoding, kann sich also innerhalb einer App-Session aendern (Login,
// Einstellungen-Screen).
object ApiClientFactory {

    fun create(credentials: ServerCredentials): Retrofit {
        val client = OkHttpClient.Builder()
            .connectTimeout(15, TimeUnit.SECONDS)
            .readTimeout(30, TimeUnit.SECONDS)
            .addInterceptor(BasicAuthInterceptor(credentials.username, credentials.password))
            .addInterceptor(
                HttpLoggingInterceptor().apply { level = HttpLoggingInterceptor.Level.BASIC },
            )
            .build()

        return Retrofit.Builder()
            .baseUrl(normalizeBaseUrl(credentials.baseUrl))
            .client(client)
            .addConverterFactory(json.asConverterFactory("application/json".toMediaType()))
            .build()
    }

    private fun normalizeBaseUrl(input: String): String {
        var url = input.trim()
        if (!url.startsWith("http://") && !url.startsWith("https://")) {
            url = "https://$url"
        }
        if (!url.endsWith("/")) {
            url = "$url/"
        }
        return url
    }
}
