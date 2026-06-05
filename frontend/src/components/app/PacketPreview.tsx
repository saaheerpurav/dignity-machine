import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Disclosure, Transition } from '@headlessui/react'
import { ChevronDown, FileText, Mail, BookOpen, CheckSquare, Bell, Square, CheckCircle2 } from 'lucide-react'
import { clsx } from 'clsx'
import { Shimmer } from '@/components/ui/Shimmer'
import { CopyButton } from '@/components/ui/CopyButton'
import { ApprovalModal } from './ApprovalModal'
import type { StructuredResult } from '@/types/api'

interface PacketPreviewProps {
  structured: StructuredResult | null
  loading: boolean
}

function Section({
  icon: Icon,
  label,
  count,
  accent,
  children,
  defaultOpen = false,
  headerExtra,
}: {
  icon: React.ElementType
  label: string
  count?: string
  accent: string
  children: React.ReactNode
  defaultOpen?: boolean
  headerExtra?: React.ReactNode
}) {
  return (
    <Disclosure defaultOpen={defaultOpen}>
      {({ open }) => (
        <div className="border border-slate-200 rounded-xl overflow-hidden">
          <Disclosure.Button className="w-full flex items-center justify-between px-5 py-4 bg-white hover:bg-slate-50 transition-colors cursor-pointer text-left">
            <div className="flex items-center gap-3">
              <div className={clsx('w-7 h-7 rounded-lg flex items-center justify-center shrink-0', accent)}>
                <Icon size={14} />
              </div>
              <span className="text-sm font-semibold text-slate-800">{label}</span>
              {count && <span className="text-xs font-bold text-slate-400">{count}</span>}
            </div>
            <div className="flex items-center gap-3">
              {headerExtra}
              <ChevronDown size={15} className={clsx('text-slate-300 transition-transform duration-200', open && 'rotate-180')} />
            </div>
          </Disclosure.Button>
          <Transition
            enter="transition duration-150 ease-out"
            enterFrom="opacity-0 -translate-y-1"
            enterTo="opacity-100 translate-y-0"
            leave="transition duration-100 ease-in"
            leaveFrom="opacity-100"
            leaveTo="opacity-0"
          >
            <Disclosure.Panel className="px-5 py-4 bg-slate-50 border-t border-slate-100">
              {children}
            </Disclosure.Panel>
          </Transition>
        </div>
      )}
    </Disclosure>
  )
}

function InteractiveChecklist({ actions }: { actions: string[] }) {
  const [done, setDone] = useState<Set<number>>(new Set())
  const completed = done.size
  const total = actions.length
  const pct = total === 0 ? 0 : Math.round((completed / total) * 100)

  const toggle = (i: number) => {
    setDone(prev => {
      const next = new Set(prev)
      if (next.has(i)) next.delete(i)
      else next.add(i)
      return next
    })
  }

  return (
    <div className="space-y-3">
      {/* progress */}
      <div className="flex items-center gap-3">
        <div className="flex-1 h-1.5 bg-slate-200 rounded-full overflow-hidden">
          <motion.div
            className="h-full bg-emerald-300 rounded-full"
            animate={{ width: `${pct}%` }}
            transition={{ duration: 0.4, ease: [0.25, 0.46, 0.45, 0.94] as const }}
          />
        </div>
        <span className="text-[11px] font-mono text-slate-400 shrink-0 tabular-nums">{completed}/{total}</span>
      </div>

      <ol className="space-y-1.5">
        {actions.map((action, i) => {
          const isDone = done.has(i)
          return (
            <li key={i}>
              <button
                onClick={() => toggle(i)}
                className="w-full flex items-start gap-3 text-left p-2 -mx-2 rounded-lg hover:bg-white transition-colors cursor-pointer"
              >
                <motion.div
                  whileTap={{ scale: 0.85 }}
                  className="shrink-0 mt-0.5"
                >
                  <AnimatePresence mode="wait" initial={false}>
                    {isDone ? (
                      <motion.div
                        key="checked"
                        initial={{ scale: 0.5, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.5, opacity: 0 }}
                        transition={{ duration: 0.18 }}
                      >
                        <CheckCircle2 size={16} className="text-emerald-400" />
                      </motion.div>
                    ) : (
                      <motion.div
                        key="empty"
                        initial={{ scale: 0.5, opacity: 0 }}
                        animate={{ scale: 1, opacity: 1 }}
                        exit={{ scale: 0.5, opacity: 0 }}
                        transition={{ duration: 0.18 }}
                      >
                        <Square size={16} className="text-slate-300" strokeWidth={1.5} />
                      </motion.div>
                    )}
                  </AnimatePresence>
                </motion.div>
                <span
                  className={clsx(
                    'text-sm leading-relaxed transition-all',
                    isDone ? 'text-slate-300 line-through' : 'text-slate-700'
                  )}
                >
                  {action}
                </span>
              </button>
            </li>
          )
        })}
      </ol>
    </div>
  )
}

