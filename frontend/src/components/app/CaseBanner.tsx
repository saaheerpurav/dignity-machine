import { motion } from 'framer-motion'
import { Briefcase, Calendar, FileText, MapPin } from 'lucide-react'

export function CaseBanner() {
  return (
    <motion.section
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] as const }}
      className="relative bg-white border border-slate-200 rounded-3xl overflow-hidden"
    >
      <div className="absolute inset-0 bg-gradient-to-br from-rose-50/40 via-white to-teal-50/30 pointer-events-none" />

      <div className="relative px-6 sm:px-8 py-7 flex items-start gap-6">
        <motion.div
          initial={{ scale: 0.85, opacity: 0 }}
          animate={{ scale: 1, opacity: 1 }}
          transition={{ duration: 0.45, delay: 0.1, type: 'spring', stiffness: 220, damping: 18 }}
          className="shrink-0 w-16 h-16 sm:w-20 sm:h-20 rounded-2xl bg-gradient-to-br from-teal-100 to-teal-200 border border-teal-200 flex items-center justify-center"
        >
          <span className="text-2xl sm:text-3xl font-bold text-teal-700">ML</span>
        </motion.div>

        <div className="flex-1 min-w-0">
          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.18 }}
            className="text-[10px] font-bold uppercase tracking-widest text-slate-400 mb-1.5"
          >
            Maria's documents
          </motion.p>

          <motion.h1
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.22 }}
            className="text-4xl sm:text-5xl font-bold text-slate-900 tracking-tight leading-none"
          >
            Maria Lopez
          </motion.h1>

          <motion.div
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.4, delay: 0.3 }}
            className="mt-3 flex items-baseline gap-2 flex-wrap"
          >
            <span className="text-lg sm:text-xl font-semibold text-rose-400">Denied</span>
            <span className="text-lg sm:text-xl text-slate-400 font-light">for</span>
            <span className="text-lg sm:text-xl font-semibold text-slate-700">Fibromyalgia</span>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.36 }}
            className="mt-3 max-w-2xl text-sm text-slate-500 leading-relaxed"
          >
            The agent is reading Maria's denial letter and doctor records, then comparing them with Social Security rules saved in Elastic.
          </motion.p>

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ delay: 0.42 }}
            className="mt-4 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs text-slate-400"
          >
            <span className="flex items-center gap-1.5">
              <Calendar size={11} className="text-slate-300" />
              Denial letter <span className="text-slate-600 font-medium">March 2024</span>
            </span>
            <span className="flex items-center gap-1.5">
              <Briefcase size={11} className="text-slate-300" />
              Past work <span className="text-slate-600 font-medium">Data entry clerk</span>
            </span>
            <span className="flex items-center gap-1.5">
              <MapPin size={11} className="text-slate-300" />
              <span className="text-slate-600 font-medium">Lakeview, CA</span>
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
          <a
            href="/documents/maria-lopez-documents.pdf"
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-[11px] font-semibold text-slate-400 hover:text-teal-700"
          >
            <FileText size={12} />
            View documents
          </a>
        </motion.div>
      </div>
    </motion.section>
  )
}
