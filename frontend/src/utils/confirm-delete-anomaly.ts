import type { AnomalyRow } from '@/types/project'

export function confirmDeleteAnomaly(anomaly: AnomalyRow): boolean {
  const label = [anomaly.element, anomaly.anomalyType].filter(Boolean).join(' — ')
  return window.confirm(
    `Excluir a anomalia "${label || 'sem identificação'}"?\n\nEla será removida da validação e do relatório fotográfico. Esta ação não pode ser desfeita.`,
  )
}
