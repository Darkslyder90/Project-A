package com.projecta.mobile.ui.common

import androidx.compose.foundation.layout.padding
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddCircle
import androidx.compose.material.icons.filled.Chat
import androidx.compose.material.icons.filled.Description
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Icon
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import com.projecta.mobile.ui.chat.ChatScreen
import com.projecta.mobile.ui.create.CreateScreen
import com.projecta.mobile.ui.documents.DocumentsTabScreen

private object ShellTabs {
    const val CHAT = "chat"
    const val CREATE = "create"
    const val DOCUMENTS = "documents"
}

// Bottom-Navigation je Projekt (siehe Briefing-Navigationsskizze: Chat /
// Neu anlegen / Dokumente).
@Composable
fun ProjectShellScreen(projectId: Int) {
    val tabNavController = rememberNavController()
    val backStackEntry by tabNavController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route

    // Hier statt in DocumentsTabScreen gehalten, damit eine Quellenangabe im
    // Chat direkt ein Dokument im Dokumente-Tab oeffnen kann (siehe
    // ChatScreen::onOpenDocument), nicht nur ein Tap in dessen eigener Liste.
    var selectedDocumentId by remember { mutableStateOf<Int?>(null) }

    fun navigateToTab(route: String) {
        tabNavController.navigate(route) {
            popUpTo(tabNavController.graph.startDestinationId) { saveState = true }
            launchSingleTop = true
            restoreState = true
        }
    }

    fun openDocument(documentId: Int) {
        selectedDocumentId = documentId
        navigateToTab(ShellTabs.DOCUMENTS)
    }

    Scaffold(
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    selected = currentRoute == ShellTabs.CHAT,
                    onClick = { navigateToTab(ShellTabs.CHAT) },
                    icon = { Icon(Icons.Filled.Chat, contentDescription = null) },
                    label = { Text("Chat") },
                )
                NavigationBarItem(
                    selected = currentRoute == ShellTabs.CREATE,
                    onClick = { navigateToTab(ShellTabs.CREATE) },
                    icon = { Icon(Icons.Filled.AddCircle, contentDescription = null) },
                    label = { Text("Neu anlegen") },
                )
                NavigationBarItem(
                    selected = currentRoute == ShellTabs.DOCUMENTS,
                    onClick = { navigateToTab(ShellTabs.DOCUMENTS) },
                    icon = { Icon(Icons.Filled.Description, contentDescription = null) },
                    label = { Text("Dokumente") },
                )
            }
        },
    ) { padding ->
        NavHost(
            navController = tabNavController,
            startDestination = ShellTabs.CHAT,
            modifier = Modifier.padding(padding),
        ) {
            composable(ShellTabs.CHAT) { ChatScreen(projectId, onOpenDocument = ::openDocument) }
            composable(ShellTabs.CREATE) { CreateScreen(projectId) }
            composable(ShellTabs.DOCUMENTS) {
                DocumentsTabScreen(
                    projectId = projectId,
                    selectedDocumentId = selectedDocumentId,
                    onDocumentSelected = { selectedDocumentId = it },
                )
            }
        }
    }
}
