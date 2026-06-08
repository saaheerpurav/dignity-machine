import { motion } from 'framer-motion'
import { AlertCircle, CalendarClock, CheckCircle2, ClipboardList, FileText, Save } from 'lucide-react'
import type { AppealDeadline, CaseTask, CaseTaskStatus, CaseTaskType } from '@/types/api'

interface ActionPlanProps {
  deadline?: AppealDeadline
  tasks?: CaseTask[]
  hasRecordsDraft?: boolean
  hasReviewSummary?: boolean
  showArtifactCards?: boolean
  saved?: boolean
  loading: boolean
}

const TASK_TYPE_LABELS: Record<CaseTaskType, string> = {
  missing_proof: 'Suggested task',
  missing_notice_date: 'Needs info',
  missing_denial_reason: 'Needs info',
  missing_condition: 'Needs info',
  missing_appeal_stage: 'Needs info',
  missing_provider: 'Needs info',
  records_request_review: 'Draft created',
  review_summary_review: 'Ready for review',
}

const STATUS_LABELS: Record<CaseTaskStatus, string> = {
  suggested: 'Suggested task',
  needs_info: 'Needs info',
  draft_created: 'Draft created',
  ready_for_review: 'Ready for review',
}

const MISSING_DETAIL_TYPES: CaseTaskType[] = [
  'missing_notice_date',
  'missing_denial_reason',
  'missing_condition',
  'missing_appeal_stage',
  'missing_provider',
]

const GENERATED_DRAFT_TYPES: CaseTaskType[] = ['records_request_review', 'review_summary_review']

function taskType(task: CaseTask): CaseTaskType {
  return task.task_type ?? 'missing_proof'
}

function taskLabel(task: CaseTask) {
  return TASK_TYPE_LABELS[taskType(task)] ?? STATUS_LABELS[task.status] ?? 'Suggested task'
}

function deadlineStatus(deadline?: AppealDeadline) {
  if (deadline?.appeal_deadline) return 'Human review required'
  return 'Needs notice date'
}

function taskIconClass(task: CaseTask) {
  const type = taskType(task)
  if (type === 'missing_proof') return 'text-teal-400'
  if (GENERATED_DRAFT_TYPES.includes(type)) return 'text-emerald-400'
  return 'text-amber-400'
}

