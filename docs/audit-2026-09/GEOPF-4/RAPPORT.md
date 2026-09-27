# GEOPF-4 — Contrôle avant merge de GEOPF-3 (lecture seule)

Worktree `labuse-geopf3`, branche `audit/geopf-4` (dérivée de `feat/geopf-3`, HEAD `c37052ed`).
Aucune écriture dans `src/` ni en base — audit sur la base partagée où les 8 couches GEOPF-3 sont
déjà ingérées. Base : `postgresql://openclaw@localhost:5432/labuse`.

## Verdict

**RAS bloquant — GEOPF-3 est mergeable.** Les 8 couches sont raccordées conformément à leur
cahier des charges ; les sources sont cohérentes (page Sources / data_sources / sentinelle) ; les
mesures compensatoires n'entrent **ni dans le résiduel ni dans le scoring**. Trois points de
vigilance (non bloquants) sont détaillés ci-dessous : (V1) « 8 nouvelles couches » = **7 nouvelles
sources** + BD TOPO IGN réutilisée ; (V2) les mesures compensatoires sont surfacées par l'**outil**
« Pièges et risques », pas par la **section §Risques de la fiche** ni l'export PDF (comportement
cohérent avec toutes les autres contraintes dormantes) ; (V3) 3 lignes `data_sources` legacy hors
catalogue code.

---

## A · Cohérence des sources (page Sources / data_sources / sentinelle)

### Chiffres live (au 26/09/2026)
| Mesure | Valeur | Définition |
|--------|-------:|-----------|
| `data_sources` en base | **128** | toutes les lignes |
| Catalogue code (`SOURCES`) | **125** | le catalogue déclaré (`seed_sources.SOURCES`) |
| Affichées (page Sources) | **98** | `count(*) WHERE {WHERE_AFFICHEES}` (accueil.py:85, dynamique) |
| `MODE_ET_CADENCE` | **128** | mode + cadence par source |
| Sentinelle : SEED / RAISONS | **86 / 38** | surveillées / non-surveillées (raison donnée) |

Répartition des statuts en base : `connecte 96 · partenariat_requis 14 · alias 6 · retiree 5 ·
hub 4 · manuel 2 · interne 1` = 128.

### Explication de l'écart « 92 affichées / 118 actives » (mandat = état PRÉ-GEOPF-3)
- **« actives » = 118** = le **catalogue code complet** (`SOURCES`), toutes les sources déclarées,
  quel que soit leur statut. Après GEOPF-3 : **125** (+7).
- **« affichées » = 92** = la **vitrine client** : `WHERE_AFFICHEES` = `lower(status) IN
  ('connecte','manuel')` **ET** technical_notes ne commence pas par `DOUBLON`/`RETIRÉ`/`DORMANT`
  **ET** pas `affichage_desactive` **ET** pas masquée (sources_catalog.py:36). Après GEOPF-3 : **98** (+6/7).
- **L'écart (26 pré-GEOPF-3, 30 en base aujourd'hui) est STRUCTUREL** : ce sont les sources
  **déclarées mais volontairement non montrées au client** — `partenariat_requis`/à-faire (14),
  doublons/`alias` (6), `retiree` (5), `hub` (4), `interne` (1). Ce n'est pas une incohérence : la
  page Sources, `est_affichee` (Python) et `WHERE_AFFICHEES` (SQL) appliquent **le même prédicat**
  (sources_catalog.py, invariant testé). Le client voit la vitrine ; le catalogue complet vit derrière.

### Les 7 nouvelles sources (couches 3-9) sont bien inscrites partout
Vérifié pour chacune : présente en `data_sources` (**connecte, affichée=True**), mode+cadence
(`MODE_ET_CADENCE`), sonde sentinelle, slug (`NOM_VERS_SLUG`) → réservoir (`RESERVOIR_TABLES`).

| Source | statut | affichée | cadence | sonde sentinelle (source_veille) | slug |
|--------|--------|:--------:|---------|----------------------------------|------|
| GéoMCE — mesures compensatoires | connecte | ✓ | one_shot / 365 j | SEED (témoin WFS, actif) | geomce |
| SCOT (GPU) | connecte | ✓ | one_shot / 365 j | SEED (témoin WFS, actif) | scot_gpu |
| Zones exclues EnR sauf toiture (OFB/APER) | connecte | ✓ | one_shot / 365 j | SEED (témoin WFS, actif) | enr_aper_ofb |
| BD NYME — lieux-dits (IGN) | connecte | ✓ | one_shot / 365 j | SEED (api data.gouv, actif) | bd_nyme |
| Contraintes EnR près habitations (Géoplateforme) | connecte | ✓ | sans objet | RAISON (raster WMTS figé) | enr_habitation_wmts |
| SCAN 50 historique 1950 (IGN) | connecte | ✓ | sans objet | RAISON (carte figée) | scan50_1950 |
| EduGéo Réunion 1980 (IGN) | connecte | ✓ | sans objet | RAISON (carte figée) | edugeo_1980 |

