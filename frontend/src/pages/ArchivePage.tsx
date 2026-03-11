import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { BookOpen, Clock, FileText, Loader2 } from 'lucide-react';
import { storyboardApi } from '../lib/api';

interface IRBlock {
  block_id: string;
  chapter_id: string;
  summary: string;
  content_html: string | null;
  created_at: string;
}

export default function ArchivePage() {
  const [blocks, setBlocks] = useState<IRBlock[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedBlock, setSelectedBlock] = useState<IRBlock | null>(null);

  useEffect(() => {
    const fetchBlocks = async () => {
      try {
        // Fetch blocks from the default chapter for now
        const data = await storyboardApi.getChapterBlocks('default-chapter');
        setBlocks(data.blocks as IRBlock[]);
      } catch {
        // Backend offline - graceful empty state
      } finally {
        setLoading(false);
      }
    };
    fetchBlocks();
  }, []);

  return (
    <div className="flex-1 flex flex-col h-screen">
      {/* Header */}
      <header className="h-14 border-b border-grimoire-border flex items-center px-6 bg-grimoire-surface/50 backdrop-blur-sm flex-shrink-0">
        <BookOpen className="w-5 h-5 text-grimoire-accent-glow mr-3" />
        <h2 className="text-base font-semibold">Archive</h2>
        <span className="text-xs text-grimoire-text-muted font-mono ml-3">— Rendered Prose</span>
        {blocks.length > 0 && (
          <span className="ml-2 px-2 py-0.5 rounded-full bg-grimoire-info/10 text-[10px] text-grimoire-info font-mono border border-grimoire-info/20">
            {blocks.length} blocks
          </span>
        )}
      </header>

      <div className="flex-1 flex overflow-hidden">
        {/* Block List */}
        <div className="w-80 border-r border-grimoire-border bg-grimoire-surface/30 overflow-y-auto p-4 flex-shrink-0">
          <p className="text-[10px] uppercase tracking-widest text-grimoire-text-muted mb-3 px-2">
            Committed Blocks
          </p>

          {loading && (
            <div className="flex items-center justify-center py-8">
              <Loader2 className="w-5 h-5 text-grimoire-accent animate-spin" />
            </div>
          )}

          {!loading && blocks.length === 0 && (
            <div className="text-center py-12 space-y-3">
              <BookOpen className="w-8 h-8 mx-auto text-grimoire-text-muted" />
              <p className="text-xs text-grimoire-text-muted">No committed blocks yet</p>
              <p className="text-[10px] text-grimoire-text-muted max-w-xs mx-auto">
                When the Maestro generates and you commit story blocks, they'll appear in this archive.
              </p>
            </div>
          )}

          <div className="space-y-1">
            {blocks.map((block) => (
              <button
                key={block.block_id}
                onClick={() => setSelectedBlock(block)}
                className={`w-full text-left px-3 py-3 rounded-lg transition-all border ${
                  selectedBlock?.block_id === block.block_id
                    ? 'bg-grimoire-accent/10 border-grimoire-accent/20'
                    : 'border-transparent hover:bg-grimoire-hover'
                }`}
              >
                <div className="flex items-center gap-2 mb-1">
                  <FileText className="w-3.5 h-3.5 text-grimoire-gold" />
                  <span className="text-sm text-grimoire-text truncate">{block.summary}</span>
                </div>
                <div className="flex items-center gap-1.5 text-[10px] text-grimoire-text-muted">
                  <Clock className="w-3 h-3" />
                  <span>{new Date(block.created_at).toLocaleString()}</span>
                </div>
              </button>
            ))}
          </div>
        </div>

        {/* Prose Reader */}
        <div className="flex-1 overflow-y-auto p-8">
          {selectedBlock ? (
            <motion.article
              key={selectedBlock.block_id}
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="max-w-2xl mx-auto"
            >
              <div className="mb-6">
                <p className="text-[10px] uppercase tracking-widest text-grimoire-text-muted mb-1">
                  Block {selectedBlock.block_id.slice(0, 8)}
                </p>
                <h3 className="text-xl font-serif font-semibold text-grimoire-text">
                  {selectedBlock.summary}
                </h3>
              </div>

              {selectedBlock.content_html ? (
                <div
                  className="prose prose-invert prose-sm max-w-none font-serif leading-relaxed"
                  dangerouslySetInnerHTML={{ __html: selectedBlock.content_html }}
                />
              ) : (
                <div className="glass-card p-8 text-center">
                  <p className="text-sm text-grimoire-text-muted italic">
                    This block has not been rendered yet. The Camera Agent will generate prose when triggered.
                  </p>
                </div>
              )}
            </motion.article>
          ) : (
            <div className="h-full flex items-center justify-center">
              <div className="text-center space-y-4 animate-fade-in">
                <div className="w-16 h-16 mx-auto rounded-2xl bg-grimoire-card border border-grimoire-border flex items-center justify-center">
                  <BookOpen className="w-8 h-8 text-grimoire-text-muted" />
                </div>
                <h3 className="text-lg font-semibold text-grimoire-text">Select a Block</h3>
                <p className="text-sm text-grimoire-text-muted max-w-sm">
                  Browse committed IR blocks from the sidebar to read the rendered prose.
                </p>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
