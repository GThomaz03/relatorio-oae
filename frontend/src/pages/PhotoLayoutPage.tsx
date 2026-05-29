import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion, Reorder } from 'framer-motion'
import { ArrowLeft, ArrowRight, Copy, GripVertical, Save, Trash2 } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import { EmptyState, PageHeader, PageShell } from '@/components/layout/PageShell'
import { resolveMediaUrl } from '@/services/api-client'
import { preloadAround } from '@/services/image-cache'
import type { AnomalyRow, PhotoEntry } from '@/types/project'
import { useSaveDraft } from '@/hooks/use-save-draft'
import { useProjectStore } from '@/store/project-store'
import { confirmDeleteAnomaly } from '@/utils/confirm-delete-anomaly'

const PHOTOS_PER_PAGE = 2

export function PhotoLayoutPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const analysisByProject = useProjectStore((s) => s.analysisByProject)
  const reorderPhotos = useProjectStore((s) => s.reorderPhotos)
  const duplicatePhotoAt = useProjectStore((s) => s.duplicatePhotoAt)
  const deleteAnomaly = useProjectStore((s) => s.deleteAnomaly)
  const saveProjectDraft = useProjectStore((s) => s.saveProjectDraft)
  const updatePhotoLegend = useProjectStore((s) => s.updatePhotoLegend)
  const setActiveProject = useProjectStore((s) => s.setActiveProject)
  const projects = useProjectStore((s) => s.projects)
  const updateAnomaly = useProjectStore((s) => s.updateAnomaly)

  const project = projects.find((p) => p.id === projectId)
  const analysis = projectId ? analysisByProject[projectId] : undefined
  const [photos, setPhotos] = useState<PhotoEntry[]>([])
  const [invalidPhotoByAnomaly, setInvalidPhotoByAnomaly] = useState<Record<string, boolean>>({})
  const { saveDraft, savedHint } = useSaveDraft(projectId)

  useEffect(() => {
    if (projectId) setActiveProject(projectId)
  }, [projectId, setActiveProject])

  useEffect(() => {
    if (analysis?.photos) setPhotos(analysis.photos)
  }, [analysis?.photos])

  if (!project || !analysis) {
    return (
      <PageShell width="narrow">
        <EmptyState message="Dados de análise não disponíveis." />
      </PageShell>
    )
  }

  const pages: PhotoEntry[][] = []
  for (let i = 0; i < photos.length; i += PHOTOS_PER_PAGE) {
    pages.push(photos.slice(i, i + PHOTOS_PER_PAGE))
  }

  const handleReorder = (reordered: PhotoEntry[]) => {
    setPhotos(reordered)
    if (projectId) reorderPhotos(projectId, reordered.map((p) => p.id))
  }

  const anomalyById = new Map(analysis.anomalies.map((a) => [a.id, a]))
  const anomalyByRow = new Map(
    analysis.anomalies
      .filter((a) => typeof a.rowIndex === 'number')
      .map((a) => [a.rowIndex as number, a]),
  )

  const handleDeleteAnomaly = (anomaly: AnomalyRow) => {
    if (!projectId || !confirmDeleteAnomaly(anomaly)) return
    deleteAnomaly(projectId, anomaly.id)
    setInvalidPhotoByAnomaly((prev) => {
      const { [anomaly.id]: _removed, ...rest } = prev
      return rest
    })
  }

  const applySelectedPhoto = (
    anomaly: AnomalyRow,
    photoId: string,
    nextPhotoNumber: string,
  ) => {
    const options = anomaly.availableImages ?? []
    const selected = options.find((opt) => opt.photoNumber === nextPhotoNumber)
    if (!selected || !projectId) return
    setInvalidPhotoByAnomaly((prev) => ({ ...prev, [anomaly.id]: false }))

    updateAnomaly(projectId, anomaly.id, {
      selectedPhotoNumber: selected.photoNumber,
      imagePath: selected.imagePath,
      thumbnailUrl: selected.thumbnailUrl,
    })
    setPhotos((prev) =>
      prev.map((p) =>
        p.id === photoId
          ? {
              ...p,
              imagePath: selected.imagePath,
              thumbnailUrl: selected.thumbnailUrl,
            }
          : p,
      ),
    )
    const idx = options.findIndex((opt) => opt.photoNumber === selected.photoNumber)
    preloadAround([
      options[idx - 1]?.thumbnailUrl,
      options[idx + 1]?.thumbnailUrl,
      selected.thumbnailUrl,
    ])
  }

  return (
    <PageShell width="narrow">
      <PageHeader
        title="Relatório Fotográfico"
        description="Valide ordem, legendas e paginação (2 fotos por página)"
        actions={
          <>
            <Button variant="outline" onClick={() => navigate(`/obras/${projectId}/validacao`)}>
              <ArrowLeft className="h-4 w-4" />
              Voltar
            </Button>
            <Button variant="secondary" onClick={() => saveDraft({ photos })}>
              <Save className="h-4 w-4" />
              Salvar rascunho
              {savedHint ? <span className="ml-2 text-xs text-success">Salvo!</span> : null}
            </Button>
            <Button
              onClick={() => {
                if (projectId) saveProjectDraft(projectId, { photos })
                navigate(`/obras/${projectId}/processamento`)
              }}
            >
              Gerar Relatório
              <ArrowRight className="h-4 w-4" />
            </Button>
          </>
        }
      />

      <Reorder.Group axis="y" values={photos} onReorder={handleReorder} className="mt-6 space-y-6">
        {pages.map((pagePhotos, pageIndex) => (
          <motion.div
            key={`page-${pageIndex}`}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: pageIndex * 0.05 }}
          >
            <Card className="overflow-hidden">
              <div className="border-b border-graphite-100 bg-graphite-50 px-4 py-2">
                <p className="text-xs font-medium uppercase tracking-wide text-graphite-500">
                  Página {pageIndex + 1}
                </p>
              </div>
              <CardContent className="space-y-0 p-0">
                {pagePhotos.map((photo, slotIndex) => {
                  const anomaly =
                    (photo.anomalyId ? anomalyById.get(photo.anomalyId) : undefined) ??
                    (typeof photo.anomalyRowIndex === 'number'
                      ? anomalyByRow.get(photo.anomalyRowIndex)
                      : undefined) ??
                    anomalyById.get(`anomaly-${photo.sequenceIndex}`)
                  const options = anomaly?.availableImages ?? []
                  const currentPhotoNumber = anomaly?.selectedPhotoNumber ?? options[0]?.photoNumber
                  const currentIndex = options.findIndex((opt) => opt.photoNumber === currentPhotoNumber)
                  const canPrev = currentIndex > 0
                  const canNext = currentIndex >= 0 && currentIndex < options.length - 1

                  return (
                  <Reorder.Item
                    key={photo.id}
                    value={photo}
                    className="border-b border-graphite-100 last:border-b-0"
                  >
                    <div className="p-5">
                      {slotIndex === 0 && pageIndex > 0 ? (
                        <div className="mb-4 h-4" aria-hidden />
                      ) : slotIndex === 0 && pageIndex === 0 ? (
                        <div className="mb-4 h-4" aria-hidden />
                      ) : slotIndex === 1 ? (
                        <div className="mb-4 h-8 border-t border-dashed border-graphite-200 pt-4" />
                      ) : null}

                      <div className="flex gap-3">
                        <GripVertical className="mt-2 h-4 w-4 shrink-0 cursor-grab text-graphite-400" />
                        <div className="flex-1 space-y-3">
                          <div className="mx-auto max-w-md overflow-hidden rounded-lg border border-graphite-200">
                            <img
                              src={resolveMediaUrl(photo.thumbnailUrl) ?? ''}
                              alt={photo.code}
                              loading="lazy"
                              decoding="async"
                              className="aspect-[4/3] w-full object-cover"
                            />
                          </div>
                          <p className="text-center text-xs font-medium text-graphite-500">
                            {photo.code}
                          </p>
                          <p className="text-center text-xs text-graphite-500">
                            Foto selecionada: {anomaly?.selectedPhotoNumber ?? '—'} · Arquivo:{' '}
                            {photo.imagePath}
                          </p>
                          <textarea
                            className="w-full rounded-lg border border-graphite-200 px-3 py-2 text-sm text-graphite-700 focus:border-petrol-400 focus:outline-none focus:ring-2 focus:ring-petrol-500/20"
                            rows={2}
                            value={photo.legend}
                            onChange={(e) => {
                              const legend = e.target.value
                              setPhotos((prev) =>
                                prev.map((p) => (p.id === photo.id ? { ...p, legend } : p)),
                              )
                              if (projectId) updatePhotoLegend(projectId, photo.id, legend)
                            }}
                          />

                          {anomaly ? (
                            <div className="space-y-2 rounded-lg border border-graphite-200 bg-graphite-50 p-3">
                              <p className="text-xs text-graphite-600">
                                {anomaly.rangeLabel ?? `Fotos ${anomaly.rangeStart} a ${anomaly.rangeEnd}`}
                              </p>
                              <div className="flex items-center gap-2">
                                <button
                                  type="button"
                                  className="inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-md border border-graphite-200 bg-white text-graphite-700 transition-colors hover:bg-graphite-50 disabled:cursor-not-allowed disabled:opacity-40"
                                  disabled={!canPrev}
                                  onClick={() =>
                                    canPrev &&
                                    applySelectedPhoto(anomaly, photo.id, options[currentIndex - 1]!.photoNumber)
                                  }
                                >
                                  <ArrowLeft className="h-4 w-4" />
                                </button>
                                <input
                                  type="number"
                                  value={currentPhotoNumber ?? ''}
                                  onChange={(e) => {
                                    const typed = e.target.value
                                    const exists = options.some((opt) => opt.photoNumber === typed)
                                    if (exists) {
                                      applySelectedPhoto(anomaly, photo.id, typed)
                                    } else {
                                      setInvalidPhotoByAnomaly((prev) => ({
                                        ...prev,
                                        [anomaly.id]: true,
                                      }))
                                    }
                                  }}
                                  className={`h-8 w-24 rounded-md border bg-white px-2 text-sm ${
                                    invalidPhotoByAnomaly[anomaly.id]
                                      ? 'border-error text-error'
                                      : 'border-graphite-200'
                                  }`}
                                />
                                <button
                                  type="button"
                                  className="inline-flex h-8 w-8 cursor-pointer items-center justify-center rounded-md border border-graphite-200 bg-white text-graphite-700 transition-colors hover:bg-graphite-50 disabled:cursor-not-allowed disabled:opacity-40"
                                  disabled={!canNext}
                                  onClick={() =>
                                    canNext &&
                                    applySelectedPhoto(anomaly, photo.id, options[currentIndex + 1]!.photoNumber)
                                  }
                                >
                                  <ArrowRight className="h-4 w-4" />
                                </button>
                                <button
                                  type="button"
                                  title="Duplicar anomalia abaixo"
                                  className="ml-auto inline-flex h-8 items-center gap-1 rounded-md border border-petrol-200 bg-petrol-50 px-2 text-xs font-medium text-petrol-800 transition-colors hover:bg-petrol-100"
                                  onClick={() => projectId && duplicatePhotoAt(projectId, photo.id)}
                                >
                                  <Copy className="h-3.5 w-3.5" />
                                  Duplicar
                                </button>
                                <button
                                  type="button"
                                  title="Excluir anomalia"
                                  className="inline-flex h-8 items-center gap-1 rounded-md border border-error/30 bg-error/5 px-2 text-xs font-medium text-error transition-colors hover:bg-error/10"
                                  onClick={() => handleDeleteAnomaly(anomaly)}
                                >
                                  <Trash2 className="h-3.5 w-3.5" />
                                  Excluir
                                </button>
                              </div>
                              {invalidPhotoByAnomaly[anomaly.id] ? (
                                <p className="text-xs text-error">
                                  Foto fora do range permitido para esta anomalia.
                                </p>
                              ) : null}
                            </div>
                          ) : null}
                        </div>
                      </div>
                    </div>
                  </Reorder.Item>
                  )
                })}
                {pagePhotos.length === PHOTOS_PER_PAGE && (
                  <div className="border-t border-dashed border-petrol-200 bg-petrol-50/30 px-4 py-2 text-center">
                    <p className="text-[11px] font-medium uppercase tracking-wide text-petrol-600">
                      Quebra de página
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>
          </motion.div>
        ))}
      </Reorder.Group>
    </PageShell>
  )
}
