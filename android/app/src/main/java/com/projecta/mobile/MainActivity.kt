package com.projecta.mobile

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.ui.Modifier
import com.projecta.mobile.navigation.ProjectAApp
import com.projecta.mobile.ui.theme.ProjectAMobileTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        setContent {
            ProjectAMobileTheme {
                Surface(modifier = Modifier.fillMaxSize()) {
                    ProjectAApp()
                }
            }
        }
    }
}
