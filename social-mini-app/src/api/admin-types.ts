export interface ConfigSchemaField {
  type: string;
  label: string;
  required: boolean;
  sensitive: boolean;
}

export interface Platform {
  id: string;
  name: string;
  slug: string;
  description: string | null;
  auth_type: string;
  config_schema: Record<string, ConfigSchemaField>;
  icon_url: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface Credential {
  id: string;
  platform_id: string;
  platform_slug: string;
  label: string;
  status: string;
  last_verified_at: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface CredentialDetail extends Credential {
  configured_fields: string[];
}

export interface CreateCredentialRequest {
  platform_slug: string;
  label: string;
  credentials: Record<string, string>;
}

export interface UpdateCredentialRequest {
  label?: string;
  credentials?: Record<string, string>;
  is_active?: boolean;
}