export function PacketPreview({ structured, loading }: PacketPreviewProps) {
  const [modalOpen, setModalOpen] = useState(false)

  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4">
        <div className="shimmer h-3 w-32 rounded" />
        <Shimmer lines={4} />
      </div>
    )
  }

  if (!structured) return null
  const { denial_summary, records_request_draft, advocate_alert_draft, packet_summary, next_actions } = structured
  if (!denial_summary && !records_request_draft && !packet_summary) return null

  return (
    <>
      <motion.div
        initial={{ opacity: 0, y: 14 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.45, delay: 0.15, ease: [0.25, 0.46, 0.45, 0.94] as const }}
        className="bg-white border border-slate-200 rounded-2xl overflow-hidden relative"
      >
        {/* subtle success glow */}
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ duration: 0.8, delay: 0.3 }}
          className="absolute -inset-px rounded-2xl pointer-events-none"
          style={{ boxShadow: '0 0 0 1px rgba(94,184,173,0.18)' }}
        />

        {/* header */}
        <div className="px-6 py-5 border-b border-slate-100 flex items-baseline gap-3 relative">
          <span className="text-xs font-bold uppercase tracking-widest text-slate-400">Review summary</span>
          <div className="h-px flex-1 bg-slate-100" />
          <div className="flex items-center gap-1.5 text-xs text-emerald-500 font-medium">
            <span className="relative flex w-1.5 h-1.5">
              <span className="absolute inset-0 rounded-full bg-emerald-400 opacity-75 animate-ping" />
              <span className="relative rounded-full bg-emerald-400 w-1.5 h-1.5" />
            </span>
            Ready for review
          </div>
        </div>

        <div className="p-5 space-y-3">
          {denial_summary && (
            <Section icon={BookOpen} label="Denial summary" accent="bg-rose-50 text-rose-400" defaultOpen>
              <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{denial_summary}</p>
            </Section>
          )}

          {records_request_draft && (
            <Section
              icon={FileText}
              label="Doctor records request"
              accent="bg-sky-50 text-sky-400"
              headerExtra={<CopyButton text={records_request_draft} />}
            >
              <pre className="text-xs text-slate-700 whitespace-pre-wrap font-mono leading-relaxed">{records_request_draft}</pre>
            </Section>
          )}

          {advocate_alert_draft && (
            <Section
              icon={Mail}
              label="Helper alert"
              accent="bg-teal-50 text-teal-400"
              headerExtra={<CopyButton text={advocate_alert_draft} />}
            >
              <pre className="text-xs text-slate-700 whitespace-pre-wrap font-mono leading-relaxed">{advocate_alert_draft}</pre>
              <button
                onClick={() => setModalOpen(true)}
                className="mt-4 inline-flex items-center gap-2 text-xs font-semibold text-teal-500 hover:text-teal-700 cursor-pointer transition-colors"
              >
                <Bell size={12} />
                Review &amp; approve send →
              </button>
            </Section>
          )}

          {packet_summary && (
            <Section icon={BookOpen} label="Packet summary" accent="bg-violet-50 text-violet-400">
              <p className="text-sm text-slate-700 leading-relaxed whitespace-pre-wrap">{packet_summary}</p>
            </Section>
          )}

          {next_actions && next_actions.length > 0 && (
            <Section
              icon={CheckSquare}
              label="Next actions"
              count={`${next_actions.length} steps`}
              accent="bg-emerald-50 text-emerald-400"
              defaultOpen
            >
              <InteractiveChecklist actions={next_actions} />
            </Section>
          )}
        </div>
      </motion.div>

      <ApprovalModal open={modalOpen} onOpenChange={setModalOpen} draft={advocate_alert_draft ?? ''} />
    </>
  )
}
