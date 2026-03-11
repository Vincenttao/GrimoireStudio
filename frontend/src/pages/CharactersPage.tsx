import { useState, useEffect, useCallback } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { Users, Plus, Search, RefreshCw, Loader2 } from 'lucide-react';
import CharacterCard, { type CharacterEntity } from '../components/CharacterCard';
import CreateCharacterModal from '../components/CreateCharacterModal';
import DeleteConfirmDialog from '../components/DeleteConfirmDialog';
import { grimoireApi } from '../lib/api';
import { cn } from '../lib/utils';

export default function CharactersPage() {
  const [characters, setCharacters] = useState<CharacterEntity[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingEntity, setEditingEntity] = useState<CharacterEntity | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<{ id: string; name: string } | null>(null);

  const fetchCharacters = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await grimoireApi.listEntities('CHARACTER');
      setCharacters(data.entities as CharacterEntity[]);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to fetch characters');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchCharacters();
  }, [fetchCharacters]);

  const handleCreate = async (entity: CharacterEntity) => {
    try {
      await grimoireApi.createEntity(entity);
      await fetchCharacters();
      setIsModalOpen(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to create character');
    }
  };

  const handleEdit = (entity: CharacterEntity) => {
    setEditingEntity(entity);
    setIsModalOpen(true);
  };

  const handleUpdate = async (entity: CharacterEntity) => {
    try {
      await grimoireApi.updateEntity(entity.entity_id, entity);
      await fetchCharacters();
      setIsModalOpen(false);
      setEditingEntity(null);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to update character');
    }
  };

  const handleDeleteRequest = (entityId: string) => {
    const char = characters.find((c) => c.entity_id === entityId);
    if (char) {
      setDeleteTarget({ id: entityId, name: char.name });
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    try {
      await grimoireApi.deleteEntity(deleteTarget.id);
      await fetchCharacters();
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to delete character');
    } finally {
      setDeleteTarget(null);
    }
  };

  const handleModalClose = () => {
    setIsModalOpen(false);
    setEditingEntity(null);
  };

  const filteredCharacters = characters.filter((c) =>
    c.name.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div className="flex-1 flex flex-col h-screen">
      {/* Header */}
      <header className="h-14 border-b border-grimoire-border flex items-center justify-between px-6 bg-grimoire-surface/50 backdrop-blur-sm flex-shrink-0">
        <div className="flex items-center gap-3">
          <Users className="w-5 h-5 text-grimoire-accent-glow" />
          <h2 className="text-base font-semibold">Characters</h2>
          <span className="text-xs text-grimoire-text-muted font-mono">— The Grimoire</span>
          {characters.length > 0 && (
            <span className="ml-2 px-2 py-0.5 rounded-full bg-grimoire-accent/10 text-[10px] text-grimoire-accent-glow font-mono border border-grimoire-accent/20">
              {characters.length}
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <button onClick={fetchCharacters} className="btn-ghost" title="Refresh">
            <RefreshCw className={cn('w-4 h-4', loading && 'animate-spin')} />
          </button>
          <button onClick={() => setIsModalOpen(true)} className="btn-glow flex items-center gap-2">
            <Plus className="w-4 h-4" />
            <span>New Character</span>
          </button>
        </div>
      </header>

      {/* Search & Content */}
      <div className="flex-1 overflow-y-auto p-6">
        {/* Search Bar */}
        {characters.length > 0 && (
          <div className="mb-6 relative max-w-md">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-grimoire-text-muted" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              className="input-dark pl-10"
              placeholder="Search characters..."
            />
          </div>
        )}

        {/* Error */}
        {error && (
          <div className="mb-4 px-4 py-3 rounded-lg bg-grimoire-danger/10 border border-grimoire-danger/20 text-sm text-grimoire-danger">
            ⚠️ {error}
          </div>
        )}

        {/* Loading */}
        {loading && characters.length === 0 && (
          <div className="flex-1 flex items-center justify-center min-h-[200px]">
            <Loader2 className="w-6 h-6 text-grimoire-accent animate-spin" />
          </div>
        )}

        {/* Empty State */}
        {!loading && characters.length === 0 && (
          <div className="flex-1 flex items-center justify-center min-h-[400px]">
            <div className="text-center space-y-4 animate-fade-in">
              <div className="w-16 h-16 mx-auto rounded-2xl bg-grimoire-card border border-grimoire-border flex items-center justify-center">
                <Users className="w-8 h-8 text-grimoire-text-muted" />
              </div>
              <h3 className="text-lg font-semibold text-grimoire-text">No Characters Yet</h3>
              <p className="text-sm text-grimoire-text-muted max-w-sm">
                Create your first character to populate the Grimoire.
                Each character has a personality, motive, and living memory.
              </p>
              <button onClick={() => setIsModalOpen(true)} className="btn-glow mt-4">
                <Plus className="w-4 h-4 inline mr-2" />
                Summon First Character
              </button>
            </div>
          </div>
        )}

        {/* Grid */}
        {filteredCharacters.length > 0 && (
          <motion.div layout className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-4">
            <AnimatePresence>
              {filteredCharacters.map((char) => (
                <CharacterCard
                  key={char.entity_id}
                  entity={char}
                  onEdit={handleEdit}
                  onDelete={handleDeleteRequest}
                />
              ))}
            </AnimatePresence>
          </motion.div>
        )}

        {/* No search results */}
        {!loading && characters.length > 0 && filteredCharacters.length === 0 && (
          <p className="text-center text-sm text-grimoire-text-muted py-12">
            No characters match "{searchQuery}"
          </p>
        )}
      </div>

      {/* Modals */}
      <CreateCharacterModal
        isOpen={isModalOpen}
        onClose={handleModalClose}
        onSubmit={editingEntity ? handleUpdate : handleCreate}
        editingEntity={editingEntity}
      />

      <DeleteConfirmDialog
        isOpen={!!deleteTarget}
        entityName={deleteTarget?.name || ''}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
}
