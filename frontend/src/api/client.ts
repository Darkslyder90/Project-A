export type Project = {
  id: number
  name: string
  beschreibung: string | null
  erstellt_am: string
}

export type ProjectCreateInput = {
  name: string
  beschreibung?: string | null
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    const body = await response.json().catch(() => null)
    throw new Error(body?.detail ?? `Anfrage fehlgeschlagen (${response.status})`)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

export const api = {
  listProjects: () => request<Project[]>('/api/projects'),
  createProject: (input: ProjectCreateInput) =>
    request<Project>('/api/projects', { method: 'POST', body: JSON.stringify(input) }),
  deleteProject: (id: number) => request<void>(`/api/projects/${id}`, { method: 'DELETE' }),
}
