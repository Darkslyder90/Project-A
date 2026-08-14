import { useEffect, useState } from 'react'

const STORAGE_KEY = 'project-a.active-project-id'

export function useActiveProjectId(): [number | null, (id: number | null) => void] {
  const [activeProjectId, setActiveProjectIdState] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY)
    return stored ? Number(stored) : null
  })

  useEffect(() => {
    if (activeProjectId === null) {
      localStorage.removeItem(STORAGE_KEY)
    } else {
      localStorage.setItem(STORAGE_KEY, String(activeProjectId))
    }
  }, [activeProjectId])

  return [activeProjectId, setActiveProjectIdState]
}
