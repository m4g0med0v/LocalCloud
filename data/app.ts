// LocalCloud — typed API client

export interface NodeListItem {
  id: string;
  name: string;
  node_type: 'file' | 'folder';
  parent_id: string | null;
  file_size_bytes?: number | null;
  file_mime_type?: string | null;
  created_at: string;
  updated_at: string;
}

export interface PageResponse<T> {
  items: T[];
  total: number;
  limit: number;
  offset: number;
}

export interface UploadSession {
  id: string;
  parent_node_id: string;
  file_name: string;
  file_size_bytes: number;
  status: 'created' | 'uploading' | 'completed' | 'failed';
  progress_percent: number;
}

const API_BASE = '/api/v1';

async function fetchJson<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(API_BASE + path, {
    ...init,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...init?.headers },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json() as Promise<T>;
}

export const nodesApi = {
  list: (parentId?: string | null): Promise<PageResponse<NodeListItem>> =>
    fetchJson(`/nodes/${parentId ? `?parent_id=${parentId}` : ''}`),

  rename: (id: string, name: string): Promise<void> =>
    fetchJson(`/nodes/${id}/rename`, { method: 'POST', body: JSON.stringify({ name }) }),

  softDelete: (id: string): Promise<void> =>
    fetchJson(`/nodes/${id}`, { method: 'DELETE' }),
};

export const uploadsApi = {
  create: (data: {
    parent_node_id: string;
    filename: string;
    file_size_bytes: number;
    parts_count: number;
    mime_type?: string | null;
  }): Promise<UploadSession> =>
    fetchJson('/uploads/', { method: 'POST', body: JSON.stringify(data) }),
};
