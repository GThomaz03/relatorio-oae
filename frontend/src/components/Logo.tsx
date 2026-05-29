import { Layers } from 'lucide-react'
import { cn } from '@/utils/cn'

interface LogoProps {
  compact?: boolean
  className?: string
}

export function Logo({ compact, className }: LogoProps) {
  return (
    <div className={cn('flex items-center gap-3', className)}>
      <div className="flex h-9 w-9 items-center justify-center rounded-lg bg-petrol-600">
        <Layers className="h-5 w-5 text-white" strokeWidth={1.75} />
      </div>
      {!compact && (
        <div className="min-w-0">
          <p className="text-sm font-semibold leading-tight text-graphite-800">OAE Report</p>
          <p className="text-[11px] leading-tight text-graphite-500">Generator</p>
        </div>
      )}
    </div>
  )
}
