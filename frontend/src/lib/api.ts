/**
 * Genesis Engine - REST API Client
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
// Sandbox API (SPEC §4.1)
// ===========================
export const sandboxApi = {
  getState: () => request<{ state: string }>('/sandbox/state'),

  triggerSpark: (spark: {
    spark_id: string;
    chapter_id: string;
    user_prompt: string;
    overrides?: Record<string, unknown>;
  }) => request<{ message: string; spark_id: string }>('/sandbox/spark', {
    method: 'POST',
    body: spark,
  }),

  sendOverride: (sparkId: string, entityId: string, newDirective: string) =>
    request('/sandbox/override', {
      method: 'POST',
      body: { spark_id: sparkId, entity_id: entityId, new_directive: newDirective },
    }),

  commit: (irBlockId: string, finalContentHtml: string) =>
    request('/sandbox/commit', {
      method: 'POST',
      body: { ir_block_id: irBlockId, final_content_html: finalContentHtml },
    }),

  createBranch: (name: string, originSnapshotId?: string, parentBranchId?: string) =>
    request<{ branch: unknown; message: string }>('/sandbox/branch', {
      method: 'POST',
      body: { name, origin_snapshot_id: originSnapshotId, parent_branch_id: parentBranchId },
    }),

  listBranches: () =>
    request<{ branches: unknown[] }>('/sandbox/branches'),

  rollback: (snapshotId: string) =>
    request<{ snapshot_id: string; branch_id: string; entities_count: number; message: string }>('/sandbox/rollback', {
      method: 'POST',
      body: { snapshot_id: snapshotId },
    }),
};

// ===========================
// Grimoire API (Entity CRUD)
// ===========================
export const grimoireApi = {
  listEntities: (type?: string) =>
    request<{ entities: unknown[] }>(`/grimoire/entities${type ? `?type=${type}` : ''}`),

  getEntity: (entityId: string) =>
    request<{ entity: unknown }>(`/grimoire/entities/${entityId}`),

  createEntity: (entity: unknown) =>
    request('/grimoire/entities', { method: 'POST', body: entity }),

  updateEntity: (entityId: string, data: unknown) =>
    request(`/grimoire/entities/${entityId}`, { method: 'PATCH', body: data }),

  deleteEntity: (entityId: string) =>
    request(`/grimoire/entities/${entityId}`, { method: 'DELETE' }),

  queryEntities: (query: string) =>
    request<{ entities: unknown[]; query: string; count: number }>('/grimoire/entities/query', {
      method: 'POST',
      body: { query },
    }),
};

// ===========================
// Storyboard API
// ===========================
export const storyboardApi = {
  getNodes: (branchId: string) =>
    request<{ nodes: unknown[] }>(`/storyboard/nodes?branch_id=${branchId}`),

  createNode: (node: unknown) =>
    request('/storyboard/nodes', { method: 'POST', body: node }),

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
// Render API (Camera Controls)
// ===========================
export interface RenderMixerSettings {
  pov_type: 'OMNISCIENT' | 'FIRST_PERSON' | 'CHARACTER_LIMITED';
  style_template: string;
  subtext_ratio: number;
}

export const renderApi = {
  getSettings: () => request<{ settings: { default_render_mixer: RenderMixerSettings } }>('/settings'),
  adjust: (params: Partial<RenderMixerSettings>) =>
    request<{ default_render_mixer: RenderMixerSettings; message: string }>('/render/adjust', {
      method: 'POST',
      body: params,
    }),
};

// ===========================
// Muse API
// ===========================
export const museApi = {
  chatStream: async function* (messages: { role: string; content: string }[]) {
    const response = await fetch(`${API_BASE}/muse/chat`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ messages }),
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
  }
};
