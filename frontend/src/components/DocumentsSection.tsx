import { useEffect, useState } from 'react'
import { api, type Document, type DocumentType } from '../api/client'

type Props = {
  projectId: number
}

const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  meeting: 'Meeting',
  systemeinstellung: 'Systemeinstellung',
  prozess: 'Prozess',
  notiz: 'Notiz',
  sonstiges: 'Sonstiges',
}

const STATUS_LABELS: Record<Document['status'], string> = {
  pending: 'wartet …',
  processing: 'wird verarbeitet …',
  review_required: 'Prüfung ausstehend',
  indexing: 'wird indexiert …',
  ready: 'bereit',
  failed: 'Fehler',
}

function StatusBadge({ status }: { status: Document['status'] }) {
  return <span className={`status-badge status-badge--${status}`}>{STATUS_LABELS[status]}</span>
}

export function DocumentsSection({ projectId }: Props) {
  const [documents, setDocuments] = useState<Document[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [typ, setTyp] = useState<DocumentType>('notiz')
  const [titel, setTitel] = useState('')
  const [inhalt, setInhalt] = useState('')
  const [dokumentdatum, setDokumentdatum] = useState('')
  const [creating, setCreating] = useState(false)
  const [reprocessingId, setReprocessingId] = useState<number | null>(null)

  const loadDocuments = () => {
    api
      .listDocuments(projectId)
      .then(setDocuments)
      .catch((err: Error) => setError(err.message))
  }

  useEffect(() => {
    setDocuments(null)
    loadDocuments()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!titel.trim() || !inhalt.trim()) return
    setCreating(true)
    setError(null)
    try {
      const document = await api.createDocument(projectId, {
        typ,
        titel: titel.trim(),
        inhalt: inhalt.trim(),
        dokumentdatum: dokumentdatum || null,
      })
      setTitel('')
      setInhalt('')
      setDokumentdatum('')
      setDocuments((prev) => [document, ...(prev ?? [])])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setCreating(false)
    }
  }

  const handleReprocess = async (documentId: number) => {
    setReprocessingId(documentId)
    setError(null)
    try {
      const updated = await api.reprocessDocument(projectId, documentId)
      setDocuments((prev) => prev?.map((d) => (d.id === documentId ? updated : d)) ?? null)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setReprocessingId(null)
    }
  }

  return (
    <section className="documents-section">
      <h2>Dokumente</h2>
      {error && <p className="status-error">{error}</p>}

      <form className="create-document-form" onSubmit={handleCreate}>
        <div className="form-row">
          <select value={typ} onChange={(e) => setTyp(e.target.value as DocumentType)}>
            {Object.entries(DOCUMENT_TYPE_LABELS).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <input
            type="text"
            placeholder="Titel"
            value={titel}
            onChange={(e) => setTitel(e.target.value)}
            required
          />
          <input
            type="date"
            value={dokumentdatum}
            onChange={(e) => setDokumentdatum(e.target.value)}
            title="Dokumentdatum (optional, sonst heute)"
          />
        </div>
        <textarea
          placeholder="Inhalt …"
          value={inhalt}
          onChange={(e) => setInhalt(e.target.value)}
          rows={5}
          required
        />
        <button type="submit" disabled={creating}>
          {creating ? 'Wird angelegt …' : 'Dokument anlegen'}
        </button>
      </form>

      {documents === null && !error && <p className="subtitle">Lade Dokumente …</p>}
      {documents?.length === 0 && <p className="subtitle">Noch keine Dokumente vorhanden.</p>}

      <ul className="document-list">
        {documents?.map((doc) => (
          <li key={doc.id} className="document-list-item">
            <div className="document-list-item-header">
              <span className="document-title">{doc.titel}</span>
              <StatusBadge status={doc.status} />
            </div>
            <div className="document-meta">
              {DOCUMENT_TYPE_LABELS[doc.typ]}
              {doc.dokumentdatum && ` · ${doc.dokumentdatum}`}
            </div>
            {doc.status === 'failed' && (
              <div className="document-error">
                <span>{doc.fehlermeldung}</span>
                <button disabled={reprocessingId === doc.id} onClick={() => handleReprocess(doc.id)}>
                  {reprocessingId === doc.id ? 'Wird erneut verarbeitet …' : 'Erneut verarbeiten'}
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
