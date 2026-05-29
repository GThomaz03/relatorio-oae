import { useRef } from 'react'
import { Download, FileText, RotateCcw, Upload } from 'lucide-react'
import { Button, buttonVariants } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import {
  DEFAULT_TEMPLATE_NAME,
  DEFAULT_TEMPLATE_URL,
  useTemplateStore,
} from '@/store/template-store'
import { formatDate, formatFileSize } from '@/utils/project-status'
import { cn } from '@/utils/cn'

export function DocumentTab() {
  const inputRef = useRef<HTMLInputElement>(null)
  const customTemplate = useTemplateStore((s) => s.customTemplate)
  const useCustomTemplate = useTemplateStore((s) => s.useCustomTemplate)
  const setCustomTemplate = useTemplateStore((s) => s.setCustomTemplate)
  const clearCustomTemplate = useTemplateStore((s) => s.clearCustomTemplate)
  const hasCustomBlob = useTemplateStore((s) => s.hasCustomBlob)
  const getCustomBlob = useTemplateStore((s) => s.getCustomBlob)

  const customBlob = getCustomBlob()
  const customDownloadUrl =
    customBlob && customTemplate ? URL.createObjectURL(customBlob) : null
  const needsReupload = useCustomTemplate && customTemplate && !hasCustomBlob()

  return (
    <div className="space-y-6">
      <p className="text-sm text-graphite-600">
        O template Word personalizado aplica-se a <strong>todas as obras</strong> nesta instalação.
      </p>

      <Card>
        <CardHeader>
          <div className="flex items-start gap-3">
            <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-petrol-100">
              <FileText className="h-5 w-5 text-petrol-600" />
            </div>
            <div>
              <CardTitle>Modelo padrão RSP</CardTitle>
              <CardDescription className="mt-1">{DEFAULT_TEMPLATE_NAME}</CardDescription>
            </div>
          </div>
        </CardHeader>
        <CardContent>
          <a
            href={DEFAULT_TEMPLATE_URL}
            download={DEFAULT_TEMPLATE_NAME}
            className={cn(buttonVariants({ variant: 'secondary' }))}
          >
            <Download className="h-4 w-4" />
            Baixar template padrão
          </a>
        </CardContent>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Template personalizado</CardTitle>
          <CardDescription>Substitui o padrão na geração do relatório.</CardDescription>
        </CardHeader>
        <CardContent className="space-y-4">
          {useCustomTemplate && customTemplate ? (
            <div className="rounded-lg border border-petrol-200 bg-petrol-50/40 p-4">
              <p className="text-sm font-medium">{customTemplate.name}</p>
              <p className="mt-1 text-xs text-graphite-500">
                {customTemplate.size ? formatFileSize(customTemplate.size) : ''}
                {customTemplate.lastModified
                  ? ` · ${formatDate(new Date(customTemplate.lastModified).toISOString())}`
                  : ''}
              </p>
              {needsReupload ? (
                <p className="mt-2 text-xs text-warning">Reenvie o arquivo após recarregar.</p>
              ) : null}
            </div>
          ) : (
            <p className="text-sm text-graphite-500">Nenhum template personalizado ativo.</p>
          )}

          <input
            ref={inputRef}
            type="file"
            accept=".docx"
            className="sr-only"
            onChange={(e) => {
              const file = e.target.files?.[0]
              if (!file) return
              if (!file.name.toLowerCase().endsWith('.docx')) {
                window.alert('Selecione um arquivo .docx')
                return
              }
              setCustomTemplate(file)
              e.target.value = ''
            }}
          />

          <div className="flex flex-wrap gap-3">
            <Button type="button" onClick={() => inputRef.current?.click()}>
              <Upload className="h-4 w-4" />
              Enviar template
            </Button>
            {useCustomTemplate ? (
              <Button type="button" variant="secondary" onClick={clearCustomTemplate}>
                <RotateCcw className="h-4 w-4" />
                Voltar ao padrão
              </Button>
            ) : null}
            {customDownloadUrl && customTemplate ? (
              <a
                href={customDownloadUrl}
                download={customTemplate.name}
                className={cn(buttonVariants({ variant: 'outline' }))}
              >
                <Download className="h-4 w-4" />
                Baixar enviado
              </a>
            ) : null}
          </div>
        </CardContent>
      </Card>
    </div>
  )
}
