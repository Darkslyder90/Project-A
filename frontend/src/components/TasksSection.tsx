import { useEffect, useState } from 'react'
import { api, type Document, type Person, type Task, type TaskStatus } from '../api/client'

type Props = {
  projectId: number
}

const STATUS_LABELS: Record<TaskStatus, string> = {
  offen: 'Offen',
  in_arbeit: 'In Arbeit',
  erledigt: 'Erledigt',
}

export function TasksSection({ projectId }: Props) {
  const [tasks, setTasks] = useState<Task[] | null>(null)
  const [people, setPeople] = useState<Person[]>([])
  const [documents, setDocuments] = useState<Document[]>([])
  const [error, setError] = useState<string | null>(null)
  const [filter, setFilter] = useState<TaskStatus | ''>('')

  const [titel, setTitel] = useState('')
  const [beschreibung, setBeschreibung] = useState('')
  const [zugewiesenAn, setZugewiesenAn] = useState('')
  const [faelligAm, setFaelligAm] = useState('')
  const [dokumentIds, setDokumentIds] = useState<number[]>([])
  const [creating, setCreating] = useState(false)

  const loadTasks = (statusFilter: TaskStatus | '' = filter) => {
    api
      .listTasks(projectId, statusFilter || undefined)
      .then(setTasks)
      .catch((err: Error) => setError(err.message))
  }

  useEffect(() => {
    setTasks(null)
    loadTasks('')
    setFilter('')
    api.listPeople(projectId).then(setPeople).catch(() => {})
    api.listDocuments(projectId).then(setDocuments).catch(() => {})
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const personName = (id: number | null) => people.find((p) => p.id === id)?.name ?? null
  const documentTitel = (id: number) => documents.find((d) => d.id === id)?.titel ?? `#${id}`

  const handleFilterChange = (value: TaskStatus | '') => {
    setFilter(value)
    loadTasks(value)
  }

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!titel.trim()) return
    setCreating(true)
    setError(null)
    try {
      const task = await api.createTask(projectId, {
        titel: titel.trim(),
        beschreibung: beschreibung.trim() || null,
        zugewiesen_an: zugewiesenAn ? Number(zugewiesenAn) : null,
        faellig_am: faelligAm || null,
        dokument_ids: dokumentIds,
      })
      setTitel('')
      setBeschreibung('')
      setZugewiesenAn('')
      setFaelligAm('')
      setDokumentIds([])
      if (!filter) setTasks((prev) => [task, ...(prev ?? [])])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setCreating(false)
    }
  }

  const handleStatusChange = async (task: Task, status: TaskStatus) => {
    setError(null)
    try {
      const updated = await api.updateTask(projectId, task.id, { status })
      if (filter && updated.status !== filter) {
        setTasks((prev) => prev?.filter((t) => t.id !== task.id) ?? null)
      } else {
        setTasks((prev) => prev?.map((t) => (t.id === task.id ? updated : t)) ?? null)
      }
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const handleDelete = async (taskId: number) => {
    if (!confirm('Diese Aufgabe wirklich löschen?')) return
    setError(null)
    try {
      await api.deleteTask(projectId, taskId)
      setTasks((prev) => prev?.filter((t) => t.id !== taskId) ?? null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <section className="tasks-section">
      <h2>Aufgaben</h2>
      {error && <p className="status-error">{error}</p>}

      <form className="create-task-form" onSubmit={handleCreate}>
        <div className="form-row">
          <input
            type="text"
            placeholder="Titel"
            value={titel}
            onChange={(e) => setTitel(e.target.value)}
            required
          />
          <select value={zugewiesenAn} onChange={(e) => setZugewiesenAn(e.target.value)}>
            <option value="">Niemand zugewiesen</option>
            {people.map((p) => (
              <option key={p.id} value={p.id}>
                {p.name}
              </option>
            ))}
          </select>
          <input type="date" value={faelligAm} onChange={(e) => setFaelligAm(e.target.value)} title="Fällig am" />
        </div>
        <textarea
          placeholder="Beschreibung …"
          value={beschreibung}
          onChange={(e) => setBeschreibung(e.target.value)}
          rows={2}
        />
        {documents.length > 0 && (
          <label className="form-field-label">
            Verknüpfte Dokumente
            <select
              multiple
              value={dokumentIds.map(String)}
              onChange={(e) =>
                setDokumentIds(Array.from(e.target.selectedOptions).map((o) => Number(o.value)))
              }
            >
              {documents.map((d) => (
                <option key={d.id} value={d.id}>
                  {d.titel}
                </option>
              ))}
            </select>
          </label>
        )}
        <button type="submit" disabled={creating}>
          {creating ? 'Wird angelegt …' : 'Aufgabe anlegen'}
        </button>
      </form>

      <div className="task-filter">
        <span>Filter:</span>
        <button className={filter === '' ? 'active' : 'link-button'} onClick={() => handleFilterChange('')}>
          Alle
        </button>
        {(Object.keys(STATUS_LABELS) as TaskStatus[]).map((s) => (
          <button
            key={s}
            className={filter === s ? 'active' : 'link-button'}
            onClick={() => handleFilterChange(s)}
          >
            {STATUS_LABELS[s]}
          </button>
        ))}
      </div>

      {tasks === null && !error && <p className="subtitle">Lade Aufgaben …</p>}
      {tasks?.length === 0 && <p className="subtitle">Keine Aufgaben vorhanden.</p>}

      <ul className="entity-list">
        {tasks?.map((task) => (
          <li key={task.id} className="entity-list-item">
            <div className="entity-list-item-header">
              <span className="entity-title">{task.titel}</span>
              <select value={task.status} onChange={(e) => handleStatusChange(task, e.target.value as TaskStatus)}>
                {(Object.keys(STATUS_LABELS) as TaskStatus[]).map((s) => (
                  <option key={s} value={s}>
                    {STATUS_LABELS[s]}
                  </option>
                ))}
              </select>
            </div>
            <div className="entity-meta">
              {personName(task.zugewiesen_an) && <>Zugewiesen: {personName(task.zugewiesen_an)} · </>}
              {task.faellig_am && <>Fällig: {task.faellig_am}</>}
            </div>
            {task.beschreibung && <p className="entity-notes">{task.beschreibung}</p>}
            {task.dokument_ids.length > 0 && (
              <div className="entity-meta">
                Dokumente: {task.dokument_ids.map((id) => documentTitel(id)).join(', ')}
              </div>
            )}
            <div className="entity-actions">
              <button className="link-button" onClick={() => handleDelete(task.id)}>
                Löschen
              </button>
            </div>
          </li>
        ))}
      </ul>
    </section>
  )
}
