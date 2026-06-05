import * as ScrollArea from '@radix-ui/react-scroll-area'
import { Shimmer } from '@/components/ui/Shimmer'
import { Database, Search } from 'lucide-react'
import type { StructuredResult } from '@/types/api'

interface TechTraceProps {
  structured: StructuredResult | null
  loading: boolean
  missionId: string | null
}

interface TraceEvent {
  tool: string
  index: string
  result: string
}

function buildEvents(s: StructuredResult): TraceEvent[] {
  const events: TraceEvent[] = []
  s.medical_evidence?.forEach(e =>
    events.push({ tool: 'search_case_documents', index: e.index ?? 'case_documents', result: e.doc_id })
  )
  s.policy_citations?.forEach(c =>
    events.push({ tool: 'search_ssa_policy', index: 'ssa_policy', result: c.title })
  )
  if (s.missing_evidence?.length) {
    events.push({ tool: 'search_ssa_forms', index: 'ssa_forms', result: `${s.missing_evidence.length} gaps identified` })
  }
  if (s.advocate_alert_draft) {
    events.push({ tool: 'get_advocate_contact', index: 'advocate_contacts', result: 'contact retrieved' })
  }
  return events
}

export function TechTrace({ structured, loading, missionId }: TechTraceProps) {
  const events = structured ? buildEvents(structured) : []

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden flex flex-col h-full">
      <div className="px-5 py-4 border-b border-slate-100">
        <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Agent trace</p>
        {missionId && (
          <p className="text-[10px] font-mono text-slate-300 mt-1 truncate">{missionId}</p>
        )}
      </div>

      <ScrollArea.Root className="flex-1 overflow-hidden">
        <ScrollArea.Viewport className="h-full max-h-[520px]">
          <div className="p-4 space-y-3">
            {loading && <div className="space-y-4 pt-1"><Shimmer lines={2} /><Shimmer lines={2} /><Shimmer lines={2} /></div>}

            {!loading && events.length === 0 && (
              <p className="text-xs text-slate-300 pt-1">Choose an action to see what the agent searched.</p>
            )}

            {events.map((ev, i) => (
              <div key={i} className="space-y-1.5">
                <div className="flex items-center gap-2">
                  <Search size={11} className="text-teal-500 shrink-0" />
                  <span className="text-[11px] font-bold text-slate-700 font-mono">{ev.tool}</span>
                </div>
                <div className="flex items-center gap-2 pl-4">
                  <Database size={9} className="text-slate-300 shrink-0" />
                  <span className="text-[10px] text-slate-400 font-mono">{ev.index}</span>
                </div>
                <p className="text-[11px] text-slate-500 pl-4 leading-relaxed truncate">{ev.result}</p>
                {i < events.length - 1 && <div className="border-t border-slate-100 mt-2" />}
              </div>
            ))}
          </div>
        </ScrollArea.Viewport>
        <ScrollArea.Scrollbar className="flex select-none p-0.5 w-1.5 bg-transparent" orientation="vertical">
          <ScrollArea.Thumb className="flex-1 bg-slate-200 rounded-full" />
        </ScrollArea.Scrollbar>
      </ScrollArea.Root>
    </div>
  )
}