La cadence est portée par `mode_remplissage` + `cadence_attendue_jours` (= `MODE_ET_CADENCE`),
**pas** par la colonne libre `source_cadence` (NULL, comme pour la source de référence BD TOPO IGN).

### (V1) « 8 couches » mais **7 nouvelles sources**
Pylône et poste de transformation **réutilisent la source existante « BD TOPO IGN »**
(`KIND_SOURCE['pylone'] = KIND_SOURCE['poste_transformation'] = 'BD TOPO IGN'`) : pas de nouvelle
ligne `data_sources` pour eux, ce qui est correct (même flux amont, même sonde). Le raccordement
source↔couche en base est propre : `spatial_layers.data_source_id` rempli pour les 5 kinds vecteur
(pylone/poste → BD TOPO IGN ; mesures_compensatoires → GéoMCE ; scot → SCOT (GPU) ;
enr_exclue_hors_toiture → OFB/APER).

### (V3) 3 lignes `data_sources` legacy hors catalogue code (128 base vs 125 SOURCES)
`Communes La Réunion — contours (…seed)` (connecte, seedée hors `SOURCES` — admise par le test
sentinelle), `EDF SEI Réunion — open data` (**retiree**), `Registre national des installations
(ODRÉ)` (**retiree**). Divergence PRÉEXISTANTE (signalée au rapport TESTS-1), sans impact vitrine
(les 2 retirées ne sont pas affichées ; communes seed l'est).

**Conclusion A : cohérent.** Les trois surfaces disent la même chose ; l'écart affichées/actives
est structurel (vitrine vs catalogue) ; les 7 nouvelles sources sont inscrites de bout en bout.

---

## B · Raccordement des 8 couches (surfaces attendues, vérifié sur témoins live)

Légende : ✓ présent · — non attendu · ⚠ écart (attendu mais absent).

| Couche | Carte | Fiche parcelle | Fiche commune | « Pièges et risques » (outil) | Prospection solaire | Remonter le temps | Recherche | Export PDF |
|--------|:----:|:----:|:----:|:----:|:----:|:----:|:----:|:----:|
| **Pylônes** | ✓ | — | — | — | — | — | — | — |
| **Postes de transformation** | ✓ | ✓ (tiroir Réseaux, distance) | — | — | — | — | — | ✓ (bloc réseaux) |
| **Mesures compensatoires** | ✓ | ✓* (via outil) | — | ✓ | — | — | — | ✗* |
| **SCOT** | ✓ | — | ✓ (carte Urbanisme) | — | — | — | — | — |
| **EnR interdites hors toiture** | ✓ | — | — | — | ✓ (filtre exclusion) | — | — | — |
| **Contraintes EnR près habitations** | ✓ (raster) | — | — | — | ✓ (note) | — | — | — |
| **Lieux-dits** | — | ✓ (« Secteur ») | — | — | — | — | ✓ (5ᵉ grammaire) | — |
| **Cartes anciennes** | — | — | — | — | — | ✓ | — | — |

`*` voir (V2) ci-dessous.

### Témoins vérifiés en direct (appels des fonctions servies)
- **Postes** — parcelle `97416000DY0106` (Saint-Pierre) : `_proximites_block` sert
  `poste_transformation = {distance_m: 0, libellé "au contact… coût de raccordement (EDF SEI)"}`.
  Export courrier : `exports/blocs/reseaux.py` ligne « Poste de transformation ». ✓
- **Mesures compensatoires** — parcelle `97408000BI0304` (La Possession, corridor NRL) :
  `contraintes_parcelle` renvoie « Mesure compensatoire biodiversité (ERC) — … Nouvelle route du
  littoral · C1 » (source GéoMCE). ✓
- **SCOT** — `La Possession → SCOT TCO`, `Saint-Denis → SCOT DE LA CINOR` (ST_Contains centroïde,
  `scot_commune`). ✓ (rattachement 974 : TCO = Ouest, CINOR = Nord, Grand Sud = Sud ; Est/CIREST →
  aucun SCOT publié.)
- **EnR interdites hors toiture** — parcelle `97424000AI0287` (Parc national) :
  `prospection_solaire_parcelle` sert `enr_au_sol_exclu=True, zone="Réunion"`. ✓
- **Lieux-dits** — parcelle `97415000BH0283` (Saint-Paul) : `_secteur_lieudit → "Savanna"` ;
  recherche « Guillaume » → « le Guillaume, Saint-Paul » (vérifié navigateur, GEOPF-3). ✓

### Écarts / conformité
- **Pylônes = carte seule** : conforme au mandat (aucune autre surface attendue).
- **Contraintes EnR près habitations (raster)** : couche carte + note dans Prospection solaire
  (`data-solaire-enr-habitation`). Pas d'intersection parcellaire (raster) — conforme (mandat =
  « couche + visible dans l'outil », pas un fait parcellaire).
- **Lieux-dits** : pas de couche carte (mandat = recherche + « Secteur », pas une couche) — conforme.
- **(V2) Mesures compensatoires — nuance importante :** elles sont surfacées par l'**outil
  « Pièges et risques »** (outil #8 : `/modules/duediligence` pour un lot **et**
  `/servitudes-invisibles/{idu}` pour une parcelle, `blocB.tsx`) via `contraintes_parcelle`. Mais :
  - la **section §Risques de la fiche parcelle** (`risques.tsx`) rend les **aléas de la CASCADE**
    (`f.aleas`, via `aleas_parcelle_liste`), **pas** `contraintes_parcelle` — le payload
    `/parcels/{idu}` **n'appelle pas** `contraintes_parcelle` (0 occurrence dans app.py) ;
  - l'**export PDF §Risques** (`exports/blocs/risques.py`) lit `aleas_parcelle_liste` (cascade) —
    donc **n'inclut pas** les mesures compensatoires.
  **Ce n'est pas un défaut propre à GEOPF-3** : TOUTES les contraintes dormantes (SUP, DPU, ZNIEFF,
  DPF, zone humide, ENS…) suivent exactement ce chemin — l'outil « Pièges et risques », pas la
  section §Risques de la fiche ni l'export. La formule du mandat GEOPF-3 « visible dans Pièges et
  risques **et la fiche** » est donc satisfaite **via l'outil lié à la fiche**, pas via une nouvelle
  ligne dans la section §Risques. **Aucune action requise** — l'insertion au point unique
  `contraintes_parcelle` est le bon geste et propage la mesure partout où les autres contraintes
  apparaissent. À corriger seulement si Vic veut, en plus, une ligne « contraintes/servitudes »
  dans la section §Risques de la fiche et l'export (chantier transverse à toutes les contraintes,
  hors périmètre GEOPF-3).
