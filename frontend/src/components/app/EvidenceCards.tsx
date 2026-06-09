import { useState, useMemo } from 'react'
import { useTrail, animated } from '@react-spring/web'
import { motion, AnimatePresence } from 'framer-motion'
import { ShimmerCard } from '@/components/ui/Shimmer'
import { ExternalLink, ChevronDown } from 'lucide-react'
import { clsx } from 'clsx'
import type { MedicalEvidence, PolicyCitation } from '@/types/api'

type FilterMode = 'all' | 'medical' | 'policy'

interface EvidenceCardsProps {
  medical: MedicalEvidence[]
  policy: PolicyCitation[]
  loading: boolean
}

function ExpandableCard({
  children,
  expanded,
  preview,
}: {
  children: React.ReactNode
  expanded: React.ReactNode
  preview: string
}) {
  const [open, setOpen] = useState(false)
  return (
    <>
      <p
        className={clsx(
          'text-sm text-slate-700 leading-relaxed transition-all',
          !open && 'line-clamp-3'
        )}
      >
        {preview}
      </p>
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.25, ease: [0.25, 0.46, 0.45, 0.94] as const }}
            className="overflow-hidden"
          >
            <div className="pt-3">{expanded}</div>
          </motion.div>
        )}
      </AnimatePresence>
      <button
        onClick={() => setOpen(o => !o)}
        className="flex items-center gap-1 text-[10px] font-semibold uppercase tracking-widest text-slate-600 hover:text-slate-800 transition-colors cursor-pointer mt-1"
      >
        {open ? 'Show less' : 'Show details'}
        <ChevronDown
          size={11}
          className={clsx('transition-transform duration-200', open && 'rotate-180')}
        />
      </button>
      {children}
    </>
  )
}

function MedicalCard({ ev, style }: { ev: MedicalEvidence; style: object }) {
  const preview = ev.excerpt || ev.finding || ev.title || 'Retrieved case document'
  const distinctDetails = ev.relevance && ev.relevance.trim() !== preview.trim() ? ev.relevance : ''
  return (
    <animated.div style={style} className="bg-white border border-slate-200 rounded-2xl overflow-hidden hover:border-blue-200 transition-colors">
      <div className="h-1 w-full bg-blue-200" />
      <div className="p-5 space-y-2.5">
        <div className="flex items-start justify-between gap-3">
          <div>
            <p className="text-[10px] font-bold uppercase tracking-widest text-blue-400 mb-1">Case evidence</p>
            {ev.title && <p className="text-xs font-semibold text-slate-600 leading-tight mt-1">{ev.title}</p>}
          </div>
        </div>
        <ExpandableCard
          preview={preview}
          expanded={
            distinctDetails ? (
              <div className="border-l-2 border-teal-200 pl-3">
                <p className="text-[10px] font-bold uppercase tracking-widest text-teal-400 mb-1">Why it matters</p>
                <p className="text-xs text-teal-700 font-medium leading-relaxed">{distinctDetails}</p>
              </div>
            ) : (
              <div className="text-[11px] text-slate-600 leading-relaxed space-y-1">
                <p><span className="font-semibold text-slate-700">Source:</span> Selected case documents</p>
                {ev.title && <p><span className="font-semibold text-slate-700">Document:</span> {ev.title}</p>}
              </div>
            )
          }
        >{null}</ExpandableCard>
      </div>
    </animated.div>
  )
}

function PolicyCard({ citation, style }: { citation: PolicyCitation; style: object }) {
  const body = citation.excerpt || citation.why_it_matters || 'Retrieved SSA policy citation'
  return (
    <animated.div style={style} className="bg-white border border-slate-200 rounded-2xl overflow-hidden hover:border-teal-200 transition-colors">
      <div className="h-1 w-full bg-teal-200" />
      <div className="p-5 space-y-2.5">
        <div className="flex items-start justify-between gap-3">
          <div className="min-w-0">
            <p className="text-[10px] font-bold uppercase tracking-widest text-teal-500 mb-1">Social Security rule</p>
            <p className="text-xs font-semibold text-slate-600 leading-tight">{citation.title}</p>
          </div>
        </div>
        <p className="text-sm text-slate-700 leading-relaxed">{body}</p>
        {citation.url && (
          <a
            href={citation.url}
            target="_blank"
            rel="noopener noreferrer"
            className="inline-flex items-center gap-1.5 text-xs font-semibold text-teal-600 hover:text-teal-700 break-all"
          >
            <ExternalLink size={12} className="shrink-0" />
            {citation.url}
          </a>
        )}
        <div className="text-[11px] text-slate-400">
          <span className="font-semibold">Source:</span> Social Security rules
        </div>
      </div>
    </animated.div>
  )
}

