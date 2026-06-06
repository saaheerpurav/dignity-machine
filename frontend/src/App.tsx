import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { RotateCcw } from 'lucide-react'
import { useConfig } from '@/hooks/useConfig'
import { useAnalyze } from '@/hooks/useAnalyze'
import { LandingPage } from '@/components/landing/LandingPage'
import { DocumentPreview } from '@/components/landing/DocumentPreview'
import { UploadCase } from '@/components/landing/UploadCase'
import { CaseHeader } from '@/components/app/CaseHeader'
import { MissionButtons } from '@/components/app/MissionButtons'
import { MissionTimeline } from '@/components/app/MissionTimeline'
import { EvidenceCards } from '@/components/app/EvidenceCards'
import { MissingEvidence } from '@/components/app/MissingEvidence'
import { PacketPreview } from '@/components/app/PacketPreview'
import { TechTrace } from '@/components/app/TechTrace'
import { WritebackStatus } from '@/components/app/WritebackStatus'
import { StatsBar } from '@/components/app/StatsBar'
import { CaseBanner } from '@/components/app/CaseBanner'
import type { CaseSummary } from '@/types/api'

type View = 'landing' | 'upload' | 'documents' | 'app'

const pageTransition = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.35, ease: 'easeInOut' as const },
}

function AppDashboard({ selectedCase, onBack }: { selectedCase: CaseSummary; onBack: () => void }) {
  const { config, loading: configLoading } = useConfig()
  const { data, loading, error, events, statusMessages, run, reset } = useAnalyze()
  const [activeMission, setActiveMission] = useState<string | null>(null)
  const [writeback, setWriteback] = useState(false)

  const handleMission = (id: string) => {
    setActiveMission(id)
    run(selectedCase.case_id, id, writeback)
  }

  const handleReset = async () => {
    if (!confirm('Delete generated notes for this case from Elastic?')) return
    const res = await fetch(`/api/cases/${encodeURIComponent(selectedCase.case_id)}/writeback/reset`, { method: 'POST' })
    if (res.ok) {
      reset()
      setActiveMission(null)
    }
  }

  const structured = data?.structured ?? null

  return (
    <div className="min-h-screen bg-slate-50">
      <CaseHeader caseId={selectedCase.case_id} title={selectedCase.title} onBack={onBack} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <CaseBanner selectedCase={selectedCase} />

        {configLoading ? (
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
            {[1, 2, 3, 4].map(i => <div key={i} className="shimmer h-28 rounded-2xl" />)}
          </div>
        ) : (
          <MissionButtons
            missions={config?.missions ?? []}
            activeMission={activeMission}
            loading={loading}
            onSelect={handleMission}
          />
        )}

        <MissionTimeline running={loading} done={!!data && !loading} />

        {loading && statusMessages.length > 0 && (
          <div className="bg-white border border-teal-100 rounded-xl px-4 py-3">
            <p className="text-xs font-semibold text-teal-700">{statusMessages[statusMessages.length - 1]}</p>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl px-4 py-3">
            <p className="text-sm font-semibold text-red-700">Analysis failed</p>
            <p className="text-xs text-red-600 mt-1 break-words">{error}</p>
          </div>
        )}

        <div className="flex items-center justify-between gap-3 pb-2 border-b border-slate-100">
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer select-none">
            <input type="checkbox" checked={writeback} onChange={e => setWriteback(e.target.checked)} className="accent-teal-600" />
            Save generated notes in Elastic
          </label>
          <button onClick={handleReset} className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-red-400 transition-colors cursor-pointer">
            <RotateCcw size={11} />
            Reset notes
          </button>
        </div>

        {data && <WritebackStatus enabled={data.writeback_enabled} writeCounts={data.write_counts} />}
        {structured && !loading && <StatsBar structured={structured} />}

        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <EvidenceCards
              medical={structured?.medical_evidence ?? []}
              policy={structured?.policy_citations ?? []}
              loading={loading}
            />
            <MissingEvidence items={structured?.missing_evidence ?? []} loading={loading} />
            <PacketPreview structured={structured} loading={loading} />
          </div>
          <div className="lg:col-span-1">
            <TechTrace structured={structured} events={events} loading={loading} missionId={data?.mission_id ?? null} />
          </div>
        </div>

        {!loading && !data && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-24">
            <p className="text-sm font-medium text-slate-400">Choose what you want the agent to do</p>
            <p className="text-xs mt-1.5 text-slate-300">Each run searches selected case documents and Social Security rules in Elastic</p>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const [view, setView] = useState<View>('landing')
  const [selectedCase, setSelectedCase] = useState<CaseSummary | null>(null)
  const [caseLoading, setCaseLoading] = useState(false)
  const [caseError, setCaseError] = useState<string | null>(null)

  const loadExample = async () => {
    setCaseLoading(true)
    setCaseError(null)
    try {
      const res = await fetch('/api/cases/example', { method: 'POST' })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || 'Could not load example case')
      setSelectedCase(json)
      setView('documents')
    } catch (err) {
      setCaseError(err instanceof Error ? err.message : 'Could not load example case')
    } finally {
      setCaseLoading(false)
    }
  }

  const uploadPdf = async (file: File) => {
    setCaseLoading(true)
    setCaseError(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/cases/upload', { method: 'POST', body: form })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || 'Could not read this PDF')
      setSelectedCase(json)
      setView('documents')
    } catch (err) {
      setCaseError(err instanceof Error ? err.message : 'Could not read this PDF')
    } finally {
      setCaseLoading(false)
    }
  }

  return (
    <AnimatePresence mode="wait">
      {view === 'landing' ? (
        <motion.div key="landing" {...pageTransition}>
          <LandingPage
            loading={caseLoading}
            error={caseError}
            onExample={loadExample}
            onUpload={() => {
              setCaseError(null)
              setView('upload')
            }}
          />
        </motion.div>
      ) : view === 'upload' ? (
        <motion.div key="upload" {...pageTransition}>
          <UploadCase
            loading={caseLoading}
            error={caseError}
            onBack={() => setView('landing')}
            onUpload={uploadPdf}
          />
        </motion.div>
      ) : view === 'documents' ? (
        <motion.div key="documents" {...pageTransition}>
          {selectedCase ? (
            <DocumentPreview
              selectedCase={selectedCase}
              onBack={() => setView('landing')}
              onAnalyze={() => setView('app')}
            />
          ) : (
            <LandingPage loading={caseLoading} error={caseError} onExample={loadExample} onUpload={() => setView('upload')} />
          )}
        </motion.div>
      ) : (
        <motion.div key="app" {...pageTransition}>
          {selectedCase ? (
            <AppDashboard selectedCase={selectedCase} onBack={() => setView('documents')} />
          ) : (
            <LandingPage loading={caseLoading} error={caseError} onExample={loadExample} onUpload={() => setView('upload')} />
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
