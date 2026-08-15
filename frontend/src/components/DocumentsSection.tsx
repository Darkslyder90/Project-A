import { useEffect, useRef, useState } from 'react'
import { ApiError, api, type Document, type DocumentType, type Tag } from '../api/client'
import { useSpeechDictation } from '../hooks/useSpeechDictation'

type Props = {
  projectId: number
}

const ACTIVE_STATUSES: Document['status'][] = ['pending', 'processing', 'indexing']

const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  meeting: 'Meeting',
  systemeinstellung: 'Systemeinstellung',
  prozess: 'Prozess',
  notiz: 'Notiz',
  datei: 'Datei',
  bild: 'Bild',
  sonstiges: 'Sonstiges',
}

// Nur diese Typen sind ueber die Formulare waehlbar - 'datei'/'bild' werden
// beim Upload serverseitig automatisch gesetzt (siehe document_service.py).
const SELECTABLE_DOCUMENT_TYPES: DocumentType[] = [
  'meeting',
  'systemeinstellung',
  'prozess',
  'notiz',
  'sonstiges',
]

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
  const [deletingId, setDeletingId] = useState<number | null>(null)

  // Spracheingabe fuer den Inhalt (siehe hooks/useSpeechDictation.ts) - haengt
  // erkannten Text an, statt ihn zu ersetzen (mehrere Diktier-Durchgaenge moeglich).
  const dictation = useSpeechDictation((text) =>
    setInhalt((prev) => (prev.trim() ? `${prev.trim()} ${text}` : text)),
  )

  const [mode, setMode] = useState<'manuell' | 'datei' | 'bild'>('manuell')
  const [uploadTyp, setUploadTyp] = useState<DocumentType>('notiz')
  const [uploadTitel, setUploadTitel] = useState('')
  const [uploadDatum, setUploadDatum] = useState('')
  const [uploadFile, setUploadFile] = useState<File | null>(null)
  const [uploading, setUploading] = useState(false)
  const [duplicateHint, setDuplicateHint] = useState<string | null>(null)

  const [imageTitel, setImageTitel] = useState('')
  const [imageDatum, setImageDatum] = useState('')
  const [imageFile, setImageFile] = useState<File | null>(null)
  const [uploadingImage, setUploadingImage] = useState(false)

  // Entwurf der bestaetigten/bearbeiteten Analyse pro Dokument-ID, waehrend der
  // Review-Schritt (status=review_required) noch offen ist (Schritt 9).
  const [reviewDrafts, setReviewDrafts] = useState<Record<number, string>>({})
  const [submittingReviewId, setSubmittingReviewId] = useState<number | null>(null)

  const [tags, setTags] = useState<Tag[]>([])
  const [newTagDrafts, setNewTagDrafts] = useState<Record<number, string>>({})

  const loadDocuments = () => {
    api
      .listDocuments(projectId)
      .then(setDocuments)
      .catch((err: Error) => setError(err.message))
  }

  const loadTags = () => {
    api.listTags(projectId).then(setTags).catch(() => {})
  }

  useEffect(() => {
    setDocuments(null)
    loadDocuments()
    loadTags()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const tagName = (id: number) => tags.find((t) => t.id === id)?.name ?? `#${id}`

  const handleAddTag = async (documentId: number) => {
    const name = (newTagDrafts[documentId] ?? '').trim()
    if (!name) return
    setError(null)
    try {
      const updated = await api.assignTag(projectId, documentId, name)
      setDocuments((prev) => prev?.map((d) => (d.id === documentId ? updated : d)) ?? null)
      setNewTagDrafts((prev) => ({ ...prev, [documentId]: '' }))
      loadTags()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const handleRemoveTag = async (documentId: number, tagId: number) => {
    setError(null)
    try {
      const updated = await api.unassignTag(projectId, documentId, tagId)
      setDocuments((prev) => prev?.map((d) => (d.id === documentId ? updated : d)) ?? null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

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

  const handleImageUpload = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!imageFile) return
    setUploadingImage(true)
    setError(null)
    try {
      const document = await api.uploadDocument(projectId, {
        file: imageFile,
        typ: 'bild',
        titel: imageTitel.trim() || undefined,
        dokumentdatum: imageDatum || undefined,
      })
      setImageFile(null)
      setImageTitel('')
      setImageDatum('')
      setDocuments((prev) => [document, ...(prev ?? [])])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setUploadingImage(false)
    }
  }

  const handleSubmitReview = async (documentId: number, inhalt: string) => {
    if (!inhalt.trim()) return
    setSubmittingReviewId(documentId)
    setError(null)
    try {
      const updated = await api.submitDocumentReview(projectId, documentId, inhalt.trim())
      setDocuments((prev) => prev?.map((d) => (d.id === documentId ? updated : d)) ?? null)
      setReviewDrafts((prev) => {
        const next = { ...prev }
        delete next[documentId]
        return next
      })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSubmittingReviewId(null)
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

  const handleDelete = async (documentId: number) => {
    if (!confirm('Dieses Dokument wirklich löschen?')) return
    setDeletingId(documentId)
    setError(null)
    try {
      await api.deleteDocument(projectId, documentId)
      setDocuments((prev) => prev?.filter((d) => d.id !== documentId) ?? null)
    } catch (err) {
      // 409: Dokument ist das Protokoll eines Meetings (siehe Briefing) - klare
      // Fehlermeldung statt eines generischen Fehlschlags.
      setError((err as Error).message)
    } finally {
      setDeletingId(null)
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
        <button
          type="button"
          className={mode === 'bild' ? 'active' : 'link-button'}
          onClick={() => setMode('bild')}
        >
          Bild hochladen
        </button>
      </div>

      {mode === 'manuell' && (
        <form className="create-document-form" onSubmit={handleCreate}>
          <div className="form-row">
            <select value={typ} onChange={(e) => setTyp(e.target.value as DocumentType)}>
              {SELECTABLE_DOCUMENT_TYPES.map((value) => (
                <option key={value} value={value}>
                  {DOCUMENT_TYPE_LABELS[value]}
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
          {dictation.supported && (
            <div className="dictation-row">
              <button
                type="button"
                className={dictation.dictating ? 'active' : 'link-button'}
                onClick={dictation.toggle}
              >
                {dictation.dictating ? '⏹ Aufnahme beenden' : '🎤 Diktieren'}
              </button>
              {dictation.dictating && (
                <span className="subtitle">
                  Läuft … Spracherkennung des Browsers, Audio verlässt dafür deinen Rechner (nicht
                  Project-A selbst).
                </span>
              )}
            </div>
          )}
          <button type="submit" disabled={creating}>
            {creating ? 'Wird angelegt …' : 'Dokument anlegen'}
          </button>
        </form>
      )}

      {mode === 'datei' && (
        <form className="create-document-form" onSubmit={(e) => handleUpload(e, false)}>
          <div className="form-row">
            <select value={uploadTyp} onChange={(e) => setUploadTyp(e.target.value as DocumentType)}>
              {SELECTABLE_DOCUMENT_TYPES.map((value) => (
                <option key={value} value={value}>
                  {DOCUMENT_TYPE_LABELS[value]}
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

      {mode === 'bild' && (
        <form className="create-document-form" onSubmit={handleImageUpload}>
          <div className="form-row">
            <input
              type="text"
              placeholder="Titel (optional, sonst Dateiname)"
              value={imageTitel}
              onChange={(e) => setImageTitel(e.target.value)}
            />
            <input
              type="date"
              value={imageDatum}
              onChange={(e) => setImageDatum(e.target.value)}
              title="Dokumentdatum (optional, sonst Upload-Zeitpunkt)"
            />
          </div>
          <input
            type="file"
            accept=".png,.jpg,.jpeg"
            onChange={(e) => setImageFile(e.target.files?.[0] ?? null)}
            required
          />
          <p className="subtitle">
            Unterstützt: PNG, JPG. Das Bild wird zur Analyse (Texterkennung + Beschreibung)
            an die Claude API übertragen; das Ergebnis prüfst du anschließend im Review-Schritt,
            bevor es indexiert wird.
          </p>
          <button type="submit" disabled={uploadingImage || !imageFile}>
            {uploadingImage ? 'Wird hochgeladen …' : 'Hochladen'}
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
            <div className="tag-list">
              {doc.tag_ids.map((tagId) => (
                <span key={tagId} className="tag-chip">
                  {tagName(tagId)}
                  <button type="button" onClick={() => handleRemoveTag(doc.id, tagId)}>
                    ×
                  </button>
                </span>
              ))}
              <input
                type="text"
                className="tag-input"
                placeholder="+ Tag"
                value={newTagDrafts[doc.id] ?? ''}
                onChange={(e) => setNewTagDrafts((prev) => ({ ...prev, [doc.id]: e.target.value }))}
                onKeyDown={(e) => {
                  if (e.key === 'Enter') {
                    e.preventDefault()
                    handleAddTag(doc.id)
                  }
                }}
              />
            </div>
            <div className="entity-actions">
              {(doc.status === 'ready' || doc.status === 'failed') && (
                <button
                  className="link-button"
                  disabled={reprocessingId === doc.id}
                  onClick={() => handleReprocess(doc.id)}
                >
                  {reprocessingId === doc.id ? 'Wird neu indexiert …' : 'Neu indexieren'}
                </button>
              )}
              <button
                className="link-button"
                disabled={deletingId === doc.id}
                onClick={() => handleDelete(doc.id)}
              >
                {deletingId === doc.id ? 'Wird gelöscht …' : 'Löschen'}
              </button>
            </div>
            {doc.status === 'failed' && doc.fehlermeldung && (
              <div className="document-error">
                <span>{doc.fehlermeldung}</span>
              </div>
            )}
            {doc.status === 'review_required' && (
              <div className="document-review-panel">
                {doc.ocr_text && (
                  <div>
                    <p className="subtitle">Im Bild erkannter Text (OCR):</p>
                    <pre className="document-review-ocr">{doc.ocr_text}</pre>
                  </div>
                )}
                <p className="subtitle">
                  KI-Analyse – bitte prüfen und bei Bedarf korrigieren, bevor sie als Inhalt
                  übernommen wird:
                </p>
                <textarea
                  rows={5}
                  value={reviewDrafts[doc.id] ?? doc.ki_analyse_rohtext ?? ''}
                  onChange={(e) =>
                    setReviewDrafts((prev) => ({ ...prev, [doc.id]: e.target.value }))
                  }
                />
                <button
                  disabled={submittingReviewId === doc.id}
                  onClick={() =>
                    handleSubmitReview(doc.id, reviewDrafts[doc.id] ?? doc.ki_analyse_rohtext ?? '')
                  }
                >
                  {submittingReviewId === doc.id ? 'Wird übernommen …' : 'Bestätigen & übernehmen'}
                </button>
              </div>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
