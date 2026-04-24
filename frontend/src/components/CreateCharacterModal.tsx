import { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { X, Sparkles, Plus, Minus, ChevronDown, ChevronRight, MessageCircle } from 'lucide-react';
import { uuid } from '../lib/utils';
import type { CharacterEntity } from './CharacterCard';

interface CreateCharacterModalProps {
  isOpen: boolean;
  onClose: () => void;
  onSubmit: (entity: CharacterEntity) => void;
  editingEntity?: CharacterEntity | null;
}

export default function CreateCharacterModal({
  isOpen,
  onClose,
  onSubmit,
  editingEntity,
}: CreateCharacterModalProps) {
  const isEditing = !!editingEntity;

  const [name, setName] = useState(editingEntity?.name || '');
  const [personality, setPersonality] = useState(editingEntity?.base_attributes.personality || '');
  const [coreMotive, setCoreMotive] = useState(editingEntity?.base_attributes.core_motive || '');
  const [background, setBackground] = useState(editingEntity?.base_attributes.background || '');
  const [health, setHealth] = useState(editingEntity?.current_status.health || '良好');
  const [aliases, setAliases] = useState<string[]>(editingEntity?.base_attributes.aliases || []);
  const [newAlias, setNewAlias] = useState('');

  // V1.1: VoiceSignature
  const [voiceOpen, setVoiceOpen] = useState(
    !!(editingEntity?.voice_signature?.catchphrases?.length ||
      editingEntity?.voice_signature?.forbidden_words?.length)
  );
  const [catchphrases, setCatchphrases] = useState<string[]>(
    editingEntity?.voice_signature?.catchphrases || []
  );
  const [newCatchphrase, setNewCatchphrase] = useState('');
  const [forbiddenWords, setForbiddenWords] = useState<string[]>(
    editingEntity?.voice_signature?.forbidden_words || []
  );
  const [newForbidden, setNewForbidden] = useState('');
  const [sampleUtterances, setSampleUtterances] = useState<string[]>(
    editingEntity?.voice_signature?.sample_utterances || []
  );
  const [newSample, setNewSample] = useState('');
  const [toneKeywords, setToneKeywords] = useState<string[]>(
    editingEntity?.voice_signature?.tone_keywords || []
  );
  const [newTone, setNewTone] = useState('');

  const handleAddAlias = () => {
    if (newAlias.trim()) {
      setAliases([...aliases, newAlias.trim()]);
      setNewAlias('');
    }
  };

  const handleRemoveAlias = (index: number) => {
    setAliases(aliases.filter((_, i) => i !== index));
  };

  const addTo = (value: string, setValue: (s: string) => void, list: string[], setList: (l: string[]) => void) => {
    if (value.trim()) {
      setList([...list, value.trim()]);
      setValue('');
    }
  };

  const hasVoiceSig =
    catchphrases.length || forbiddenWords.length || sampleUtterances.length || toneKeywords.length;

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
      voice_signature: hasVoiceSig
        ? {
            catchphrases,
            catchphrase_min_freq_chapters: 10,
            honorifics: editingEntity?.voice_signature?.honorifics || {},
            forbidden_words: forbiddenWords,
            sample_utterances: sampleUtterances,
            tone_keywords: toneKeywords,
          }
        : null,
      is_deleted: false,
      created_at: editingEntity?.created_at || now,
      updated_at: now,
    };

    onSubmit(entity);
  };

  const ChipList = ({ items, onRemove }: { items: string[]; onRemove: (i: number) => void }) => (
    <div className="flex flex-wrap gap-1.5">
      {items.map((v, i) => (
        <span
          key={i}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded-md bg-grimoire-accent/10 text-xs text-grimoire-accent-glow border border-grimoire-accent/20"
        >
          {v}
          <button type="button" onClick={() => onRemove(i)}>
            <Minus className="w-3 h-3" />
          </button>
        </span>
      ))}
    </div>
  );

  return (
    <AnimatePresence>
      {isOpen && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            onClick={onClose}
            className="fixed inset-0 bg-black/60 backdrop-blur-sm z-40"
          />

          <motion.div
            initial={{ x: '100%' }}
            animate={{ x: 0 }}
            exit={{ x: '100%' }}
            transition={{ type: 'spring', damping: 25, stiffness: 250 }}
            className="fixed right-0 top-0 bottom-0 w-full max-w-lg bg-grimoire-surface border-l border-grimoire-border z-50 flex flex-col"
          >
            <div className="flex items-center justify-between px-6 h-16 border-b border-grimoire-border flex-shrink-0">
              <div className="flex items-center gap-3">
                <Sparkles className="w-5 h-5 text-grimoire-accent-glow" />
                <h2 className="text-base font-semibold">
                  {isEditing ? '编辑角色' : '创建角色'}
                </h2>
              </div>
              <button onClick={onClose} className="p-2 rounded-lg hover:bg-grimoire-hover transition-colors">
                <X className="w-4 h-4 text-grimoire-text-muted" />
              </button>
            </div>

            <form onSubmit={handleSubmit} className="flex-1 overflow-y-auto p-6 space-y-5">
              {/* Name */}
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  角色姓名 <span className="text-grimoire-danger">*</span>
                </label>
                <input
                  type="text"
                  value={name}
                  onChange={(e) => setName(e.target.value)}
                  className="input-dark text-lg font-semibold"
                  placeholder="如：宁毅"
                  required
                  autoFocus
                />
              </div>

              {/* Aliases */}
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  别名
                </label>
                <div className="flex gap-2 mb-2">
                  <input
                    type="text"
                    value={newAlias}
                    onChange={(e) => setNewAlias(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && (e.preventDefault(), handleAddAlias())}
                    className="input-dark flex-1"
                    placeholder="添加一个别名..."
                  />
                  <button type="button" onClick={handleAddAlias} className="btn-ghost">
                    <Plus className="w-4 h-4" />
                  </button>
                </div>
                {aliases.length > 0 && <ChipList items={aliases} onRemove={handleRemoveAlias} />}
              </div>

              {/* Personality */}
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  性格
                </label>
                <textarea
                  value={personality}
                  onChange={(e) => setPersonality(e.target.value)}
                  className="input-dark resize-none h-20"
                  placeholder="散漫玩世不恭，实则心思缜密..."
                />
              </div>

              {/* Core Motive */}
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  核心动机
                </label>
                <textarea
                  value={coreMotive}
                  onChange={(e) => setCoreMotive(e.target.value)}
                  className="input-dark resize-none h-16"
                  placeholder="这个角色最底层的驱动力是什么？"
                />
              </div>

              {/* Background */}
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  背景
                </label>
                <textarea
                  value={background}
                  onChange={(e) => setBackground(e.target.value)}
                  className="input-dark resize-none h-20"
                  placeholder="简短的出身/前史..."
                />
              </div>

              {/* Health */}
              <div>
                <label className="text-xs text-grimoire-text-muted uppercase tracking-wider mb-1.5 block">
                  初始状态
                </label>
                <input
                  type="text"
                  value={health}
                  onChange={(e) => setHealth(e.target.value)}
                  className="input-dark"
                  placeholder="良好"
                />
              </div>

              {/* V1.1: VoiceSignature collapsible */}
              <div className="border-t border-grimoire-border pt-4">
                <button
                  type="button"
                  onClick={() => setVoiceOpen(!voiceOpen)}
                  className="w-full flex items-center justify-between text-xs uppercase tracking-wider text-grimoire-gold hover:text-grimoire-gold-glow transition-colors"
                >
                  <span className="flex items-center gap-2">
                    <MessageCircle className="w-3.5 h-3.5" />
                    声音签名（VoiceSignature）— 防 OOC
                  </span>
                  {voiceOpen ? <ChevronDown className="w-4 h-4" /> : <ChevronRight className="w-4 h-4" />}
                </button>
                <p className="text-[10px] text-grimoire-text-muted mt-1">
                  口头禅、禁用词、范本台词 — Scribe 会用 grep 级检测防止角色说话跑偏。
                </p>

                {voiceOpen && (
                  <div className="mt-4 space-y-4">
                    {/* Catchphrases */}
                    <div>
                      <label className="text-[10px] text-grimoire-text-muted uppercase tracking-wider mb-1 block">
                        口头禅 · 每 10 章至少出现一次
                      </label>
                      <div className="flex gap-2 mb-2">
                        <input
                          type="text"
                          value={newCatchphrase}
                          onChange={(e) => setNewCatchphrase(e.target.value)}
                          onKeyDown={(e) =>
                            e.key === 'Enter' &&
                            (e.preventDefault(),
                            addTo(newCatchphrase, setNewCatchphrase, catchphrases, setCatchphrases))
                          }
                          className="input-dark flex-1 text-xs"
                          placeholder="如：大人，时代变了"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            addTo(newCatchphrase, setNewCatchphrase, catchphrases, setCatchphrases)
                          }
                          className="btn-ghost"
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                      </div>
                      {catchphrases.length > 0 && (
                        <ChipList
                          items={catchphrases}
                          onRemove={(i) => setCatchphrases(catchphrases.filter((_, idx) => idx !== i))}
                        />
                      )}
                    </div>

                    {/* Forbidden words */}
                    <div>
                      <label className="text-[10px] text-grimoire-text-muted uppercase tracking-wider mb-1 block">
                        禁用词 · 命中硬失败（阻断 Commit）
                      </label>
                      <div className="flex gap-2 mb-2">
                        <input
                          type="text"
                          value={newForbidden}
                          onChange={(e) => setNewForbidden(e.target.value)}
                          onKeyDown={(e) =>
                            e.key === 'Enter' &&
                            (e.preventDefault(),
                            addTo(newForbidden, setNewForbidden, forbiddenWords, setForbiddenWords))
                          }
                          className="input-dark flex-1 text-xs"
                          placeholder="如：宝宝 / 亲亲"
                        />
                        <button
                          type="button"
                          onClick={() =>
                            addTo(newForbidden, setNewForbidden, forbiddenWords, setForbiddenWords)
                          }
                          className="btn-ghost"
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                      </div>
                      {forbiddenWords.length > 0 && (
                        <ChipList
                          items={forbiddenWords}
                          onRemove={(i) =>
                            setForbiddenWords(forbiddenWords.filter((_, idx) => idx !== i))
                          }
                        />
                      )}
                    </div>

                    {/* Sample utterances */}
                    <div>
                      <label className="text-[10px] text-grimoire-text-muted uppercase tracking-wider mb-1 block">
                        范本台词 · 3-5 条，作为声音锚点
                      </label>
                      <div className="flex gap-2 mb-2">
                        <input
                          type="text"
                          value={newSample}
                          onChange={(e) => setNewSample(e.target.value)}
                          onKeyDown={(e) =>
                            e.key === 'Enter' &&
                            (e.preventDefault(),
                            addTo(newSample, setNewSample, sampleUtterances, setSampleUtterances))
                          }
                          className="input-dark flex-1 text-xs"
                          placeholder='如："风投比算命靠谱多了。"'
                        />
                        <button
                          type="button"
                          onClick={() =>
                            addTo(newSample, setNewSample, sampleUtterances, setSampleUtterances)
                          }
                          className="btn-ghost"
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                      </div>
                      {sampleUtterances.length > 0 && (
                        <ChipList
                          items={sampleUtterances}
                          onRemove={(i) =>
                            setSampleUtterances(sampleUtterances.filter((_, idx) => idx !== i))
                          }
                        />
                      )}
                    </div>

                    {/* Tone keywords */}
                    <div>
                      <label className="text-[10px] text-grimoire-text-muted uppercase tracking-wider mb-1 block">
                        语气副词 · 常用助词
                      </label>
                      <div className="flex gap-2 mb-2">
                        <input
                          type="text"
                          value={newTone}
                          onChange={(e) => setNewTone(e.target.value)}
                          onKeyDown={(e) =>
                            e.key === 'Enter' &&
                            (e.preventDefault(),
                            addTo(newTone, setNewTone, toneKeywords, setToneKeywords))
                          }
                          className="input-dark flex-1 text-xs"
                          placeholder="如：便 / 倒是 / 罢了"
                        />
                        <button
                          type="button"
                          onClick={() => addTo(newTone, setNewTone, toneKeywords, setToneKeywords)}
                          className="btn-ghost"
                        >
                          <Plus className="w-3 h-3" />
                        </button>
                      </div>
                      {toneKeywords.length > 0 && (
                        <ChipList
                          items={toneKeywords}
                          onRemove={(i) => setToneKeywords(toneKeywords.filter((_, idx) => idx !== i))}
                        />
                      )}
                    </div>
                  </div>
                )}
              </div>
            </form>

            <div className="flex items-center justify-end gap-3 px-6 py-4 border-t border-grimoire-border flex-shrink-0">
              <button type="button" onClick={onClose} className="btn-ghost">
                取消
              </button>
              <button onClick={handleSubmit} className="btn-glow">
                {isEditing ? '保存修改' : '召唤角色'}
              </button>
            </div>
          </motion.div>
        </>
      )}
    </AnimatePresence>
  );
}
