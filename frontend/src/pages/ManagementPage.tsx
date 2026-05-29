import { useCallback, useEffect, useRef, useState } from 'react'
import { motion } from 'framer-motion'
import { Download, RefreshCw, Save, Upload } from 'lucide-react'
import { AnomalyCatalogTab } from '@/components/management/AnomalyCatalogTab'
import { DescriptionsTab, type DescriptionRule } from '@/components/management/DescriptionsTab'
import { DocumentTab } from '@/components/management/DocumentTab'
import { InputDataTab } from '@/components/management/InputDataTab'
import { LegendaTab } from '@/components/management/LegendaTab'
import { ManagementChecklist } from '@/components/management/ManagementChecklist'
import { PhotosRspTab } from '@/components/management/PhotosRspTab'
import { Button } from '@/components/ui/button'
import { PageHeader, PageShell } from '@/components/layout/PageShell'
import {
  getManagementSettings,
  updateManagementSettings,
} from '@/services/api-client'
import {
  exportManagementConfig,
  getAnomalyCatalog,
  getManagementSummary,
  importManagementConfig,
  type ManagementSummaryResponse,
} from '@/services/management-api'
import { cn } from '@/utils/cn'

type TabId = 'entrada' | 'catalogo' | 'textos' | 'fotos' | 'documento'

const TABS: { id: TabId; label: string }[] = [
  { id: 'entrada', label: 'Dados de entrada' },
  { id: 'catalogo', label: 'Catálogo' },
  { id: 'textos', label: 'Textos' },
  { id: 'fotos', label: 'Fotos e RSP' },
  { id: 'documento', label: 'Documento' },
]