function TaskGroup({
  title,
  countLabel,
  tasks,
}: {
  title: string
  countLabel: string
  tasks: CaseTask[]
}) {
  if (tasks.length === 0) return null

  return (
    <div className="border border-slate-200 rounded-xl p-4 space-y-2 bg-slate-50">
      <div className="flex items-center justify-between gap-3">
        <div className="flex items-center gap-2">
          <ClipboardList size={15} className="text-teal-500" />
          <p className="text-sm font-semibold text-slate-800">{title}</p>
        </div>
        <span className="text-[11px] font-semibold text-teal-600">{tasks.length} {countLabel}</span>
      </div>
      <div className="space-y-2">
        {tasks.slice(0, 5).map(task => (
          <div key={task.task_id} className="flex gap-2">
            {GENERATED_DRAFT_TYPES.includes(taskType(task)) ? (
              <CheckCircle2 size={14} className={`${taskIconClass(task)} shrink-0 mt-0.5`} />
            ) : (
              <AlertCircle size={14} className={`${taskIconClass(task)} shrink-0 mt-0.5`} />
            )}
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-700">{task.title}</p>
              <p className="text-[11px] text-slate-400">{taskLabel(task)}</p>
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

export function ActionPlan({ deadline, tasks = [], hasRecordsDraft, hasReviewSummary, showArtifactCards = true, saved, loading }: ActionPlanProps) {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-3">
        <div className="shimmer h-3 w-36 rounded" />
        <div className="shimmer h-16 rounded-xl" />
        <div className="shimmer h-16 rounded-xl" />
      </div>
    )
  }

  if (!deadline && tasks.length === 0 && !hasRecordsDraft && !hasReviewSummary) return null

  const missingProofTasks = tasks.filter(task => taskType(task) === 'missing_proof')
  const missingDetailTasks = tasks.filter(task => MISSING_DETAIL_TYPES.includes(taskType(task)))
  const generatedDraftTasks = tasks.filter(task => GENERATED_DRAFT_TYPES.includes(taskType(task)))
  const hasRecordsRequestTask = tasks.some(task => taskType(task) === 'records_request_review')
  const hasReviewSummaryTask = tasks.some(task => taskType(task) === 'review_summary_review')

  return (
    <motion.section
      initial={{ opacity: 0, y: 14 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] as const }}
      className="bg-white border border-slate-200 rounded-2xl overflow-hidden"
    >
      <div className="px-6 py-5 border-b border-slate-100 flex items-center justify-between gap-3">
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Appeal action plan</p>
          <p className="text-xs text-slate-400 mt-1">Draft tasks created from this selected denial.</p>
        </div>
        {saved && (
          <span className="inline-flex items-center gap-1.5 text-xs font-semibold text-emerald-600 bg-emerald-50 border border-emerald-100 rounded-full px-3 py-1">
            <Save size={12} />
            Saved to Elastic
          </span>
        )}
      </div>

      <div className="p-5 grid sm:grid-cols-2 gap-3">
        {deadline && (
          <div className="border border-slate-200 rounded-xl p-4 space-y-2 bg-slate-50">
            <div className="flex items-center justify-between gap-3">
              <div className="flex items-center gap-2">
                <CalendarClock size={15} className="text-amber-500" />
                <p className="text-sm font-semibold text-slate-800">Possible deadline</p>
              </div>
              <span className="text-[11px] font-semibold text-amber-600">{deadlineStatus(deadline)}</span>
            </div>
            {deadline.appeal_deadline ? (
              <div className="text-sm text-slate-700 space-y-1">
                <p className="font-mono">{deadline.appeal_deadline}</p>
                <p className="text-xs text-slate-400">
                  Notice: {deadline.notice_date ?? 'unknown'} / assumed receipt: {deadline.assumed_receipt_date ?? 'unknown'}
                </p>
              </div>
            ) : (
              <p className="text-sm text-slate-600">Find the notice date before relying on any appeal deadline.</p>
            )}
          </div>
        )}

        <TaskGroup
          title="Missing proof"
          countLabel={missingProofTasks.length === 1 ? 'task' : 'tasks'}
          tasks={missingProofTasks}
        />

        <TaskGroup
          title="Missing case details"
          countLabel={missingDetailTasks.length === 1 ? 'item' : 'items'}
          tasks={missingDetailTasks}
        />

        <TaskGroup
          title="Generated drafts"
          countLabel={generatedDraftTasks.length === 1 ? 'draft' : 'drafts'}
          tasks={generatedDraftTasks}
        />

        {showArtifactCards && hasRecordsDraft && !hasRecordsRequestTask && (
          <div className="border border-slate-200 rounded-xl p-4 bg-slate-50 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <FileText size={15} className="text-sky-500" />
              <p className="text-sm font-semibold text-slate-800">Doctor records request</p>
            </div>
            <span className="text-[11px] font-semibold text-sky-600">Draft created</span>
          </div>
        )}

        {showArtifactCards && hasReviewSummary && !hasReviewSummaryTask && (
          <div className="border border-slate-200 rounded-xl p-4 bg-slate-50 flex items-center justify-between gap-3">
            <div className="flex items-center gap-2">
              <ClipboardList size={15} className="text-violet-500" />
              <p className="text-sm font-semibold text-slate-800">Review summary</p>
            </div>
            <span className="text-[11px] font-semibold text-violet-600">Ready for review</span>
          </div>
        )}
      </div>
    </motion.section>
  )
}
