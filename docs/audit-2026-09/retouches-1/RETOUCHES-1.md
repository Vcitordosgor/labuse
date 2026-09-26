# RETOUCHES-1 — les retouches notées pendant les audits de septembre

Branche `fix/retouches-1` (worktree `~/Desktop/labuse-retouches`, base main `74839455`, ports
8525/5725, non mergée). Un commit par point. DONNEES-FIX-1 vérifié mergé (`bcc32144`) — condition
d'entrée OK. Venv `~/Desktop/labuse/.venv`, `PYTHONPATH=src` (l'éditable pointe le worktree principal).

## État d'avancement

| Lot | Point | État |
|---|---|---|
| A | A.1 — 0 échec pytest | ✅ fait (`344fab8c`, `0b157d0a`, `d1420362`, `a5a6bd8b`) — voir §Vérification pour les 6 pré-existants hors périmètre |
| A | A.2 — verrou V1c | ✅ fait (commit `f9a02b18`) |
| A | A.3 — captures S2 déplacées | ✅ fait (commit `4d7621ed`) |
| B | B.6 — garde-fou commune 400 | ✅ fait (commit `61fe199e`) |
| B | B.7 — tuile terrain nu / seuil | ✅ sans objet (RECETTE-6, voir §B.7) |
| B | B.4 — Assemblage sur l'union | ⏳ à faire — plan détaillé §B.4 |
| B | B.5 — médianes DVF unifiées | ⏳ à faire — plan détaillé §B.5 |
| B | B.8 — badge Estimé au bilan | ⏳ à faire — plan détaillé §B.8 |
| C | C.9–14 — 6 blocs fiche (FICHE-3) | ⏳ à faire — plan détaillé §C |
| D | D.15 — Gabarit ER/EBC/SUP | ⏳ à faire — plan détaillé §D.15 |
| D | D.16 — sources `live` | ⏳ à faire — plan détaillé §D.16 |
| D | D.17 — RGE ALTI VPS (note prod) | note, pas d'action |

---

## Étape 0 — référence pytest

La suite complète **se bloquait** sur trois fichiers de digest e-mail (interblocage
`mailfile.ensure_tables`, corrigé au lot A.1 — voir ligne `mailfile`). Le compte de référence des
échecs (avant correctifs) est établi par **analyse ciblée test par test** plutôt que par un run
complet tronqué :

- Non-`local` : **8 échecs** — `test_g2`, `test_g5`, `test_g6` (garanties), `test_vocabulaire_client_gravé`,
  `test_module_unique_aucune_autre_lecture` (plu_destinations), `test_aucune_instanciation_directe_hypotheses`,
  `test_agents_sources_dimanche`, `test_duediligence_ne_lit_plus_la_cascade` (servitudes).
- `@local` (base réelle) : `test_verrous_lot1_passent_sur_la_base_reelle` (V1c orphelines) — corrigé au lot A.2.
- Interblocages : `test_veille2_lot5`, `test_veille_fix1`, `test_veille_notifs_fixes` — corrigés au lot A.1 (mailfile).

Compte documenté des runs précédents (mémoire projet) : **~19 F pré-existants** (les variantes
`@local`/`@db` passent sur la base réelle ; la différence tient aux gardes registre cassées par les
merges de `main`). **Après correctifs** : voir §Vérification.

---

## Lot A — la suite au vert, les verrous complets

### A.1 — les échecs pré-existants : cause · geste (ligne par ligne)

