import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  CheckCircle2,
  Copy,
  Download,
  ExternalLink,
  FileText,
  FolderOpen,
  Home,
  RefreshCw,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { EmptyState, PageShell } from '@/components/layout/PageShell'
import { artifactUrl, downloadArtifact, openLocalPath } from '@/services/api-client'
import { useProjectStore } from '@/store/project-store'
import { formatDate } from '@/utils/project-status'

export function ReportCompletePage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const projects = useProjectStore((s) => s.projects)
  const duplicateProject = useProjectStore((s) => s.duplicateProject)

  const project = projects.find((p) => p.id === projectId)

  if (!project || project.status !== 'relatorio_gerado') {
    return (
      <PageShell width="centered">
        <EmptyState message="Relatório ainda não foi gerado." />
      </PageShell>
    )
  }

  const stats = project.reportStats
  const reportUrl =
    project.reportDownloadUrl ?? (projectId ? artifactUrl(projectId, 'report') : '')
  const outputUrl =
    project.outputDownloadUrl ?? (projectId ? artifactUrl(projectId, 'output') : '')
  const photosUrl =
    project.photosDownloadUrl ?? (projectId ? artifactUrl(projectId, 'photos') : '')

  const publishedDir = project.publishedOutputDir
  const publishedPhotosDir = project.publishedPhotosDir
  const savedToUserFolder = Boolean(publishedDir)

  const openReport = () => {
    if (project.reportPath && savedToUserFolder) {
      void openLocalPath(project.reportPath)
      return
    }
    void downloadArtifact(
      reportUrl,
      `${project.bridgeId || 'OAE'}_relatorio.docx`,
      { openAfterSave: true },
    )
  }

  const openOutputFolder = () => {
    if (publishedDir) {
      void openLocalPath(publishedDir)
      return
    }
    void downloadArtifact(outputUrl, `${project.bridgeId || project.id}_output.zip`, {
      openAfterSave: false,
    })
  }

  const openPhotosFolder = () => {
    if (publishedPhotosDir) {
      void openLocalPath(publishedPhotosDir)
      return
    }
    void downloadArtifact(photosUrl, `${project.bridgeId || project.id}_fotos_relatorio.zip`, {
      openAfterSave: false,
    })
  }

  return (
    <PageShell width="centered">
      <motion.div
        initial={{ opacity: 0, scale: 0.96 }}
        animate={{ opacity: 1, scale: 1 }}
        transition={{ duration: 0.45 }}
      >
        <div className="mb-6 rounded-xl border border-graphite-200 bg-white p-6 text-center">
          <div className="mx-auto mb-4 flex h-16 w-16 items-center justify-center rounded-full bg-success-bg">
            <CheckCircle2 className="h-8 w-8 text-success" />
          </div>
          <h1 className="text-2xl font-semibold text-graphite-800">Relatório Gerado</h1>
          <p className="mt-2 text-graphite-500">{project.name}</p>
        </div>

        <Card className="mb-6">
          <CardContent className="space-y-4 p-6">
            <InfoRow
              label="Pasta de saída"
              value={publishedDir ?? project.files.outputDir?.path ?? '—'}
              mono
            />
            <InfoRow label="Relatório Word" value={project.reportPath ?? '—'} mono />
            {publishedPhotosDir ? (
              <InfoRow label="Fotos do relatório" value={publishedPhotosDir} mono />
            ) : null}
            <InfoRow
              label="Gerado em"
              value={project.reportGeneratedAt ? formatDate(project.reportGeneratedAt) : '—'}
            />
            <InfoRow label="Páginas" value={String(stats?.pageCount ?? '—')} />
            <InfoRow label="Fotos" value={String(stats?.photoCount ?? '—')} />
            <InfoRow label="Anomalias" value={String(stats?.anomalyCount ?? '—')} />
          </CardContent>
        </Card>

        <p className="mb-4 text-sm text-graphite-500">
          {savedToUserFolder
            ? 'O relatório (.docx) e a pasta fotos_relatorio foram gravados na pasta de saída selecionada no cadastro da obra. As fotos foram renomeadas na ordem do relatório (ex.: 1-IMG_0098.JPG).'
            : 'Selecione uma pasta de saída com caminho completo no cadastro da obra para gravar o relatório e as fotos renomeadas automaticamente.'}
        </p>

        <div className="grid gap-3 sm:grid-cols-2">
          <Button variant="secondary" className="justify-start" onClick={openReport}>
            <ExternalLink className="h-4 w-4" />
            {savedToUserFolder ? 'Abrir relatório' : 'Baixar relatório'}
          </Button>
          <Button variant="secondary" className="justify-start" onClick={openOutputFolder}>
            <FolderOpen className="h-4 w-4" />
            {savedToUserFolder ? 'Abrir pasta de saída' : 'Baixar pasta de saída (ZIP)'}
          </Button>
          <Button variant="secondary" className="justify-start" onClick={openPhotosFolder}>
            <Download className="h-4 w-4" />
            {savedToUserFolder ? 'Abrir fotos do relatório' : 'Baixar fotos (ZIP)'}
          </Button>
          <Button variant="secondary" className="justify-start" disabled title="Em breve">
            <FileText className="h-4 w-4" />
            Exportar PDF
          </Button>
        </div>

        <motion.div className="mt-8 flex flex-wrap gap-3 border-t border-graphite-200 pt-6">
          <Button
            variant="outline"
            onClick={() => projectId && navigate(`/obras/${projectId}/processamento`)}
          >
            <RefreshCw className="h-4 w-4" />
            Gerar novamente
          </Button>
          <Button
            variant="secondary"
            onClick={() => {
              if (!projectId) return
              const id = duplicateProject(projectId)
              navigate(`/obras/${id}`)
            }}
          >
            <Copy className="h-4 w-4" />
            Duplicar obra
          </Button>
          <Button variant="ghost" onClick={() => navigate('/')}>
            <Home className="h-4 w-4" />
            Voltar ao dashboard
          </Button>
        </motion.div>
      </motion.div>
    </PageShell>
  )
}

function InfoRow({
  label,
  value,
  mono,
}: {
  label: string
  value: string
  mono?: boolean
}) {
  return (
    <div className="flex min-w-0 flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
      <span className="shrink-0 text-sm text-graphite-500">{label}</span>
      <span
        className={
          mono
            ? 'break-all font-mono text-xs text-graphite-700 sm:max-w-[65%] sm:text-right'
            : 'text-sm font-medium text-graphite-800 sm:text-right'
        }
      >
        {value}
      </span>
    </div>
  )
}