- **Copilote / cascade** : aucune des 8 couches n'y entre (attendu — ce sont des couches
  d'information, pas des critères de scoring). Voir partie C pour les mesures compensatoires.

**Conclusion B : raccordement conforme.** Seule nuance (V2), documentée et cohérente avec
l'architecture existante.

---

## C · Mesures compensatoires : ni résiduel, ni scoring — CONFIRMÉ

Grep exhaustif de `mesures_compensatoires` (tout le repo) : les seules occurrences sont
**ingestion** (`cli.py`, `ingestion/mesures_compensatoires.py`, `seed_sources.py`), **couche carte**
(`declarations/couches/famille_nature.yaml`), **registre** (`layers_ingest.KIND_SOURCE`,
`registre/{donnees,robinets,couverture,tables}.py`), et **contraintes lecture-seule**
(`api/servitudes.py:_KINDS` → `contraintes_parcelle`). Un test la mentionne en commentaire.

- **RÉSIDUEL** (`faisabilite/residuel.py`) — kinds consommés : `batiment`, `plu_gpu_zone`.
  `mesures_compensatoires` **absent**. ✓
- **CASCADE** (`config/cascade_rules.yaml`) — 36 kinds déclarés (abf, bassin_versant, …, znieff,
  zone_activite, zone_humide). `mesures_compensatoires` **absent** (grep vide). ✓
- **SCORING** (`scoring/p_model/features.py`) — features du modèle P ; seul kind spatial_layers
  indirect = `friche`. `mesures_compensatoires` **absent**. ✓
- **Usage réel** : ingestion + rendu carte + liste de contraintes à l'écran (lecture seule) +
  métadonnées registre. **Zéro calcul.**

**Conclusion C : confirmé — `mesures_compensatoires` n'entre ni dans le résiduel ni dans le
scoring** (ni dans la cascade). C'est bien une contrainte d'INFORMATION dormante, comme voulu.

---

## Synthèse des points de vigilance (aucun bloquant)
1. **(V1)** 8 couches ⇒ **7 nouvelles sources** (pylône + poste réutilisent « BD TOPO IGN »). Correct.
2. **(V2)** Mesures compensatoires visibles via l'**outil** « Pièges et risques » (pas la section
   §Risques de la fiche ni l'export PDF) — cohérent avec toutes les contraintes dormantes.
3. **(V3)** 3 lignes `data_sources` legacy hors catalogue code (communes seed, EDF SEI ret., ODRÉ ret.)
   — divergence préexistante, sans impact vitrine.
