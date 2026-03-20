import { useState, useEffect, useCallback, useRef } from 'react';
import { Camera, Type, Eye } from 'lucide-react';
import { motion } from 'framer-motion';
import { renderApi, type RenderMixerSettings } from '../lib/api';

const POV_OPTIONS: { value: RenderMixerSettings['pov_type']; label: string }[] = [
  { value: 'OMNISCIENT', label: 'Omniscient' },
  { value: 'FIRST_PERSON', label: 'First Person' },
  { value: 'CHARACTER_LIMITED', label: 'Character Limited' },
];

export default function RenderMixer() {
  const [povType, setPovType] = useState<RenderMixerSettings['pov_type']>('OMNISCIENT');
  const [styleTemplate, setStyleTemplate] = useState('Standard');
  const [subtextRatio, setSubtextRatio] = useState(0.5);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch settings on mount
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await renderApi.getSettings();
        const mixer = response.settings.default_render_mixer;
        if (mixer) {
          setPovType(mixer.pov_type);
          setStyleTemplate(mixer.style_template);
          setSubtextRatio(mixer.subtext_ratio);
        }
      } catch {
        // Backend may be offline — use defaults
      } finally {
        setLoading(false);
      }
    };
    fetchSettings();
  }, []);

  // Debounced save function
  const saveSettings = useCallback(
    async (updates: Partial<RenderMixerSettings>) => {
      if (debounceRef.current) {
        clearTimeout(debounceRef.current);
      }

      debounceRef.current = setTimeout(async () => {
        setSaving(true);
        try {
          await renderApi.adjust(updates);
        } catch {
          // Error handled silently
        } finally {
          setSaving(false);
        }
      }, 300);
    },
    []
  );

  const handlePovChange = (value: RenderMixerSettings['pov_type']) => {
    setPovType(value);
    saveSettings({ pov_type: value });
  };

  const handleStyleChange = (value: string) => {
    setStyleTemplate(value);
    saveSettings({ style_template: value });
  };

  const handleSubtextChange = (value: number) => {
    setSubtextRatio(value);
    saveSettings({ subtext_ratio: value });
  };

  if (loading) {
    return (
      <div className="flex items-center gap-2 px-3 py-1.5 rounded-lg bg-grimoire-card/50 border border-grimoire-border">
        <Camera className="w-4 h-4 text-grimoire-text-muted animate-pulse" />
        <span className="text-xs text-grimoire-text-muted">Loading...</span>
      </div>
    );
  }

  return (
    <motion.div
      initial={{ opacity: 0, x: 10 }}
      animate={{ opacity: 1, x: 0 }}
      className="flex items-center gap-4 px-4 py-2 rounded-xl bg-grimoire-card/60 backdrop-blur-md border border-grimoire-border/50"
    >
      {/* POV Type Dropdown */}
      <div className="flex items-center gap-2">
        <Eye className="w-3.5 h-3.5 text-grimoire-gold" />
        <select
          value={povType}
          onChange={(e) => handlePovChange(e.target.value as RenderMixerSettings['pov_type'])}
          className="text-xs bg-grimoire-surface border border-grimoire-border rounded-md px-2 py-1 text-grimoire-text focus:outline-none focus:border-grimoire-accent focus:ring-1 focus:ring-grimoire-accent/30 transition-all cursor-pointer min-w-[110px]"
        >
          {POV_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-grimoire-card">
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-grimoire-border/50" />

      {/* Style Template Input */}
      <div className="flex items-center gap-2">
        <Type className="w-3.5 h-3.5 text-grimoire-accent-glow" />
        <input
          type="text"
          value={styleTemplate}
          onChange={(e) => handleStyleChange(e.target.value)}
          placeholder="Style..."
          className="text-xs bg-grimoire-surface border border-grimoire-border rounded-md px-2 py-1 text-grimoire-text placeholder-grimoire-text-muted focus:outline-none focus:border-grimoire-accent focus:ring-1 focus:ring-grimoire-accent/30 transition-all w-24"
        />
      </div>

      {/* Divider */}
      <div className="w-px h-6 bg-grimoire-border/50" />

      {/* Subtext Ratio Slider */}
      <div className="flex items-center gap-3">
        <span className="text-[10px] uppercase tracking-wider text-grimoire-text-muted font-mono">
          Subtext
        </span>
        <div className="flex items-center gap-2">
          <input
            type="range"
            min="0"
            max="1"
            step="0.05"
            value={subtextRatio}
            onChange={(e) => handleSubtextChange(parseFloat(e.target.value))}
            className="w-20 h-1.5 bg-grimoire-border rounded-full appearance-none cursor-pointer accent-grimoire-accent-glow [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-grimoire-accent-glow [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:shadow-grimoire-accent/50 [&::-webkit-slider-thumb]:transition-transform [&::-webkit-slider-thumb]:hover:scale-110"
          />
          <span className="text-[10px] font-mono text-grimoire-text-dim w-8 text-right">
            {Math.round(subtextRatio * 100)}%
          </span>
        </div>
      </div>

      {/* Saving indicator */}
      {saving && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.8 }}
          className="absolute -top-1 -right-1 w-2 h-2 rounded-full bg-grimoire-accent animate-pulse"
        />
      )}
    </motion.div>
  );
}
