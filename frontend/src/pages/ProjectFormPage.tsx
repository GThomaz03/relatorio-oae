import { useEffect } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { motion } from 'framer-motion'
import { ArrowRight, Loader2, Save } from 'lucide-react'
import { FileUploadCard } from '@/components/FileUploadCard'
import { EmptyState, PageHeader, PageShell } from '@/components/layout/PageShell'
import { StatusBadge } from '@/components/StatusBadge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input, Label, Select, Textarea } from '@/components/ui/input'
import { SENTIDO_OPTIONS, useProjectStore } from '@/store/project-store'
import { useFileStagingStore } from '@/store/file-staging-store'
import { useSaveDraft } from '@/hooks/use-save-draft'
import { buildBridgeId, formatRodoviaHint } from '@/utils/bridge-id'

export function ProjectFormPage() {
  const { projectId } = useParams<{ projectId: string }>()
  const navigate = useNavigate()
  const projects = useProjectStore((s) => s.projects)
  const updateProject = useProjectStore((s) => s.updateProject)
  const updateProjectFiles = useProjectStore((s) => s.updateProjectFiles)
  const startAnalysis = useProjectStore((s) => s.startAnalysis)
  const setActiveProject = useProjectStore((s) => s.setActiveProject)
  const setExcel = useFileStagingStore((s) => s.setExcel)
  const setImages = useFileStagingStore((s) => s.setImages)
  const setDesktopPaths = useFileStagingStore((s) => s.setDesktopPaths)
  const isAnalyzing = useProjectStore((s) => s.isAnalyzing)

  const project = projects.find((p) => p.id === projectId)
  const { saveDraft, savedHint } = useSaveDraft(projectId)

  useEffect(() => {
    if (projectId) setActiveProject(projectId)
  }, [projectId, setActiveProject])

  if (!project) {
    return (
      <PageShell width="wide">
        <EmptyState message="Obra não encontrada." />
      </PageShell>
    )
  }

  const canAnalyze = Boolean(
    project.name.trim() &&
      project.rodovia.trim() &&
      project.km.trim() &&
      project.bridgeId.trim() &&
      project.files.excel &&
      project.files.photosDir &&
      project.files.outputDir,
  )

  const handleStartAnalysis = async () => {
    if (!projectId || !canAnalyze) return
    try {
      await startAnalysis(projectId)
      navigate(`/obras/${projectId}/validacao`)
    } catch (error) {
      const message = error instanceof Error ? error.message : 'Erro ao analisar arquivos'
      window.alert(
        `${message}\n\nCertifique-se de que a API está rodando (python -m backend.api.server) e de ter selecionado novamente a planilha e as fotos.`,
      )
    }
  }

  const applyRodovia = (rodovia: string) => {
    const prefix = project.bridgePrefix ?? 'E'
    updateProject(project.id, {
      rodovia,
      bridgePrefix: prefix,
      bridgeId: buildBridgeId(prefix, rodovia),
    })
  }

  const applyBridgePrefix = (bridgePrefix: string) => {
    const letter = bridgePrefix.toUpperCase().replace(/[^A-Z]/g, '').slice(0, 1) || 'E'
    updateProject(project.id, {
      bridgePrefix: letter,
      bridgeId: buildBridgeId(letter, project.rodovia),
    })
  }

  return (
    <PageShell width="wide">
      <motion.div
        initial={{ opacity: 0, y: 8 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
      >
        <PageHeader
          title={project.name || 'Nova Obra'}
          description="Cadastro e configuração do projeto"
          actions={<StatusBadge status={project.status} className="text-xs" />}
        />

        <Card className="mt-6 mb-6">
          <CardHeader>
            <CardTitle>Informações básicas</CardTitle>
          </CardHeader>
          <CardContent className="grid gap-5 sm:grid-cols-2">
            <div className="space-y-2 sm:col-span-2">
              <Label required>Nome da obra</Label>
              <Input
                value={project.name}
                placeholder="Ex.: Ponte sobre o Rio Tietê"
                onChange={(e) => updateProject(project.id, { name: e.target.value })}
              />
            </div>
            <div className="space-y-2">
              <Label required>Rodovia</Label>
              <Input
                value={project.rodovia}
                placeholder={formatRodoviaHint()}
                onChange={(e) => applyRodovia(e.target.value)}
              />
              <p className="text-xs text-graphite-400">
                Número da rodovia: BR-116, 116-RJ, RJ-116, SP-270…
              </p>
            </div>
            <div className="space-y-2">
              <Label required>KM</Label>
              <Input
                value={project.km}
                placeholder="Ex.: 233 ou 244+710"
                onChange={(e) =>
                  updateProject(project.id, {
                    km: e.target.value,
                    photoKm: e.target.value.replace('+', ''),
                  })
                }
              />
            </div>
            <div className="space-y-2">
              <Label required>Prefixo RSP</Label>
              <Input
                value={project.bridgePrefix ?? 'E'}
                placeholder="E"
                maxLength={1}
                onChange={(e) => applyBridgePrefix(e.target.value)}
              />
              <p className="text-xs text-graphite-400">
                Letra de identificação antes do número da rodovia
              </p>
            </div>
            <div className="space-y-2">
              <Label>Identificador da obra</Label>
              <Input
                value={project.bridgeId}
                readOnly
                className="bg-graphite-50 text-graphite-700"
                placeholder="Calculado automaticamente (ex.: E116)"
              />
              <p className="text-xs text-graphite-400">
                Usado nos códigos fotográficos RSP (ex.: {project.bridgeId || 'E116'}K244710F001S)
              </p>
            </div>
            <div className="space-y-2">
              <Label required>Sentido</Label>
              <Select
                value={project.sentido}
                onChange={(e) =>
                  updateProject(project.id, {
                    sentido: e.target.value as typeof project.sentido,
                  })
                }
              >
                {SENTIDO_OPTIONS.map((s) => (
                  <option key={s} value={s}>
                    {s}
                  </option>
                ))}
              </Select>
            </div>
            <div className="space-y-2 sm:col-span-2">
              <Label>Observações gerais</Label>
              <Textarea
                value={project.observacoes}
                placeholder="Notas técnicas ou observações sobre a inspeção..."
                onChange={(e) => updateProject(project.id, { observacoes: e.target.value })}
              />
            </div>
          </CardContent>
        </Card>

        <section className="mb-6 rounded-xl border border-graphite-200 bg-white p-4 sm:p-5">
          <h2 className="mb-4 text-lg font-semibold text-graphite-800">Arquivos do Projeto</h2>
          <p className="mb-4 text-sm text-graphite-500">
            O template Word padrão RSP é utilizado automaticamente. Para baixar ou enviar uma
            versão editada, acesse <strong>Template Word</strong> na barra lateral.
          </p>
          <div className="grid gap-4 md:grid-cols-2">
            <FileUploadCard
              title="Planilha Excel"
              description="Planilha de inspeção com anomalias (.xlsx)"
              icon="excel"
              accept=".xlsx,.xls,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
              buttonLabel="Selecionar Planilha"
              fileRef={project.files.excel}
              onSelect={(fileRef) => updateProjectFiles(project.id, { excel: fileRef })}
              onRawFiles={(files) => {
                const file = Array.isArray(files) ? files[0] : files
                if (file) setExcel(project.id, file)
              }}
              onDesktopPaths={(paths) => {
                if (paths.excelPath) {
                  setDesktopPaths(project.id, { excelPath: paths.excelPath })
                }
              }}
            />
            <FileUploadCard
              title="Pasta de Fotos"
              description="Imagens de inspeção organizadas por pasta"
              icon="photos"
              directory
              folderPurpose="images"
              buttonLabel="Selecionar Pasta de Fotos"
              fileRef={project.files.photosDir}
              extraInfo={
                project.files.photoCount
                  ? `${project.files.photoCount} imagens encontradas`
                  : undefined
              }
              onSelect={(fileRef, extra) =>
                updateProjectFiles(project.id, {
                  photosDir: fileRef,
                  photoCount: extra?.photoCount,
                })
              }
              onRawFiles={(files) => {
                const list = Array.isArray(files) ? files : [files]
                setImages(project.id, list)
              }}
              onDesktopPaths={(paths) => {
                if (paths.imagesDirPath) {
                  setDesktopPaths(project.id, { imagesDirPath: paths.imagesDirPath })
                }
              }}
            />
            <FileUploadCard
              title="Pasta de Saída"
              description="Destino do relatório gerado"
              icon="output"
              directory
              folderPurpose="output"
              buttonLabel="Selecionar Pasta de Saída"
              fileRef={project.files.outputDir}
              onSelect={(fileRef) => updateProjectFiles(project.id, { outputDir: fileRef })}
              onDesktopPaths={(paths) => {
                if (paths.outputDirPath) {
                  setDesktopPaths(project.id, { outputDirPath: paths.outputDirPath })
                  updateProjectFiles(project.id, {
                    outputDir: {
                      name:
                        paths.outputDirPath.split(/[/\\]/).filter(Boolean).pop() ??
                        paths.outputDirPath,
                      path: paths.outputDirPath,
                    },
                  })
                }
              }}
            />
          </div>
        </section>

        <div className="flex flex-wrap items-center justify-between gap-3 border-t border-graphite-200 pt-6">
          <Button variant="secondary" onClick={() => saveDraft()}>
            <Save className="h-4 w-4" />
            Salvar rascunho
            {savedHint ? <span className="ml-2 text-xs text-success">Salvo!</span> : null}
          </Button>
          <Button disabled={!canAnalyze || isAnalyzing} onClick={handleStartAnalysis}>
            {isAnalyzing ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                Analisando...
              </>
            ) : (
              <>
                Iniciar análise
                <ArrowRight className="h-4 w-4" />
              </>
            )}
          </Button>
        </div>
      </motion.div>
    </PageShell>
  )
}
