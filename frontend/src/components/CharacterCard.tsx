import { motion } from 'framer-motion';
import { Trash2, Edit3, Heart, Package, Brain } from 'lucide-react';
import { cn } from '../lib/utils';

export interface CharacterEntity {
  entity_id: string;
  type: string;
  name: string;
  base_attributes: {
    aliases?: string[];
    personality: string;
    core_motive: string;
    background: string;
  };
  current_status: {
    health: string;
    inventory: string[];
    relationships: Record<string, string>;
    recent_memory_summary: string[];
  };
  is_deleted: boolean;
  created_at: string;
  updated_at: string;
}

interface CharacterCardProps {
  entity: CharacterEntity;
  onEdit: (entity: CharacterEntity) => void;
  onDelete: (entityId: string) => void;
}

export default function CharacterCard({ entity, onEdit, onDelete }: CharacterCardProps) {
  const relationshipCount = Object.keys(entity.current_status.relationships).length;
  const memoryCount = entity.current_status.recent_memory_summary.length;

  return (
    <motion.div
      layout
      initial={{ opacity: 0, scale: 0.95 }}
      animate={{ opacity: 1, scale: 1 }}
      exit={{ opacity: 0, scale: 0.9 }}
      whileHover={{ y: -2 }}
      className="glass-card p-5 group relative overflow-hidden"
    >
      {/* Accent line */}
      <div className="absolute top-0 left-0 right-0 h-0.5 bg-gradient-to-r from-grimoire-accent via-grimoire-accent-glow to-grimoire-gold" />

      {/* Header */}
      <div className="flex items-start justify-between mb-4">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-grimoire-accent/30 to-grimoire-gold/20 flex items-center justify-center border border-grimoire-accent/20">
            <span className="text-lg font-bold text-grimoire-accent-glow">
              {entity.name.charAt(0).toUpperCase()}
            </span>
          </div>
          <div>
            <h3 className="font-semibold text-grimoire-text">{entity.name}</h3>
            <p className="text-[10px] uppercase tracking-wider text-grimoire-text-muted font-mono">
              {entity.type}
              {entity.base_attributes.aliases && entity.base_attributes.aliases.length > 0 && (
                <span className="ml-2 text-grimoire-text-dim">
                  aka {entity.base_attributes.aliases.join(', ')}
                </span>
              )}
            </p>
          </div>
        </div>

        {/* Actions */}
        <div className="flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <button
            onClick={() => onEdit(entity)}
            className="p-1.5 rounded-lg hover:bg-grimoire-hover text-grimoire-text-muted hover:text-grimoire-text transition-colors"
            title="Edit"
          >
            <Edit3 className="w-3.5 h-3.5" />
          </button>
          <button
            onClick={() => onDelete(entity.entity_id)}
            className="p-1.5 rounded-lg hover:bg-grimoire-danger/10 text-grimoire-text-muted hover:text-grimoire-danger transition-colors"
            title="Delete"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>

      {/* Core Attributes */}
      <div className="space-y-2.5 mb-4">
        <div>
          <p className="text-[10px] uppercase tracking-wider text-grimoire-text-muted mb-0.5">Personality</p>
          <p className="text-xs text-grimoire-text-dim leading-relaxed line-clamp-2">
            {entity.base_attributes.personality || '—'}
          </p>
        </div>
        <div>
          <p className="text-[10px] uppercase tracking-wider text-grimoire-text-muted mb-0.5">Core Motive</p>
          <p className="text-xs text-grimoire-text-dim leading-relaxed line-clamp-2">
            {entity.base_attributes.core_motive || '—'}
          </p>
        </div>
      </div>

      {/* Status Chips */}
      <div className="flex flex-wrap gap-2 pt-3 border-t border-grimoire-border">
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-grimoire-surface text-[10px]">
          <Heart className="w-3 h-3 text-grimoire-danger" />
          <span className="text-grimoire-text-dim">{entity.current_status.health}</span>
        </div>
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-grimoire-surface text-[10px]">
          <Package className="w-3 h-3 text-grimoire-gold" />
          <span className="text-grimoire-text-dim">{entity.current_status.inventory.length} items</span>
        </div>
        <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-grimoire-surface text-[10px]">
          <Brain className="w-3 h-3 text-grimoire-accent-glow" />
          <span className="text-grimoire-text-dim">{memoryCount} memories</span>
        </div>
        {relationshipCount > 0 && (
          <div className="flex items-center gap-1.5 px-2 py-1 rounded-md bg-grimoire-surface text-[10px]">
            <span className="text-grimoire-info">🔗</span>
            <span className="text-grimoire-text-dim">{relationshipCount} bonds</span>
          </div>
        )}
      </div>
    </motion.div>
  );
}
