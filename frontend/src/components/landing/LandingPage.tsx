import { useEffect, useRef } from 'react'
import { motion, useReducedMotion } from 'framer-motion'
import gsap from 'gsap'
import {
  ArrowRight,
  CalendarClock,
  CheckCircle2,
  FileText,
  FileUp,
  IdCard,
  Lock,
  Mail,
  PlayCircle,
  Receipt,
  ScrollText,
  ShieldCheck,
  Stethoscope,
} from 'lucide-react'

interface LandingPageProps {
  loading: boolean
  error: string | null
  onExample: () => void
  onUpload: () => void
}

const steps = [
  {
    n: '1',
    title: 'Share one denial letter',
    body: 'Try the included example, or upload a single text-readable PDF of the denial you received.',
  },
  {
    n: '2',
    title: 'We read it with you',
    body: 'The workspace identifies the rule SSA cited, surfaces the missing evidence, and drafts the records request for your review.',
  },
  {
    n: '3',
    title: 'You decide what to send',
    body: 'Deadlines open as a calendar draft. Letters open in your email. Nothing is sent on your behalf.',
  },
]

const documentsYouNeed = [
  { icon: FileText, label: 'The denial letter', body: 'Most important. A PDF you can highlight text in.' },
  { icon: Receipt, label: 'Recent medical bills', body: 'Helpful for showing care received and costs.' },
  { icon: ShieldCheck, label: 'Insurance policy', body: 'So we can match denial reasons to coverage.' },
  { icon: Stethoscope, label: 'Hospital records', body: 'Discharge summaries, visit notes, treatment history.' },
  { icon: IdCard, label: 'A photo ID', body: 'Only if you choose to share it with an advocate later.' },
]

const trust = [
  {
    icon: Lock,
    title: 'Private by design',
    body: 'Your case stays in its own scoped workspace. Searches are filtered to your case only — never anyone else’s.',
  },
  {
    icon: ScrollText,
    title: 'You can see the work',
    body: 'Every step the agent takes is logged and visible. Sources are shown next to conclusions, not hidden.',
  },
  {
    icon: Stethoscope,
    title: 'Not a lawyer or doctor',
    body: 'We help you organize and understand your denial. For medical or legal decisions, we point you to someone who can.',
  },
]

const ease = [0.22, 1, 0.36, 1] as const

