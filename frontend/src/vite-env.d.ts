/// <reference types="vite/client" />

// Clôture A-1 : le run servi est configurable au build (fin du hard-code). Défaut dans api.ts.
interface ImportMetaEnv {
  readonly VITE_RUN_LABEL?: string
  // ECRANS-NOV-1 §1 — l'ordre/les noms des sections de la fiche (JSON), lus de declarations/fiche/sections.yaml au build.
  readonly VITE_FICHE_SECTIONS?: string
}
interface ImportMeta {
  readonly env: ImportMetaEnv
}
