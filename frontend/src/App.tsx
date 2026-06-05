import { useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import { RotateCcw } from 'lucide-react'
import { useConfig } from '@/hooks/useConfig'
import { useAnalyze } from '@/hooks/useAnalyze'
import { LandingPage } from '@/components/landing/LandingPage'
import { DocumentPreview } from '@/components/landing/DocumentPreview'
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

type View = 'landing' | 'documents' | 'app'

const pageTransition = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.35, ease: 'easeInOut' as const },
}

function AppDashboard({ onBack }: { onBack: () => void }) {
  const { config, loading: configLoading } = useConfig()
  const { data, loading, run } = useAnalyze()
  const [activeMission, setActiveMission] = useState<string | null>(null)
  const [writeback, setWriteback] = useState(false)

  const handleMission = (id: string) => {
    setActiveMission(id)
    run(id, writeback)
  }

  const handleReset = async () => {
    if (!confirm('Delete generated demo notes from Elastic?')) return
    await fetch('/api/reset-demo-writeback', { method: 'POST' })
  }

  const structured = data?.structured ?? null

  return (
    <div className="min-h-screen bg-slate-50">
      <CaseHeader caseId={config?.case_id ?? '...'} onBack={onBack} />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8 space-y-6">
        <CaseBanner />

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

        <div className="flex items-center justify-between gap-3 pb-2 border-b border-slate-100">
          <label className="flex items-center gap-2 text-xs text-slate-400 cursor-pointer select-none">
            <input type="checkbox" checked={writeback} onChange={e => setWriteback(e.target.checked)} className="accent-teal-600" />
            Save generated notes in Elastic
          </label>
          <button onClick={handleReset} className="flex items-center gap-1.5 text-xs text-slate-300 hover:text-red-400 transition-colors cursor-pointer">
            <RotateCcw size={11} />
            Reset demo
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
            <TechTrace structured={structured} loading={loading} missionId={data?.mission_id ?? null} />
          </div>
        </div>

        {!loading && !data && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-24">
            <p className="text-sm font-medium text-slate-400">Choose what you want the agent to do</p>
            <p className="text-xs mt-1.5 text-slate-300">Each run searches Maria's documents and Social Security rules in Elastic</p>
          </motion.div>
        )}
      </div>
    </div>
  )
}

export default function App() {
  const [view, setView] = useState<View>('landing')

  return (
    <AnimatePresence mode="wait">
      {view === 'landing' ? (
        <motion.div key="landing" {...pageTransition}>
          <LandingPage onEnter={() => setView('documents')} />
        </motion.div>
      ) : view === 'documents' ? (
        <motion.div key="documents" {...pageTransition}>
          <DocumentPreview onBack={() => setView('landing')} onAnalyze={() => setView('app')} />
        </motion.div>
      ) : (
        <motion.div key="app" {...pageTransition}>
          <AppDashboard onBack={() => setView('documents')} />
        </motion.div>
      )}
    </AnimatePresence>
  )
}
