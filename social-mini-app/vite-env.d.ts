/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_API_BASE_URL: string;
  readonly VITE_INTERNAL_API_KEY: string;
  readonly VITE_ADMIN_TOKEN: string;
  readonly VITE_ALLOWED_HOSTS?: string;
  readonly VITE_API_PROXY_TARGET?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
