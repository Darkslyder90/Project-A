import { useEffect, useState } from 'react'
import { api, type Project } from '../api/client'

type Props = {
  onSelect: (projectId: number) => void
}

export function ProjectsPage({ onSelect }: Props) {
  const [projects, setProjects] = useState<Project[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [beschreibung, setBeschreibung] = useState('')
  const [creating, setCreating] = useState(false)
  const [deletingId, setDeletingId] = useState<number | null>(null)
  const [pendingDeleteId, setPendingDeleteId] = useState<number | null>(null)
  const [importFile, setImportFile] = useState<File | null>(null)
  const [importing, setImporting] = useState(false)

  const loadProjects = () => {
    api
      .listProjects()
      .then(setProjects)
      .catch((err: Error) => setError(err.message))
  }

  useEffect(loadProjects, [])

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!name.trim()) return
    setCreating(true)
    setError(null)
    try {
      const project = await api.createProject({
        name: name.trim(),
        beschreibung: beschreibung.trim() || null,
      })
      setName('')
      setBeschreibung('')
      setProjects((prev) => [...(prev ?? []), project])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setCreating(false)
    }
  }

  const handleImport = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!importFile) return
    setImporting(true)
    setError(null)
    try {
      const project = await api.importProject(importFile)
      setImportFile(null)
      setProjects((prev) => [...(prev ?? []), project])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setImporting(false)
    }
  }

  const handleDelete = async (projectId: number) => {
    setDeletingId(projectId)
    setError(null)
    try {
      await api.deleteProject(projectId)
      setProjects((prev) => prev?.filter((p) => p.id !== projectId) ?? null)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setDeletingId(null)
      setPendingDeleteId(null)
    }
  }

  return (
    <div className="projects-page">
      <h1>Project-A</h1>
      <p className="subtitle">Projekt auswählen oder neu anlegen</p>

      {error && <p className="status-error">{error}</p>}

      <form className="create-project-form" onSubmit={handleCreate}>
        <input
          type="text"
          placeholder="Projektname"
          value={name}
          onChange={(e) => setName(e.target.value)}
          required
        />
        <input
          type="text"
          placeholder="Beschreibung (optional)"
          value={beschreibung}
          onChange={(e) => setBeschreibung(e.target.value)}
        />
        <button type="submit" disabled={creating}>
          {creating ? 'Wird angelegt …' : 'Projekt anlegen'}
        </button>
      </form>

      <form className="import-project-form" onSubmit={handleImport}>
        <input
          type="file"
          accept=".zip"
          onChange={(e) => setImportFile(e.target.files?.[0] ?? null)}
        />
        <button type="submit" disabled={importing || !importFile}>
          {importing ? 'Wird importiert …' : 'Projekt-Export importieren'}
        </button>
      </form>

      {projects === null && !error && <p>Lade Projekte …</p>}
      {projects?.length === 0 && <p className="subtitle">Noch keine Projekte vorhanden.</p>}

      <ul className="project-list">
        {projects?.map((project) => (
          <li key={project.id} className="project-list-item">
            <button className="project-select" onClick={() => onSelect(project.id)}>
              <span className="project-name">{project.name}</span>
              {project.beschreibung && <span className="project-desc">{project.beschreibung}</span>}
            </button>

            {pendingDeleteId === project.id ? (
              <span className="confirm-delete">
                Wirklich löschen?
                <button
                  className="danger"
                  disabled={deletingId === project.id}
                  onClick={() => handleDelete(project.id)}
                >
                  Ja, löschen
                </button>
                <button onClick={() => setPendingDeleteId(null)}>Abbrechen</button>
              </span>
            ) : (
              <button className="link-button" onClick={() => setPendingDeleteId(project.id)}>
                Löschen
              </button>
            )}
          </li>
        ))}
      </ul>
    </div>
  )
}
