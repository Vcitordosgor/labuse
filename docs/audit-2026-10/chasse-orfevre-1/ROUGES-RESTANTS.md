# ROUGES-RESTANTS — catalogue des verrous cassés et des tests rouges « avec base »

Diagnostic du 19/10/2026 · worktree `~/Desktop/labuse-fix-orfevre` · branche `fix/logements-source-unique` (HEAD `6b032c8a`).
Lecture seule : AUCUNE correction appliquée, AUCUN commit. Chaque item dit **ce qui le fera repasser au vert**, en trois catégories :
**AUTO** (prochain run/cron le répare seul) · **GESTE** (one-shot, commande donnée) · **CODE** (vraie correction, à mandater).

## Comptes exacts

- `labuse circuit verrous -w G8` : **32 joués (22 verrous + 8 garanties) — 5 CASSÉS : V1c, V6b, V7a, G5, G7** · G8 en avertissement (non bloquant).
  ⚠ **G7 est « nouveau » par rapport aux 4 attendus** — mais purement environnemental : la sonde a tourné le 17/10 09:21 et le seuil est 48 h ; rejoué le 18/10 il était vert, rejoué le 19/10 il casse. Rien à corriger (voir détail).
- Suite pytest complète avec base (sans filtre de marqueurs) : **11 failed, 4040 passed, 82 skipped en 27 min 10** (run du 19/10, venv `~/Desktop/labuse/.venv`, `.env` DSN openclaw). Les 11 rejoués isolément : 11/11 reproduits (aucun flaky parmi eux ; `test_enrichment.py::test_reseaux_et_proprietaire_honnetes` est PASSÉ ce run).
- **Vs les 13 d'avant** : 3 des 13 sont REPASSÉS AU VERT — `test_flux.py` (famille flux), `test_circuit2_lot2.py::test_documents_commites_a_jour_du_registre` (docs committés `mixite_seuil_m2`, réparé par `e703c128` « régénérer FICHE-PARCELLE-DONNEES.md », ancêtre de HEAD) et un 3e de la famille retours16 (carte et permis passent désormais ; seul `recherche` reste rouge). **1 apparu : `test_g7_vert_apres_sonde`** — purement environnemental (la sonde date du 17/10, le seuil 48 h a été franchi dans la nuit du 18 au 19) ; ce n'est PAS un rouge de notre ressort. **AUCUN rouge nouveau imputable à fix/orfevre-1 ni à fix/logements-source-unique.**
- À noter aussi : `docs/TESTS-TOLERES.md` tolère encore 3 tests (v2a, g4, lot1) à échéance **2026-10-20 (demain)** — v2a et g4 sont REPASSÉS au vert (lignes mortes, à retirer) ; lot1 est toujours rouge : passé l'échéance, `labuse circuit suite` (et donc deploy.sh) REFUSERA.

---

## 1. Verrous cassés

