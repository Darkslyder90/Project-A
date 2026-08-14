import { useEffect, useState } from 'react'
import './App.css'

type HealthResponse = {
  status: 'ok' | 'degraded'
  checks: Record<string, string>
}

function App() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    fetch('/health')
      .then((res) => res.json())
      .then(setHealth)
      .catch(() => setError('Backend nicht erreichbar'))
  }, [])

  return (
    <main className="app-shell">
      <h1>Project-A</h1>
      <p className="subtitle">Persönlicher Projekt-Assistent</p>

      <section className="status-card">
        <h2>Backend-Status</h2>
        {error && <p className="status-error">{error}</p>}
        {!error && !health && <p>Prüfe Verbindung …</p>}
        {health && (
          <>
            <p className={health.status === 'ok' ? 'status-ok' : 'status-error'}>
              {health.status === 'ok' ? 'Betriebsbereit' : 'Eingeschränkt'}
            </p>
            <ul>
              {Object.entries(health.checks).map(([name, value]) => (
                <li key={name}>
                  {name}: {value}
                </li>
              ))}
            </ul>
          </>
        )}
      </section>
    </main>
  )
}

export default App
