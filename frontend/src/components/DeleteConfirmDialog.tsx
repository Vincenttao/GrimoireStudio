import { motion, AnimatePresence } from 'framer-motion';
import { AlertTriangle } from 'lucide-react';

interface DeleteConfirmDialogProps {
  isOpen: boolean;
  entityName: string;
  onConfirm: () => void;
  onCancel: () => void;
}

export default function DeleteConfirmDialog({ isOpen, entityName, onConfirm, onCancel }: DeleteConfirmDialogProps) {
  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onCancel}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-50"
          />
          <motion.div
            initial={{ opacity: 0, scale: 0.9 }}
            animate={{ opacity: 1, scale: 1 }}
            exit={{ opacity: 0, scale: 0.9 }}
            className="fixed left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 w-full max-w-sm glass-card p-6 z-50"
          >
            <div className="flex items-start gap-4 mb-4">
              <div className="w-10 h-10 rounded-xl bg-grimoire-danger/10 flex items-center justify-center flex-shrink-0">
                <AlertTriangle className="w-5 h-5 text-grimoire-danger" />
              </div>
              <div>
                <h3 className="font-semibold text-grimoire-text mb-1">Remove Character</h3>
                <p className="text-sm text-grimoire-text-dim">
                  Are you sure you want to remove <strong className="text-grimoire-text">{entityName}</strong>? 
                  This performs a soft-delete — the character can be restored later.
                </p>
              </div>
            </div>
            <div className="flex justify-end gap-3 mt-6">
              <button onClick={onCancel} className="btn-ghost">Cancel</button>
              <button onClick={onConfirm} className="btn-danger">Remove</button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
