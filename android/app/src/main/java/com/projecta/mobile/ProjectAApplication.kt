package com.projecta.mobile

import android.app.Application
import android.content.Context
import com.projecta.mobile.data.api.ApiSession
import com.projecta.mobile.data.auth.CredentialStore
import com.projecta.mobile.data.repository.ChatRepository
import com.projecta.mobile.data.repository.DocumentRepository
import com.projecta.mobile.data.repository.MeetingRepository
import com.projecta.mobile.data.repository.PersonRepository
import com.projecta.mobile.data.repository.ProjectRepository

// Einfache manuelle Dependency-Injection (kein Hilt/Dagger noetig fuer den
// ueberschaubaren Umfang dieser App) - alle Abhaengigkeiten leben hier einmal
// pro Prozess.
class ProjectAApplication : Application() {

    lateinit var credentialStore: CredentialStore
        private set
    lateinit var apiSession: ApiSession
        private set
    lateinit var projectRepository: ProjectRepository
        private set
    lateinit var chatRepository: ChatRepository
        private set
    lateinit var documentRepository: DocumentRepository
        private set
    lateinit var personRepository: PersonRepository
        private set
    lateinit var meetingRepository: MeetingRepository
        private set

    override fun onCreate() {
        super.onCreate()
        credentialStore = CredentialStore(this)
        apiSession = ApiSession(credentialStore)
        projectRepository = ProjectRepository(apiSession)
        chatRepository = ChatRepository(apiSession)
        documentRepository = DocumentRepository(apiSession)
        personRepository = PersonRepository(apiSession)
        meetingRepository = MeetingRepository(apiSession)
    }
}

fun Context.projectAApplication(): ProjectAApplication = applicationContext as ProjectAApplication
