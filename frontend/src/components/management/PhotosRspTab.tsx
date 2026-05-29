import { useEffect, useState } from 'react'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { getPhotoSections, type PhotoSectionItem } from '@/services/management-api'

interface Props {
  runtimeSettings: Record<string, string>
  runtimeDefaults: Record<string, string>
  onRuntimeChange: (key: string, value: string) => void
  onRuntimeReset: (key: string) => void
}

export function PhotosRspTab({
  runtimeSettings,
  runtimeDefaults,
  onRuntimeChange,
  onRuntimeReset,
}: Props) {
  const [sections, setSections] = useState<PhotoSectionItem[]>([])

  useEffect(() => {
    void getPhotoSections().then(setSections)
  }, [])

  return (
    <div className="space-y-6">
      <Card>
        <CardHeader>
          <CardTitle>Ordem técnica do registro fotográfico</CardTitle>
          <CardDescription>
            Sequência fixa RSP aplicada à numeração F001, anexo fotográfico e tela de revisão.
            (Somente leitura — ordem definida pelo padrão de engenharia.)
          </CardDescription>
        </CardHeader>
        <CardContent>
          <ol className="grid gap-1 sm:grid-cols-2 text-sm text-graphite-700">
            {sections.map((s) => (
              <li key={s.key} className="flex gap-2 rounded-md bg-graphite-50 px-2 py-1">
                <span className="w-6 shrink-0 font-mono text-xs text-graphite-400">{s.order}</span>
                <span>{s.label}</span>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Códigos e legendas RSP</CardTitle>
          <CardDescription>Parâmetros usados na geração dos códigos fotográficos.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {[
            {
              key: 'photo_caption_template',
              label: 'Template da legenda no Word',
              help: 'Fig. {figure_number} — {code} — {description_line}',
            },
            {
              key: 'photo_direction',
              label: 'Sufixo de direção',
              help: 'Última letra do código (S/N)',
            },
            {
              key: 'photo_seq_width',
              label: 'Dígitos da sequência',
              help: 'Ex.: 3 → F001',
            },
          ].map((item) => (
            <div key={item.key} className="space-y-1">
              <div className="flex justify-between">
                <label className="text-sm font-medium text-graphite-700">{item.label}</label>
                <button
                  type="button"
                  className="text-xs text-petrol-700 hover:underline"
                  onClick={() => onRuntimeReset(item.key)}
                >
                  Restaurar
                </button>
              </div>
              <input
                className="flex h-10 w-full rounded-lg border border-graphite-200 px-3 text-sm"
                value={runtimeSettings[item.key] ?? runtimeDefaults[item.key] ?? ''}
                onChange={(e) => onRuntimeChange(item.key, e.target.value)}
              />
              <p className="text-xs text-graphite-500">{item.help}</p>
            </div>
          ))}
        </CardContent>
      </Card>
    </div>
  )
}
