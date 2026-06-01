import { motion } from 'framer-motion'
import * as Dialog from '@radix-ui/react-dialog'
import { X, Send } from 'lucide-react'

interface ApprovalModalProps {
  open: boolean
  onOpenChange: (open: boolean) => void
  draft: string
}

export function ApprovalModal({ open, onOpenChange, draft }: ApprovalModalProps) {
  return (
    <Dialog.Root open={open} onOpenChange={onOpenChange}>
      <Dialog.Portal>
        <Dialog.Overlay className="fixed inset-0 bg-black/20 backdrop-blur-sm z-40" />
        <Dialog.Content className="fixed top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 z-50 w-full max-w-lg focus:outline-none">
          <motion.div
            initial={{ opacity: 0, scale: 0.96, y: 10 }}
            animate={{ opacity: 1, scale: 1, y: 0 }}
            exit={{ opacity: 0, scale: 0.96, y: 10 }}
            transition={{ duration: 0.2, ease: 'easeOut' }}
            className="bg-white rounded-2xl border border-slate-200 shadow-2xl p-6 mx-4"
          >
            <div className="flex items-center justify-between mb-4">
              <Dialog.Title className="text-base font-semibold text-slate-800">
                Review advocate alert
              </Dialog.Title>
              <Dialog.Close className="text-slate-400 hover:text-slate-600 cursor-pointer transition-colors">
                <X size={16} />
              </Dialog.Close>
            </div>

            <Dialog.Description className="text-xs text-slate-500 mb-3">
              Review the message before sending. Nothing is sent without your approval.
            </Dialog.Description>

            <textarea
              readOnly
              value={draft}
              rows={8}
              className="w-full text-sm text-slate-700 bg-slate-50 border border-slate-200 rounded-lg p-3 resize-none font-mono leading-relaxed focus:outline-none"
            />

            <div className="flex items-center justify-between mt-4 pt-4 border-t border-slate-100">
              <Dialog.Close className="text-sm text-slate-500 hover:text-slate-700 cursor-pointer transition-colors">
                Cancel
              </Dialog.Close>
              <div className="flex items-center gap-2">
                <span className="text-xs text-slate-400 bg-slate-50 border border-slate-200 rounded px-2 py-1">
                  Twilio WhatsApp — coming soon
                </span>
                <button
                  disabled
                  className="inline-flex items-center gap-1.5 text-sm font-medium bg-teal-700 text-white px-4 py-2 rounded-lg opacity-40 cursor-not-allowed"
                >
                  <Send size={14} />
                  Confirm send
                </button>
              </div>
            </div>
          </motion.div>
        </Dialog.Content>
      </Dialog.Portal>
    </Dialog.Root>
  )
}
