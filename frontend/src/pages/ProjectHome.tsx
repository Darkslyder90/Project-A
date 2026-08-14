import { useEffect, useState } from 'react'
import { api, type Project } from '../api/client'
import { ChatSection } from '../components/ChatSection'
import { DocumentsSection } from '../components/DocumentsSection'
import { MeetingsSection } from '../components/MeetingsSection'
import { OverviewSection } from '../components/OverviewSection'
import { PeopleSection } from '../components/PeopleSection'
import { RetrievalTestSection } from '../components/RetrievalTestSection'
import { TasksSection } from '../components/TasksSection'

type Props = {
  projectId: number
  onSwitch: () => void
}

type Tab = 'uebersicht' | 'chat' | 'verwalten'

const TAB_LABELS: Record<Tab, string> = {
  uebersicht: 'Übersicht',
  chat: 'Chat',
  verwalten: 'Verwalten',
}

export function ProjectHome({ projectId, onSwitch }: Props) {
  const [project, setProject] = useState<Project | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [tab, setTab] = useState<Tab>('uebersicht')

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

  useEffect(() => {
    setTab('uebersicht')
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

      <nav className="project-tabs">
        {(Object.keys(TAB_LABELS) as Tab[]).map((t) => (
          <button key={t} className={tab === t ? 'active' : ''} onClick={() => setTab(t)}>
            {TAB_LABELS[t]}
          </button>
        ))}
      </nav>

      {tab === 'uebersicht' && <OverviewSection projectId={projectId} />}

      {tab === 'chat' && (
        <>
          <ChatSection projectId={projectId} />
          <RetrievalTestSection projectId={projectId} />
        </>
      )}

      {tab === 'verwalten' && (
        <>
          <DocumentsSection projectId={projectId} />
          <PeopleSection projectId={projectId} />
          <TasksSection projectId={projectId} />
          <MeetingsSection projectId={projectId} />
        </>
      )}
    </div>
  )
}
