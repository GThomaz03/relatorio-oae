import type { ProjectStatus } from '@/types/project'
import type { LucideIcon } from 'lucide-react'
import {
  AlertCircle,
  CheckCircle2,
  Clock,
  FileSearch,
  FileWarning,
  Loader2,
  Settings,
} from 'lucide-react'

export interface StatusConfig {
  label: string
  variant: 'default' | 'success' | 'warning' | 'error' | 'info' | 'petrol'
  icon: LucideIcon
}

export const PROJECT_STATUS_CONFIG: Record<ProjectStatus, StatusConfig> = {
  nao_configurada: {
    label: 'Não configurada',
    variant: 'default',
    icon: Settings,
  },
  arquivos_pendentes: {
    label: 'Arquivos pendentes',
    variant: 'warning',
    icon: FileWarning,
  },
  pronta_analise: {
    label: 'Pronta para análise',
    variant: 'info',
    icon: FileSearch,
  },
  em_validacao: {
    label: 'Em validação',
    variant: 'petrol',
    icon: Clock,
  },
  processando: {
    label: 'Processando',
    variant: 'info',
    icon: Loader2,
  },
  relatorio_gerado: {
    label: 'Relatório gerado',
    variant: 'success',
    icon: CheckCircle2,
  },
  erro: {
    label: 'Erro de processamento',
    variant: 'error',
    icon: AlertCircle,
  },
}

export function deriveProjectStatus(
  hasBasicInfo: boolean,
  hasAllFiles: boolean,
  hasAnalysis: boolean,
  currentStatus: ProjectStatus,
): ProjectStatus {
  if (currentStatus === 'processando' || currentStatus === 'relatorio_gerado' || currentStatus === 'erro') {
    return currentStatus
  }
  if (!hasBasicInfo) return 'nao_configurada'
  if (!hasAllFiles) return 'arquivos_pendentes'
  if (hasAnalysis) return 'em_validacao'
  return 'pronta_analise'
}

export function formatFileSize(bytes?: number): string {
  if (!bytes) return '—'
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

export function formatDate(iso: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  }).format(new Date(iso))
}
