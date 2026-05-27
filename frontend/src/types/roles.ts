export interface Role {
  id: string;
  name: string;
  code: string;
  display_name: string;
  description: string | null;
  is_system: boolean;
  is_active: boolean;
  created_at: string;
}
