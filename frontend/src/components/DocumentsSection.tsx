import { useEffect, useRef, useState } from 'react'
import { ApiError, api, type Document, type DocumentType } from '../api/client'

type Props = {
  projectId: number
}

const ACTIVE_STATUSES: Document['status'][] = ['pending', 'processing', 'indexing']

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

  const [mode, setMode] = useState<'manuell' | 'datei'>('manuell')
  const [uploadTyp, setUploadTyp] = useState<DocumentType>('notiz')
  const [uploadTitel, setUploadTitel] = useState('')
  const [uploadDatum, setUploadDatum] = useState('')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [duplicateHint, setDuplicateHint] = useState<string | null>(null)

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

  // Seit Schritt 8 laeuft die Verarbeitung asynchron im Hintergrund - solange
  // mindestens ein Dokument noch nicht in einem Endzustand ist, wird die Liste
  // periodisch neu geladen, damit Status-Badges automatisch aktuell bleiben.
  const documentsRef = useRef<Document[] | null>(null)
  useEffect(() => {
    documentsRef.current = documents
  }, [documents])

  useEffect(() => {
    const interval = setInterval(() => {
      const current = documentsRef.current
      const hasActiveDocument = current?.some((d) => ACTIVE_STATUSES.includes(d.status))
      if (!hasActiveDocument) return
      api
        .listDocuments(projectId)
        .then(setDocuments)
        .catch(() => {
          // Polling-Fehler ignorieren, der naechste Tick versucht es erneut.
        })
    }, 1500)
    return () => clearInterval(interval)
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

  const handleUpload = async (event: React.FormEvent, force = false) => {
    event.preventDefault()
    if (!uploadFile) return
    setUploading(true)
    setError(null)
    if (!force) setDuplicateHint(null)
    try {
      const document = await api.uploadDocument(projectId, {
        file: uploadFile,
        typ: uploadTyp,
        titel: uploadTitel.trim() || undefined,
        dokumentdatum: uploadDatum || undefined,
        force,
      })
      setUploadFile(null)
      setUploadTitel('')
      setUploadDatum('')
      setDuplicateHint(null)
      setDocuments((prev) => [document, ...(prev ?? [])])
    } catch (err) {
      if (err instanceof ApiError && err.status === 409) {
        setDuplicateHint(err.message)
      } else {
        setError((err as Error).message)
      }
    } finally {
      setUploading(false)
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

      <div className="document-mode-switch">
        <button
          type="button"
          className={mode === 'manuell' ? 'active' : 'link-button'}
          onClick={() => setMode('manuell')}
        >
          Text eingeben
        </button>
        <button
          type="button"
          className={mode === 'datei' ? 'active' : 'link-button'}
          onClick={() => setMode('datei')}
        >
          Datei hochladen
        </button>
      </div>

      {mode === 'manuell' && (
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
      )}

      {mode === 'datei' && (
        <form className="create-document-form" onSubmit={(e) => handleUpload(e, false)}>
          <div className="form-row">
            <select value={uploadTyp} onChange={(e) => setUploadTyp(e.target.value as DocumentType)}>
              {Object.entries(DOCUMENT_TYPE_LABELS).map(([value, label]) => (
                <option key={value} value={value}>
                  {label}
                </option>
              ))}
            </select>
            <input
              type="text"
              placeholder="Titel (optional, sonst Dateiname)"
              value={uploadTitel}
              onChange={(e) => setUploadTitel(e.target.value)}
            />
            <input
              type="date"
              value={uploadDatum}
              onChange={(e) => setUploadDatum(e.target.value)}
              title="Dokumentdatum (optional, sonst aus Datei oder Upload-Zeitpunkt)"
            />
          </div>
          <input
            type="file"
            accept=".pdf,.docx,.txt,.md"
            onChange={(e) => setUploadFile(e.target.files?.[0] ?? null)}
            required
          />
          <p className="subtitle">Unterstützt: PDF, DOCX, TXT, MD.</p>
          {duplicateHint && (
            <div className="document-error">
              <span>{duplicateHint}</span>
              <button type="button" disabled={uploading} onClick={(e) => handleUpload(e, true)}>
                Trotzdem hochladen
              </button>
            </div>
          )}
          <button type="submit" disabled={uploading || !uploadFile}>
            {uploading ? 'Wird hochgeladen …' : 'Hochladen'}
          </button>
        </form>
      )}

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
              {doc.dateiname && (
                <>
                  {' · '}
                  <a href={api.documentFileUrl(projectId, doc.id)} target="_blank" rel="noreferrer">
                    {doc.dateiname}
                  </a>
                </>
              )}
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
