export type Project = {
  id: number
  name: string
  beschreibung: string | null
  erstellt_am: string
}

export type ProjectCreateInput = {
  name: string
  beschreibung?: string | null
}

export type DocumentType =
  | 'meeting'
  | 'systemeinstellung'
  | 'prozess'
  | 'notiz'
  | 'datei'
  | 'bild'
  | 'sonstiges'

export type DocumentStatus = 'pending' | 'processing' | 'review_required' | 'indexing' | 'ready' | 'failed'

export type Document = {
  id: number
  project_id: number
  typ: DocumentType
  titel: string
  inhalt: string | null
  ocr_text: string | null
  ki_analyse_rohtext: string | null
  status: DocumentStatus
  fehlermeldung: string | null
  dokumentdatum: string | null
  dateiname: string | null
  erstellt_am: string
  aktualisiert_am: string
}

export type DocumentCreateInput = {
  typ: DocumentType
  titel: string
  inhalt: string
  dokumentdatum?: string | null
}

export type DocumentUploadInput = {
  file: File
  typ: DocumentType
  titel?: string
  dokumentdatum?: string
  force?: boolean
}

export type GefundenUeber = 'vector' | 'keyword' | 'beide'

export type RetrievalHit = {
  chunk_id: string
  document_id: number
  document_titel: string
  vector_rank: number | null
  vector_score: number | null
  keyword_rank: number | null
  keyword_score: number | null
  fusion_rank: number
  gefunden_ueber: GefundenUeber
  text: string
  dokumenttyp: DocumentType | null
  dokumentdatum: string | null
  abschnitt: string | null
}

export type ChatSourceSnapshot = {
  source_id: string
  document_id: number
  document_titel: string
  dokumentdatum: string | null
  abschnitt: string | null
  text_ausschnitt: string
  geloescht: boolean
}

export type ChatRole = 'user' | 'assistant'

export type ChatMessage = {
  id: number
  conversation_id: number
  rolle: ChatRole
  text: string
  quellen: ChatSourceSnapshot[] | null
  erstellt_am: string
}

export type ChatConversation = {
  id: number
  project_id: number
  titel: string | null
  erstellt_am: string
  zuletzt_aktualisiert_am: string
}

export type ChatConversationDetail = ChatConversation & {
  nachrichten: ChatMessage[]
}

export type SendMessageResponse = {
  conversation: ChatConversation
  nachricht: ChatMessage
}

export type Person = {
  id: number
  project_id: number
  name: string
  rolle: string | null
  kontaktinfo: string | null
  notizen: string | null
}

export type PersonCreateInput = {
  name: string
  rolle?: string | null
  kontaktinfo?: string | null
  notizen?: string | null
}

export type PersonUpdateInput = Partial<PersonCreateInput>

export type TaskStatus = 'offen' | 'in_arbeit' | 'erledigt'

export type Task = {
  id: number
  project_id: number
  titel: string
  beschreibung: string | null
  status: TaskStatus
  zugewiesen_an: number | null
  faellig_am: string | null
  dokument_ids: number[]
}

export type TaskCreateInput = {
  titel: string
  beschreibung?: string | null
  status?: TaskStatus
  zugewiesen_an?: number | null
  faellig_am?: string | null
  dokument_ids?: number[]
}

export type TaskUpdateInput = {
  titel?: string
  beschreibung?: string | null
  status?: TaskStatus
  zugewiesen_an?: number | null
  faellig_am?: string | null
}

export type Meeting = {
  id: number
  project_id: number
  datum: string
  document_id: number | null
  zusammenfassung: string | null
  teilnehmer_ids: number[]
}

export type MeetingCreateInput = {
  datum: string
  document_id?: number | null
  zusammenfassung?: string | null
  teilnehmer_ids?: number[]
}

export type MeetingUpdateInput = {
  datum?: string
  zusammenfassung?: string | null
  document_id?: number | null
}

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.detail ?? `Anfrage fehlgeschlagen (${response.status})`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

// Kein 'Content-Type'-Header hier - der Browser setzt bei FormData automatisch
// die korrekte multipart/form-data-Boundary. Ein manueller JSON-Header wuerde
// den Upload kaputt machen.
async function requestForm<T>(path: string, formData: FormData): Promise<T> {
  const response = await fetch(path, { method: 'POST', body: formData })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new ApiError(response.status, body?.detail ?? `Anfrage fehlgeschlagen (${response.status})`)
  }
  return response.json() as Promise<T>
}

