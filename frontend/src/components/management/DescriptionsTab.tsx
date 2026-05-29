import { useCallback, useEffect, useRef, useState } from 'react'
import { Copy, Plus, Search, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Label, Textarea } from '@/components/ui/input'
import { previewDescription } from '@/services/management-api'

export type DescriptionRule = { id: string; key: string; template: string }

interface Props {
  runtimeDefaults: Record<string, string>
  runtimeSettings: Record<string, string>
  onRuntimeChange: (key: string, value: string) => void
  onRuntimeReset: (key: string) => void
  descriptionRules: DescriptionRule[]
  onRulesChange: (rules: DescriptionRule[]) => void
  referenceFields: Array<{ token: string; label: string }>
  templateKeys: string[]
}

const RUNTIME_FIELDS = [
  {
    key: 'default_report_title_template',
    label: 'Template de título',
    help: 'Ex.: Relatório de Inspeção — {project_name}',
    previewKeys: ['project_name', 'rodovia', 'km'],
  },
  {
    key: 'bridge_location_line_template',
    label: 'Linha de localização',
    help: 'Ex.: {project_name} — {rodovia} — — Km {km} —',
    previewKeys: ['project_name', 'rodovia', 'km'],
  },
  {
    key: 'photo_caption_template',
    label: 'Legenda da foto',
    help: '{figure_number}, {code}, {description_line}, {location_line}',
    previewKeys: ['figure_number', 'code', 'description_line', 'location_line'],
  },
  {
    key: 'photo_direction',
    label: 'Direção RSP (sufixo)',
    help: 'S ou N — sufixo do código E116K244710F001S',
    previewKeys: [],
  },
  {
    key: 'photo_seq_width',
    label: 'Largura sequencial F001',
    help: 'Número de dígitos (ex.: 3)',
    previewKeys: [],
  },
  {
    key: 'default_bridge_prefix',
    label: 'Prefixo RSP padrão',
    help: 'Letra antes da rodovia (ex.: E)',
    previewKeys: [],
  },
  {
    key: 'excel_preferred_sheet',
    label: 'Aba Excel preferida',
    help: 'Ex.: db_ficha',
    previewKeys: [],
  },
] as const

function renderRuntimePreview(template: string, keys: string[]): string {
  const samples: Record<string, string> = {
    project_name: 'Ponte Exemplo',
    rodovia: 'BR-116',
    km: '244+710',
    bridge_id: 'E116',
    figure_number: '1',
    code: 'E116K244710F001S',
    description_line: 'Fissuras verticais na laje em balanço LB1.',
    location_line: 'Ponte Exemplo — BR-116 — — Km 244+710 —',
  }
  let result = template
  for (const key of keys) {
    result = result.replaceAll(`{${key}}`, samples[key] ?? `{${key}}`)
  }
  return result
}

