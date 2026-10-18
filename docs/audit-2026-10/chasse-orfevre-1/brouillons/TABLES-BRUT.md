# CHASSE-ORFEVRE-1 — Angle A : bilan table par table

Base `labuse`, 274 tables public (18/10/2026). ~70 tables examinées en profondeur, le reste écarté avec motif (§ fin).
Renvois « A-xx » → `ANGLE-A.md`. « PROPRE » = tous les contrôles joués sont à zéro.

## Cœur parcellaire
| Table | Lignes | Verdict |
|---|---|---|
| parcels | 434 582 (dont 1 353 disparues) | PROPRE sauf A-19 (1 593 écarts surface/contenance, 7 parcelles >10 Mm² légitimes = forêts, 1 381 contenance NULL) ; 0 doublon idu, 0 geom invalide/vide, 0 commune hors 24, 0 incohérence nom/idu |
| parcel_geometrie | 431 663 | PROPRE (0 orphelin, 0 doublon) |
| parcel_zone_plu | 430 320 | PROPRE (0 orphelin, 0 doublon) |
| parcel_residuel_runs | 1 729 784 (4 runs) | A-02 (taux/pct > 100 %) ; 0 orphelin parcel_id/run_seq, 0 sdp négatif |
| residuel_runs | 4 (servi = 16 q_v19) | PROPRE |
| score_labuse | 1 298 121 (3 runs) | PROPRE (0 orphelin, 0 score hors 0-100, 0 bande NULL, score NULL ⇔ non_calculable) ; bande HC nouvelle en q_v19 (observation) |
| score_labuse_runs | 3 | A-01 (n_parcelles faux 3/3) |
| parcel_v_score | 431 663 | PROPRE (0 orphelin, 0 doublon) |
| score_e | 279 946 | PROPRE (0 orphelin, 0 doublon (idu,run), 0 prix ≤0, 0 estimable sans prix) |
| mvt_parcels | 433 229 | PROPRE (0 orphelin, 0 doublon, 0 surface ≤0, 0 geom NULL) |
| parcel_au_statut | 10 537 | PROPRE (0 orphelin) ; classes ASCII/accent mélangées (observation) |
| parcel_constructibilite | 11 782 | PROPRE (0 orphelin) |
| parcel_blocs / parcel_bloc_membres | 11 222 / 59 870 | A-08 (1 197 siren « U… » by design) ; n_parcelles = membres 0 écart ; 0 orphelin bloc/parcel |

## Satellites parcelle (valeurs)
| Table | Lignes | Verdict |
|---|---|---|
| parcel_viabilisation | 431 663 | PROPRE (scores 0-100, 4 bandes) |
| parcel_terrain | 423 452 | PROPRE (pentes 0-90, max ≥ moy) |
| parcel_solar | 429 284 | PROPRE (score, proba, azimut, ghi dans bornes) |
| parcel_vegetation | 426 107 | PROPRE (pct 0-100, ndvi −1..1) |
| parcel_amenites | ~419 789 | PROPRE (0 orphelin parcel_id) |
| parcel_filtre_bati | 294 942 | A-04 (1 année 1761 héritée DPE) ; 0 orphelin/doublon |
| parcel_residuel_bati | 288 287 | PROPRE (hauteurs ≤55,6 m, 0 emprise négative) |
| parcel_renouvellement | 55 796 | PROPRE (scores/contraintes dans bornes, 0 orphelin) |
| parcel_anc / parcel_adresse / parcel_equipements | 278 685 / 258 403 / 11 558 | PROPRE (0 orphelin, 0 doublon) |
| parcel_pau / parcel_acquerabilite / parcel_entree_tete / pc_caducs | 2 656 / 1 060 / 514 / 4 822 | PROPRE (0 orphelin) |
| parcel_signaux_vie | 30 896 | A-16 (185 idu orphelins) |
| parcel_veille_succession | 6 256 | A-23 (1 âge 114) ; 0 orphelin |
| parcel_signals | 69 357 | PROPRE (0 orphelin parcel_id) |
| parcel_bati_revele | 16 142 | PROPRE (0 orphelin) |
| batiment_hauteur_lidar | 303 452 | A-03 CONNU (56 faîtage ≤0, 2 >60 m dont 53 401 m, 1 507 égout ≤0) ; 0 orphelin/doublon |

## DVF / marché
| Table | Lignes | Verdict |
|---|---|---|
| dvf_mutations_parcelle | 102 551 | A-05 (7 082 groupes doublons structurels, 1 128 orphelins id_parcelle, 1 351 vf ≤1 €, 698 vf NULL) |
| dvf_mutations | 29 566 | A-06 (16 vf ≤1 €) ; 0 doublon mutation_id, 0 geom NULL |
| dvf_mutation_detail | 55 016 | PROPRE (0 orphelin id_mutation) |
| dvf_mutations_histo | 110 477 | A-06 (2 289 vf ≤1 €) ; 0 recouvrement avec parcelle |
| dvf_secteur_medianes | 2 359 | PROPRE (0 médiane ≤0 ou >20 k€/m², 0 n_ventes ≤0) |
| dvf_prix_sortie_neuf | 12 | PROPRE (comptage seul) |

