package com.projecta.mobile.data.repository

import com.projecta.mobile.data.api.ApiResult
import com.projecta.mobile.data.api.ApiSession
import com.projecta.mobile.data.api.apiCall
import com.projecta.mobile.data.dto.DocumentCreateRequestDto
import com.projecta.mobile.data.dto.DocumentDto
import com.projecta.mobile.data.dto.DocumentReviewRequestDto
import com.projecta.mobile.data.dto.DocumentType
import com.projecta.mobile.data.dto.DocumentUpdateRequestDto
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import java.io.File

class DocumentRepository(private val session: ApiSession) {

    suspend fun listDocuments(projectId: Int): ApiResult<List<DocumentDto>> =
        apiCall { session.documentApi.listDocuments(projectId) }

    suspend fun createDocument(
        projectId: Int,
        typ: DocumentType,
        titel: String,
        inhalt: String,
        dokumentdatum: String? = null,
    ): ApiResult<DocumentDto> = apiCall {
        session.documentApi.createDocument(
            projectId,
            DocumentCreateRequestDto(typ = typ, titel = titel, inhalt = inhalt, dokumentdatum = dokumentdatum),
        )
    }

    suspend fun getDocument(projectId: Int, documentId: Int): ApiResult<DocumentDto> =
        apiCall { session.documentApi.getDocument(projectId, documentId) }

    suspend fun uploadImage(
        projectId: Int,
        imageFile: File,
        titel: String?,
        force: Boolean,
    ): ApiResult<DocumentDto> = apiCall {
        // Backend validiert Dateiendung + Inhalt strikt gegeneinander (siehe
        // security/file_safety.py::looks_like_plausible_content) - Content-Type
        // muss daher zur tatsaechlichen Dateiendung passen, nicht pauschal jpeg.
        val mediaType = when (imageFile.extension.lowercase()) {
            "png" -> "image/png"
            else -> "image/jpeg"
        }.toMediaType()
        val filePart = MultipartBody.Part.createFormData(
            "file",
            imageFile.name,
            imageFile.asRequestBody(mediaType),
        )
        val typPart = "bild".toPlainRequestBody()
        val titelPart = titel?.takeIf { it.isNotBlank() }?.toPlainRequestBody()
        val forcePart = force.toString().toPlainRequestBody()

        session.documentApi.uploadDocument(projectId, filePart, typPart, titelPart, forcePart)
    }

    suspend fun confirmReview(projectId: Int, documentId: Int, inhalt: String): ApiResult<DocumentDto> =
        apiCall { session.documentApi.confirmReview(projectId, documentId, DocumentReviewRequestDto(inhalt)) }

    suspend fun updateDocument(
        projectId: Int,
        documentId: Int,
        request: DocumentUpdateRequestDto,
    ): ApiResult<DocumentDto> = apiCall { session.documentApi.updateDocument(projectId, documentId, request) }

    suspend fun deleteDocument(projectId: Int, documentId: Int): ApiResult<Unit> =
        apiCall { session.documentApi.deleteDocument(projectId, documentId) }

    suspend fun reprocessDocument(projectId: Int, documentId: Int): ApiResult<DocumentDto> =
        apiCall { session.documentApi.reprocessDocument(projectId, documentId) }

    suspend fun reprocessAllDocuments(projectId: Int): ApiResult<List<DocumentDto>> =
        apiCall { session.documentApi.reprocessAllDocuments(projectId) }
}

private fun String.toPlainRequestBody(): RequestBody = toRequestBody("text/plain".toMediaType())
