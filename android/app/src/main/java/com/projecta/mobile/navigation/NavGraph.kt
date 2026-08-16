package com.projecta.mobile.navigation

import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.navigation.NavType
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import com.projecta.mobile.data.api.AuthEventBus
import com.projecta.mobile.projectAApplication
import com.projecta.mobile.ui.common.ProjectShellScreen
import com.projecta.mobile.ui.login.LoginScreen
import com.projecta.mobile.ui.projectpicker.ProjectPickerScreen

private object Routes {
    const val LOGIN = "login"
    const val PROJECTS = "projects"
    const val PROJECT_SHELL = "project/{projectId}"
    fun projectShell(projectId: Int) = "project/$projectId"
}

@Composable
fun ProjectAApp() {
    val app = androidx.compose.ui.platform.LocalContext.current.projectAApplication()
    val navController = rememberNavController()
    var pendingLoginError by remember { mutableStateOf<String?>(null) }

    // Zentraler Reflex auf abgelehnte Zugangsdaten (siehe AuthEventBus): egal
    // von welchem Screen aus, immer zurueck zum Login mit Fehlermeldung -
    // siehe Briefing "Auth".
    LaunchedEffect(Unit) {
        AuthEventBus.unauthorized.collect {
            app.apiSession.logout()
            pendingLoginError = "Zugangsdaten wurden vom Server abgelehnt. Bitte erneut anmelden."
            navController.navigate(Routes.LOGIN) {
                popUpTo(0) { inclusive = true }
            }
        }
    }

    val startDestination = if (app.apiSession.isConfigured()) Routes.PROJECTS else Routes.LOGIN

    NavHost(navController = navController, startDestination = startDestination) {
        composable(Routes.LOGIN) {
            LoginScreen(
                prefillErrorMessage = pendingLoginError,
                onLoginSuccess = {
                    pendingLoginError = null
                    navController.navigate(Routes.PROJECTS) {
                        popUpTo(0) { inclusive = true }
                    }
                },
            )
        }
        composable(Routes.PROJECTS) {
            ProjectPickerScreen(
                onProjectSelected = { project -> navController.navigate(Routes.projectShell(project.id)) },
            )
        }
        composable(
            route = Routes.PROJECT_SHELL,
            arguments = listOf(navArgument("projectId") { type = NavType.IntType }),
        ) { backStackEntry ->
            val projectId = backStackEntry.arguments?.getInt("projectId") ?: return@composable
            ProjectShellScreen(projectId = projectId)
        }
    }
}
