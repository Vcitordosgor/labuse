# CRON-2 — Compléter CRON-1

Branche `feat/outils-1`. Golden non touché (`config/served_run.txt` = q_v11_m137, inchangé). Les 4 restes
signalés au compte-rendu CRON-1 sont traités.

## K7 — la page front `/admin/cron`

Nouvelle section admin **Cron** (`frontend/src/components/admin/Cron.tsx`), sur le backend déjà livré.
Un rang par job (13) : **nom + statut**, description en clair, **cadence + heure Réunion**, **dernière
exécution** (date + durée), **prochaine exécution** (calculée sans dépendance — mini-parser cron dans
`jobs.prochaine`, affichée en heure Réunion), **compteurs métier** (ou l'erreur), **bouton « Lancer
maintenant »** (POST `/admin/cron/{nom}/run` → CLI détachée → **même verrou flock** : un job en cours
refuse le double lancement), **« voir le log »** (dernières lignes), **mention dry-run** (bandeau tant que
Brevo/SMTP n'est pas branché + puce par job). Capture `01-admin-cron.png` (13 jobs, tous verts après
relance), `02-admin-cron-log.png` (log ouvert).

## Badges sources-fraîcheur — réconciliés

Le job `sources-fraicheur` calcule désormais sur les **AFFICHÉES** via le **même prédicat canonique
`est_affichee`** que `/sources` — plus le `WHERE lower(status) IN ('connecte','manuel')` qui comptait 67
(sources non affichées incluses). `/sources` sert le statut **PERSISTÉ** (`data_sources.fraicheur_statut`,
écrit par le job) au lieu de l'estimer à la volée. **Un seul chiffre, un seul prédicat** : mesuré, /sources
et le job renvoient le même ensemble (64), badges { à_jour 3 · en_retard 2 · sans_échéance 59 }. Le front
affiche `en_retard` ET `en_panne` (retard fort). Garde par existence de colonne (jamais d'abort de
transaction si le job n'a pas encore tourné → repli sur le calcul live). Capture `03-sources-page.png`.

## K5 — run candidat après ingestion (sitadel) + rapport mail

`ingest_sitadel` déclenche, en fin d'ingestion réussie, `golden_ops.rapport_candidat(dry_run)` : compare
le run candidat (le plus récent en base, non servi) au run servi et envoie le rapport (**parcelles promues,
tiers, dérive %**), dry-run aware. La **promotion reste manuelle** (`golden promote`) — aucune bascule
automatique, le run servi n'est jamais touché. **Testé sur une ingestion simulée** (candidat synthétique
`q_candidat_test` injecté puis nettoyé) : promues 1224/1478, **dérive −17,2 %**, rapport produit ;
`served_run.txt` inchangé.

## Backup — rotation en constante + taille au rapport

`BACKUP_ROTATION_N = 7` (constante) : on garde les 7 dumps les plus récents (le pull-mac archive plus
loin). `rapport-admin` affiche désormais **la taille du dernier dump** (« nom · N Mo », ou « aucun dump »).

## Vérif finale

| Contrôle | Résultat |
|---|---|
| `pytest tests/` | **1999 passed, 43 skipped, 0 failed** |
| `tsc` / `vitest` / `build` | **0 erreur · 108 passed · vert** |
| Golden | **intact** (served_run inchangé, aucun fichier scoring) |
| Page cron | 13 jobs, tous les champs, Lancer maintenant, log, dry-run — capturée |
| Sources | badges depuis le job persisté, un seul prédicat (64) — capturée |
| Candidat post-ingestion | dérive −17,2 % calculée sur ingestion simulée, servi intact |
| Rapport dry-run | logué via `send_email` (no-config sans SMTP) ; en local SMTP présent = envoyé |

**Fichiers** : `frontend/src/components/admin/Cron.tsx` (K7), `AdminView.tsx` (+section cron),
`lib/api.ts` + `lib/types.ts` (types cron + fraicheur vocab), `SourcesPage.tsx` (badge en_panne) ;
backend `jobs.py` (prochaine exéc), `jobs_impl.py` (rotation 7, sources 59/prédicat, taille dump),
`golden_ops.py` (rapport_candidat, candidat depuis parcel_p_score_v2), `api/app.py` (/sources persisté).

**Provenance** — API+front redémarrés (uvicorn :8000, build /socle/) ; captures Playwright ; état sous
`.local/` (gitignoré) ; golden non touché.
