import type { ReactNode } from 'react'
import { cn } from '@/utils/cn'

type PageWidth = 'default' | 'narrow' | 'wide' | 'centered' | 'flush'

const WIDTH: Record<PageWidth, string> = {
  default: 'max-w-6xl',
  narrow: 'max-w-4xl',
  wide: 'max-w-7xl',
  centered: 'max-w-3xl',
  flush: 'max-w-none',
}

interface PageShellProps {
  children: ReactNode
  width?: PageWidth
  /** Preenche altura disponível do main (telas com painéis internos). */
  fill?: boolean
  className?: string
}

export function PageShell({
  children,
  width = 'default',
  fill = false,
  className,
}: PageShellProps) {
  return (
    <div
      className={cn(
        'mx-auto w-full min-w-0 px-4 py-5 sm:px-6 lg:px-8',
        WIDTH[width],
        fill &&
          'flex h-[calc(100dvh-3.25rem)] max-h-[calc(100dvh-3.25rem)] flex-col overflow-hidden',
        className,
      )}
    >
      {children}
    </div>
  )
}

interface PageHeaderProps {
  title: string
  description?: string
  actions?: ReactNode
  className?: string
}

export function PageHeader({ title, description, actions, className }: PageHeaderProps) {
  return (
    <div
      className={cn(
        'rounded-xl border border-graphite-200 bg-white px-4 py-4 sm:px-5 sm:py-5',
        className,
      )}
    >
      <div className="flex flex-wrap items-start justify-between gap-3 sm:gap-4">
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold tracking-tight text-graphite-800 sm:text-2xl">
            {title}
          </h1>
          {description ? (
            <p className="mt-1 text-sm text-graphite-500">{description}</p>
          ) : null}
        </div>
        {actions ? (
          <div className="flex shrink-0 flex-wrap items-center gap-2">{actions}</div>
        ) : null}
      </div>
    </div>
  )
}

interface EmptyStateProps {
  message: string
  className?: string
}

export function EmptyState({ message, className }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-1 items-center justify-center p-8 text-center text-sm text-graphite-500',
        className,
      )}
    >
      {message}
    </div>
  )
}
