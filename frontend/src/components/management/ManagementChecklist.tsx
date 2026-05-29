import type { ManagementSummaryResponse } from '@/services/management-api'
import { CheckCircle2, Circle } from 'lucide-react'

export function ManagementChecklist({ summary }: { summary: ManagementSummaryResponse | null }) {
  if (!summary) return null

  return (
    <div className="mb-6 rounded-xl border border-graphite-200 bg-white p-4">
      <h2 className="text-sm font-semibold text-graphite-800">Antes da primeira análise</h2>
      <p className="mt-1 text-xs text-graphite-500">
        Configuração global — aplica-se a todas as obras.{' '}
        {summary.description_rule_count} regras · {summary.catalog_base_count} bases no catálogo ·{' '}
        {summary.legenda_count} siglas.
      </p>
      <ul className="mt-3 space-y-2">
        {summary.checklist.map((item) => (
          <li key={item.id} className="flex items-start gap-2 text-sm">
            {item.ok ? (
              <CheckCircle2 className="mt-0.5 h-4 w-4 shrink-0 text-success" />
            ) : (
              <Circle className="mt-0.5 h-4 w-4 shrink-0 text-graphite-400" />
            )}
            <div>
              <span className={item.ok ? 'text-graphite-700' : 'text-graphite-800 font-medium'}>
                {item.label}
              </span>
              {!item.ok && item.hint ? (
                <p className="text-xs text-graphite-500">{item.hint}</p>
              ) : null}
            </div>
          </li>
        ))}
      </ul>
    </div>
  )
}
