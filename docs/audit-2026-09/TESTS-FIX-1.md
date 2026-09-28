# TESTS-FIX-1 — les 16 tests pytest en échec sur `main`

**Branche** `fix/tests-1` (rebasée sur `main` `52f97272`). **venv** `~/Desktop/labuse/.venv`, `PYTHONPATH=src`.
**Base applicative réelle** `labuse` (tests `@local`), **base de test** `labuse_test` (par défaut) ou une
base privée `LABUSE_TEST_DATABASE_URL=labuse_tf1` pour s'isoler de la contention inter-sessions.

## Constat de départ

Suite complète jouée sur `main` (base `labuse_test`) : **16 failed, 3448 passed, 69 skipped**
(`1813 s`). Les 16 échecs couvrent 9 familles : circuit2, front-reliquats (×3), oracle, pige,
reparations1, retours11f4, retours17-permis, veille2, verrous/garanties (g1/g4/g6/g7 + lot1).

> ⚠️ **Contention inter-sessions.** Plusieurs worktrees (`labuse-sources3`, `labuse-exportsfix`)
> jouaient leur propre suite sur la base de test PARTAGÉE `labuse_test` pendant la recette. Cela a
> produit des faux rouges intermittents sur les tests `db` (deadlock / idle-in-transaction). La
> vérification finale a donc été isolée sur une base privée `labuse_tf1`.

## Tableau des 16

