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

export type DocumentType = 'meeting' | 'systemeinstellung' | 'prozess' | 'notiz' | 'sonstiges'

export type DocumentStatus = 'pending' | 'processing' | 'review_required' | 'indexing' | 'ready' | 'failed'

export type Document = {
  id: number
  project_id: number
  typ: DocumentType
  titel: string
  inhalt: string | null
  status: DocumentStatus
  fehlermeldung: string | null
  dokumentdatum: string | null
  erstellt_am: string
  aktualisiert_am: string
}

export type DocumentCreateInput = {
  typ: DocumentType
  titel: string
  inhalt: string
  dokumentdatum?: string | null
}

export type RetrievalHit = {
  chunk_id: string
  document_id: number
  document_titel: string
  vector_rank: number
  vector_score: number
  text: string
  dokumenttyp: DocumentType | null
  dokumentdatum: string | null
  abschnitt: string | null
}

export type ChatSource = {
  source_id: string
  document_id: number
  document_titel: string
  dokumentdatum: string | null
  abschnitt: string | null
  text: string
}

export type ChatResponse = {
  antwort: string
  quellen: ChatSource[]
  unbekannte_zitate: string[]
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Anfrage fehlgeschlagen (${response.status})`)
  }
  if (response.status === 204) {
    return undefined as T
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

  testRetrieval: (projectId: number, query: string, topK = 5) =>
    request<RetrievalHit[]>(`/api/projects/${projectId}/retrieval-test`, {
      method: 'POST',
      body: JSON.stringify({ query, top_k: topK }),
    }),

  askChat: (projectId: number, query: string) =>
    request<ChatResponse>(`/api/projects/${projectId}/chat`, {
      method: 'POST',
      body: JSON.stringify({ query }),
    }),
}
