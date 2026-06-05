import { motion } from 'framer-motion'
import { ArrowLeft, ArrowRight, ExternalLink, FileText } from 'lucide-react'

interface DocumentPreviewProps {
  onBack: () => void
  onAnalyze: () => void
}

const PDF_URL = '/documents/maria-lopez-documents.pdf'

export function DocumentPreview({ onBack, onAnalyze }: DocumentPreviewProps) {
  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-100">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-4">
          <button
            onClick={onBack}
            className="text-slate-400 hover:text-slate-700 transition-colors p-1.5 -ml-1.5 rounded-lg hover:bg-slate-100 cursor-pointer"
            aria-label="Back"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <p className="text-sm font-bold text-teal-700 tracking-widest uppercase">Dignity Machine</p>
            <p className="text-xs text-slate-400">Maria's documents</p>
          </div>
          <button
            onClick={onAnalyze}
            className="ml-auto inline-flex items-center gap-2 bg-teal-700 hover:bg-teal-800 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors cursor-pointer"
          >
            Analyze these documents
            <ArrowRight size={15} />
          </button>
        </div>
      </header>

      <main className="max-w-7xl mx-auto px-4 sm:px-6 py-6 grid lg:grid-cols-[360px_1fr] gap-6">
        <motion.aside
          initial={{ opacity: 0, x: -12 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ duration: 0.35 }}
          className="space-y-4"
        >
          <section className="bg-white border border-slate-200 rounded-2xl p-5 space-y-4">
            <div className="flex items-start gap-3">
              <div className="w-10 h-10 rounded-xl bg-teal-50 border border-teal-100 text-teal-700 flex items-center justify-center shrink-0">
                <FileText size={18} />
              </div>
              <div>
                <h1 className="text-xl font-bold text-slate-900 leading-tight">Maria Lopez</h1>
                <p className="text-sm text-slate-500 mt-1">Denied disability benefits for fibromyalgia.</p>
              </div>
            </div>

            <div className="space-y-3 text-sm">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-1">What you are reading</p>
                <p className="text-slate-700 leading-relaxed">
                  A short example file with Maria's denial letter, doctor notes, daily-work limits, missing records, and helper contact.
                </p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-1">What the agent uses</p>
                <p className="text-slate-700 leading-relaxed">
                  The same text is already saved in Elastic, along with Social Security rules, so the agent can search it live.
                </p>
              </div>
            </div>

            <div className="rounded-xl bg-slate-50 border border-slate-100 p-4 space-y-2">
              <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Included</p>
              <ul className="space-y-1.5 text-sm text-slate-600">
                <li>Denial letter summary</li>
                <li>Doctor records from Lakeview Rheumatology</li>
                <li>Maria's daily-work limits</li>
                <li>Missing proof the agent should find</li>
              </ul>
            </div>

            <a
              href={PDF_URL}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 text-sm font-semibold text-teal-700 hover:text-teal-800"
            >
              Open PDF in a new tab
              <ExternalLink size={14} />
            </a>
          </section>

          <button
            onClick={onAnalyze}
            className="w-full inline-flex items-center justify-center gap-2 bg-teal-700 hover:bg-teal-800 text-white text-sm font-semibold px-5 py-3.5 rounded-xl transition-colors cursor-pointer"
          >
            Analyze Maria's denial
            <ArrowRight size={15} />
          </button>
        </motion.aside>

        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.08 }}
          className="bg-white border border-slate-200 rounded-2xl overflow-hidden min-h-[720px]"
        >
          <iframe
            title="Maria Lopez documents"
            src={PDF_URL}
            className="w-full h-[calc(100vh-140px)] min-h-[720px] border-0"
          />
        </motion.section>
      </main>
    </div>
  )
}
