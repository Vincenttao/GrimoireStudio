import { useState, useEffect, useRef } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  ChevronUp,
  ChevronDown,
  Play,
  Cpu,
  MessageSquare,
  AlertCircle,
  CheckCircle2,
  Terminal,
  Hand,
  Unlock,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { wsManager, type SandboxState } from '../lib/ws';

interface LogEntry {
  id: string;
  type: 'reasoning' | 'reject' | 'warning' | 'dispatch' | 'dialogue' | 'error' | 'complete';
  message: string;
  timestamp: Date;
  actorId?: string;
}

interface TurnLog {
  turn: number;
  actorId?: string;
  dialogue?: string;
}

export default function Monitor() {
  const [collapsed, setCollapsed] = useState(true);
  const [sandboxState, setSandboxState] = useState<SandboxState>('IDLE');
  const [currentTurn, setCurrentTurn] = useState<number>(0);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [turnLogs, setTurnLogs] = useState<TurnLog[]>([]);
  const [error, setError] = useState<{ message: string; code: string } | null>(null);
  const currentTurnIndexRef = useRef<number>(-1);
  const currentDialogueRef = useRef<string>('');
  const turnLogsLengthRef = useRef<number>(0);

  // God's Hand state
  const [freezeMode, setFreezeMode] = useState(false);
  const [selectedTurnIndex, setSelectedTurnIndex] = useState<number | null>(null);
  const [overrideDirective, setOverrideDirective] = useState('');
  const [currentSparkId, setCurrentSparkId] = useState<string | null>(null);

  const isActive = sandboxState !== 'IDLE' && sandboxState !== 'INTERRUPTED';

  // WebSocket subscriptions
  useEffect(() => {
    const unsubState = wsManager.on('STATE_CHANGE', (data) => {
      setSandboxState(data.state as SandboxState);
      if (data.state === 'IDLE') {
        currentDialogueRef.current = '';
        setError(null);
        setFreezeMode(false);
      }
      if (data.spark_id) {
        setCurrentSparkId(data.spark_id as string);
      }
    });

    const unsubTurn = wsManager.on('TURN_STARTED', (data) => {
      const turn = data.turn as number;
      setCurrentTurn(turn);
      currentDialogueRef.current = '';
      currentTurnIndexRef.current = turnLogsLengthRef.current;
    });

    const unsubDispatch = wsManager.on('DISPATCH', (data) => {
      const actorId = data.actor_id as string;
      setLogs((prev) => [
        ...prev,
        {
          id: `dispatch-${Date.now()}`,
          type: 'dispatch',
          message: `Character ${actorId} is acting`,
          timestamp: new Date(),
          actorId,
        },
      ]);
      setTurnLogs((prev) => {
        const updated = [...prev, { turn: currentTurn + 1, actorId }];
        turnLogsLengthRef.current = updated.length;
        return updated;
      });
    });

    const unsubCharStream = wsManager.on('CHAR_STREAM', (data) => {
      const delta = data.delta as string;
      currentDialogueRef.current += delta;
    });

    const unsubSysDevLog = wsManager.on('SYS_DEV_LOG', (data) => {
      const newLogs: LogEntry[] = [];

      if (data.reasoning) {
        newLogs.push({
          id: `reasoning-${Date.now()}`,
          type: 'reasoning',
          message: data.reasoning as string,
          timestamp: new Date(),
        });
      }

      if (data.reject) {
        newLogs.push({
          id: `reject-${Date.now()}`,
          type: 'reject',
          message: data.reject as string,
          timestamp: new Date(),
        });
      }

      if (data.warning) {
        newLogs.push({
          id: `warning-${Date.now()}`,
          type: 'warning',
          message: data.warning as string,
          timestamp: new Date(),
        });
      }

      if (newLogs.length > 0) {
        setLogs((prev) => [...prev, ...newLogs]);
      }
    });

    const unsubSceneComplete = wsManager.on('SCENE_COMPLETE', () => {
      setLogs((prev) => [
        ...prev,
        {
          id: `complete-${Date.now()}`,
          type: 'complete',
          message: 'Scene completed',
          timestamp: new Date(),
        },
      ]);
      if (currentDialogueRef.current && currentTurnIndexRef.current >= 0) {
        setTurnLogs((prev) => {
          const idx = currentTurnIndexRef.current;
          if (idx >= 0 && idx < prev.length && !prev[idx].dialogue) {
            const updated = [...prev];
            updated[idx] = { ...updated[idx], dialogue: currentDialogueRef.current };
            turnLogsLengthRef.current = updated.length;
            return updated;
          }
          return prev;
        });
      }
      currentDialogueRef.current = '';
    });

    const unsubError = wsManager.on('ERROR', (data) => {
      setError({
        message: (data.message as string) || 'Unknown error',
        code: (data.code as string) || 'UNKNOWN',
      });
      setLogs((prev) => [
        ...prev,
        {
          id: `error-${Date.now()}`,
          type: 'error',
          message: `[${data.code}] ${data.message}`,
          timestamp: new Date(),
        },
      ]);
    });

    return () => {
      unsubState();
      unsubTurn();
      unsubDispatch();
      unsubCharStream();
      unsubSysDevLog();
      unsubSceneComplete();
      unsubError();
    };
  }, [currentTurn]);

  const handleTurnClick = (index: number, _actorId?: string) => {
    if (!isActive || !currentSparkId) return;
    setFreezeMode(true);
    setSelectedTurnIndex(index);
    setOverrideDirective('');
  };

  const handleReleaseOverride = () => {
    if (!currentSparkId || selectedTurnIndex === null) return;
    const turn = turnLogs[selectedTurnIndex];
    if (turn?.actorId && overrideDirective.trim()) {
      wsManager.sendOverride(currentSparkId, turn.actorId, overrideDirective.trim());
    }
    setFreezeMode(false);
    setSelectedTurnIndex(null);
    setOverrideDirective('');
  };

  const handleCancelFreeze = () => {
    setFreezeMode(false);
    setSelectedTurnIndex(null);
    setOverrideDirective('');
  };

  const handlePardonOverride = () => {
    if (!currentSparkId) return;
    wsManager.sendOverride(currentSparkId, 'SYSTEM', 'FORCE_ACCEPT');
  };

  const getStateColor = (state: SandboxState): string => {
    switch (state) {
      case 'IDLE':
        return 'bg-grimoire-text-muted';
      case 'REASONING':
      case 'CALLING_CHARACTER':
      case 'EVALUATING':
        return 'bg-grimoire-accent animate-pulse';
      case 'EMITTING_IR':
        return 'bg-grimoire-gold';
      case 'INTERRUPTED':
        return 'bg-grimoire-danger animate-pulse';
      case 'SPARK_RECEIVED':
      case 'RENDERING':
      case 'COMMITTED':
        return 'bg-grimoire-success';
      default:
        return 'bg-grimoire-text-muted';
    }
  };

  const getLogIcon = (type: LogEntry['type']) => {
    switch (type) {
      case 'reasoning':
        return <Cpu className="w-3 h-3 text-grimoire-accent" />;
      case 'reject':
        return <AlertCircle className="w-3 h-3 text-grimoire-gold" />;
      case 'warning':
        return <AlertCircle className="w-3 h-3 text-grimoire-danger" />;
      case 'dispatch':
        return <Play className="w-3 h-3 text-grimoire-success" />;
      case 'dialogue':
        return <MessageSquare className="w-3 h-3 text-grimoire-accent-glow" />;
      case 'error':
        return <AlertCircle className="w-3 h-3 text-grimoire-danger" />;
      case 'complete':
        return <CheckCircle2 className="w-3 h-3 text-grimoire-success" />;
      default:
        return <Terminal className="w-3 h-3 text-grimoire-text-muted" />;
    }
  };

  return (
    <motion.div
      initial={false}
      animate={{
        height: collapsed ? 40 : 300,
      }}
      transition={{ duration: 0.3, ease: 'easeInOut' }}
      className={cn(
        'glass-card overflow-hidden flex flex-col',
        collapsed ? 'cursor-pointer' : ''
      )}
      onClick={() => collapsed && setCollapsed(false)}
    >
      {/* Collapsed Header - Always visible */}
      <div
        className="h-10 flex items-center justify-between px-4 border-b border-grimoire-border/50 flex-shrink-0"
        onClick={(e) => {
          e.stopPropagation();
          setCollapsed(!collapsed);
        }}
      >
        <div className="flex items-center gap-3">
          {/* State Badge */}
          <div className="flex items-center gap-2">
            <div className={cn('w-2 h-2 rounded-full', getStateColor(sandboxState))} />
            <span className="text-[10px] font-mono uppercase tracking-wider text-grimoire-text-dim">
              {sandboxState}
            </span>
          </div>

          {/* Turn Counter */}
          {currentTurn > 0 && (
            <div className="flex items-center gap-1.5 px-2 py-0.5 rounded-full bg-grimoire-surface/50 border border-grimoire-border">
              <span className="text-[9px] text-grimoire-text-muted">Turn</span>
              <span className="text-[10px] font-mono text-grimoire-accent-glow">{currentTurn}</span>
            </div>
          )}

          {/* Active Character */}
          {isActive && turnLogs.length > 0 && !collapsed && (
            <span className="text-[10px] text-grimoire-text-muted truncate max-w-[120px]">
              {turnLogs[turnLogs.length - 1]?.actorId}
            </span>
          )}
        </div>

        {/* Expand/Collapse Icon */}
        <button
          onClick={(e) => {
            e.stopPropagation();
            setCollapsed(!collapsed);
          }}
          className="btn-ghost p-1"
          aria-label={collapsed ? 'Expand monitor' : 'Collapse monitor'}
        >
          {collapsed ? (
            <ChevronUp className="w-4 h-4 text-grimoire-text-muted" />
          ) : (
            <ChevronDown className="w-4 h-4 text-grimoire-text-muted" />
          )}
        </button>
      </div>

      {/* Expanded Content */}
      <AnimatePresence>
        {!collapsed && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.2, delay: 0.1 }}
            className="flex-1 flex overflow-hidden"
          >
            {/* Left: State Timeline */}
            <div className="w-48 border-r border-grimoire-border/50 p-3 overflow-y-auto">
              <p className="text-[9px] uppercase tracking-widest text-grimoire-text-muted mb-3">
                State Timeline
              </p>
              <div className="space-y-2">
                {[
                  'IDLE',
                  'SPARK_RECEIVED',
                  'REASONING',
                  'CALLING_CHARACTER',
                  'EVALUATING',
                  'EMITTING_IR',
                  'RENDERING',
                  'COMMITTED',
                  'INTERRUPTED',
                ].map((state) => {
                  const isCurrent = sandboxState === state;
                  const isPast =
                    [
                      'IDLE',
                      'SPARK_RECEIVED',
                      'REASONING',
                      'CALLING_CHARACTER',
                      'EVALUATING',
                      'EMITTING_IR',
                      'RENDERING',
                      'COMMITTED',
                    ].indexOf(sandboxState) >=
                    [
                      'IDLE',
                      'SPARK_RECEIVED',
                      'REASONING',
                      'CALLING_CHARACTER',
                      'EVALUATING',
                      'EMITTING_IR',
                      'RENDERING',
                      'COMMITTED',
                    ].indexOf(state as SandboxState);

                  return (
                    <div
                      key={state}
                      className={cn(
                        'flex items-center gap-2 text-[10px] transition-colors',
                        isCurrent
                          ? 'text-grimoire-accent-glow font-medium'
                          : isPast
                            ? 'text-grimoire-text-dim'
                            : 'text-grimoire-text-muted/50'
                      )}
                    >
                      <div
                        className={cn(
                          'w-1.5 h-1.5 rounded-full',
                          isCurrent
                            ? 'bg-grimoire-accent animate-pulse'
                            : isPast
                              ? 'bg-grimoire-success'
                              : 'bg-grimoire-border'
                        )}
                      />
                      <span className="font-mono uppercase">{state}</span>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Middle: Logs */}
            <div className="flex-1 flex flex-col border-r border-grimoire-border/50">
              <div className="p-2 border-b border-grimoire-border/50 flex items-center justify-between">
                <p className="text-[9px] uppercase tracking-widest text-grimoire-text-muted">
                  Orchestration Log
                </p>
                {logs.length > 0 && (
                  <button
                    onClick={() => setLogs([])}
                    className="text-[9px] text-grimoire-text-muted hover:text-grimoire-text-dim transition-colors"
                  >
                    Clear
                  </button>
                )}
              </div>
              <div className="flex-1 overflow-y-auto p-3 space-y-2">
                {logs.length === 0 ? (
                  <p className="text-[10px] text-grimoire-text-muted text-center py-4 italic">
                    No events yet...
                  </p>
                ) : (
                  logs.map((log) => (
                    <motion.div
                      key={log.id}
                      initial={{ opacity: 0, x: -10 }}
                      animate={{ opacity: 1, x: 0 }}
                      className={cn(
                        'flex flex-col gap-1 text-[10px] p-2 rounded-lg',
                        log.type === 'error'
                          ? 'bg-grimoire-danger/10 border border-grimoire-danger/20'
                          : log.type === 'warning'
                            ? 'bg-grimoire-gold/10 border border-grimoire-gold/20'
                            : 'bg-grimoire-surface/50'
                      )}
                    >
                      <div className="flex items-start gap-2">
                        <div className="flex-shrink-0 mt-0.5">{getLogIcon(log.type)}</div>
                        <div className="flex-1 min-w-0">
                          <p
                            className={cn(
                              'break-words',
                              log.type === 'error'
                                ? 'text-grimoire-danger'
                                : log.type === 'warning'
                                  ? 'text-grimoire-gold'
                                  : 'text-grimoire-text-dim'
                            )}
                          >
                            {log.message}
                          </p>
                          <p className="text-[8px] text-grimoire-text-muted mt-1">
                            {log.timestamp.toLocaleTimeString()}
                          </p>
                        </div>
                      </div>
                      {log.type === 'reject' && isActive && currentSparkId && (
                        <button
                          onClick={handlePardonOverride}
                          className="mt-1 w-full btn-ghost text-[9px] py-1 border border-grimoire-gold/30 text-grimoire-gold hover:bg-grimoire-gold/10"
                        >
                          <Hand className="w-3 h-3 inline mr-1" />
                          Override (God's Pardon)
                        </button>
                      )}
                    </motion.div>
                  ))
                )}
              </div>
            </div>

            {/* Right: Character Dispatches */}
            <div className="w-56 flex flex-col">
              <div className="p-2 border-b border-grimoire-border/50">
                <p className="text-[9px] uppercase tracking-widest text-grimoire-text-muted">
                  Character Dispatches
                </p>
              </div>
              <div className="flex-1 overflow-y-auto p-3 space-y-2">
                {turnLogs.length === 0 ? (
                  <p className="text-[10px] text-grimoire-text-muted text-center py-4 italic">
                    No turns yet...
                  </p>
                ) : (
                  turnLogs.map((turn, idx) => (
                    <motion.div
                      key={`${turn.turn}-${idx}`}
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      onClick={() => handleTurnClick(idx, turn.actorId)}
                      className={cn(
                        "p-2 rounded-lg border transition-all",
                        freezeMode && selectedTurnIndex === idx
                          ? "bg-grimoire-accent/10 border-grimoire-accent cursor-default"
                          : isActive
                            ? "bg-grimoire-surface/50 border-grimoire-border/30 cursor-pointer hover:border-grimoire-accent/50"
                            : "bg-grimoire-surface/50 border-grimoire-border/30"
                      )}
                    >
                      <div className="flex items-center gap-2 mb-1">
                        <span className="text-[9px] font-mono text-grimoire-accent">
                          Turn {turn.turn}
                        </span>
                        {turn.actorId && (
                          <span className="text-[9px] text-grimoire-text-dim truncate">
                            {turn.actorId}
                          </span>
                        )}
                        {freezeMode && selectedTurnIndex === idx && (
                          <Hand className="w-3 h-3 text-grimoire-gold ml-auto" />
                        )}
                      </div>
                      {turn.dialogue && (
                        <p className="text-[9px] text-grimoire-text-muted line-clamp-3">
                          {turn.dialogue.slice(0, 100)}
                          {turn.dialogue.length > 100 ? '...' : ''}
                        </p>
                      )}
                      {freezeMode && selectedTurnIndex === idx && (
                        <div className="mt-2 pt-2 border-t border-grimoire-border/50 space-y-2">
                          <input
                            type="text"
                            value={overrideDirective}
                            onChange={(e) => setOverrideDirective(e.target.value)}
                            placeholder="Enter new directive..."
                            className="w-full text-[10px] px-2 py-1 bg-grimoire-surface border border-grimoire-border rounded text-grimoire-text placeholder-grimoire-text-muted focus:outline-none focus:border-grimoire-accent"
                            onClick={(e) => e.stopPropagation()}
                            autoFocus
                          />
                          <div className="flex gap-2">
                            <button
                              onClick={(e) => { e.stopPropagation(); handleReleaseOverride(); }}
                              disabled={!overrideDirective.trim()}
                              className="flex-1 btn-glow text-[9px] py-1 disabled:opacity-50"
                            >
                              <Unlock className="w-3 h-3 inline mr-1" />
                              Release
                            </button>
                            <button
                              onClick={(e) => { e.stopPropagation(); handleCancelFreeze(); }}
                              className="flex-1 btn-ghost text-[9px] py-1"
                            >
                              Cancel
                            </button>
                          </div>
                        </div>
                      )}
                    </motion.div>
                  ))
                )}
              </div>
            </div>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Error Alert (when expanded) */}
      <AnimatePresence>
        {!collapsed && error && (
          <motion.div
            initial={{ opacity: 0, height: 0 }}
            animate={{ opacity: 1, height: 'auto' }}
            exit={{ opacity: 0, height: 0 }}
            className="px-4 py-2 bg-grimoire-danger/10 border-t border-grimoire-danger/20 flex items-center gap-2"
          >
            <AlertCircle className="w-4 h-4 text-grimoire-danger flex-shrink-0" />
            <div className="flex-1 min-w-0">
              <p className="text-[10px] text-grimoire-danger font-medium">
                Error {error.code}
              </p>
              <p className="text-[9px] text-grimoire-danger/80 truncate">
                {error.message}
              </p>
            </div>
            <button
              onClick={() => setError(null)}
              className="btn-ghost p-1 text-grimoire-danger"
            >
              Dismiss
            </button>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  );
}