export function LandingPage({ loading, error, onExample, onUpload }: LandingPageProps) {
  const reduceMotion = useReducedMotion()
  const trustListRef = useRef<HTMLUListElement>(null)

  useEffect(() => {
    if (reduceMotion || !trustListRef.current) return
    const items = trustListRef.current.querySelectorAll('li')
    gsap.from(items, {
      opacity: 0,
      y: 14,
      duration: 0.6,
      ease: 'power3.out',
      stagger: 0.12,
      delay: 0.5,
    })
  }, [reduceMotion])

  const breath = reduceMotion
    ? {}
    : {
        animate: {
          boxShadow: [
            '0 0 0 0 rgba(63,93,74,0.0)',
            '0 0 0 8px rgba(63,93,74,0.10)',
            '0 0 0 0 rgba(63,93,74,0.0)',
          ],
        },
        transition: { duration: 3.6, repeat: Infinity, ease: 'easeInOut' as const },
      }

  const fadeUp = (delay = 0) =>
    reduceMotion
      ? { initial: { opacity: 1 }, animate: { opacity: 1 } }
      : {
          initial: { opacity: 0, y: 18 },
          whileInView: { opacity: 1, y: 0 },
          viewport: { once: true, margin: '-60px' },
          transition: { duration: 0.6, delay, ease },
        }

  return (
    <div
      className="min-h-screen text-[#2a241d] antialiased"
      style={{
        backgroundColor: '#f6f1e8',
        fontFamily:
          '"Inter", "IBM Plex Sans", system-ui, -apple-system, "Segoe UI", Roboto, sans-serif',
      }}
    >
      {/* nav */}
      <header className="border-b border-[#e5dcc9]">
        <div className="max-w-5xl mx-auto px-6 py-5 flex items-center justify-between">
          <div className="flex items-center gap-2.5">
            <div className="h-8 w-8 rounded-full bg-[#3f5d4a] flex items-center justify-center">
              <ShieldCheck size={16} className="text-[#f6f1e8]" strokeWidth={2} />
            </div>
            <span className="text-[15px] font-semibold tracking-tight text-[#1f1b16]">
              Dignity Machine
            </span>
          </div>
          <div className="hidden sm:flex items-center gap-2 text-[13px] text-[#6b6258]">
            <span className="h-1.5 w-1.5 rounded-full bg-[#3f5d4a]" />
            Private case workspace
          </div>
        </div>
      </header>

      {/* hero */}
      <section className="px-6 pt-20 pb-24">
        <div className="max-w-5xl mx-auto grid md:grid-cols-[1.3fr,1fr] gap-12 items-start">
          <div>
            <motion.span
              initial={reduceMotion ? false : { opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.5, ease }}
              className="inline-block text-[13px] font-medium text-[#3f5d4a] bg-[#e8efe6] border border-[#cddccd] rounded-full px-3 py-1"
            >
              For people who just got a disability denial letter
            </motion.span>

            <motion.h1
              initial={reduceMotion ? false : { opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.7, ease }}
              style={{ fontFamily: '"Fraunces", "Inter", Georgia, serif' }}
              className="mt-6 text-[clamp(2.5rem,5.5vw,4.25rem)] font-medium leading-[1.05] tracking-[-0.015em] text-[#1f1b16]"
            >
              You opened the letter.
              <br />
              <span className="italic text-[#3f5d4a]">We’ll help you read it.</span>
            </motion.h1>

            <motion.p
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.15, ease }}
              className="mt-6 text-[17px] leading-[1.65] text-[#4f463b] max-w-xl"
            >
              A calm, private workspace for understanding a Social Security disability denial. We
              read the letter with you, point to the rule it leans on, and help you draft what
              comes next — at your pace.
            </motion.p>

            <motion.div
              initial={reduceMotion ? false : { opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.6, delay: 0.3, ease }}
              className="mt-8 flex flex-col sm:flex-row gap-3"
            >
              <motion.button
                onClick={onExample}
                disabled={loading}
                {...breath}
                whileHover={reduceMotion ? undefined : { scale: 1.02 }}
                whileTap={reduceMotion ? undefined : { scale: 0.98 }}
                className="group inline-flex items-center justify-center gap-2.5 bg-[#3f5d4a] hover:bg-[#34503e] disabled:bg-[#a8b8ac] text-[#f6f1e8] text-[15px] font-medium px-6 py-3.5 rounded-full transition-colors cursor-pointer disabled:cursor-wait"
              >
                <PlayCircle size={18} strokeWidth={2} />
                See a worked example
                <ArrowRight size={15} className="group-hover:translate-x-0.5 transition-transform" />
              </motion.button>
              <button
                onClick={onUpload}
                disabled={loading}
                className="inline-flex items-center justify-center gap-2.5 bg-white hover:bg-[#fbf8f1] disabled:bg-[#f0eadd] text-[#1f1b16] text-[15px] font-medium px-6 py-3.5 rounded-full border border-[#d9cfba] transition-colors cursor-pointer disabled:cursor-wait"
              >
                <FileUp size={18} className="text-[#3f5d4a]" strokeWidth={2} />
                Upload your denial PDF
              </button>
            </motion.div>

            {loading && (
              <p className="mt-5 text-[14px] text-[#3f5d4a] flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-[#3f5d4a] animate-pulse" />
                Reading the letter and setting up your workspace…
              </p>
            )}
            {error && (
              <motion.div
                initial={{ opacity: 0, y: -6 }}
                animate={{ opacity: 1, y: 0 }}
                role="alert"
                className="alert mt-5 bg-[#fbeae4] border border-[#e8c4ba] text-[#9c3a2a] rounded-2xl px-4 py-3 flex items-start gap-2.5"
              >
                <ShieldCheck size={16} className="text-[#9c3a2a] shrink-0 mt-0.5" />
                <div className="text-[14px] leading-[1.5]">
                  <p className="font-semibold">We couldn't reach your workspace</p>
                  <p className="text-[13px] text-[#7d2e21] mt-0.5">Please try again in a moment. If this keeps happening, the workspace service may be offline.</p>
                </div>
              </motion.div>
            )}
          </div>

          {/* trust card */}
          <motion.aside
            initial={reduceMotion ? false : { opacity: 0, y: 24 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.7, delay: 0.2, ease }}
            className="bg-white border border-[#e5dcc9] rounded-3xl p-6 shadow-[0_2px_24px_-12px_rgba(63,93,74,0.18)]"
          >
            <p className="text-[12px] font-semibold uppercase tracking-wider text-[#6b6258]">
              Before you start
            </p>
            <h3
              style={{ fontFamily: '"Fraunces", Georgia, serif' }}
              className="mt-2 text-[22px] font-medium tracking-tight text-[#1f1b16]"
            >
              A few things to know
            </h3>
            <ul ref={trustListRef} className="mt-5 space-y-4">
              {trust.map(item => {
                const Icon = item.icon
                return (
                  <li key={item.title} className="flex gap-3">
                    <div className="h-8 w-8 rounded-full bg-[#eef3eb] flex items-center justify-center shrink-0">
                      <Icon size={15} className="text-[#3f5d4a]" strokeWidth={2} />
                    </div>
                    <div>
                      <p className="text-[14px] font-semibold text-[#1f1b16]">{item.title}</p>
                      <p className="text-[14px] text-[#5a5145] leading-[1.55] mt-0.5">{item.body}</p>
                    </div>
                  </li>
                )
              })}
            </ul>
          </motion.aside>
        </div>
      </section>

      {/* 3-step flow */}
      <section className="px-6 py-20 bg-[#efe7d5]/60 border-y border-[#e5dcc9]">
        <div className="max-w-5xl mx-auto">
          <motion.div {...fadeUp()} className="max-w-2xl">
            <p className="text-[13px] font-semibold uppercase tracking-wider text-[#3f5d4a]">
              How it works
            </p>
            <h2
              style={{ fontFamily: '"Fraunces", Georgia, serif' }}
              className="mt-2 text-[34px] sm:text-[40px] font-medium tracking-tight leading-[1.1] text-[#1f1b16]"
            >
              A clear three-step process. You remain in control throughout.
            </h2>
          </motion.div>

          <div className="mt-12 grid md:grid-cols-3 gap-4">
            {steps.map((s, i) => (
              <motion.div
                key={s.n}
                {...fadeUp(i * 0.08)}
                className="bg-white border border-[#e5dcc9] rounded-3xl p-7"
              >
                <div className="flex items-center gap-3">
                  <span className="h-9 w-9 rounded-full bg-[#3f5d4a] text-[#f6f1e8] text-[15px] font-semibold flex items-center justify-center">
                    {s.n}
                  </span>
                  <span className="text-[13px] font-medium text-[#6b6258]">Step {s.n} of 3</span>
                </div>
                <h3 className="mt-5 text-[19px] font-semibold text-[#1f1b16] tracking-tight">
                  {s.title}
                </h3>
                <p className="mt-2 text-[15px] text-[#5a5145] leading-[1.6]">{s.body}</p>
              </motion.div>
            ))}
          </div>
        </div>
      </section>

      {/* documents you need */}
      <section className="px-6 py-20">
        <div className="max-w-5xl mx-auto grid md:grid-cols-[1fr,1.4fr] gap-12">
          <motion.div {...fadeUp()}>
            <p className="text-[13px] font-semibold uppercase tracking-wider text-[#3f5d4a]">
              What to gather
            </p>
            <h2
              style={{ fontFamily: '"Fraunces", Georgia, serif' }}
              className="mt-2 text-[34px] sm:text-[40px] font-medium tracking-tight leading-[1.1] text-[#1f1b16]"
            >
              Helpful to have nearby
            </h2>
            <p className="mt-4 text-[16px] text-[#5a5145] leading-[1.65]">
              You only need the denial letter to start. The rest you can add later, as you go.
            </p>
          </motion.div>

          <div className="space-y-3">
            {documentsYouNeed.map((d, i) => {
              const Icon = d.icon
              return (
                <motion.div
                  key={d.label}
                  {...fadeUp(i * 0.05)}
                  className="flex items-start gap-4 bg-white border border-[#e5dcc9] rounded-2xl p-5"
                >
                  <div className="h-10 w-10 rounded-xl bg-[#f4ead3] border border-[#e6d8b5] flex items-center justify-center shrink-0">
                    <Icon size={17} className="text-[#7a5e2a]" strokeWidth={2} />
                  </div>
                  <div className="flex-1">
                    <div className="flex items-baseline justify-between gap-3 flex-wrap">
                      <p className="text-[16px] font-semibold text-[#1f1b16]">{d.label}</p>
                      {i === 0 && (
                        <span className="text-[12px] font-semibold text-[#3f5d4a] bg-[#e8efe6] px-2 py-0.5 rounded-full">
                          Required to start
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-[15px] text-[#5a5145] leading-[1.55]">{d.body}</p>
                  </div>
                </motion.div>
              )
            })}
          </div>
        </div>
      </section>

      {/* final actions */}
      <section className="px-6 py-20 bg-[#efe7d5]/60 border-y border-[#e5dcc9]">
        <div className="max-w-5xl mx-auto">
          <motion.div {...fadeUp()} className="max-w-2xl">
            <p className="text-[13px] font-semibold uppercase tracking-wider text-[#3f5d4a]">
              What you’ll leave with
            </p>
            <h2
              style={{ fontFamily: '"Fraunces", Georgia, serif' }}
              className="mt-2 text-[34px] sm:text-[40px] font-medium tracking-tight leading-[1.1] text-[#1f1b16]"
            >
              Drafts you can use today
            </h2>
            <p className="mt-4 text-[16px] text-[#5a5145] leading-[1.65]">
              Nothing is sent for you. Calendar events and emails open as drafts in your own tools,
              so you can read them, change them, and decide.
            </p>
          </motion.div>

          <div className="mt-10 grid md:grid-cols-2 gap-4">
            <motion.div {...fadeUp()} className="bg-white border border-[#e5dcc9] rounded-3xl p-7">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-[#eef3eb] flex items-center justify-center">
                  <CalendarClock size={18} className="text-[#3f5d4a]" strokeWidth={2} />
                </div>
                <p className="text-[16px] font-semibold text-[#1f1b16]">A calendar reminder</p>
              </div>
              <p className="mt-4 text-[15px] text-[#5a5145] leading-[1.6]">
                Your appeal deadline opens as a prefilled Google Calendar event. You add it when
                you’re ready.
              </p>
            </motion.div>
            <motion.div {...fadeUp(0.08)} className="bg-white border border-[#e5dcc9] rounded-3xl p-7">
              <div className="flex items-center gap-3">
                <div className="h-10 w-10 rounded-xl bg-[#eef3eb] flex items-center justify-center">
                  <Mail size={18} className="text-[#3f5d4a]" strokeWidth={2} />
                </div>
                <p className="text-[16px] font-semibold text-[#1f1b16]">A request for records</p>
              </div>
              <p className="mt-4 text-[15px] text-[#5a5145] leading-[1.6]">
                A polite, specific email draft opens in your mail client — already addressed, with
                the records named. You send it.
              </p>
            </motion.div>
          </div>
        </div>
      </section>

      {/* disclaimer */}
      <section className="px-6 py-20">
        <div className="max-w-3xl mx-auto bg-white border border-[#e5dcc9] rounded-3xl p-8 sm:p-10">
          <div className="flex items-center gap-3">
            <CheckCircle2 size={20} className="text-[#3f5d4a]" strokeWidth={2} />
            <p className="text-[13px] font-semibold uppercase tracking-wider text-[#6b6258]">
              A clear note on what this is
            </p>
          </div>
          <h2
            style={{ fontFamily: '"Fraunces", Georgia, serif' }}
            className="mt-4 text-[28px] sm:text-[32px] font-medium tracking-tight leading-[1.15] text-[#1f1b16]"
          >
            We are not your lawyer or your doctor.
          </h2>
          <p className="mt-4 text-[16px] text-[#4f463b] leading-[1.7]">
            Dignity Machine helps you understand and organize a denial letter and the next steps.
            We are not a law firm. We do not provide legal or medical advice. For decisions that
            need a professional, we’ll suggest you talk to an attorney, advocate, or clinician —
            and we’ll help you prepare what to bring.
          </p>
          <div className="mt-6 flex flex-wrap gap-3">
            <span className="text-[13px] font-medium text-[#3f5d4a] bg-[#e8efe6] border border-[#cddccd] px-3 py-1.5 rounded-full">
              No information leaves your case
            </span>
            <span className="text-[13px] font-medium text-[#3f5d4a] bg-[#e8efe6] border border-[#cddccd] px-3 py-1.5 rounded-full">
              Every step is shown to you
            </span>
            <span className="text-[13px] font-medium text-[#3f5d4a] bg-[#e8efe6] border border-[#cddccd] px-3 py-1.5 rounded-full">
              You decide what gets sent
            </span>
          </div>
        </div>
      </section>

      {/* closing */}
      <section className="px-6 pb-24">
        <div className="max-w-3xl mx-auto text-center">
          <motion.h2
            {...fadeUp()}
            style={{ fontFamily: '"Fraunces", Georgia, serif' }}
            className="text-[clamp(2rem,4.5vw,3.25rem)] font-medium tracking-tight leading-[1.1] text-[#1f1b16]"
          >
            Take it one page at a time.
            <br />
            <span className="italic text-[#3f5d4a]">We’ll sit with you.</span>
          </motion.h2>
          <motion.div {...fadeUp(0.1)} className="mt-8 flex flex-col sm:flex-row gap-3 justify-center">
            <motion.button
              onClick={onExample}
              disabled={loading}
              {...breath}
              whileHover={reduceMotion ? undefined : { scale: 1.02 }}
              whileTap={reduceMotion ? undefined : { scale: 0.98 }}
              className="inline-flex items-center justify-center gap-2.5 bg-[#3f5d4a] hover:bg-[#34503e] disabled:bg-[#a8b8ac] text-[#f6f1e8] text-[15px] font-medium px-6 py-3.5 rounded-full transition-colors cursor-pointer disabled:cursor-wait"
            >
              <PlayCircle size={18} strokeWidth={2} />
              See a worked example
            </motion.button>
            <button
              onClick={onUpload}
              disabled={loading}
              className="inline-flex items-center justify-center gap-2.5 bg-white hover:bg-[#fbf8f1] disabled:bg-[#f0eadd] text-[#1f1b16] text-[15px] font-medium px-6 py-3.5 rounded-full border border-[#d9cfba] transition-colors cursor-pointer disabled:cursor-wait"
            >
              <FileUp size={18} className="text-[#3f5d4a]" strokeWidth={2} />
              Upload your denial PDF
            </button>
          </motion.div>
        </div>
      </section>

      <footer className="border-t border-[#e5dcc9] px-6 py-8 text-center">
        <p className="text-[13px] text-[#6b6258]">
          Dignity Machine · Built for the Google Agent AI Hackathon · Palak, Saaheer, Supreet
        </p>
      </footer>
    </div>
  )
}
