package com.projecta.mobile.data.auth

import okhttp3.Credentials
import okhttp3.Interceptor
import okhttp3.Response

// Haengt bei jedem Request denselben Basic-Auth-Header an, den auch Caddy vor
// der Web-App verlangt (siehe Hauptprojekt-Deployment) - der Nutzer meldet
// sich dadurch nie manuell in der App an, siehe Briefing "Auth".
class BasicAuthInterceptor(
    private val username: String,
    private val password: String,
) : Interceptor {

    override fun intercept(chain: Interceptor.Chain): Response {
        val authenticated = chain.request().newBuilder()
            .header("Authorization", Credentials.basic(username, password))
            .build()
        return chain.proceed(authenticated)
    }
}
