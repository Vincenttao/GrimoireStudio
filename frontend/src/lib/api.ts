/**
 * Genesis Engine - REST API Client (V1.1 Web Novel Workshop)
 * Handles all HTTP communication with the FastAPI backend.
 * SPEC §4.1 REST Endpoint Compliance
 */

const API_BASE = import.meta.env.VITE_API_BASE || '/api/v1';

interface ApiOptions {
  method?: string;
  body?: unknown;
  headers?: Record<string, string>;
}

async function request<T>(endpoint: string, options: ApiOptions = {}): Promise<T> {
  const { method = 'GET', body, headers = {} } = options;

  const config: RequestInit = {
    method,
    headers: {
      'Content-Type': 'application/json',
      ...headers,
    },
  };

  if (body) {
    config.body = JSON.stringify(body);
  }

  const response = await fetch(`${API_BASE}${endpoint}`, config);

  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: 'Unknown error' }));
    throw new Error(error.detail || `API Error: ${response.status}`);
  }

  return response.json();
}

// ===========================
// V1.1 Shared Types
// ===========================
export type BeatType =
  | 'SHOW_OFF_FACE_SLAP'
  | 'PAYOFF'
  | 'SUSPENSE_SETUP'
  | 'EMOTIONAL_CLIMAX'
  | 'POWER_REVEAL'
  | 'REVERSAL'
  | 'WORLDBUILDING'
  | 'DAILY_SLICE';

export const BEAT_TYPE_LABELS: Record<BeatType, string> = {
  SHOW_OFF_FACE_SLAP: '装逼打脸',
  PAYOFF: '爽点兑现',
  SUSPENSE_SETUP: '悬念铺垫',
  EMOTIONAL_CLIMAX: '情感升华',
  POWER_REVEAL: '金手指展示',
  REVERSAL: '反转',
  WORLDBUILDING: '世界观补完',
  DAILY_SLICE: '日常流',
};

export type PlatformProfile =
  | 'QIDIAN'
  | 'FANQIE'
  | 'JINJIANG'
  | 'ZONGHENG'
  | 'QIMAO'
  | 'CUSTOM';

export const PLATFORM_LABELS: Record<PlatformProfile, string> = {
  QIDIAN: '起点中文网',
  FANQIE: '番茄小说',
  JINJIANG: '晋江文学城',
  ZONGHENG: '纵横中文网',
  QIMAO: '七猫 / 飞卢',
  CUSTOM: '自定义',
};

export interface VoiceSignature {
  catchphrases: string[];
  catchphrase_min_freq_chapters?: number;
  honorifics: Record<string, string>;
  forbidden_words: string[];
  sample_utterances: string[];
  tone_keywords: string[];
}

export interface SparkPayload {
  spark_id: string;
  chapter_id: string;
  user_prompt: string;
  overrides?: Record<string, string>;
  beat_type?: BeatType;
  target_char_count?: number;
}

export interface SparkCandidate {
  direction: string;
  beat_type: BeatType;
  user_prompt: string;
  target_char_count: number;
  why: string;
}

export interface SoftPatch {
  patch_id: string;
  target_entity_id: string;
  target_path: string;
  old_value: unknown;
  new_value: unknown;
  author_note: string;
  status: 'PENDING' | 'MERGED' | 'DISCARDED';
  created_at: string;
  merged_into_snapshot_id: string | null;
}

export interface RenderMixerSettings {
  pov_type: 'OMNISCIENT' | 'FIRST_PERSON' | 'CHARACTER_LIMITED';
  style_template: string;
  subtext_ratio: number;
}

// ===========================
// Sandbox API (SPEC §4.1)
// ===========================
export const sandboxApi = {
  getState: () => request<{ state: string }>('/sandbox/state'),

  triggerSpark: (spark: SparkPayload) =>
    request<{ message: string; spark_id: string }>('/sandbox/spark', {
      method: 'POST',
      body: spark,
    }),

  sendOverride: (sparkId: string, entityId: string, newDirective: string) =>
    request('/sandbox/override', {
      method: 'POST',
      body: { spark_id: sparkId, entity_id: entityId, new_directive: newDirective },
    }),

  commit: (irBlockId: string, finalContentHtml: string) =>
    request<{
      status: string;
      soft_patches_merged: number;
      daily_streak_count: number;
    }>('/sandbox/commit', {
      method: 'POST',
      body: { ir_block_id: irBlockId, final_content_html: finalContentHtml },
    }),

  createBranch: (name: string, originSnapshotId?: string, parentBranchId?: string) =>
    request<{ branch: unknown; message: string }>('/sandbox/branch', {
      method: 'POST',
      body: { name, origin_snapshot_id: originSnapshotId, parent_branch_id: parentBranchId },
    }),

  listBranches: () => request<{ branches: unknown[] }>('/sandbox/branches'),

  rollback: (snapshotId: string) =>
    request<{
      snapshot_id: string;
      branch_id: string;
      entities_count: number;
      message: string;
    }>('/sandbox/rollback', {
      method: 'POST',
      body: { snapshot_id: snapshotId },
    }),
};

