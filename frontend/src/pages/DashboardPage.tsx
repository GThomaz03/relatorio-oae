import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import {
  AlertTriangle,
  Building2,
  CheckCircle2,
  FileCheck,
  ImageIcon,
  Plus,
} from 'lucide-react'
import { PageHeader, PageShell } from '@/components/layout/PageShell'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { useProjectStore } from '@/store/project-store'

const fadeIn = {
  initial: { opacity: 0, y: 12 },
  animate: { opacity: 1, y: 0 },
  transition: { duration: 0.35 },
}

export function DashboardPage() {
  const navigate = useNavigate()
  const projects = useProjectStore((s) => s.projects)
  const createProject = useProjectStore((s) => s.createProject)
  const analysisByProject = useProjectStore((s) => s.analysisByProject)

  const generated = projects.filter((p) => p.status === 'relatorio_gerado').length
  const pending = projects.filter(
    (p) => p.status !== 'relatorio_gerado' && p.status !== 'erro',
  ).length
  const totalPhotos = Object.values(analysisByProject).reduce(
    (acc, a) => acc + a.photos.length,
    0,
  )

  const handleNewProject = () => {
    const id = createProject()
    navigate(`/obras/${id}`)
  }

  return (
    <PageShell width="default">
      <motion.div {...fadeIn}>
        {projects.length === 0 ? (
          <Card className="mx-auto max-w-xl text-center">
            <CardContent className="p-8 sm:p-10">
              <div className="mx-auto mb-6 flex h-16 w-16 items-center justify-center rounded-2xl bg-petrol-100">
                <Building2 className="h-8 w-8 text-petrol-700" />
              </div>
              <h1 className="text-2xl font-semibold text-graphite-800">Nenhuma obra selecionada</h1>
              <p className="mt-2 text-graphite-500">
                Selecione uma obra na barra lateral ou crie uma nova para começar.
              </p>
              <Button className="mt-6" onClick={handleNewProject}>
                <Plus className="h-4 w-4" />
                Nova Obra
              </Button>
            </CardContent>
          </Card>
        ) : (
          <>
            <PageHeader
              title="Dashboard"
              description="Visão geral da operação e status das inspeções"
            />

            <div className="mt-6 grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
              <SummaryCard
                title="Total de obras"
                value={projects.length}
                icon={<Building2 className="h-5 w-5 text-petrol-600" />}
              />
              <SummaryCard
                title="Relatórios gerados"
                value={generated}
                icon={<CheckCircle2 className="h-5 w-5 text-success" />}
              />
              <SummaryCard
                title="Pendências"
                value={pending}
                icon={<AlertTriangle className="h-5 w-5 text-warning" />}
              />
              <SummaryCard
                title="Fotos em análise"
                value={totalPhotos}
                icon={<ImageIcon className="h-5 w-5 text-petrol-600" />}
              />
            </div>

            <Card className="mt-6">
              <CardHeader>
                <CardTitle className="text-base">Acesso rápido</CardTitle>
              </CardHeader>
              <CardContent className="flex flex-wrap gap-3">
                <Button onClick={handleNewProject}>
                  <Plus className="h-4 w-4" />
                  Nova Obra
                </Button>
                <Button
                  variant="secondary"
                  onClick={() => {
                    const latest = projects[0]
                    if (latest) navigate(`/obras/${latest.id}`)
                  }}
                >
                  <FileCheck className="h-4 w-4" />
                  Continuar última obra
                </Button>
              </CardContent>
            </Card>
          </>
        )}
      </motion.div>
    </PageShell>
  )
}

function SummaryCard({
  title,
  value,
  icon,
}: {
  title: string
  value: number
  icon: React.ReactNode
}) {
  return (
    <Card>
      <CardContent className="flex items-center gap-4 p-5">
        <div className="flex h-11 w-11 shrink-0 items-center justify-center rounded-lg bg-graphite-50">
          {icon}
        </div>
        <div className="min-w-0">
          <p className="text-2xl font-semibold tabular-nums text-graphite-800">{value}</p>
          <p className="text-xs text-graphite-500">{title}</p>
        </div>
      </CardContent>
    </Card>
  )
}
