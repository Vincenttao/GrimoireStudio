import { useState, useCallback, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Map, Plus, ChevronRight, BookOpen, FileText, Loader2 } from 'lucide-react';
import { storyboardApi } from '../lib/api';
import { cn } from '../lib/utils';
import { uuid } from '../lib/utils';

interface StoryNodeData {
  node_id: string;
  branch_id: string;
  type: string;
  title: string;
  summary: string | null;
  lexorank: string;
  parent_node_id: string | null;
}

export default function StoryboardPage() {
  const [nodes, setNodes] = useState<StoryNodeData[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedNode, setSelectedNode] = useState<StoryNodeData | null>(null);
  const [isCreating, setIsCreating] = useState(false);
  const [newTitle, setNewTitle] = useState('');

  const fetchNodes = useCallback(async () => {
    setLoading(true);
    try {
      const data = await storyboardApi.getNodes('main');
      setNodes(data.nodes as StoryNodeData[]);
    } catch {
      // Backend may be offline — show empty state gracefully
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchNodes();
  }, [fetchNodes]);

  const handleCreateChapter = async () => {
    if (!newTitle.trim()) return;
    try {
      const node: StoryNodeData = {
        node_id: uuid(),
        branch_id: 'main',
        type: 'CHAPTER',
        title: newTitle.trim(),
        summary: null,
        lexorank: `${nodes.length + 1}`.padStart(5, '0'),
        parent_node_id: null,
      };
      await storyboardApi.createNode(node);
      setNewTitle('');
      setIsCreating(false);
      await fetchNodes();
    } catch {
      // Error handled gracefully
    }
  };

  const volumes = nodes.filter((n) => n.type === 'VOLUME');
  const chapters = nodes.filter((n) => n.type === 'CHAPTER');

  return (
    <div className="flex-1 flex flex-col h-screen">
      {/* Header */}
      <header className="h-14 border-b border-grimoire-border flex items-center justify-between px-6 bg-grimoire-surface/50 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center gap-3">
          <Map className="w-5 h-5 text-grimoire-accent-glow" />
          <h2 className="text-base font-semibold">Storyboard</h2>
          <span className="text-xs text-grimoire-text-muted font-mono">— Narrative Topology</span>
          {nodes.length > 0 && (
            <span className="ml-2 px-2 py-0.5 rounded-full bg-grimoire-gold/10 text-[10px] text-grimoire-gold font-mono border border-grimoire-gold/20">
              {chapters.length} chapters
            </span>
          )}
        </div>
        <button onClick={() => setIsCreating(true)} className="btn-glow flex items-center gap-2">
          <Plus className="w-4 h-4" />
          <span>New Chapter</span>
        </button>
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Left: Node Tree */}
        <div className="w-72 border-r border-grimoire-border bg-grimoire-surface/30 overflow-y-auto p-4 flex-shrink-0">
          <p className="text-[10px] uppercase tracking-widest text-grimoire-text-muted mb-3 px-2">
            Story Structure
          </p>

          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 text-grimoire-accent animate-spin" />
            </div>
          )}

          {!loading && nodes.length === 0 && !isCreating && (
            <div className="text-center py-8 space-y-3">
              <BookOpen className="w-8 h-8 mx-auto text-grimoire-text-muted" />
              <p className="text-xs text-grimoire-text-muted">No chapters yet</p>
              <button onClick={() => setIsCreating(true)} className="text-xs text-grimoire-accent-glow hover:underline">
                Create your first chapter →
              </button>
            </div>
          )}

          {/* Create inline form */}
          <AnimatePresence>
            {isCreating && (
              <motion.div
                initial={{ height: 0, opacity: 0 }}
                animate={{ height: 'auto', opacity: 1 }}
                exit={{ height: 0, opacity: 0 }}
                className="mb-3 overflow-hidden"
              >
                <div className="glass-card p-3 space-y-2">
                  <input
                    autoFocus
                    value={newTitle}
                    onChange={(e) => setNewTitle(e.target.value)}
                    onKeyDown={(e) => e.key === 'Enter' && handleCreateChapter()}
                    className="input-dark text-sm"
                    placeholder="Chapter title..."
                  />
                  <div className="flex gap-2">
                    <button onClick={handleCreateChapter} className="btn-glow text-xs flex-1">Create</button>
                    <button onClick={() => setIsCreating(false)} className="btn-ghost text-xs">Cancel</button>
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Node list */}
          <div className="space-y-1">
            {chapters.map((node) => (
              <button
                key={node.node_id}
                onClick={() => setSelectedNode(node)}
                className={cn(
                  'w-full flex items-center gap-2.5 px-3 py-2.5 rounded-lg text-left transition-all',
                  selectedNode?.node_id === node.node_id
                    ? 'bg-grimoire-accent/10 border border-grimoire-accent/20 text-grimoire-text'
                    : 'hover:bg-grimoire-hover text-grimoire-text-dim border border-transparent'
                )}
              >
                <FileText className="w-4 h-4 flex-shrink-0 text-grimoire-gold" />
                <span className="text-sm truncate">{node.title}</span>
                <ChevronRight className="w-3 h-3 ml-auto text-grimoire-text-muted" />
              </button>
            ))}
          </div>
        </div>

        {/* Right: Content Area */}
        <div className="flex-1 flex items-center justify-center p-6">
          {selectedNode ? (
            <motion.div
              key={selectedNode.node_id}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="max-w-2xl w-full space-y-6"
            >
              <div>
                <p className="text-[10px] uppercase tracking-widest text-grimoire-text-muted mb-1">Chapter</p>
                <h3 className="text-2xl font-serif font-semibold text-grimoire-text">{selectedNode.title}</h3>
                {selectedNode.summary && (
                  <p className="text-sm text-grimoire-text-dim mt-2">{selectedNode.summary}</p>
                )}
              </div>

              <div className="glass-card p-6">
                <p className="text-sm text-grimoire-text-muted text-center">
                  IR Blocks for this chapter will appear here after the Maestro generates them.
                </p>
              </div>
            </motion.div>
          ) : (
            <div className="text-center space-y-4 animate-fade-in">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-grimoire-card border border-grimoire-border flex items-center justify-center">
                <Map className="w-8 h-8 text-grimoire-text-muted" />
              </div>
              <h3 className="text-lg font-semibold text-grimoire-text">Select a Chapter</h3>
              <p className="text-sm text-grimoire-text-muted max-w-sm">
                Choose a chapter from the sidebar to view its story blocks, or create a new one to begin writing.
              </p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
