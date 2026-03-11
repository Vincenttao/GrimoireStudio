import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Sparkles, Plus, Minus } from 'lucide-react';
import { cn } from '../lib/utils';
import { uuid } from '../lib/utils';
import type { CharacterEntity } from './CharacterCard';

interface CreateCharacterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (entity: CharacterEntity) => void;
  editingEntity?: CharacterEntity | null;
}

export default function CreateCharacterModal({ isOpen, onClose, onSubmit, editingEntity }: CreateCharacterModalProps) {
  const isEditing = !!editingEntity;

  const [name, setName] = useState(editingEntity?.name || '');
  const [personality, setPersonality] = useState(editingEntity?.base_attributes.personality || '');
  const [coreMotive, setCoreMotive] = useState(editingEntity?.base_attributes.core_motive || '');
  const [background, setBackground] = useState(editingEntity?.base_attributes.background || '');
  const [health, setHealth] = useState(editingEntity?.current_status.health || '100/100');
  const [aliases, setAliases] = useState<string[]>(editingEntity?.base_attributes.aliases || []);
  const [newAlias, setNewAlias] = useState('');

  const handleAddAlias = () => {
    if (newAlias.trim()) {
      setAliases([...aliases, newAlias.trim()]);
      setNewAlias('');
    }
  };

  const handleRemoveAlias = (index: number) => {
    setAliases(aliases.filter((_, i) => i !== index));
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!name.trim()) return;

    const now = new Date().toISOString();
    const entity: CharacterEntity = {
      entity_id: editingEntity?.entity_id || uuid(),
      type: 'CHARACTER',
      name: name.trim(),
      base_attributes: {
        aliases,
        personality: personality.trim(),
        core_motive: coreMotive.trim(),
        background: background.trim(),
      },
      current_status: {
        health: health.trim(),
        inventory: editingEntity?.current_status.inventory || [],
        relationships: editingEntity?.current_status.relationships || {},
        recent_memory_summary: editingEntity?.current_status.recent_memory_summary || [],
      },
      is_deleted: false,
      created_at: editingEntity?.created_at || now,
      updated_at: now,
    };

    onSubmit(entity);
  };

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          {/* Backdrop */}
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          />

          {/* Panel */}
          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 250 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-grimoire-surface border-l border-grimoire-border z-50 flex flex-col"
          >
            {/* Header */}
            <div className="flex items-center justify-between px-6 h-16 border-b border-grimoire-border flex-shrink-0">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-grimoire-accent-glow" />
                <h2 className="text-base font-semibold">
                  {isEditing ? 'Edit Character' : 'Create Character'}
                </h2>
              </div>
              <button onClick={onClose} className="p-2 rounded-lg hover:bg-grimoire-hover transition-colors">
                <X className="w-4 h-4 text-grimoire-text-muted" />
              </button>
            </div>

            {/* Form */}
            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">
              {/* Name */}
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  Character Name <span className="text-grimoire-danger">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-dark text-lg font-semibold"
                  placeholder="e.g., Artemis Blackthorn"
                  required
                  autoFocus
                />
              </div>

              {/* Aliases */}
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  Aliases
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={newAlias}
                    onChange={(e) => setNewAlias(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddAlias())}
                    className="input-dark flex-1"
                    placeholder="Add an alias..."
                  />
                  <button type="button" onClick={handleAddAlias} className="btn-ghost">
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
                {aliases.length > 0 && (
                  <div className="flex flex-wrap gap-1.5">
                    {aliases.map((alias, i) => (
                      <span
                        key={i}
                        className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-grimoire-accent/10 text-xs text-grimoire-accent-glow border border-grimoire-accent/20"
                      >
                        {alias}
                        <button type="button" onClick={() => handleRemoveAlias(i)}>
                          <Minus className="w-3 h-3" />
                        </button>
                      </span>
                    ))}
                  </div>
                )}
              </div>

              {/* Personality */}
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  Personality
                </label>
                <textarea
                  value={personality}
                  onChange={(e) => setPersonality(e.target.value)}
                  className="input-dark resize-none h-20"
                  placeholder="Stoic, calculating, secretly compassionate..."
                />
              </div>

              {/* Core Motive */}
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  Core Motive
                </label>
                <textarea
                  value={coreMotive}
                  onChange={(e) => setCoreMotive(e.target.value)}
                  className="input-dark resize-none h-16"
                  placeholder="What drives this character at their core?"
                />
              </div>

              {/* Background */}
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  Background
                </label>
                <textarea
                  value={background}
                  onChange={(e) => setBackground(e.target.value)}
                  className="input-dark resize-none h-20"
                  placeholder="A brief history or origin story..."
                />
              </div>

              {/* Health */}
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  Initial Health
                </label>
                <input
                  type="text"
                  value={health}
                  onChange={(e) => setHealth(e.target.value)}
                  className="input-dark"
                  placeholder="100/100"
                />
              </div>
            </form>

            {/* Footer */}
            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-grimoire-border flex-shrink-0">
              <button type="button" onClick={onClose} className="btn-ghost">
                Cancel
              </button>
              <button onClick={handleSubmit} className="btn-glow">
                {isEditing ? 'Save Changes' : 'Summon Character'}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
