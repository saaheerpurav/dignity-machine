import { motion } from 'framer-motion'
import { CheckCircle2 } from 'lucide-react'

interface WritebackStatusProps {
  enabled: boolean
}

export function WritebackStatus({ enabled }: WritebackStatusProps) {
  if (!enabled) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 6 }}
      animate={{ opacity: 1, y: 0 }}
      className="flex items-center gap-2.5 bg-green-50 border border-green-200 rounded-xl px-4 py-3"
    >
      <CheckCircle2 size={15} className="text-green-600 shrink-0" />
      <div className="flex flex-wrap gap-3">
        <span className="text-sm font-medium text-green-800">Action plan saved</span>
      </div>
    </motion.div>
  )
}
