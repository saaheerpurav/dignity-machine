import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import { Check, RefreshCw, Save } from 'lucide-react'
import type { AgentEvent, CaseFact, CaseTask, CaseTaskType } from '@/types/api'

interface CaseFactsPanelProps {
  caseId: string
  tasks: CaseTask[]
  facts: CaseFact[]
  onSaved: (facts: CaseFact[]) => void
  onUpdateActionPlan: () => void
  onWorkspaceEvent: (event: AgentEvent) => void
}

const FIELD_BY_TASK: Partial<Record<CaseTaskType, { field: string; label: string; input: 'date' | 'text' | 'textarea' | 'select' }>> = {
  missing_notice_date: { field: 'notice_date', label: 'Notice date', input: 'date' },
  missing_condition: { field: 'main_condition', label: 'Main condition', input: 'text' },
  missing_appeal_stage: { field: 'appeal_stage', label: 'Appeal stage', input: 'select' },
  missing_provider: { field: 'provider_name', label: 'Provider or clinic', input: 'text' },
  missing_denial_reason: { field: 'denial_reason', label: 'Denial reason', input: 'textarea' },
}

function eventFor(caseId: string, eventType: string, result: string, output: Record<string, unknown> = {}): AgentEvent {
  return {
    event_id: `ui_${eventType}_${Date.now()}`,
    case_id: caseId,
    mission_id: 'workspace',
    event_type: eventType,
    tool_name: 'case_workspace',
    index_name: eventType === 'fact_saved' ? 'case_facts' : 'case_actions',
    output: { result, ...output },
    created_at: new Date().toISOString(),
  }
}

export function CaseFactsPanel({ caseId, tasks, facts, onSaved, onUpdateActionPlan, onWorkspaceEvent }: CaseFactsPanelProps) {
  const missingInfoTasks = useMemo(
    () => tasks.filter(task => FIELD_BY_TASK[task.task_type]),
    [tasks],
  )
  const factValues = useMemo(
    () => Object.fromEntries(facts.map(fact => [fact.field, fact.value])),
    [facts],
  )
  const [values, setValues] = useState<Record<string, string>>({})
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState<string | null>(null)

  useEffect(() => {
    setValues(prev => ({ ...factValues, ...prev }))
  }, [factValues])

  if (missingInfoTasks.length === 0) return null

  const fields = missingInfoTasks
    .map(task => ({ task, meta: FIELD_BY_TASK[task.task_type] }))
    .filter((item): item is { task: CaseTask; meta: NonNullable<typeof item.meta> } => !!item.meta)

  const saveFacts = async () => {
    const payloadFacts = fields
      .map(({ meta }) => ({
        field: meta.field,
        label: meta.label,
        value: (values[meta.field] || '').trim(),
      }))
      .filter(fact => fact.value)

    if (payloadFacts.length === 0) {
      setMessage('Enter at least one detail before saving.')
      return
    }

    setSaving(true)
    setMessage(null)
    try {
      const res = await fetch(`/api/cases/${encodeURIComponent(caseId)}/facts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ facts: payloadFacts }),
      })
      const json = await res.json().catch(() => null)
      if (!res.ok) throw new Error(json?.detail || 'Could not save facts')
      onSaved(json.facts ?? [])
      onWorkspaceEvent(eventFor(caseId, 'fact_saved', 'Saved facts to Elastic', { fields: payloadFacts.map(fact => fact.field) }))

      await Promise.all(fields
        .filter(({ meta }) => payloadFacts.some(fact => fact.field === meta.field))
        .map(({ task, meta }) =>
          fetch(`/api/cases/${encodeURIComponent(caseId)}/tasks/${encodeURIComponent(task.task_id)}/status`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ task_type: task.task_type, to_status: 'done', note: `${meta.label} entered.` }),
          }).catch(() => null),
        ))

      onWorkspaceEvent(eventFor(caseId, 'task_status_updated', 'Marked missing-info tasks done'))
      setMessage('Saved to Elastic. Update the action plan to use these details.')
    } catch (err) {
      setMessage(err instanceof Error ? err.message : 'Could not save facts')
    } finally {
      setSaving(false)
    }
  }

  return (
    <motion.section
      initial={{ opacity: 0, y: 12 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.35, ease: [0.25, 0.46, 0.45, 0.94] as const }}
      className="bg-white border border-slate-200 rounded-2xl overflow-hidden"
    >
      <div className="px-6 py-4 border-b border-slate-100">
        <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Missing case details</p>
      </div>
      <div className="p-5 space-y-4">
        <div className="grid sm:grid-cols-2 gap-3">
          {fields.map(({ task, meta }) => (
            <label key={task.task_id} className={meta.input === 'textarea' ? 'sm:col-span-2 space-y-1.5' : 'space-y-1.5'}>
              <span className="text-xs font-semibold text-slate-500">{meta.label}</span>
              {meta.input === 'textarea' ? (
                <textarea
                  value={values[meta.field] ?? ''}
                  onChange={event => setValues(prev => ({ ...prev, [meta.field]: event.target.value }))}
                  rows={3}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 outline-none focus:border-teal-400 focus:bg-white"
                />
              ) : meta.input === 'select' ? (
                <select
                  value={values[meta.field] ?? ''}
                  onChange={event => setValues(prev => ({ ...prev, [meta.field]: event.target.value }))}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 outline-none focus:border-teal-400 focus:bg-white"
                >
                  <option value="">Select stage</option>
                  <option value="Initial denial">Initial denial</option>
                  <option value="Reconsideration">Reconsideration</option>
                  <option value="Hearing">Hearing</option>
                  <option value="Appeals Council">Appeals Council</option>
                </select>
              ) : (
                <input
                  type={meta.input}
                  value={values[meta.field] ?? ''}
                  onChange={event => setValues(prev => ({ ...prev, [meta.field]: event.target.value }))}
                  className="w-full rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-sm text-slate-700 outline-none focus:border-teal-400 focus:bg-white"
                />
              )}
            </label>
          ))}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          <button
            onClick={saveFacts}
            disabled={saving}
            className="inline-flex items-center gap-2 rounded-xl bg-teal-600 px-3 py-2 text-xs font-semibold text-white hover:bg-teal-700 disabled:opacity-50"
          >
            <Save size={14} />
            {saving ? 'Saving facts' : 'Save facts'}
          </button>
          <button
            onClick={onUpdateActionPlan}
            className="inline-flex items-center gap-2 rounded-xl border border-slate-200 bg-white px-3 py-2 text-xs font-semibold text-slate-600 hover:border-teal-200 hover:text-teal-700"
          >
            <RefreshCw size={14} />
            Update action plan
          </button>
          {message && (
            <span className="inline-flex items-center gap-1.5 text-xs font-medium text-emerald-600">
              <Check size={13} />
              {message}
            </span>
          )}
        </div>
      </div>
    </motion.section>
  )
}
