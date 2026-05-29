import { useCallback, useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Label, Textarea } from '@/components/ui/input'
import {
  getAnomalyCatalog,
  previewAnomalyCatalog,
  updateAnomalyCatalog,
  type AnomalyCatalogResponse,
  type CatalogBaseEntry,
  type CatalogModifierEntry,
  type CatalogPreviewResponse,
} from '@/services/management-api'

interface Props {
  onSaved: () => void
  registerSave: (fn: () => Promise<void>) => void
}

export function AnomalyCatalogTab({ onSaved, registerSave }: Props) {
  const [catalog, setCatalog] = useState<AnomalyCatalogResponse | null>(null)
  const [previewText, setPreviewText] = useState('1.10 - Fissuras verticais com manchas de umidade')
  const [preview, setPreview] = useState<CatalogPreviewResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setCatalog(await getAnomalyCatalog())
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const save = useCallback(async () => {
    if (!catalog) return
    setError(null)
    await updateAnomalyCatalog({ bases: catalog.bases, modifiers: catalog.modifiers })
    await load()
    onSaved()
  }, [catalog, load, onSaved])

  useEffect(() => {
    registerSave(save)
  }, [registerSave, save])

  const updateBase = (index: number, patch: Partial<CatalogBaseEntry>) => {
    if (!catalog) return
    const bases = [...catalog.bases]
    bases[index] = { ...bases[index]!, ...patch }
    setCatalog({ ...catalog, bases })
  }

  const updateModifier = (index: number, patch: Partial<CatalogModifierEntry>) => {
    if (!catalog) return
    const modifiers = [...catalog.modifiers]
    modifiers[index] = { ...modifiers[index]!, ...patch }
    setCatalog({ ...catalog, modifiers })
  }

  const runPreview = async () => {
    try {
      setPreview(await previewAnomalyCatalog(previewText))
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Erro no preview')
    }
  }

  if (!catalog) {
    return <p className="text-sm text-graphite-500">Carregando catálogo...</p>
  }

  return (
    <div className="space-y-6">
      {error ? <p className="text-sm text-error">{error}</p> : null}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Bases de anomalia</CardTitle>
            <CardDescription>Texto do Excel → template_key → regra em descriptions.yaml</CardDescription>
          </div>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() =>
              setCatalog({
                ...catalog,
                bases: [
                  ...catalog.bases,
                  { key: '', label: '', template_key: 'default', aliases: [] },
                ],
              })
            }
          >
            <Plus className="h-4 w-4" />
            Base
          </Button>
        </CardHeader>
        <CardContent className="space-y-4">
          {catalog.bases.map((base, index) => (
            <div key={`base-${index}`} className="rounded-lg border border-graphite-200 p-3">
              <div className="mb-2 flex justify-end">
                <button
                  type="button"
                  className="text-xs text-error hover:underline"
                  onClick={() =>
                    setCatalog({
                      ...catalog,
                      bases: catalog.bases.filter((_, i) => i !== index),
                    })
                  }
                >
                  <Trash2 className="h-3.5 w-3.5" />
                </button>
              </div>
              <div className="grid gap-3 md:grid-cols-3">
                <div>
                  <Label>Chave</Label>
                  <Input value={base.key} onChange={(e) => updateBase(index, { key: e.target.value })} />
                </div>
                <div>
                  <Label>Rótulo</Label>
                  <Input
                    value={base.label}
                    onChange={(e) => updateBase(index, { label: e.target.value })}
                  />
                </div>
                <div>
                  <Label>template_key</Label>
                  <select
                    className="flex h-10 w-full rounded-lg border border-graphite-200 px-3 text-sm"
                    value={base.template_key}
                    onChange={(e) => updateBase(index, { template_key: e.target.value })}
                  >
                    {catalog.template_keys.map((k) => (
                      <option key={k} value={k}>
                        {k}
                      </option>
                    ))}
                  </select>
                </div>
              </div>
              <div className="mt-2">
                <Label>Aliases (um por linha)</Label>
                <Textarea
                  className="min-h-[60px] font-mono text-xs"
                  value={base.aliases.join('\n')}
                  onChange={(e) =>
                    updateBase(index, {
                      aliases: e.target.value.split('\n').map((s) => s.trim()).filter(Boolean),
                    })
                  }
                />
              </div>
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <CardTitle>Modificadores</CardTitle>
          <Button
            type="button"
            variant="secondary"
            size="sm"
            onClick={() =>
              setCatalog({
                ...catalog,
                modifiers: [...catalog.modifiers, { key: '', label: '', aliases: [] }],
              })
            }
          >
            <Plus className="h-4 w-4" />
            Modificador
          </Button>
        </CardHeader>
        <CardContent className="space-y-3">
          {catalog.modifiers.map((mod, index) => (
            <div key={`mod-${index}`} className="grid gap-2 rounded-lg border border-graphite-200 p-3 md:grid-cols-2">
              <Input
                placeholder="chave"
                value={mod.key}
                onChange={(e) => updateModifier(index, { key: e.target.value })}
              />
              <Input
                placeholder="rótulo"
                value={mod.label}
                onChange={(e) => updateModifier(index, { label: e.target.value })}
              />
              <Textarea
                className="md:col-span-2 min-h-[50px] text-xs"
                placeholder="aliases"
                value={mod.aliases.join('\n')}
                onChange={(e) =>
                  updateModifier(index, {
                    aliases: e.target.value.split('\n').map((s) => s.trim()).filter(Boolean),
                  })
                }
              />
            </div>
          ))}
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Preview semântico</CardTitle>
        </CardHeader>
        <CardContent className="space-y-3">
          <Textarea value={previewText} onChange={(e) => setPreviewText(e.target.value)} />
          <Button type="button" variant="secondary" onClick={() => void runPreview()}>
            Testar texto
          </Button>
          {preview ? (
            <div className="rounded-md bg-graphite-50 p-3 text-xs text-graphite-700">
              <p>
                Base: {preview.base_label} → template <strong>{preview.template_key}</strong>
              </p>
              {preview.modifier_labels.length ? (
                <p>Modificadores: {preview.modifier_labels.join(', ')}</p>
              ) : null}
              {preview.rendered_description ? (
                <p className="mt-2 font-medium">{preview.rendered_description}</p>
              ) : null}
            </div>
          ) : null}
        </CardContent>
      </Card>
    </div>
  )
}