| Verrou | Vérifie | Cause racine | Pour le vert |
|---|---|---|---|
| V1c | toute table du schéma est dans la carte ou orpheline LISTÉE avec action | base dev PARTAGÉE : 10 tables hors carte (staging cadastre `_cad_sm1_*` d'un worktree voisin + tables d'exploitation jamais déclarées au registre : `job_runs`, `ops_incidents`, `bilan_ratios`, `parcel_zone_plu_version`, `parcel_couche_intersection_build`, `parcel_cadastre_remplacement`) — PRÉ-EXISTANT (identique sur main) | GESTE (purge staging, accord Vic) + CODE (déclarer les 5 tables d'exploitation au registre) |
| V6b | banc de cohérence permanent + 7 témoins golden sans dérive non acceptée | **dérive réelle ATTENDUE** : q_v19 re-scoré EN ENTIER le 18/10 12:53 (433 229 lignes) après les correctifs de calcul → rangs/SDP des témoins ont bougé (sdp −1/−2 m², rangs ±150-3700) ; les golden datent de CHASSE-FIX-2 | GESTE : valider la dérive puis `labuse coherence --accepter` + commit (motif = re-run q_v19 du 18/10) |
| V7a | tuile servie == géométrie brute (objets/parties/contour/position, z10/13/16) | 47 écarts sur 180 : comptages servi<retenu (ex. batiment z10 119 085 ≠ 199 909) + Hausdorff >1 px sur lignes/petits polygones à z10 — couches rechargées sur la base dev (BD TOPO bâtiment, géorisques…) vs tuiles/retenue ; PRÉ-EXISTANT | GESTE d'abord (purge `mvt_tile_cache` + rebuild) ; si écarts persistent → CODE (verrou vs ST_AsMVTGeom à z10) — voir détail |
| G5 | chaque source affiche la date du dernier contrôle, « jamais vérifié » en rouge | données manquantes : 4 sources (Contraintes EnR Géoplateforme, SCAN 50 1950, EduGéo 1980, INPN patrinat) chargées one_shot SANS `last_sync_at` NI sonde → état « à jour » muet ; PRÉ-EXISTANT (3 créées le 26/09, INPN en juin) | GESTE : renseigner `data_sources.last_sync_at` (ou `mode_remplissage='sans_millesime'` pour les archives figées) — SQL fourni au détail |
| G7 | la sonde des robinets a tourné < 48 h | environnemental pur : pas de cron sur le Mac dev ; dernier passage 17/10 09:21, rejoué le 19/10 → > 48 h | AUTO en prod (job nocturne `coherence-robinets`) ; en dev, geste : rejouer la sonde (commande au détail) |
| G8 (avert.) | aucune source vitrine sans contrôle > 7 j | 92/99 sondes muettes depuis le 22-24/09 (agent plafonné à 0 €) — état CONNU, non bloquant par design | AUTO quand le budget agent est rouvert / sondes relancées ; rien à faire ici |

### V1c — 10 orphelines sans action proposée

- **Sortie** : `✗ V1c — 10 orpheline(s) sans action proposée (docs/CIRCUIT/TABLES-ORPHELINES.md à compléter)` : `_cad_sm1_disparues` (1 353 lignes), `_cad_sm1_geommodif` (1 501), `_cad_sm1_nouvelles` (2 919), `_cad_sm1_staging` (433 229 = copie entière de parcels), `bilan_ratios` (1), `job_runs` (1), `ops_incidents` (0), `parcel_cadastre_remplacement` (3 007), `parcel_couche_intersection_build` (110 449), `parcel_zone_plu_version` (1).
- **Vérifie** : `registre/tables.py::orphelines()` = relations du schéma − carte ; une orpheline absente de `ACTIONS_PROPOSEES` casse.
- **Cause racine** : DEUX familles, toutes deux PRÉ-EXISTANTES (le registre de main ne déclare aucune des 10 ; base dev partagée) :
  1. **Résidus de worktree voisin** : `_cad_sm1_*` ×4 + `parcel_cadastre_remplacement` = staging d'une synchro cadastre millésime (« SM1 ») d'une branche non mergée — aucune référence dans le code de cette branche.
  2. **Tables créées par le code servi mais JAMAIS déclarées à la carte** : `job_runs` (jobs.py SOLIDITE-1), `ops_incidents` (ops_alertes.py), `bilan_ratios` (models.ensure_bilan_ratios, BILAN-1), `parcel_zone_plu_version` + `parcel_couche_intersection_build` (api/tiles.py, caches de version/build). Le code de main les écrit, le registre de main les ignore → V1c casse PARTOUT où ces tables existent. (`parcel_couche_intersection_build` est en outre déjà toléré dans `docs/TESTS-TOLERES.md` : « build-intersections de Vic EN COURS », échéance 2026-10-20.)
- **Pour le vert** :
  - GESTE (famille 1, accord Vic) : purger les 5 tables de staging SM1 (`labuse tables purger`, qui déplace vers le schéma poubelle — jamais un DROP direct) OU les lister dans `ACTIONS_PROPOSEES` + `docs/CIRCUIT/TABLES-ORPHELINES.md` (« purger — staging SM1, branche X »). Avec actions proposées seulement, V1c passe de « cassé » à « à décider ».
  - CODE (famille 2) : déclarer les 5 tables d'exploitation dans `registre/tables.py::TABLES_EXPLOITATION` (même recette que `coherence_runs`/`fraicheur_etat` dans CHASSE-FIX-2/3 : « table d'exploitation active, jamais une orpheline »). Correction de curation triviale mais c'est du code — à mandater, pas pour ce diagnostic.
