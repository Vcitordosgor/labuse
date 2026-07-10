# NOTES — Wave Sitadel3 : refresh permis de construire (SDES/Dido)

Branche `feat/wave-sitadel3` (jamais mergée — Vic valide puis merge en `--no-ff`).
Session du 10/07/2026. Source : flux national SDES/Dido, dispositif **Sitadel3** (mars 2026),
dataset `6513f0189d7d312c80ec5b5b`, 4 datafiles (logements / locaux / PA / PD), licence LO,
MAJ mensuelle. Endpoint retenu : `GET /dido/api/v1/datafiles/{rid}/csv?DEP_CODE=eq:974`
(+ `DATE_REELLE_AUTORISATION=gte:` pour le delta) — filtrage SERVEUR, vérifié live.

## Volumétrie avant / après

| | Avant (ODS Région, mort 2023-09) | Après (SDES Sitadel3) |
|---|---|---|
| Permis | 19 975 | **50 043** |
| Période | 2017-01 → **2023-01** (figé) | 2013* → **2026-08** (vivant, mensuel) |
| Mois vides 2017→ mois courant−2 | 41 | **0** |
| Communes | 24 | 24 |
| Taux de géolocalisation | 76,6 % | **78,5 %** |
| Doublons permit_id | 2 | **0** (purgés + contrainte unique `uq_sitadel_permit`) |

\* le flux remonte à 2013 ; 51 647 lignes 974 lues, 51 186 upserts, 461 sans référence
cadastrale (écartées, même règle que la voie ODS). Les lignes ODS écrasées par leur version
SDES gardent leur geom quand la jointure n'en trouve pas (COALESCE).

## Champs pétitionnaire et PV dans le flux réel

- **Pétitionnaire : PRÉSENT** (`DENOM_DEM` / `SIREN_DEM` / `SIRET_DEM`, personnes morales
  seulement — physiques anonymisées à la source). **9 694 permis avec pétitionnaire** stockés
  dans `raw` (`petitioner_name`/`petitioner_siren`/`petitioner_siret`), index
  `ix_sitadel_petitioner_siret` sur `(raw->>'petitioner_siret')` posé.
- **Photovoltaïque : ABSENT** du flux au 10/07/2026 (annoncé par le SDES « plus tard dans
  l'année ») — capté automatiquement dans `raw['pv']` dès qu'une colonne `PV*/I_PHOTOVOLT*`
  apparaîtra (détection générique, non bloquant).
- Parcelles cadastrales : 3 paires `SEC/NUM_CADASTREn` aujourd'hui, boucle **générique**
  prête pour les 15 annoncées (tout passe par `idu_codes`, pas de nouvelle colonne).

## Géolocalisation — pourquoi 21,5 % restent sans geom

Le référentiel `parcels` EST le cadastre courant complet des 24 communes : une référence qui
échoue la jointure échoue aussi l'API Carto (vérifié sur échantillon : parcelles remembrées /
divisées / renumérotées depuis le permis). Le fallback API Carto est donc recentré sur les
seules sections HORS référentiel (35 trouvées, toutes vides côté IGN aussi). Le reliquat est
un état de fait de la source, pas un manque à combler. Taux final ≥ baseline ✓.

## Contrats préservés (vérifiés sur données réelles)

- Clés `raw` identiques à l'ODS (`nb_lgt`, `surf_hab`, `destination`, `daact`, `etat`) →
  `_nature()`/`_statut()` (permits.py) intacts.
- **Codes état Sitadel3 = mêmes codes que l'ODS** : 6 = achevé (99,8 % ont une DAACT),
  2/4/5 sans DAACT → le module M04 « Promesses mortes » fonctionne **sans modification**.
- `/modules/permis` (Radar permis, M03) ancré sur max(date) → affiche les permis post-2023
  **sans modification frontend** (12 derniers mois : 2 265 permis, 3 plus récents en 2026).
- Signal `new_permit_nearby` : recalcul sans erreur, 31 499 parcelles de Saint-Paul avec
  permis 2024+ à proximité (200 m).

## Refresh mensuel (Lot 4)

- `python -m labuse.ingestion.permits_sdes --refresh` : delta depuis max(date) − 3 mois
  (recouvrement états/DAACT tardifs), idempotent (testé : 121 upserts, total inchangé).
- Cron : `deploy/cron.d/sitadel` (le 5 du mois à 04h15, chemins alignés labuse.service,
  `set -a` pour exporter l'EnvironmentFile). Runs tracés dans `ingestion_runs`,
  `data_sources.last_sync_at` posé.

## Points d'attention

- Un permis daté **2026-08-17** (postérieur au jour du run) existe dans la source — quirk
  d'alimentation Sitadel, sans impact (fenêtres ancrées sur max(date)).
- Le fichier « locaux » a un millésime décalé d'un mois (2026-07) par rapport aux trois
  autres (2026-06) — normal côté Dido, le connecteur prend toujours le dernier.
- Voie ODS Région marquée legacy dans permits.py `[† mort depuis 2023-09, remplacé par
  SDES/Dido]`, non appelée ; ses helpers restent partagés.
