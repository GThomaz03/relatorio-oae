import { memo, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import {
  AlertTriangle,
  ArrowLeft,
  ArrowRight,
  CheckCircle2,
  ImageOff,
  Save,
  Search,
  Trash2,
  XCircle,
} from 'lucide-react'
import { EmptyState, PageHeader, PageShell } from '@/components/layout/PageShell'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { useContainerHeight } from '@/hooks/useContainerHeight'
import { useSaveDraft } from '@/hooks/use-save-draft'
import type { AnomalyRow } from '@/types/project'
import { resolveMediaUrl } from '@/services/api-client'
import { normalizeAnalysisResult } from '@/services/analysis-service'
import { useProjectStore } from '@/store/project-store'
import { confirmDeleteAnomaly } from '@/utils/confirm-delete-anomaly'
import { cn } from '@/utils/cn'
import { List, type RowComponentProps } from 'react-window'

const TABLE_MIN_WIDTH = 820
const TABLE_COLUMNS =
  'grid grid-cols-[88px_minmax(120px,180px)_minmax(140px,1fr)_minmax(180px,1.6fr)_72px_44px]'

export function ValidationPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const projects = useProjectStore((s) => s.projects)
  const analysisByProject = useProjectStore((s) => s.analysisByProject)
  const updateAnomaly = useProjectStore((s) => s.updateAnomaly)
  const deleteAnomaly = useProjectStore((s) => s.deleteAnomaly)
  const setActiveProject = useProjectStore((s) => s.setActiveProject)

  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [search, setSearch] = useState('')
  const [filter, setFilter] = useState<'all' | 'ok' | 'warning' | 'error'>('all')
  const { saveDraft, savedHint } = useSaveDraft(projectId)
  const listContainerRef = useRef<HTMLDivElement>(null)
  const listHeight = useContainerHeight(listContainerRef, 240)

  const project = projects.find((p) => p.id === projectId)
  const analysis = useMemo(() => {
    const raw = projectId ? analysisByProject[projectId] : undefined
    return raw ? normalizeAnalysisResult(raw) : undefined
  }, [projectId, analysisByProject])

  useEffect(() => {
    if (projectId) setActiveProject(projectId)
  }, [projectId, setActiveProject])

  const filteredAnomalies = useMemo(() => {
    if (!analysis) return []
    return analysis.anomalies.filter((a) => {
      const matchesSearch =
        !search ||
        a.element.toLowerCase().includes(search.toLowerCase()) ||
        a.anomalyType.toLowerCase().includes(search.toLowerCase()) ||
        a.legend.toLowerCase().includes(search.toLowerCase())
      const matchesFilter = filter === 'all' || a.status === filter
      return matchesSearch && matchesFilter
    })
  }, [analysis, search, filter])

  const selected = filteredAnomalies.find((a) => a.id === selectedId) ?? filteredAnomalies[0]

  const handleDeleteAnomaly = (anomaly: AnomalyRow) => {
    if (!projectId || !confirmDeleteAnomaly(anomaly)) return
    deleteAnomaly(projectId, anomaly.id)
    if (selectedId === anomaly.id) {
      const remaining = filteredAnomalies.filter((a) => a.id !== anomaly.id)
      setSelectedId(remaining[0]?.id ?? null)
    }
  }

  if (!project || !analysis) {
    return (
      <PageShell width="flush" fill>
        <EmptyState message="Execute a análise antes de validar os dados." />
      </PageShell>
    )
  }

  const { summary } = analysis

  return (
    <PageShell width="flush" fill className="pb-5">
      <PageHeader
        title="Validação dos Dados"
        description={project.name}
        actions={
          <>
            <Button variant="outline" onClick={() => navigate(`/obras/${projectId}`)}>
              <ArrowLeft className="h-4 w-4" />
              Voltar
            </Button>
            <Button variant="secondary" onClick={() => saveDraft()}>
              <Save className="h-4 w-4" />
              Salvar rascunho
              {savedHint ? <span className="ml-2 text-xs text-success">Salvo!</span> : null}
            </Button>
            <Button onClick={() => navigate(`/obras/${projectId}/fotos`)}>
              Organizar fotos
              <ArrowRight className="h-4 w-4" />
            </Button>
          </>
        }
      />

      <div className="mt-4 grid gap-3 sm:grid-cols-2 xl:grid-cols-5">
        <SummaryPill label="Anomalias" value={summary.anomalyCount} />
        <SummaryPill label="Imagens encontradas" value={summary.imagesFound} />
        <SummaryPill label="Imagens faltantes" value={summary.imagesMissing} variant="warning" />
        <SummaryPill label="Inconsistências" value={summary.inconsistencies} variant="warning" />
        <SummaryPill label="Elementos" value={summary.structuralElements.length} />
      </div>

      <div className="mt-4 flex min-h-0 flex-1 flex-col overflow-hidden rounded-xl border border-graphite-200 bg-white lg:min-h-0 lg:flex-row">
        <div className="flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
          <div className="flex flex-wrap items-center gap-2 border-b border-graphite-200 px-3 py-3 sm:gap-3 sm:px-4">
            <div className="relative min-w-[180px] flex-1">
              <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-graphite-400" />
              <Input
                className="pl-9"
                placeholder="Pesquisar anomalias..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
              />
            </div>
            <div className="flex flex-wrap gap-1.5">
              <FilterButton active={filter === 'all'} onClick={() => setFilter('all')}>
                Todas
              </FilterButton>
              <FilterButton active={filter === 'ok'} onClick={() => setFilter('ok')}>
                OK
              </FilterButton>
              <FilterButton active={filter === 'warning'} onClick={() => setFilter('warning')}>
                Avisos
              </FilterButton>
              <FilterButton active={filter === 'error'} onClick={() => setFilter('error')}>
                Erros
              </FilterButton>
            </div>
          </div>

          <div className="scrollbar-thin flex min-h-0 min-w-0 flex-1 flex-col overflow-hidden">
            <div
              className="flex min-h-0 flex-1 flex-col overflow-hidden"
              style={{ minWidth: TABLE_MIN_WIDTH }}
            >
              <div
                className={cn(
                  TABLE_COLUMNS,
                  'sticky top-0 z-10 border-b border-graphite-100 bg-graphite-50 px-2 py-2.5 text-xs font-medium uppercase tracking-wide text-graphite-500',
                )}
              >
                <div className="px-2">Foto</div>
                <div className="px-2">Elemento</div>
                <div className="px-2">Anomalia</div>
                <div className="px-2">Legenda</div>
                <div className="px-2">Status</div>
                <div className="px-1" aria-hidden />
              </div>

              <div ref={listContainerRef} className="min-h-0 flex-1 overflow-hidden">
                {filteredAnomalies.length === 0 ? (
                  <p className="px-4 py-8 text-center text-sm text-graphite-500">
                    Nenhuma anomalia corresponde aos filtros.
                  </p>
                ) : (
                  <List
                    rowCount={filteredAnomalies.length}
                    rowHeight={88}
                    style={{ height: Math.max(listHeight, 240), width: '100%' }}
                    rowComponent={VirtualAnomalyRow}
                    rowProps={{
                      anomalies: filteredAnomalies,
                      selectedId: selected?.id ?? null,
                      onSelect: setSelectedId,
                      onUpdateLegend: (anomalyId: string, legend: string) =>
                        projectId && updateAnomaly(projectId, anomalyId, { legend }),
                      onDelete: handleDeleteAnomaly,
                    }}
                  />
                )}
              </div>
            </div>
          </div>
        </div>

        <aside className="shrink-0 border-t border-graphite-200 bg-graphite-50/50 p-4 lg:w-[min(340px,100%)] lg:border-l lg:border-t-0 lg:bg-white lg:p-5">
          {selected ? (
            <ImagePreview anomaly={selected} onDelete={() => handleDeleteAnomaly(selected)} />
          ) : (
            <p className="text-sm text-graphite-500">
              Selecione uma linha para visualizar a foto.
            </p>
          )}
        </aside>
      </div>
    </PageShell>
  )
}

