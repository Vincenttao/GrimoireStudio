import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Sparkles, Square, Wand2, Bot, User, PanelRightClose, Check } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { cn } from '../lib/utils';
import { uuid } from '../lib/utils';
import { sandboxApi, museApi, grimoireApi } from '../lib/api';
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
      content: '✨ Welcome to **The Muse**. I am your creative companion. Describe a scene, a conflict, or a moment — and I will bring it to life through your characters.',
      timestamp: new Date(),
    },
  ]);
  const [input, setInput] = useState('');
  const [sandboxState, setSandboxState] = useState<SandboxState>('IDLE');
  const [currentSparkId, setCurrentSparkId] = useState<string | null>(null);
  const [collapsed, setCollapsed] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
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

    return () => {
      unsubState();
      unsubIR();
    };
  }, []);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  const handleSend = async () => {
    const text = input.trim();
    if (!text || isRunning || isTyping) return;

    setInput('');
    const newMessages: ChatMessage[] = [...messages, { id: uuid(), role: 'user', content: text, timestamp: new Date() }];
    setMessages(newMessages);
    setIsTyping(true);

    const museMessageId = uuid();
    setMessages((prev) => [
      ...prev,
      { id: museMessageId, role: 'muse', content: '', timestamp: new Date() },
    ]);

    try {
      const history = newMessages
        .filter(m => m.role !== 'system')
        .map(m => ({ role: m.role, content: m.content }));
        
      const stream = museApi.chatStream(history);
      
      for await (const chunk of stream) {
        setMessages((prev) => prev.map(m => {
          if (m.id === museMessageId) {
            return { ...m, content: m.content + chunk };
          }
          return m;
        }));
      }
    } catch (err) {
      console.error('[MusePanel] chat error:', err);
      setMessages((prev) => [
        ...prev,
        { id: uuid(), role: 'system', content: `⚠️ Error: ${err instanceof Error ? err.message : 'Unknown error'}`, timestamp: new Date() },
      ]);
    } finally {
      setIsTyping(false);
    }
  };

  const executeToolCall = async (toolCall: any) => {
    try {
      if (toolCall.action === 'create_entity') {
        const entity = {
          entity_id: `char-${uuid().slice(0,8)}`,
          type: toolCall.payload.type || 'CHARACTER',
          name: toolCall.payload.name,
          base_attributes: toolCall.payload.base_attributes,
          current_status: { health: '100/100', inventory: [], relationships: {}, recent_memory_summary: [] },
          is_deleted: false,
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString()
        };
        await grimoireApi.createEntity(entity);
        setMessages((prev) => [
          ...prev,
          { id: uuid(), role: 'system', content: `✅ Character **${entity.name}** created successfully.`, timestamp: new Date() }
        ]);
      } else if (toolCall.action === 'start_spark') {
        const sparkId = uuid();
        setCurrentSparkId(sparkId);
        await sandboxApi.triggerSpark({
          spark_id: sparkId,
          chapter_id: 'default-chapter',
          user_prompt: toolCall.payload.user_prompt,
        });
        setMessages((prev) => [
          ...prev,
          { id: uuid(), role: 'system', content: `🎬 The Spark has ignited. Maestro is rolling...`, timestamp: new Date() }
        ]);
      }
    } catch (err) {
      console.error('Tool call failed', err);
      setMessages((prev) => [
        ...prev,
        { id: uuid(), role: 'system', content: `❌ Failed to execute action: ${err instanceof Error ? err.message : 'Unknown error'}`, timestamp: new Date() }
      ]);
    }
  };

  const handleCut = () => {
    if (currentSparkId) {
      wsManager.sendCut(currentSparkId);
      setMessages((prev) => [
        ...prev,
        { id: uuid(), role: 'system', content: '🛑 **CUT** — Scene interrupted by the Director.', timestamp: new Date() },
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
        <div className={cn(
          'w-7 h-7 rounded-lg flex items-center justify-center flex-shrink-0',
          isUser
            ? 'bg-grimoire-accent/20 text-grimoire-accent-glow'
            : isMuse
              ? 'bg-gradient-to-br from-grimoire-accent to-grimoire-gold text-white'
              : 'bg-grimoire-border text-grimoire-text-muted'
        )}>
          {isUser ? <User className="w-3.5 h-3.5" /> : isMuse ? <Wand2 className="w-3.5 h-3.5" /> : <Bot className="w-3.5 h-3.5" />}
        </div>

        {/* Bubble */}
        <div className={cn(
          'max-w-[85%] flex flex-col gap-2',
          isUser ? 'items-end' : 'items-start'
        )}>
          <div className={cn(
            'rounded-xl px-3 py-2 text-xs leading-relaxed',
            isUser
              ? 'bg-grimoire-accent/15 border border-grimoire-accent/20 text-grimoire-text'
              : 'glass-card text-grimoire-text'
          )}>
            <div className="prose prose-invert prose-sm max-w-none 
              prose-p:my-1 first:prose-p:mt-0 last:prose-p:mb-0
              prose-strong:text-grimoire-accent-glow prose-strong:font-semibold
              prose-headings:text-grimoire-text prose-headings:my-2
              prose-ul:my-1 prose-li:my-0.5">
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
              <div className="text-[10px] font-mono text-grimoire-text-muted">
                {toolCallData.action === 'create_entity' ? 'CREATE ENTITY' : 'START SPARK'}
              </div>
              <pre className="text-[10px] text-grimoire-text-muted overflow-x-auto bg-black/20 p-2 rounded">
                {JSON.stringify(toolCallData.payload, null, 2)}
              </pre>
              <button
                onClick={() => executeToolCall(toolCallData)}
                className="w-full btn-glow py-1.5 text-[10px] flex items-center justify-center gap-1 mt-2"
              >
                <Check className="w-3 h-3" />
                <span>Confirm {toolCallData.action === 'create_entity' ? 'Creation' : 'Spark'}</span>
              </button>
            </div>
          )}
        </div>
      </motion.div>
    );
  };

  // Collapsed state — just show icon strip
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
        {isRunning && (
          <div className="mt-3 w-2 h-2 bg-grimoire-accent rounded-full animate-pulse" />
        )}
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
        <div className="flex items-center gap-2">
          {isRunning && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-grimoire-accent/10 border border-grimoire-accent/20">
              <div className="w-1.5 h-1.5 bg-grimoire-accent rounded-full animate-pulse" />
              <span className="text-[10px] text-grimoire-accent-glow font-mono">{sandboxState}</span>
            </div>
          )}
          <button
            onClick={() => setCollapsed(true)}
            className="w-7 h-7 rounded-md flex items-center justify-center text-grimoire-text-muted hover:text-grimoire-text hover:bg-grimoire-hover transition-colors"
            title="Collapse panel"
          >
            <PanelRightClose className="w-4 h-4" />
          </button>
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-3 py-3 space-y-3">
        <AnimatePresence>
          {messages.map(renderMessage)}
        </AnimatePresence>
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
              placeholder="Ask The Muse..."
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
