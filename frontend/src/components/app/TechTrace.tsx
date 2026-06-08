import * as ScrollArea from '@radix-ui/react-scroll-area'
import { AnimatePresence, motion } from 'framer-motion'
import { Shimmer } from '@/components/ui/Shimmer'
import { Database, Search } from 'lucide-react'
import type { AgentEvent, StructuredResult } from '@/types/api'

interface TechTraceProps {
  structured: StructuredResult | null
  events: AgentEvent[]
  loading: boolean
  missionId: string | null
}

interface TraceEvent {
  key: string
  tool: string
  index: string
  result: string
}

function buildEvents(s: StructuredResult): TraceEvent[] {
  const events: TraceEvent[] = []
  s.medical_evidence?.forEach(e =>
    events.push({ key: `medical-${e.doc_id}`, tool: 'search_case_documents', index: e.index ?? 'case_documents', result: e.doc_id })
  )
  s.policy_citations?.forEach(c =>
    events.push({ key: `policy-${c.doc_id ?? c.title}`, tool: 'search_ssa_policy', index: 'ssa_policy', result: c.title })
  )
  if (s.missing_evidence?.length) {
    events.push({ key: 'missing-evidence', tool: 'search_ssa_forms', index: 'ssa_forms', result: `${s.missing_evidence.length} gaps identified` })
  }
  if (s.advocate_alert_draft) {
    events.push({ key: 'advocate-contact', tool: 'get_advocate_contact', index: 'advocate_contacts', result: 'contact retrieved' })
  }
  return events
}

function eventsFromStream(events: AgentEvent[]): TraceEvent[] {
  return events
    .filter(ev => ev.event_type === 'tool_call' || ev.event_type === 'tool_result' || ev.event_type === 'agent_final_response' || ev.tool_name === 'action_plan')
    .map((ev, index) => ({
      key: ev.event_id || `${ev.event_type}-${ev.tool_name}-${index}`,
      tool: ev.tool_name === 'action_plan' ? (ev.event_type || 'action_event') : (ev.tool_name || ev.event_type || 'agent_event'),
      index: ev.index_name || '',
      result:
        ev.tool_name === 'action_plan'
          ? String((ev.output as { result?: unknown } | undefined)?.result || ev.event_type || 'completed')
          : ev.event_type === 'tool_call'
            ? 'called'
            : ev.event_type === 'tool_result'
              ? 'returned'
              : 'final response',
    }))
}

export function TechTrace({ structured, events: streamedEvents, loading, missionId }: TechTraceProps) {
  const events = streamedEvents.length > 0 ? eventsFromStream(streamedEvents) : structured ? buildEvents(structured) : []
  const visibleEvents = [...events].reverse()
  const waitingForFirstEvent = loading && events.length === 0

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden flex flex-col">
      <div className="px-5 py-4 border-b border-slate-100">
        <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Agent trace</p>
        {missionId && (
          <p className="text-[10px] font-mono text-slate-300 mt-1 truncate">{missionId}</p>
        )}
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
                    <Search size={11} className="text-teal-500 shrink-0" />
                    <span className="text-[11px] font-bold text-slate-700 font-mono">{ev.tool}</span>
                  </div>
                  <div className="flex items-center gap-2 pl-4">
                    <Database size={9} className="text-slate-300 shrink-0" />
                    <span className="text-[10px] text-slate-400 font-mono">{ev.index}</span>
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
