import { motion } from 'framer-motion'
import { FileText, Search, ShieldCheck } from 'lucide-react'
import type { CaseSummary } from '@/types/api'

export function CaseBanner({ selectedCase }: { selectedCase: CaseSummary }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] as const }}
      className="relative bg-white border border-slate-200 rounded-2xl overflow-hidden"
    >
      <div className="relative px-6 sm:px-8 py-7 flex items-start gap-6">
        <div className="flex-1 min-w-0">
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.18 }}
            className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5"
          >
            Selected case
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.22 }}
            className="text-3xl sm:text-4xl font-bold text-slate-900 tracking-tight leading-tight"
          >
            {selectedCase.title}
          </motion.h1>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.36 }}
            className="mt-3 max-w-2xl text-sm text-slate-500 leading-relaxed"
          >
            The agent is reading this denial and any uploaded case text, then comparing it with relevant Social Security rules.
          </motion.p>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.42 }}
            className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-slate-400"
          >
            <span className="flex items-center gap-1.5">
              <FileText size={11} className="text-slate-300" />
              {selectedCase.source_name}
            </span>
            <span className="flex items-center gap-1.5">
              <Search size={11} className="text-slate-300" />
              Case documents <span className="text-slate-600 font-medium">scoped</span>
            </span>
            <span className="flex items-center gap-1.5">
              <ShieldCheck size={11} className="text-slate-300" />
              Social Security rules <span className="text-slate-600 font-medium">searchable</span>
            </span>
          </motion.div>
        </div>

        <motion.div
          initial={{ opacity: 0, x: 12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.38 }}
          className="hidden md:flex flex-col items-end shrink-0 gap-2"
        >
          <div className="flex items-center gap-1.5">
            <span className="relative flex w-2 h-2">
              <span className="absolute inset-0 rounded-full bg-teal-300 opacity-75 animate-ping" />
              <span className="relative rounded-full bg-teal-500 w-2 h-2" />
            </span>
            <span className="text-[10px] font-bold uppercase tracking-widest text-teal-600">Ready to analyze</span>
          </div>
          {selectedCase.pdf_url && (
            <a
              href={selectedCase.pdf_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-slate-400 hover:text-teal-700"
            >
              <FileText size={12} />
              View PDF
            </a>
          )}
        </motion.div>
      </div>
    </motion.section>
  )
}
