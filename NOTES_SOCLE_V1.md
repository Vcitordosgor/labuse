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

## Cycle polish — vu mais PAS fait (matière du prochain cycle)
- **MVT (tuiles vectorielles)** : le geojson 51k parcelles pèse ~3,7 s au premier chargement.
  Un passage en MVT (ST_AsMVT côté API) descendrait sous la seconde et préparera l'île entière.
- **Filtre de zone sur la carte** : la zone filtre liste+compteurs ; assombrir les parcelles hors
  zone demanderait un masque géométrique (turf difference) ou le MVT — différé.
- **Orthos annuelles fines** (2016, 2019, 2022…) : les couches WMTS millésimées par département
  existent mais répondent 400 sur le 974 en accès libre — à recreuser (clés « acces différencié »).
- **Alti sur mesure de distance** (profil altimétrique le long d'un tracé) : l'API geopf le permet
  (elevationpath) — beau candidat outil V1.1.
- **Filtre A-score** : le popover filtre Q mais pas A — attendre le re-jugement du seuil A (Phase 3
  scoring) avant d'exposer.
- **575 ms sur le filtre plein jeu** (51k matchAll client) : acceptable, mais un index client
  (typed arrays) ou le MVT le rendrait instantané.

---

# NUIT DES OUTILS (feat/outils-ia) — recos, volumétries, backlog

## Recos consignées (avant build, données réelles)
- M01 : 6 904 candidats bruts → 698 après C1-C5 ; spec officielle ABSENTE → critères définis dans
  modules.py ; lot = carré inscrit dans le cercle max (conservateur, sous-estime les lots allongés).
- Sitadel : codes `raw.etat` {2,4,5,6} NON documentés par la source ; 6 = achevé (100 % DAACT) ;
  données du 02/01/2017 au 31/01/2023 ; 77 % géocodés (91 % sur 24 mois glissants fin de données).
- M05 : PAS de dates dépôt/décision dans la source → « vélocité » = permis→DAACT (assumé, affiché).
- M07 : 545 SIREN de PM introuvables au RNE (Q≥50, PM privées SP) ; 0 dirigeant inactif ;
  indivision/succession non détectables (Fichiers fonciers non branchés).
- M15 : lecture du zonage via les lignes de cascade (déjà résolu) — 0,7 s au lieu de 2 min 33
  (jointure spatiale île). Leçon générale : le run q_v2 EST un index thématique par parcelle.

## Backlog prochain cycle (vu, pas fait)
- M01 : rectangle inscrit exact (grille/rotating calipers) si la spec l'exige ; multi-communes.
- M08 : curseur d'années supplémentaires quand les millésimes IGN 2006-2015 s'ouvriront sur le 974.
- M11-14 : brancher le cron réel (labuse detect-events) après le prochain run de scoring ; SMTP digest.
- M15 : vrai recalcul règlementaire (moteur de faisabilité avec YAML U en mémoire).
- M17 : surfaces OCS dédoublonnées (ST_Union) + quotas SAR/SCOT officiels quand publiés.
- M19-21 : vrais comptes (auth), révocation de liens M20, clés API gérées.
- ia_log : page d'admin coûts (la table existe).
