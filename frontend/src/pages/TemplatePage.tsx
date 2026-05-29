import { useRef } from 'react'
import { motion } from 'framer-motion'
import { Download, FileText, RotateCcw, Upload } from 'lucide-react'
import { Button, buttonVariants } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { PageHeader, PageShell } from '@/components/layout/PageShell'
import {
  DEFAULT_TEMPLATE_NAME,
  DEFAULT_TEMPLATE_URL,
  useTemplateStore,
} from '@/store/template-store'
import { formatDate, formatFileSize } from '@/utils/project-status'
import { cn } from '@/utils/cn'

export function TemplatePage() {
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

  const handleUpload = (event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0]
    if (!file) return
    if (!file.name.toLowerCase().endsWith('.docx')) {
      window.alert('Selecione um arquivo .docx')
      return
    }
    setCustomTemplate(file)
    event.target.value = ''
  }

  const needsReupload = useCustomTemplate && customTemplate && !hasCustomBlob()

  return (
    <PageShell width="narrow">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <PageHeader
          title="Template Word"
          description="O relatório utiliza o modelo RSP padrão. Baixe o template oficial, edite no Word e envie a versão personalizada quando necessário."
        />

        <Card className="mt-6 mb-6">
          <CardHeader>
            <div className="flex items-start gap-3">
              <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-petrol-100">
                <FileText className="h-5 w-5 text-petrol-600" />
              </div>
              <div>
                <CardTitle>Modelo padrão RSP</CardTitle>
                <CardDescription className="mt-1">
                  {DEFAULT_TEMPLATE_NAME} — placeholders docxtpl para anomalias e anexo fotográfico
                </CardDescription>
              </div>
            </div>
          </CardHeader>
          <CardContent>
            <a
              href={DEFAULT_TEMPLATE_URL}
              download={DEFAULT_TEMPLATE_NAME}
              className={cn(buttonVariants({ variant: 'secondary', size: 'default' }))}
            >
              <Download className="h-4 w-4" />
              Baixar template padrão
            </a>
          </CardContent>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Template personalizado</CardTitle>
            <CardDescription>
              Opcional. Ao enviar um .docx editado, ele substitui o padrão na geração do relatório.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            {useCustomTemplate && customTemplate ? (
              <div className="rounded-lg border border-petrol-200 bg-petrol-50/40 p-4">
                <p className="text-sm font-medium text-graphite-800">{customTemplate.name}</p>
                <p className="mt-1 text-xs text-graphite-500">
                  {customTemplate.size ? formatFileSize(customTemplate.size) : ''}
                  {customTemplate.lastModified
                    ? ` · ${formatDate(new Date(customTemplate.lastModified).toISOString())}`
                    : ''}
                </p>
                {needsReupload ? (
                  <p className="mt-2 text-xs text-warning">
                    Reenvie o arquivo após recarregar a página — o conteúdo não permanece no
                    navegador.
                  </p>
                ) : null}
              </div>
            ) : (
              <p className="text-sm text-graphite-500">
                Nenhum template personalizado. O modelo padrão será utilizado.
              </p>
            )}

            <input
              ref={inputRef}
              id="template-upload-input"
              type="file"
              accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document"
              className="sr-only"
              onChange={handleUpload}
            />

            <div className="flex flex-wrap gap-3">
              <label
                htmlFor="template-upload-input"
                className={cn(buttonVariants({ variant: 'default', size: 'default' }), 'cursor-pointer')}
              >
                <Upload className="h-4 w-4" />
                Enviar template editado
              </label>
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
                  className={cn(buttonVariants({ variant: 'outline', size: 'default' }))}
                >
                  <Download className="h-4 w-4" />
                  Baixar versão enviada
                </a>
              ) : null}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </PageShell>
  )
}