- **Se répare tout seul ?** NON — ni run ni cron ne touche au registre ni ne purge le staging.

### V6b — 10 dérives des 7 témoins golden du banc de cohérence

- **Sortie** (abrégée) : `✗ V6b — 10 problème(s)` : `97411000BZ1065·classe_residuel(sous_densite): True → False`, `…BZ1065·rang_score: 277170 → 276268`, `…BZ1065·sdp_residuelle_m2: 36.0 → 35.0`, `97415000EO0796·rang_score: 22970 → 23220`, `…EO0796·sdp 187→185`, `97415000AX0990·rang 3527→3674`, `97408000AO1424·rang 372107→374686`, `97402000AB1117·rang 405020→408011`, `97418000AC0198·rang 424522→426208`, `97415000CK0678·rang 157747→161445`.
- **Vérifie** : les 7 fichiers `tests/golden/coherence/<idu>.json` (gravés au commit `24be0d36` CHASSE-FIX-2) comparés à la base vivante, tolérances déclarées par champ.
- **Cause racine** : **dérive réelle et EXPLICABLE, pas un bug** — `score_labuse` q_v19 (run SERVI) a été recalculé EN ENTIER le 18/10 à 12:53 (433 229 lignes, toutes `computed_at` 18/10) après les correctifs de calcul des branches fix récentes. Les SDP bougent de 1-2 m² (clips/arrondis corrigés), le rang de TOUS les témoins glisse mécaniquement (±150 à ±3 700 sur 433 229 = dérive relative < 1 %), et BZ1065 franchit le seuil `sous_densite` (sdp 36→35). AUCUNE dérive n'excède ce qu'un re-scoring île entière explique.
- **Pour le vert** : GESTE (après validation Vic que le re-run du 18/10 est bien l'état voulu) :
  `PYTHONPATH=src python -c "from labuse.cli import app;app()" coherence --accepter`
  → réécrit les 7 témoins (`tests/golden/coherence/`), puis commit avec le motif (« re-run q_v19 du 18/10 ») — le verrou exige une acceptation EXPLICITE, c'est sa raison d'être. Vérifier avant avec `coherence --comparer` que la liste des dérives est exactement celle-ci.
- **Se répare tout seul ?** NON — c'est voulu : toute dérive doit être acceptée à la main.

### V7a — 47 écarts tuiles servies vs brute (28/60 couches fidèles)

- **Sortie** (abrégée) : `✗ V7a — 28/60 couches fidèles ; 47 écart(s) sur 180 contrôle(s)` ; ex. `alea_inondation z10 (670/573) : 15084 servi(s) ≠ 16035 retenu(s)` · `batiment z10 : 119085 ≠ 199909` · `bruit_carte z10 dim2 : Hausdorff 1094.0 m > 1 px (152.9 m)` · `casias z10 : 158 ≠ 159` · `construction_lineaire z10 dim1 : Hausdorff 1071.7 m` · + 30 autres (alea_mvt, artificialisation, ebc, er, limites_parcelles, plu_gpu_zone, ppr, safer, sup, transport_ligne, tri_zone, zonage_parcelle…).
- **Vérifie** : `circuit_tuiles.verrou_tuiles` décode la tuile MVT réellement servie par le tuyau (`couches_tuyau`, cache persistant `mvt_tile_cache` versionné run + max(created_at) de spatial_layers + `tuyau_rev`) et la compare à `geom_2975` brute, z10/13/16 — comptage, parties par dimension, Hausdorff < 1 px.
- **Cause racine** : PRÉ-EXISTANT (déjà cassé avant fix/orfevre, identique sur main). Les écarts sont massifs aux z10 (grandes emprises très denses : 200 k bâtiments dans UNE tuile) et portent le motif connu « servi < retenu » : la génération MVT (quantification extent 4096 + `ST_AsMVTGeom`) écarte les géométries sous-pixel, tandis que la « retenue » SQL compte tout ce qui intersecte l'emprise ; s'y ajoutent de possibles tuiles de cache figées sur un état antérieur de la base dev partagée (couches géorisques/bâtiment rechargées depuis). Le détail exact (cache périmé vs écart structurel z10) n'est pas tranché ici — c'est le POINT À INSTRUIRE avant toute correction.
- **Pour le vert** — dans l'ordre :
  1. GESTE de discrimination : purger le cache et rejouer — `DELETE FROM mvt_tile_cache WHERE layer <> 'parcels';` (c'est exactement ce que fait `_invalider_cache_persistant_overlays`, best-effort et sans risque) puis rejouer `circuit verrous`. Si les écarts tombent → c'était de l'eau ancienne de la base dev, terminé.
  2. Si les écarts PERSISTENT (probable au moins pour les comptages z10 sous-pixel) : vraie CORRECTION DE CODE à mandater — soit le verrou applique la même rétention que le tuyau (compter après `ST_AsMVTGeom`, comme il sait déjà « reporter le contour à z13/z16 »), soit le tuyau garantit la non-troncature à z10. Décision d'architecte, hors de ce diagnostic.
- **Se répare tout seul ?** NON (le cache se réinvalide par version, mais si la version n'a pas bougé le run du soir n'y change rien).

### G5 — 4 sources « à jour » sans AUCUNE date de contrôle

- **Sortie** : `✗ G5 — 99 en vitrine : 99 avec date… 0 « jamais vérifié »` puis 4 lignes : `Contraintes EnR près des habitations (Géoplateforme)`, `SCAN 50 historique 1950 (IGN)`, `INPN / patrinat — espaces protégés`, `EduGéo Réunion 1980 (IGN)` — chacune « aucune date de contrôle ET aucune mention “jamais” (état “à jour”) ».
- **Vérifie** : `circuit_garanties.verrou_g5` — pour chaque source vitrine, `max(source_veille.dernier_passage_at, data_sources.last_sync_at)` doit exister, OU l'état doit être parlant (« jamais vérifié » en rouge, « vide »), OU `mode_remplissage='sans_millesime'`.
- **Cause racine** : données manquantes en base, PRÉ-EXISTANT. Vérifié en SQL : les 4 ont `last_sync_at IS NULL`, aucune ligne `source_veille` avec méthode, `mode_remplissage='one_shot'`. Trois ont été créées le 26/09 (chantier couches implantation : EnR, SCAN 50, EduGéo), INPN patrinat date de juin — leurs chargeurs n'ont jamais stampé `last_sync_at`.
- **Pour le vert** : GESTE one-shot (après vérification de la date de chargement réelle de chaque couche) :
  ```sql
  UPDATE data_sources SET last_sync_at = created_at  -- ou la date réelle du chargement
   WHERE name IN ('Contraintes EnR près des habitations (Géoplateforme)',
                  'SCAN 50 historique 1950 (IGN)', 'EduGéo Réunion 1980 (IGN)',
                  'INPN / patrinat — espaces protégés') AND last_sync_at IS NULL;
  ```
  Alternative plus juste pour SCAN 50 1950 / EduGéo 1980 (archives FIGÉES par nature) : `mode_remplissage='sans_millesime'` (« à jour par construction », prévu par le verrou). + CODE léger à mandater : que les chargeurs one_shot stampent `last_sync_at` à l'ingestion pour que ça ne revienne pas.
- **Se répare tout seul ?** NON (aucune sonde configurée sur ces 4 ; l'agent de sources est plafonné à 0 €).

### G7 — sonde des robinets > 48 h (NOUVEAU vs liste attendue, purement environnemental)

- **Sortie** : `✗ G7 — dernier passage sonde 17/10 09:21 ; 0 fuite(s) ouverte(s)` · `la sonde n'a pas tourné depuis 2 j — au-delà de 48 h`.
- **Vérifie** : la sonde `coherence-robinets` (chiffres ≥ 2 robinets comparés sur les témoins) a tourné il y a < 48 h ET chaque écart ouvert est une ligne rouge complète. **0 fuite ouverte** — seul l'ÂGE casse.
- **Cause racine** : environnementale pure. Pas de cron sur le Mac dev ; la sonde a tourné le 17/10 (vraisemblablement lancée à la main ou par un passage verrous d'un worktree voisin). Les rejeux « 4 CASSÉS » du 17-18/10 étaient < 48 h ; le rejeu du 19/10 franchit le seuil. Ce n'est PAS une 5e casse de notre ressort.
- **Pour le vert** : AUTO en prod (job nocturne `coherence-robinets` du registre). En dev, geste : rejouer la sonde —
  `PYTHONPATH=src python -c "from labuse.db import session_scope; from labuse.sonde_circuit import controle; import json;\nwith session_scope() as s: print(controle(s, declencheur='manuel'))"`
  (ou le bouton « Vérifier que tout coule » de la page Circuit, API locale).

### G8 (avertissement, pour mémoire)

- 92/99 sources vitrine sans contrôle récent : sondes muettes depuis le 22-24/09, agent de sources plafonné à 0 €. CONNU, affiché en avertissement non bloquant par design (« signalé, n'empêche pas le déploiement »). Pour le vert : rouvrir le budget agent / relancer les sondes — décision produit, pas un bug.

---

## 2. Tests rouges « avec base » — les 11 du run du 19/10

| # | Test | Échec (1 ligne) | Cause racine | Pour le vert |
|---|---|---|---|---|
| 1 | `test_golden_run_servi.py::test_golden_grave_sur_le_run_servi` | `GoldenPerimeError : la référence cite run_v2_servi='q_v11_m137' mais le run servi est 'q_v19'` | golden M6 jamais regravé depuis la bascule q_v11→…→q_v19 (c'est EXACTEMENT ce que ce garde-fou doit attraper) | GESTE : régénérer le golden (`qa/golden_regen.py`, API up) + commit |
| 2 | `test_served_cascade.py::test_default_run_est_le_run_servi_pas_q_v8` | la ligne semée sous `Q_A_RUN_LABEL` n'est pas rendue (aucun détail « servi ») | le run servi a des étiquettes SCINDÉES : scoring `q_v19`, cascade `q_v18_sources` (manifeste) ; le test sème sous `Q_A_RUN_LABEL` et suppose cascade == scoring | CODE (test) : semer sous `runs.cascade()` ; + GESTE à signaler (manifeste périmé, voir détail) |
| 3 | `test_simulplu.py::test_simulplu_ne_leve_pas_et_dit_son_total` | `n_total == 0` au lieu de 2 | même cause que #2 (simulplu lit `runs.cascade()` = `q_v18_sources`, seeds sous `q_v19`) | idem #2 |
| 4 | `test_simulplu.py::test_simulplu_dit_la_troncature_quand_plafonnee` | `n_total == 0` au lieu de 2 | idem #2/#3 | idem #2 |
| 5 | `test_chasse_invariants_fix1.py::test_lot3_cascade_exclue_sort_du_classement_avec_raison` | `assert 'B' == 'A'` — un témoin bande A (run q_v18) recombiné donne B | test figé sur `run_label='q_v18'` (run PÉRIMÉ) ; le code de calcul a bougé depuis (orfèvre-1 : logements/ratios) → la frontière A/B n'est plus celle du 11/10 | CODE (test) : repointer q_v18 → `Q_A_RUN_LABEL` ; (devient skip tout seul si q_v18 est purgé par la rétention) |
| 6 | `test_score_e.py::test_build_ecartee_exclue_et_non_estimable` | parcelle A attendue estimable → `estimable=False, marge NULL` | correctif VEFA-1 (voulu) : `neuf_vefa_commune` ne compte que les lots `type_local` HABITATION ; le seed du test insère des VEFA SANS `type_local` → médiane neuf live vide → non estimable | CODE (test) : seed avec `type_local='Appartement'` dans `_seed_medianes` |
| 7 | `test_zone_recette.py::test_flash_par_adresse_trouve_la_parcelle` | `'Votre rapport Flash' not in r.text` | texte /flash RÉÉCRIT par Vic (CORRECTIFS-1 A5, commit `0507cd5a`) : « Votre rapport Flash » n'existe plus dans src (écran = « Est-ce le bon terrain ? ») — assertion périmée | CODE (test) : asserter le libellé actuel |
| 8 | `test_retours16_recherche.py::test_front_un_seul_composant_plus_d_autocompletion_maison` | `'Aucune correspondance pour' not in AddressAutocomplete.tsx` | FIX-1 recette (A-01-1, commit `b55481e4`, voulu) a remplacé le zéro-résultat par « Aucun résultat pour « … » — formats acceptés : … » — assertion périmée | CODE (test) : asserter « Aucun résultat pour » |
| 9 | `tests/verrous/test_garanties.py::test_g5_vert_sur_la_base_reelle` | `verdict 'casse'` — les 4 sources sans date de contrôle | = verrou G5 (section 1) | = G5 : GESTE SQL `last_sync_at` / `sans_millesime` |
| 10 | `tests/verrous/test_garanties.py::test_g7_vert_apres_sonde` | `verdict 'casse'` — « la sonde n'a pas tourné depuis 2 j » | = verrou G7 (section 1) — NOUVEAU vs les 13, environnemental pur (seuil 48 h franchi dans la nuit) | AUTO (cron prod) / GESTE dev : rejouer la sonde |
| 11 | `tests/verrous/test_lot1_tables.py::test_verrous_lot1_passent_sur_la_base_reelle` | `jouer_tous` sur la base réelle → V1c + V6b + V7a cassés | miroir pytest du circuit : vert quand V1c, V6b ET V7a le sont (les « à décider » sont admis) | = section 1 (V1c geste+code, V6b geste d'acceptation, V7a geste puis arbitrage) |

### Détail par item

**1 — golden M6 périmé** (`@pytest.mark.reel`, lecture seule, aucune DB)
`check_golden_regenere(Q_A_RUN_LABEL)` lit `reports/m6-audit/golden/golden-parcelles.json` (meta `run_v2_servi='q_v11_m137'`, gravé le 29/08) et `config/served_run.txt` (= `q_v19`). C'est le garde-fou posé par GOLDEN-REGEN LOT 2 précisément pour rougir tant que la bascule n'a pas regravé le golden — il fait son travail. **Pour le vert (GESTE, dans le même geste qu'une revue Vic)** : API locale up puis `qa/golden_regen.py` (lit la référence courante — 119 parcelles dont 84 ancres J3 —, re-dumpe sur CES ids, préserve les ancres ; pré-requis `LABUSE_API_BASE` + `LABUSE_SERVED_RUN`) ; le diff git de la référence EST la revue ; commit. NE PAS utiliser `golden_check.py --dump` nu (perd les ancres J3 — le message d'erreur le rappelle). Ne se répare PAS tout seul.

**2/3/4 — served_cascade + simulplu ×2 : étiquettes de run scindées**
`config/served_manifest.json` (bascule du 17/10 05:20) : `scoring_run=q_v19`, **`cascade_run=q_v18_sources`**. `served_cascade_lines` et `moteurs.simulplu` lisent le run de cascade via `runs.cascade()` (COHÉRENCE-RUN-1 — correct) ; les tests sèment leurs lignes `dryrun_cascade_results` sous `Q_A_RUN_LABEL` (= `q_v19`) en supposant cascade == scoring. Depuis que les runs servis scindent les étiquettes (`*_sources`), cette hypothèse est fausse EN PERMANENCE : même une re-bascule pointant `q_v19_sources` laisserait les tests rouges (`q_v19` ≠ `q_v19_sources`).
**Pour le vert : CODE (tests)** — semer sous `runs.cascade()` (1 ligne par test). **Constat à signaler au passage (hors tests)** : la base porte `q_v19_sources` CALCULÉE le 18/10 10:12 (21,1 M lignes) alors que le manifeste sert encore la cascade `q_v18_sources` du 11/10 — le scoring q_v19 re-calculé le 18/10 12:53 est donc servi avec une cascade d'étage 0 plus vieille que celle dont il est probablement issu. Un geste de re-bascule (page Circuit / `labuse golden promote`) re-épinglerait la cascade fraîche — décision Vic, PAS faite ici.

**5 — chasse_invariants_fix1 lot 3 : témoins figés sur q_v18**
Le test tire ses témoins de `score_labuse WHERE run_label='q_v18'` (codé en dur — même famille que ORF-40 « labels périmés ») puis RE-combine avec le code courant : un témoin bande A du 11/10 sort aujourd'hui en B (le calcul a bougé depuis : retrait logements ancien moteur, ratios 0,46/0,40 au registre, logements-source-unique). L'assertion « une A non exclue reste A » compare donc DEUX époques du moteur. **Pour le vert : CODE (test)** — repointer sur `Q_A_RUN_LABEL` (q_v19, calculé le 18/10 avec le code courant) ; à défaut, le test deviendra `skip` de lui-même quand q_v18 sera purgé par la rétention des runs.

**6 — score_e : seed VEFA sans `type_local`**
`build_score_e` calcule le neuf live par `neuf_vefa_commune`, dont VEFA-1 (correctif VOULU, docs/audit-2026-10/VEFA-1) a changé le dénominateur : `sum(surface_reelle_bati) FILTER (WHERE type_local IN (VEFA_LOTS_HABITATION))`. Le seed du test (`_seed_medianes`) insère 8 mutations VEFA **sans `type_local`** → `bati=0` → `n=0 < seuil 8` → aucune médiane neuf → parcelle A « non estimable ». **Pour le vert : CODE (test)** — ajouter `type_local='Appartement'` au INSERT du seed.

**7 — zone_recette /flash par adresse : libellé réécrit**
La résolution adresse→parcelle fonctionne ; c'est l'ÉCRAN qui a changé : CORRECTIFS-1 A5 (`0507cd5a`, « texte /flash de Vic appliqué aux deux écrans ») a supprimé « Votre rapport Flash » du code (grep src = 0) ; l'écran de confirmation s'intitule « Est-ce le bon terrain ? ». **Pour le vert : CODE (test)** — asserter le libellé actuel (ex. « Est-ce le bon terrain ? » + « Saint-André »).

**8 — retours16 recherche : zéro-résultat reformulé**
`AddressAutocomplete.tsx` dit désormais « Aucun résultat pour « {texte} » — formats acceptés : {formats}. » (FIX-1 recette A-01-1, commit `b55481e4` — poussé hook vert, dans l'historique de cette branche). Le test exige l'ancien « Aucune correspondance pour ». Tout le reste du test passe. **Pour le vert : CODE (test)** — mettre à jour l'assertion.

**9/10/11 — miroirs pytest des verrous** : mêmes causes et mêmes remèdes que la section 1 (G5 → geste SQL ; G7 → auto/cron ou rejouer la sonde ; lot1 → V1c + V6b + V7a). `test_lot1` admet les « à décider » : compléter `ACTIONS_PROPOSEES` pour les 10 orphelines suffirait pour CE test même sans purge, mais il restera rouge tant que V6b et V7a le sont.

---

## 3. Synthèse — qui répare quoi

- **Se répare TOUT SEUL** : G7 (sonde nocturne en prod ; en dev un passage de sonde suffit).
- **GESTES one-shot (à faire valider par Vic)** :
  1. V6b : `labuse coherence --comparer` (contrôle) puis `--accepter` + commit (motif : re-run q_v19 du 18/10) ;
  2. golden M6 : `qa/golden_regen.py` + commit (test #1) ;
  3. G5 : SQL `last_sync_at` (ou `sans_millesime`) sur les 4 sources ;
  4. V1c : purge (`labuse tables purger`) des 5 tables de staging SM1 du worktree voisin ;
  5. V7a : purge `mvt_tile_cache` (hors parcels) + rejeu pour discriminer cache/structurel ;
  6. (constat) re-bascule pour épingler `q_v19_sources` — décision Vic.
- **CODE à mandater (tous des tests périmés par des correctifs VOULUS — aucun bug produit)** : tests #2/3/4 (semer sous `runs.cascade()`), #5 (q_v18 → run servi), #6 (`type_local` au seed), #7 et #8 (libellés actuels) ; registre : déclarer les 5 tables d'exploitation (V1c) ; et l'issue de la discrimination V7a si le cache n'explique pas tout.
- **Hygiène** : retirer de `docs/TESTS-TOLERES.md` les 2 lignes mortes (v2a, g4 repassés verts) et traiter la 3e (lot1) avant son échéance du 2026-10-20.

