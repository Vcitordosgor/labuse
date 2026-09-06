# Lot E — Inventaire des exports CSV & retrait des gestes utilisateur

Décision Vic 06/09 : **aucun export CSV dans l'app pour l'instant**. On retire le geste (bouton/lien) ;
les **endpoints et helpers back restent** (E3), aucune fonction/route/test back supprimée.

## E1 — Inventaire (avant retrait)

### Points d'export CSV côté écran (user-facing) — RETIRÉS en E2

| # | `fichier:ligne` | Écran / outil | Élément | Type | Endpoint back |
|---|------------------|---------------|---------|------|---------------|
| 1 | `frontend/src/components/compare/ComparePanel.tsx:201` (+ générateur `exporterCsv` 174-183) | Comparer (tableau) | `<button data-compare-csv>` « ⬇ CSV » | Blob généré côté client | aucun (client) |
| 2 | `frontend/src/components/outils/ProspectionSolaire.tsx:256` | Prospection solaire → Piscines | `<a data-piscines-csv>` « ⬇ CSV » | Lien `fmt=csv` | `/modules/prospection-solaire?…&fmt=csv` |
| 3 | `frontend/src/components/outils/ModulePanel.tsx:930` (M03 Vélocité, onglet Permis) | Permis (vélocité d'instruction) | `<a>` « ⬇ CSV » | Lien `fmt=csv` | `/modules/velocite?fmt=csv` |

### Helpers/URL builders CSV — CONSERVÉS (aucun appelant écran ; E3)

| `fichier:ligne` | Helper | Endpoint | État |
|------------------|--------|----------|------|
| `frontend/src/lib/api.ts:806` | `prospectionSolaireCsvUrl(f)` | `/modules/prospection-solaire?…&fmt=csv` | conservé ; l'appel écran (Solaire) retiré, import nettoyé |
| `frontend/src/lib/api.ts:990` | `modPatrimoineCsvUrl(siren)` | `/modules/patrimoine?siren=…&fmt=csv` | conservé ; **déjà orphelin** (aucun composant ne l'appelait) |
| `frontend/src/lib/api.ts:1641` | `projetCsvUrl(id)` | `/projets/{id}/export.csv` | conservé ; **déjà orphelin** (aucun composant ne l'appelait) |

### Exports CSV déjà retirés avant ce mandat (rappel — rien à faire)

- Liste parcelles `/parcels/export.csv` + `csvExportUrl` — supprimés (SUITE-1 S7 / RETOURS-7 Z11), cf. `api.ts:296`.
- Densifier / Renouvellement CSV — retirés OUTILS-1 B7 (`ListPagination.tsx` n'en garde que la mention en commentaire).
- Faisabilité (`data-prog-csv`) — retiré RETOURS-11 O2b (garde de test le vérifie faux).

### Hors périmètre (ce n'est PAS du CSV)

- `frontend/src/lib/filters.ts:196` `CSV_KEYS` — sérialisation de filtres en query « comma-separated », pas un export.
- Exports **PDF** (fiche : `Fiche.tsx:1623` ; EtudeZone déjà retiré) — hors sujet (le mandat vise le CSV).

## E2 — Retrait des gestes (fait)

1. Comparer — bouton `⬇ CSV` + générateur client `exporterCsv` supprimés (`ComparePanel.tsx`).
2. Prospection solaire — lien `⬇ CSV` + import `prospectionSolaireCsvUrl` retirés (`ProspectionSolaire.tsx`).
3. Permis / Vélocité — lien `⬇ CSV` retiré (`ModulePanel.tsx`).

## E3 — Back intact

Aucun endpoint, aucune route, aucun helper `api.ts`, aucun test back supprimé. Les endpoints
`fmt=csv` (`patrimoine`, `prospection-solaire`, `velocite`) et `/projets/{id}/export.csv` restent
servis et testés — seule la porte d'entrée à l'écran disparaît.
