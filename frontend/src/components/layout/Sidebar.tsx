import { useEffect } from 'react'
import { useNavigate, useLocation } from 'react-router-dom'
import { FileText, Plus, SlidersHorizontal, Trash2, X } from 'lucide-react'
import { Logo } from '@/components/Logo'
import { StatusBadge } from '@/components/StatusBadge'
import { Button } from '@/components/ui/button'
import { useProjectStore } from '@/store/project-store'
import { cn } from '@/utils/cn'

interface SidebarProps {
  mobileOpen?: boolean
  onMobileClose?: () => void
}

export function Sidebar({ mobileOpen = false, onMobileClose }: SidebarProps) {
  const navigate = useNavigate()
  const location = useLocation()
  const projects = useProjectStore((s) => s.projects)
  const activeProjectId = useProjectStore((s) => s.activeProjectId)
  const createProject = useProjectStore((s) => s.createProject)
  const setActiveProject = useProjectStore((s) => s.setActiveProject)
  const deleteProject = useProjectStore((s) => s.deleteProject)

  useEffect(() => {
    onMobileClose?.()
  }, [location.pathname, onMobileClose])

  const handleNewProject = () => {
    const id = createProject()
    onMobileClose?.()
    navigate(`/obras/${id}`)
  }

  const handleSelectProject = (id: string) => {
    setActiveProject(id)
    onMobileClose?.()
    const project = projects.find((p) => p.id === id)
    if (!project) return

    if (project.status === 'relatorio_gerado') {
      navigate(`/obras/${id}/concluido`)
    } else if (project.status === 'em_validacao') {
      navigate(`/obras/${id}/validacao`)
    } else if (project.status === 'processando') {
      navigate(`/obras/${id}/processamento`)
    } else {
      navigate(`/obras/${id}`)
    }
  }

  const handleDeleteProject = (id: string, name: string) => {
    const confirmed = window.confirm(
      `Deseja remover a obra "${name || 'Obra sem nome'}"? Esta ação não pode ser desfeita.`,
    )
    if (!confirmed) return

    const wasActive = id === activeProjectId
    deleteProject(id)

    if (wasActive) {
      navigate('/')
    }
  }

  const navItemClass = (active: boolean) =>
    cn(
      'flex w-full cursor-pointer items-center gap-2 rounded-lg px-3 py-2.5 text-sm transition-colors duration-200 motion-reduce:transition-none',
      active
        ? 'bg-petrol-50 text-petrol-700'
        : 'text-graphite-500 hover:bg-graphite-100 hover:text-graphite-700',
    )

  return (
    <aside
      data-app-no-drag
      className={cn(
        'fixed inset-y-0 left-0 z-50 flex h-full w-[min(292px,88vw)] shrink-0 flex-col border-r border-graphite-200 bg-white transition-transform duration-200 motion-reduce:transition-none lg:static lg:z-auto lg:h-full lg:w-[292px] lg:translate-x-0',
        mobileOpen ? 'translate-x-0' : '-translate-x-full',
      )}
      aria-hidden={!mobileOpen ? undefined : false}
    >
      <div className="flex items-center justify-between border-b border-graphite-200 px-5 py-4">
        <Logo />
        <button
          type="button"
          aria-label="Fechar menu"
          className="inline-flex cursor-pointer rounded-lg p-1.5 text-graphite-500 transition-colors hover:bg-graphite-100 lg:hidden"
          onClick={onMobileClose}
        >
          <X className="h-5 w-5" />
        </button>
      </div>

      <div className="px-4 py-4">
        <Button className="w-full" onClick={handleNewProject}>
          <Plus className="h-4 w-4" />
          Nova Obra
        </Button>
      </div>

      <div className="scrollbar-thin flex-1 overflow-y-auto px-3 pb-4">
        <p className="px-2 py-2 text-[11px] font-semibold uppercase tracking-wider text-graphite-500">
          Obras
        </p>
        {projects.length === 0 ? (
          <p className="px-2 py-4 text-xs text-graphite-500">Nenhuma obra cadastrada</p>
        ) : (
          <ul className="space-y-1">
            {projects.map((project) => {
              const isActive = project.id === activeProjectId
              const label = project.name || 'Obra sem nome'
              const subtitle = project.km
                ? `${project.rodovia || 'Rodovia'} km ${project.km}`
                : 'Configuração pendente'

              return (
                <li key={project.id} className="relative">
                  <button
                    type="button"
                    onClick={() => handleSelectProject(project.id)}
                    className={cn(
                      'w-full cursor-pointer rounded-lg border px-3 py-3 pr-10 text-left transition-colors duration-200 motion-reduce:transition-none',
                      isActive
                        ? 'border-petrol-200 bg-petrol-50'
                        : 'border-transparent hover:border-graphite-200 hover:bg-graphite-50',
                    )}
                  >
                    <p className="truncate text-sm font-medium text-graphite-800">{label}</p>
                    <p className="mt-0.5 truncate text-xs text-graphite-500">{subtitle}</p>
                    <div className="mt-2">
                      <StatusBadge
                        status={project.status}
                        className="text-[10px]"
                        animate={project.status === 'processando'}
                      />
                    </div>
                  </button>
                  <button
                    type="button"
                    onClick={(e) => {
                      e.stopPropagation()
                      void handleDeleteProject(project.id, label)
                    }}
                    className="absolute right-2 top-2 z-10 inline-flex cursor-pointer items-center justify-center rounded-md p-1.5 text-graphite-400 transition-colors duration-200 hover:bg-error-bg hover:text-error"
                    title="Remover obra"
                    aria-label={`Remover obra ${label}`}
                  >
                    <Trash2 className="h-3.5 w-3.5" />
                  </button>
                </li>
              )
            })}
          </ul>
        )}
      </div>

      <div className="shrink-0 border-t border-graphite-200 px-3 py-3">
        <button
          type="button"
          onClick={() => {
            onMobileClose?.()
            navigate('/template')
          }}
          className={navItemClass(location.pathname === '/template')}
        >
          <FileText className="h-4 w-4 shrink-0" />
          Template Word
        </button>
        <button
          type="button"
          onClick={() => {
            onMobileClose?.()
            navigate('/gerenciamento')
          }}
          className={cn(navItemClass(location.pathname === '/gerenciamento'), 'mt-2')}
        >
          <SlidersHorizontal className="h-4 w-4 shrink-0" />
          Gerenciamento
        </button>
      </div>

      <div className="shrink-0 border-t border-graphite-200 px-5 py-4">
        <p className="text-[11px] text-graphite-500">v0.1.0 · Desktop</p>
      </div>
    </aside>
  )
}
