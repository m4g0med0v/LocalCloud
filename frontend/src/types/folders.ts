import type { NodeListItem, NodeRead } from "./nodes";

export interface FolderCreateRequest {
  name: string;
  parent_id?: string | null;
}

export interface FolderPatchRequest {
  name?: string;
}

export interface FolderRead {
  id: string;
  node_id: string;
  description: string | null;
  color: string | null;
  created_at: string;
  updated_at: string;
  node: NodeRead | null;
}

export interface FolderContent {
  folder: FolderRead;
  breadcrumbs: NodeListItem[];
  items: NodeListItem[];
  total: number;
}
