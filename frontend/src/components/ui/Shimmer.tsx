import { clsx } from 'clsx'

interface ShimmerProps {
  className?: string
  lines?: number
}

export function Shimmer({ className, lines = 1 }: ShimmerProps) {
  return (
    <div className={clsx('space-y-2', className)}>
      {Array.from({ length: lines }).map((_, i) => (
        <div
          key={i}
          className={clsx('shimmer rounded h-4', i === lines - 1 && lines > 1 ? 'w-3/4' : 'w-full')}
        />
      ))}
    </div>
  )
}

export function ShimmerCard() {
  return (
    <div className="bg-white border border-slate-200 rounded-xl p-4 space-y-3">
      <div className="shimmer h-4 w-1/3 rounded" />
      <div className="shimmer h-3 w-full rounded" />
      <div className="shimmer h-3 w-5/6 rounded" />
      <div className="shimmer h-3 w-2/3 rounded" />
    </div>
  )
}
