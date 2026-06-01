import { motion } from 'framer-motion'
import { Search, FileSearch, FilePlus, Package } from 'lucide-react'
import { clsx } from 'clsx'
import type { Mission } from '@/types/api'

const iconMap: Record<string, React.ElementType> = {
  analyze_denial: Search,
  find_missing_evidence: FileSearch,
  draft_records_request: FilePlus,
  prepare_packet: Package,
}

const descMap: Record<string, string> = {
  analyze_denial: 'Extract denial reason + SSA policy',
  find_missing_evidence: 'Find gaps vs. policy requirements',
  draft_records_request: 'Draft provider records request',
  prepare_packet: 'Build full advocate-ready packet',
}

interface MissionButtonsProps {
  missions: Mission[]
  activeMission: string | null
  loading: boolean
  onSelect: (id: string) => void
}

export function MissionButtons({ missions, activeMission, loading, onSelect }: MissionButtonsProps) {
  return (
    <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
      {missions.map((mission, i) => {
        const Icon = iconMap[mission.id] ?? Search
        const isActive = activeMission === mission.id
        const desc = descMap[mission.id] ?? mission.description
        return (
          <motion.button
            key={mission.id}
            initial={{ opacity: 0, y: 14 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.35, delay: i * 0.07, ease: [0.25, 0.46, 0.45, 0.94] as const }}
            whileHover={loading ? {} : { y: -3, boxShadow: '0 8px 24px rgba(94,184,173,0.18)' }}
            whileTap={loading ? {} : { scale: 0.97 }}
            onClick={() => !loading && onSelect(mission.id)}
            disabled={loading}
            className={clsx(
              'relative text-left p-4 rounded-2xl border-2 transition-all duration-200 cursor-pointer disabled:cursor-wait',
              isActive
                ? 'bg-teal-50 border-teal-300 shadow-sm'
                : 'bg-white border-slate-100 hover:border-teal-200 hover:bg-slate-50/60'
            )}
          >
            {isActive && (
              <motion.div
                layoutId="missionGlow"
                className="absolute inset-0 rounded-2xl bg-teal-50"
                transition={{ type: 'spring', stiffness: 300, damping: 28 }}
              />
            )}
            <div className={clsx(
              'relative w-9 h-9 rounded-xl flex items-center justify-center mb-3',
              isActive ? 'bg-teal-200/60' : 'bg-slate-100'
            )}>
              <Icon size={16} className={isActive ? 'text-teal-700' : 'text-slate-400'} />
            </div>
            <div className={clsx(
              'relative text-sm font-semibold leading-tight mb-1',
              isActive ? 'text-teal-800' : 'text-slate-700'
            )}>
              {mission.label}
            </div>
            <div className={clsx(
              'relative text-xs leading-relaxed',
              isActive ? 'text-teal-600' : 'text-slate-400'
            )}>
              {desc}
            </div>
          </motion.button>
        )
      })}
    </div>
  )
}
