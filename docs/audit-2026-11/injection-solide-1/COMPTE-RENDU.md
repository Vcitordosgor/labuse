# INJECTION-SOLIDE-1 — une source mise à jour arrive partout, et l'injection ne casse jamais

**Branche** `fix/injection-solide-1` · worktree `~/Desktop/labuse-injection` · ports 9580/6780 · Opus.
**Pas de merge. Aucune écriture en prod** (lecture seule). Tous les essais sur la base locale `labuse`
(run servi `q_v20`). Les essais de casse tournent sur une table **jetable** (`zzz_injsure_test`,
créée/détruite par la fixture) et dans des **transactions annulées** — rien n'est écrit durablement.

---

## Résumé exécutif

1. **Étape 0 — carte des chemins** : les 118 sources actives (99 en vitrine + 19 internes/référentiels),
   chacune avec ses consommateurs et son mode de rafraîchissement, dans
   [`carte_des_chemins.csv`](carte_des_chemins.csv) + la carte par famille ci-dessous. **42** sources
   entrent dans le classement (recalcul de nuit requis) ; **76** sont lues directement.

2. **Propagation prouvée** (21 tests, `tests/test_injection_solide_propagation.py`, verts) : pour les
   **10 familles**, une nouvelle version fait **bouger la clé de fraîcheur des caches**
   (`fraicheur_caches.empreinte_attendue`) → tout cache qui en dépend (fiche commune, tuiles, IA) se
   régénère ; et les tuiles d'overlay se versionnent sur `spatial_layers.created_at` (injection =
   tuiles refaites). **La propagation EXISTE et est vérifiée.**

3. **Solidité — le vrai trou, et sa correction**. Constat : la doctrine « contrôles + retour arrière »
   (`autonomie.controler_injection` / `injecter_avec_rollback`) **n'avait AUCUN appelant en production**
   — `injection-nuit` lance chaque ingestion en sous-processus détaché et s'en remet, pour la sûreté,
   au banc de cohérence du **lendemain**. Entre les deux, une livraison vide / à moitié / aux colonnes
   renommées / hors Réunion pouvait remplacer la table servie. **Correction** : une primitive
   d'injection SÛRE (`labuse/ingestion/injection_sure.py`) qui câble enfin le jugement à une écriture
   **atomique** (staging + swap transactionnel sous verrou), et les **11 essais de casse**
   (`tests/test_injection_solide_casse.py`, verts) qui prouvent, sur une vraie table PostGIS : refus ou
   retour arrière à chaque panne, table servie intacte, **jamais une table à moitié remplie servie**.

4. **Tableau de bord** : colonne **« Effet »** par source + bloc **« Où en est la mise à jour ? »** en
   3 phrases. Backend + front livrés, verts (tsc 0, vitest snapshot mis à jour). Capture :
   [`preuve_tableau_de_bord_apres.json`](preuve_tableau_de_bord_apres.json).

**Dette assumée** (détaillée en §6) : l'**adoption** de la primitive par les 100 ingestions existantes
(surtout les `TRUNCATE`-en-place) est le suivant du mandat ; je livre la primitive + la preuve + le plan,
je ne réécris pas les 100 scripts dans cette session.

---

## 1. Étape 0 — La carte des chemins

### 1.1 Les quatre modes de rafraîchissement (la taxonomie, vérifiée dans le code)

