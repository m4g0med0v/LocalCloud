// LocalCloud — frontend entry point

const API_BASE = '/api/v1';

async function fetchJson(path, options = {}) {
  const res = await fetch(API_BASE + path, {
    ...options,
    credentials: 'include',
    headers: { 'Content-Type': 'application/json', ...options.headers },
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}: ${await res.text()}`);
  return res.json();
}

class FileManager {
  constructor(parentNodeId) {
    this.parentNodeId = parentNodeId;
    this.selectedIds = new Set();
  }

  async listFiles() {
    const params = this.parentNodeId ? `?parent_id=${this.parentNodeId}` : '';
    return fetchJson(`/nodes/${params}`);
  }

  async uploadFile(file) {
    const session = await fetchJson('/uploads/', {
      method: 'POST',
      body: JSON.stringify({
        parent_node_id: this.parentNodeId,
        filename: file.name,
        file_size_bytes: file.size,
        parts_count: 1,
        mime_type: file.type || null,
        part_size_bytes: file.size,
      }),
    });
    console.log('Upload session created:', session.id);
    return session;
  }

  selectItem(id, { ctrl = false, shift = false } = {}) {
    if (ctrl) {
      if (this.selectedIds.has(id)) this.selectedIds.delete(id);
      else this.selectedIds.add(id);
    } else {
      this.selectedIds = new Set([id]);
    }
    this.render();
  }

  render() {
    console.log('Selected:', [...this.selectedIds]);
  }
}

document.addEventListener('DOMContentLoaded', () => {
  const manager = new FileManager(null);
  manager.listFiles().then(data => console.log('Files:', data));
});
