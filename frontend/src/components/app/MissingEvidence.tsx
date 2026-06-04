import { motion } from 'framer-motion'
import { Shimmer } from '@/components/ui/Shimmer'
import type { MissingEvidenceItem } from '@/types/api'

interface MissingEvidenceProps {
  items: MissingEvidenceItem[]
  loading: boolean
}

export function MissingEvidence({ items, loading }: MissingEvidenceProps) {
  if (loading) {
    return (
      <div className="bg-white border border-slate-200 rounded-2xl p-6 space-y-4">
        <div className="shimmer h-3 w-36 rounded" />
        <Shimmer lines={3} />
      </div>
    )
  }

  if (!items || items.length === 0) return null

  return (
    <div className="bg-white border border-slate-200 rounded-2xl overflow-hidden">
      {/* header strip */}
      <div className="bg-amber-50/60 border-b border-amber-100 px-6 py-4 flex items-baseline gap-3">
        <span className="text-2xl font-bold text-amber-400 leading-none">{items.length}</span>
        <div>
          <p className="text-xs font-bold uppercase tracking-widest text-amber-500">Evidence gaps</p>
          <p className="text-xs text-amber-400 mt-0.5">Missing proof that weakened the claim</p>
        </div>
      </div>

      {/* items */}
      <div className="divide-y divide-slate-100">
        {items.map((item, i) => {
          const title = item.item || item.gap_type || `Evidence gap ${i + 1}`
          const description = item.reason || item.description || item.why_it_matters || 'The agent flagged this as missing or incomplete evidence.'
          const support = [
            ...(item.supporting_case_doc_ids ?? []),
            ...(item.supporting_policy_ids ?? []),
          ]

          return (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -12 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.35, delay: i * 0.09, ease: [0.25, 0.46, 0.45, 0.94] as const }}
              className="px-6 py-4 flex gap-4"
            >
              <div className="w-7 h-7 rounded-full bg-amber-50 border border-amber-200 flex items-center justify-center shrink-0 mt-0.5">
                <span className="text-xs font-bold text-amber-400">{i + 1}</span>
              </div>
              <div className="space-y-1.5 min-w-0">
                <p className="text-sm font-semibold text-slate-800">{title}</p>
                <p className="text-xs text-slate-500 leading-relaxed">{description}</p>
                {item.why_it_matters && item.why_it_matters !== description && (
                  <p className="text-xs text-amber-600 leading-relaxed">{item.why_it_matters}</p>
                )}
                {support.length > 0 && (
                  <div className="flex flex-wrap gap-1.5 pt-1">
                    {support.map(id => (
                      <span key={id} className="text-[10px] font-mono text-slate-400 bg-slate-50 border border-slate-100 rounded px-1.5 py-0.5">
                        {id}
                      </span>
                    ))}
                  </div>
                )}
              </div>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}
