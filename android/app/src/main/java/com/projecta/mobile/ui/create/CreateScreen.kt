package com.projecta.mobile.ui.create

import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Tab
import androidx.compose.material3.TabRow
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Modifier

private val TAB_TITLES = listOf("Dokument/Notiz", "Foto", "Person", "Meeting")

@Composable
fun CreateScreen(projectId: Int) {
    var selectedTab by remember { mutableIntStateOf(0) }

    Column(modifier = Modifier.fillMaxSize()) {
        TabRow(selectedTabIndex = selectedTab) {
            TAB_TITLES.forEachIndexed { index, title ->
                Tab(
                    selected = selectedTab == index,
                    onClick = { selectedTab = index },
                    text = { Text(title) },
                )
            }
        }
        when (selectedTab) {
            0 -> DocumentFormScreen(projectId)
            1 -> PhotoUploadScreen(projectId)
            2 -> PersonFormScreen(projectId)
            3 -> MeetingFormScreen(projectId)
        }
    }
}
