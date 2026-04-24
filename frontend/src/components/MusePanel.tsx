import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Send,
  Sparkles,
  Square,
  Wand2,
  Bot,
  User,
  PanelRightClose,
  Check,
  LifeBuoy,
  BookOpenText,
  Settings2,
} from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { cn, uuid } from '../lib/utils';
import {
  sandboxApi,
  museApi,
  grimoireApi,
  renderApi,
  BEAT_TYPE_LABELS,
  type BeatType,
  type SparkCandidate,
  type MuseMode,
  type PlatformProfile,
} from '../lib/api';
import { wsManager, type SandboxState } from '../lib/ws';

interface ChatMessage {
  id: string;
  role: 'user' | 'system' | 'muse';
  content: string;
  timestamp: Date;
}

export default function MusePanel() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: 'welcome',
      role: 'muse',
      content:
        '✨ 欢迎回来。我是 **The Muse**，你的贴身责编。告诉我今天想写什么，或者点右上角 🆘 **卡文救急** 让我给你 3 个方向。',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [sandboxState, setSandboxState] = useState<SandboxState>('IDLE');
  const [currentSparkId, setCurrentSparkId] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const [mode, setMode] = useState<MuseMode>('write');
  const [unblockCandidates, setUnblockCandidates] = useState<SparkCandidate[] | null>(null);
  const [loadingUnblock, setLoadingUnblock] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const isRunning = sandboxState !== 'IDLE' && sandboxState !== 'INTERRUPTED';

  useEffect(() => {
    const unsubState = wsManager.on('STATE_CHANGE', (data) => {
      setSandboxState(data.state as SandboxState);
    });

    const unsubIR = wsManager.on('IR_EMITTED', (data) => {
      setMessages((prev) => [
        ...prev,
        {
          id: uuid(),
          role: 'system',
          content: `📜 **IR Block Generated**: ${(data as Record<string, unknown>).summary || 'New story segment ready'}`,
          timestamp: new Date(),
        },
      ]);
    });

    const unsubCommit = wsManager.on('COMMIT_COMPLETE', (data) => {
      const d = data as Record<string, unknown>;
      setMessages((prev) => [
        ...prev,
        {
          id: uuid(),
          role: 'system',
          content: `🎉 已提交。连续日更 **${d.daily_streak_count}** 天 🔥${
            d.soft_patches_merged ? `（并入 ${d.soft_patches_merged} 条事实修订）` : ''
          }`,
          timestamp: new Date(),
        },
      ]);
    });

    return () => {
      unsubState();
      unsubIR();
      unsubCommit();
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isRunning || isTyping) return;

    setInput('');
    const newMessages: ChatMessage[] = [
      ...messages,
      { id: uuid(), role: 'user', content: text, timestamp: new Date() },
    ];
    setMessages(newMessages);
    setIsTyping(true);

    const museMessageId = uuid();
    setMessages((prev) => [
      ...prev,
      { id: museMessageId, role: 'muse', content: '', timestamp: new Date() },
    ]);

    try {
      const history = newMessages
        .filter((m) => m.role !== 'system')
        .map((m) => ({ role: m.role, content: m.content }));

      const stream = museApi.chatStream(history, mode);

      for await (const chunk of stream) {
        setMessages((prev) =>
          prev.map((m) => {
            if (m.id === museMessageId) {
              return { ...m, content: m.content + chunk };
            }
            return m;
          })
        );
      }
    } catch (err) {
      console.error('[MusePanel] chat error:', err);
      setMessages((prev) => [
        ...prev,
        {
          id: uuid(),
          role: 'system',
          content: `⚠️ 出错了: ${err instanceof Error ? err.message : '未知错误'}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const handleUnblock = async () => {
    if (loadingUnblock || isRunning) return;
    setLoadingUnblock(true);
    try {
      const res = await museApi.unblockWriter();
      setUnblockCandidates(res.candidates);
      setMessages((prev) => [
        ...prev,
        {
          id: uuid(),
          role: 'system',
          content: `🆘 **卡文救急**：基于当前 Grimoire 生成了 3 个方向，选一个开推。`,
          timestamp: new Date(),
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: uuid(),
          role: 'system',
          content: `⚠️ 卡文救急失败: ${err instanceof Error ? err.message : '未知错误'}`,
          timestamp: new Date(),
        },
      ]);
    } finally {
      setLoadingUnblock(false);
    }
  };

  const startSparkFromCandidate = async (c: SparkCandidate) => {
    setUnblockCandidates(null);
    const sparkId = uuid();
    setCurrentSparkId(sparkId);
    try {
      await sandboxApi.triggerSpark({
        spark_id: sparkId,
        chapter_id: 'default-chapter',
        user_prompt: c.user_prompt,
        beat_type: c.beat_type,
        target_char_count: c.target_char_count,
      });
      setMessages((prev) => [
        ...prev,
        {
          id: uuid(),
          role: 'system',
          content: `🎬 推演启动：**${c.direction}**（${BEAT_TYPE_LABELS[c.beat_type]}，目标 ${c.target_char_count} 字）`,
          timestamp: new Date(),
        },
      ]);
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: uuid(),
          role: 'system',
          content: `❌ 推演启动失败: ${err instanceof Error ? err.message : '未知错误'}`,
          timestamp: new Date(),
        },
      ]);
    }
  };

  const executeToolCall = async (toolCall: any) => {
    try {
      if (toolCall.action === 'create_entity') {
        const entity = {
          entity_id: `char-${uuid().slice(0, 8)}`,
          type: toolCall.payload.type || 'CHARACTER',
          name: toolCall.payload.name,
          base_attributes: toolCall.payload.base_attributes,
          current_status: {
            health: '良好',
            inventory: [],
            relationships: {},
            recent_memory_summary: [],
          },
          voice_signature: toolCall.payload.voice_signature || null,
          is_deleted: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        };
        await grimoireApi.createEntity(entity);
        setMessages((prev) => [
          ...prev,
          {
            id: uuid(),
            role: 'system',
            content: `✅ 角色 **${entity.name}** 已创建。`,
            timestamp: new Date(),
          },
        ]);
      } else if (toolCall.action === 'start_spark') {
        const sparkId = uuid();
        setCurrentSparkId(sparkId);
        const beatType = (toolCall.payload.beat_type as BeatType) || 'DAILY_SLICE';
        const targetCharCount = toolCall.payload.target_char_count || 3000;
        await sandboxApi.triggerSpark({
          spark_id: sparkId,
          chapter_id: toolCall.payload.chapter_id || 'default-chapter',
          user_prompt: toolCall.payload.user_prompt,
          beat_type: beatType,
          target_char_count: targetCharCount,
        });
        setMessages((prev) => [
          ...prev,
          {
            id: uuid(),
            role: 'system',
            content: `🎬 推演启动（${BEAT_TYPE_LABELS[beatType]} · ${targetCharCount} 字）`,
            timestamp: new Date(),
          },
        ]);
      } else if (toolCall.action === 'unblock_writer') {
        await handleUnblock();
      } else if (toolCall.action === 'update_entity') {
        const { entity_id, updates } = toolCall.payload;
        await grimoireApi.updateEntity(entity_id, updates);
        setMessages((prev) => [
          ...prev,
          {
            id: uuid(),
            role: 'system',
            content: `✏️ 实体 **${entity_id}** 已更新。`,
            timestamp: new Date(),
          },
        ]);
      } else if (toolCall.action === 'delete_entity') {
        const { entity_id } = toolCall.payload;
        await grimoireApi.deleteEntity(entity_id);
        setMessages((prev) => [
          ...prev,
          {
            id: uuid(),
            role: 'system',
            content: `🗑️ 实体 **${entity_id}** 已软删除。`,
            timestamp: new Date(),
          },
        ]);
      } else if (toolCall.action === 'apply_soft_patch') {
        const r = await grimoireApi.createSoftPatch(toolCall.payload);
        setMessages((prev) => [
          ...prev,
          {
            id: uuid(),
            role: 'system',
            content: `✏️ 事实修订已登记: ${r.patch.target_path} → 下次 Commit 合并入快照`,
            timestamp: new Date(),
          },
        ]);
      } else if (toolCall.action === 'query_memory') {
        const result = await grimoireApi.queryEntities(toolCall.payload.query || 'all');
        const entityCount = result.count;
        const memorySummary = result.entities
          .map(
            (e: any) =>
              `**${e.name}**: ${e.current_status?.recent_memory_summary?.join(', ') || '暂无记忆'}`
          )
          .join('\n');
        setMessages((prev) => [
          ...prev,
          {
            id: uuid(),
            role: 'system',
            content: `📚 **当前世界** (${entityCount} 个实体):\n\n${memorySummary}`,
            timestamp: new Date(),
          },
        ]);
      } else if (toolCall.action === 'override_turn') {
        const { spark_id, entity_id, directive } = toolCall.payload;
        if (!currentSparkId && !spark_id) {
          setMessages((prev) => [
            ...prev,
            {
              id: uuid(),
              role: 'system',
              content: `⚠️ 当前没有推演中的 Spark，先开一场。`,
              timestamp: new Date(),
            },
          ]);
          return;
        }
        await sandboxApi.sendOverride(spark_id || currentSparkId!, entity_id, directive);
        setMessages((prev) => [
          ...prev,
          {
            id: uuid(),
            role: 'system',
            content: `✋ **Override 注入**: ${entity_id} → "${directive}"`,
            timestamp: new Date(),
          },
        ]);
      } else if (toolCall.action === 'adjust_render') {
        const payload = toolCall.payload;
        await renderApi.adjust(payload);
        setMessages((prev) => [
          ...prev,
          {
            id: uuid(),
            role: 'system',
            content: `🎨 渲染参数已调整。`,
            timestamp: new Date(),
          },
        ]);
      } else if (toolCall.action === 'switch_platform_profile') {
        const r = await renderApi.switchPlatform(toolCall.payload.platform as PlatformProfile);
        setMessages((prev) => [
          ...prev,
          {
            id: uuid(),
            role: 'system',
            content: `📡 已切换到平台 **${r.platform}**（默认字数 ${r.default_target_char_count}，句长 ${r.default_max_sent_len}）`,
            timestamp: new Date(),
          },
        ]);
      } else if (toolCall.action === 'create_branch') {
        const { name, origin_snapshot_id, parent_branch_id } = toolCall.payload;
        const result = await sandboxApi.createBranch(name, origin_snapshot_id, parent_branch_id);
        setMessages((prev) => [
          ...prev,
          {
            id: uuid(),
            role: 'system',
            content: `🌿 分支已创建: **${name}** (${
              (result.branch as { branch_id: string }).branch_id
            })`,
            timestamp: new Date(),
          },
        ]);
      } else if (toolCall.action === 'rollback') {
        const { snapshot_id } = toolCall.payload;
        const result = await sandboxApi.rollback(snapshot_id);
        setMessages((prev) => [
          ...prev,
          {
            id: uuid(),
            role: 'system',
            content: `⏪ 已回档到 \`${snapshot_id}\`。恢复 ${result.entities_count} 个实体。`,
            timestamp: new Date(),
          },
        ]);
      } else {
        setMessages((prev) => [
          ...prev,
          {
            id: uuid(),
            role: 'system',
            content: `⚠️ 未知动作: ${toolCall.action}`,
            timestamp: new Date(),
          },
        ]);
      }
    } catch (err) {
      console.error('Tool call failed', err);
      setMessages((prev) => [
        ...prev,
        {
          id: uuid(),
          role: 'system',
          content: `❌ 执行失败: ${err instanceof Error ? err.message : '未知错误'}`,
          timestamp: new Date(),
        },
      ]);
    }
  };

  const handleCut = () => {
    if (currentSparkId) {
      wsManager.sendCut(currentSparkId);
      setMessages((prev) => [
        ...prev,
        {
          id: uuid(),
          role: 'system',
          content: '🛑 **CUT** — 推演已被导演切断。',
          timestamp: new Date(),
        },
      ]);
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  const renderMessage = (msg: ChatMessage) => {
    const isUser = msg.role === 'user';
    const isMuse = msg.role === 'muse';

    let displayContent = msg.content;
    let toolCallData: any = null;

    const toolCallMatch = msg.content.match(/```tool_call\n([\s\S]*?)\n```/);
    if (toolCallMatch) {
      displayContent = msg.content.replace(toolCallMatch[0], '').trim();
      try {
        toolCallData = JSON.parse(toolCallMatch[1]);
      } catch (e) {
        // ignore parse error while streaming
      }
    }

    return (
      <motion.div
        key={msg.id}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn('flex gap-2 group', isUser ? 'flex-row-reverse' : '')}
      >
        {/* Avatar */}
        <div
          className={cn(
            'w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0',
            isUser
              ? 'bg-grimoire-accent/20 text-grimoire-accent-glow'
              : isMuse
                ? 'bg-gradient-to-br from-grimoire-accent to-grimoire-gold text-white'
                : 'bg-grimoire-border text-grimoire-text-muted'
          )}
        >
          {isUser ? (
            <User className="w-3.5 h-3.5" />
          ) : isMuse ? (
            <Wand2 className="w-3.5 h-3.5" />
          ) : (
            <Bot className="w-3.5 h-3.5" />
          )}
        </div>

        {/* Bubble */}
        <div className={cn('max-w-[85%] flex flex-col gap-2', isUser ? 'items-end' : 'items-start')}>
          <div
            className={cn(
              'rounded-xl px-3 py-2 text-xs leading-relaxed',
              isUser
                ? 'bg-grimoire-accent/15 border border-grimoire-accent/20 text-grimoire-text'
                : 'glass-card text-grimoire-text'
            )}
          >
            <div
              className="prose prose-invert prose-sm max-w-none
              prose-p:my-1 first:prose-p:mt-0 last:prose-p:mb-0
              prose-strong:text-grimoire-accent-glow prose-strong:font-semibold
              prose-headings:text-grimoire-text prose-headings:my-2
              prose-ul:my-1 prose-li:my-0.5"
            >
              <ReactMarkdown>
                {displayContent || (isTyping && msg.role === 'muse' && !toolCallData ? '...' : '')}
              </ReactMarkdown>
            </div>
            <p className="text-[9px] text-grimoire-text-muted mt-1 opacity-0 group-hover:opacity-100 transition-opacity">
              {msg.timestamp.toLocaleTimeString()}
            </p>
          </div>

          {toolCallData && (
            <div className="w-full rounded-lg bg-grimoire-surface/50 border border-grimoire-border p-3 space-y-2">
              <div className="text-[10px] font-mono text-grimoire-text-muted uppercase">
                {toolCallData.action}
              </div>
              <pre className="text-[10px] text-grimoire-text-muted overflow-x-auto bg-black/20 p-2 rounded max-h-32 overflow-y-auto">
                {JSON.stringify(toolCallData.payload, null, 2)}
              </pre>
              <button
                onClick={() => executeToolCall(toolCallData)}
                className={cn(
                  'w-full py-1.5 text-[10px] flex items-center justify-center gap-1 mt-2',
                  toolCallData.action === 'delete_entity' || toolCallData.action === 'rollback'
                    ? 'btn-danger'
                    : 'btn-glow'
                )}
              >
                <Check className="w-3 h-3" />
                <span>确认执行</span>
              </button>
            </div>
          )}
        </div>
      </motion.div>
    );
  };

  // Collapsed state
  if (collapsed) {
    return (
      <div className="w-12 h-screen flex flex-col items-center border-l border-grimoire-border bg-grimoire-surface/50 py-4">
        <button
          onClick={() => setCollapsed(false)}
          className="w-8 h-8 rounded-lg bg-gradient-to-br from-grimoire-accent to-grimoire-gold flex items-center justify-center hover:scale-105 transition-transform"
          title="Open The Muse"
        >
          <Sparkles className="w-4 h-4 text-white" />
        </button>
        {isRunning && <div className="mt-3 w-2 h-2 bg-grimoire-accent rounded-full animate-pulse" />}
      </div>
    );
  }

  return (
    <motion.div
      initial={{ width: 0, opacity: 0 }}
      animate={{ width: 340, opacity: 1 }}
      exit={{ width: 0, opacity: 0 }}
      transition={{ duration: 0.2 }}
      className="h-screen flex flex-col border-l border-grimoire-border bg-grimoire-surface/30 backdrop-blur-sm"
      style={{ width: 340, minWidth: 340 }}
    >
      {/* Header */}
      <header className="h-14 border-b border-grimoire-border flex items-center justify-between px-4 bg-grimoire-surface/50 flex-shrink-0">
        <div className="flex items-center gap-2">
          <Sparkles className="w-4 h-4 text-grimoire-accent-glow" />
          <h2 className="text-sm font-semibold">The Muse</h2>
        </div>
        <div className="flex items-center gap-1">
          {/* V1.1 Mode Toggle */}
          <div className="flex bg-grimoire-surface border border-grimoire-border rounded-md overflow-hidden text-[10px]">
            <button
              onClick={() => setMode('write')}
              className={cn(
                'px-2 py-1 flex items-center gap-1 transition-colors',
                mode === 'write'
                  ? 'bg-grimoire-accent/20 text-grimoire-accent-glow'
                  : 'text-grimoire-text-muted hover:text-grimoire-text'
              )}
              title="写稿档：生成 Spark / 推演微操 / 调渲染"
            >
              <BookOpenText className="w-3 h-3" />
              写稿
            </button>
            <button
              onClick={() => setMode('setting')}
              className={cn(
                'px-2 py-1 flex items-center gap-1 transition-colors',
                mode === 'setting'
                  ? 'bg-grimoire-accent/20 text-grimoire-accent-glow'
                  : 'text-grimoire-text-muted hover:text-grimoire-text'
              )}
              title="设定档：实体 CRUD / 事实修订 / 分支 / 回档"
            >
              <Settings2 className="w-3 h-3" />
              设定
            </button>
          </div>

          {/* V1.1 Unblock button */}
          <button
            onClick={handleUnblock}
            disabled={loadingUnblock || isRunning}
            className={cn(
              'w-7 h-7 rounded-md flex items-center justify-center transition-colors',
              loadingUnblock || isRunning
                ? 'text-grimoire-text-muted opacity-50 cursor-not-allowed'
                : 'text-grimoire-gold hover:bg-grimoire-gold/10'
            )}
            title="🆘 卡文救急：基于当前世界生成 3 个 Spark 候选"
          >
            <LifeBuoy className={cn('w-4 h-4', loadingUnblock && 'animate-spin')} />
          </button>

          {isRunning && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-grimoire-accent/10 border border-grimoire-accent/20">
              <div className="w-1.5 h-1.5 bg-grimoire-accent rounded-full animate-pulse" />
              <span className="text-[10px] text-grimoire-accent-glow font-mono">{sandboxState}</span>
            </div>
          )}
          <button
            onClick={() => setCollapsed(true)}
            className="w-7 h-7 rounded-md flex items-center justify-center text-grimoire-text-muted hover:text-grimoire-text hover:bg-grimoire-hover transition-colors"
            title="收起面板"
          >
            <PanelRightClose className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        <AnimatePresence>{messages.map(renderMessage)}</AnimatePresence>

        {/* V1.1 Unblock Candidates Overlay */}
        {unblockCandidates && (
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            className="glass-card p-3 space-y-2 border-grimoire-gold/40"
          >
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-1 text-xs font-semibold text-grimoire-gold">
                <LifeBuoy className="w-3.5 h-3.5" />
                卡文救急 · 选一个开推
              </div>
              <button
                onClick={() => setUnblockCandidates(null)}
                className="text-[10px] text-grimoire-text-muted hover:text-grimoire-text"
              >
                关闭
              </button>
            </div>
            {unblockCandidates.map((c, i) => (
              <div
                key={i}
                className="rounded-lg bg-grimoire-surface/50 border border-grimoire-border p-3 space-y-1.5"
              >
                <div className="text-xs font-semibold text-grimoire-accent-glow">{c.direction}</div>
                <div className="text-[10px] text-grimoire-text-muted">
                  {BEAT_TYPE_LABELS[c.beat_type]} · 目标 {c.target_char_count} 字
                </div>
                <p className="text-xs text-grimoire-text">{c.user_prompt}</p>
                <p className="text-[10px] text-grimoire-text-muted italic">💡 {c.why}</p>
                <button
                  onClick={() => startSparkFromCandidate(c)}
                  className="w-full btn-glow text-[11px] py-1.5 mt-1"
                >
                  选这个开推
                </button>
              </div>
            ))}
          </motion.div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="border-t border-grimoire-border p-3 bg-grimoire-surface/50">
        <div className="flex items-end gap-2">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={mode === 'write' ? '描述下一章/下一场戏...' : '管理设定、分支、回档...'}
              rows={1}
              className="input-dark resize-none min-h-[38px] max-h-24 text-xs"
              disabled={isRunning}
            />
          </div>

          {isRunning ? (
            <button
              type="button"
              onClick={handleCut}
              className="btn-danger flex items-center gap-1 text-xs px-3 py-2"
              id="cut-button"
            >
              <Square className="w-3 h-3" />
              <span>CUT</span>
            </button>
          ) : (
            <button
              type="button"
              onClick={handleSend}
              disabled={!input.trim()}
              className={cn(
                'btn-glow flex items-center gap-1 text-xs px-3 py-2',
                !input.trim() && 'opacity-50 cursor-not-allowed'
              )}
              id="send-button"
            >
              <Send className="w-3 h-3" />
            </button>
          )}
        </div>
      </div>
    </motion.div>
  );
}
