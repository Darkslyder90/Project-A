import { useEffect, useState } from 'react'
import { api, type AppSettings, type UsageSummary } from '../api/client'

type Props = {
  onBack: () => void
}

const API_KEY_STATUS_LABELS: Record<AppSettings['claude_api_key_status'], string> = {
  db: 'Gespeicherter Key aktiv',
  db_invalid: 'Gespeicherter Key kann nicht entschlüsselt werden (SETTINGS_ENCRYPTION_KEY geändert?)',
  env: 'Kein Key gespeichert – .env-Fallback aktiv',
  none: 'Kein Claude-API-Key konfiguriert',
}

export function SettingsPage({ onBack }: Props) {
  const [settings, setSettings] = useState<AppSettings | null>(null)
  const [usage, setUsage] = useState<UsageSummary | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saved, setSaved] = useState(false)

  const [apiKeyInput, setApiKeyInput] = useState('')
  const [savingKey, setSavingKey] = useState(false)

  const [claudeModel, setClaudeModel] = useState('')
  const [embeddingModel, setEmbeddingModel] = useState('')
  const [candidateKVector, setCandidateKVector] = useState(20)
  const [candidateKKeyword, setCandidateKKeyword] = useState(20)
  const [finalK, setFinalK] = useState(8)
  const [chunkZielTokens, setChunkZielTokens] = useState(350)
  const [chunkOverlapTokens, setChunkOverlapTokens] = useState(60)
  const [savingTuning, setSavingTuning] = useState(false)

  const load = () => {
    api
      .getSettings()
      .then((s) => {
        setSettings(s)
        setClaudeModel(s.claude_model ?? '')
        setEmbeddingModel(s.embedding_model_name)
        setCandidateKVector(s.candidate_k_vector)
        setCandidateKKeyword(s.candidate_k_keyword)
        setFinalK(s.final_k)
        setChunkZielTokens(s.chunk_ziel_tokens)
        setChunkOverlapTokens(s.chunk_overlap_tokens)
      })
      .catch((err: Error) => setError(err.message))
    api.getUsageSummary().then(setUsage).catch(() => {})
  }

  useEffect(() => {
    load()
  }, [])

  const flashSaved = () => {
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  const handleSaveKey = async () => {
    if (!apiKeyInput.trim()) return
    setSavingKey(true)
    setError(null)
    try {
      const updated = await api.updateSettings({ claude_api_key: apiKeyInput.trim() })
      setSettings(updated)
      setApiKeyInput('')
      flashSaved()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSavingKey(false)
    }
  }

  const handleRemoveKey = async () => {
    if (!confirm('Gespeicherten Claude-API-Key wirklich entfernen? Ein evtl. konfigurierter .env-Key greift danach wieder als Fallback.')) {
      return
    }
    setError(null)
    try {
      const updated = await api.updateSettings({ claude_api_key: '' })
      setSettings(updated)
      flashSaved()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const handleSaveModel = async () => {
    setError(null)
    try {
      const updated = await api.updateSettings({ claude_model: claudeModel.trim() || null })
      setSettings(updated)
      flashSaved()
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const handleSaveTuning = async (event: React.FormEvent) => {
    event.preventDefault()
    setSavingTuning(true)
    setError(null)
    try {
      const updated = await api.updateSettings({
        embedding_model_name: embeddingModel.trim(),
        candidate_k_vector: candidateKVector,
        candidate_k_keyword: candidateKKeyword,
        final_k: finalK,
        chunk_ziel_tokens: chunkZielTokens,
        chunk_overlap_tokens: chunkOverlapTokens,
      })
      setSettings(updated)
      flashSaved()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSavingTuning(false)
    }
  }

  return (
    <div className="settings-page">
      <header className="project-home-header">
        <h1>Einstellungen</h1>
        <button onClick={onBack}>Zurück</button>
      </header>

      {error && <p className="status-error">{error}</p>}
      {saved && <p className="status-ok">Gespeichert.</p>}
      {settings === null && !error && <p className="subtitle">Lade Einstellungen …</p>}

      {settings && (
        <>
          <section className="settings-section">
            <h2>Claude-API-Key</h2>
            <p className="subtitle">
              Globale Einstellung, gilt für alle Projekte. Der Key wird verschlüsselt in der
              Datenbank gespeichert, nie im Klartext angezeigt.
            </p>
            <p>
              Status: <strong>{API_KEY_STATUS_LABELS[settings.claude_api_key_status]}</strong>
              {settings.claude_api_key_masked && <> ({settings.claude_api_key_masked})</>}
            </p>
            <div className="form-row">
              <input
                type="password"
                placeholder="sk-ant-…"
                value={apiKeyInput}
                onChange={(e) => setApiKeyInput(e.target.value)}
              />
              <button disabled={savingKey || !apiKeyInput.trim()} onClick={handleSaveKey}>
                {savingKey ? 'Speichert …' : 'Key speichern'}
              </button>
              {settings.claude_api_key_status === 'db' && (
                <button className="link-button" onClick={handleRemoveKey}>
                  Gespeicherten Key entfernen
                </button>
              )}
            </div>
          </section>

          <section className="settings-section">
            <h2>Claude-Modell (Chat)</h2>
            <p className="subtitle">
              Unabhängig vom lokalen Embedding-Modell. Aktuell wirksam:{' '}
              <strong>{settings.effective_claude_model}</strong>
            </p>
            <div className="form-row">
              <input
                type="text"
                placeholder="z. B. claude-opus-5"
                value={claudeModel}
                onChange={(e) => setClaudeModel(e.target.value)}
              />
              <button onClick={handleSaveModel}>Speichern</button>
              {settings.claude_model && (
                <button
                  className="link-button"
                  onClick={() => {
                    setClaudeModel('')
                    api.updateSettings({ claude_model: null }).then((s) => {
                      setSettings(s)
                      flashSaved()
                    })
                  }}
                >
                  Standard verwenden
                </button>
              )}
            </div>
          </section>

          <section className="settings-section">
            <h2>RAG-Feintuning</h2>
            <p className="subtitle">
              Wirkt sofort auf neue Chat-/Retrieval-Anfragen. Embedding-Modell und Chunk-Größe
              wirken sich nur auf neu angelegte Projekte aus – bereits aktive Indizes bestehender
              Projekte werden dadurch nicht automatisch neu aufgebaut.
            </p>
            <form className="create-document-form" onSubmit={handleSaveTuning}>
              <label className="form-field-label">
                Embedding-Modell
                <input
                  type="text"
                  value={embeddingModel}
                  onChange={(e) => setEmbeddingModel(e.target.value)}
                />
              </label>
              <div className="form-row">
                <label className="form-field-label">
                  candidate_k (Vektor)
                  <input
                    type="number"
                    min={1}
                    max={200}
                    value={candidateKVector}
                    onChange={(e) => setCandidateKVector(Number(e.target.value))}
                  />
                </label>
                <label className="form-field-label">
                  candidate_k (Volltext)
                  <input
                    type="number"
                    min={1}
                    max={200}
                    value={candidateKKeyword}
                    onChange={(e) => setCandidateKKeyword(Number(e.target.value))}
                  />
                </label>
                <label className="form-field-label">
                  final_k
                  <input
                    type="number"
                    min={1}
                    max={50}
                    value={finalK}
                    onChange={(e) => setFinalK(Number(e.target.value))}
                  />
                </label>
              </div>
              <div className="form-row">
                <label className="form-field-label">
                  Chunk-Zielgröße (Tokens)
                  <input
                    type="number"
                    min={50}
                    max={2000}
                    value={chunkZielTokens}
                    onChange={(e) => setChunkZielTokens(Number(e.target.value))}
                  />
                </label>
                <label className="form-field-label">
                  Chunk-Overlap (Tokens)
                  <input
                    type="number"
                    min={0}
                    max={500}
                    value={chunkOverlapTokens}
                    onChange={(e) => setChunkOverlapTokens(Number(e.target.value))}
                  />
                </label>
                <label className="form-field-label">
                  Fusionsverfahren
                  <input type="text" value="Reciprocal Rank Fusion (RRF)" disabled />
                </label>
              </div>
              <button type="submit" disabled={savingTuning}>
                {savingTuning ? 'Speichert …' : 'Speichern'}
              </button>
            </form>
          </section>

          <section className="settings-section">
            <h2>API-Nutzung</h2>
            {usage === null ? (
              <p className="subtitle">Lade Nutzungsdaten …</p>
            ) : (
              <ul className="usage-summary">
                <li>
                  Heute: {usage.heute.anfragen} Anfragen · {usage.heute.tokens.toLocaleString('de-DE')} Tokens
                </li>
                <li>
                  Diese Woche: {usage.woche.anfragen} Anfragen · {usage.woche.tokens.toLocaleString('de-DE')} Tokens
                </li>
                <li>
                  Diesen Monat: {usage.monat.anfragen} Anfragen · {usage.monat.tokens.toLocaleString('de-DE')} Tokens
                </li>
              </ul>
            )}
          </section>
        </>
      )}
    </div>
  )
}
