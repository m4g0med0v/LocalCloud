export interface PageMeta {
  limit: number;
  offset: number;
  total: number;
  count: number;
  has_next: boolean;
  has_previous: boolean;
  page: number;
  pages: number;
}

export interface PageResponse<T> {
  items: T[];
  meta: PageMeta;
}

export interface PaginationParams {
  limit?: number;
  offset?: number;
}
