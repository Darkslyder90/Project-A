package com.projecta.mobile.ui.create

import android.content.Context
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.layout.ContentScale
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import androidx.lifecycle.compose.collectAsStateWithLifecycle
import androidx.lifecycle.viewmodel.compose.viewModel
import androidx.lifecycle.viewmodel.initializer
import androidx.lifecycle.viewmodel.viewModelFactory
import coil.compose.AsyncImage
import com.projecta.mobile.data.dto.DocumentStatus
import com.projecta.mobile.projectAApplication
import java.io.File

@Composable
fun PhotoUploadScreen(projectId: Int) {
    val context = LocalContext.current
    val app = context.projectAApplication()
    val viewModel: PhotoUploadViewModel = viewModel(
        key = "photo-upload-$projectId",
        factory = viewModelFactory {
            initializer { PhotoUploadViewModel(projectId, app.documentRepository) }
        },
    )
    val state by viewModel.uiState.collectAsStateWithLifecycle()

    var pendingCameraFile by remember { mutableStateOf<File?>(null) }
    val cameraLauncher = rememberLauncherForActivityResult(ActivityResultContracts.TakePicture()) { success ->
        if (success) {
            pendingCameraFile?.let { viewModel.onImageSelected(it) }
        }
    }
    val galleryLauncher = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri?.let {
            val file = copyUriToCacheFile(context, it)
            if (file != null) {
                viewModel.onImageSelected(file)
            } else {
                viewModel.onUnsupportedImageFormat()
            }
        }
    }

    Column(
        modifier = Modifier
            .fillMaxSize()
            .verticalScroll(rememberScrollState())
            .padding(16.dp),
    ) {
        val document = state.document

        when {
            // Review-Schritt: KI-Analyse bestaetigen/bearbeiten (siehe Briefing
            // "inkl. KI-Analyse/Review-Schritt").
            document != null && document.status == DocumentStatus.REVIEW_REQUIRED -> {
                Text("Bildanalyse pruefen", style = MaterialTheme.typography.titleMedium)
                Text(
                    "Von der KI erkannter Text - bei Bedarf korrigieren, bevor er indexiert wird.",
                    style = MaterialTheme.typography.bodySmall,
                    modifier = Modifier.padding(top = 4.dp, bottom = 12.dp),
                )
                OutlinedTextField(
                    value = state.reviewInhalt,
                    onValueChange = viewModel::onReviewInhaltChange,
                    minLines = 8,
                    modifier = Modifier.fillMaxWidth(),
                )
                Button(
                    onClick = viewModel::confirmReview,
                    enabled = !state.isConfirming && state.reviewInhalt.isNotBlank(),
                    modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
                ) {
                    if (state.isConfirming) {
                        CircularProgressIndicator(modifier = Modifier.size(20.dp))
                    } else {
                        Text("Bestaetigen")
                    }
                }
            }

            state.isProcessing -> {
                Column(
                    modifier = Modifier.fillMaxWidth().padding(top = 32.dp),
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    CircularProgressIndicator()
                    Text("Bild wird verarbeitet …", modifier = Modifier.padding(top = 12.dp))
                }
            }

            else -> {
                Text("Neues Foto", style = MaterialTheme.typography.titleMedium)
                Row(
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    modifier = Modifier.padding(top = 12.dp),
                ) {
                    OutlinedButton(onClick = {
                        val file = createImageCaptureFile(context)
                        pendingCameraFile = file
                        val uri = FileProvider.getUriForFile(context, "${context.packageName}.fileprovider", file)
                        cameraLauncher.launch(uri)
                    }) { Text("Kamera") }
                    OutlinedButton(onClick = { galleryLauncher.launch("image/*") }) { Text("Galerie") }
                }

                state.imageFile?.let { file ->
                    AsyncImage(
                        model = file,
                        contentDescription = null,
                        contentScale = ContentScale.Fit,
                        modifier = Modifier.fillMaxWidth().height(220.dp).padding(top = 16.dp),
                    )

                    OutlinedTextField(
                        value = state.titel,
                        onValueChange = viewModel::onTitelChange,
                        label = { Text("Titel (optional)") },
                        singleLine = true,
                        modifier = Modifier.fillMaxWidth().padding(top = 16.dp),
                    )

                    Row(
                        verticalAlignment = Alignment.CenterVertically,
                        modifier = Modifier.padding(top = 8.dp),
                    ) {
                        Checkbox(checked = state.forceDuplicate, onCheckedChange = viewModel::onForceDuplicateChange)
                        Text("Trotzdem hochladen (Duplikat-Pruefung ignorieren)")
                    }

                    Button(
                        onClick = viewModel::upload,
                        enabled = !state.isUploading,
                        modifier = Modifier.fillMaxWidth().padding(top = 12.dp),
                    ) {
                        if (state.isUploading) {
                            CircularProgressIndicator(modifier = Modifier.size(20.dp))
                        } else {
                            Text("Hochladen")
                        }
                    }
                }
            }
        }

        state.errorMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(top = 16.dp))
        }
        state.savedMessage?.let {
            Text(it, color = MaterialTheme.colorScheme.primary, modifier = Modifier.padding(top = 16.dp))
        }
    }
}

private fun createImageCaptureFile(context: Context): File {
    val dir = File(context.cacheDir, "photo_uploads").apply { mkdirs() }
    return File(dir, "capture_${System.currentTimeMillis()}.jpg")
}

// Nur JPG/PNG werden vom Backend akzeptiert (siehe
// security/file_safety.py::IMAGE_EXTENSIONS) - die Dateiendung muss dabei zum
// echten Bildformat passen, daher hier ueber den MIME-Typ bestimmt statt
// pauschal ".jpg" anzunehmen wie bei der Kamera-Aufnahme (die immer JPEG
// liefert).
private fun copyUriToCacheFile(context: Context, uri: Uri): File? {
    val extension = when (context.contentResolver.getType(uri)) {
        "image/jpeg" -> "jpg"
        "image/png" -> "png"
        else -> null
    } ?: return null

    val dir = File(context.cacheDir, "photo_uploads").apply { mkdirs() }
    val file = File(dir, "gallery_${System.currentTimeMillis()}.$extension")
    context.contentResolver.openInputStream(uri)?.use { input ->
        file.outputStream().use { output -> input.copyTo(output) }
    }
    return file
}
