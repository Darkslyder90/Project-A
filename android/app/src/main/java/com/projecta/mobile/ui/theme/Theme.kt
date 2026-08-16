package com.projecta.mobile.ui.theme

import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

private val ProjectAColorScheme = darkColorScheme(
    primary = Color(0xFF7C9CFF),
    secondary = Color(0xFFB0C4FF),
    background = Color(0xFF121212),
    surface = Color(0xFF1E1E1E),
)

// Dunkelmodus als Standard (konsistent zum Web-Frontend), unabhaengig vom
// System-Theme - siehe Briefing "Design".
@Composable
fun ProjectAMobileTheme(content: @Composable () -> Unit) {
    MaterialTheme(
        colorScheme = ProjectAColorScheme,
        content = content,
    )
}
