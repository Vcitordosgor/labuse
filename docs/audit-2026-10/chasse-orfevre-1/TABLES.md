# CHASSE-ORFEVRE-1 — Bilan par table

Base `labuse`, **274 tables public** (18/10/2026). ~70 tables examinées en profondeur ; le reste écarté avec motif (annexe).
Contrôles rejouables : `scripts/angle_a_tables.py` (68 contrôles, 0 erreur à l'exécution de référence).
Renvois : `ORF-xx` → `ECARTS.md` ; `K-x` = déjà connu ; détail des requêtes → `brouillons/ANGLE-A.md`.
« PROPRE » = tous les contrôles joués (doublons, orphelins, NULL obligatoires, valeurs impossibles, encodage, géométries) à zéro.

## Cœur parcellaire
| Table | Lignes | Verdict |
|---|---|---|
| parcels | 434 582 (dont 1 353 disparues) | PROPRE sauf ORF-28 (1 593 écarts surface/contenance) ; 0 doublon idu, 0 geom invalide/vide, 0 commune hors 24 ; 2 GEOMETRYCOLLECTION (ORF-30) ; 391 parcelles ≤ 1 m² toutes neutralisées (ORF-45) |
| parcel_geometrie | 431 663 | PROPRE (0 orphelin, 0 doublon) |
| parcel_zone_plu | 430 320 | PROPRE (0 zone vide/minuscule/espaces — cf. angle C) |
| parcel_residuel_runs | 1 729 784 (4 runs) | ORF-04 (61 555 taux_emprise_pct > 100 au run servi 16) ; 0 orphelin, 0 sdp négatif |
| residuel_runs | 4 (servi = 16, q_v19) | PROPRE |
| score_labuse | 1 298 121 (3 runs) | ORF-04 (phrases de contribution non bornées) ; 0 orphelin, 0 score hors 0-100, 0 bande NULL ; bande HC nouvelle en q_v19 (observation, à documenter côté UI) |
| score_labuse_runs | 3 | ORF-16 (n_parcelles faux 3/3) |
| parcel_v_score | 431 663 | PROPRE |
| score_e | 279 946 | PROPRE |
| mvt_parcels | 433 229 | PROPRE |
| parcel_au_statut | 10 537 | PROPRE ; classes ASCII/accent mélangées (observation) |
| parcel_constructibilite | 11 782 | PROPRE |
| parcel_blocs / parcel_bloc_membres | 11 222 / 59 870 | 1 197 siren « U… » by design (A-08) ; n_parcelles = membres 0 écart ; 0 orphelin |

## Satellites parcelle (valeurs)
| Table | Lignes | Verdict |
|---|---|---|
| parcel_viabilisation | 431 663 | PROPRE (scores 0-100, 4 bandes) |
| parcel_terrain | 423 452 | PROPRE (pentes 0-90, max ≥ moy) |
| parcel_solar | 429 284 | PROPRE |
| parcel_vegetation | 426 107 | PROPRE (pct 0-100, ndvi −1..1) |
| parcel_amenites | ~419 789 | PROPRE |
| parcel_filtre_bati | 294 942 | K-2 (année 1761 héritée DPE) ; ORF-45 (ratio_pct plafond 300 flottant, 10 lignes > 300) |
| parcel_residuel_bati | 288 287 | PROPRE (hauteurs ≤ 55,6 m) |
| parcel_renouvellement | 55 796 | PROPRE |
| parcel_anc / parcel_adresse / parcel_equipements | 278 685 / 258 403 / 11 558 | PROPRE |
| parcel_pau / parcel_acquerabilite / parcel_entree_tete / pc_caducs | 2 656 / 1 060 / 514 / 4 822 | PROPRE |
| parcel_signaux_vie | 30 896 | ORF-26 (185 idu orphelins) |
| parcel_veille_succession | 6 256 | ORF-48 (1 âge 114) |
| parcel_signals | 69 357 | PROPRE |
| parcel_bati_revele | 16 142 | PROPRE |
| batiment_hauteur_lidar | 303 452 | K-1 (hauteurs impossibles, bornées à la lecture) ; 0 orphelin/doublon |
| parcel_cosia_couverture | (couche) | ORF-05 (parts servies > 100 % — défaut au SERVICE, pas à la table) |

## DVF / marché
| Table | Lignes | Verdict |
|---|---|---|
| dvf_mutations_parcelle | 102 551 | ORF-13 (1 128 orphelins id_parcelle) ; ORF-27 (7 082 groupes doublons structurels, 1 351 vf ≤ 1 €, 698 vf NULL) |
| dvf_mutations | 29 566 | ORF-06 (1 mutation inventée, vestige démo) ; ORF-27 (16 vf ≤ 1 €) ; ORF-18 (index date_mutation manquant) |
| dvf_mutation_detail | 55 016 | PROPRE |
| dvf_mutations_histo | 110 477 | ORF-27 (2 289 vf ≤ 1 €) ; 0 recouvrement avec le flux actuel ; lon/lat 100 % NULL (ORF-49) |
| dvf_secteur_medianes | 2 359 | PROPRE (0 médiane ≤ 0, euros symboliques bien filtrés) |
| dvf_prix_sortie_neuf | 12 | PROPRE |

## Propriétaires / entreprises
| Table | Lignes | Verdict |
|---|---|---|
| sirene_etablissements | 173 524 → **158 515 dans la journée** | ORF-11 (purge non journalisée) ; ORF-48 (10 dates de création impossibles) ; ORF-18 (index siren manquant) ; **0 Luhn KO**, 0 doublon siret, 0 geom NULL |
| etablissement_parcelle | 131 187 | PROPRE (0 Luhn KO, 0 orphelin siret ni idu) |
| parcelle_personne_morale | 82 701 | ORF-13 (601 idu orphelins) ; 10 145 siren « U… » by design ; 0 doublon, 0 Luhn KO |
| pm_dirigeants | 27 146 | PROPRE |
| owner_enrichment | 9 730 | ORF-48 (121 siren périmés) |
| bodacc_depots | 14 078 | PROPRE ; 4 colonnes jamais lues (ORF-49) |
| rnic_coproprietes | 2 220 | PROPRE |

## Permis / bâti / adresses
| Table | Lignes | Verdict |
|---|---|---|
| sitadel_permits | 50 809 | ORF-48 (734 sans geom, tous rattachables par idu_codes) ; 0 doublon, 0 date future |
| m10_permit_delais | 50 290 | ORF-15 (7 633 délais négatifs valide=f ; 127 incohérences valide=t) |
| piscines | 50 516 | ORF-14 (15 servies sans idu, 6 servies sans commune) ; 28 surfaces ≤ 0 écartées |
| rnb_batiments | 414 081 | PROPRE |
| adresses | 339 915 | ORF-26 (266 fantômes BAN Petite-Île ; 2 043 sur parcelles disparues) ; 0 geom NULL, 0 doublon, 0 encodage |
| adresse_parcelles | 416 365 | PROPRE |
| cadastre_historique | 6 526 | PROPRE — « orphelins » par construction |
| dpe_records | 1 123 | K-2 (année 1761) ; ORF-38 (DELETE sans garde de volume, côté job) |

## Référentiels communaux
| Table | Lignes | Verdict |
|---|---|---|
| communes_referentiel | 24 | PROPRE (les 24 INSEE 97401-97424) |
| mairies | 24 | ORF-22 (Saint-Denis sans email) |
| commune_contexte_cache | 24 | PROPRE (recalculé du 18/10 — le run du soir l'a rempli) |
| rpls / sru / enaf / insee_logement / rei / zonage_abc / population / fiscal / mvt / grid / rp_logement | 24 chacune | PROPRE (24/24 partout) ; rpls_commune : 4 colonnes mortes (ORF-49) |
| plu_reglement_extrait | 3 258 | PROPRE |
| catnat_arretes | 426 | PROPRE ; 1 arrêté de retard vs producteur (ORF-48) |

## Comptes / CRM / journal
| Table | Lignes | Verdict |
|---|---|---|
| comptes | 47 | ORF-12 (2 doublons de nom = comptes de recette, dont « recette onb » ×2 ACTIFS) |
| utilisateurs | 29 | ORF-12 (1 actif sans hash `qa-m23@labuse.test`) ; 0 doublon email, 0 orphelin |
| sessions_auth | 1 | PROPRE |
| mail_queue | 17 | ORF-07 (12 a_rejouer dus, 3 vers compte supprimé) ; ORF-08/ORF-35/ORF-47 côté code |
| evenements_compte | 496 | ORF-12 (84/89 orphelins, comptes de recette) |
| stripe_events | 185 | PROPRE (dédup exactly-once saine) |
| pipeline_entries | 227 | K-3 (38 GB-TEST) ; 0 orphelin |
| projets / projet_parcelles | 9 / 1 004 | PROPRE |
| alertes | 9 061 | PROPRE |
| usage_events | 16 479 | PROPRE |
| consultation_log | 9 832 | ORF-12 (617 idu orphelins dont idu forgés de recette) |
| share_links | 50 | PROPRE |
| courrier_demandes / courrier_envois | 33 / 3 | ORF-36 (28 demandes anciennes sans relance, 2 `poste` legacy) |
| watch_zones / watched_parcels / saved_searches | 3 / 14 / 3 | PROPRE |
| event_log | (journal) | ORF-09 (31 couples dedup/jour dupliqués, ×19 — dépôt Radar) |
| pige_depots | 238 | ORF-09 (19× le même hash) |

## Annexe — tables écartées (et pourquoi)
- **Datasets ML reconstruisibles** (`p_model_*` ×17 ~4,3 M lignes chacun ; `dryrun_cascade_results` 59 M ; `dryrun_parcel_evaluations` ; `cascade_results` 20 M ; `parcel_evaluations` ; `score_snapshot_parcelles` ; `parcel_p_score_v2` ; `p_score_v2_runs`) : intermédiaires de scoring regénérés par les arènes/runs, non servis ligne à ligne ; trop volumineux pour un Mac 8 Go. Les sorties SERVIES (score_labuse, parcel_residuel_runs…) ont, elles, été auditées.
- **Staging cadastre** (`_cad_sm1_*`) : tables de travail du chargement.
- **Couches spatiales brutes** (spatial_layers, ocsge_*, rgealti_*, filosofi, arcep, ban_plus, dfi, tuyau_*, etc. — liste complète dans `brouillons/TABLES-BRUT.md`) : réservoirs amont rejouables depuis les sources officielles ; leurs produits aval (`parcel_*`) ont été contrôlés.
- **Machinerie interne** (registre_*, circuit_*, data_sources, ia_*, job_runs, ingestion_runs, filtre_*, copilote_*, pige_* hors dépôts, etc.) : journaux/caches/configuration, non servis au client ou couverts par les verrous du circuit — les FILES ont toutefois été auditées par l'angle E.
- **Vides (30 tables)** : rien à contrôler (watch_snapshots, totp_2fa, ops_incidents, prefs_carte, etc.).
- **Quasi-vides** (≤ ~100 lignes) : comptées, aucune anomalie (liste dans `brouillons/TABLES-BRUT.md`).

## Notes de méthode
- DSN `.env` au format SQLAlchemy `postgresql+psycopg://` : retirer `+psycopg` pour psql.
- Validation Luhn jouée en SQL pur (`generate_series`), sans fonction ni table temporaire (rôle read-only).
- Aucune requête > ~10 s ; aucun échantillonnage nécessaire.
- La base BOUGE pendant l'audit (ORF-11) : chaque compte est daté du 18/10.
