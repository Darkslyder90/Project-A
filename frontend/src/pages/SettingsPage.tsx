import { useEffect, useState } from 'react'
import {
  api,
  type AppSettings,
  type EmailWatchConfig,
  type MailFolder,
  type ModelPricing,
  type OAuthStatus,
  type UsageSummary,
} from '../api/client'

type Props = {
  onBack: () => void
  activeProjectId: number | null
}

const API_KEY_STATUS_LABELS: Record<AppSettings['claude_api_key_status'], string> = {
  db: 'Gespeicherter Key aktiv',
  db_invalid: 'Gespeicherter Key kann nicht entschlüsselt werden (SETTINGS_ENCRYPTION_KEY geändert?)',
  env: 'Kein Key gespeichert – .env-Fallback aktiv',
  none: 'Kein Claude-API-Key konfiguriert',
}

export function SettingsPage({ onBack, activeProjectId }: Props) {
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

  const [wechselkurs, setWechselkurs] = useState(0.92)
  const [savingWechselkurs, setSavingWechselkurs] = useState(false)
  const [pricing, setPricing] = useState<ModelPricing[] | null>(null)
  const [newPricingModell, setNewPricingModell] = useState('')
  const [newPricingGueltigAb, setNewPricingGueltigAb] = useState('')
  const [newPricingInput, setNewPricingInput] = useState(0)
  const [newPricingOutput, setNewPricingOutput] = useState(0)
  const [savingPricing, setSavingPricing] = useState(false)

  const [oauthStatus, setOauthStatus] = useState<OAuthStatus | null>(null)
  const [oauthRedirectMessage, setOauthRedirectMessage] = useState<string | null>(null)
  const [connectingOAuth, setConnectingOAuth] = useState(false)
  const [mailFolders, setMailFolders] = useState<MailFolder[] | null>(null)
  const [emailWatchConfig, setEmailWatchConfig] = useState<EmailWatchConfig | null>(null)
  const [selectedFolderId, setSelectedFolderId] = useState('')
  const [pollingIntervall, setPollingIntervall] = useState(10)
  const [watchAktiv, setWatchAktiv] = useState(true)
  const [savingEmailWatch, setSavingEmailWatch] = useState(false)
  const [pollingNow, setPollingNow] = useState(false)

  const loadEmailWatch = () => {
    api.getOAuthStatus().then(setOauthStatus).catch(() => {})
    if (activeProjectId !== null) {
      api
        .getEmailWatchConfig(activeProjectId)
        .then((config) => {
          setEmailWatchConfig(config)
          if (config) {
            setSelectedFolderId(config.outlook_ordner_id)
            setPollingIntervall(config.polling_intervall_minuten)
            setWatchAktiv(config.aktiv)
          }
        })
        .catch(() => {})
    }
  }

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
        setWechselkurs(s.eur_usd_wechselkurs)
      })
      .catch((err: Error) => setError(err.message))
    api.getUsageSummary().then(setUsage).catch(() => {})
    api.listPricing().then(setPricing).catch(() => {})
  }

  useEffect(() => {
    load()
    loadEmailWatch()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeProjectId])

  useEffect(() => {
    const outlookOauth = new URLSearchParams(window.location.search).get('outlook_oauth')
    if (outlookOauth === 'success') {
      setOauthRedirectMessage('Microsoft-Konto erfolgreich verbunden.')
    } else if (outlookOauth === 'error') {
      setOauthRedirectMessage('Verbindung mit Microsoft fehlgeschlagen. Bitte erneut versuchen.')
    }
    if (outlookOauth !== null) {
      window.history.replaceState(null, '', window.location.pathname)
    }
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

  const handleSaveWechselkurs = async () => {
    if (!(wechselkurs > 0)) return
    setSavingWechselkurs(true)
    setError(null)
    try {
      const updated = await api.updateSettings({ eur_usd_wechselkurs: wechselkurs })
      setSettings(updated)
      flashSaved()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSavingWechselkurs(false)
    }
  }

  const handleAddPricing = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!newPricingModell.trim() || !newPricingGueltigAb) return
    setSavingPricing(true)
    setError(null)
    try {
      const created = await api.createPricing({
        modell_name: newPricingModell.trim(),
        gueltig_ab: newPricingGueltigAb,
        input_preis_pro_million_usd: newPricingInput,
        output_preis_pro_million_usd: newPricingOutput,
      })
      setPricing((prev) => [created, ...(prev ?? [])])
      setNewPricingModell('')
      setNewPricingGueltigAb('')
      setNewPricingInput(0)
      setNewPricingOutput(0)
      flashSaved()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSavingPricing(false)
    }
  }

  const handleDeletePricing = async (id: number) => {
    setError(null)
    try {
      await api.deletePricing(id)
      setPricing((prev) => prev?.filter((p) => p.id !== id) ?? null)
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

  const handleConnectOAuth = async () => {
    setConnectingOAuth(true)
    setError(null)
    try {
      const { authorization_url } = await api.startOAuthLogin()
      window.location.href = authorization_url
    } catch (err) {
      setError((err as Error).message)
      setConnectingOAuth(false)
    }
  }

  const handleDisconnectOAuth = async () => {
    if (!confirm('Microsoft-Konto trennen? Alle projektbezogenen Ordner-Überwachungen können dann keine neuen Mails mehr abrufen, bis erneut verbunden wird.')) {
      return
    }
    setError(null)
    try {
      await api.disconnectOAuth()
      loadEmailWatch()
      setMailFolders(null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const handleLoadFolders = async () => {
    setError(null)
    try {
      setMailFolders(await api.listMailFolders())
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const handleSaveEmailWatch = async () => {
    if (activeProjectId === null || !selectedFolderId) return
    const folderName = mailFolders?.find((f) => f.id === selectedFolderId)?.name ?? selectedFolderId
    setSavingEmailWatch(true)
    setError(null)
    try {
      const saved = await api.saveEmailWatchConfig(activeProjectId, {
        outlook_ordner_id: selectedFolderId,
        outlook_ordner_name: folderName,
        aktiv: watchAktiv,
        polling_intervall_minuten: pollingIntervall,
      })
      setEmailWatchConfig(saved)
      flashSaved()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSavingEmailWatch(false)
    }
  }

  const handleDeleteEmailWatch = async () => {
    if (activeProjectId === null) return
    if (!confirm('Outlook-Ordnerüberwachung für dieses Projekt entfernen?')) return
    setError(null)
    try {
      await api.deleteEmailWatchConfig(activeProjectId)
      setEmailWatchConfig(null)
      setSelectedFolderId('')
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const handlePollNow = async () => {
    if (activeProjectId === null) return
    setPollingNow(true)
    setError(null)
    try {
      setEmailWatchConfig(await api.pollEmailWatchNow(activeProjectId))
      flashSaved()
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setPollingNow(false)
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
      {oauthRedirectMessage && (
        <p className={oauthRedirectMessage.includes('fehlgeschlagen') ? 'status-error' : 'status-ok'}>
          {oauthRedirectMessage}
        </p>
      )}
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
            <p className="subtitle">
              Kosten sind eine grobe Schätzung (Tokens × hinterlegter Preis × Wechselkurs, siehe
              unten) – kein exakter Rechnungsbetrag.
            </p>
            {usage === null ? (
              <p className="subtitle">Lade Nutzungsdaten …</p>
            ) : (
              <ul className="usage-summary">
                <li>
                  Heute: {usage.heute.anfragen} Anfragen · {usage.heute.tokens.toLocaleString('de-DE')}{' '}
                  Tokens · ca. {usage.heute.kosten_eur.toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })}
                  {!usage.heute.vollstaendig && ' (unvollständig – nicht für alle Modelle ein Preis hinterlegt)'}
                </li>
                <li>
                  Diese Woche: {usage.woche.anfragen} Anfragen · {usage.woche.tokens.toLocaleString('de-DE')}{' '}
                  Tokens · ca. {usage.woche.kosten_eur.toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })}
                  {!usage.woche.vollstaendig && ' (unvollständig)'}
                </li>
                <li>
                  Diesen Monat: {usage.monat.anfragen} Anfragen · {usage.monat.tokens.toLocaleString('de-DE')}{' '}
                  Tokens · ca. {usage.monat.kosten_eur.toLocaleString('de-DE', { style: 'currency', currency: 'EUR' })}
                  {!usage.monat.vollstaendig && ' (unvollständig)'}
                </li>
              </ul>
            )}
          </section>

          <section className="settings-section">
            <h2>Preise & Wechselkurs</h2>
            <p className="subtitle">
              Grundlage für die Kostenschätzung oben. Kein automatischer Preisabruf – Preise
              gelten ab ihrem "Gültig ab"-Datum, ändere sie hier, wenn Anthropic seine Preise
              anpasst. Historische Auswertungen bleiben dabei korrekt: für jeden vergangenen
              API-Aufruf wird der zu diesem Zeitpunkt gültige Preis verwendet, nicht rückwirkend
              der neueste.
            </p>
            <div className="form-row">
              <label className="form-field-label">
                EUR/USD-Wechselkurs (1 USD in EUR)
                <input
                  type="number"
                  step="0.01"
                  min={0.01}
                  value={wechselkurs}
                  onChange={(e) => setWechselkurs(Number(e.target.value))}
                />
              </label>
              <button disabled={savingWechselkurs} onClick={handleSaveWechselkurs}>
                {savingWechselkurs ? 'Speichert …' : 'Speichern'}
              </button>
            </div>

            {pricing === null ? (
              <p className="subtitle">Lade Preise …</p>
            ) : pricing.length === 0 ? (
              <p className="subtitle">Noch keine Preise hinterlegt.</p>
            ) : (
              <div className="overview-table-wrap">
                <table className="overview-table">
                  <thead>
                    <tr>
                      <th>Modell</th>
                      <th>Gültig ab</th>
                      <th>Input $/Mio.</th>
                      <th>Output $/Mio.</th>
                      <th></th>
                    </tr>
                  </thead>
                  <tbody>
                    {pricing.map((p) => (
                      <tr key={p.id}>
                        <td>{p.modell_name}</td>
                        <td>{p.gueltig_ab}</td>
                        <td>{p.input_preis_pro_million_usd.toFixed(2)}</td>
                        <td>{p.output_preis_pro_million_usd.toFixed(2)}</td>
                        <td>
                          <button className="link-button" onClick={() => handleDeletePricing(p.id)}>
                            Löschen
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}

            <form className="create-document-form" onSubmit={handleAddPricing}>
              <div className="form-row">
                <input
                  type="text"
                  placeholder="Modellname (z. B. claude-opus-5)"
                  value={newPricingModell}
                  onChange={(e) => setNewPricingModell(e.target.value)}
                  required
                />
                <input
                  type="date"
                  value={newPricingGueltigAb}
                  onChange={(e) => setNewPricingGueltigAb(e.target.value)}
                  required
                />
              </div>
              <div className="form-row">
                <label className="form-field-label">
                  Input $/Mio. Tokens
                  <input
                    type="number"
                    step="0.01"
                    min={0}
                    value={newPricingInput}
                    onChange={(e) => setNewPricingInput(Number(e.target.value))}
                  />
                </label>
                <label className="form-field-label">
                  Output $/Mio. Tokens
                  <input
                    type="number"
                    step="0.01"
                    min={0}
                    value={newPricingOutput}
                    onChange={(e) => setNewPricingOutput(Number(e.target.value))}
                  />
                </label>
              </div>
              <button type="submit" disabled={savingPricing}>
                {savingPricing ? 'Speichert …' : 'Preis hinzufügen'}
              </button>
            </form>
          </section>

          <section className="settings-section">
            <h2>Outlook-Ordnerüberwachung</h2>
            <p className="subtitle">
              Legt neue eingehende Mails aus einem festen Outlook-Ordner automatisch als Dokument im
              zugeordneten Projekt an (nur Betreff + Text, keine Anhänge; Mails älter als 1 Woche
              werden nie abgeholt). Das Microsoft-Konto ist global – mehrere Projekte können jeweils
              einen eigenen Ordner desselben Kontos überwachen.
            </p>

            {oauthStatus === null ? (
              <p className="subtitle">Lade Verbindungsstatus …</p>
            ) : oauthStatus.connected ? (
              <>
                <p>
                  Verbunden als <strong>{oauthStatus.account_email ?? 'unbekanntes Konto'}</strong>.
                </p>
                <button className="link-button" onClick={handleDisconnectOAuth}>
                  Microsoft-Konto trennen
                </button>
              </>
            ) : (
              <>
                <p>Kein Microsoft-Konto verbunden.</p>
                <button disabled={connectingOAuth} onClick={handleConnectOAuth}>
                  {connectingOAuth ? 'Weiterleitung …' : 'Mit Microsoft verbinden'}
                </button>
              </>
            )}

            {activeProjectId === null ? (
              <p className="subtitle" style={{ marginTop: '1rem' }}>
                Wähle zuerst ein Projekt aus, um dessen Ordner-Zuordnung zu konfigurieren.
              </p>
            ) : (
              <div style={{ marginTop: '1rem' }}>
                <h3>Ordner für aktuelles Projekt</h3>
                {emailWatchConfig && (
                  <p className="subtitle">
                    Zugeordneter Ordner: <strong>{emailWatchConfig.outlook_ordner_name}</strong> ·{' '}
                    {emailWatchConfig.aktiv ? 'aktiv' : 'pausiert'} · zuletzt abgefragt:{' '}
                    {emailWatchConfig.letzte_abfrage_am
                      ? new Date(emailWatchConfig.letzte_abfrage_am).toLocaleString('de-DE')
                      : 'noch nie'}
                    {emailWatchConfig.letzter_fehler && (
                      <>
                        {' '}
                        — <span className="status-error">Fehler: {emailWatchConfig.letzter_fehler}</span>
                      </>
                    )}
                  </p>
                )}

                {oauthStatus?.connected && (
                  <div className="form-row">
                    {mailFolders === null ? (
                      <button className="link-button" onClick={handleLoadFolders}>
                        Ordnerliste laden
                      </button>
                    ) : (
                      <select value={selectedFolderId} onChange={(e) => setSelectedFolderId(e.target.value)}>
                        <option value="">Ordner wählen …</option>
                        {mailFolders.map((folder) => (
                          <option key={folder.id} value={folder.id}>
                            {folder.name}
                          </option>
                        ))}
                      </select>
                    )}
                    <label className="form-field-label">
                      Intervall (Minuten)
                      <input
                        type="number"
                        min={1}
                        max={1440}
                        value={pollingIntervall}
                        onChange={(e) => setPollingIntervall(Number(e.target.value))}
                      />
                    </label>
                    <label>
                      <input type="checkbox" checked={watchAktiv} onChange={(e) => setWatchAktiv(e.target.checked)} />
                      {' '}aktiv
                    </label>
                    <button disabled={savingEmailWatch || !selectedFolderId} onClick={handleSaveEmailWatch}>
                      {savingEmailWatch ? 'Speichert …' : 'Speichern'}
                    </button>
                    {emailWatchConfig && (
                      <>
                        <button disabled={pollingNow} onClick={handlePollNow}>
                          {pollingNow ? 'Ruft ab …' : 'Jetzt abrufen'}
                        </button>
                        <button className="link-button" onClick={handleDeleteEmailWatch}>
                          Entfernen
                        </button>
                      </>
                    )}
                  </div>
                )}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  )
}
