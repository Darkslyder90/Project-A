import { Fragment, useEffect, useState } from 'react'
import {
  api,
  type Document,
  type DocumentType,
  type Meeting,
  type Person,
  type Tag,
  type Task,
  type TaskStatus,
} from '../api/client'

type Props = {
  projectId: number
}

const DOCUMENT_TYPE_LABELS: Record<DocumentType, string> = {
  meeting: 'Meeting',
  systemeinstellung: 'Systemeinstellung',
  prozess: 'Prozess',
  notiz: 'Notiz',
  datei: 'Datei',
  bild: 'Bild',
  sonstiges: 'Sonstiges',
  email: 'E-Mail',
}

const STATUS_LABELS: Record<Document['status'], string> = {
  pending: 'wartet …',
  processing: 'wird verarbeitet …',
  review_required: 'Prüfung ausstehend',
  indexing: 'wird indexiert …',
  ready: 'bereit',
  failed: 'Fehler',
}

const TASK_STATUS_LABELS: Record<TaskStatus, string> = {
  offen: 'Offen',
  in_arbeit: 'In Arbeit',
  erledigt: 'Erledigt',
}

const KURZTEXT_LAENGE = 140

function kurztext(text: string | null): string {
  if (!text) return ''
  const trimmed = text.trim()
  return trimmed.length > KURZTEXT_LAENGE ? `${trimmed.slice(0, KURZTEXT_LAENGE)}…` : trimmed
}

export function OverviewSection({ projectId }: Props) {
  const [documents, setDocuments] = useState<Document[] | null>(null)
  const [people, setPeople] = useState<Person[] | null>(null)
  const [tasks, setTasks] = useState<Task[] | null>(null)
  const [meetings, setMeetings] = useState<Meeting[] | null>(null)
  const [tags, setTags] = useState<Tag[]>([])
  const [error, setError] = useState<string | null>(null)
  const [expandedDocId, setExpandedDocId] = useState<number | null>(null)

  useEffect(() => {
    setDocuments(null)
    setPeople(null)
    setTasks(null)
    setMeetings(null)
    Promise.all([
      api.listDocuments(projectId).then(setDocuments),
      api.listPeople(projectId).then(setPeople),
      api.listTasks(projectId).then(setTasks),
      api.listMeetings(projectId).then(setMeetings),
      api.listTags(projectId).then(setTags),
    ]).catch((err: Error) => setError(err.message))
  }, [projectId])

  const personName = (id: number | null) => (id === null ? '–' : (people?.find((p) => p.id === id)?.name ?? `#${id}`))
  const documentTitel = (id: number | null) =>
    id === null ? 'Kein Protokoll' : (documents?.find((d) => d.id === id)?.titel ?? `#${id}`)
  const documentExcerpt = (id: number | null) => {
    if (id === null) return '–'
    const doc = documents?.find((d) => d.id === id)
    return doc ? kurztext(doc.inhalt) || '–' : '–'
  }
  const tagName = (id: number) => tags.find((t) => t.id === id)?.name ?? `#${id}`
  const tasksForPerson = (personId: number) => tasks?.filter((t) => t.zugewiesen_an === personId) ?? []

  const loading = documents === null || people === null || tasks === null || meetings === null

  return (
    <section className="overview-section">
      <h2>Übersicht</h2>
      {error && <p className="status-error">{error}</p>}
      {loading && !error && <p className="subtitle">Lade Übersicht …</p>}

      {!loading && (
        <>
          <h3>Dokumente</h3>
          {documents!.length === 0 ? (
            <p className="subtitle">Noch keine Dokumente vorhanden.</p>
          ) : (
            <div className="overview-table-wrap">
              <table className="overview-table">
                <thead>
                  <tr>
                    <th>Titel</th>
                    <th>Typ</th>
                    <th>Datum</th>
                    <th>Status</th>
                    <th>Tags</th>
                    <th>Kurztext</th>
                  </tr>
                </thead>
                <tbody>
                  {documents!.map((doc) => (
                    <Fragment key={doc.id}>
                      <tr
                        className="overview-row-clickable"
                        onClick={() => setExpandedDocId(expandedDocId === doc.id ? null : doc.id)}
                      >
                        <td>{doc.titel}</td>
                        <td>{DOCUMENT_TYPE_LABELS[doc.typ]}</td>
                        <td>{doc.dokumentdatum ?? '–'}</td>
                        <td>
                          <span className={`status-badge status-badge--${doc.status}`}>
                            {STATUS_LABELS[doc.status]}
                          </span>
                        </td>
                        <td>{doc.tag_ids.map((id) => tagName(id)).join(', ') || '–'}</td>
                        <td>{kurztext(doc.inhalt) || '–'}</td>
                      </tr>
                      {expandedDocId === doc.id && (
                        <tr className="overview-expanded-row">
                          <td colSpan={6}>
                            {doc.typ === 'bild' && (
                              <img
                                className="overview-image-preview"
                                src={api.documentFileUrl(projectId, doc.id)}
                                alt={doc.titel}
                              />
                            )}
                            <pre className="overview-fulltext">{doc.inhalt ?? '(kein Inhalt)'}</pre>
                          </td>
                        </tr>
                      )}
                    </Fragment>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3>Personen</h3>
          {people!.length === 0 ? (
            <p className="subtitle">Noch keine Personen erfasst.</p>
          ) : (
            <div className="overview-table-wrap">
              <table className="overview-table">
                <thead>
                  <tr>
                    <th>Name</th>
                    <th>Rolle</th>
                    <th>Aufgaben</th>
                  </tr>
                </thead>
                <tbody>
                  {people!.map((person) => (
                    <tr key={person.id}>
                      <td>{person.name}</td>
                      <td>{person.rolle ?? '–'}</td>
                      <td>{tasksForPerson(person.id).map((t) => t.titel).join(', ') || '–'}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3>Aufgaben</h3>
          {tasks!.length === 0 ? (
            <p className="subtitle">Noch keine Aufgaben erfasst.</p>
          ) : (
            <div className="overview-table-wrap">
              <table className="overview-table">
                <thead>
                  <tr>
                    <th>Titel</th>
                    <th>Status</th>
                    <th>Zugewiesen</th>
                    <th>Dokumente</th>
                  </tr>
                </thead>
                <tbody>
                  {tasks!.map((task) => (
                    <tr key={task.id}>
                      <td>{task.titel}</td>
                      <td>{TASK_STATUS_LABELS[task.status]}</td>
                      <td>{personName(task.zugewiesen_an)}</td>
                      <td>
                        {task.dokument_ids
                          .map((id) => documents?.find((d) => d.id === id)?.titel ?? `#${id}`)
                          .join(', ') || '–'}
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}

          <h3>Meetings</h3>
          {meetings!.length === 0 ? (
            <p className="subtitle">Noch keine Meetings erfasst.</p>
          ) : (
            <div className="overview-table-wrap">
              <table className="overview-table">
                <thead>
                  <tr>
                    <th>Datum</th>
                    <th>Teilnehmer</th>
                    <th>Protokoll</th>
                    <th>Auszug</th>
                  </tr>
                </thead>
                <tbody>
                  {meetings!.map((meeting) => (
                    <tr key={meeting.id}>
                      <td>{meeting.datum}</td>
                      <td>{meeting.teilnehmer_ids.map((id) => personName(id)).join(', ') || '–'}</td>
                      <td>{documentTitel(meeting.document_id)}</td>
                      <td>{documentExcerpt(meeting.document_id)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}
    </section>
  )
}
