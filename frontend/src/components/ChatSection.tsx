import { useState } from 'react'
import { api, type ChatSource } from '../api/client'

type Props = {
  projectId: number
}

type Turn = {
  role: 'user' | 'assistant'
  text: string
  quellen?: ChatSource[]
  unbekannteZitate?: string[]
}

export function ChatSection({ projectId }: Props) {
  const [turns, setTurns] = useState<Turn[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleSend = async (event: React.FormEvent) => {
    event.preventDefault()
    const query = input.trim()
    if (!query) return

    setInput('')
    setError(null)
    setTurns((prev) => [...prev, { role: 'user', text: query }])
    setSending(true)

    try {
      const response = await api.askChat(projectId, query)
      setTurns((prev) => [
        ...prev,
        {
          role: 'assistant',
          text: response.antwort,
          quellen: response.quellen,
          unbekannteZitate: response.unbekannte_zitate,
        },
      ])
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSending(false)
    }
  }

  return (
    <section className="chat-section">
      <h2>Chat</h2>
      <p className="subtitle">
        Fragen werden ausschließlich anhand der indexierten Projektdokumente beantwortet – mit
        nachvollziehbaren Quellenangaben. Der Konversationsverlauf wird noch nicht gespeichert
        (folgt in einem späteren Schritt).
      </p>

      <div className="chat-turns">
        {turns.map((turn, i) => (
          <div key={i} className={`chat-turn chat-turn--${turn.role}`}>
            <div className="chat-turn-bubble">
              <p>{turn.text}</p>
              {turn.quellen && turn.quellen.length > 0 && (
                <ul className="chat-sources">
                  {turn.quellen.map((q) => (
                    <li key={q.source_id}>
                      <span className="chat-source-id">[{q.source_id}]</span> {q.document_titel}
                      {q.dokumentdatum && ` · ${q.dokumentdatum}`}
                      {q.abschnitt && ` · ${q.abschnitt}`}
                    </li>
                  ))}
                </ul>
              )}
              {turn.unbekannteZitate && turn.unbekannteZitate.length > 0 && (
                <p className="chat-warning">
                  Hinweis: Claude hat nicht existierende Quellen genannt (
                  {turn.unbekannteZitate.join(', ')}) – diese wurden entfernt.
                </p>
              )}
            </div>
          </div>
        ))}
        {sending && <p className="subtitle">Claude denkt nach …</p>}
      </div>

      {error && <p className="status-error">{error}</p>}

      <form className="chat-input-form" onSubmit={handleSend}>
        <input
          type="text"
          placeholder="Frage zum Projekt stellen …"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          disabled={sending}
        />
        <button type="submit" disabled={sending || !input.trim()}>
          Senden
        </button>
      </form>
    </section>
  )
}