| Test | Cause | périmé / bug | Geste |
|---|---|---|---|
| `test_garanties::test_g2_etat_invisible_sort_rouge` | `etat_reservoir` refondu (CIRCUIT-P4/P6) en vocabulaire à 5 mots ; « INVISIBLE » ne colore plus la pastille (porté par la page de détail). Le test tenait l'ancien `("rouge","INVISIBLE …")`. | **périmé** | test réécrit (`test_g2_invisible_hors_pastille`) : l'état est le même avec/sans le drapeau ; garantie tenue par `verrou_g2` (@local) |
| `test_garanties::test_g5_jamais_verifie_est_rouge` | Dérive de libellé : test attendait `("rouge","jamais vérifié")` ; le code sert `("gris","jamais vérifiée")` (trou de vérif, pas action). | **périmé** | test réécrit (`test_g5_jamais_verifie_est_gris`) sur la valeur servie |
| `test_garanties::test_g6_vert_apres_raccords` | `verrou_g6` casse : (a) `lieux_dits`/`bd_nyme` (GEOPF-3) lue par l'app mais MUETTE ; (b) lecture fine `catnat_arretes` déclarée sur `api/modules.py` qui ne la lit plus. | **vrai bug** | chiffre `secteur_lieu_dit` (réservoir `bd_nyme`) + reciblage lecture catnat → `api/fiche_commune.py` |
| `test_scoring6::test_vocabulaire_client_gravé` | Décision Vic (ANALYSE-2) : bande `"0"` = « Non retenue » (ex « Sans potentiel constructible »). | **périmé** | test mis à jour |
| `test_plu_destinations::test_module_unique_aucune_autre_lecture` | Garde `grep "plu_destinations"` trop large : 4 fichiers MENTIONNENT la chaîne (commentaire, libellé `PLU_PROVIDER`, chemin `git log`) sans LIRE les YAML. | **périmé** | test affiné : ne compte que les vraies lectures (co-occurrence `open`/`glob`/`safe_load`…) |
| `test_hypotheses_source_unique::test_aucune_instanciation_directe_hypotheses` | `prospection.py:72` instancie `Hypotheses()` en direct hors `engine.py`. | **vrai bug** | `Hypotheses.charger()` (source unique) |
| `test_cron1_registre::test_agents_sources_dimanche` | Dérive de cadence : job `agents-sources` passé à « 1 semaine sur 2 » (CIRCUIT-P7) → `cadence="tous les 15 j (dim)"`. | **périmé** | test mis à jour |
| `test_servitudes::test_duediligence_ne_lit_plus_la_cascade` | Garde `"dryrun_cascade_results" not in src` piégé par une MENTION dans la docstring de `duediligence`. | **périmé** | test affiné : docstring retirée avant le contrôle (corps exécutable strict) |
| `test_lot1_tables::test_verrous_lot1_passent_sur_la_base_reelle` (`@local`) | `taxe_amenagement_secteur` + `mvt_tile_cache` orphelines (schéma ∖ carte) → V1c casse. | **vrai bug** | **lot A.2** (inscription à la carte) |
| `test_veille2_lot5` / `_fix1` / `_notifs` (interblocage) | `mailfile.ensure_tables` : `ALTER … ADD COLUMN IF NOT EXISTS avert` prend un ACCESS EXCLUSIVE même en no-op, sur une connexion séparée → interblocage contre la session non committée (2ᵉ `envoyer_digests`). | **vrai bug** | ALTER derrière une garde d'existence de colonne (pas de verrou en régime établi) |

Suite A.1 (`0b157d0a`) : le chiffre `secteur_lieu_dit` n'était rattaché à aucun robinet → **V5b**
cassait (« servie par aucun robinet ») ; rattaché au robinet `fiche_parcelle_entete` (mono-robinet →
V5c inchangé).

**Vérification A.1** : les 8 tests non-`local` + les 3 fichiers de digest → **108 passed, 0 failed**
(run consolidé, `-m "not local"`).

### A.2 — verrou V1c (carte des tables)

- `taxe_amenagement_secteur` → réservoir `taxe_amenagement` (secteurs à taux majoré par parcelle,
  à côté de `taxe_amenagement_taux`).
- `mvt_tile_cache` → `TABLES_FABRIQUEES` (artefact `labuse tiles-warm`, tuiles MVT z9-z11), à côté de `mvt_parcels`.
- `verrou_tables_orphelines` (V1c) sur la base réelle : **ok — 0 orpheline** (les deux tables reconnues).

### A.3 — captures S2

9 PNG déplacés de `captures/outils-s2/` (racine) vers `docs/audit-2026-09/outils-s2/captures/`
(`git mv`) ; lien du rapport OUTILS-S2 mis à jour.

### État des verrous (`labuse circuit verrous`, base réelle)

