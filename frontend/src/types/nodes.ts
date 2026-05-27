export type NodeType = "file" | "folder";
export type NodeVisibility = "private" | "shared" | "public";

export interface NodeRead {
  id: string;
  owner_id: string;
  parent_id: string | null;
  name: string;
  node_type: NodeType;
  visibility: NodeVisibility;
  path: string;
  depth: number;
  created_by: string | null;
  updated_by: string | null;
  deleted_by: string | null;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
  deleted_at: string | null;
}

export interface NodeListItem {
  id: string;
  owner_id: string;
  parent_id: string | null;
  name: string;
  node_type: NodeType;
  visibility: NodeVisibility;
  path: string;
  depth: number;
  created_at: string;
  updated_at: string;
  is_deleted: boolean;
  file_size_bytes?: number | null;
  file_mime_type?: string | null;
}

export interface NodeMoveRequest {
  target_parent_id: string | null;
}

export interface NodeSearchResult {
  id: string;
  name: string;
  node_type: NodeType;
  path: string;
  owner_id: string;
  created_at: string;
}