| Mode | Ce que c'est | Qui s'en sert | Quand le neuf apparaît |
|---|---|---|---|
| **Lecture directe** | le consommateur lit la table à CHAQUE requête (SQL live) | fiche (géométrie, droit des sols, marché), outils (Gabarit, Faisabilité, Assemblage), fiche commune (comptes) | **dès la lecture suivante** (le lendemain matin, après l'injection de nuit) |
| **Cache (clé d'empreinte)** | valeur mémorisée, portant la clé `empreinte_attendue` (run + cascade + résiduel + **hash des millésimes+horizons sources** + sha code) | fiche commune (`commune_contexte_cache`), réponses IA (`ia_cache`) | **à la lecture suivante** : la clé ne colle plus → régénération paresseuse ; + job nuit `fiche-commune-cache` |
| **Tuiles** | donnée cuite dans les tuiles carte | carte (parcelles `mvt_parcels` ; overlays PPR/PLU/SUP… via `couches_tuyau`) | **overlays** : version = `run·max(created_at spatial_layers)·tuyau_rev` → bump à l'injection ; **parcelles** : à la bascule du run (`build-mvt`) |
| **Préparation de nuit / run** | valeur précalculée dans le run (`parcel_p_score_v2`, cascade, résiduel) par `calcul-nuit` | classement, score, cascade, capacité, exports/PDF qui lisent le run | **après le calcul de nuit + bascule** (déclencheur : une entrée a avancé) |

Références vérifiées : `fraicheur_caches.empreinte_attendue` (hash `source_millesime` **et**
`source_horizon_at`, FIX-NU3-3 L-CHN-04), `api/couches_tuyau._version` (overlays), `bascule_flux.basculer`
(purge caches + build-mvt détaché), `jobs_impl.calcul_nuit` (déclencheur
`GREATEST(last_sync_at, source_horizon_at) > dernière promotion`).

### 1.2 Carte par famille (source → tables → consommateurs → mode)

> La liste **complète des 118 sources** (consommateurs = moteurs/surfaces de `flux.MATRICE`, effet,
> mode) est dans [`carte_des_chemins.csv`](carte_des_chemins.csv). Résumé des 10 familles du mandat :

| Famille | Table(s) servie(s) | Classement ? | Consommateurs principaux | Mode |
|---|---|---|---|---|
| **PPR / aléas** | `spatial_layers (ppr, georisque_alea, icpe, cavite, sol_pollue…)`, `catnat_arretes` | **oui** (cascade) | fiche §risques, carte (overlays), classement, PDF, Copilote, fiche commune | cascade→run ; carte=tuiles tuyau ; fiche commune=lecture directe |
| **PLU / urbanisme** | `spatial_layers (plu_gpu_zone, prescriptions)`, `plu_reglement_extrait` | **oui** (cascade + zone_servie) | fiche urbanisme/droit des sols, outils (Faisa/Gabarit/PLU/Étude zone), carte, PDF, fiche commune | zone=lecture directe ; cascade→run ; carte=tuiles tuyau |
| **DVF / marché** | `dvf_mutations_parcelle`, `dvf_secteur_medianes`, `dvf_prix_sortie_neuf` | **oui** (signaux cascade + features) | fiche marché, fiche commune prix, outils (Estimer/Comparer/Radar), PDF, Copilote | médiane=lecture directe ; signaux cascade→run |
| **cadastre** | `parcels`, `parcel_geometrie`, `parcelle_personne_morale` | **oui** (surface/zone) | fiche entête/le bien, carte (contours `mvt_parcels`), tous outils, PDF, fiche commune, John | lecture directe ; carte=tuiles run |
| **propriétaires** (DGFiP PM / RNIC / dirigeants) | `parcelle_personne_morale`, `pm_dirigeants`, `rnic_*` | non (hors `sources_du_score`) | fiche propriétaire, outils (Scan patrimoine/Successions/Blocs), Copilote, fiche commune, John | lecture directe (+ `parcel_blocs` précalculé) |
| **BODACC** | `bodacc_procedures` | non | fiche propriétaire (timeline), Scan patrimoine, alertes | lecture directe + événement sur ingestion |
| **permis (SITADEL)** | `sitadel_permits`, `m10_permit_delais` | **oui** (features score_e) | fiche autour, fiche commune (vélocité/délai), outils (Permis/Radar/Communes), Copilote, PDF | lecture directe ; features→run |
| **DPE** | `dpe_records` | non | fiche le bien (`dpe_connu`), filtre bâti (Faisabilité) | lecture directe |
| **servitudes (SUP/GPU)** | `spatial_layers (sup, er, ebc, dpu, peb, sis, casias…)` | **oui** (cascade SUP) | fiche droit des sols/contraintes, carte (overlays), outils (Faisa/Gabarit), PDF, fiche commune (ZFANG/FRR) | lecture directe (intersections) ; carte=tuiles tuyau ; cascade→run |
| **réseaux (VRD/SPANC/fibre/EDF)** | `arcep_immeubles`, `parcel_amenites`, `spatial_layers (transport, tcsp, ligne_mt…)` | partiel (aménités→cascade) | fiche réseaux/fibre/autour, outils (Étude zone/Faisa/Implantation), carte, PDF, John | lecture directe (distances) ; aménités→run ; carte=tuiles tuyau |

---

## 2. Propagation prouvée (les 10 familles)

`tests/test_injection_solide_propagation.py` — **21 tests, verts**. Pour chaque famille, on simule une
nouvelle version (horizon +1 j, millésime suffixé `-TEMOIN`) **dans une transaction annulée** et on
prouve que la clé de fraîcheur bouge, donc que les caches dérivés se régénèrent.

| Famille (source témoin) | Effet | Avant (empreinte) | Après | Cache invalidé |
|---|---|---|---|---|
| PPR/aléas — *DEAL PPR* | classement | `…\|sources=HASH_A\|code=…` | `…\|sources=HASH_B\|…` | commune, tuiles, IA + recalcul requis |
| PLU — *Urbanisme PLU/GPU* | classement | idem | ≠ | commune, tuiles, IA + recalcul |
| DVF — *DVF valeurs foncières* | classement | idem | ≠ | commune, tuiles, IA + recalcul |
| cadastre — *Cadastre API Carto* | classement | idem | ≠ | commune, tuiles, IA + recalcul |
| propriétaires — *DGFiP PM* | direct | idem | ≠ | commune, IA (lecture directe, pas de recalcul) |
| BODACC — *BODACC* | direct | idem | ≠ | commune, IA (lecture directe) |
| permis — *SITADEL* | classement | idem | ≠ | commune, tuiles, IA + recalcul |
| DPE — *DPE ADEME* | direct | idem | ≠ | commune, IA (lecture directe) |
| servitudes — *SUP GPU* | classement | idem | ≠ | commune, tuiles, IA + recalcul |
| réseaux — *Fibre Arcep* | direct | idem | ≠ | commune, IA (lecture directe) |

Transverse prouvé : la version des **tuiles d'overlay** lit `max(created_at)` de `spatial_layers` et le
run courant (test `test_tuiles_overlay_se_versionnent_sur_spatial_layers`) → une injection qui insère
dans `spatial_layers` (created_at = now()) change la version servie → **tuiles reconstruites**, sans
redémarrage.

**Ce qui ne suivait pas et devient automatique** : la clé d'empreinte hache déjà `source_horizon_at` en
plus de `source_millesime` (une relivraison DVF « même millésime, horizon neuf » invalide quand même) ;
les overlays se re-versionnent sur `spatial_layers.created_at` (ceinture) **et** `tuyau_rev` (bretelles).
Aucune correction de code n'a été nécessaire sur la propagation : elle était déjà complète — ce mandat
l'a **prouvée famille par famille** (elle n'était jusqu'ici qu'affirmée).

---

## 3. Solidité — essais de casse

### 3.1 Le trou trouvé

`injection-nuit` (`jobs_impl.py:1365`) lance chaque ingestion de classe A via `lancer_ingestion_source`
(sous-processus CLI détaché) **sans jamais appeler** `controler_injection` / `injecter_avec_rollback`.
Vérifié : ces deux fonctions **n'ont aucun appelant en production** (seul un test les exerce). La doctrine
« refus / retour arrière » existait sur le papier, pas dans le flux réel. La sûreté reposait donc (a) sur
la robustesse propre de chacun des 100 scripts d'ingestion — dont beaucoup font `TRUNCATE`/`DELETE`
en place — et (b) sur le banc de cohérence du **lendemain**.

### 3.2 La correction : une primitive d'injection SÛRE

`labuse/ingestion/injection_sure.py` — `injecter_table_sure(...)` câble le jugement à l'écriture :

1. **verrou consultatif** par table (`pg_try_advisory_xact_lock`) → deux injections concurrentes : la 2ᵉ refusée ;
2. **staging** : chargement dans `<table>__inj_staging` (jamais la servie) ;
3. **contrôles** (`controler_injection` réutilisé + périmètre Réunion + doublons) : comptes non nuls,
   géométries valides, couverture 974, écart sous seuil, **hors Réunion = 0**, **doublons = 0** ;
4. **swap atomique** : `DELETE + INSERT` dans **une** transaction (pas d'`ACCESS EXCLUSIVE` : le MVCC
   sert l'ancienne version entière jusqu'au COMMIT, sans bloquer les lectures) → jamais une table à
   moitié remplie ;
5. **retour arrière** au moindre contrôle en échec **ou** exception → table servie **intacte** + verdict.

### 3.3 Les essais (`tests/test_injection_solide_casse.py` — 11 tests, verts)

| # | Essai | Attendu | Prouvé |
|---|---|---|---|
| 0 | nominal | injection servie | ✅ nouvelle version en base |
| 1 | **fichier vide** | refus, table intacte | ✅ « injection vide » + 5→5 |
| 2 | **à moitié téléchargé** | refus (écart) | ✅ « écart … » + 10→10 |
| 3 | **colonnes renommées** | retour arrière | ✅ exception → rollback + 4→4 |
| 4 | **doublons** | refus | ✅ « doublon » + 3→3 |
| 5 | **géométries invalides** | refus | ✅ « géométrie invalide » + 3→3 |
| 6 | **hors de La Réunion** | refus | ✅ « hors de La Réunion » + 3→3 |
| 7 | **coupure réseau / disque plein** | retour arrière | ✅ `ConnectionError` → rollback + 6→6 |
| 8 | **deux injections en même temps** | 2ᵉ refusée | ✅ « déjà en cours » + table intacte |
| 9 | **lecture client pendant remplacement** | jamais une table à moitié remplie | ✅ lecteur REPEATABLE READ voit 4 avant/pendant, 9 après |
| 10 | **retour arrière réel après échec** | lignes exactement restaurées, staging jetée | ✅ lignes identiques + staging absente |

Le scénario « injection pendant le calcul de nuit » est couvert par #9 (atomicité MVCC : un lecteur — le
calcul — voit une version cohérente, jamais partielle) et #8 (sérialisation des écritures).

