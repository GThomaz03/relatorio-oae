import { Badge } from '@/components/ui/badge'
import { PROJECT_STATUS_CONFIG } from '@/utils/project-status'
import type { ProjectStatus } from '@/types/project'
import { cn } from '@/utils/cn'

interface StatusBadgeProps {
  status: ProjectStatus
  showIcon?: boolean
  className?: string
  animate?: boolean
}

export function StatusBadge({ status, showIcon = true, className, animate }: StatusBadgeProps) {
  const config = PROJECT_STATUS_CONFIG[status]
  const Icon = config.icon

  return (
    <Badge variant={config.variant} className={cn('gap-1', className)}>
      {showIcon && (
        <Icon
          className={cn(
            'h-3 w-3',
            status === 'processando' && animate !== false && 'animate-spin',
          )}
        />
      )}
      {config.label}
    </Badge>
  )
}
