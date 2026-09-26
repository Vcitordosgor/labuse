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
| B | B.4 — Assemblage sur l'union | ✅ fait — SDP union 1017→1394 m², une VRD (voir §B.4) |
| B | B.5 — médianes DVF unifiées | ✅ fait — fiche == Étude de zone (voir §B.5) |
| B | B.8 — badge Estimé au bilan | ✅ fait — badge + source/fenêtre (voir §B.8) |
| C | C.9–14 — 6 blocs fiche (FICHE-3) | ✅ fait — 6 blocs sourcés (voir §C) |
| D | D.15 — Gabarit : SUP déduit | ✅ fait — SUP dans le moteur (voir §D.15) |
| D | D.16 — sources `live` | ✅ fait — statut live + badge « En direct » (voir §D.16) |
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

### B.4 — Assemblage sur l'union (✅ fait)

**Bug** : `assemblage.aggregate_assiette` SOMMAIT les `fiche_payload` par parcelle → reculs internes
comptés deux fois, VRD ×N. **Correctif** (une assiette, un moteur, une VRD) dans `src/labuse/assemblage.py` :
1. `_EMPRISE_UNION` (SQL) — `ST_Buffer(ST_Union(geom_2975), -recul)` (les limites internes disparaissent),
   ∩ portion U/AU, − union des grèves (ER ∪ EBC ∪ PPR rouge ∪ PEB A/B ∪ DPF ∪ ravine ∪ 50 pas ∩
   assiette) — MÊME logique/seuils que l'assiette clippée servie (`_EMPRISE` + `_GREVE_CERTAINE`).
2. `_capacite_union` — `estimate_capacity(rules_dominante, surface_union, emprise_geo=(emprise_union, recul))`
   (le moteur du résiduel/fiche) → SDP de l'union ; puis **`compute_bilan_servi` UNE fois** (COMPARER-2 §2,
   VRD sur l'emprise réellement aménagée) via un `(ctx, f)` synthétique de l'union + le parcel_id de la
   parcelle dominante (prix de sortie du secteur, identique pour des parcelles contiguës).
3. `aggregate_assiette` garde `sdp_par_parcelle` (gain vs la meilleure seule) ; les figures combinées
   viennent de l'union. Note servie réécrite (plus « estimation qui sous-compte »).

**Témoin** (trio Saint-Paul `97415000BI0055 / BI0701 / BI0616`, surface cumulée 1 626 m²) :

| | Somme des résiduels (avant) | Union (après) |
|---|---|---|
| SDP | 575 + 158 + 284 = **1 017 m²** | **1 394 m²** (+37 %) |
| Charge foncière | 3 VRD sommées | **une seule** : 328 386 € (central), **202 €/m² terrain** |
| Emprise constructible | — | 774 m² (union insetée, reculs internes supprimés) |