## Propriétaires / entreprises
| Table | Lignes | Verdict |
|---|---|---|
| sirene_etablissements | 173 524 | A-09 (10 dates création impossibles) ; **0 Luhn KO**, 0 doublon siret, 0 insee hors 24, 0 geom NULL |
| etablissement_parcelle | 131 187 | PROPRE (0 Luhn KO, 0 orphelin siret ni idu) |
| parcelle_personne_morale | 82 701 | A-07 (601 idu orphelins) + A-08 (10 145 siren « U… » by design) ; 0 doublon (idu,siren,millésime), 0 Luhn KO |
| pm_dirigeants | 27 146 | PROPRE (0 Luhn KO, 0 prise de fonction future) |
| owner_enrichment | 9 730 | A-22 (121 siren périmés) |
| bodacc_depots | 14 078 | PROPRE (0 siren mal formé) |
| rnic_coproprietes | 2 220 | PROPRE (0 orphelin, 0 siret mal formé, 0 lots incohérents, 0 doublon) |

## Permis / bâti / adresses
| Table | Lignes | Verdict |
|---|---|---|
| sitadel_permits | 50 809 | A-20 (734 sans geom, tous avec idu_codes) ; 0 doublon permit_id, 0 date future |
| m10_permit_delais | 50 290 | A-11 (7 633 délais négatifs valide=f ; 127 incohérences valide=t) |
| piscines | 50 516 | A-10 (380 sans idu dont 15 servies ; 4 359 sans commune dont 6 servies ; 28 surfaces ≤0 écartées) |
| rnb_batiments | 414 081 | PROPRE (0 sans geom, 0 doublon rnb_id, 0 insee hors 24) |
| adresses | 339 915 | PROPRE (0 geom NULL, 0 doublon id_ban, 0 encodage) |
| adresse_parcelles | 416 365 | PROPRE (0 doublon, 0 orphelin BAN ni parcelle) |
| cadastre_historique | 6 526 | PROPRE — 6 496 « orphelins » = par construction (parcelles disparues) |
| dpe_records | 1 123 | A-04 CONNU (année 1761) ; 0 doublon numero_dpe, 0 coord hors Réunion, 0 orphelin idu |

