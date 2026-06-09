import * as ScrollArea from '@radix-ui/react-scroll-area'
import { AnimatePresence, motion } from 'framer-motion'
import { Shimmer } from '@/components/ui/Shimmer'
import { CheckCircle2 } from 'lucide-react'
import type { AgentEvent, StructuredResult } from '@/types/api'

interface TechTraceProps {
  structured: StructuredResult | null
  events: AgentEvent[]
  loading: boolean
}

interface TraceEvent {
  key: string
  label: string
  result: string
}

function friendlyTraceLabel(toolName?: string, eventType?: string) {
  if (toolName === 'case_workspace') {
    if (eventType === 'fact_saved') return 'Saved case details'
    if (eventType === 'task_status_updated') return 'Updated task'
    if (eventType === 'google_calendar_opened') return 'Opened calendar draft'
    if (eventType === 'mailto_opened') return 'Opened email draft'
    return 'Updated workspace'
  }
  if (toolName === 'action_plan') {
    if (eventType === 'case_text_searched') return 'Read selected denial'
    if (eventType === 'case_facts_loaded') return 'Used saved details'
    if (eventType === 'policy_searched') return 'Checked Social Security rules'
    if (eventType === 'evidence_gap_created') return 'Found missing proof'
    if (eventType === 'deadline_created') return 'Calculated possible deadline'
    if (eventType === 'deadline_needed') return 'Asked for notice date'
    if (eventType === 'case_tasks_created') return 'Created action tasks'
    if (eventType === 'records_request_drafted') return 'Drafted records request'
    if (eventType === 'review_summary_created') return 'Created review summary'
    if (eventType === 'action_plan_saved') return 'Saved action plan'
    return 'Updated action plan'
  }
  if (toolName?.includes('case_documents')) return 'Read case documents'
  if (toolName?.includes('ssa_policy')) return 'Checked Social Security rules'
  if (toolName?.includes('ssa_forms')) return 'Checked appeal forms'
  if (toolName?.includes('advocate')) return 'Checked helper details'
  if (eventType === 'agent_final_response') return 'Finished review'
  if (eventType === 'tool_call') return 'Started a review step'
  if (eventType === 'tool_result') return 'Completed a review step'
  return 'Review step'
}

function buildEvents(s: StructuredResult): TraceEvent[] {
  const events: TraceEvent[] = []
  s.medical_evidence?.forEach(e =>
    events.push({ key: `medical-${e.doc_id}`, label: 'Read case documents', result: e.title || 'Found a relevant case document' })
  )
  s.policy_citations?.forEach(c =>
    events.push({ key: `policy-${c.doc_id ?? c.title}`, label: 'Checked Social Security rules', result: c.title })
  )
  if (s.missing_evidence?.length) {
    events.push({ key: 'missing-evidence', label: 'Found missing proof', result: `${s.missing_evidence.length} possible gap${s.missing_evidence.length === 1 ? '' : 's'} identified` })
  }
  if (s.advocate_alert_draft) {
    events.push({ key: 'advocate-contact', label: 'Prepared helper note', result: 'Draft ready for review' })
  }
  return events
}

function eventsFromStream(events: AgentEvent[]): TraceEvent[] {
  return events
    .filter(ev => ev.event_type === 'tool_call' || ev.event_type === 'tool_result' || ev.event_type === 'agent_final_response' || ev.tool_name === 'action_plan' || ev.tool_name === 'case_workspace')
    .map((ev, index) => ({
      key: ev.event_id || `${ev.event_type}-${ev.tool_name}-${index}`,
      label: friendlyTraceLabel(ev.tool_name, ev.event_type),
      result:
        ev.tool_name === 'action_plan'
          ? String((ev.output as { result?: unknown } | undefined)?.result || ev.event_type || 'completed')
          : ev.event_type === 'tool_call'
            ? 'called'
            : ev.event_type === 'tool_result'
              ? 'returned'
              : 'Finished review',
    }))
}

export function TechTrace({ structured, events: streamedEvents, loading }: TechTraceProps) {
  const events = streamedEvents.length > 0 ? eventsFromStream(streamedEvents) : structured ? buildEvents(structured) : []
  const visibleEvents = [...events].reverse()
  const waitingForFirstEvent = loading && events.length === 0

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden flex flex-col">
      <div className="px-5 py-4 border-b border-slate-100">
        <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Review activity</p>
      </div>

      <ScrollArea.Root className="max-h-[720px] overflow-hidden">
        <ScrollArea.Viewport className="max-h-[720px]">
          <div className="p-4 space-y-3">
            {waitingForFirstEvent && <div className="space-y-4 pt-1"><Shimmer lines={2} /><Shimmer lines={2} /></div>}

            {!loading && events.length === 0 && (
              <p className="text-xs text-slate-300 pt-1">Choose an action to see what the agent searched.</p>
            )}

            <AnimatePresence initial={false}>
              {visibleEvents.map((ev, i) => (
                <motion.div
                  key={ev.key}
                  initial={{ opacity: 0, x: 18, y: 6 }}
                  animate={{ opacity: 1, x: 0, y: 0 }}
                  exit={{ opacity: 0, x: -8 }}
                  transition={{ duration: 0.24, ease: [0.25, 0.46, 0.45, 0.94] as const }}
                  className="space-y-1.5"
                >
                  <div className="flex items-center gap-2">
                    <CheckCircle2 size={12} className="text-teal-500 shrink-0" />
                    <span className="text-[11px] font-bold text-slate-700">{ev.label}</span>
                  </div>
                  <p className="text-[11px] text-slate-600 pl-4 leading-relaxed break-words">{ev.result}</p>
                  {i < visibleEvents.length - 1 && <div className="border-t border-slate-100 mt-2" />}
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        </ScrollArea.Viewport>
        <ScrollArea.Scrollbar className="flex select-none p-0.5 w-1.5 bg-transparent" orientation="vertical">
          <ScrollArea.Thumb className="flex-1 bg-slate-200 rounded-full" />
        </ScrollArea.Scrollbar>
      </ScrollArea.Root>
    </div>
  )
}
