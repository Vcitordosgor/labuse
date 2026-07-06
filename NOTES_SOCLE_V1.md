# NOTES CHANTIER — SOCLE V1 (feat/socle-v1)

## Source de vérité affichage
`dryrun_parcel_evaluations` / `dryrun_cascade_results`, `run_label='q_v2'` — épinglée dans
`frontend/src/lib/api.ts` (`SOURCE`). Tous les endpoints acceptent `?source=q_v2` (extension,
pas duplication). La bascule vers les tables officielles = chantier séparé post-Brique 1 (brief).

## ⚠ Écart chiffres à arbitrer (Vic, revue finale)
Le mandat fixe « 42 chaudes · 486 à surveiller · 13 979 à creuser » comme vérités. Le SQL direct
sur q_v2/Saint-Paul — la référence que le mandat impose à l'auto-QA — donne **83 · 1 720 · 3 353**
(les « 486 » = à_surveiller du run *etape2*, les autres ne correspondent à aucun run en base).
L'UI affiche le SQL. Si 42 est la cible produit, c'est un recalibrage matrice (Phase 3 scoring),
pas un correctif d'affichage. **Invariant vérifié : 97415000AC0253 = chaude par événement.** ✓

## Incident « serveur périmé » (cause des bugs signalés sur la Brique 1)
Un `labuse api` lancé avant les nouveaux endpoints servait l'ancien code : le front à jour
appelait `/parcels/{idu}?source=q_v2` → ancien format → crash au clic parcelle ; index.html en
cache navigateur → vieux bundle → filtres morts. Corrections : middleware `no-store` sur le HTML,
ErrorBoundary global, états d'erreur réseau explicites (« serveur à relancer ? »).

## Dettes / hors V1
- **Lieu-dit** : absent de `parcels` → les cartes résultat affichent la commune. Enrichissement
  futur (lookup spatial BD TOPO lieux-dits).
- **Omnibox adresse** : IDU seulement (pas de géocodeur branché).
- **J-2 dynamique** : le badge du rail est statique ; la page Sources calcule la vraie fraîcheur
  par source (last_sync_at). Câbler le badge sur max(last_sync_at) = petite itération.
- **Onglet Bilan** : placeholder assumé (charge foncière = SDP × prix − coûts, en attente du
  paramétrage des coûts standards 974 par Vic).
- **/sources test** : le bouton « tester la connexion » de l'API existe, non exposé dans l'UI V1.
- **MVT tuiles** : geojson bbox suffit à 51 129 parcelles simplifiées (~15 Mo gzip) ; passer en MVT
  si généralisation île entière.

## Auto-QA
`frontend/qa/qa.mjs` — 2 passes (1440/1280) : console, cliquables (effet réel), compteurs vs psql,
layout, anti-crash 10 parcelles aléatoires, parcours complet (fiche→PDF→pipeline→sources).
Sortie : « AUTO-QA 100 % VERTE ». Captures : docs/design/captures/qa/.
