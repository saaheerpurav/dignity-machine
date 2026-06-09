import { motion } from 'framer-motion'
import { ArrowLeft, Zap } from 'lucide-react'

interface CaseHeaderProps {
  title: string
  onBack: () => void
}

export function CaseHeader({ title, onBack }: CaseHeaderProps) {
  return (
    <motion.header
      initial={{ y: -20, opacity: 0 }}
      animate={{ y: 0, opacity: 1 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] as const }}
      className="bg-white/90 backdrop-blur border-b border-slate-100 sticky top-0 z-30"
    >
      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-3.5 flex items-center gap-4">
        <button
          onClick={onBack}
          className="text-slate-300 hover:text-slate-600 transition-colors cursor-pointer p-1.5 -ml-1.5 rounded-lg hover:bg-slate-100"
          aria-label="Back to selected documents"
        >
          <ArrowLeft size={15} />
        </button>

        <div>
          <span className="text-teal-600 font-bold text-sm tracking-widest uppercase">
            Dignity Machine
          </span>
          <p className="text-[11px] text-slate-400 hidden sm:block">Analyzing selected denial</p>
        </div>

        <span className="text-xs text-slate-400 hidden lg:inline truncate max-w-[260px] ml-2">
          {title}
        </span>

        <div className="ml-auto flex items-center gap-1.5 text-teal-500 text-xs font-medium shrink-0">
          <Zap size={11} />
          <span className="hidden sm:inline">Review in progress</span>
        </div>
      </div>
    </motion.header>
  )
}
