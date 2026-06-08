import { motion } from 'framer-motion'
import { ArrowLeft, ArrowRight, ExternalLink, FileText } from 'lucide-react'
import type { CaseSummary } from '@/types/api'

interface DocumentPreviewProps {
  selectedCase: CaseSummary
  onBack: () => void
  onAnalyze: () => void
}

export function DocumentPreview({ selectedCase, onBack, onAnalyze }: DocumentPreviewProps) {
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
            <p className="text-xs text-slate-400">{selectedCase.source_name}</p>
          </div>
          <button
            onClick={onAnalyze}
            className="ml-auto inline-flex items-center gap-2 bg-teal-700 hover:bg-teal-800 text-white text-sm font-semibold px-4 py-2.5 rounded-xl transition-colors cursor-pointer"
          >
            Analyze this denial
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
              <div className="min-w-0">
                <h1 className="text-xl font-bold text-slate-900 leading-tight">{selectedCase.title}</h1>
                <p className="text-sm text-slate-500 mt-1 break-words">{selectedCase.source_name}</p>
              </div>
            </div>

            <div className="space-y-3 text-sm">
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-1">What you are reading</p>
                <p className="text-slate-700 leading-relaxed">
                  A text-based denial PDF with extracted content saved into a selected case workspace.
                </p>
              </div>
              <div>
                <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-1">Elastic workspace</p>
                <p className="text-slate-700 leading-relaxed">
                  {selectedCase.document_count} document{selectedCase.document_count === 1 ? '' : 's'} indexed for this case.
                </p>
              </div>
            </div>

            {selectedCase.pdf_url && (
              <a
                href={selectedCase.pdf_url}
                target="_blank"
                rel="noopener noreferrer"
                className="inline-flex items-center gap-2 text-sm font-semibold text-teal-700 hover:text-teal-800"
              >
                Open PDF in a new tab
                <ExternalLink size={14} />
              </a>
            )}
          </section>

          <button
            onClick={onAnalyze}
            className="w-full inline-flex items-center justify-center gap-2 bg-teal-700 hover:bg-teal-800 text-white text-sm font-semibold px-5 py-3.5 rounded-xl transition-colors cursor-pointer"
          >
            Analyze this denial
            <ArrowRight size={15} />
          </button>
        </motion.aside>

        <motion.section
          initial={{ opacity: 0, y: 12 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: 0.08 }}
          className="bg-white border border-slate-200 rounded-2xl overflow-hidden min-h-[620px]"
        >
          {selectedCase.pdf_url ? (
            <iframe
              title="Selected denial PDF"
              src={selectedCase.pdf_url}
              className="w-full h-[calc(100vh-140px)] min-h-[620px] border-0"
            />
          ) : (
            <div className="h-full flex items-center justify-center p-6 sm:p-8">
              <div className="max-w-md text-center space-y-3">
                <div className="mx-auto w-12 h-12 rounded-2xl bg-teal-50 border border-teal-100 text-teal-700 flex items-center justify-center">
                  <FileText size={20} />
                </div>
                <h2 className="text-lg font-bold text-slate-900">PDF preview unavailable</h2>
                <p className="text-sm text-slate-500 leading-relaxed">
                  The extracted text is still saved in Elastic. Re-upload the denial PDF if you need to preview the original file.
                </p>
              </div>
            </div>
          )}
        </motion.section>
      </main>
    </div>
  )
}
