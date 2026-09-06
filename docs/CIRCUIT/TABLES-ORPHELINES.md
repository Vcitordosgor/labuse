# TABLES ORPHELINES — l'état des lieux (CIRCUIT-5 lot 1.3)

Généré le 06/09/2026 sur la base locale `labuse` (254 relations dans `public`).
Une table est **orpheline** quand elle n'appartient ni à la carte table → réservoir
(`src/labuse/registre/tables.py`), ni aux fabrications de la pompe, ni aux tables
d'exploitation. La liste ci-dessous n'est PAS tenue à la main : elle est **calculée**
(le schéma moins la carte) — c'est le verrou V1c qui la tient à jour, et une orpheline
nouvelle sans action proposée casse le verrou.

**Rien n'est supprimé.** La purge est un geste de Vic :

```
labuse tables purger            # lister (ce tableau, vivant)
labuse tables purger --apply    # DÉPLACER vers le schéma `poubelle` (jamais un DROP)
```

Retour arrière possible à tout moment : `ALTER TABLE poubelle.<nom> SET SCHEMA public;`.

## Les 32 orphelines — 1,56 Go au total

« Dern. écritures » = compteur cumulé de Postgres (`n_tup_ins+upd+del`) ; « — » = aucune
maintenance datée. « Lecteur connu » = grep mot-entier de `src/labuse` (code servi).

