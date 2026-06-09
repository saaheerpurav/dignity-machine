import { motion } from 'framer-motion'
import { ArrowRight, FileUp, PlayCircle, ShieldCheck } from 'lucide-react'

interface LandingPageProps {
  loading: boolean
  error: string | null
  onExample: () => void
  onUpload: () => void
}

const steps = [
  'Read one text-based denial PDF',
  'Create a private case workspace',
  'Analyze only the selected case',
  'Compare with Social Security rules',
]

export function LandingPage({ loading, error, onExample, onUpload }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      <header className="border-b border-slate-100 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <span className="text-teal-700 font-bold text-sm tracking-widest uppercase">Dignity Machine</span>
          <span className="text-xs text-slate-400 bg-slate-50 border border-slate-200 px-3 py-1 rounded-full">Appeal prep workspace</span>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-6 py-16">
        <div className="max-w-3xl w-full text-center space-y-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] as const }}
            className="space-y-4"
          >
            <div className="inline-flex items-center gap-3">
              <div className="h-px w-10 bg-slate-200" />
              <span className="text-xs text-slate-400 uppercase tracking-widest font-medium">Disability Denial Review</span>
              <div className="h-px w-10 bg-slate-200" />
            </div>
            <h1 className="text-5xl sm:text-6xl font-bold text-slate-900 tracking-tight leading-none">
              Analyze a denial PDF
            </h1>
            <p className="text-base sm:text-lg text-slate-500 leading-relaxed font-light max-w-xl mx-auto">
              Select the example denial or upload one text-readable PDF. The review stays focused on that selected case.
            </p>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.12, ease: [0.25, 0.46, 0.45, 0.94] as const }}
            className="grid sm:grid-cols-2 gap-3 max-w-2xl mx-auto"
          >
            <button
              onClick={onExample}
              disabled={loading}
              className="group inline-flex items-center justify-center gap-3 bg-teal-700 hover:bg-teal-800 disabled:bg-teal-300 text-white text-base font-semibold px-6 py-4 rounded-2xl transition-all shadow-lg shadow-teal-900/20 cursor-pointer disabled:cursor-wait"
            >
              <PlayCircle size={19} />
              Try example denial
              <ArrowRight size={16} className="group-hover:translate-x-0.5 transition-transform" />
            </button>
            <button
              onClick={onUpload}
              disabled={loading}
              className="inline-flex items-center justify-center gap-3 bg-white hover:bg-slate-50 disabled:bg-slate-50 text-slate-800 text-base font-semibold px-6 py-4 rounded-2xl border border-slate-200 transition-all cursor-pointer disabled:cursor-wait"
            >
              <FileUp size={19} className="text-teal-700" />
              Upload denial PDF
            </button>
          </motion.div>

          {loading && <p className="text-sm text-teal-600 font-medium">Reading PDF and preparing case workspace</p>}
          {error && <p className="text-sm text-red-500 font-medium">{error}</p>}

          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.25 }}
            className="border-t border-slate-100 pt-8"
          >
            <p className="text-xs uppercase tracking-widest text-slate-400 font-semibold mb-5">Flow</p>
            <div className="flex flex-wrap justify-center gap-2.5">
              {steps.map((step, i) => (
                <div key={step} className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-full px-4 py-2">
                  <div className="w-5 h-5 rounded-full flex items-center justify-center shrink-0 border text-teal-600 bg-teal-50 border-teal-100">
                    <ShieldCheck size={11} />
                  </div>
                  <span className="text-xs font-medium text-slate-700">
                    <span className="text-slate-400 mr-1">{i + 1}.</span>{step}
                  </span>
                </div>
              ))}
            </div>
          </motion.div>
        </div>
      </main>
    </div>
  )
}
