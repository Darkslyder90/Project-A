import { useEffect, useState } from 'react'
import './App.css'
import { ProjectHome } from './pages/ProjectHome'
import { ProjectsPage } from './pages/ProjectsPage'
import { useActiveProjectId } from './state/activeProject'

function BackendStatusBadge() {
  const [ok, setOk] = useState<boolean | null>(null)

  useEffect(() => {
    fetch('/health')
      .then((res) => res.json())
      .then((body) => setOk(body.status === 'ok'))
      .catch(() => setOk(false))
  }, [])

  if (ok === null) return null
  return (
    <span className={ok ? 'backend-badge-ok' : 'backend-badge-error'} title="Backend-Status">
      {ok ? '● Backend verbunden' : '● Backend nicht erreichbar'}
    </span>
  )
}

function App() {
  const [activeProjectId, setActiveProjectId] = useActiveProjectId()

  return (
    <main className="app-shell">
      <div className="backend-status-row">
        <BackendStatusBadge />
      </div>

      {activeProjectId === null ? (
        <ProjectsPage onSelect={setActiveProjectId} />
      ) : (
        <ProjectHome projectId={activeProjectId} onSwitch={() => setActiveProjectId(null)} />
      )}
    </main>
  )
}

export default App