function SummaryPill({
  label,
  value,
  variant,
}: {
  label: string
  value: number
  variant?: 'warning'
}) {
  return (
    <Card>
      <CardContent className="p-4">
        <p className="text-xs text-graphite-500">{label}</p>
        <p
          className={cn(
            'mt-1 text-xl font-semibold tabular-nums',
            variant === 'warning' && value > 0 ? 'text-warning' : 'text-graphite-800',
          )}
        >
          {value}
        </p>
      </CardContent>
    </Card>
  )
}

function FilterButton({
  active,
  onClick,
  children,
}: {
  active: boolean
  onClick: () => void
  children: React.ReactNode
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        'cursor-pointer rounded-lg px-3 py-1.5 text-xs font-medium transition-colors duration-200 motion-reduce:transition-none',
        active
          ? 'bg-petrol-100 text-petrol-800'
          : 'bg-graphite-100 text-graphite-600 hover:bg-graphite-200',
      )}
    >
      {children}
    </button>
  )
}

const AnomalyTableRow = memo(function AnomalyTableRow({
  anomaly,
  selected,
  onSelect,
  onUpdateLegend,
  onDelete,
}: {
  anomaly: AnomalyRow
  selected: boolean
  onSelect: () => void
  onUpdateLegend: (value: string) => void
  onDelete: () => void
}) {
  return (
    <div
      role="button"
      tabIndex={0}
      className={cn(
        TABLE_COLUMNS,
        'min-h-[88px] items-center cursor-pointer border-b border-graphite-100 px-2 transition-colors hover:bg-petrol-50/40 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-inset focus-visible:ring-petrol-400/50',
        selected && 'bg-petrol-50/60',
      )}
      onClick={onSelect}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          onSelect()
        }
      }}
    >
      <div className="px-2 py-3">
        {anomaly.thumbnailUrl ? (
          <img
            src={resolveMediaUrl(anomaly.thumbnailUrl)}
            alt=""
            loading="lazy"
            decoding="async"
            className="h-10 w-14 rounded object-cover"
          />
        ) : (
          <div className="flex h-10 w-14 items-center justify-center rounded bg-graphite-100">
            <ImageOff className="h-4 w-4 text-graphite-400" />
          </div>
        )}
      </div>
      <div className="truncate px-2 py-3 text-sm font-medium text-graphite-800">
        {anomaly.element}
      </div>
      <div className="truncate px-2 py-3 text-sm text-graphite-600">{anomaly.anomalyType}</div>
      <div className="px-2 py-2" onClick={(e) => e.stopPropagation()}>
        <input
          aria-label="Legenda da anomalia"
          className="w-full min-w-0 rounded border border-transparent bg-transparent px-1 py-0.5 text-sm text-graphite-700 hover:border-graphite-200 focus:border-petrol-300 focus:outline-none focus-visible:ring-2 focus-visible:ring-petrol-400/30"
          value={anomaly.legend}
          onChange={(e) => onUpdateLegend(e.target.value)}
        />
      </div>
      <div className="px-2 py-3">
        <StatusIcon status={anomaly.status} />
      </div>
      <div className="flex items-center justify-center px-1 py-3" onClick={(e) => e.stopPropagation()}>
        <button
          type="button"
          title="Excluir anomalia"
          aria-label="Excluir anomalia"
          className="inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-md border border-graphite-200 text-graphite-500 transition-colors hover:border-error/40 hover:bg-error/10 hover:text-error"
          onClick={onDelete}
        >
          <Trash2 className="h-4 w-4" />
        </button>
      </div>
    </div>
  )
})

