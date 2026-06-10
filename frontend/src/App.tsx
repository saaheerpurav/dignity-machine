import { useEffect, useState } from 'react'
import { AnimatePresence, motion } from 'framer-motion'
import {
  ModalRoot,
  ModalBackdrop,
  ModalContainer,
  ModalDialog,
  ModalHeader,
  ModalHeading,
  ModalBody,
  ModalFooter,
  useOverlayState,
} from '@heroui/react'
import { RotateCcw } from 'lucide-react'
import { useConfig } from '@/hooks/useConfig'
import { useAnalyze } from '@/hooks/useAnalyze'
import { LandingPage } from '@/components/landing/LandingPage'
import { DocumentPreview } from '@/components/landing/DocumentPreview'
import { UploadCase } from '@/components/landing/UploadCase'
import { CaseHeader } from '@/components/app/CaseHeader'
import { MissionButtons } from '@/components/app/MissionButtons'
import { MissionTimeline } from '@/components/app/MissionTimeline'
import { MissionResults } from '@/components/app/MissionResults'
import { TechTrace } from '@/components/app/TechTrace'
import { WritebackStatus } from '@/components/app/WritebackStatus'
import { StatsBar } from '@/components/app/StatsBar'
import { CaseBanner } from '@/components/app/CaseBanner'
import type { AgentEvent, CaseFact, CaseSummary } from '@/types/api'

type View = 'landing' | 'upload' | 'documents' | 'app'
const SELECTED_CASE_KEY = 'dignity:selected_case_id'

const pageTransition = {
  initial: { opacity: 0, y: 16 },
  animate: { opacity: 1, y: 0 },
  exit: { opacity: 0, y: -8 },
  transition: { duration: 0.35, ease: 'easeInOut' as const },
}

function selectedCaseFromUrl() {
  return new URLSearchParams(window.location.search).get('case')?.trim() || null
}

function rememberCase(selectedCase: CaseSummary) {
  localStorage.setItem(SELECTED_CASE_KEY, selectedCase.case_id)
  window.history.replaceState(null, '', `?case=${encodeURIComponent(selectedCase.case_id)}`)
}

function clearRememberedCase() {
  localStorage.removeItem(SELECTED_CASE_KEY)
  window.history.replaceState(null, '', window.location.pathname)
}

