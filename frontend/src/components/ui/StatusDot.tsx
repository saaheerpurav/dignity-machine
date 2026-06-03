import { clsx } from 'clsx'

type Status = 'idle' | 'active' | 'done'

interface StatusDotProps {
  status: Status
  size?: 'sm' | 'md'
}

export function StatusDot({ status, size = 'md' }: StatusDotProps) {
  const sizeClass = size === 'sm' ? 'w-2 h-2' : 'w-2.5 h-2.5'
  return (
    <span className="relative inline-flex shrink-0">
      <span
        className={clsx(
          'rounded-full',
          sizeClass,
          status === 'idle' && 'bg-slate-300',
          status === 'active' && 'bg-teal-500 pulse-teal',
          status === 'done' && 'bg-green-500'
        )}
      />
    </span>
  )
}
