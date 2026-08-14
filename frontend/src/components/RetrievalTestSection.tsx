import { useState } from 'react'
import { api, type RetrievalHit } from '../api/client'

type Props = {
  projectId: number
}

export function RetrievalTestSection({ projectId }: Props) {
  const [query, setQuery] = useState('')
  const [hits, setHits] = useState<RetrievalHit[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [searching, setSearching] = useState(false)

  const handleSearch = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!query.trim()) return
    setSearching(true)
    setError(null)
    try {
      const results = await api.testRetrieval(projectId, query.trim())
      setHits(results)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setSearching(false)
    }
  }

  return (
    <section className="retrieval-test-section">
      <h2>Retrieval testen</h2>
      <p className="subtitle">
        Reine Vektorsuche über die vorhandenen Dokumente – ohne Claude-Aufruf. Nützlich, um vor
        der Chat-Anbindung zu prüfen, ob die richtigen Textstellen gefunden werden.
      </p>

      <form className="retrieval-test-form" onSubmit={handleSearch}>
        <input
          type="text"
          placeholder="Suchanfrage …"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
        />
        <button type="submit" disabled={searching}>
          {searching ? 'Suche …' : 'Suchen'}
        </button>
      </form>

      {error && <p className="status-error">{error}</p>}

      {hits !== null && hits.length === 0 && (
        <p className="subtitle">Keine Treffer (oder noch keine indexierten Dokumente).</p>
      )}

      <ul className="retrieval-hit-list">
        {hits?.map((hit) => (
          <li key={hit.chunk_id} className="retrieval-hit">
            <div className="retrieval-hit-header">
              <span className="retrieval-hit-rank">#{hit.vector_rank}</span>
              <span className="retrieval-hit-title">{hit.document_titel}</span>
              {hit.abschnitt && <span className="retrieval-hit-section">{hit.abschnitt}</span>}
              <span className="retrieval-hit-score">Score {hit.vector_score.toFixed(3)}</span>
            </div>
            <p className="retrieval-hit-text">{hit.text}</p>
          </li>
        ))}
      </ul>
    </section>
  )
}
