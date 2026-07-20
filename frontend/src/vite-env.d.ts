/// <reference types="vite/client" />

// Clôture A-1 : le run servi est configurable au build (fin du hard-code). Défaut dans api.ts.
interface ImportMetaEnv {
  readonly VITE_RUN_LABEL?: string
}
interface ImportMeta {
  readonly env: ImportMetaEnv
}
