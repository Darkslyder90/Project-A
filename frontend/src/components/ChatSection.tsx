import { useEffect, useState } from 'react'
import { api, type ChatConversation, type ChatMessage } from '../api/client'

type Props = {
  projectId: number
}

function conversationLabel(c: ChatConversation): string {
  if (c.titel) return c.titel
  return `Konversation vom ${new Date(c.erstellt_am).toLocaleString('de-DE')}`
}

export function ChatSection({ projectId }: Props) {
  const [conversations, setConversations] = useState<ChatConversation[] | null>(null)
  const [activeId, setActiveId] = useState<number | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [renaming, setRenaming] = useState(false)
  const [titleDraft, setTitleDraft] = useState('')

  const loadConversations = (selectId?: number) => {
    api
      .listConversations(projectId)
      .then((list) => {
        setConversations(list)
        if (selectId !== undefined) {
          setActiveId(selectId)
        } else if (activeId === null && list.length > 0) {
          setActiveId(list[0].id)
        }
      })
      .catch((err: Error) => setError(err.message))
  }

  useEffect(() => {
    setConversations(null)
    setActiveId(null)
    setMessages([])
    loadConversations()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  useEffect(() => {
    if (activeId === null) {
      setMessages([])
      return
    }
    api
      .getConversation(projectId, activeId)
      .then((detail) => setMessages(detail.nachrichten))
      .catch((err: Error) => setError(err.message))
  }, [projectId, activeId])

  const handleNewConversation = async () => {
    setError(null)
    try {
      const conversation = await api.createConversation(projectId)
      setConversations((prev) => [conversation, ...(prev ?? [])])
      setActiveId(conversation.id)
      setMessages([])
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const handleSend = async (event: React.FormEvent) => {
    event.preventDefault()
    const query = input.trim()
    if (!query) return

    setError(null)
    setSending(true)
    try {
      let conversationId = activeId
      if (conversationId === null) {
        const conversation = await api.createConversation(projectId)
        conversationId = conversation.id
        setActiveId(conversationId)
        setConversations((prev) => [conversation, ...(prev ?? [])])
      }

      setMessages((prev) => [
        ...prev,
        {
          id: -Date.now(),
          conversation_id: conversationId!,
          rolle: 'user',
          text: query,
          quellen: null,
          erstellt_am: new Date().toISOString(),
        },
      ])
      setInput('')

      const response = await api.sendMessage(projectId, conversationId, query)
      setMessages((prev) => [...prev, response.nachricht])
      loadConversations(conversationId)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSending(false)
    }
  }

  const handleDelete = async () => {
    if (activeId === null) return
    setError(null)
    try {
      await api.deleteConversation(projectId, activeId)
      setConversations((prev) => (prev ?? []).filter((c) => c.id !== activeId))
      setActiveId(null)
      setMessages([])
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const startRename = () => {
    const current = conversations?.find((c) => c.id === activeId)
    setTitleDraft(current?.titel ?? '')
    setRenaming(true)
  }

  const handleRenameSubmit = async (event: React.FormEvent) => {
    event.preventDefault()
    if (activeId === null || !titleDraft.trim()) return
    try {
      const updated = await api.renameConversation(projectId, activeId, titleDraft.trim())
      setConversations((prev) => (prev ?? []).map((c) => (c.id === updated.id ? updated : c)))
      setRenaming(false)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <section className="chat-section">
      <h2>Chat</h2>
      <p className="subtitle">
        Fragen werden ausschließlich anhand der indexierten Projektdokumente beantwortet – mit
        nachvollziehbaren Quellenangaben.
      </p>

      <div className="chat-conversation-bar">
        <select
          value={activeId ?? ''}
          onChange={(e) => setActiveId(e.target.value ? Number(e.target.value) : null)}
        >
          <option value="">Neue Konversation …</option>
          {conversations?.map((c) => (
            <option key={c.id} value={c.id}>
              {conversationLabel(c)}
            </option>
          ))}
        </select>
        <button type="button" onClick={handleNewConversation}>
          Neu
        </button>
        {activeId !== null && !renaming && (
          <button type="button" className="link-button" onClick={startRename}>
            Umbenennen
          </button>
        )}
        {activeId !== null && (
          <button type="button" className="link-button" onClick={handleDelete}>
            Löschen
          </button>
        )}
      </div>

      {renaming && (
        <form className="chat-rename-form" onSubmit={handleRenameSubmit}>
          <input
            type="text"
            value={titleDraft}
            onChange={(e) => setTitleDraft(e.target.value)}
            autoFocus
          />
          <button type="submit">Speichern</button>
          <button type="button" onClick={() => setRenaming(false)}>
            Abbrechen
          </button>
        </form>
      )}

      <div className="chat-turns">
        {messages.map((m) => (
          <div key={m.id} className={`chat-turn chat-turn--${m.rolle}`}>
            <div className="chat-turn-bubble">
              <p>{m.text}</p>
              {m.quellen && m.quellen.length > 0 && (
                <ul className="chat-sources">
                  {m.quellen.map((q) => (
                    <li key={q.source_id}>
                      <span className="chat-source-id">[{q.source_id}]</span>{' '}
                      {q.geloescht ? (
                        <span className="chat-warning">Quelle wurde inzwischen gelöscht</span>
                      ) : (
                        <>
                          {q.document_titel}
                          {q.dokumentdatum && ` · ${q.dokumentdatum}`}
                          {q.abschnitt && ` · ${q.abschnitt}`}
                        </>
                      )}
                    </li>
                  ))}
                </ul>
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
