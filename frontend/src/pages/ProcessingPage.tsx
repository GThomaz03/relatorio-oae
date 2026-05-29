import { useEffect, useRef } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { CheckCircle2, Circle, Loader2, XCircle } from 'lucide-react'
import { Progress } from '@/components/ui/progress'
import { Button } from '@/components/ui/button'
import { EmptyState, PageHeader, PageShell } from '@/components/layout/PageShell'
import { useProjectStore } from '@/store/project-store'
import { cn } from '@/utils/cn'

export function ProcessingPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const startReportGeneration = useProjectStore((s) => s.startReportGeneration)
  const processingByProject = useProjectStore((s) => s.processingByProject)
  const projects = useProjectStore((s) => s.projects)
  const setActiveProject = useProjectStore((s) => s.setActiveProject)
  const started = useRef(false)

  const project = projects.find((p) => p.id === projectId)
  const processing = projectId ? processingByProject[projectId] : undefined

  useEffect(() => {
    if (projectId) setActiveProject(projectId)
  }, [projectId, setActiveProject])

  useEffect(() => {
    if (!projectId || started.current) return
    started.current = true
    void startReportGeneration(projectId).finally(() => {
      if (projectId && useProjectStore.getState().processingByProject[projectId]?.error) {
        started.current = false
      }
    })
  }, [projectId, startReportGeneration])

  useEffect(() => {
    if (processing?.isComplete && projectId) {
      const timer = setTimeout(() => navigate(`/obras/${projectId}/concluido`), 800)
      return () => clearTimeout(timer)
    }
  }, [processing?.isComplete, projectId, navigate])

  if (!project) {
    return (
      <PageShell width="centered">
        <EmptyState message="Obra não encontrada." />
      </PageShell>
    )
  }

  if (processing?.error) {
    return (
      <PageShell width="centered">
        <PageHeader title="Erro na geração" />
        <p className="mt-4 text-sm text-error">{processing.error}</p>
        <p className="mt-2 text-sm text-graphite-500">
          Verifique se a API está em execução ({`python -m backend.api.server`}) e se os arquivos
          foram selecionados novamente no cadastro.
        </p>
        <Button
          className="mt-6 w-fit"
          variant="secondary"
          onClick={() => projectId && navigate(`/obras/${projectId}`)}
        >
          Voltar ao cadastro
        </Button>
      </PageShell>
    )
  }

  const progress = processing?.progress ?? 0

  return (
    <PageShell width="centered">
      <motion.div
        initial={{ opacity: 0, y: 12 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.4 }}
      >
        <PageHeader title="Gerando Relatório" description={project.name} />

        <div className="mt-8 space-y-3">
          <div className="flex items-center justify-between text-sm">
            <span className="text-graphite-600">Progresso</span>
            <span className="font-medium text-petrol-700">{progress}%</span>
          </div>
          <Progress value={progress} />
        </div>

        <ul className="mt-8 space-y-3">
          {(processing?.steps ?? []).map((step) => (
            <li
              key={step.id}
              className={cn(
                'flex items-center gap-3 rounded-lg border px-4 py-3 transition-colors',
                step.status === 'running' && 'border-petrol-200 bg-petrol-50/50',
                step.status === 'done' && 'border-graphite-200 bg-white',
                step.status === 'pending' && 'border-graphite-100 bg-graphite-50/50 opacity-60',
              )}
            >
              <StepIcon status={step.status} />
              <span className="text-sm font-medium text-graphite-700">{step.label}</span>
            </li>
          ))}
        </ul>

        <div className="mt-8 max-h-48 overflow-y-auto rounded-xl border border-graphite-200 bg-graphite-900 p-4 font-mono text-xs scrollbar-thin">
          <p className="mb-2 text-graphite-500">// logs</p>
          <div className="space-y-1">
            {(processing?.logs ?? []).map((log) => (
              <p
                key={log.id}
                className={cn(
                  log.level === 'ok' && 'text-emerald-400',
                  log.level === 'warn' && 'text-amber-400',
                  log.level === 'error' && 'text-red-400',
                  log.level === 'info' && 'text-graphite-300',
                )}
              >
                [{log.level.toUpperCase()}] {log.message}
              </p>
            ))}
            {(!processing?.logs?.length ||
              processing?.steps?.some((s) => s.status === 'running')) && (
              <p className="animate-pulse text-graphite-500">Processando...</p>
            )}
          </div>
        </div>
      </motion.div>
    </PageShell>
  )
}

function StepIcon({ status }: { status: string }) {
  if (status === 'done') return <CheckCircle2 className="h-5 w-5 text-success" />
  if (status === 'running') return <Loader2 className="h-5 w-5 animate-spin text-petrol-600" />
  if (status === 'error') return <XCircle className="h-5 w-5 text-error" />
  return <Circle className="h-5 w-5 text-graphite-300" />
}
