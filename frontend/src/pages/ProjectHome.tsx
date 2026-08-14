import { useEffect, useState } from 'react'
import { api, type Project } from '../api/client'
import { ChatSection } from '../components/ChatSection'
import { DocumentsSection } from '../components/DocumentsSection'
import { MeetingsSection } from '../components/MeetingsSection'
import { PeopleSection } from '../components/PeopleSection'
import { RetrievalTestSection } from '../components/RetrievalTestSection'
// Aufgaben-Section auf Nutzerwunsch erstmal wieder raus (siehe TasksSection.tsx,
// Backend/API bleiben unveraendert bestehen) - moeglicherweise spaeter in
// anderer Form/Platzierung wieder aktiviert.
// import { TasksSection } from '../components/TasksSection'

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

      <PeopleSection projectId={projectId} />

      {/* <TasksSection projectId={projectId} /> */}

      <MeetingsSection projectId={projectId} />

      <ChatSection projectId={projectId} />

      <RetrievalTestSection projectId={projectId} />
    </div>
  )
}
