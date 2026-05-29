import { useCallback, useEffect, useState } from 'react'
import { Plus, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Label } from '@/components/ui/input'
import { getLegenda, updateLegenda, type LegendaEntry } from '@/services/management-api'

interface Props {
  onSaved: () => void
  registerSave: (fn: () => Promise<void>) => void
}

export function LegendaTab({ onSaved, registerSave }: Props) {
  const [entries, setEntries] = useState<LegendaEntry[]>([])
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    const data = await getLegenda()
    setEntries(data.entries)
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const save = useCallback(async () => {
    setError(null)
    const codes = entries.map((e) => e.code.trim().toUpperCase())
    if (new Set(codes).size !== codes.filter(Boolean).length) {
      setError('Existem códigos duplicados na legenda.')
      throw new Error('Códigos duplicados')
    }
    await updateLegenda(
      entries.filter((e) => e.code.trim() && e.label.trim()).map((e) => ({
        code: e.code.trim().toUpperCase(),
        label: e.label.trim(),
      })),
    )
    await load()
    onSaved()
  }, [entries, load, onSaved])

  useEffect(() => {
    registerSave(save)
  }, [registerSave, save])

  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between">
        <div>
          <CardTitle>Siglas estruturais</CardTitle>
          <CardDescription>
            Códigos do campo Local (LB, VL, P…) usados na ordenação fotográfica e nas descrições.
          </CardDescription>
        </div>
        <Button
          type="button"
          variant="secondary"
          size="sm"
          onClick={() => setEntries([...entries, { code: '', label: '' }])}
        >
          <Plus className="h-4 w-4" />
          Sigla
        </Button>
      </CardHeader>
      <CardContent className="space-y-3">
        {error ? <p className="text-sm text-error">{error}</p> : null}
        <div className="max-h-[420px] overflow-y-auto space-y-2">
          {entries.map((entry, index) => (
            <div key={`leg-${index}`} className="flex items-center gap-2">
              <div className="w-24">
                <Label className="sr-only">Código</Label>
                <Input
                  value={entry.code}
                  placeholder="LB"
                  onChange={(e) => {
                    const next = [...entries]
                    next[index] = { ...entry, code: e.target.value.toUpperCase() }
                    setEntries(next)
                  }}
                />
              </div>
              <div className="flex-1">
                <Input
                  value={entry.label}
                  placeholder="Laje em balanço"
                  onChange={(e) => {
                    const next = [...entries]
                    next[index] = { ...entry, label: e.target.value }
                    setEntries(next)
                  }}
                />
              </div>
              <button
                type="button"
                className="text-error"
                onClick={() => setEntries(entries.filter((_, i) => i !== index))}
              >
                <Trash2 className="h-4 w-4" />
              </button>
            </div>
          ))}
        </div>
      </CardContent>
    </Card>
  )
}
