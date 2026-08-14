import { useEffect, useState } from 'react'
import { api, type Person } from '../api/client'

type Props = {
  projectId: number
}

export function PeopleSection({ projectId }: Props) {
  const [people, setPeople] = useState<Person[] | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [name, setName] = useState('')
  const [rolle, setRolle] = useState('')
  const [kontaktinfo, setKontaktinfo] = useState('')
  const [notizen, setNotizen] = useState('')
  const [creating, setCreating] = useState(false)
  const [editingId, setEditingId] = useState<number | null>(null)
  const [editDraft, setEditDraft] = useState<{ name: string; rolle: string; kontaktinfo: string; notizen: string }>({
    name: '',
    rolle: '',
    kontaktinfo: '',
    notizen: '',
  })

  const loadPeople = () => {
    api
      .listPeople(projectId)
      .then(setPeople)
      .catch((err: Error) => setError(err.message))
  }

  useEffect(() => {
    setPeople(null)
    loadPeople()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [projectId])

  const handleCreate = async (event: React.FormEvent) => {
    event.preventDefault()
    if (!name.trim()) return
    setCreating(true)
    setError(null)
    try {
      const person = await api.createPerson(projectId, {
        name: name.trim(),
        rolle: rolle.trim() || null,
        kontaktinfo: kontaktinfo.trim() || null,
        notizen: notizen.trim() || null,
      })
      setName('')
      setRolle('')
      setKontaktinfo('')
      setNotizen('')
      setPeople((prev) => [...(prev ?? []), person].sort((a, b) => a.name.localeCompare(b.name)))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setCreating(false)
    }
  }

  const startEdit = (person: Person) => {
    setEditingId(person.id)
    setEditDraft({
      name: person.name,
      rolle: person.rolle ?? '',
      kontaktinfo: person.kontaktinfo ?? '',
      notizen: person.notizen ?? '',
    })
  }

  const handleSaveEdit = async (personId: number) => {
    setError(null)
    try {
      const updated = await api.updatePerson(projectId, personId, {
        name: editDraft.name.trim(),
        rolle: editDraft.rolle.trim() || null,
        kontaktinfo: editDraft.kontaktinfo.trim() || null,
        notizen: editDraft.notizen.trim() || null,
      })
      setPeople((prev) => prev?.map((p) => (p.id === personId ? updated : p)) ?? null)
      setEditingId(null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  const handleDelete = async (personId: number) => {
    if (!confirm('Diese Person wirklich löschen? Zuweisungen bei Aufgaben werden entfernt, die Aufgaben bleiben bestehen.')) return
    setError(null)
    try {
      await api.deletePerson(projectId, personId)
      setPeople((prev) => prev?.filter((p) => p.id !== personId) ?? null)
    } catch (err) {
      setError((err as Error).message)
    }
  }

  return (
    <section className="people-section">
      <h2>Personen</h2>
      {error && <p className="status-error">{error}</p>}

      <form className="create-person-form" onSubmit={handleCreate}>
        <div className="form-row">
          <input type="text" placeholder="Name" value={name} onChange={(e) => setName(e.target.value)} required />
          <input type="text" placeholder="Rolle" value={rolle} onChange={(e) => setRolle(e.target.value)} />
          <input
            type="text"
            placeholder="Kontakt (E-Mail, Telefon …)"
            value={kontaktinfo}
            onChange={(e) => setKontaktinfo(e.target.value)}
          />
        </div>
        <textarea
          placeholder="Notizen …"
          value={notizen}
          onChange={(e) => setNotizen(e.target.value)}
          rows={2}
        />
        <button type="submit" disabled={creating}>
          {creating ? 'Wird angelegt …' : 'Person anlegen'}
        </button>
      </form>

      {people === null && !error && <p className="subtitle">Lade Personen …</p>}
      {people?.length === 0 && <p className="subtitle">Noch keine Personen erfasst.</p>}

      <ul className="entity-list">
        {people?.map((person) => (
          <li key={person.id} className="entity-list-item">
            {editingId === person.id ? (
              <div className="entity-edit-form">
                <div className="form-row">
                  <input
                    type="text"
                    value={editDraft.name}
                    onChange={(e) => setEditDraft((d) => ({ ...d, name: e.target.value }))}
                  />
                  <input
                    type="text"
                    placeholder="Rolle"
                    value={editDraft.rolle}
                    onChange={(e) => setEditDraft((d) => ({ ...d, rolle: e.target.value }))}
                  />
                  <input
                    type="text"
                    placeholder="Kontakt"
                    value={editDraft.kontaktinfo}
                    onChange={(e) => setEditDraft((d) => ({ ...d, kontaktinfo: e.target.value }))}
                  />
                </div>
                <textarea
                  rows={2}
                  value={editDraft.notizen}
                  onChange={(e) => setEditDraft((d) => ({ ...d, notizen: e.target.value }))}
                />
                <div className="entity-edit-actions">
                  <button onClick={() => handleSaveEdit(person.id)}>Speichern</button>
                  <button className="link-button" onClick={() => setEditingId(null)}>
                    Abbrechen
                  </button>
                </div>
              </div>
            ) : (
              <>
                <div className="entity-list-item-header">
                  <span className="entity-title">{person.name}</span>
                  {person.rolle && <span className="entity-meta">{person.rolle}</span>}
                </div>
                {person.kontaktinfo && <div className="entity-meta">{person.kontaktinfo}</div>}
                {person.notizen && <p className="entity-notes">{person.notizen}</p>}
                <div className="entity-actions">
                  <button className="link-button" onClick={() => startEdit(person)}>
                    Bearbeiten
                  </button>
                  <button className="link-button" onClick={() => handleDelete(person.id)}>
                    Löschen
                  </button>
                </div>
              </>
            )}
          </li>
        ))}
      </ul>
    </section>
  )
}