type VirtualData = {
  anomalies: AnomalyRow[]
  selectedId: string | null
  onSelect: (id: string) => void
  onUpdateLegend: (id: string, legend: string) => void
  onDelete: (anomaly: AnomalyRow) => void
}

function VirtualAnomalyRow({ index, style, ...data }: RowComponentProps<VirtualData>) {
  const anomaly = data.anomalies[index]!
  return (
    <div style={style}>
      <AnomalyTableRow
        anomaly={anomaly}
        selected={data.selectedId === anomaly.id}
        onSelect={() => data.onSelect(anomaly.id)}
        onUpdateLegend={(legend) => data.onUpdateLegend(anomaly.id, legend)}
        onDelete={() => data.onDelete(anomaly)}
      />
    </div>
  )
}

function StatusIcon({ status }: { status: AnomalyRow['status'] }) {
  if (status === 'ok') return <CheckCircle2 className="h-4 w-4 text-success" aria-label="OK" />
  if (status === 'warning')
    return <AlertTriangle className="h-4 w-4 text-warning" aria-label="Aviso" />
  if (status === 'error') return <XCircle className="h-4 w-4 text-error" aria-label="Erro" />
  return <Badge variant="default">Pendente</Badge>
}

function ImagePreview({ anomaly, onDelete }: { anomaly: AnomalyRow; onDelete: () => void }) {
  return (
    <div className="space-y-4">
      <div className="overflow-hidden rounded-lg border border-graphite-200 bg-graphite-50">
        {anomaly.thumbnailUrl ? (
          <img
            src={resolveMediaUrl(anomaly.thumbnailUrl)}
            alt={anomaly.imagePath ?? 'Pré-visualização'}
            loading="lazy"
            decoding="async"
            className="aspect-[4/3] w-full object-cover"
          />
        ) : (
          <div className="flex aspect-[4/3] items-center justify-center">
            <ImageOff className="h-8 w-8 text-graphite-400" />
          </div>
        )}
      </div>
      <div className="space-y-2 text-sm">
        <PreviewField label="Arquivo" value={anomaly.imagePath ?? '—'} />
        <PreviewField label="Nº foto" value={anomaly.photoToken} />
        <PreviewField label="Elemento" value={anomaly.element} />
        <PreviewField label="Anomalia" value={anomaly.anomalyType} />
        <PreviewField label="Face" value={anomaly.face} />
      </div>
      <Button variant="destructive" className="w-full" onClick={onDelete}>
        <Trash2 className="h-4 w-4" />
        Excluir anomalia
      </Button>
    </div>
  )
}

function PreviewField({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-0">
      <p className="text-xs font-medium uppercase tracking-wide text-graphite-400">{label}</p>
      <p className="mt-0.5 break-words text-graphite-700">{value}</p>
    </div>
  )
}
