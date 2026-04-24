import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Settings, Save, Loader2, Check, AlertCircle, Flame } from 'lucide-react';
import { settingsApi, PLATFORM_LABELS, type PlatformProfile } from '../lib/api';

interface ProjectSettings {
  id?: string;
  llm_model: string;
  llm_api_keys: {
    openai: string | null;
    anthropic: string | null;
    deepseek: string | null;
  };
  llm_api_base: string | null;
  max_turns: number;
  tension_threshold: number;
  default_render_mixer: {
    pov_type: string;
    style_template: string;
    subtext_ratio: number;
  };
  // V1.1
  target_platform: PlatformProfile;
  default_target_char_count: number;
  default_max_sent_len: number;
  ending_hook_guard_enabled: boolean;
  padding_detector_enabled: boolean;
  daily_streak_count: number;
  last_commit_at: string | null;
}

const DEFAULT_SETTINGS: ProjectSettings = {
  llm_model: 'gpt-4',
  llm_api_keys: {
    openai: '',
    anthropic: '',
    deepseek: '',
  },
  llm_api_base: '',
  max_turns: 12,
  tension_threshold: 0.8,
  default_render_mixer: {
    pov_type: 'OMNISCIENT',
    style_template: '热血爽文',
    subtext_ratio: 0.2,
  },
  target_platform: 'QIDIAN',
  default_target_char_count: 3000,
  default_max_sent_len: 30,
  ending_hook_guard_enabled: true,
  padding_detector_enabled: true,
  daily_streak_count: 0,
  last_commit_at: null,
};

const PLATFORM_OPTIONS: PlatformProfile[] = [
  'QIDIAN',
  'FANQIE',
  'JINJIANG',
  'ZONGHENG',
  'QIMAO',
  'CUSTOM',
];

