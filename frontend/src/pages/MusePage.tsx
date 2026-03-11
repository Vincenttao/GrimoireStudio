import { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Send, Sparkles, Square, Wand2, Bot, User } from 'lucide-react';
import { cn } from '../lib/utils';
import { uuid } from '../lib/utils';
import { sandboxApi } from '../lib/api';
import { wsManager, type SandboxState } from '../lib/ws';

interface ChatMessage {
  id: string;
  role: 'user' | 'system' | 'muse';
  content: string;
  timestamp: Date;
}

export default function MusePage() {
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
    if (!text || isRunning) return;

    const sparkId = uuid();
    setCurrentSparkId(sparkId);

    // Add user message
    setMessages((prev) => [
      ...prev,
      { id: uuid(), role: 'user', content: text, timestamp: new Date() },
    ]);
    setInput('');

    // Add Muse acknowledgement
    setMessages((prev) => [
      ...prev,
      {
        id: uuid(),
        role: 'muse',
        content: '🎭 The characters have heard your prompt. The Maestro is orchestrating...',
        timestamp: new Date(),
      },
    ]);

    try {
      await sandboxApi.triggerSpark({
        spark_id: sparkId,
        chapter_id: 'default-chapter',
        user_prompt: text,
      });
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          id: uuid(),
          role: 'system',
          content: `⚠️ Failed to send spark: ${err instanceof Error ? err.message : 'Unknown error'}`,
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

    return (
      <motion.div
        key={msg.id}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        className={cn('flex gap-3 group', isUser ? 'flex-row-reverse' : '')}
      >
        {/* Avatar */}
        <div className={cn(
          'w-8 h-8 rounded-lg flex items-center justify-center flex-shrink-0',
          isUser
            ? 'bg-grimoire-accent/20 text-grimoire-accent-glow'
            : isMuse
              ? 'bg-gradient-to-br from-grimoire-accent to-grimoire-gold text-white'
              : 'bg-grimoire-border text-grimoire-text-muted'
        )}>
          {isUser ? <User className="w-4 h-4" /> : isMuse ? <Wand2 className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
        </div>

        {/* Bubble */}
        <div className={cn(
          'max-w-[75%] rounded-xl px-4 py-3 text-sm leading-relaxed',
          isUser
            ? 'bg-grimoire-accent/15 border border-grimoire-accent/20 text-grimoire-text'
            : 'glass-card text-grimoire-text'
        )}>
          <p className="whitespace-pre-wrap">{msg.content}</p>
          <p className="text-[10px] text-grimoire-text-muted mt-2 opacity-0 group-hover:opacity-100 transition-opacity">
            {msg.timestamp.toLocaleTimeString()}
          </p>
        </div>
      </motion.div>
    );
  };

  return (
    <div className="flex-1 flex flex-col h-screen">
      {/* Header */}
      <header className="h-14 border-b border-grimoire-border flex items-center justify-between px-6 bg-grimoire-surface/50 backdrop-blur-sm">
        <div className="flex items-center gap-3">
          <Sparkles className="w-5 h-5 text-grimoire-accent-glow" />
          <h2 className="text-base font-semibold">The Muse</h2>
          <span className="text-xs text-grimoire-text-muted font-mono">— Dialogue Gateway</span>
        </div>
        <div className="flex items-center gap-2">
          {isRunning && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="flex items-center gap-2 px-3 py-1 rounded-full bg-grimoire-accent/10 border border-grimoire-accent/20"
            >
              <div className="w-2 h-2 bg-grimoire-accent rounded-full animate-pulse" />
              <span className="text-xs text-grimoire-accent-glow font-mono">{sandboxState}</span>
            </motion.div>
          )}
        </div>
      </header>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
        <AnimatePresence>
          {messages.map(renderMessage)}
        </AnimatePresence>
        <div ref={messagesEndRef} />
      </div>

      {/* Input Bar */}
      <div className="border-t border-grimoire-border p-4 bg-grimoire-surface/50 backdrop-blur-sm">
        <div className="flex items-end gap-3 max-w-4xl mx-auto">
          <div className="flex-1 relative">
            <textarea
              ref={inputRef}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Describe a scene, conflict, or moment..."
              rows={1}
              className="input-dark resize-none min-h-[44px] max-h-32 pr-12"
              disabled={isRunning}
            />
          </div>

          {isRunning ? (
            <button onClick={handleCut} className="btn-danger flex items-center gap-2" id="cut-button">
              <Square className="w-4 h-4" />
              <span>CUT</span>
            </button>
          ) : (
            <button
              onClick={handleSend}
              disabled={!input.trim()}
              className={cn(
                'btn-glow flex items-center gap-2',
                !input.trim() && 'opacity-50 cursor-not-allowed'
              )}
              id="send-button"
            >
              <Send className="w-4 h-4" />
              <span>Ignite</span>
            </button>
          )}
        </div>
      </div>
    </div>
  );
}
