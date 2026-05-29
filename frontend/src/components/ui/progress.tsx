import { cn } from '@/utils/cn'

interface ProgressProps {
  value: number
  className?: string
}

export function Progress({ value, className }: ProgressProps) {
  const clamped = Math.min(100, Math.max(0, value))
  return (
    <div
      className={cn(
        'relative h-2 w-full overflow-hidden rounded-full bg-graphite-100',
        className,
      )}
    >
      <div
        className="h-full rounded-full bg-gradient-to-r from-petrol-600 to-petrol-400 transition-all duration-500 ease-out"
        style={{ width: `${clamped}%` }}
      />
    </div>
  )
}