export default function SettingsPage() {
  const [settings, setSettings] = useState<ProjectSettings>(DEFAULT_SETTINGS);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchSettings = useCallback(async () => {
    try {
      const data = await settingsApi.get();
      if (data.settings && typeof data.settings === 'object') {
        // Deep merge to ensure all fields exist
        const merged = {
          ...DEFAULT_SETTINGS,
          ...(data.settings as Partial<ProjectSettings>),
          llm_api_keys: {
            ...DEFAULT_SETTINGS.llm_api_keys,
            ...(data.settings as ProjectSettings).llm_api_keys,
          },
          default_render_mixer: {
            ...DEFAULT_SETTINGS.default_render_mixer,
            ...(data.settings as ProjectSettings).default_render_mixer,
          },
        };
        setSettings(merged);
      }
    } catch (err) {
      console.error('Failed to fetch settings:', err);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchSettings();
  }, [fetchSettings]);

  const handleSave = async () => {
    setSaving(true);
    setError(null);
    try {
      await settingsApi.update(settings);
      setSaved(true);
      setTimeout(() => setSaved(false), 2000);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save settings');
    } finally {
      setSaving(false);
    }
  };

  const updateRootField = <K extends keyof ProjectSettings>(key: K, value: ProjectSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

  const updateNestedField = (
    category: 'llm_api_keys' | 'default_render_mixer',
    key: string,
    value: string | number | null
  ) => {
    setSettings((prev) => ({
      ...prev,
      [category]: {
        ...prev[category],
        [key]: value,
      },
    }));
    setSaved(false);
  };

  if (loading) {
    return (
      <div className="flex-1 flex items-center justify-center">
        <Loader2 className="w-8 h-8 text-grimoire-accent animate-spin" />
      </div>
    );
  }

  return (
    <div className="flex-1 flex flex-col h-screen">
      {/* Header */}
      <header className="h-14 border-b border-grimoire-border flex items-center justify-between px-6 bg-grimoire-surface/50 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center gap-3">
          <Settings className="w-5 h-5 text-grimoire-accent-glow" />
          <h2 className="text-base font-semibold">Settings</h2>
          <span className="text-xs text-grimoire-text-muted font-mono">— Project Configuration</span>
        </div>
        <button
          onClick={handleSave}
          disabled={saving}
          className="btn-glow flex items-center gap-2"
        >
          {saving ? (
            <Loader2 className="w-4 h-4 animate-spin" />
          ) : saved ? (
            <Check className="w-4 h-4" />
          ) : (
            <Save className="w-4 h-4" />
          )}
          <span>{saving ? 'Saving...' : saved ? 'Saved!' : 'Save Settings'}</span>
        </button>
      </header>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-6">
        <div className="max-w-2xl mx-auto space-y-6 animate-fade-in">
          {error && (
            <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-grimoire-danger/10 border border-grimoire-danger/20">
              <AlertCircle className="w-4 h-4 text-grimoire-danger flex-shrink-0" />
              <p className="text-sm text-grimoire-danger">{error}</p>
            </div>
          )}

          {/* LLM Configuration */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-6 space-y-4"
          >
            <h3 className="text-base font-semibold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-grimoire-accent" />
              LLM Configuration
            </h3>
            <div className="space-y-4">
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">Model</label>
                <input
                  type="text"
                  className="input-dark"
                  value={settings.llm_model || ''}
                  onChange={(e) => updateRootField('llm_model', e.target.value)}
                  placeholder="e.g., gpt-4, claude-3-sonnet"
                />
                <p className="text-[10px] text-grimoire-text-muted mt-1">
                  Supports all LiteLLM-compatible model identifiers
                </p>
              </div>
              
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">OpenAI Key</label>
                  <input
                    type="password"
                    className="input-dark"
                    value={settings.llm_api_keys.openai || ''}
                    onChange={(e) => updateNestedField('llm_api_keys', 'openai', e.target.value)}
                    placeholder="sk-..."
                  />
                </div>
                <div>
                  <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">Anthropic Key</label>
                  <input
                    type="password"
                    className="input-dark"
                    value={settings.llm_api_keys.anthropic || ''}
                    onChange={(e) => updateNestedField('llm_api_keys', 'anthropic', e.target.value)}
                    placeholder="sk-ant-..."
                  />
                </div>
              </div>

              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">API Base URL</label>
                <input
                  type="text"
                  className="input-dark"
                  value={settings.llm_api_base || ''}
                  onChange={(e) => updateRootField('llm_api_base', e.target.value)}
                  placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
                />
                <p className="text-[10px] text-grimoire-text-muted mt-1">
                  自定义 OpenAI 兼容端点（阿里云、DeepSeek 等）。留空则使用供应商默认地址
                </p>
              </div>
            </div>
          </motion.div>

          {/* V1.1: 网文作坊参数 */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.05 }}
            className="glass-card p-6 space-y-4"
          >
            <h3 className="text-base font-semibold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-grimoire-gold" />
              网文作坊参数 (V1.1)
            </h3>

            {/* 连胜显示 */}
            {settings.daily_streak_count > 0 && (
              <div className="flex items-center gap-3 px-4 py-3 rounded-lg bg-grimoire-gold/5 border border-grimoire-gold/30">
                <Flame className="w-5 h-5 text-grimoire-gold" />
                <div>
                  <p className="text-xs text-grimoire-text-muted">连续日更</p>
                  <p className="text-lg font-semibold text-grimoire-gold">
                    {settings.daily_streak_count} 天 🔥
                  </p>
                </div>
                {settings.last_commit_at && (
                  <div className="ml-auto text-right">
                    <p className="text-[10px] text-grimoire-text-muted">上次 Commit</p>
                    <p className="text-xs text-grimoire-text">
                      {new Date(settings.last_commit_at).toLocaleString()}
                    </p>
                  </div>
                )}
              </div>
            )}

            <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  目标平台
                </label>
                <select
                  className="input-dark"
                  value={settings.target_platform}
                  onChange={(e) =>
                    updateRootField('target_platform', e.target.value as PlatformProfile)
                  }
                >
                  {PLATFORM_OPTIONS.map((p) => (
                    <option key={p} value={p}>
                      {PLATFORM_LABELS[p]}
                    </option>
                  ))}
                </select>
                <p className="text-[10px] text-grimoire-text-muted mt-1">
                  切换后 Render Mixer 默认值会跟着平台走
                </p>
              </div>
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  默认章节字数
                </label>
                <input
                  type="number"
                  className="input-dark"
                  value={settings.default_target_char_count}
                  onChange={(e) =>
                    updateRootField(
                      'default_target_char_count',
                      parseInt(e.target.value) || 3000
                    )
                  }
                  min={500}
                  max={20000}
                  step={100}
                />
                <p className="text-[10px] text-grimoire-text-muted mt-1">Camera 渲染硬约束 ±10%</p>
              </div>
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  默认最大句长
                </label>
                <input
                  type="number"
                  className="input-dark"
                  value={settings.default_max_sent_len}
                  onChange={(e) =>
                    updateRootField('default_max_sent_len', parseInt(e.target.value) || 30)
                  }
                  min={10}
                  max={100}
                />
                <p className="text-[10px] text-grimoire-text-muted mt-1">
                  番茄/七猫类短句平台用 18-20
                </p>
              </div>
              <div className="flex flex-col gap-2">
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider">
                  渲染守卫
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.ending_hook_guard_enabled}
                    onChange={(e) =>
                      updateRootField('ending_hook_guard_enabled', e.target.checked)
                    }
                  />
                  <span className="text-xs">章末钩子守卫</span>
                </label>
                <label className="flex items-center gap-2 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={settings.padding_detector_enabled}
                    onChange={(e) =>
                      updateRootField('padding_detector_enabled', e.target.checked)
                    }
                  />
                  <span className="text-xs">水字数检测</span>
                </label>
              </div>
            </div>
          </motion.div>

          {/* Maestro Tuning */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="glass-card p-6 space-y-4"
          >
            <h3 className="text-base font-semibold flex items-center gap-2">
              <span className="w-2 h-2 rounded-full bg-grimoire-gold" />
              Maestro Tuning
            </h3>
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  Max Turns
                </label>
                <input
                  type="number"
                  className="input-dark"
                  value={settings.max_turns}
                  onChange={(e) => updateRootField('max_turns', parseInt(e.target.value) || 12)}
                  min={1}
                  max={50}
                />
                <p className="text-[10px] text-grimoire-text-muted mt-1">Per scene beat</p>
              </div>
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  Tension Threshold
                </label>
                <input
                  type="number"
                  className="input-dark"
                  value={settings.tension_threshold}
                  onChange={(e) => updateRootField('tension_threshold', parseFloat(e.target.value) || 0.8)}
                  min={0}
                  max={1}
                  step={0.05}
                />
                <p className="text-[10px] text-grimoire-text-muted mt-1">Climax signal (0-1)</p>
              </div>
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  Subtext Ratio
                </label>
                <input
                  type="number"
                  className="input-dark"
                  value={settings.default_render_mixer.subtext_ratio}
                  onChange={(e) => updateNestedField('default_render_mixer', 'subtext_ratio', parseFloat(e.target.value) || 0.3)}
                  min={0}
                  max={1}
                  step={0.05}
                />
                <p className="text-[10px] text-grimoire-text-muted mt-1">Hidden narrative %</p>
              </div>
            </div>
          </motion.div>

          {/* System Info */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="glass-card p-6"
          >
            <h3 className="text-base font-semibold flex items-center gap-2 mb-4">
              <span className="w-2 h-2 rounded-full bg-grimoire-info" />
              System
            </h3>
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <p className="text-grimoire-text-muted text-xs">Engine</p>
                <p className="text-grimoire-text font-mono">Genesis v1.0.0-MVP</p>
              </div>
              <div>
                <p className="text-grimoire-text-muted text-xs">Database</p>
                <p className="text-grimoire-text font-mono">SQLite (WAL)</p>
              </div>
              <div>
                <p className="text-grimoire-text-muted text-xs">Architecture</p>
                <p className="text-grimoire-text font-mono">Monolith (Single User)</p>
              </div>
              <div>
                <p className="text-grimoire-text-muted text-xs">Frontend</p>
                <p className="text-grimoire-text font-mono">Vite + React + TS</p>
              </div>
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  );
}
