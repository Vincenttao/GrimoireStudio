import { useState, useEffect, useCallback } from 'react';
import { motion } from 'framer-motion';
import { Settings, Save, Loader2, Check, AlertCircle } from 'lucide-react';
import { settingsApi } from '../lib/api';

interface ProjectSettings {
  llm_model: string;
  llm_api_key: string;
  llm_api_base: string;
  max_turns: number;
  tension_threshold: number;
  subtext_ratio: number;
}

const DEFAULT_SETTINGS: ProjectSettings = {
  llm_model: 'gpt-4',
  llm_api_key: '',
  llm_api_base: '',
  max_turns: 12,
  tension_threshold: 0.8,
  subtext_ratio: 0.3,
};

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
        setSettings({ ...DEFAULT_SETTINGS, ...(data.settings as Partial<ProjectSettings>) });
      }
    } catch {
      // Use defaults if backend is offline
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

  const updateField = <K extends keyof ProjectSettings>(key: K, value: ProjectSettings[K]) => {
    setSettings((prev) => ({ ...prev, [key]: value }));
    setSaved(false);
  };

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
                  value={settings.llm_model}
                  onChange={(e) => updateField('llm_model', e.target.value)}
                  placeholder="e.g., gpt-4, claude-3-sonnet"
                />
                <p className="text-[10px] text-grimoire-text-muted mt-1">
                  Supports all LiteLLM-compatible model identifiers
                </p>
              </div>
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">API Key</label>
                <input
                  type="password"
                  className="input-dark"
                  value={settings.llm_api_key}
                  onChange={(e) => updateField('llm_api_key', e.target.value)}
                  placeholder="sk-..."
                />
              </div>
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">API Base URL</label>
                <input
                  type="text"
                  className="input-dark"
                  value={settings.llm_api_base}
                  onChange={(e) => updateField('llm_api_base', e.target.value)}
                  placeholder="https://dashscope.aliyuncs.com/compatible-mode/v1"
                />
                <p className="text-[10px] text-grimoire-text-muted mt-1">
                  自定义 OpenAI 兼容端点（阿里云、DeepSeek 等）。留空则使用供应商默认地址
                </p>
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
                  onChange={(e) => updateField('max_turns', parseInt(e.target.value) || 12)}
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
                  onChange={(e) => updateField('tension_threshold', parseFloat(e.target.value) || 0.8)}
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
                  value={settings.subtext_ratio}
                  onChange={(e) => updateField('subtext_ratio', parseFloat(e.target.value) || 0.3)}
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
