import { useState, useEffect } from 'react';
import { useLocation } from 'wouter';
import { motion, AnimatePresence } from 'framer-motion';
import {
  BookOpen,
  Users,
  Map,
  Settings,
  Zap,
  ChevronLeft,
  ChevronRight,
  Flame,
} from 'lucide-react';
import { cn } from '../lib/utils';
import { wsManager, type SandboxState } from '../lib/ws';
import { settingsApi } from '../lib/api';

interface NavItem {
  icon: React.ElementType;
  label: string;
  path: string;
  badge?: string;
}

const navItems: NavItem[] = [
  { icon: Map, label: 'Storyboard', path: '/storyboard' },
  { icon: Users, label: 'Characters', path: '/characters' },
  { icon: BookOpen, label: 'Archive', path: '/archive' },
  { icon: Settings, label: 'Settings', path: '/settings' },
];

export default function Sidebar() {
  const [location, setLocation] = useLocation();
  const [collapsed, setCollapsed] = useState(false);
  const [sandboxState, setSandboxState] = useState<SandboxState>('IDLE');
  const [wsConnected, setWsConnected] = useState(false);
  const [streak, setStreak] = useState(0);

  useEffect(() => {
    const unsubState = wsManager.on('STATE_CHANGE', (data) => {
      setSandboxState(data.state as SandboxState);
    });
    const unsubConn = wsManager.on('CONNECTION_STATUS', (data) => {
      setWsConnected(data.connected as boolean);
    });
    const unsubCommit = wsManager.on('COMMIT_COMPLETE', (data) => {
      const d = data as Record<string, unknown>;
      if (typeof d.daily_streak_count === 'number') {
        setStreak(d.daily_streak_count);
      }
    });

    // Initial fetch
    (async () => {
      try {
        const r = await settingsApi.get();
        const s = r.settings as Record<string, unknown>;
        if (typeof s.daily_streak_count === 'number') {
          setStreak(s.daily_streak_count);
        }
      } catch {
        // ignore
      }
    })();

    return () => {
      unsubState();
      unsubConn();
      unsubCommit();
    };
  }, []);

  const stateColor: Record<string, string> = {
    IDLE: 'bg-grimoire-text-muted',
    SPARK_RECEIVED: 'bg-grimoire-gold animate-pulse',
    REASONING: 'bg-grimoire-accent animate-pulse-slow',
    EMITTING_IR: 'bg-grimoire-accent-glow animate-glow',
    RENDERING: 'bg-grimoire-info animate-pulse-slow',
    INTERRUPTED: 'bg-grimoire-danger',
  };

  return (
    <motion.aside
      initial={false}
      animate={{ width: collapsed ? 64 : 240 }}
      transition={{ duration: 0.2, ease: 'easeInOut' }}
      className="h-screen flex flex-col bg-grimoire-surface border-r border-grimoire-border relative z-10"
    >
      {/* Header */}
      <div className="flex items-center gap-3 px-4 h-16 border-b border-grimoire-border">
        <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-grimoire-accent to-grimoire-gold flex items-center justify-center flex-shrink-0">
          <Zap className="w-4 h-4 text-white" />
        </div>
        <AnimatePresence>
          {!collapsed && (
            <motion.div
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              exit={{ opacity: 0, x: -10 }}
              className="overflow-hidden whitespace-nowrap"
            >
              <h1 className="text-sm font-bold tracking-wide bg-gradient-to-r from-grimoire-accent-glow to-grimoire-gold bg-clip-text text-transparent">
                GRIMOIRE
              </h1>
              <p className="text-[10px] text-grimoire-text-muted font-mono">Genesis Engine</p>
            </motion.div>
          )}
        </AnimatePresence>
      </div>

      {/* Engine Status */}
      <div className={cn(
        'mx-3 mt-4 mb-2 rounded-lg border border-grimoire-border transition-all',
        collapsed ? 'p-2 flex items-center justify-center' : 'p-3'
      )}>
        <div className="flex items-center gap-2">
          <div className={cn('w-2 h-2 rounded-full flex-shrink-0', stateColor[sandboxState] || stateColor.IDLE)} />
          {!collapsed && (
            <div className="min-w-0">
              <p className="text-[10px] uppercase tracking-widest text-grimoire-text-muted">Engine</p>
              <p className="text-xs font-mono text-grimoire-text truncate">{sandboxState}</p>
            </div>
          )}
        </div>
      </div>

      {/* V1.1: Daily streak */}
      {streak > 0 && (
        <div
          className={cn(
            'mx-3 mb-2 rounded-lg border border-grimoire-gold/30 bg-grimoire-gold/5 transition-all',
            collapsed ? 'p-2 flex items-center justify-center' : 'px-3 py-2'
          )}
          title={`连续日更 ${streak} 天`}
        >
          <div className="flex items-center gap-2">
            <Flame className="w-4 h-4 text-grimoire-gold flex-shrink-0" />
            {!collapsed && (
              <div className="min-w-0">
                <p className="text-[10px] uppercase tracking-widest text-grimoire-text-muted">
                  连续日更
                </p>
                <p className="text-xs font-mono text-grimoire-gold">{streak} 天 🔥</p>
              </div>
            )}
          </div>
        </div>
      )}

      {/* Navigation */}
      <nav className="flex-1 px-2 py-2 space-y-1">
        {navItems.map((item) => {
          const isActive = location === item.path;
          return (
            <button
              key={item.path}
              onClick={() => setLocation(item.path)}
              className={cn(
                'w-full flex items-center gap-3 px-3 py-2.5 rounded-lg transition-all duration-150 group',
                isActive
                  ? 'bg-grimoire-accent/15 text-grimoire-accent-glow border border-grimoire-accent/20'
                  : 'text-grimoire-text-dim hover:text-grimoire-text hover:bg-grimoire-hover border border-transparent'
              )}
            >
              <item.icon className={cn(
                'w-5 h-5 flex-shrink-0 transition-colors',
                isActive ? 'text-grimoire-accent-glow' : 'text-grimoire-text-muted group-hover:text-grimoire-text'
              )} />
              <AnimatePresence>
                {!collapsed && (
                  <motion.span
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    exit={{ opacity: 0 }}
                    className="text-sm font-medium truncate"
                  >
                    {item.label}
                  </motion.span>
                )}
              </AnimatePresence>
            </button>
          );
        })}
      </nav>

      {/* Footer: Connection Status */}
      <div className={cn(
        'px-3 py-3 border-t border-grimoire-border',
        collapsed ? 'flex justify-center' : ''
      )}>
        <div className="flex items-center gap-2">
          <div className={cn('w-1.5 h-1.5 rounded-full', wsConnected ? 'bg-grimoire-success' : 'bg-grimoire-danger')} />
          {!collapsed && (
            <span className="text-[10px] text-grimoire-text-muted font-mono">
              {wsConnected ? 'CONNECTED' : 'OFFLINE'}
            </span>
          )}
        </div>
      </div>

      {/* Collapse toggle */}
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="absolute -right-3 top-20 w-6 h-6 rounded-full bg-grimoire-card border border-grimoire-border flex items-center justify-center hover:bg-grimoire-hover transition-colors"
      >
        {collapsed ? <ChevronRight className="w-3 h-3" /> : <ChevronLeft className="w-3 h-3" />}
      </button>
    </motion.aside>
  );
}
