# TESTS-1 — la suite de tests redit quelque chose

**Branche** : `fix/tests-1` depuis `main` (`6415ac5d`, SOURCES-3 mergé). **Worktree** : `~/Desktop/labuse-tests`.
**Étape 0** : arbre propre, `.env` en place, `labuse circuit verrous` **24/24 verts** avant tout geste.

## Lot 0 — l'inventaire

Suite complète jouée sur `main` (14/09) : **36 échecs**, 3 032 passés, 55 skippés, 2 min 48.
Le mandat en annonçait 38 : deux ont été résorbés entre-temps par le merge SOURCES-3 (le compte
bouge à chaque merge — c'est précisément la dérive que ce mandat arrête).

Causes : **A** le test a raison, le code est cassé · **B** le code a changé exprès, le test dit
l'ancien contrat · **C** l'objet du test n'existe plus · **D** l'environnement de test manque.

### Le compte par cause

| Cause | Nombre | Lecture |
|---|---|---|
| **A — vrais bugs / vraies dettes, jamais vus** | **9** | dont 2 incohérences servies aux clients (Résumé Circuit muet, tuiles carte sur un autre run que la fiche) |
| **B — contrats changés exprès, tests jamais mis à jour** | **15** | 6 mandats différents ont changé un contrat sans repasser sur son test |
| **C — objet disparu** | **0** | aucune suppression légitime : rien de ce que testent les 36 n'a disparu |
| **D — environnement de test incomplet** | **12** | 2 causes seulement : 2 tables d'ingestion absentes de `labuse_test`, et les FK `comptes` de COMPTE-2 |

### Le tableau des 36

| # | fichier::test | Message | Cassé par (depuis quand) | Cause |
|---|---|---|---|---|
| 1 | test_api.py::test_m136_exports_ne_crashent_pas | `relation "commune_zonage_abc" does not exist` | `9753b745` RECETTE-4 lot 1 (09/09) : la fiche lit le zonage A/B/C ; la table (créée par ingestion, hors ORM) n'a jamais été ajoutée à la base de test | D |
| 2 | test_audit_stripe.py::test_flash_recuperable_apres_onglet_ferme | idem (via fiche du Flash) | idem | D |
| 3 | test_audit_stripe.py::test_flash_token_ne_donne_que_son_pdf | idem | idem | D |
| 4 | test_audit_stripe.py::test_flash_lien_expire_apres_30j | idem | idem | D |
| 5 | test_audit_stripe.py::test_reprise_flash_apres_interruption | idem | idem | D |
| 6 | test_dossier.py::test_pdf_genere_avec_mention | idem (+ `pc_caducs` absente, même famille) | idem | D |
| 7 | test_verdict_effectif.py::test_fiche_expose_score_v2_et_etage0 | idem | idem | D |
| 8 | test_verdict_effectif.py::test_etage0_du_run_servi_prime | idem | idem | D |
| 9 | test_verdict_effectif.py::test_repli_legacy_sans_ligne_v2 | idem | idem | D |
| 10 | test_courrier_boucle.py::test_boucle_piste_courrier_reponse | FK `fk_pipeline_entries_compte` : compte_id 4242 absent de `comptes` | `72d5343b` COMPTE-2 (07/09) : les FK gravées ; le test insère un compte_id sans créer le compte | D |
| 11 | test_courrier_boucle.py::test_backfill_rattache_par_idu_compte_univoque | idem (4243) | idem | D |
| 12 | test_dashboard.py::test_ia_log_attribue_au_compte | FK `fk_ia_log_compte` : 4242 absent | idem | D |
| 13 | test_api.py::test_fiche_verdict_traduit_le_tier_servi | `'À suivre' == 'Priorité'` | `c87e9919` REPARATIONS-1 lot 2b (13/09) : `PRIORITE_SERVIE=False` — Priorité n'est plus servie (décision métier, ~0,52× marche) | B |
| 14 | test_assistant.py::test_rules_summary_vraie_opportunite | `'Priorité' in md` faux | idem | B |
| 15 | test_resume.py::test_resume_brulante | `'À suivre' == 'Priorité'` | idem | B |
| 16 | test_resume.py::test_resume_brulante_badge_division | idem | idem | B |
| 17 | test_verdict_servi.py::test_servable_traduit_le_tier | idem | idem | B |
| 18 | test_registre.py::test_modes_cadences_declares | `121 == 116` | `0cadf3d6` SOURCES-2 lot 3 (13/09) : +5 sources (endiguement, hypsométrie, BAN PLUS, RNB, OCS GE) ; le commentaire-chronique du test s'arrête à SOURCES-1 | B |
| 19 | test_circuit2_lot1.py::test_couches_et_fonds_tous_declares | `35 == 33` | SOURCES-2 : `couche_artificialisation` (OCS GE) + `couche_batiments_3d` (LiDAR) déclarées, compte du test figé | B |
| 20 | test_sources1_lot4.py::test_catalogue_lot4 | `'partenariat_requis' == 'a_faire'` | `3221ba2a` SOURCES-3 lot 0 (14/09) : arbitrage Vic — le SAR passe en partenariat_requis | B |
| 21 | test_sources1_lot4.py::test_echantillon_producteur_dvf_rempli | `'2026-09-13' == '2026-09-07'` | `3221ba2a` : contrôle producteur DVF rafraîchi ; le test fige une date appelée à avancer | B |
| 22 | test_recette6.py::test_e5_un_seul_usage_servi_les_autres_grises_avec_raison | `2 == 1` usages servis | `8f84a994` RECETTE-8 W13bis (09/09) : le parcours « Revente en l'état » est bâti et servi | B |
| 23 | test_recette11.py::test_a6_aucun_verdict_de_surelevation | `'sous la hauteur réglementaire'` absent | `c5dc44e1` RECETTE-12 D3 (13/09) : format Q7 une ligne (« Égout X mesuré (règle Y, marge Z) · … ») — la phrase testée a été retirée exprès | B |
| 24 | test_recette11.py::test_a3_date_de_survol_avec_la_mesure | `'LiDAR HD — IGN / Géoplateforme'` absent du §3 | `c5dc44e1` RECETTE-12 D3 : arbitrage écrit dans le code — source citée au §10 SEULEMENT, la date reste sur la ligne de mesure | B |
| 25 | test_recette4.py::test_fiscalite_locale_dit_le_taux_et_la_zone_sources | `'zone A'` absent | `61f420aa` RECETTE-9 T4 : le littéral « zone » retiré (redondant avec la clé « Zone d'investissement (A/B/C) ») | B |
| 26 | test_front_reliquats.py::test_r5_etudier_deux_marges_chacune_dit_son_referentiel | `'la charge calibrée'` absent du .tsx | refonte bascule unique (RETOURS-12 O2 `9c9c27cb` puis RECETTE-1 `0848ebf9`) : le référentiel est dit par « Hypothèses calibrées LABUSE » / « Selon vos hypothèses » | B |
| 27 | test_dashboard2_cloture.py::test_rail_horloge_et_verrous_presents | `17 in (None, 16)` | `ff82b2a4` SOURCES-3 lot 4 (13/09) : verrou V4e ajouté, 16 → 17 verrous ; le test fige le compte | B |
| 28 | test_circuit_p3_lot2.py::test_reservoirs_a_regarder_sans_doublon | compteur « à regarder » 101 ≠ 94 réservoirs des lignes | état **« INVISIBLE — branchée mais vide »** (rouge, CIRCUIT-6/G2) sans AUCUNE ligne au Résumé : 7 réservoirs rouges muets — un état rouge silencieux, l'exact contraire de la doctrine | **A** |
| 29 | test_circuit_p3_lot3.py::test_coherence_globale_base_reelle | réservoir 37 au Circuit, absent du Résumé | même racine : 37 = « DPE ADEME (logements existants) », l'unique source INVISIBLE de la base réelle (G2) | **A** |
| 30 | test_circuit2_lot16.py::test_chaque_passe_plat_declare_sa_table | `rtaa_exigences : passe_plat sans table déclarée` | SOURCES-3 : la donnée `rtaa_exigences` entrée au registre sans dire ce qu'elle lit (`config/rtaa_dom.yaml`) | **A** |
| 31 | test_circuit2_lot2.py::test_documents_commites_a_jour_du_registre | `rnb_batiments_liste` absent du doc committé | SOURCES-2 lot 3 : données RNB/OCS GE ajoutées au registre, `docs/CIRCUIT/FICHE-PARCELLE-DONNEES.md` jamais régénéré | **A** |
| 32 | test_circuit4_lot1.py::test_toute_donnee_moteur_a_sa_fiche | 5 données sans fiche de règle | SOURCES-2/3 : `ban_plus_adresses_bati`, `part_artificialisee_pct`, `rnb_batiments_liste`, `usage_sol_dominant`, `zan_evolution_commune` servies sans fiche | **A** |
| 33 | test_circuit4_lot1.py::test_toute_fonction_moteurs_pkg_couverte | `commune.zan_ocsge_commune` sans fiche | même dette (la fiche `zan_evolution_commune` couvre la fonction) | **A** |
| 34 | test_sentinelle.py::test_seed_et_raisons_couvrent_les_64_sources_par_nom_exact | 6 raisons pour des noms hors catalogue | `99f3d672` CIRCUIT-6 lot 4 (13/09) : raisons écrites pour 6 sources **réelles en base** (121) mais absentes de la liste `SOURCES` du code (112) — le catalogue code a dérivé de la base | **A** |
| 35 | test_hypotheses_source_unique.py::test_aucune_constante_de_cout_hors_source | `MAX_COUT_CONSTRUCTION_M2 = 8000` hors source | RECETTE-6 E2 (09/09) : la borne de vraisemblance posée en littéral dans `financier_bilan.py`, hors de la source unique que le garde protège (bug 2100) | **A** |
| 36 | test_run_serving_coherence.py::test_tuiles_mvt_materialisees_sur_le_run_servi | tuiles `q_v14` ≠ run servi `q_v11_m137` | COHERENCE-RUN-1 a matérialisé les tuiles q_v14 (08/09) en anticipant une bascule ; BASCULE-1 (étape 0) a ramené le servi à q_v11_m137 sans re-matérialiser — **la carte montre un autre run que la fiche**, chez les clients, depuis le 08/09 | **A** |

### Ce que le mot « préexistant » cachait

- **2 incohérences servies aux clients** : la carte (tuiles q_v14) contredit la fiche (q_v11_m137)
  depuis le 08/09 ; et 7 réservoirs ROUGES (« INVISIBLE — branchée mais vide ») sans aucune ligne
  au Résumé du Circuit — un rouge silencieux.
- **1 dérive de doctrine** : une borne « coût » en littéral hors source unique, la re-création du
  motif du bug 2100 que ce garde existe pour empêcher.
- **1 dérive de catalogue** : 9 sources vivent en base (121) sans entrée dans la liste `SOURCES`
  du code (112) — dont les 6 que les raisons G4 nomment. Les 6 nommées sont réparées ici ; les
  3 restantes (« EDF SEI Réunion — open data », « Registre national des installations (ODRÉ) »,
  « ZNIEFF (INPN / Région) ») sont signalées, aucune assertion ne les couvre encore.
- **5 fiches de règle + 1 doc + 1 déclaration de table** en retard sur SOURCES-2/3.
- **15 tests jamais repassés** après des changements de contrat pourtant assumés (6 mandats).
- **12 échecs d'environnement** ramenés à 2 causes réparables (2 tables data-gap, FK comptes).

*(Lots 1 à 3 : voir plus bas — complétés au fil du mandat.)*