| # | Test | Cause | Classe | Correction | Commit |
|---|------|-------|--------|------------|--------|
| 1 | `test_pige_socle::test_aucune_requete_portail_dans_le_depot` | La garde doctrine « aucun portail dans le code » ne détectait que les commentaires MONO-ligne ; deux mentions légitimes de `leboncoin` en commentaire MULTI-lignes (docstring `html_ingest.py`, `{/* … */}` JSX `MapView.tsx`) étaient prises pour du code. | **Fragile** | Suivi de l'état de bloc (docstring `"""`, `/* */`) → ces lignes comptent comme commentaire. Garde inchangée pour le vrai danger (token sur ligne d'appel réseau ou en code hors affichage). | `b88a1f91` |
| 2 | `test_oracle_dossier::test_oracle_couvre_chaque_ligne_du_dossier` | SOURCES-FIX-1 a ajouté 3 extracteurs (`enr_exclue_parcelle`, `mesures_compensatoires_parcelle`, `scot_parcelle`) sans les déclarer à l'oracle. | **Bug de code** | Les 3 lisent le payload `/parcels` (gate `disponible`, comme DPU/PEB) → ajoutés en `ORACLE_FN`. | `2653171a` |
| 3 | `test_front_reliquats::test_r2_sortie_distincte_des_decisions` | DA-FIX-1 Lot 4 a migré « ✕ Quitter » vers `<Bouton niveau="lien">` ; le style sobre n'est plus une classe `text-txt-mut` locale. | **Périmé** | Test → vérifie `niveau="lien"` (le niveau sobre du design system). | `55882cc8` |
| 4 | `test_front_reliquats::test_m135_echelle_action` | L'interdiction des anciens libellés d'action scannait TOUT `status.ts` et heurtait `BANDE_META D = { label: 'Faible' }` — libellé LÉGITIME de la bande de constructibilité (mandat §2), autre échelle. | **Périmé** | Garde bornée au bloc `PALIER_META` (comme `test_m135_tiers_front_back_alignes`). | `55882cc8` |
| 5 | `test_front_reliquats::test_marche_fiche_porte_les_3_faits_uniques` | KELFONCIER-FIX-2 Lot I a remplacé le FactRow `data-secteur-par-type` par les Tuiles c3 (mêmes données `ms.par_type`). | **Périmé** | Test → vérifie la nouvelle forme (`par_type` + `typeTuiles` + `<Tuiles>` + 3 libellés). | `55882cc8` |
| 6 | `test_retours17_permis::test_w2_cinq_lignes_etat_avec_definitions_sur_les_lignes` | FINITIONS-2 (title sweep) a retiré l'attribut `title="… l'instruction déposée n'y figure pas"`. | **Périmé** | Test → vérifie le texte visible « pas l'instruction en cours ». | `3ef12b56` |
| 7 | `test_retours17_permis::test_w3_legende_trois_entrees_quand_permis_actif` | RETOURS-15 B1 (recette Vic 27/09, vérifié live BZ1065) a RETIRÉ la légende « Permis (par état) » de la carte ; les couleurs vivent au panneau/à la carte via `permisEtats`. | **Périmé** | Test → vérifie le partage carte (`PERMIS_ETAT_COLOR`) + panneau (`etatColor`), sans légende carto, + les 3 couleurs de la source unique. | `3ef12b56` |
| 8 | `test_retours11f4::test_f8_reseaux_quatre_blocs_sans_permis` | FICHE-FIX-4 Lot H a restructuré §Réseaux « tout en Ligne » ; le GroupLabel « Axes et nuisances » a disparu (survit en commentaire). | **Périmé** | Test → vérifie les FAITS du 4e bloc (« Axe structurant » + « Trafic »). | `3e2197c8` |
| 9 | `test_circuit2_lot5::test_traçage_des_classes_pose` | FICHE-FIX-5 Lot F a retiré les `<Trace id="alea_*_couche">` ; la provenance de l'aléa passe désormais par la note du bloc + le « i ». | **Périmé** | Test → vérifie la nouvelle provenance (`data-aleas-detail` + `a.source`/`a.millesime`). La lettre de zone garde son `<Trace>`. | `2268e91a` |
| 10 | `test_reparations1_lot2::test_graphe_exact_dans_les_deux_sens` | Graphe fin `registre/lectures.py` non tenu à jour : 1 déclaration PÉRIMÉE (zone.py↔dvf_mutations_parcelle re-pointé vers dvf_mutations par SOURCES-FIX-1) + 25 arêtes de DETTE (GABARIT/RADAR/RETOURS-13…). | **Bug de code** (maintenance) | Périmée re-pointée ; 25 arêtes instruites (3 chiffre+robinet vérifiés, 22 machinerie/écran-sans-robinet). `dette=0`, `périmées=0`. | `68402085` |
| 11 | `test_veille2_lot5::test_un_seul_mail_par_jour_trois_comptes` | Le rejeu du digest appelait `envoyer_digests` 2× dans UNE transaction non validée : le DDL `_mq_ensure` (connexion séparée) du 2ᵉ run attend le verrou `mail_queue` du 1er run non commit → `db` idle-in-transaction tué (~600 s). En prod chaque run est sa propre transaction. | **Test (transaction)** | `db.commit()` entre les deux runs (comme en prod) ; dédup mail_queue vérifiée à l'identique. | `d34345db` |
| 12 | `test_garanties::test_g1_vert_sur_la_base_reelle` | `data.geopf.fr/wmts` (passerelle de TUILES IGN, N couches par LAYER) manquait de `PASSERELLES_MUTUALISEES` alors que `/wfs` et `/wms` y sont. Les 3 « doublons » partageaient cet endpoint. | **Bug de code** | Ajout de `data.geopf.fr/wmts`. | `121540d8` |
| 13 | `test_garanties::test_g4_vert_et_vide_jamais_a_jour` | SOURCES-CORRECTION-1 a rempli le DPE (16→1123) ; il n'est plus « vide », l'assertion le hardcodait comme exemple. | **Périmé** | Généralisée à l'invariant réel : toute source mesurée vide → « pas à jour » (jamais « à jour »). | `121540d8` |
| 14 | `test_garanties::test_g6_vert_apres_raccords` | `verrou_g6` cassait sur la déclaration PÉRIMÉE zone.py↔dvf_mutations_parcelle (même cause que #10 ; la dette ne casse PAS le verrou). | **Bug de code** | Périmée re-pointée (cf. #10) → `verrou_g6` vert (0 muet, 0 périmée). | `68402085` |
| 15 | `test_garanties::test_g7_vert_apres_sonde` | La sonde d'observation (`circuit_controles`) n'avait pas tourné depuis le 24/09 (>48 h) sur la base locale — état opérationnel, pas un défaut de code/test. | **Environnement** | Passage de sonde `controle(declencheur="bouton")` rejoué sur la base réelle (précondition du test « vert_apres_sonde ») → `verrou_g7` vert. Dépend de la cadence opérationnelle (fenêtre 48 h). | *(opération, pas de commit code)* |
| 16 | `test_lot1_tables::test_verrous_lot1_passent_sur_la_base_reelle` | V1c cassait : `pige_watermark` (filigrane du digest Radar, créé au vol par `pige/digests.py`) était orpheline sans action. | **Bug de code** (curation) | Classée en `TABLES_EXPLOITATION` (état d'exploitation, comme `mail_queue`). | `121540d8` |

## Bilan par classe (sur les 16 tests)

- **Bugs de code réels : 5 tests** — oracle (#2), graphe des lectures (#10 + #14, corrigés par UN
  seul changement `registre/lectures.py`), G1 WMTS (#12), V1c `pige_watermark` (#16).
  *(4 défauts de code distincts ; #10 et #14 partagent la périmée, #10 ajoute les 25 arêtes de dette.)*
- **Tests périmés : 8** — front-reliquats ×3 (#3/#4/#5), retours17 ×2 (#6/#7), retours11f4 (#8),
  circuit2 (#9), G4 DPE rempli (#13).
- **Tests fragiles : 2** — pige commentaires multi-lignes (#1), veille2 rejeu/transaction (#11).
- **Environnement (ni code ni test) : 1** — G7 sonde à rafraîchir (#15), résolu par un passage de
  sonde opérationnel (précondition « vert_apres_sonde »).
- **Non tranchés : 0.**

5 + 8 + 2 + 1 = 16.

## Vérifications

- `tsc -b` : **0 erreur**. `vitest run` : **225 passed** (50 fichiers).
- Chaque famille vérifiée verte en isolation (voir commits).
- Suite complète finale : *(voir §Résultat final ci-dessous)*.

## Notes de méthode / vigilance

- La base de test `labuse_test` est PARTAGÉE entre worktrees ; une recette parallèle produit des
  faux rouges sur les tests `db`. Vérifier au calme ou avec `LABUSE_TEST_DATABASE_URL` privée.
- Les tests `@local` lisent la base APPLICATIVE réelle `labuse` ; leur verdict dépend de son état
  servi (G7 = sonde fraîche ≤ 48 h ; G4/G1 = catalogue des sources ; V1c = schéma réel).
