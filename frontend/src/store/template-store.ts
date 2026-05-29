import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { FileRef } from '@/types/project'

export const DEFAULT_TEMPLATE_URL = '/templates/report_template.docx'
export const DEFAULT_TEMPLATE_NAME = 'report_template.docx'

/** Blob em memória (não persiste entre recarregamentos). */
const customTemplateBlob = { current: null as Blob | null }

interface TemplateStore {
  customTemplate: FileRef | null
  useCustomTemplate: boolean

  setCustomTemplate: (file: File) => void
  clearCustomTemplate: () => void
  getDownloadUrl: () => string
  getActiveTemplateName: () => string
  hasCustomBlob: () => boolean
  getCustomBlob: () => Blob | null
}

export const useTemplateStore = create<TemplateStore>()(
  persist(
    (set, get) => ({
      customTemplate: null,
      useCustomTemplate: false,

      setCustomTemplate: (file: File) => {
        customTemplateBlob.current = file
        set({
          useCustomTemplate: true,
          customTemplate: {
            name: file.name,
            path: file.name,
            size: file.size,
            lastModified: file.lastModified,
          },
        })
      },

      clearCustomTemplate: () => {
        customTemplateBlob.current = null
        set({ customTemplate: null, useCustomTemplate: false })
      },

      getDownloadUrl: () => {
        if (get().useCustomTemplate && customTemplateBlob.current) {
          return URL.createObjectURL(customTemplateBlob.current)
        }
        return DEFAULT_TEMPLATE_URL
      },

      getActiveTemplateName: () => {
        if (get().useCustomTemplate && get().customTemplate) {
          return get().customTemplate!.name
        }
        return DEFAULT_TEMPLATE_NAME
      },

      hasCustomBlob: () => Boolean(customTemplateBlob.current),

      getCustomBlob: () => customTemplateBlob.current,
    }),
    {
      name: 'oae-report-template',
      partialize: (state) => ({
        customTemplate: state.customTemplate,
        useCustomTemplate: state.useCustomTemplate,
      }),
      onRehydrateStorage: () => () => {
        customTemplateBlob.current = null
      },
    },
  ),
)
