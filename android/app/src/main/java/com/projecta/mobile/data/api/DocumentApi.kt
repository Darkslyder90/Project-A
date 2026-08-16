package com.projecta.mobile.data.api

import com.projecta.mobile.data.dto.DocumentCreateRequestDto
import com.projecta.mobile.data.dto.DocumentDto
import com.projecta.mobile.data.dto.DocumentReviewRequestDto
import com.projecta.mobile.data.dto.DocumentUpdateRequestDto
import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.DELETE
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.PATCH
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path

interface DocumentApi {
    @GET("api/projects/{projectId}/documents")
    suspend fun listDocuments(@Path("projectId") projectId: Int): List<DocumentDto>

    @POST("api/projects/{projectId}/documents")
    suspend fun createDocument(
        @Path("projectId") projectId: Int,
        @Body request: DocumentCreateRequestDto,
    ): DocumentDto

    @GET("api/projects/{projectId}/documents/{documentId}")
    suspend fun getDocument(
        @Path("projectId") projectId: Int,
        @Path("documentId") documentId: Int,
    ): DocumentDto

    @Multipart
    @POST("api/projects/{projectId}/documents/upload")
    suspend fun uploadDocument(
        @Path("projectId") projectId: Int,
        @Part file: MultipartBody.Part,
        @Part("typ") typ: RequestBody,
        @Part("titel") titel: RequestBody?,
        @Part("force") force: RequestBody,
    ): DocumentDto

    @PATCH("api/projects/{projectId}/documents/{documentId}")
    suspend fun updateDocument(
        @Path("projectId") projectId: Int,
        @Path("documentId") documentId: Int,
        @Body request: DocumentUpdateRequestDto,
    ): DocumentDto

    @POST("api/projects/{projectId}/documents/{documentId}/review")
    suspend fun confirmReview(
        @Path("projectId") projectId: Int,
        @Path("documentId") documentId: Int,
        @Body request: DocumentReviewRequestDto,
    ): DocumentDto

    @DELETE("api/projects/{projectId}/documents/{documentId}")
    suspend fun deleteDocument(@Path("projectId") projectId: Int, @Path("documentId") documentId: Int)

    @POST("api/projects/{projectId}/documents/{documentId}/reprocess")
    suspend fun reprocessDocument(
        @Path("projectId") projectId: Int,
        @Path("documentId") documentId: Int,
    ): DocumentDto

    @POST("api/projects/{projectId}/documents/reprocess-all")
    suspend fun reprocessAllDocuments(@Path("projectId") projectId: Int): List<DocumentDto>
}
