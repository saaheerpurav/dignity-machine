import { motion } from 'framer-motion'
import { AlertTriangle, BookOpen, CheckCircle2, ClipboardList, FileSearch, ListChecks } from 'lucide-react'
import { AnimatedNumber } from '@/components/ui/AnimatedNumber'
import type { StructuredResult } from '@/types/api'

interface StatsBarProps {
  structured: StructuredResult
  mission?: string | null
}

export function StatsBar({ structured, mission }: StatsBarProps) {
  const activeMission = mission || structured.mission
  const stats = (() => {
    if (activeMission === 'analyze_denial') {
      return [
        { icon: CheckCircle2, value: structured.denial_summary ? 1 : 0, label: 'Denial read', color: 'text-rose-400 bg-rose-50' },
        { icon: BookOpen, value: structured.policy_citations?.length ?? 0, label: 'Policy checked', color: 'text-teal-400 bg-teal-50' },
        { icon: FileSearch, value: structured.evidence_mentioned?.length ?? 0, label: 'Evidence mentioned', color: 'text-sky-400 bg-sky-50' },
      ]
    }
    if (activeMission === 'find_missing_evidence') {
      const result = [
        { icon: AlertTriangle, value: structured.missing_evidence?.length ?? 0, label: 'Evidence gaps', color: 'text-amber-400 bg-amber-50' },
        { icon: ListChecks, value: structured.case_tasks?.length ?? 0, label: 'Action tasks', color: 'text-emerald-400 bg-emerald-50' },
      ]
      if (structured.policy_citations?.length) {
        result.push({ icon: BookOpen, value: structured.policy_citations.length, label: 'Policy references', color: 'text-teal-400 bg-teal-50' })
      }
      return result
    }
    if (activeMission === 'draft_records_request') {
      return [
        { icon: FileSearch, value: structured.records_needed?.length ?? 0, label: 'Records needed', color: 'text-sky-400 bg-sky-50' },
        { icon: ClipboardList, value: structured.placeholder_fields?.length ?? 0, label: 'Placeholder fields', color: 'text-amber-400 bg-amber-50' },
        { icon: CheckCircle2, value: structured.records_request_draft ? 1 : 0, label: 'Draft ready', color: 'text-emerald-400 bg-emerald-50' },
      ]
    }
    return [
      { icon: BookOpen, value: structured.policy_citations?.length ?? 0, label: 'Policy citations', color: 'text-teal-400 bg-teal-50' },
      { icon: AlertTriangle, value: structured.missing_evidence?.length ?? 0, label: 'Evidence gaps', color: 'text-amber-400 bg-amber-50' },
      { icon: ListChecks, value: structured.case_tasks?.length ?? 0, label: 'Action tasks', color: 'text-emerald-400 bg-emerald-50' },
      {
        icon: FileSearch,
        value: [structured.denial_summary, structured.records_request_draft, structured.review_summary].filter(Boolean).length,
        label: 'Review sections',
        color: 'text-sky-400 bg-sky-50',
      },
    ]
  })()

  if (stats.length === 0) return null

  return (
    <motion.div
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] as const }}
      className="grid grid-cols-2 sm:grid-cols-4 gap-3"
    >
      {stats.map((stat, i) => (
        <motion.div
          key={stat.label}
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.35, delay: i * 0.06, ease: [0.25, 0.46, 0.45, 0.94] as const }}
          className="bg-white border border-slate-100 rounded-2xl p-4 flex items-center gap-3"
        >
          <div className={`w-10 h-10 rounded-xl flex items-center justify-center shrink-0 ${stat.color}`}>
            <stat.icon size={17} />
          </div>
          <div className="min-w-0">
            <div className="text-2xl font-bold text-slate-800 leading-none tabular-nums">
              <AnimatedNumber value={stat.value} />
            </div>
            <p className="text-xs text-slate-400 mt-1 truncate">{stat.label}</p>
          </div>
        </motion.div>
      ))}
    </motion.div>
  )
}