## Référentiels communaux
| Table | Lignes | Verdict |
|---|---|---|
| communes_referentiel | 24 | PROPRE (les 24 INSEE 97401-97424) |
| mairies | 24 | A-21 (Saint-Denis sans email) ; 0 email invalide, 0 tél vide |
| commune_contexte_cache | 24 | PROPRE (recalculé du 18/10 — le run du soir l'a rempli, comme attendu) |
| rpls / sru / enaf / insee_logement / rei / zonage_abc / population / fiscal / mvt / grid / rp_logement | 24 chacune | PROPRE (24/24 partout) |
| plu_reglement_extrait | 3 258 | PROPRE (0 page ≤0, 0 verbatim vide, 0 doublon, insee ok) |
| catnat_arretes | 426 | PROPRE (0 date future, 0 fin<début, 0 doublon) |

## Comptes / CRM / journal
| Table | Lignes | Verdict |
|---|---|---|
| comptes | 47 | A-12 (2 doublons de nom = comptes de recette dont 2 actifs) ; 0 stripe id dupliqué |
| utilisateurs | 29 | A-13 (1 actif sans hash qa-m23@labuse.test) ; 0 doublon email, 0 orphelin |
| sessions_auth | 1 | PROPRE (1 expirée, 0 orphelin) |
| mail_queue | 17 | A-14 (12 a_rejouer dry-run, 3 vers compte supprimé) |
| evenements_compte | 496 | A-15 (84/89 orphelins compte/utilisateur) |
| stripe_events | 185 | PROPRE (0 doublon event_id) |
| pipeline_entries | 227 | A-17 CONNU (38 GB-TEST) ; 0 orphelin |
| projets / projet_parcelles | 9 / 1 004 | PROPRE (0 orphelin) |
| alertes | 9 061 | PROPRE (0 orphelin compte/zone/parcelle, 0 sans cible) |
| usage_events | 16 479 | PROPRE (0 orphelin, 0 kind vide) |
| consultation_log | 9 832 | A-18 (617 idu orphelins dont idu de test) |
| share_links | 50 | PROPRE (0 orphelin idu/compte) |
| courrier_demandes / courrier_envois | 33 / 3 | PROPRE (0 orphelin ; envois tous `simule`) |
| watch_zones / watched_parcels / saved_searches | 3 / 14 / 3 | PROPRE (via contrôles orphelins alertes ; volumes triviaux) |

## Tables écartées (et pourquoi)
- **Datasets ML reconstruisibles** (`p_model_*` ×17, ~4,3 M lignes chacun ; `dryrun_cascade_results` 59 M ; `dryrun_parcel_evaluations` ; `cascade_results` 20 M ; `parcel_evaluations` ; `score_snapshot_parcelles` ; `parcel_p_score_v2` ; `p_score_v2_runs`) : intermédiaires de scoring regénérés par les arènes/runs, non servis ligne à ligne ; trop volumineux pour un Mac 8 Go et hors du « servi ». Les sorties servies (score_labuse, parcel_residuel_runs…) ont, elles, été auditées.
- **Staging cadastre** (`_cad_sm1_staging/nouvelles/geommodif/disparues`) : tables de travail du chargement, préfixe `_`.
- **Couches spatiales brutes** (`spatial_layers`, `spatial_layers_sub`, `parcel_couche_intersection{,_build,_meta}`, `ocsge_sol`, `ocsge_evolution`, `parcel_ocsge`, `parcel_cosia_couverture`, `vegetation_zonal_acc`, `qa_cosia_bati`, `rgealti_*`, `lidar_dalle_grille`, `mnt_tiles`, `ortho_tiles`, `ortho_detections`, `solar_grid`, `filosofi_carreaux_200m`, `iris_rp`, `arcep_immeubles`, `ban_plus_liens`, `rnb_rattachement_bdtopo`, `dfi_filiation`, `pm_proprietaires_millesimes`, `tuyau_*`, `via_permits_geo`, `parkings_aper`, `trafic_rn`, `lieux_dits`, `oll_*`, `azi_communes`, `anc_*`, `taxe_amenagement_*`, `zone_isochrone_cache`, `mvt_tile_cache`, `watch_zone_zonage_snap`, `surface_d_events`, `ocsge_evolution`) : réservoirs amont rejouables depuis les sources officielles ; l'angle A a contrôlé leurs produits aval (parcel_*).
- **Machinerie interne** (`registre_*`, `circuit_*`, `data_sources`, `source_veille/radar/checks/agent_rapports`, `ia_cache/ia_log/ia_ask_quota`, `event_log`, `job_runs`, `ingestion_runs/delta`, `coherence_runs`, `filtre_versions/resultats`, `entonnoir_motifs`, `matching_review_queue`, `served_run_exceptions`, `run_bascule_journal`, `export_fingerprints`, `veille_reprise`, `usage_compteurs`, `defisc_fenetres`, `module_division`, `division_or_*`, `copilote_*`, `pige_*`, `bodacc_sondages/annonces_owner/procedures`, `pm_dirigeant_gigogne`, `owner_denom_lookup`, `parcel_cadastre_remplacement`, `parcel_enrichment`, `annuaire_services`, `spatial_ref_sys` PostGIS) : journaux/caches/configuration, non servis au client ou déjà couverts par les verrous du circuit.
- **Vides (0 ligne, 30 tables)** : `watch_snapshots`, `totp_2fa`, `totp_secours`, `retours`, `radar_releves`, `prefs_carte`, `piscine_corrections`, `pige_watermark/interets_agence/captures`, `parcel_source_results`, `parcel_feedback`, `ops_incidents`, `notif_canaux`, `mobpro_commune`, `ingestion_delta`, `event_seen`, `documents_generes`, `courrier_opposition/config`, `coherence_runs`, `annonces`, `acces_gels`, `saved_filters`, `source_checks` — rien à contrôler.
- **Quasi-vides consultées sans anomalie** (comptage seul) : `api_keys` 1, `abuse_scores` 1, `bilan_ratios` 1, `commune_contacts` 1, `commune_pau` 1, `parcel_zone_plu_version` 1, `app_reglages` 2, `match_profiles` 2, `fraicheur_etat` 2, `admin_alertes` 3, `notif_prefs` 3, `cout_construction_ref` 3, `mvt_meta` 3, `suggestions` 4, `licence_mails` 4, `pige_clics` 4, `entite_acronyme` 5, `plh_epci` 5, `anc_office_eau_commune` 6, `anru_quartiers` 8, `tuyau_telepherique` 8, `programmes` 9, `bilan_params` 12, `flash_commandes` 12, `nl_query_log` 13, `veilles` 15, `questionnaire_financier` 15, `crm_columns` 16, `commune_ort` 19, `lettre_zonage_refs` 19, `pige_passes` 19, `signalements` 19, `sudocuh_procedures` 24, `score_snapshots` 11, `source_veille` 104…

## Notes de méthode / pièges
- DSN `.env` au format SQLAlchemy `postgresql+psycopg://` : retirer `+psycopg` pour psql.
- `piscines` : le « LEFT JOIN using(idu) » compte les idu NULL comme orphelins — distingués (380 = tous idu NULL, pas des références cassées).
- La validation Luhn a été jouée en SQL pur (sous-requête `generate_series`), sans fonction ni table temporaire (rôle read-only).
- Aucune requête n'a dépassé ~10 s (la plus lourde : Luhn sur sirene, 7,8 s ; orphelins satellites, 9,8 s) — aucun échantillonnage nécessaire.
- Exécution de référence du script : 68 contrôles, 0 erreur (18/10/2026).
