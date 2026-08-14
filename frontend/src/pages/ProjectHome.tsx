import { useEffect, useState } from 'react'
import { api, type Project } from '../api/client'
import { DocumentsSection } from '../components/DocumentsSection'

type Props = {
  projectId: number
  onSwitch: () => void
}

export function ProjectHome({ projectId, onSwitch }: Props) {
  const [project, setProject] = useState<Project | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    api
      .listProjects()
      .then((projects) => {
        const found = projects.find((p) => p.id === projectId)
        if (!found) {
          setError('Projekt wurde nicht gefunden.')
          return
        }
        setProject(found)
      })
      .catch((err: Error) => setError(err.message))
  }, [projectId])

  return (
    <div className="project-home">
      <header className="project-home-header">
        <div>
          <h1>{project?.name ?? '…'}</h1>
          {project?.beschreibung && <p className="subtitle">{project.beschreibung}</p>}
        </div>
        <button onClick={onSwitch}>Projekt wechseln</button>
      </header>

      {error && <p className="status-error">{error}</p>}

      <DocumentsSection projectId={projectId} />

      <p className="subtitle">
        Weitere Funktionen (Chat, Personen, Aufgaben, Meetings) folgen in den nächsten Schritten.
      </p>
    </div>
  )
}
