import { useCallback, useState } from 'react'
import { useProjectStore } from '@/store/project-store'
import type { PhotoEntry } from '@/types/project'

export function useSaveDraft(projectId: string | undefined) {
  const saveProjectDraft = useProjectStore((s) => s.saveProjectDraft)
  const [savedHint, setSavedHint] = useState(false)

  const saveDraft = useCallback(
    (options?: { photos?: PhotoEntry[] }) => {
      if (!projectId) return
      saveProjectDraft(projectId, options)
      setSavedHint(true)
      window.setTimeout(() => setSavedHint(false), 2000)
    },
    [projectId, saveProjectDraft],
  )

  return { saveDraft, savedHint }
}
