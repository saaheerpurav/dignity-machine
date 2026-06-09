import { useState } from 'react'
import { motion } from 'framer-motion'
import { ArrowLeft, FileText, FileUp } from 'lucide-react'

interface UploadCaseProps {
  loading: boolean
  error: string | null
  onBack: () => void
  onUpload: (file: File) => void
}

export function UploadCase({ loading, error, onBack, onUpload }: UploadCaseProps) {
  const [file, setFile] = useState<File | null>(null)

  return (
    <div className="min-h-screen bg-slate-50">
      <header className="bg-white border-b border-slate-100">
        <div className="max-w-4xl mx-auto px-4 sm:px-6 py-4 flex items-center gap-4">
          <button
            onClick={onBack}
            className="text-slate-400 hover:text-slate-700 transition-colors p-1.5 -ml-1.5 rounded-lg hover:bg-slate-100 cursor-pointer"
            aria-label="Back"
          >
            <ArrowLeft size={16} />
          </button>
          <div>
            <p className="text-sm font-bold text-teal-700 tracking-widest uppercase">Dignity Machine</p>
            <p className="text-xs text-slate-400">Upload denial PDF</p>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 sm:px-6 py-12">
        <motion.section
          initial={{ opacity: 0, y: 16 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35 }}
          className="bg-white border border-slate-200 rounded-2xl p-6 sm:p-8 space-y-6"
        >
          <div className="flex items-start gap-4">
            <div className="w-12 h-12 rounded-xl bg-teal-50 border border-teal-100 text-teal-700 flex items-center justify-center shrink-0">
              <FileText size={20} />
            </div>
            <div>
              <h1 className="text-2xl font-bold text-slate-900">Upload denial PDF</h1>
              <p className="text-sm text-slate-500 mt-1">Version 1 accepts one text-readable PDF. Scanned image-only PDFs are rejected.</p>
            </div>
          </div>

          <label className="block border-2 border-dashed border-slate-200 rounded-2xl p-6 hover:border-teal-200 transition-colors cursor-pointer bg-slate-50/60">
            <input
              type="file"
              accept="application/pdf,.pdf"
              className="sr-only"
              onChange={event => setFile(event.target.files?.[0] ?? null)}
            />
            <div className="flex flex-col items-center text-center gap-3">
              <FileUp size={28} className="text-teal-700" />
              <div>
                <p className="text-sm font-semibold text-slate-800">{file ? file.name : 'Choose one PDF'}</p>
                <p className="text-xs text-slate-400 mt-1">The readable text will be prepared for this case before analysis.</p>
              </div>
            </div>
          </label>

          {loading && <p className="text-sm text-teal-600 font-medium">Reading PDF and preparing case workspace</p>}
          {error && <p className="text-sm text-red-500 font-medium">{error}</p>}

          <button
            onClick={() => file && onUpload(file)}
            disabled={!file || loading}
            className="inline-flex items-center justify-center gap-2 bg-teal-700 hover:bg-teal-800 disabled:bg-teal-300 text-white text-sm font-semibold px-5 py-3 rounded-xl transition-colors cursor-pointer disabled:cursor-not-allowed"
          >
            Read this PDF
            <FileText size={15} />
          </button>
        </motion.section>
      </main>
    </div>
  )
}