function FilterControl({ mode, onChange, counts }: {
  mode: FilterMode
  onChange: (m: FilterMode) => void
  counts: { all: number; medical: number; policy: number }
}) {
  const options: { id: FilterMode; label: string; count: number }[] = [
    { id: 'all', label: 'All', count: counts.all },
    { id: 'medical', label: 'Case docs', count: counts.medical },
    { id: 'policy', label: 'Policy', count: counts.policy },
  ]
  return (
    <div className="flex items-center gap-1 bg-slate-50 rounded-xl p-1">
      {options.map(opt => {
        const active = mode === opt.id
        return (
          <button
            key={opt.id}
            onClick={() => onChange(opt.id)}
            className={clsx(
              'relative px-3 py-1.5 text-xs font-semibold rounded-lg transition-colors cursor-pointer',
              active ? 'text-teal-700' : 'text-slate-400 hover:text-slate-600'
            )}
          >
            {active && (
              <motion.div
                layoutId="filterPill"
                className="absolute inset-0 bg-white rounded-lg shadow-sm border border-slate-100"
                transition={{ type: 'spring', stiffness: 360, damping: 30 }}
              />
            )}
            <span className="relative">
              {opt.label}
              <span className="ml-1.5 text-slate-300 font-mono text-[10px]">{opt.count}</span>
            </span>
          </button>
        )
      })}
    </div>
  )
}

export function EvidenceCards({ medical, policy, loading }: EvidenceCardsProps) {
  const [mode, setMode] = useState<FilterMode>('all')

  const visible = useMemo(() => {
    const med = medical ?? []
    const pol = policy ?? []
    if (mode === 'medical') return { items: med.map(m => ({ kind: 'm' as const, data: m })), counts: { all: med.length + pol.length, medical: med.length, policy: pol.length } }
    if (mode === 'policy') return { items: pol.map(p => ({ kind: 'p' as const, data: p })), counts: { all: med.length + pol.length, medical: med.length, policy: pol.length } }
    return {
      items: [...med.map(m => ({ kind: 'm' as const, data: m })), ...pol.map(p => ({ kind: 'p' as const, data: p }))],
      counts: { all: med.length + pol.length, medical: med.length, policy: pol.length },
    }
  }, [mode, medical, policy])

  const trail = useTrail(visible.items.length, {
    from: { opacity: 0, transform: 'translateY(20px)' },
    to: { opacity: 1, transform: 'translateY(0px)' },
    config: { tension: 260, friction: 22 },
    reset: true,
    keys: visible.items.map((it, i) => `${mode}-${i}-${it.kind}`),
  })

  if (loading) {
    return (
      <div className="space-y-4">
        <div className="shimmer h-3 w-44 rounded" />
        <div className="grid sm:grid-cols-2 gap-3">
          <ShimmerCard /><ShimmerCard /><ShimmerCard /><ShimmerCard />
        </div>
      </div>
    )
  }

  if (visible.counts.all === 0) return null

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-baseline gap-3">
          <h3 className="text-xs font-bold uppercase tracking-widest text-slate-400">What the agent found</h3>
        </div>
        <FilterControl mode={mode} onChange={setMode} counts={visible.counts} />
      </div>
      <div className="grid sm:grid-cols-2 gap-3">
        {trail.map((style, i) => {
          const item = visible.items[i]
          return item.kind === 'm'
            ? <MedicalCard key={`m-${i}`} ev={item.data} style={style} />
            : <PolicyCard key={`p-${i}`} citation={item.data} style={style} />
        })}
      </div>
    </div>
  )
}
