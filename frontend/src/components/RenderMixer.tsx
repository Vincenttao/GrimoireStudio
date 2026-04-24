import { useState, useEffect, useCallback, useRef } from 'react';
import { Camera, Type, Eye, Target, Radio } from 'lucide-react';
import { motion } from 'framer-motion';
import {
  renderApi,
  settingsApi,
  PLATFORM_LABELS,
  type RenderMixerSettings,
  type PlatformProfile,
} from '../lib/api';

const POV_OPTIONS: { value: RenderMixerSettings['pov_type']; label: string }[] = [
  { value: 'OMNISCIENT', label: '上帝视角' },
  { value: 'FIRST_PERSON', label: '第一人称' },
  { value: 'CHARACTER_LIMITED', label: '限制视角' },
];

const PLATFORM_OPTIONS: PlatformProfile[] = [
  'QIDIAN',
  'FANQIE',
  'JINJIANG',
  'ZONGHENG',
  'QIMAO',
  'CUSTOM',
];

export default function RenderMixer() {
  const [povType, setPovType] = useState<RenderMixerSettings['pov_type']>('OMNISCIENT');
  const [styleTemplate, setStyleTemplate] = useState('热血爽文');
  const [subtextRatio, setSubtextRatio] = useState(0.2);
  const [platform, setPlatform] = useState<PlatformProfile>('QIDIAN');
  const [targetCharCount, setTargetCharCount] = useState(3000);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Fetch settings on mount
  useEffect(() => {
    const fetchSettings = async () => {
      try {
        const response = await settingsApi.get();
        const s = response.settings as {
          default_render_mixer?: RenderMixerSettings;
          target_platform?: PlatformProfile;
          default_target_char_count?: number;
        };
        if (s?.default_render_mixer) {
          setPovType(s.default_render_mixer.pov_type);
          setStyleTemplate(s.default_render_mixer.style_template);
          setSubtextRatio(s.default_render_mixer.subtext_ratio);
        }
        if (s?.target_platform) setPlatform(s.target_platform);
        if (s?.default_target_char_count) setTargetCharCount(s.default_target_char_count);
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

  const handlePlatformChange = async (value: PlatformProfile) => {
    setPlatform(value);
    setSaving(true);
    try {
      const r = await renderApi.switchPlatform(value);
      // 同步 UI 到新预设
      setPovType(r.default_render_mixer.pov_type);
      setStyleTemplate(r.default_render_mixer.style_template);
      setSubtextRatio(r.default_render_mixer.subtext_ratio);
      setTargetCharCount(r.default_target_char_count);
    } catch {
      // ignore
    } finally {
      setSaving(false);
    }
  };

  const handleTargetCharCountChange = async (value: number) => {
    setTargetCharCount(value);
    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(async () => {
      setSaving(true);
      try {
        await settingsApi.update({ default_target_char_count: value });
      } catch {
        // ignore
      } finally {
        setSaving(false);
      }
    }, 400);
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
      className="flex items-center gap-3 px-4 py-2 rounded-xl bg-grimoire-card/60 backdrop-blur-md border border-grimoire-border/50 flex-wrap"
    >
      {/* Platform */}
      <div className="flex items-center gap-2">
        <Radio className="w-3.5 h-3.5 text-grimoire-gold" />
        <select
          value={platform}
          onChange={(e) => handlePlatformChange(e.target.value as PlatformProfile)}
          className="text-xs bg-grimoire-surface border border-grimoire-border rounded-md px-2 py-1 text-grimoire-text focus:outline-none focus:border-grimoire-accent focus:ring-1 focus:ring-grimoire-accent/30 transition-all cursor-pointer min-w-[120px]"
          title="目标平台 — 切换后默认参数会自动更新"
        >
          {PLATFORM_OPTIONS.map((p) => (
            <option key={p} value={p} className="bg-grimoire-card">
              {PLATFORM_LABELS[p]}
            </option>
          ))}
        </select>
      </div>

      <div className="w-px h-6 bg-grimoire-border/50" />

      {/* POV */}
      <div className="flex items-center gap-2">
        <Eye className="w-3.5 h-3.5 text-grimoire-gold" />
        <select
          value={povType}
          onChange={(e) => handlePovChange(e.target.value as RenderMixerSettings['pov_type'])}
          className="text-xs bg-grimoire-surface border border-grimoire-border rounded-md px-2 py-1 text-grimoire-text focus:outline-none focus:border-grimoire-accent focus:ring-1 focus:ring-grimoire-accent/30 transition-all cursor-pointer min-w-[100px]"
        >
          {POV_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value} className="bg-grimoire-card">
              {opt.label}
            </option>
          ))}
        </select>
      </div>

      <div className="w-px h-6 bg-grimoire-border/50" />

      {/* Style */}
      <div className="flex items-center gap-2">
        <Type className="w-3.5 h-3.5 text-grimoire-accent-glow" />
        <input
          type="text"
          value={styleTemplate}
          onChange={(e) => handleStyleChange(e.target.value)}
          placeholder="文风"
          className="text-xs bg-grimoire-surface border border-grimoire-border rounded-md px-2 py-1 text-grimoire-text placeholder-grimoire-text-muted focus:outline-none focus:border-grimoire-accent focus:ring-1 focus:ring-grimoire-accent/30 transition-all w-28"
        />
      </div>

      <div className="w-px h-6 bg-grimoire-border/50" />

      {/* Target char count */}
      <div className="flex items-center gap-2">
        <Target className="w-3.5 h-3.5 text-grimoire-accent" />
        <input
          type="number"
          min={500}
          max={20000}
          step={100}
          value={targetCharCount}
          onChange={(e) => handleTargetCharCountChange(parseInt(e.target.value) || 3000)}
          className="text-xs bg-grimoire-surface border border-grimoire-border rounded-md px-2 py-1 text-grimoire-text focus:outline-none focus:border-grimoire-accent focus:ring-1 focus:ring-grimoire-accent/30 transition-all w-20"
          title="目标字数（±10%）"
        />
        <span className="text-[10px] text-grimoire-text-muted font-mono">字</span>
      </div>

      <div className="w-px h-6 bg-grimoire-border/50" />

      {/* Subtext slider */}
      <div className="flex items-center gap-2">
        <span className="text-[10px] uppercase tracking-wider text-grimoire-text-muted font-mono">
          潜台词
        </span>
        <input
          type="range"
          min="0"
          max="1"
          step="0.05"
          value={subtextRatio}
          onChange={(e) => handleSubtextChange(parseFloat(e.target.value))}
          className="w-20 h-1.5 bg-grimoire-border rounded-full appearance-none cursor-pointer accent-grimoire-accent-glow [&::-webkit-slider-thumb]:appearance-none [&::-webkit-slider-thumb]:w-3 [&::-webkit-slider-thumb]:h-3 [&::-webkit-slider-thumb]:rounded-full [&::-webkit-slider-thumb]:bg-grimoire-accent-glow [&::-webkit-slider-thumb]:shadow-lg [&::-webkit-slider-thumb]:shadow-grimoire-accent/50"
        />
        <span className="text-[10px] font-mono text-grimoire-text-dim w-8 text-right">
          {Math.round(subtextRatio * 100)}%
        </span>
      </div>

      {saving && (
        <motion.div
          initial={{ opacity: 0, scale: 0.8 }}
          animate={{ opacity: 1, scale: 1 }}
          className="w-2 h-2 rounded-full bg-grimoire-accent animate-pulse"
        />
      )}
    </motion.div>
  );
}