Tests : `test_assemblage.py` — guard structure endpoint (note « UNION », ca/charge None sans zonage
en base de test) + `test_aggregate_assiette_calcule_sur_l_union` (@db, skip justifié si la base de test
n'a pas de run résiduel ; vérifie sur données réelles SDP_union ≥ somme + charge unique). 4 passed, 1 skip.

### B.5 — médianes DVF unifiées (✅ fait)

Fonction canonique de la fiche pour les médianes PAR TYPE : `mon_secteur.par_type` (maison/appartement
via `reference_locale`/FICHE-FIX-2 P2, rayon adaptatif 500→1500 m ; terrain nu via la section
cadastrale `_terrain_section`). L'Étude de zone (`flash._marche`) calculait un `med_m2_bati` tous-types
à rayon FIXE (500 m) — divergent (mesuré sur CV1498 : 5 116 €/m² vs maison 5 058 / appartement 4 246).

**Correctif** : extraction d'un point de calcul UNIQUE `mon_secteur.medianes_par_type(db, idu)` →
{maison, appartement, terrain_nu} ; `mon_secteur` (fiche) ET `flash._marche` (Étude de zone) le lisent.
Le `med_m2_bati` tous-types (indicateur local) reste, distinct et documenté ; ce sont les médianes
PAR TYPE qui coïncident désormais.

**Témoin CV1498 (Saint-Paul)** — fiche == Étude de zone, à l'euro :

| | maison | appartement | terrain nu |
|---|---|---|---|
| Fiche (`mon_secteur.par_type`) | 5 058 €/m² | 4 246 €/m² | 295 €/m² |
| Étude de zone (`flash._marche.par_type`) | 5 058 | 4 246 | 295 |

**Comparer** : `/compare` (comparateur de PARCELLES) lit déjà `fiche_payload`/`_q_v2_fiche` (les
fonctions de la fiche) — aucun chemin de médiane parallèle. `neuf_vefa_commune` sert le prix NEUF au
grain COMMUNE (comparateur de communes) — métrique et maille légitimement distinctes (le neuf VEFA
d'une commune ≠ l'ancien par type d'une parcelle) ; déjà le point unique `DVF_NEUF_VEFA` de
`marche_service`. Test `test_mon_secteur_coherence::test_etude_de_zone_medianes_par_type_identiques_a_la_fiche`
(skip justifié si base de test vide ; vérifié sur données réelles).

### B.8 — badge Estimé au bilan (✅ fait)

Le bilan affichait « prix de sortie X €/m² » sous « LABUSE (sourcé) » alors que c'est une **médiane
DVF** (estimée). Correctif :
- back (`bilan.py` `compute_calculette`) : le bloc `marche` porte désormais la SOURCE et la FENÊTRE —
  `n`, `rayon_m`, `periode`, `type_prix` (en plus de median/fiabilite).
- front (`constructibilite.tsx`) : badge **« Estimé »** (motif ambre `st-creuser`, comme Comparer)
  après le prix + sous-ligne `data-prix-sortie-source` : « Prix de sortie Estimé — DVF (ventes actées,
  <type>) · N ventes · rayon R m · AAAA–AAAA. » Étiquette « LABUSE (sourcé) » → « LABUSE » (le prix
  n'est plus présenté comme sourcé).

Témoin CV1498 : « 4 246 €/m² [Estimé] — DVF (ventes actées, appartement) · 13 ventes · rayon 1 000 m ·
2023–2025 ». Test `test_bilan::test_calculette_marche_porte_source_et_fenetre`. tsc 0.

---

## Lot C — ce qui manque à la fiche (FICHE-3) — ✅ fait

Six blocs ajoutés à la fiche : back `api/fiche_blocs3.py` (une fonction par bloc, sourcée/millésimée,
`disponible=False` = « sans objet », **garde `_has` sur les tables** — une source non ingérée ne lance
jamais une requête qui échoue), branchés dans le payload `_q_v2_fiche` ; front dans LA section choisie
(source + millésime + « sans objet » quand vide). Témoin BZ1065 (Saint-Denis) : CatNat **21 arrêtés**
(5 servis) et **acquéreurs PM voisins** (GERER IMMOBILIER RÉUNION, LMA…) présents ; Cartofriches / OLL /
trafic RN / ancienneté « sans objet » sur ce témoin (données absentes pour cette parcelle).

Tables déjà en base (FICHE-AUDIT-2 §3) et fonctions de lecture :

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

### D.15 — Gabarit : SUP déduit du moteur (✅ fait)

ER et EBC sont DÉJÀ retranchés par le résiduel (`faisabilite/db.py` `_GREVE`/`_EMPRISE`). Le **moteur
unique GEOMETRIE-1** (`compute_gabarit`, exclusions en `gabarit/builder.py`) n'excluait que le PPR
rouge → le SUP (servitudes d'utilité publique) était ignoré partout. **Correctif** : `build_gabarit_input`
ajoute une `Exclusion` **type='sup'** (`kind='sup'`, assiette ∩ parcelle, même optimisation
ST_ClipByBox2D que le PPR) + une règle applicable « Servitudes d'utilité publique » (integrated si
présente, sinon not_integrated « dit, jamais tue »). Le moteur retranche cette exclusion comme le PPR
(`engine.py` : `zone = after_setbacks.difference(exclusions)`), donc **le gabarit-outil ET le résiduel**
(qui lit l'assiette gabarit) en tiennent compte. **Aucun run relancé** — le prochain run résiduel le
prendra (mandat). Témoin réel : `97415000BH0283` (Saint-Paul) → `exclusions=['sup']` dans l'entrée du
moteur. Tests `test_builder` : SUP présent → exclusion + règle integrated ; SUP absent → not_integrated
(82 gabarit verts ; le chemin de soustraction est celui, déjà prouvé, du PPR rouge).

### D.16 — sources servies en direct (`live`) (✅ fait)

Extension minimale du modèle du catalogue : statut **`live`** = servie EN DIRECT d'un producteur externe
SANS réservoir (overlay WMTS relayé). Ajouté à `enums.DataSourceStatus`, `circuit_garanties.STATUTS_ADMIS`
(liste fermée), `sources_catalog.STATUTS_AFFICHES` / `WHERE_AFFICHEES` / `est_affichee` → une source `live`
APPARAÎT dans la liste (page Données). SEED : les overlays externes sans réservoir passent `S.LIVE` —
**Remonter le temps** (SCAN 50 1950, EduGéo 1980) + **Contraintes EnR (APER)**. `/sources` expose `statut` ;
front `SourcesPage` : badge **« En direct »** (jamais « à jour »/vide). Verrous à jour : liste fermée
étendue (+ test `test_g1_statut_hors_liste_fermee_casse`), et ces sources portent déjà une raison écrite
(`RAISONS_NON_SURVEILLEES`, rasters figés) → pas de faux flag G4.

⚠ **courbes de niveau** (`ELEVATION.CONTOUR.LINE`) : ce N'EST pas une source distincte — c'est un canal
de diffusion de **RGE ALTI** (déjà catalogué), fold DÉLIBÉRÉ verrouillé par `test_outils_s2_couches_source`
(le compte reste à 92). Elle est donc déjà représentée (via RGE ALTI) ; la séparer casserait ce verrou
(décision hors périmètre). Les rows DB passent `live` au prochain seed (aucune écriture DB ici — pas de
run ; le code + le SEED portent le statut).

### D.17 — RGE ALTI VPS (note prod, pas d'action)

Vérifier au déploiement que le raster RGE ALTI est complet sur le VPS (profil altimétrique).

---

## Vérification

- `pytest` ciblé (aires touchées lot A + B.6) : **108 passed, 0 failed** (`-m "not local"`).
- `labuse circuit verrous` base réelle : **V1c ok, G6 ok, V5b ok**.
- Frontend : `tsc --noEmit` 0 · `vitest run` **188 passed** · `npm run build` exit 0.
- `pytest tests/` complet : **run final `6 failed, 3372 passed, 64 skipped` en 15:00** (les 3
  interblocages de digest étant levés, la suite se termine désormais — avant, elle se figeait à ~92 %).

### Les échecs du run complet : tranchés

Départ (run complet, base d'entrée) : **11 échecs**. **5 corrigés** par RETOUCHES-1 (cascades induites
par le lot A + même-cause) ; **6 pré-existants** restent, tous hors périmètre.

**Corrigés — 5 :**

| Test | Nature |
|---|---|
| `test_lot5d::test_v5d_vert_sur_le_registre_reel` | cascade A.1 : `secteur_lieu_dit` exigeait une section fiche → déclarée |
| `test_circuit2_lot2::test_documents_commites_a_jour_du_registre` | cascade A.1 : docs registre régénérés (secteur_lieu_dit + rattrapage `taxe_amenagement_communale_pct` périmé) |
| `test_circuit1_lot6::test_agent_source_surface_et_plafond` | même dérive de cadence que `test_agents_sources` (CIRCUIT-P7) |
| `test_deps_declared::test_tous_les_imports_du_code_sont_declares` | `matplotlib` (scripts gabarit) déclaré au groupe `ml` |
| `test_lot1_tables::test_verrous_lot1_passent_sur_la_base_reelle` (`@local`) | V1c (A.2) + V5b (secteur_lieu_dit rattaché) verts → `jouer_tous` ne trouve plus aucun V-verrou cassé |

(Ceci s'ajoute aux 8 échecs anticipés par le mandat, déjà corrigés au lot A.1/A.2 — cf. tableau A.1 —
qui ne figuraient déjà plus dans ce run complet.)

**PRÉ-EXISTANTS hors périmètre RETOUCHES-1 (vérifié : aucun n'est causé par mes changements) — 6.**
Dettes de merge GEOPF-3 ou reliquats de features retirées par d'autres mandats ; chacun a son geste,
à traiter dans le mandat qui l'a créé :

| Test | Cause | Geste |
|---|---|---|
| `test_reparations1_lot2::test_graphe_exact_dans_les_deux_sens` | 17 lecteurs de tables réservoir non déclarés finement (dette G6 : `batiment_hauteur_lidar`, `oll_loyers`, `cadastre_historique`, `filosofi_carreaux_200m`, `trafic_rn`… readers ajoutés par GEOPF-3/DONNEES-FIX). Le verrou G6 NE casse PAS (dette « affichée, jamais tue ») ; ce test est plus strict (dette==[]). | déclarer les 17 arêtes fines dans `registre/lectures.py` (réconciliation GEOPF-3) |
| `test_g1_vert_sur_la_base_reelle` (`@local`) | 3 doublons de couches GEOPF-3 sans arbitrage (Contraintes EnR / SCAN 50 1950 / EduGéo 1980 partagent `data.geopf.fr/wmts`) | note ARBITRAGE ou alias sur ces `data_sources` (réconciliation GEOPF-3) |
| `test_front_reliquats::test_r2_sortie_distincte_des_decisions` | reliquat front (Tinder — `text-txt-mut` absent d'un bloc) | front, mandat Tinder/décisions |
| `test_front_reliquats::test_m135_echelle_action` | reliquat front (une STATUS-map porte encore `label: 'Faible'`) | front, mandat M135 |
| `test_copilote2_outil::test_portes_concept_toutes_vivantes` | `_CONCEPT_MAP` garde une porte morte `renouvellement` (Densifier retiré, PISCINES-2) | retirer l'entrée morte, mandat Densifier |
| `test_retours17_permis::test_w2_cinq_lignes_etat…` | reliquat front (texte « l'instruction déposée n'y figure pas » absent du MP permis) | front, mandat RETOURS-17 |

→ **Compte final : 6 échecs pré-existants** (tous hors périmètre RETOUCHES-1, documentés avec leur
geste), **0 échec introduit**. Tous les échecs anticipés par le mandat + les 5 cascades/régressions
induites sont au vert (le fix V5b a même rendu `test_verrous_lot1` vert en prime).

- Captures : à joindre (`docs/audit-2026-09/retouches-1/captures/`).

## Hors mandat

Un run île · la bascule · le déploiement · le vrai parcellaire par millésime · la mixité sociale au
calibrage · les autres usages du LiDAR · merger.