---

## 4. Tableau de bord

### 4.1 Colonne « Effet » (onglet Sources)
Chaque source porte, serveur (`circuit_maj.effet`, posé dans `_assembler_reservoirs`), l'une des deux
phrases exactes du mandat :
- **« entre dans le classement, déclenche un nouveau calcul »** (chip mauve) — 42 sources du score/cascade ;
- **« lue directement, visible le lendemain matin »** — 76 sources.

### 4.2 « Où en est la mise à jour ? » (onglet Tableau de bord)
Trois phrases (`circuit_maj.resume_mise_a_jour`), au-dessus des 4 étapes. Exemple servi ce jour :
> 1. « Les clients sont servis en q_v20, calculé le 2026-10-21. »
> 2. « 1 source a changé depuis (Radar (pige d'annonces)), toutes lues directement → visibles sans recalcul. »
> 3. « Rien à recalculer. »

Si une source **du classement** avait changé, la phrase 2 dirait « N entre(nt) dans le classement → un
nouveau calcul est nécessaire » et la phrase 3 « Prochain calcul prévu : <heure du job calcul-nuit> ».

**Fichiers** : `src/labuse/circuit_maj.py` (pur, 7 tests), `api/dashboard.py` (`_assembler_reservoirs`
+ `_sources_changees_depuis` + câblage `admin_circuit`), `cockpit_resume.py` (`composer_cockpit`),
`frontend/.../circuit/{Sources.tsx,TableauDeBord.tsx,types.ts,style.ts}`.
**Capture** : [`preuve_tableau_de_bord_apres.json`](preuve_tableau_de_bord_apres.json).

---

## 5. Recette

| Vérification | Résultat |
|---|---|
| `circuit_maj` (pur) | **7/7** |
| essais de casse (`local`) | **11/11** |
| propagation (`local`) | **21/21** |
| cockpit/tableau/circuit (régression du câblage) | **113/113** |
| unitaires (hors base) — référence pré-mandat | **2935 passed, 50 skipped** |
| front `tsc -b` | **0 erreur** |
| front `vitest` | snapshot `Donnees` mis à jour (CSS ajouté) ; 8 suites `outils` = artefact `node_modules` symlinké (connu, hors de mon périmètre) |
| cohérence (`coherence_run.sh`) | **6/6, aucun écart** (1 €/1 m² sur les témoins) |
| banc complet (`pytest -m "not network"`, 4594 tests) | **3403 passed, 1191 skipped, 41 failed, 16 errors** — voir le diagnostic ci-dessous |

### 5.1 Diagnostic du banc complet (0 régression de cette branche)

Le banc a tourné 31 min ; **PostgreSQL (conda `labusedb`) a cessé d'accepter les connexions en
plein run** (`OperationalError: … port 5432 … Connection refused`, 73 occurrences) → cascade de
41 échecs + 16 erreurs sur stripe/alertes/témoins/cockpit/provenance. Vérifications :

- **Les tests que j'ai touchés repassent tous, DB rétablie** : `test_cockpit_lot_a/lot_d/1b` = **28/28**.
- **Rejeu de l'ensemble des 55 tests tombés** (DB saine, un seul process) : **51/55 verts** ; restent
  **4** rouges.
- **Les 4 derniers échouent À L'IDENTIQUE sur le worktree `main` vierge** (même base) :
  `test_autonomie_1_db::test_controler_run_cable_les_mesures_reelles`,
  `test_circuit_p3_lot3::test_coherence_globale_base_reelle`,
  `verrous/test_garanties::test_g7_vert_apres_sonde`,
  `verrous/test_lot1_tables::test_verrous_lot1_passent_sur_la_base_reelle`.
  → **pré-existants**, liés à l'état de la base DEV locale (ces `reel`/`local` passent sur les données
  prod-like du banc de nuit, pas sur q_v20 local). **Aucun n'est causé par cette branche**, aucun ne
  touche `circuit_maj` / mes changements dashboard.

**Conclusion recette** : tout ce que touche INJECTION-SOLIDE-1 est vert ; le rouge du banc complet est
(a) une panne d'infra (la base locale tombée sous la charge du run entier) et (b) 4 rouges pré-existants
de la base dev, identiques sur `main`. Le banc complet « 0 rouge » est à confirmer sur les données
prod-like du **banc de nuit** (doctrine COHERENCE-HOOK-1), hors de portée d'une base dev locale.

---

## 6. Reste à faire (dette assumée, honnête)

1. **Adopter `injection_sure` dans les 100 ingestions** — prioriser les `TRUNCATE`/`DELETE`-en-place
   (ban_plus, cosia, dvf_detail, dvf_marche, ocsge, rnic, etablissement_parcelle…) qui n'ont aucune
   garantie d'atomicité au niveau de l'orchestration. La primitive est prête et prouvée ; chaque
   ingestion fournit son `charger_staging`.
2. **Câbler un garde post-injection dans `injection-nuit`** : aujourd'hui l'ingestion est détachée
   (sous-processus) ; soit la faire passer par `injection_sure` en process, soit ajouter une vérification
   `controler_injection` après la fin du sous-processus (avant que la cohérence du lendemain ne soit le
   seul filet).
3. **Capture visuelle live** du tableau de bord (Playwright, ports 9580/6780) — livré ici en capture
   JSON du payload servi (le contenu est rendu serveur) ; la capture pixel reste à faire.
4. **Banc complet** (`pytest -m "not network"`, ~4400) à rejouer de bout en bout (j'ai joué les familles
   touchées + cohérence ; le banc entier n'a pas été rejoué dans la session par coût de temps).

---

## 7. Notes d'environnement

- Python : `/Users/openclaw/Desktop/labuse/.venv/bin/python` + `PYTHONPATH=src` (pas de `.venv` dans ce
  worktree ; conda `labusedb` porte PostGIS mais pas pytest).
- Front : `node_modules` symlinké depuis `labuse-main/frontend` (même commit) → 8 suites `outils`
  tombent à « 0 test » à la collecte (artefact du symlink, documenté dans les mémoires précédentes,
  sans rapport avec le code livré).
- Base locale `labuse` partagée entre worktrees : les essais de casse utilisent une table **jetable**
  dédiée et des transactions annulées — zéro impact sur les données servies.