export const api = {
  listProjects: () => request<Project[]>('/api/projects'),
  createProject: (input: ProjectCreateInput) =>
    request<Project>('/api/projects', { method: 'POST', body: JSON.stringify(input) }),
  deleteProject: (id: number) => request<void>(`/api/projects/${id}`, { method: 'DELETE' }),

  listDocuments: (projectId: number) => request<Document[]>(`/api/projects/${projectId}/documents`),
  createDocument: (projectId: number, input: DocumentCreateInput) =>
    request<Document>(`/api/projects/${projectId}/documents`, {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  reprocessDocument: (projectId: number, documentId: number) =>
    request<Document>(`/api/projects/${projectId}/documents/${documentId}/reprocess`, {
      method: 'POST',
    }),
  submitDocumentReview: (projectId: number, documentId: number, inhalt: string) =>
    request<Document>(`/api/projects/${projectId}/documents/${documentId}/review`, {
      method: 'POST',
      body: JSON.stringify({ inhalt }),
    }),
  uploadDocument: (projectId: number, input: DocumentUploadInput) => {
    const formData = new FormData()
    formData.append('file', input.file)
    formData.append('typ', input.typ)
    if (input.titel) formData.append('titel', input.titel)
    if (input.dokumentdatum) formData.append('dokumentdatum', input.dokumentdatum)
    if (input.force) formData.append('force', 'true')
    return requestForm<Document>(`/api/projects/${projectId}/documents/upload`, formData)
  },
  documentFileUrl: (projectId: number, documentId: number) =>
    `/api/projects/${projectId}/documents/${documentId}/file`,
  deleteDocument: (projectId: number, documentId: number) =>
    request<void>(`/api/projects/${projectId}/documents/${documentId}`, { method: 'DELETE' }),

  testRetrieval: (projectId: number, query: string, topK = 5) =>
    request<RetrievalHit[]>(`/api/projects/${projectId}/retrieval-test`, {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    }),

  listConversations: (projectId: number) =>
    request<ChatConversation[]>(`/api/projects/${projectId}/chat/conversations`),
  createConversation: (projectId: number) =>
    request<ChatConversation>(`/api/projects/${projectId}/chat/conversations`, { method: 'POST' }),
  getConversation: (projectId: number, conversationId: number) =>
    request<ChatConversationDetail>(
      `/api/projects/${projectId}/chat/conversations/${conversationId}`,
    ),
  renameConversation: (projectId: number, conversationId: number, titel: string) =>
    request<ChatConversation>(
      `/api/projects/${projectId}/chat/conversations/${conversationId}`,
      { method: 'PATCH', body: JSON.stringify({ titel }) },
    ),
  deleteConversation: (projectId: number, conversationId: number) =>
    request<void>(`/api/projects/${projectId}/chat/conversations/${conversationId}`, {
      method: 'DELETE',
    }),
  sendMessage: (projectId: number, conversationId: number, query: string) =>
    request<SendMessageResponse>(
      `/api/projects/${projectId}/chat/conversations/${conversationId}/messages`,
      { method: 'POST', body: JSON.stringify({ query }) },
    ),

  listPeople: (projectId: number) => request<Person[]>(`/api/projects/${projectId}/people`),
  createPerson: (projectId: number, input: PersonCreateInput) =>
    request<Person>(`/api/projects/${projectId}/people`, { method: 'POST', body: JSON.stringify(input) }),
  updatePerson: (projectId: number, personId: number, input: PersonUpdateInput) =>
    request<Person>(`/api/projects/${projectId}/people/${personId}`, {
      method: 'PATCH',
      body: JSON.stringify(input),
    }),
  deletePerson: (projectId: number, personId: number) =>
    request<void>(`/api/projects/${projectId}/people/${personId}`, { method: 'DELETE' }),

  listTasks: (projectId: number, statusFilter?: TaskStatus) =>
    request<Task[]>(
      `/api/projects/${projectId}/tasks${statusFilter ? `?status_filter=${statusFilter}` : ''}`,
    ),
  createTask: (projectId: number, input: TaskCreateInput) =>
    request<Task>(`/api/projects/${projectId}/tasks`, { method: 'POST', body: JSON.stringify(input) }),
  updateTask: (projectId: number, taskId: number, input: TaskUpdateInput) =>
    request<Task>(`/api/projects/${projectId}/tasks/${taskId}`, {
      method: 'PATCH',
      body: JSON.stringify(input),
    }),
  deleteTask: (projectId: number, taskId: number) =>
    request<void>(`/api/projects/${projectId}/tasks/${taskId}`, { method: 'DELETE' }),
  linkTaskDocument: (projectId: number, taskId: number, documentId: number) =>
    request<Task>(`/api/projects/${projectId}/tasks/${taskId}/documents/${documentId}`, {
      method: 'POST',
    }),
  unlinkTaskDocument: (projectId: number, taskId: number, documentId: number) =>
    request<Task>(`/api/projects/${projectId}/tasks/${taskId}/documents/${documentId}`, {
      method: 'DELETE',
    }),

  listMeetings: (projectId: number) => request<Meeting[]>(`/api/projects/${projectId}/meetings`),
  createMeeting: (projectId: number, input: MeetingCreateInput) =>
    request<Meeting>(`/api/projects/${projectId}/meetings`, {
      method: 'POST',
      body: JSON.stringify(input),
    }),
  updateMeeting: (projectId: number, meetingId: number, input: MeetingUpdateInput) =>
    request<Meeting>(`/api/projects/${projectId}/meetings/${meetingId}`, {
      method: 'PATCH',
      body: JSON.stringify(input),
    }),
  deleteMeeting: (projectId: number, meetingId: number) =>
    request<void>(`/api/projects/${projectId}/meetings/${meetingId}`, { method: 'DELETE' }),
  addMeetingParticipant: (projectId: number, meetingId: number, personId: number) =>
    request<Meeting>(`/api/projects/${projectId}/meetings/${meetingId}/participants/${personId}`, {
      method: 'POST',
    }),
  removeMeetingParticipant: (projectId: number, meetingId: number, personId: number) =>
    request<Meeting>(`/api/projects/${projectId}/meetings/${meetingId}/participants/${personId}`, {
      method: 'DELETE',
    }),
}
