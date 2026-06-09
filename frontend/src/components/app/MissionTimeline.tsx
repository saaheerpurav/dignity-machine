import { useEffect, useRef } from 'react'
import { gsap } from 'gsap'
import * as Tooltip from '@radix-ui/react-tooltip'
import { clsx } from 'clsx'

const STAGES = [
  { label: 'Read denial', short: '1', desc: 'Read the selected denial letter and basic details.' },
  { label: 'Review records', short: '2', desc: 'Review selected case documents.' },
  { label: 'Check rules', short: '3', desc: 'Compare the denial with Social Security rules.' },
  { label: 'Find proof', short: '4', desc: 'Compare the records with the rules to find missing proof.' },
  { label: 'Get helper', short: '5', desc: 'Prepare any helper details available for the case.' },
  { label: 'Write summary', short: '6', desc: 'Draft a review summary for a human to check.' },
]

interface MissionTimelineProps {
  running: boolean
  done: boolean
}

export function MissionTimeline({ running, done }: MissionTimelineProps) {
  const dotRefs = useRef<(HTMLDivElement | null)[]>([])
  const labelRefs = useRef<(HTMLSpanElement | null)[]>([])
  const lineRefs = useRef<(HTMLDivElement | null)[]>([])
  const tlRef = useRef<gsap.core.Timeline | null>(null)

  useEffect(() => {
    if (running) {
      dotRefs.current.forEach(el => {
        if (el) gsap.set(el, { backgroundColor: '#e2e8f0', scale: 1 })
      })
      labelRefs.current.forEach(el => {
        if (el) gsap.set(el, { color: '#94a3b8' })
      })
      lineRefs.current.forEach(el => {
        if (el) gsap.set(el, { scaleX: 0 })
      })
      tlRef.current?.kill()
      const tl = gsap.timeline()
      STAGES.forEach((_, i) => {
        tl.to(dotRefs.current[i], {
          backgroundColor: '#5eb8ad', scale: 1.3, duration: 0.25, ease: 'back.out(2)',
        }, i * 4.5)
          .to(labelRefs.current[i], { color: '#0d9488', duration: 0.2 }, `<`)
          .to(dotRefs.current[i], { scale: 1, duration: 0.2 }, `>`)
        if (lineRefs.current[i]) {
          tl.to(lineRefs.current[i], { scaleX: 1, duration: 3.8, ease: 'none' }, `<+0.2`)
        }
      })
      tlRef.current = tl
    }
  }, [running])

  useEffect(() => {
    if (done) {
      tlRef.current?.kill()
      dotRefs.current.forEach((el, i) => {
        if (el) gsap.to(el, { backgroundColor: '#86efac', scale: 1, duration: 0.25, delay: i * 0.06 })
      })
      labelRefs.current.forEach((el, i) => {
        if (el) gsap.to(el, { color: '#10b981', duration: 0.25, delay: i * 0.06 })
      })
      lineRefs.current.forEach((el, i) => {
        if (el) gsap.to(el, { scaleX: 1, duration: 0.2, delay: i * 0.06 })
      })
    }
  }, [done])

  return (
    <Tooltip.Provider delayDuration={150}>
      <div className={clsx(
        'bg-white border border-slate-200 rounded-2xl px-6 py-5 transition-all duration-300',
        running && 'border-teal-200',
        done && 'border-emerald-200'
      )}>
        <div className="flex items-center gap-2 mb-4">
          <p className="text-xs font-bold uppercase tracking-widest text-slate-400">Agent progress</p>
          {running && <span className="text-xs text-teal-500 font-medium animate-pulse">Running...</span>}
          {done && <span className="text-xs text-emerald-500 font-medium">Complete</span>}
        </div>

        <div className="relative flex items-center">
          {STAGES.map((stage, i) => (
            <div key={stage.label} className="flex-1 flex flex-col items-center relative">
              {i < STAGES.length - 1 && (
                <div className="absolute top-3 left-1/2 w-full h-0.5 bg-slate-100 overflow-hidden">
                  <div
                    ref={el => { lineRefs.current[i] = el }}
                    className="h-full bg-teal-300 origin-left"
                    style={{ transform: 'scaleX(0)' }}
                  />
                </div>
              )}
              <Tooltip.Root>
                <Tooltip.Trigger asChild>
                  <div
                    ref={el => { dotRefs.current[i] = el }}
                    className="w-6 h-6 rounded-full flex items-center justify-center z-10 relative cursor-help hover:ring-4 hover:ring-teal-100 transition-all"
                    style={{ backgroundColor: !running && !done ? '#e2e8f0' : undefined }}
                  >
                    <span className="text-white text-[10px] font-bold">{stage.short}</span>
                  </div>
                </Tooltip.Trigger>
                <Tooltip.Portal>
                  <Tooltip.Content
                    side="top"
                    sideOffset={8}
                    className="bg-slate-900 text-white text-xs px-3 py-2 rounded-lg z-50 max-w-[220px] shadow-lg"
                  >
                    <p className="font-semibold mb-0.5">{stage.label}</p>
                    <p className="text-slate-300 text-[11px] leading-relaxed">{stage.desc}</p>
                    <Tooltip.Arrow className="fill-slate-900" />
                  </Tooltip.Content>
                </Tooltip.Portal>
              </Tooltip.Root>
              <span
                ref={el => { labelRefs.current[i] = el }}
                className="text-[10px] mt-1.5 text-center leading-tight hidden sm:block"
                style={{ color: '#94a3b8' }}
              >
                {stage.label}
              </span>
            </div>
          ))}
        </div>
      </div>
    </Tooltip.Provider>
  )
}
