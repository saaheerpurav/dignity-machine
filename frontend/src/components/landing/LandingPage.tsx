import { motion } from 'framer-motion'
import { ArrowRight, FileSearch, ShieldCheck, FileText, UserCheck, AlertCircle } from 'lucide-react'

interface LandingPageProps {
  onEnter: () => void
}

const steps = [
  { icon: AlertCircle, label: 'Denial read', color: 'text-red-500 bg-red-50 border-red-100' },
  { icon: ShieldCheck, label: 'Policy searched', color: 'text-teal-600 bg-teal-50 border-teal-100' },
  { icon: FileSearch, label: 'Records found', color: 'text-blue-500 bg-blue-50 border-blue-100' },
  { icon: FileText, label: 'Gaps identified', color: 'text-amber-600 bg-amber-50 border-amber-100' },
  { icon: UserCheck, label: 'Packet ready', color: 'text-green-600 bg-green-50 border-green-100' },
]

export function LandingPage({ onEnter }: LandingPageProps) {
  return (
    <div className="min-h-screen bg-white flex flex-col">
      {/* nav */}
      <header className="border-b border-slate-100 px-6 py-4">
        <div className="max-w-5xl mx-auto flex items-center justify-between">
          <span className="text-teal-700 font-bold text-sm tracking-widest uppercase">Dignity Machine</span>
          <span className="text-xs text-slate-400 bg-slate-50 border border-slate-200 px-3 py-1 rounded-full">
            Google Cloud · Elastic Partner Track
          </span>
        </div>
      </header>

      <main className="flex-1 flex flex-col items-center justify-center px-6 py-20">
        <div className="max-w-3xl w-full text-center space-y-8">

          {/* patient name — the hero */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, ease: [0.25, 0.46, 0.45, 0.94] as const }}
          >
            <div className="inline-flex items-center gap-3 mb-3">
              <div className="h-px w-10 bg-slate-200" />
              <span className="text-xs text-slate-400 uppercase tracking-widest font-medium">Case file</span>
              <div className="h-px w-10 bg-slate-200" />
            </div>
            <h2 className="text-5xl sm:text-6xl font-bold text-slate-900 tracking-tight leading-none">
              Maria Lopez
            </h2>
          </motion.div>

          {/* diagnosis — second hero line */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.12, ease: [0.25, 0.46, 0.45, 0.94] as const }}
            className="space-y-3"
          >
            <p className="text-2xl sm:text-3xl font-light text-slate-500 tracking-tight leading-tight">
              <span className="text-rose-400 font-medium">Denied</span> for
              <span className="block sm:inline sm:ml-2 text-slate-900 font-bold">Fibromyalgia</span>
            </p>
            <p className="text-xs uppercase tracking-widest text-slate-400 font-semibold">
              Social Security Disability · SSA Appeal
            </p>
          </motion.div>

          {/* explainer */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.18, ease: [0.25, 0.46, 0.45, 0.94] as const }}
          >
            <p className="text-base sm:text-lg text-slate-500 leading-relaxed font-light max-w-xl mx-auto">
              SSA said her records didn't establish severity.
              <span className="text-slate-900 font-medium"> We found what they were missing.</span>
            </p>
          </motion.div>

          {/* CTA */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.5, delay: 0.22, ease: [0.25, 0.46, 0.45, 0.94] as const }}
            className="flex flex-col items-center gap-3"
          >
            <button
              onClick={onEnter}
              className="group inline-flex items-center gap-3 bg-teal-700 hover:bg-teal-800 text-white text-base font-semibold px-8 py-4 rounded-full transition-all shadow-lg shadow-teal-900/20 hover:shadow-teal-900/30 cursor-pointer"
            >
              Analyze her case
              <ArrowRight size={18} className="group-hover:translate-x-0.5 transition-transform" />
            </button>
            <p className="text-xs text-slate-400">Real Elastic retrieval · Gemini agent · No hardcoded answers</p>
          </motion.div>

          {/* divider + steps */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.6, delay: 0.35 }}
          >
            <div className="border-t border-slate-100 pt-8">
              <p className="text-xs uppercase tracking-widest text-slate-400 font-semibold mb-6">How it works</p>
              <div className="flex flex-wrap justify-center gap-2.5">
                {steps.map((step, i) => (
                  <div
                    key={step.label}
                    className="flex items-center gap-2 bg-slate-50 border border-slate-200 rounded-full px-4 py-2"
                  >
                    <div className={`w-5 h-5 rounded-full flex items-center justify-center shrink-0 border ${step.color}`}>
                      <step.icon size={11} />
                    </div>
                    <span className="text-xs font-medium text-slate-700">
                      <span className="text-slate-400 mr-1">{i + 1}.</span>{step.label}
                    </span>
                  </div>
                ))}
              </div>
            </div>
          </motion.div>

          <motion.p
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            transition={{ duration: 0.5, delay: 0.45 }}
            className="text-xs text-slate-300"
          >
            Not an AI lawyer · Does not file with SSA · Prepares a cited packet for advocate review
          </motion.p>
        </div>
      </main>
    </div>
  )
}