function AppDashboard({ selectedCase, onBack }: { selectedCase: CaseSummary; onBack: () => void }) {
  const { config, loading: configLoading } = useConfig()
  const { data, loading, error, events, statusMessages, run, reset } = useAnalyze()
  const [activeMission, setActiveMission] = useState<string | null>(null)
  const writeback = false
  const [facts, setFacts] = useState<CaseFact[]>([])
  const [workspaceEvents, setWorkspaceEvents] = useState<AgentEvent[]>([])
  const resetDialog = useOverlayState()
  const [resetting, setResetting] = useState(false)

  useEffect(() => {
    let cancelled = false
    fetch(`/api/cases/${encodeURIComponent(selectedCase.case_id)}/facts`)
      .then(async res => {
        const json = await res.json().catch(() => null)
        if (!res.ok) throw new Error(json?.detail || 'Could not load case facts')
        return json.facts ?? []
      })
      .then(nextFacts => {
        if (!cancelled) setFacts(nextFacts)
      })
      .catch(() => {
        if (!cancelled) setFacts([])
      })
    return () => {
      cancelled = true
    }
  }, [selectedCase.case_id])

  const handleMission = (id: string) => {
    setActiveMission(id)
    run(selectedCase.case_id, id, writeback)
  }

  const updateActionPlan = () => {
    setActiveMission('prepare_review_summary')
    run(selectedCase.case_id, 'prepare_review_summary', writeback)
  }

  const appendWorkspaceEvent = (event: AgentEvent) => {
    setWorkspaceEvents(prev => [...prev, event])
  }

  const confirmReset = async () => {
    setResetting(true)
    try {
      const res = await fetch(`/api/cases/${encodeURIComponent(selectedCase.case_id)}/writeback/reset`, { method: 'POST' })
      if (res.ok) {
        reset()
        setActiveMission(null)
        resetDialog.close()
      }
    } finally {
      setResetting(false)
    }
  }

  const structured = data?.structured ?? null
  const resultMission = data?.mission ?? activeMission
  const saved = !!data?.writeback_enabled && Object.values(data.write_counts ?? {}).some(count => count > 0)

  return (
    <div className="min-h-screen bg-slate-50">
      <CaseHeader title={selectedCase.title} onBack={onBack} />

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

        <div className="flex items-center justify-end gap-3 pb-2 border-b border-slate-100">
          <button onClick={resetDialog.open} className="flex items-center gap-1.5 text-xs text-slate-400 hover:text-[#9c3a2a] transition-colors cursor-pointer">
            <RotateCcw size={11} />
            Reset action plan
          </button>
        </div>

        <ModalRoot state={resetDialog}>
          <ModalBackdrop variant="blur">
            <ModalContainer placement="center">
              <ModalDialog className="bg-[#fbf8f1] border border-[#e5dcc9] rounded-3xl p-6 max-w-md">
                <ModalHeader>
                  <ModalHeading className="text-[#1f1b16] text-lg font-semibold">
                    Reset your action plan?
                  </ModalHeading>
                </ModalHeader>
                <ModalBody className="text-sm text-[#5a5145] leading-relaxed mt-2">
                  This clears the saved action plan, tasks, and any drafts the agent generated for this case.
                  Your uploaded denial and case workspace stay intact.
                </ModalBody>
                <ModalFooter className="mt-5 flex gap-2 justify-end">
                  <button
                    onClick={resetDialog.close}
                    disabled={resetting}
                    className="px-4 py-2 rounded-full text-sm font-medium text-[#1f1b16] hover:bg-[#f4ead3] transition-colors cursor-pointer disabled:opacity-50"
                  >
                    Keep it
                  </button>
                  <button
                    onClick={confirmReset}
                    disabled={resetting}
                    className="px-4 py-2 rounded-full text-sm font-medium bg-[#9c3a2a] hover:bg-[#7d2e21] text-[#f6f1e8] transition-colors cursor-pointer disabled:opacity-60 disabled:cursor-wait"
                  >
                    {resetting ? 'Resetting…' : 'Yes, reset'}
                  </button>
                </ModalFooter>
              </ModalDialog>
            </ModalContainer>
          </ModalBackdrop>
        </ModalRoot>

        {data && <WritebackStatus enabled={saved} />}
        {structured && !loading && <StatsBar mission={resultMission} structured={structured} />}

        <div className="grid lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            <MissionResults
              caseId={selectedCase.case_id}
              structured={structured}
              mission={resultMission}
              loading={loading}
              saved={saved}
              facts={[...facts, ...(structured?.case_facts ?? [])]}
              onFactsSaved={setFacts}
              onUpdateActionPlan={updateActionPlan}
              onWorkspaceEvent={appendWorkspaceEvent}
            />
          </div>
          <div className="lg:col-span-1">
            <TechTrace structured={structured} events={[...events, ...workspaceEvents]} loading={loading} />
          </div>
        </div>

        {!loading && !data && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="text-center py-24">
            <p className="text-sm font-medium text-slate-400">Choose what you want the agent to do</p>
            <p className="text-xs mt-1.5 text-slate-300">Each run reviews the selected denial and relevant Social Security rules</p>
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
  const [restoreLoading, setRestoreLoading] = useState(true)

  useEffect(() => {
    const restoreCaseId = selectedCaseFromUrl() || localStorage.getItem(SELECTED_CASE_KEY)
    if (!restoreCaseId) {
      setRestoreLoading(false)
      return
    }

    let cancelled = false
    fetch(`/api/cases/${encodeURIComponent(restoreCaseId)}`)
      .then(async res => {
        const json = await res.json().catch(() => null)
        if (!res.ok) throw new Error(json?.detail || 'Could not restore case')
        return json as CaseSummary
      })
      .then(restoredCase => {
        if (cancelled) return
        setSelectedCase(restoredCase)
        rememberCase(restoredCase)
        setView('documents')
      })
      .catch(() => {
        if (cancelled) return
        clearRememberedCase()
        setSelectedCase(null)
        setView('landing')
      })
      .finally(() => {
        if (!cancelled) setRestoreLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const startOver = () => {
    clearRememberedCase()
    setSelectedCase(null)
    setCaseError(null)
    setView('landing')
  }

  const beginUpload = () => {
    clearRememberedCase()
    setSelectedCase(null)
    setCaseError(null)
    setView('upload')
  }

  const loadExample = async () => {
    setCaseLoading(true)
    setCaseError(null)
    try {
      const res = await fetch('/api/cases/example', { method: 'POST' })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || 'Could not load example case')
      setSelectedCase(json)
      rememberCase(json)
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
    clearRememberedCase()
    setSelectedCase(null)
    try {
      const form = new FormData()
      form.append('file', file)
      const res = await fetch('/api/cases/upload', { method: 'POST', body: form })
      const json = await res.json()
      if (!res.ok) throw new Error(json.detail || 'Could not read this PDF')
      setSelectedCase(json)
      rememberCase(json)
      setView('documents')
    } catch (err) {
      setCaseError(err instanceof Error ? err.message : 'Could not read this PDF')
    } finally {
      setCaseLoading(false)
    }
  }

  if (restoreLoading) {
    return (
      <div className="min-h-screen bg-[#f6f1e8] flex items-center justify-center">
        <div className="space-y-3 text-center">
          <div className="mx-auto w-10 h-10 rounded-xl bg-[#eef3eb] border border-[#cddccd] animate-pulse" />
          <p className="text-sm font-medium text-slate-500">Restoring your case</p>
        </div>
      </div>
    )
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
              beginUpload()
            }}
          />
        </motion.div>
      ) : view === 'upload' ? (
        <motion.div key="upload" {...pageTransition}>
          <UploadCase
            loading={caseLoading}
            error={caseError}
            onBack={startOver}
            onUpload={uploadPdf}
          />
        </motion.div>
      ) : view === 'documents' ? (
        <motion.div key="documents" {...pageTransition}>
          {selectedCase ? (
            <DocumentPreview
              selectedCase={selectedCase}
              onBack={startOver}
              onAnalyze={() => setView('app')}
            />
          ) : (
            <LandingPage loading={caseLoading} error={caseError} onExample={loadExample} onUpload={beginUpload} />
          )}
        </motion.div>
      ) : (
        <motion.div key="app" {...pageTransition}>
          {selectedCase ? (
            <AppDashboard selectedCase={selectedCase} onBack={() => setView('documents')} />
          ) : (
            <LandingPage loading={caseLoading} error={caseError} onExample={loadExample} onUpload={beginUpload} />
          )}
        </motion.div>
      )}
    </AnimatePresence>
  )
}