export function ManagementPage() {
  const [activeTab, setActiveTab] = useState<TabId>('entrada')
  const [loading, setLoading] = useState(true)
  const [saving, setSaving] = useState(false)
  const [dirty, setDirty] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [savedHint, setSavedHint] = useState(false)
  const [summary, setSummary] = useState<ManagementSummaryResponse | null>(null)

  const [runtimeDefaults, setRuntimeDefaults] = useState<Record<string, string>>({})
  const [runtimeSettings, setRuntimeSettings] = useState<Record<string, string>>({})
  const [descriptionRules, setDescriptionRules] = useState<DescriptionRule[]>([])
  const [referenceFields, setReferenceFields] = useState<Array<{ token: string; label: string }>>(
    [],
  )
  const [templateKeys, setTemplateKeys] = useState<string[]>([])

  const catalogSaveRef = useRef<(() => Promise<void>) | null>(null)
  const legendaSaveRef = useRef<(() => Promise<void>) | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const [data, catalog, sum] = await Promise.all([
        getManagementSettings(),
        getAnomalyCatalog(),
        getManagementSummary(),
      ])
      setRuntimeDefaults(data.runtime_defaults ?? {})
      setRuntimeSettings(data.runtime_settings ?? {})
      setDescriptionRules(
        (data.description_rules ?? []).map((rule, index) => ({
          id: `rule-${index}-${rule.key}`,
          key: rule.key,
          template: rule.template,
        })),
      )
      setReferenceFields(data.reference_fields ?? [])
      setTemplateKeys(catalog.template_keys)
      setSummary(sum)
      setDirty(false)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao carregar configurações')
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  useEffect(() => {
    const onBeforeUnload = (e: BeforeUnloadEvent) => {
      if (dirty) {
        e.preventDefault()
      }
    }
    window.addEventListener('beforeunload', onBeforeUnload)
    return () => window.removeEventListener('beforeunload', onBeforeUnload)
  }, [dirty])

  const markDirty = () => setDirty(true)

  const handleSave = async () => {
    setSaving(true)
    setError(null)
    try {
      const normalized = descriptionRules
        .map((rule) => ({
          key: rule.key.trim(),
          template: rule.template.trim(),
        }))
        .filter((rule) => rule.key && rule.template)

      if (!normalized.length) {
        setError('Cadastre pelo menos uma regra com chave e template.')
        setSaving(false)
        return
      }

      await updateManagementSettings({
        runtime_settings: runtimeSettings,
        description_rules: normalized,
      })

      if (catalogSaveRef.current) {
        await catalogSaveRef.current()
      }
      if (legendaSaveRef.current) {
        await legendaSaveRef.current()
      }

      setSavedHint(true)
      setDirty(false)
      setTimeout(() => setSavedHint(false), 2000)
      const sum = await getManagementSummary()
      setSummary(sum)
      const catalog = await getAnomalyCatalog()
      setTemplateKeys(catalog.template_keys)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao salvar')
    } finally {
      setSaving(false)
    }
  }

  const handleExport = async () => {
    try {
      const bundle = await exportManagementConfig()
      const blob = new Blob([JSON.stringify(bundle, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = `oae-config-${new Date().toISOString().slice(0, 10)}.json`
      a.click()
      URL.revokeObjectURL(url)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao exportar')
    }
  }

  const handleImport = async (file: File) => {
    try {
      await importManagementConfig(file)
      await load()
      setSavedHint(true)
      setTimeout(() => setSavedHint(false), 2000)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro ao importar')
    }
  }

  if (loading) {
    return (
      <PageShell width="wide">
        <p className="text-sm text-graphite-500">Carregando configurações...</p>
      </PageShell>
    )
  }

  return (
    <PageShell width="wide">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <PageHeader
          title="Gerenciamento"
          description="Prepare dados de entrada e personalize textos, fotos e documento — configuração global para todas as obras."
          actions={
            <div className="flex flex-wrap gap-2">
              <label className="inline-flex cursor-pointer">
                <input
                  type="file"
                  accept="application/json,.json"
                  className="sr-only"
                  onChange={(e) => {
                    const file = e.target.files?.[0]
                    if (file) void handleImport(file)
                    e.target.value = ''
                  }}
                />
                <span className="inline-flex items-center gap-1 rounded-lg border border-graphite-200 bg-white px-3 py-2 text-sm hover:bg-graphite-50">
                  <Upload className="h-4 w-4" />
                  Importar
                </span>
              </label>
              <Button type="button" variant="secondary" onClick={() => void handleExport()}>
                <Download className="h-4 w-4" />
                Exportar
              </Button>
              <Button type="button" variant="secondary" onClick={() => void load()}>
                <RefreshCw className="h-4 w-4" />
                Recarregar
              </Button>
              <Button type="button" onClick={() => void handleSave()} disabled={saving}>
                <Save className="h-4 w-4" />
                {saving ? 'Salvando...' : dirty ? 'Salvar alterações' : 'Salvar'}
              </Button>
            </div>
          }
        />

        {dirty ? (
          <p className="mb-3 text-xs text-warning">Alterações não salvas.</p>
        ) : null}
        {savedHint ? (
          <p className="mb-3 rounded-lg border border-success/30 bg-success-bg px-3 py-2 text-sm text-success">
            Configurações salvas.
          </p>
        ) : null}
        {error ? (
          <p className="mb-3 rounded-lg border border-error/30 bg-red-50 px-3 py-2 text-sm text-error">
            {error}
          </p>
        ) : null}

        <ManagementChecklist summary={summary} />

        <nav className="mb-6 flex flex-wrap gap-1 border-b border-graphite-200">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              type="button"
              className={cn(
                'px-4 py-2.5 text-sm font-medium transition-colors border-b-2 -mb-px',
                activeTab === tab.id
                  ? 'border-petrol-600 text-petrol-700'
                  : 'border-transparent text-graphite-500 hover:text-graphite-700',
              )}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </nav>

        {activeTab === 'entrada' ? (
          <div className="space-y-6">
            <InputDataTab />
            <LegendaTab
              onSaved={() => {}}
              registerSave={(fn) => {
                legendaSaveRef.current = fn
              }}
            />
          </div>
        ) : null}

        {activeTab === 'catalogo' ? (
          <AnomalyCatalogTab
            onSaved={() => {}}
            registerSave={(fn) => {
              catalogSaveRef.current = fn
            }}
          />
        ) : null}

        {activeTab === 'textos' ? (
          <DescriptionsTab
            runtimeDefaults={runtimeDefaults}
            runtimeSettings={runtimeSettings}
            onRuntimeChange={(key, value) => {
              markDirty()
              setRuntimeSettings((prev) => ({ ...prev, [key]: value }))
            }}
            onRuntimeReset={(key) => {
              markDirty()
              setRuntimeSettings((prev) => ({ ...prev, [key]: runtimeDefaults[key] ?? '' }))
            }}
            descriptionRules={descriptionRules}
            onRulesChange={(rules) => {
              markDirty()
              setDescriptionRules(rules)
            }}
            referenceFields={referenceFields}
            templateKeys={templateKeys}
          />
        ) : null}

        {activeTab === 'fotos' ? (
          <PhotosRspTab
            runtimeDefaults={runtimeDefaults}
            runtimeSettings={runtimeSettings}
            onRuntimeChange={(key, value) => {
              markDirty()
              setRuntimeSettings((prev) => ({ ...prev, [key]: value }))
            }}
            onRuntimeReset={(key) => {
              markDirty()
              setRuntimeSettings((prev) => ({ ...prev, [key]: runtimeDefaults[key] ?? '' }))
            }}
          />
        ) : null}

        {activeTab === 'documento' ? <DocumentTab /> : null}
      </motion.div>
    </PageShell>
  )
}