- ✅ **V1c** (orphelines) : ok — les deux tables inscrites.
- ✅ **G6** (réservoir muet) : « 0 lecture(s) de réservoir muet » (le fix `secteur_lieu_dit` + catnat porté sur la base réelle).
- ✅ **V5b** (une donnée = une fonction) : rétabli (secteur_lieu_dit servi par un robinet).
- ⚠️ **Cassés PRÉ-EXISTANTS hors périmètre RETOUCHES-1**, à traiter séparément :
  - **G1** — 3 doublons sans arbitrage (couches GEOPF-3 partageant `data.geopf.fr/wmts` : « Contraintes
    EnR », « SCAN 50 1950 », « EduGéo 1980 ») → reconciliation registre GEOPF-3, pas une régression RETOUCHES-1.
  - **G8** — 8 sources vitrine sans contrôle récent car `LABUSE_AGENT_PLAFOND_EUR=0` (agent désactivé en
    dev) : c'est l'état voulu du garde-fou (il DIT que l'agent ne dépense rien), pas un bug de code.

---

## Lot B — un chiffre, une fonction

### B.6 — garde-fou commune inconnue (✅ fait)

COMMUNE-124 : dans `/moteurs/barometre` (`_barometre_data`), un `insee` ne résolvant aucune commune
(code postal, ou code hors des 24) rendait le filtre `commune = :nom` INERTE → séries **île entière**
en silence (CP 97440 → 2 738 €/m² île au lieu de 1 600 pour Saint-André réel). Correctif :
**HTTPException 400 « Commune inconnue »** dès que `insee` fourni ne résout aucun nom ; le front
(onglet Évolution, `moteurs.tsx`) affiche `ApiError.detail`. Test `test_barometre_commune_inconnue_leve_400`
(code inconnu → 400 ; île servie au défaut ; commune réelle → ses chiffres). tsc 0.

### B.7 — tuile « terrain nu » de l'en-tête (✅ sans objet, documenté)

La tuile « Terrain nu » a **quitté l'en-tête de la fiche** (RECETTE-6 C5, `Fiche.tsx:577-578` :
« les tuiles Terrain nu et Bâti ancien ayant quitté l'en-tête, `dvfSecteur` n'est plus dérivé ici »).
Le prix terrain nu qui reste (bloc Marché de la fiche, `ligne2_terrain_zone`) lit déjà un **seuil de
config** (`seuils_effectif.terrain_cellule_commune` = 10) — le même mécanisme (« même fonction ») que
le bloc Marché (`secteur_dossier.seuil_effectif` = 8) — avec « non calculable / échantillon insuffisant »
en dessous. Le « 5 » du mandat correspond à `n_affiche: 5` (nombre de comparables AFFICHÉS, pas un seuil
de fiabilité). Il n'existe donc **plus de seuil codé en dur dans l'en-tête à aligner** ; forcer « 5 »
(sous 8/10) diminuerait l'honnêteté. **Aucune action** — la retouche est absorbée par RECETTE-6 + le
mécanisme de seuil config déjà partagé.

### B.4 — Assemblage sur l'union (⏳ à faire — plan)

**Bug** : `assemblage.aggregate_assiette` (src/labuse/assemblage.py:119) SOMME les `fiche_payload`
par parcelle (SDP + bilan) → les reculs internes entre parcelles sont comptés deux fois et la VRD est
appliquée par parcelle. La note servie l'admet déjà (« l'assiette réelle porte GÉNÉRALEMENT PLUS »).
**Plan** (une assiette, un moteur, une VRD) :
1. `ST_Union(geom_2975)` des parcelles → géométrie + surface de l'union.
2. Emprise constructible de l'union par une variante de `_EMPRISE` (faisabilite/db.py:76) sur
   `WHERE id = ANY(:ids)` + `ST_Buffer(ST_Union(...), -recul)` (les limites internes disparaissent).
3. `estimate_capacity(rules_dominante, surface_union, emprise_geo=(emprise_union, recul))`
   (faisabilite/engine.py:276) — LA fonction du résiduel → SDP de l'union.
