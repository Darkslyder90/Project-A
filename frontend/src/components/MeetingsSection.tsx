import { useEffect, useState } from 'react'
import { api, type Document, type Meeting, type Person } from '../api/client'

type Props = {
  projectId: number
}

export function MeetingsSection({ projectId }: Props) {
  const [meetings, setMeetings] = useState<Meeting[] | null>(null)
  const [people, setPeople] = useState<Person[]>([])
  const [documents, setDocuments] = useState<Document[]>([])
  const [error, setError] = useState<string | null>(null)

  const [datum, setDatum] = useState('')
  const [documentId, setDocumentId] = useState('')
  const [zusammenfassung, setZusammenfassung] = useState('')
  const [teilnehmerIds, setTeilnehmerIds] = useState<number[]>([])
  const [creating, setCreating] = useState(false)

  const loadMeetings = () => {
    api
      .listMeetings(projectId)
      .then(setMeetings)
      .catch((err: Error) => setError(err.message))
  }

  useEffect(() => {
    setMeetings(null)
    loadMeetings()
    api.listPeople(projectId).then(setPeople).catch(() => {})
    api.listDocuments(projectId).then(setDocuments).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const personName = (id: number) => people.find((p) => p.id === id)?.name ?? `#${id}`
  const documentTitel = (id: number | null) =>
    id === null ? 'Kein Protokoll' : (documents.find((d) => d.id === id)?.titel ?? `#${id}`)
  // Dokumente, die schon ein anderes Meeting tragen, stehen fuer ein neues nicht mehr zur Auswahl.
  const usedDocumentIds = new Set(meetings?.map((m) => m.document_id).filter((id) => id !== null) ?? [])
  const availableDocuments = documents.filter((d) => !usedDocumentIds.has(d.id))

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!datum) return
    setCreating(true)
    setError(null)
    try {
      const meeting = await api.createMeeting(projectId, {
        datum,
        document_id: documentId ? Number(documentId) : null,
        zusammenfassung: zusammenfassung.trim() || null,
        teilnehmer_ids: teilnehmerIds,
      })
      setDatum('')
      setDocumentId('')
      setZusammenfassung('')
      setTeilnehmerIds([])
      setMeetings((prev) => [meeting, ...(prev ?? [])])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setCreating(false)
    }
  }

  const handleDelete = async (meeting: Meeting) => {
    const hint = meeting.document_id !== null ? ' Das verknüpfte Protokoll-Dokument wird dabei mitgelöscht.' : ''
    if (!confirm(`Dieses Meeting wirklich löschen?${hint}`)) return
    setError(null)
    try {
      await api.deleteMeeting(projectId, meeting.id)
      setMeetings((prev) => prev?.filter((m) => m.id !== meeting.id) ?? null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <section className="meetings-section">
      <h2>Meetings</h2>
      {error && <p className="status-error">{error}</p>}

      <form className="create-meeting-form" onSubmit={handleCreate}>
        <div className="form-row">
          <input type="date" value={datum} onChange={(e) => setDatum(e.target.value)} required />
          <select value={documentId} onChange={(e) => setDocumentId(e.target.value)}>
            <option value="">Kein Protokoll-Dokument</option>
            {availableDocuments.map((d) => (
              <option key={d.id} value={d.id}>
                {d.titel}
              </option>
            ))}
          </select>
        </div>
        <textarea
          placeholder="Zusammenfassung …"
          value={zusammenfassung}
          onChange={(e) => setZusammenfassung(e.target.value)}
          rows={2}
        />
        {people.length > 0 && (
          <label className="form-field-label">
            Teilnehmer
            <select
              multiple
              value={teilnehmerIds.map(String)}
              onChange={(e) =>
                setTeilnehmerIds(Array.from(e.target.selectedOptions).map((o) => Number(o.value)))
              }
            >
              {people.map((p) => (
                <option key={p.id} value={p.id}>
                  {p.name}
                </option>
              ))}
            </select>
          </label>
        )}
        <button type="submit" disabled={creating || !datum}>
          {creating ? 'Wird angelegt …' : 'Meeting anlegen'}
        </button>
      </form>

      {meetings === null && !error && <p className="subtitle">Lade Meetings …</p>}
      {meetings?.length === 0 && <p className="subtitle">Noch keine Meetings erfasst.</p>}

      <ul className="entity-list">
        {meetings?.map((meeting) => (
          <li key={meeting.id} className="entity-list-item">
            <div className="entity-list-item-header">
              <span className="entity-title">{meeting.datum}</span>
              <span className="entity-meta">{documentTitel(meeting.document_id)}</span>
            </div>
            {meeting.teilnehmer_ids.length > 0 && (
              <div className="entity-meta">
                Teilnehmer: {meeting.teilnehmer_ids.map((id) => personName(id)).join(', ')}
              </div>
            )}
            {meeting.zusammenfassung && <p className="entity-notes">{meeting.zusammenfassung}</p>}
            <div className="entity-actions">
              <button className="link-button" onClick={() => handleDelete(meeting)}>
                Löschen
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