| Table | Taille (Mo) | Écritures cumulées | Dern. maintenance | Lecteur connu | Action proposée |
|---|---:|---:|---|---|---|
| `_lota_grave_parcels` | 4,1 | 73 179 | 2026-09-06 | aucun | purger (photo de travail LOT A — cumul historique, aucun écriveur dans le dépôt) |
| `algo2_prop_features` | 389,1 | 0 | — | aucun | purger (features d'essai algo2) |
| `backup_sp_ppr_avant_littoral` | 2,8 | 0 | — | aucun | purger (backup PPR avant littoral — Saint-Pierre) |
| `backup_spaul_ppr_avant_littoral` | 18,4 | 0 | — | aucun | purger (backup PPR avant littoral — Saint-Paul) |
| `cascade_ext_avant` | 0,0 | 0 | — | aucun | purger (photo avant cascade ext) |
| `conso_baseline_commune` | 0,0 | 0 | — | aucun | archiver (baseline conso) |
| `m50_marker` | 0,0 | 0 | — | aucun | purger (marqueur de migration M50) |
| `m6_a02_backup_plu_dup` | 251,9 | 0 | — | aucun | purger (backup M6 doublons PLU) |
| `m6_p103_backup_dvf_surfaces` | 0,1 | 0 | — | aucun | purger (backup M6 surfaces DVF) |
| `m6_snapshot_mvt_post2a` | 220,8 | 0 | — | aucun | purger (photo M6 tuiles) |
| `m6_snapshot_mvt_post2b` | 220,7 | 0 | — | aucun | purger (photo M6 tuiles) |
| `mv_toitures_tertiaires` | 1,8 | 0 | — | aucun | archiver (matérialisation toitures tertiaires) |
| `ortho_verdicts_quarantaine` | 0,1 | 0 | — | aucun | archiver (quarantaine ortho historique) |
| `p_model_bati_features` | 37,7 | 0 | — | aucun | purger (features d'essai modèle P) |
| `p_model_scores_2026` | 55,2 | 0 | — | aucun | archiver (scores modèle P 2026 — photo) |
| `p_model_static_pre_v8` | 79,1 | 0 | — | `bascule_gardes.py` | archiver (photo pré-v8 — **à débrancher de bascule_gardes d'abord**) |
| `parcel_adjacence` | 70,5 | 0 | — | aucun | archiver (adjacence) |
| `parcel_au_statut_pre_m32` | 3,2 | 0 | — | aucun | purger (photo pré-M32, relevée par CIRCUIT-0) |
| `parcel_au_statut_prebascule` | 3,2 | 0 | — | aucun | purger (photo pré-bascule) |
| `parcel_residuel_pre_v8` | 17,2 | 0 | — | `bascule_gardes.py` | archiver (photo pré-v8 — **à débrancher de bascule_gardes d'abord**) |
| `parcel_residuel_rerun` | 23,1 | 0 | — | aucun | purger (rerun d'essai) |
| `parcel_vue_mer` | 13,0 | 0 | — | aucun | archiver (vue mer) |
| `parcel_zone_plu_prebascule` | 21,6 | 0 | — | aucun | purger (photo pré-bascule) |
| `pv_registry` | 0,8 | 0 | — | aucun | archiver (registre PV) |
| `qa_cadastre_bati` | 147,5 | 0 | — | aucun | archiver (QA bâti cadastre — passe historique) |
| `repli_pcov` | 7,0 | 0 | — | aucun | purger (repli de migration) |
| `repli_sp_residuel` | 2,1 | 0 | — | aucun | purger (repli de migration) |
| `segment_preset_counts` | 0,1 | 0 | — | aucun | archiver (compteurs de presets) |
| `segment_presets` | 0,1 | 0 | — | aucun | archiver (presets de segments) |
| `solar_api_cache` | 0,0 | 0 | — | aucun | purger (cache API solaire mort) |
| `tdl_faisa` | 9,1 | 0 | — | aucun | purger (table de travail faisa) |
| `zone_cat_p` | 0,3 | 0 | — | aucun | archiver (catégories de zone P) |

`purger` = déplacer vers `poubelle` dès que Vic veut · `archiver` = idem, mais garder
longtemps (photo historique qui pourrait resservir) · les deux passent par la même
commande, la différence est le moment où `poubelle` sera vidée (jamais en autonomie).

## À rattacher (PAS des orphelines — des données servies sans ligne au catalogue)

Ces tables ont des lecteurs et servent des écrans ; il leur manque une ligne `data_sources`
(ou un slug registre). Elles apparaissent au Résumé sous « à décider » :

| Table | Situation | Question pour Vic |
|---|---|---|
| `mairies` | slug registre `annuaire_service_public`, AUCUNE ligne `data_sources` | créer la ligne catalogue ? |
| `rnic_coproprietes` | slug registre `rnic_anah`, AUCUNE ligne `data_sources` | créer la ligne catalogue ? |
| `rpls_commune` | servie (Flash/PDF/fiche), ni slug ni ligne | créer slug + ligne, ou débrancher ? |
| `commune_conso_enaf` | passe-plat `pression_zan_ha`, ni slug ni ligne | créer slug + ligne ? |

## Réservoirs sans lecteur au registre (lot 1.4 — « à décider »)

Neuf réservoirs de la vitrine ne sont lus par AUCUNE donnée déclarée du registre (ni par
`reservoirs=`, ni par `table=`, ni par `kind=`). Leurs tables nourrissent le scoring ou des
écrans jamais déclarés — la question est : « source à retirer, ou lecteur manquant ? »

`bd_ortho_irc` · `cadastre_epoque` · `dpe_ademe` · `inpi_rne` · `lidar_hd_mnh` · `mobpro` ·
`office_eau_chroniques` · `parkings_osm_aper` · `recherche_entreprises_dinum`

(Exemples : le DPE n'apparaît NULLE PART dans le registre alors que `dpe_records` nourrit
`v_passoire_thermique` et le scoring ; MOBPRO a été abandonné par ZONE-DONNÉES lot 2 mais la
ligne est restée en vitrine.)

## Note

Une « couche archivée » vit AUSSI à l'intérieur d'une table servie : `spatial_layers`
porte 3 lignes `kind='plu_gpu_zone__archive_m40'` (archive M40). Ce n'est pas une table à
purger — relevé ici pour mémoire, le nettoyage éventuel passe par un DELETE ciblé de Vic.