4. Bâti existant mesuré sur l'union → SDP résiduelle.
5. **`compute_bilan` UNE fois** (faisabilite/bilan.py:454, COMPARER-2 §2 : VRD sur l'emprise aménagée).
6. Garder `sdp_par_parcelle` pour le gain « vs la meilleure seule » (déjà par parcelle).
Témoin : le lot de 3 parcelles contiguës — SDP et charge foncière avant/après, écart expliqué.

### B.5 — médianes DVF unifiées (⏳ à faire — plan)

Fonction canonique de la fiche : `bilan.reference_locale` (bilan.py:306, FICHE-FIX-2 P2) — médiane
par type (maison/appart/terrain), rayon adaptatif 500→1000→1500 m. Divergent :
- `ingestion/dvf_marche.neuf_vefa_commune` (dvf_marche.py:141) — VEFA neuf, grain commune (déjà seuil
  partagé `neuf_vefa_seuil`, à confirmer comme référence neuf commune).
- `flash._marche` (flash/data.py:446) — médiane LOCALE tous types, rayon FIXE (documentée « distincte »
  du sector_price). **Plan** : faire lire `reference_locale` (par type) à Étude de zone pour maison/
  appartement/terrain ; témoins CV1498 + un polygone d'Étude de zone = mêmes médianes que la fiche.
⚠ nuance : `_marche` sert une médiane « tous types rayon fixe » ASSUMÉE distincte ; l'unification doit
préserver l'intention (indicateur local) tout en servant les 3 médianes par type de la fiche.

### B.8 — badge Estimé au bilan (⏳ à faire — plan)

Le bilan (`constructibilite.tsx:218`) affiche « prix de sortie neuf X €/m² » sous l'étiquette
« LABUSE (sourcé) » alors que c'est une **médiane DVF secteur** (estimée). **Plan** : badge
`Estimé` (motif ambre, comme `moteurs.tsx:427` `SE`) + sous-ligne source (« DVF secteur ») et fenêtre
(rayon + n + années) ; exposer `prix_sortie_source`/`n`/`fenetre` dans le payload bilan si absents.

---

## Lot C — ce qui manque à la fiche (FICHE-3) — ⏳ à faire (plan)

Tables déjà en base (FICHE-AUDIT-2 §3) et fonctions de lecture repérées :

| # | Bloc | Section choisie (pourquoi) | Table / fonction |
|---|---|---|---|
| 9 | Cartofriches | **§Risques et environnement** (une friche est une contrainte/opportunité de réemploi, lue à côté des risques ; §Urbanisme est déjà dense en zonage) | `spatial_layers kind='friche'` · `ingestion/cartofriches.py` (`parcelles_croisees`) |
| 10 | Loyers OLL | §Marché | `oll_loyers`+`oll_zonage` · `ingestion/oll_loyers.oll_parcelle(db, idu)` (millésime 2024) |
| 11 | Trafic RN (TMJA) | §Réseaux (« Axes et nuisances ») | `trafic_rn` · proximité `ST_DWithin(p.geom_2975, trafic_rn.geom, …)` (zone.py:296) |
| 12 | CatNat (5 derniers) | §Risques | `catnat_arretes` · `api/fiche_commune.py:risques` (chiffres `catnat_n`/`catnat_arretes_liste`) |
| 13 | Acquisitions PM voisines 300 m / 36 mois | §Marché | DVF × `parcelle_personne_morale` (SIREN, dénomination) + lien Scan patrimoine |
| 14 | Ancienneté de détention | §Identité | PM : `pm_proprietaires_millesimes` (1ʳᵉ apparition SIREN) ; PP : dernière mutation `v_parcel_dvf_last` (sans nom) |

Chaque ajout : une seule section, source citée, millésime, badge, « sans objet » quand vide (modèle
RefDrawer + `FactRow`/`Line`, cf. `Fiche.tsx`).

---

## Lot D — petits ajouts — ⏳ à faire (plan)

### D.15 — Gabarit ER/EBC/SUP dans le moteur

Constat : le **résiduel** (`faisabilite/db.py:429-488`, `_GREVE_SUR_ASSIETTE`/`_EMPRISE`) déduit DÉJÀ
ER + EBC (+ PEB/DPF/ravine/50 pas) de l'assiette. C'est le **moteur gabarit** (`gabarit/engine.py`
`compute_gabarit`, exclusions construites en `gabarit/builder.py:346-364`) qui n'exclut que le PPR
rouge — l'outil Gabarit n'affiche donc pas ER/EBC/SUP. **Plan** : ajouter ER (`plu_gpu_prescription`
subtype 05), EBC (subtype 01) et **SUP** (`kind='sup'`, le seul vraiment absent partout) comme
`Exclusion` dans `build_gabarit_input` (après le bloc PPR) → le TOUL les montre ; attention à ne pas
double-compter dans le résiduel (le `_GREVE` sur la zone déjà réduite trouvera ~0 pour ER/EBC).
**Ne pas relancer de run** (le run suivant les prendra) ; golden avant/après. SUP fait baisser la SDP
résiduelle là où il intersecte (nouveau).

### D.16 — sources servies en direct (`live`)

Les couches servies depuis un producteur externe SANS réservoir (courbes de niveau IGN
`ELEVATION.CONTOUR.LINE`, orthos « Remonter le temps ») n'apparaissent pas dans la liste des sources.
**Plan** (extension minimale, `sources_catalog.py` + `enums.py`) : statut `live`, l'ajouter à
`STATUTS_AFFICHES`/`WHERE_AFFICHEES`/`est_affichee`, marquer les deux sources `status='live'` ; verrous
G1/G4 à jour (une source `live` n'a pas de sonde amont → raison écrite, comme les sources manuelles).

### D.17 — RGE ALTI VPS (note prod, pas d'action)

Vérifier au déploiement que le raster RGE ALTI est complet sur le VPS (profil altimétrique).

---

## Vérification

- `pytest` ciblé (aires touchées lot A + B.6) : **108 passed, 0 failed** (`-m "not local"`).
- `labuse circuit verrous` base réelle : **V1c ok, G6 ok, V5b ok**.
- `tsc --noEmit` : 0 (frontend B.6).
- `pytest tests/` complet : le run de départ donnait **11 failed / 3366 passed** (les 3 interblocages
  de digest étant levés, la suite se termine désormais — avant, elle se figeait à ~92 %).

### Les 11 échecs du run complet : tranchés

**Corrigés par RETOUCHES-1 (cascades induites par le lot A + même-cause) — 4 :**

| Test | Nature |
|---|---|
| `test_lot5d::test_v5d_vert_sur_le_registre_reel` | cascade A.1 : `secteur_lieu_dit` exigeait une section fiche → déclarée |
| `test_circuit2_lot2::test_documents_commites_a_jour_du_registre` | cascade A.1 : docs registre régénérés (secteur_lieu_dit + rattrapage `taxe_amenagement_communale_pct` périmé) |
| `test_circuit1_lot6::test_agent_source_surface_et_plafond` | même dérive de cadence que `test_agents_sources` (CIRCUIT-P7) |
| `test_deps_declared::test_tous_les_imports_du_code_sont_declares` | `matplotlib` (scripts gabarit) déclaré au groupe `ml` |

(Ceci s'ajoute aux 8 échecs anticipés par le mandat, déjà corrigés au lot A.1/A.2 — cf. tableau A.1.)

**PRÉ-EXISTANTS hors périmètre RETOUCHES-1 (vérifié : aucun n'est causé par mes changements) — 7.**
Ce sont des dettes de merge GEOPF-3 ou des reliquats de features retirées par d'autres mandats ;
chacun a son geste, à traiter dans le mandat qui l'a créé :

| Test | Cause | Geste |
|---|---|---|
| `test_reparations1_lot2::test_graphe_exact_dans_les_deux_sens` | 17 lecteurs de tables réservoir non déclarés finement (dette G6 : `batiment_hauteur_lidar`, `oll_loyers`, `cadastre_historique`, `filosofi_carreaux_200m`, `trafic_rn`… readers ajoutés par GEOPF-3/DONNEES-FIX). Le verrou G6 lui-même NE casse PAS (dette « affichée, jamais tue ») ; ce test est plus strict (dette==[]). | déclarer les 17 arêtes fines dans `registre/lectures.py` (réconciliation GEOPF-3) |
| `test_g1_vert_sur_la_base_reelle` (`@local`) | 3 doublons de couches GEOPF-3 sans arbitrage (Contraintes EnR / SCAN 50 1950 / EduGéo 1980 partagent `data.geopf.fr/wmts`) | note ARBITRAGE ou alias sur ces `data_sources` (réconciliation GEOPF-3) |
| `test_verrous_lot1::…base_reelle` (`@local`) | échoue car le passage joue TOUS les verrous et G1 + G8 cassent (voir ci-dessus + G8 = agent à 0 €) | résolu quand G1 traité ; G8 = config env (plafond agent) |
| `test_front_reliquats::test_r2_sortie_distincte_des_decisions` | reliquat front (Tinder — `text-txt-mut` absent d'un bloc) | front, mandat Tinder/décisions |
| `test_front_reliquats::test_m135_echelle_action` | reliquat front (une STATUS-map porte encore `label: 'Faible'`) | front, mandat M135 |
| `test_copilote2_outil::test_portes_concept_toutes_vivantes` | `_CONCEPT_MAP` garde une porte morte `renouvellement` (Densifier retiré, PISCINES-2) | retirer l'entrée morte, mandat Densifier |
| `test_retours17_permis::test_w2_cinq_lignes_etat…` | reliquat front (texte « l'instruction déposée n'y figure pas » absent du MP permis) | front, mandat RETOURS-17 |

→ **Compte final : 7 échecs pré-existants** (tous hors périmètre RETOUCHES-1, documentés ci-dessus avec
leur geste), **0 échec introduit**, tous les échecs anticipés par le mandat + les cascades induites au
vert. (Départ 11 échecs sur le run complet → 4 corrigés ici ; les 8 échecs « nommés » du mandat étaient
déjà traités et ne figuraient plus dans ce run.)

- Captures : à joindre (`docs/audit-2026-09/retouches-1/captures/`).

## Hors mandat

Un run île · la bascule · le déploiement · le vrai parcellaire par millésime · la mixité sociale au
calibrage · les autres usages du LiDAR · merger.
