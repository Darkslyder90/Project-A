import { useEffect, useState } from 'react'
import './App.css'
import { ProjectHome } from './pages/ProjectHome'
import { ProjectsPage } from './pages/ProjectsPage'
import { SettingsPage } from './pages/SettingsPage'
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
  // Landet nach dem Microsoft-OAuth-Redirect direkt in den Settings (siehe
  // backend/app/api/routes/email_watch.py::oauth_callback -> /settings?outlook_oauth=...).
  const [showSettings, setShowSettings] = useState(
    () => new URLSearchParams(window.location.search).has('outlook_oauth'),
  )

  return (
    <main className="app-shell">
      <div className="backend-status-row">
        <button className="link-button" onClick={() => setShowSettings(true)}>
          Einstellungen
        </button>
        <BackendStatusBadge />
      </div>

      {showSettings ? (
        <SettingsPage onBack={() => setShowSettings(false)} activeProjectId={activeProjectId} />
      ) : activeProjectId === null ? (
        <ProjectsPage onSelect={setActiveProjectId} />
      ) : (
        <ProjectHome projectId={activeProjectId} onSwitch={() => setActiveProjectId(null)} />
      )}
    </main>
  )
}

export default App