// ===========================
// Grimoire API (Entity CRUD + V1.1 SoftPatch)
// ===========================
export const grimoireApi = {
  listEntities: (type?: string) =>
    request<{ entities: unknown[] }>(`/grimoire/entities${type ? `?type=${type}` : ''}`),

  getEntity: (entityId: string) =>
    request<{ entity: unknown }>(`/grimoire/entities/${entityId}`),

  getEntityEffective: (entityId: string) =>
    request<{ entity: Record<string, unknown>; applied_patch_count: number }>(
      `/grimoire/entities/${entityId}/effective`
    ),

  createEntity: (entity: unknown) =>
    request('/grimoire/entities', { method: 'POST', body: entity }),

  updateEntity: (entityId: string, data: unknown) =>
    request(`/grimoire/entities/${entityId}`, { method: 'PATCH', body: data }),

  deleteEntity: (entityId: string) =>
    request(`/grimoire/entities/${entityId}`, { method: 'DELETE' }),

  queryEntities: (query: string) =>
    request<{ entities: unknown[]; query: string; count: number }>(
      '/grimoire/entities/query',
      {
        method: 'POST',
        body: { query },
      }
    ),

  // V1.1 SoftPatch
  createSoftPatch: (patch: {
    target_entity_id: string;
    target_path: string;
    new_value: unknown;
    author_note: string;
  }) =>
    request<{ patch: SoftPatch; message: string }>('/grimoire/soft_patches', {
      method: 'POST',
      body: patch,
    }),

  listSoftPatches: (entityId?: string) =>
    request<{ patches: SoftPatch[]; count: number }>(
      `/grimoire/soft_patches${entityId ? `?entity_id=${entityId}` : ''}`
    ),

  discardSoftPatch: (patchId: string) =>
    request<{ status: string }>(`/grimoire/soft_patches/${patchId}`, {
      method: 'DELETE',
    }),
};

// ===========================
// Storyboard API
// ===========================
export const storyboardApi = {
  getNodes: (branchId: string) =>
    request<{ nodes: unknown[] }>(`/storyboard/nodes?branch_id=${branchId}`),

  createNode: (node: unknown) => request('/storyboard/nodes', { method: 'POST', body: node }),

  getChapterBlocks: (chapterId: string) =>
    request<{ blocks: unknown[] }>(`/storyboard/chapters/${chapterId}/blocks`),

  patchBlock: (blockId: string, contentHtml: string) =>
    request(`/storyboard/blocks/${blockId}`, {
      method: 'PATCH',
      body: { content_html: contentHtml },
    }),
};

// ===========================
// Settings API
// ===========================
export const settingsApi = {
  get: () => request<{ settings: unknown }>('/settings'),
  update: (data: unknown) => request('/settings', { method: 'PATCH', body: data }),
};

// ===========================
// Render API (Camera + V1.1 platform & hook guard)
// ===========================
export interface RenderResult {
  block_id: string;
  status: string;
  content_html: string | null;
  actual_char_count: number | null;
  padding_warnings: string[];
  hook_check_reason: string | null;
  message: string;
}

export const renderApi = {
  getSettings: () =>
    request<{ settings: { default_render_mixer: RenderMixerSettings } }>('/settings'),

  adjust: (params: Partial<RenderMixerSettings>) =>
    request<{ default_render_mixer: RenderMixerSettings; message: string }>(
      '/render/adjust',
      { method: 'POST', body: params }
    ),

  // V1.1: full render with char-count + hook guard
  renderBlock: (req: {
    ir_block_id: string;
    pov_type: 'OMNISCIENT' | 'FIRST_PERSON' | 'CHARACTER_LIMITED';
    pov_character_id?: string;
    style_template?: string;
    subtext_ratio?: number;
    target_char_count?: number;
    max_sent_len?: number;
    tolerance_ratio?: number;
    enable_hook_guard?: boolean;
  }) => request<RenderResult>('/render', { method: 'POST', body: req }),

  retry: (blockId: string, params?: Partial<RenderMixerSettings>) =>
    request<RenderResult>(`/render/${blockId}/retry`, { method: 'POST', body: params || {} }),

  switchPlatform: (platform: PlatformProfile) =>
    request<{
      platform: PlatformProfile;
      default_render_mixer: RenderMixerSettings;
      default_target_char_count: number;
      default_max_sent_len: number;
      message: string;
    }>('/render/switch_platform', { method: 'POST', body: { platform } }),
};

// ===========================
// Muse API (V1.1 dual-mode + unblock_writer)
// ===========================
export type MuseMode = 'write' | 'setting';

export const museApi = {
  chatStream: async function* (
    messages: { role: string; content: string }[],
    mode: MuseMode = 'write'
  ) {
    const response = await fetch(`${API_BASE}/muse/chat`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ messages, mode }),
    });

    if (!response.ok || !response.body) {
      throw new Error(`API Error: ${response.status}`);
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    while (true) {
      const { value, done } = await reader.read();
      if (done) break;

      buffer += decoder.decode(value, { stream: true });
      const lines = buffer.split('\n');
      buffer = lines.pop() || '';

      for (const line of lines) {
        if (line.startsWith('data: ')) {
          const data = line.slice(6);
          if (data === '[DONE]') return;
          try {
            const parsed = JSON.parse(data);
            if (parsed.error) throw new Error(parsed.error);
            if (parsed.content) yield parsed.content;
          } catch (e) {
            // ignore parse errors for partial lines
          }
        }
      }
    }
  },

  // V1.1: [卡文救急]
  unblockWriter: (opts?: { chapter_id?: string; recent_chapters?: number }) =>
    request<{ candidates: SparkCandidate[]; message: string }>(
      '/muse/unblock_writer',
      { method: 'POST', body: opts || {} }
    ),
};
