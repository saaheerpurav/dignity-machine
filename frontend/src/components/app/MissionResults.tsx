import { motion } from 'framer-motion'
import { AlertTriangle, BookOpen, ClipboardList, FileText } from 'lucide-react'
import { CopyButton } from '@/components/ui/CopyButton'
import { EvidenceCards } from './EvidenceCards'
import { MissingEvidence } from './MissingEvidence'
import { ActionPlan } from './ActionPlan'
import { ReviewSummaryPreview } from './ReviewSummaryPreview'
import type { StructuredResult } from '@/types/api'

interface MissionResultProps {
  structured: StructuredResult | null
  mission: string | null
  loading: boolean
  saved: boolean
}

function Panel({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] as const }}
      className="bg-white border border-slate-200 rounded-2xl overflow-hidden"
    >
      <div className="px-6 py-4 border-b border-slate-100">
        <p className="text-xs font-bold uppercase tracking-widest text-slate-400">{title}</p>
      </div>
      <div className="p-5 space-y-4">{children}</div>
    </motion.section>
  )
}

export function DenialExplanationResult({ structured, loading }: Pick<MissionResultProps, 'structured' | 'loading'>) {
  if (loading || !structured) return null
  return (
    <div className="space-y-6">
      <Panel title="Denial explanation">
        {structured.denial_summary && <p className="text-sm text-slate-700 leading-relaxed">{structured.denial_summary}</p>}
        {structured.denial_reason && (
          <div className="border border-rose-100 bg-rose-50 rounded-xl p-4">
            <p className="text-xs font-bold uppercase tracking-widest text-rose-400 mb-1">Reason stated</p>
            <p className="text-sm text-slate-700 leading-relaxed">{structured.denial_reason}</p>
          </div>
        )}
        {structured.ssa_explanation && (
          <div className="border border-teal-100 bg-teal-50 rounded-xl p-4">
            <p className="text-xs font-bold uppercase tracking-widest text-teal-500 mb-1">SSA explanation</p>
            <p className="text-sm text-slate-700 leading-relaxed">{structured.ssa_explanation}</p>
          </div>
        )}
        {!!structured.evidence_mentioned?.length && (
          <div>
            <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-2">Evidence mentioned</p>
            <ul className="space-y-1.5">
              {structured.evidence_mentioned.map(item => (
                <li key={item} className="text-sm text-slate-600 flex gap-2">
                  <BookOpen size={14} className="text-slate-300 shrink-0 mt-0.5" />
                  {item}
                </li>
              ))}
            </ul>
          </div>
        )}
        {structured.human_review_note && <p className="text-xs text-slate-400">{structured.human_review_note}</p>}
      </Panel>
      <EvidenceCards medical={[]} policy={structured.policy_citations ?? []} loading={false} />
    </div>
  )
}

export function MissingProofResult({ structured, loading, saved }: Pick<MissionResultProps, 'structured' | 'loading' | 'saved'>) {
  if (loading || !structured) return null
  return (
    <div className="space-y-6">
      {structured.case_context && (
        <Panel title="Case context">
          <p className="text-sm text-slate-700 leading-relaxed">{structured.case_context}</p>
        </Panel>
      )}
      <MissingEvidence items={structured.missing_evidence ?? []} loading={false} />
      <ActionPlan
        tasks={structured.case_tasks ?? []}
        showArtifactCards={false}
        saved={saved}
        loading={false}
      />
      {structured.human_review_note && <p className="text-xs text-slate-400 px-1">{structured.human_review_note}</p>}
    </div>
  )
}

export function RecordsRequestResult({ structured, loading }: Pick<MissionResultProps, 'structured' | 'loading'>) {
  if (loading || !structured) return null
  const draft = structured.records_request_draft ?? ''
  return (
    <Panel title="Doctor records request">
      {structured.request_context && <p className="text-sm text-slate-700 leading-relaxed">{structured.request_context}</p>}
      {!!structured.records_needed?.length && (
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-slate-400 mb-2">Records needed</p>
          <ul className="space-y-1.5">
            {structured.records_needed.map(item => (
              <li key={item} className="text-sm text-slate-600 flex gap-2">
                <FileText size={14} className="text-sky-400 shrink-0 mt-0.5" />
                {item}
              </li>
            ))}
          </ul>
        </div>
      )}
      {!!structured.placeholder_fields?.length && (
        <div className="border border-amber-100 bg-amber-50 rounded-xl p-4">
          <div className="flex items-start gap-2">
            <AlertTriangle size={15} className="text-amber-500 shrink-0 mt-0.5" />
            <div>
              <p className="text-sm font-semibold text-amber-800">Some fields are placeholders because they were not present in the uploaded denial.</p>
              <div className="flex flex-wrap gap-1.5 mt-3">
                {structured.placeholder_fields.map(field => (
                  <span key={field} className="text-[11px] font-mono text-amber-700 bg-white border border-amber-100 rounded px-2 py-1">
                    {field}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>
      )}
      {draft && (
        <div className="border border-slate-200 rounded-xl overflow-hidden">
          <div className="px-4 py-3 border-b border-slate-100 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <ClipboardList size={14} className="text-teal-500" />
              <p className="text-sm font-semibold text-slate-800">Request draft</p>
            </div>
            <CopyButton text={draft} label="Copy request" />
          </div>
          <pre className="p-4 text-xs text-slate-700 whitespace-pre-wrap font-mono leading-relaxed bg-slate-50">{draft}</pre>
        </div>
      )}
      {structured.human_review_note && <p className="text-xs text-slate-400">{structured.human_review_note}</p>}
    </Panel>
  )
}

export function ReviewSummaryResult({ structured, loading, saved }: MissionResultProps) {
  if (loading || !structured) return null
  return (
    <div className="space-y-6">
      <MissingEvidence items={structured.missing_evidence ?? []} loading={false} />
      <ActionPlan
        deadline={structured.deadline}
        tasks={structured.case_tasks ?? []}
        hasRecordsDraft={!!structured.records_request_draft}
        hasReviewSummary={!!structured.review_summary || !!structured.denial_summary}
        saved={saved}
        loading={false}
      />
      <EvidenceCards medical={[]} policy={structured.policy_citations ?? []} loading={false} />
      <ReviewSummaryPreview structured={structured} loading={false} />
    </div>
  )
}

export function MissionResults({ structured, mission, loading, saved }: MissionResultProps) {
  const activeMission = mission || structured?.mission
  if (loading) {
    return <Panel title="Working"><div className="shimmer h-20 rounded-xl" /></Panel>
  }
  if (activeMission === 'analyze_denial') return <DenialExplanationResult structured={structured} loading={loading} />
  if (activeMission === 'find_missing_evidence') return <MissingProofResult structured={structured} loading={loading} saved={saved} />
  if (activeMission === 'draft_records_request') return <RecordsRequestResult structured={structured} loading={loading} />
  if (activeMission === 'prepare_review_summary' || activeMission === 'prepare_packet') {
    return <ReviewSummaryResult structured={structured} mission={activeMission} loading={loading} saved={saved} />
  }
  return null
}
