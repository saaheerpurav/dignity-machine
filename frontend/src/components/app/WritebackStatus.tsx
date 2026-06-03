import { motion } from 'framer-motion'
import { CheckCircle2 } from 'lucide-react'

interface WritebackStatusProps {
  enabled: boolean
  writeCounts: Record<string, number>
}

export function WritebackStatus({ enabled, writeCounts }: WritebackStatusProps) {
  if (!enabled) return null
  const total = Object.values(writeCounts).reduce((a, b) => a + b, 0)
  if (total === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-2.5 bg-green-50 border border-green-200 rounded-xl px-4 py-3"
    >
      <CheckCircle2 size={15} className="text-green-600 shrink-0" />
      <div className="flex flex-wrap gap-3">
        <span className="text-sm font-medium text-green-800">Saved to Elastic</span>
        {Object.entries(writeCounts).map(([index, count]) =>
          count > 0 ? (
            <span key={index} className="text-xs text-green-600 bg-green-100 border border-green-200 rounded px-2 py-0.5 font-mono">
              {index}: {count}
            </span>
          ) : null
        )}
      </div>
    </motion.div>
  )
}