export function DescriptionsTab({
  runtimeDefaults,
  runtimeSettings,
  onRuntimeChange,
  onRuntimeReset,
  descriptionRules,
  onRulesChange,
  referenceFields,
  templateKeys,
}: Props) {
  const [search, setSearch] = useState('')
  const [draftRules, setDraftRules] = useState<Record<string, { key: string; template: string }>>({})
  const [previews, setPreviews] = useState<Record<string, string>>({})
  const activeTextarea = useRef<string | null>(null)

  useEffect(() => {
    setDraftRules(
      Object.fromEntries(descriptionRules.map((r) => [r.id, { key: r.key, template: r.template }])),
    )
  }, [descriptionRules])

  const filteredRules = descriptionRules.filter((rule) => {
    if (!search.trim()) return true
    const term = search.toLowerCase()
    const draft = draftRules[rule.id]
    return (
      rule.key.toLowerCase().includes(term) ||
      (draft?.template ?? rule.template).toLowerCase().includes(term)
    )
  })

  const commitRule = (id: string) => {
    const draft = draftRules[id]
    if (!draft) return
    onRulesChange(
      descriptionRules.map((r) =>
        r.id === id ? { ...r, key: draft.key, template: draft.template } : r,
      ),
    )
  }

  const refreshPreview = useCallback(async (id: string, template: string) => {
    try {
      const { rendered } = await previewDescription(template)
      setPreviews((prev) => ({ ...prev, [id]: rendered }))
    } catch {
      setPreviews((prev) => ({ ...prev, [id]: '(erro no preview)' }))
    }
  }, [])

  const insertToken = (token: string) => {
    const id = activeTextarea.current
    if (!id) return
    const draft = draftRules[id]
    if (!draft) return
    const next = `${draft.template}${token}`
    setDraftRules((prev) => ({ ...prev, [id]: { ...draft, template: next } }))
  }

  const catalogKeys = new Set(templateKeys)

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Parâmetros gerais</CardTitle>
          <CardDescription>Templates globais de título, localização e fotos.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {RUNTIME_FIELDS.map((item) => (
            <div key={item.key} className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>{item.label}</Label>
                <button
                  type="button"
                  className="text-xs text-petrol-700 hover:underline"
                  onClick={() => onRuntimeReset(item.key)}
                >
                  Restaurar padrão
                </button>
              </div>
              <Input
                value={runtimeSettings[item.key] ?? ''}
                onChange={(e) => onRuntimeChange(item.key, e.target.value)}
              />
              <p className="text-xs text-graphite-500">{item.help}</p>
              {item.previewKeys.length > 0 ? (
                <p className="text-xs text-graphite-600">
                  Preview:{' '}
                  {renderRuntimePreview(runtimeSettings[item.key] ?? runtimeDefaults[item.key] ?? '', [
                    ...item.previewKeys,
                  ])}
                </p>
              ) : null}
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-3">
          <div>
            <CardTitle>Regras de descrição</CardTitle>
            <CardDescription>Chaves ligadas ao catálogo (template_key).</CardDescription>
          </div>
          <Button
            type="button"
            variant="secondary"
            onClick={() => {
              const id = `rule-${Date.now()}`
              onRulesChange([...descriptionRules, { id, key: '', template: '' }])
            }}
          >
            <Plus className="h-4 w-4" />
            Nova regra
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-graphite-400" />
            <Input
              className="pl-9"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              placeholder="Buscar regra..."
            />
          </div>

          <div className="rounded-lg border border-graphite-200 bg-graphite-50 p-3">
            <p className="text-xs font-medium text-graphite-600">Inserir placeholder (clique)</p>
            <div className="mt-2 flex flex-wrap gap-2">
              {referenceFields.map((field) => (
                <button
                  key={field.token}
                  type="button"
                  className="rounded-md border border-graphite-200 bg-white px-2 py-1 text-xs text-graphite-600 hover:border-petrol-300"
                  onClick={() => insertToken(field.token)}
                >
                  {field.token}
                </button>
              ))}
            </div>
          </div>

          {filteredRules.map((rule) => {
            const draft = draftRules[rule.id] ?? { key: rule.key, template: rule.template }
            const inCatalog = draft.key === 'default' || catalogKeys.has(draft.key)
            return (
              <div key={rule.id} className="rounded-lg border border-graphite-200 p-4">
                <div className="mb-3 flex justify-between">
                  {!inCatalog && draft.key ? (
                    <span className="text-xs text-warning">Sem entrada no catálogo</span>
                  ) : (
                    <span />
                  )}
                  <div className="flex gap-3">
                    <button
                      type="button"
                      className="text-xs text-petrol-700"
                      onClick={() => {
                        const id = `rule-${Date.now()}`
                        onRulesChange([
                          ...descriptionRules,
                          { id, key: `${draft.key}_copia`, template: draft.template },
                        ])
                      }}
                    >
                      <Copy className="h-3.5 w-3.5 inline" /> Duplicar
                    </button>
                    <button
                      type="button"
                      className="text-xs text-error"
                      onClick={() =>
                        onRulesChange(descriptionRules.filter((r) => r.id !== rule.id))
                      }
                    >
                      <Trash2 className="h-3.5 w-3.5 inline" /> Remover
                    </button>
                  </div>
                </div>
                <div className="grid gap-3 md:grid-cols-[200px_1fr]">
                  <div>
                    <Label>Chave</Label>
                    <Input
                      value={draft.key}
                      onChange={(e) =>
                        setDraftRules((prev) => ({
                          ...prev,
                          [rule.id]: { ...draft, key: e.target.value },
                        }))
                      }
                      onBlur={() => commitRule(rule.id)}
                    />
                  </div>
                  <div>
                    <Label>Template</Label>
                    <Textarea
                      className="min-h-[90px]"
                      value={draft.template}
                      onFocus={() => {
                        activeTextarea.current = rule.id
                      }}
                      onChange={(e) =>
                        setDraftRules((prev) => ({
                          ...prev,
                          [rule.id]: { ...draft, template: e.target.value },
                        }))
                      }
                      onBlur={() => {
                        commitRule(rule.id)
                        void refreshPreview(rule.id, draft.template)
                      }}
                    />
                  </div>
                </div>
                <p className="mt-2 text-xs text-graphite-600">
                  Preview: {previews[rule.id] ?? 'Edite o template para atualizar'}
                </p>
              </div>
            )
          })}
        </CardContent>
      </Card>
    </div>
  )
}
