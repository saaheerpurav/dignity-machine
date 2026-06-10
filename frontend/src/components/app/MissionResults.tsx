import { motion } from 'framer-motion'
import { AlertTriangle, BookOpen, ClipboardList, FileText } from 'lucide-react'
import { CopyButton } from '@/components/ui/CopyButton'
import { EvidenceCards } from './EvidenceCards'
import { MissingEvidence } from './MissingEvidence'
import { ActionPlan } from './ActionPlan'
import { CaseFactsPanel } from './CaseFactsPanel'
import { ReviewSummaryPreview } from './ReviewSummaryPreview'
import type { AgentEvent, CaseFact, StructuredResult } from '@/types/api'

interface MissionResultProps {
  caseId: string
  structured: StructuredResult | null
  mission: string | null
  loading: boolean
  saved: boolean
  facts: CaseFact[]
  onFactsSaved: (facts: CaseFact[]) => void
  onUpdateActionPlan: () => void
  onWorkspaceEvent: (event: AgentEvent) => void
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

function workspaceEvent(caseId: string, eventType: string, result: string, output: Record<string, unknown> = {}): AgentEvent {
  return {
    event_id: `ui_${eventType}_${Date.now()}`,
    case_id: caseId,
    mission_id: 'workspace',
    event_type: eventType,
    tool_name: 'case_workspace',
    index_name: 'case_actions',
    output: { result, ...output },
    created_at: new Date().toISOString(),
  }
}

function factValue(facts: CaseFact[], field: string) {
  return facts.find(fact => fact.field === field)?.value?.trim() || ''
}

function openEmailDraft(caseId: string, facts: CaseFact[], draft: string, humanReviewNote: string | undefined, placeholders: string[] | undefined, onWorkspaceEvent: (event: AgentEvent) => void) {
  const recipient = factValue(facts, 'provider_email')
  const warning = placeholders?.length ? `\n\nPlaceholder warning: ${placeholders.join(', ')}` : ''
  const body = `${draft}${humanReviewNote ? `\n\nHuman review note: ${humanReviewNote}` : ''}${warning}`
  const mailto = `mailto:${encodeURIComponent(recipient)}?subject=${encodeURIComponent('Medical records request for disability appeal')}&body=${encodeURIComponent(body)}`
  window.open(mailto, '_blank', 'noopener,noreferrer')
  onWorkspaceEvent(workspaceEvent(caseId, 'mailto_opened', 'Opened prefilled email draft', { has_recipient: !!recipient }))
  fetch(`/api/cases/${encodeURIComponent(caseId)}/actions/log`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ action_type: 'mailto_opened', payload: { has_recipient: !!recipient } }),
  }).catch(() => null)
}

export function DenialExplanationResult({ structured, loading }: Pick<MissionResultProps, 'structured' | 'loading'>) {
  if (loading || !structured) return null
  return (
    <div className="space-y-6">
      <Panel title="Denial explanation">
        {structured.denial_summary && <p className="text-sm text-slate-700 leading-relaxed">{structured.denial_summary}</p>}
        {structured.denial_reason && (
          <div className="border border-[#e8d3c1] bg-[#f5e8de] rounded-xl p-4">
            <p className="text-xs font-bold uppercase tracking-widest text-[#a85a3a] mb-1">Reason stated</p>
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

export function MissingProofResult({ caseId, structured, loading, saved, facts, onFactsSaved, onUpdateActionPlan, onWorkspaceEvent }: MissionResultProps) {
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
        caseId={caseId}
        tasks={structured.case_tasks ?? []}
        showArtifactCards={false}
        saved={saved}
        loading={false}
        onWorkspaceEvent={onWorkspaceEvent}
      />
      <CaseFactsPanel
        caseId={caseId}
        tasks={structured.case_tasks ?? []}
        facts={facts}
        onSaved={onFactsSaved}
        onUpdateActionPlan={onUpdateActionPlan}
        onWorkspaceEvent={onWorkspaceEvent}
      />
      {structured.human_review_note && <p className="text-xs text-slate-400 px-1">{structured.human_review_note}</p>}
    </div>
  )
}

export function RecordsRequestResult({ caseId, structured, loading, facts, onWorkspaceEvent }: MissionResultProps) {
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
            <div className="flex items-center gap-2">
              <div className="tooltip tooltip-bottom" data-tip="Opens a prefilled draft in your mail client. You review and send.">
                <button
                  onClick={() => openEmailDraft(caseId, facts, draft, structured.human_review_note, structured.placeholder_fields, onWorkspaceEvent)}
                  className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:border-teal-200 hover:text-teal-700 cursor-pointer"
                >
                  Open email draft
                </button>
              </div>
              <CopyButton text={draft} label="Copy request" />
            </div>
          </div>
          <pre className="p-4 text-xs text-slate-700 whitespace-pre-wrap font-mono leading-relaxed bg-slate-50">{draft}</pre>
        </div>
      )}
      {structured.human_review_note && <p className="text-xs text-slate-400">{structured.human_review_note}</p>}
    </Panel>
  )
}

export function ReviewSummaryResult({ caseId, structured, loading, saved, facts, onFactsSaved, onUpdateActionPlan, onWorkspaceEvent }: MissionResultProps) {
  if (loading || !structured) return null
  return (
    <div className="space-y-6">
      <MissingEvidence items={structured.missing_evidence ?? []} loading={false} />
      <CaseFactsPanel
        caseId={caseId}
        tasks={structured.case_tasks ?? []}
        facts={facts}
        onSaved={onFactsSaved}
        onUpdateActionPlan={onUpdateActionPlan}
        onWorkspaceEvent={onWorkspaceEvent}
      />
      <ActionPlan
        caseId={caseId}
        deadline={structured.deadline}
        tasks={structured.case_tasks ?? []}
        hasRecordsDraft={!!structured.records_request_draft}
        hasReviewSummary={!!structured.review_summary || !!structured.denial_summary}
        saved={saved}
        loading={false}
        onWorkspaceEvent={onWorkspaceEvent}
      />
      <EvidenceCards medical={[]} policy={structured.policy_citations ?? []} loading={false} />
      <ReviewSummaryPreview
        structured={structured}
        loading={false}
        recordsRequestAction={
          structured.records_request_draft ? (
            <div className="tooltip tooltip-bottom" data-tip="Opens a prefilled draft in your mail client. You review and send.">
              <button
                onClick={() => openEmailDraft(caseId, facts, structured.records_request_draft ?? '', structured.human_review_note, structured.placeholder_fields, onWorkspaceEvent)}
                className="rounded-lg border border-slate-200 bg-white px-2.5 py-1.5 text-xs font-semibold text-slate-600 hover:border-teal-200 hover:text-teal-700 cursor-pointer"
              >
                Open email draft
              </button>
            </div>
          ) : null
        }
      />
    </div>
  )
}

export function MissionResults(props: MissionResultProps) {
  const { structured, mission, loading } = props
  const activeMission = mission || structured?.mission
  if (loading) {
    return <Panel title="Working"><div className="shimmer h-20 rounded-xl" /></Panel>
  }
  if (activeMission === 'analyze_denial') return <DenialExplanationResult structured={structured} loading={loading} />
  if (activeMission === 'find_missing_evidence') return <MissingProofResult {...props} />
  if (activeMission === 'draft_records_request') return <RecordsRequestResult {...props} />
  if (activeMission === 'prepare_review_summary' || activeMission === 'prepare_packet') {
    return <ReviewSummaryResult {...props} mission={activeMission} />
  }
  return null
}
