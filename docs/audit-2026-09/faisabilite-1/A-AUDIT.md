# FAISABILITE-1 — Lot A · Audit des données (lecture seule)

**Date : 24/09/2026 · Branche `feat/faisabilite-1` (base main `f1a55381`) · worktree `~/Desktop/labuse-faisa`.**
**Type : audit lecture seule. Aucun code applicatif modifié. Écrit AVANT le lot B (règle du mandat).**

Base de vérité : le code servi (`src/labuse/faisabilite/`), la config servie (`config/`) et la
**base réelle `labuse`** (run résiduel servi, PLU calibrés) — pas une mémoire de mandat. Tous les
chiffres témoins ci-dessous sortent de `docs/audit-2026-09/faisabilite-1/verif_temoins.py` (moteur
live + vue `parcel_residuel`, lancé sur la base `labuse`).

**Témoins.** Le mandat en nomme trois ; la base les précise :

| Témoin mandat | Parcelle réelle | id | commune | surface | état mesuré |
|---|---|---|---|---:|---|
| BZ1065 « nu » | `97411000BZ1065` | 336319 | Saint-Denis (Uh) | 1 625 m² | **bâtie ~40 % d'emprise, 88 % du potentiel SDP** — PAS nu (écart de description, cf. §5) |
| BW0457 « bâti, capture Kelfoncier » | `97415000BW0457` | 26887 | Saint-Paul (U6c, **calibré**) | 393 m² | bâtie ~72 %, résiduel 34 m² |
| A/N 90-99 % portion U | `97402000AB1117` | 63195 | Bras-Panon (**N dominante à cheval**) | 4 097 m² | zone N dominante, portion U/AU minoritaire |

> Un 4ᵉ témoin est instruit en contrôle : `97410000BW0457` (Saint-Benoît, Ub, **NON calibré**) —
> il expose une divergence live↔cache (§2.3).

---

## §1 — Les étapes du calcul « Par parcelle »

Le moteur `estimate_capacity` (`faisabilite/engine.py:213-593`) émet une **liste d'étapes `Step`**
(label · formule · valeur · source · `prov`). Le front (`fiche/constructibilite.tsx:436`,
`FaisabiliteTab`, partagé fiche + outil M22) les rend en liste numérotée ; il **ajoute une 12ᵉ ligne**
« SHAB vendable retenue » (`constructibilite.tsx:375-382`). Le nombre d'étapes varie (renvoi AU→U et
stationnement sont conditionnels) : **10 pour BZ1065, 11 pour BW0457**. Voici les 11 étapes
canoniques, dans l'ordre, avec la source réellement citée sur les témoins.

| # | Étape (label servi) | Source lue · où | Millésime | Badge affiché aujourd'hui | Nature réelle |
|---|---|---|---|---|---|
| 0 | Zone (renvoi AU→U) *(si renvoi)* | `rules.via_renvoi`, règlement caractère de zone | PLU commune | `—` | Sourcé |
| 1 | Emprise au sol — reculs (géométrie réelle) | **Art. 7** recul limites séparatives, `engine.py:307` ; géométrie `_EMPRISE` ST_Buffer contour EPSG:2975 `db.py:76` | PLU commune (ex. Saint-Denis `97411_PLU_20260805`) + cadastre | `—` | **Sourcé** si recul calibré ; **Estimé** si repli `recul_limites_defaut_m=3 m` (`hypotheses_ile.yaml`) |
| 2 | Emprise au sol — % réglementé | **Art. 9** `rules.emprise_sol_pct` `engine.py:326` | PLU commune | `—` | **Sourcé** si CES chiffré ; sinon « non réglementée → bornée par reculs » ; **Estimé** (`prov='estimee'`) si plage par secteur |
| 3 | Contrainte pleine terre *(si calibrée)* | **Art. 13** `rules.pleine_terre_pct` `engine.py:349` | PLU commune | `—` | Sourcé (PLU-7 : forme composée espaces verts × part) |
| 4 | Niveaux constructibles | **Art. 10** `rules.niveaux_max` / `he_m` / `hf_m` `engine.py:369` ; PROSPECT Ud/Uu = largeur voie BD TOPO `db.py:311` | PLU commune + BD TOPO | `—` | **Sourcé** (R+n lu) ; **Estimé** (`prov='estimee'`) si plage ; « estimation générique » si commune NON outillée |
| 5 | Emprise bâtie (occupation du gabarit) | `coef_occupation` **0,45** — `hypotheses_ile.yaml` (défaut dataclass) `engine.py:409` | « choix 2026 », non daté | `—` | **Estimé** (hypothèse de modélisation, pas le règlement) |
| 6 | Surface de plancher brute | `emprise bâtie × niveaux` `engine.py:427` | dérivé | `—` | **Dérivé** |
| 7 | Surface habitable (rendement) | `coef_rendement` **0,80** — `hypotheses_ile.yaml` `engine.py:430` | « audit O2 » | `—` | **Estimé** |
| 8 | Logements — après plafond de densité | `densite_logts_ha_par_niveau` **30/niveau** — `hypotheses_ile.yaml` (via dataclass) `engine.py:454` | « ex-COS », non daté | `—` | **Estimé** (filet de modélisation, « le PLU ne fixe aucune densité ») |
| 9 | Stationnement — scénario au sol *(si borné)* | **Art. 12** `rules.places_par_logement()` + `place_m2` **25** `engine.py:484` | PLU commune (places) + Estimé (m²/place) | `—` | **Sourcé** (places/logt) mixte **Estimé** (25 m²/place sauf `place_m2_source_ref`) |
| 10 | Stationnement — scénario sous-sol/silo *(si borné)* | idem Art. 12 `engine.py:489` | idem | `—` | Dérivé du scénario |
| 11 | Logements retenus au sol | `plafond densité ∩ stationnement au sol`, puis modulation réunionnaise `engine.py:553` | dérivé | `—` | **Dérivé** |
| 12 | *(ajout front)* SHAB vendable retenue | `logements retenus × logt moyen`, `constructibilite.tsx:378` | dérivé | **Dérivé** (`prov='derive'`, badge neutre) | Dérivé |

### 1.a — Constat central sur le badge

**Aujourd'hui, aucune des 11 étapes physiques ne porte de badge Sourcé/Estimé/Dérivé.** Dans
`estimate_capacity`, tous les `Step(...)` sont émis avec `prov` par défaut = `""` (chaîne vide) —
**sauf deux** cas de plage (`prov='estimee'` : emprise par secteur `engine.py:341`, hauteur par
secteur `engine.py:389`). Le front (`primitives.tsx:366-374`, `StepProv`) mappe `''` → **`—` (tiret,
ton neutre)**. Seule la 12ᵉ ligne ajoutée par le front (`prov='derive'`) porte un vrai badge.

→ La **colonne source** (texte : « Art. Uh.9 · p.73 (PLU, calibrage validé) », « hypothèse
rendement »…) est bien renseignée et distingue le sourcé du posé ; mais le **badge** ne l'est pas.
C'est le point que le **lot D** doit corriger (classer chaque étape pour verrouiller les Sourcé et
rendre éditables les Estimé/Dérivé). Les lignes 5-8-9(m²/place) sont des **constantes en dur**
(`hypotheses_ile.yaml`, valeurs « choix 2026 »/« audit O2 »/« ex-COS », non datées finement) — c'est
d'elles que viendront les champs éditables.

### 1.b — Valeur = fiche § capacité = `parcel_residuel` ? (les 3 témoins)

Le moteur alimente **identiquement** l'outil « Par parcelle » (`GET /modules/faisabilite/{idu}`,
`api/modules.py:1649`) et la fiche (onglet Constructibilité, `app.py:6260` → `fiche_payload` →
`parcel_faisabilite`). Les **11 étapes sont donc les mêmes** dans l'outil et la fiche (même payload
`steps`). Preuve témoins (moteur live, `assiette_clippee=False`) :

| Témoin | verdict live | SDP brute (étape 6) | SHAB vendable | résiduel LIVE (clippée=F) | vue `parcel_residuel` SERVIE | accord ? |
|---|---|---:|---:|---:|---:|---|
| BZ1065 (Saint-Denis) | R+0 · ~1-2 logts | 219 m² | 123 m² | **26 m²** (taux 40 %) | **26 m²** (taux 40 %, pct 88) | **✓ identique** |
| BW0457 (Saint-Paul) | R+1 · ~1-3 logts | 172 m² | 138 m² | **34 m²** (taux 72 %) | **34 m²** (taux 72 %, pct 80) | **✓ identique** |
| AB1117 (Bras-Panon, N) | **Non constructible (zone N)** | — (0 étape) | — | **indispo, SDP 0** (cause `zone_non_constructible:N`) | **81 m²** (disponible) | **✗ DIVERGENT — cf. §2.2** |

Sur les 2 témoins mono-zone U (BZ1065, BW0457-SP) : **la fiche, l'outil, le résiduel live et le
résiduel servi coïncident à l'unité.** La divergence n'apparaît que sur la parcelle A/N à cheval.

---

## §2 — Le moteur

### 2.1 — Même fonction ?

**Oui.** L'outil « Par parcelle » et l'onglet Faisabilité de la fiche appellent tous deux
`parcel_faisabilite` (`faisabilite/db.py:284`) :

- outil : `api/modules.py:1649` `parcel_faisabilite(db, row["id"])`
- fiche : `api/app.py:6260` `fiche_payload(db, p.id)` → `db.py:475` `parcel_faisabilite(session, parcel_id)`

Le front `FaisabiliteTab` est **un seul composant** (`fiche/constructibilite.tsx:357`), monté dans la
fiche (`idu`) et dans l'outil (`idu={picked} embedded`). Une seule implémentation d'affichage.

### 2.2 — Assiette clippée ou tout-ou-rien ? (LE point)

`parcel_faisabilite(..., assiette_clippee=False)` **par défaut**, et **les deux appelants servis
gardent le défaut** → **tout-ou-rien** :

- Ce que le défaut fait TOUJOURS (`db.py:332` `_EMPRISE`) : emprise = contour inseté du recul,
  **clippé à la portion U/AU** en zonage mixte (Décision 1), **ER (typepsc 05) et EBC (typepsc 01)
  soustraits** de l'assiette (`db.py:346-363`). L'aléa PPR (fort/moyen/faible), la pente, le littoral,
  le SAR agricole s'appliquent en **facteur de modulation** (`engine.py:518-545`).
- Ce que le défaut NE fait PAS (réservé à `assiette_clippee=True`, `db.py:369-378`) : **résoudre une
  sous-zone U/AU quand la zone dominante est A/N** (`_sous_zone_constructible`), et soustraire les
  **contraintes géométriques certaines** (PPR rouge/INTERDICTION, PEB A/B, marchepied DPF, ravine,
  50 pas — `_greve_certaine_m2`), et ramener la surface CES/pleine-terre à la portion U/AU.

**Preuve sur le témoin A/N (`97402000AB1117`)** :

```
parcel_faisabilite(clippee=False)  → constructible=False, zone N, cause=zone_transition,
                                     verdict « Construction neuve non autorisée en zone N », 0 étape
compute_residuel(clippee=False)    → indisponible, SDP écrite 0, cause zone_non_constructible:N
compute_residuel(clippee=True)     → disponible, SDP résiduelle 81 m²   ← la portion U/AU
vue parcel_residuel (SERVIE)       → 81 m²   ← le run servi EST clippé
```

**Conséquence — divergence servie réelle.** Le **run résiduel servi** dans la base `labuse` est
**seq 5** (`residuel_runs.is_served`, label « run 5 = copie run 3 + delta assiette clippée (fix bâti
13d8fefd) », calculé le 22/09/2026) : il a été construit **avec** `assiette_clippee=True`. Donc :

- la **carte / le filtre / « Par critères »**, qui lisent la **vue `parcel_residuel`**, voient
  **81 m²** sur cette parcelle A/N ;
- l'**outil « Par parcelle » et l'onglet fiche**, qui recalculent **en direct** `parcel_faisabilite`
  (défaut non clippé), affichent **« Construction neuve non autorisée en zone N » (0)** ;
- pire, **le bloc « potentiel résiduel » de la fiche elle-même** recalcule en direct
  (`fiche_payload` → `compute_residuel(faisa=res)`, res non clippé) → **0**, en désaccord avec la
  carte qui montre 81.

C'est un **écart data profond** (choix de run/servi), pas une constante fausse : il **se décrit et se
laisse à Vic** (soit servir un run non clippé partout, soit passer les lecteurs live en clippé — les
deux ont des effets sur le scoring/servi hors mandat). ⚠ Note annexe : `config/served_manifest.json`
du repo indique encore `residuel_run_seq: 2` (non clippé) alors que la base sert le run 5 (clippé) —
le manifeste est **désynchronisé** de l'état servi réel (à signaler à Vic).

### 2.3 — Divergence secondaire live↔cache (témoin de contrôle Saint-Benoît)

`97410000BW0457` (Ub, **commune non calibrée** → niveaux « estimation générique ») :

```
compute_residuel(clippee=False) LIVE → 178 m² (taux emprise 54 %)
compute_residuel(clippee=True)  LIVE → 144 m²
vue parcel_residuel SERVIE            → 0 m² (taux 168 %, « sur-bâtie », capacite_estimee=true)
```

Le cache servi mesure ici **beaucoup plus de bâti** (168 %) que le moteur live (54 %) → SDP servie 0
vs live 178. Cause probable : le run 5 a figé une mesure d'emprise bâtie (BD TOPO + CoSIA révélé,
`residuel.py:_emprise_revelee`) différente de l'état live courant. **Écart de fraîcheur de cache**,
pas une formule fausse — à recalculer par un run neuf (geste de Vic, hors mandat). Documenté pour ne
pas le confondre avec l'écart §2.2.

---

## §3 — Ce qui manque (données en base non injectées dans la faisabilité servie)

| Donnée | En base ? | Utilisée par la faisabilité SERVIE (live, non clippé) ? | Impact | Suite |
|---|---|---|---|---|
| **ER (emplacements réservés)** déduits de l'assiette | oui (`plu_gpu_prescription` typepsc 05) | **OUI** (`_EMPRISE`, `db.py:346`) | assiette réaliste | rien à faire |
| **EBC (boisé classé)** déduit | oui (typepsc 01) | **OUI** (`db.py:359`, L113-1 CU) | assiette réaliste | rien à faire |
| **CES vraie** quand chiffrée | oui (`rules.emprise_sol_pct`) | **OUI** (Art. 9, `engine.py:326`) | plafond emprise sourcé | rien à faire |
| **Pleine terre composée** (PLU-7) | oui (`pleine_terre_compose`) | **OUI si calibrée** (`engine.py:356`) | assiette | rien à faire |
| **Stationnement** (places exigées) | oui (`places_par_logement`, Art. 12) | **OUI** — 2 scénarios sol/sous-sol (`engine.py:474`) | plafonne les logts au sol | **lot D** : rendre la ligne explicite + `place_m2`=25 éditable |
| **PPR rouge / PEB A/B / DPF / ravine / 50 pas** clippés de l'assiette | oui (`ppr`,`peb`,`dpf`,`ravine`,`cinquante_pas`) | **NON servi** (seulement `assiette_clippee=True`) ; l'aléa PPR joue en modulation ×facteur | assiette surestimée sur parcelles grevées | **écart data (Vic)** — dépend du choix run servi §2.2 |
| **Résolution sous-zone U/AU (A/N à cheval)** | oui (`zone_parts`) | **NON servi** (clippé seulement) | 0 vs SDP réelle §2.2 | **écart data (Vic)** |
| **Hauteur LiDAR du bâti existant** (faîtage/égout) | oui (`hauteur_lidar*.py`, dalles LiDAR) | **NON** — le résiduel lit BD TOPO `nombre_d_etages`/`hauteur`, sinon **placeholder 1 niveau** (`residuel.py:_niveaux_existants`) | SDP existante (donc résiduelle) approximée quand BD TOPO muet | **écart data** — brancher la mesure LiDAR (candidat Vic, module non câblé) |
| **SUP (servitudes d'utilité publique) assiettes** | oui (couches SUP) | **NON déduites** | assiette surestimée sous SUP | **écart data (Vic)** |
| **Espaces inconstructibles boisés hors EBC** (OCS/CoSIA végétal) | oui (`parcel_ocsge`) | **NON** (seul l'EBC réglementaire est déduit) | marginal | **écart data (Vic)** |
| **Taxe d'aménagement** | oui (`config/taxe_amenagement.yaml`, outil dédié M-taxe) | **NON** dans la faisabilité (outil séparé) | pas une capacité physique | hors périmètre capacité |
| **Mixité sociale** (LLS) | partiel : **détectée en badge** (`prescriptions_eco.mixite`) mais `pct_lls=0` placeholder (`engine.py:96`), `prix_m2_lls=0` | **NON modélisée** (calibrage bloqué) | pas de part LLS dans la capacité | **lot D** : ligne « non modélisée » explicite (jamais un 0 muet) |

**À corriger au lot D (écarts simples)** : (1) exposer une **ligne stationnement** lisible + rendre
`place_m2` éditable ; (2) ajouter **espaces inconstructibles déduits** (ER/EBC — déjà calculés,
juste à afficher en ligne) + une **ligne SUP/greve** ; (3) badger correctement chaque étape (§1.a).
**À laisser à Vic (écarts profonds)** : le choix du run servi clippé vs non clippé (§2.2), le
branchement hauteur LiDAR, la déduction SUP au moteur, le calibrage mixité.

---

## §4 — « Par critères » en 5 lignes

1. **SDP nécessaire** = `unités × surface_unite_m2 × coef_circulation` (`modules.py:1926`), avec
   `coef_circulation = 1 + circulation_pct/100` (front `M22Programme.tsx:51`) ; le formulaire est
   BÂTIMENTS × (R+N) × unités/bât × m²/unité × % circulations.
2. **Colonne filtrée** = `r.sdp_residuelle_m2 >= :sdp` — la **SDP RESTANTE** de la vue
   `parcel_residuel` (run servi, `modules.py:1942`), **pas** le gabarit brut ; puis Python plafonne
   au gabarit demandé (`sdp_dispo = sdp_resid × niveaux_dem/niveaux_max`, `modules.py:2018`) et vérifie
   l'emprise (`modules.py:2030`).
3. **« Activité »** = `DestinationSelect` (front) → param `destination` : écarte les parcelles dont la
   zone rend la sous-destination R151-28 « interdit » (`_dinfo`, `modules.py:2034`) ; « calibration en
   cours » = non filtrée.
4. **« ×1 »** = la **marge de capacité** `sdp_dispo / sdp_min` (`modules.py:2040`) ; le tri est par
   marge croissante (le meilleur ajustement d'abord) — « ×1 » = la parcelle tient tout juste le
   programme.
5. **« Inclure A/N »** (front `M22Programme.tsx:181`) = inclure ou masquer les parcelles à zonage
   agricole/naturel dans la liste ; par défaut masquées (elles n'ont pas de droits neufs). Le mandat
   la supprime au lot C : le **filtre Zonage** du panneau (familles U/AU/A/N + zones exactes) fait déjà
   ce travail, et de façon globale.

> **Écart de compteur à expliquer au lot B** (« SDP ≥ 960 » ≠ 8 949 de l'ancien « Par critères ») :
> « Par critères » **ne se réduit pas à `sdp_residuelle ≥ X`** — il ajoute `surface_m2 ≥ 0,4×SDP`, un
> **filtre de tier scoring** (`s2.tier IN (…)`, `modules.py:1949`, exclut le non-scoré/`sans_signal`
> selon le cas), le plafond-au-gabarit Python et le filtre destination. Le futur groupe **Capacité**
> du panneau ne fera QUE `sdp_residuelle ≥ X` (∧ logts ≥ N ∧ destination) sur toutes les parcelles →
> le compteur sera **plus large** (pas de filtre tier ni de plafond-gabarit). L'écart sera chiffré et
> ventilé (brut vs restante, A/N inclus/exclus, tier) dans `FAISABILITE-1.md`.

---

## §5 — Écarts entre le mandat et la base (à confirmer avec Vic)

1. **BZ1065 dit « nu »** : la base le donne bâti à ~40 % d'emprise (88 % du potentiel SDP consommé),
   résiduel 26 m². Ce n'est pas un terrain nu. C'est le seul `BZ1065` de Saint-Denis (`97411000BZ1065`).
   Le témoin reste utilisable (fiche = outil = résiduel servi, à l'unité) mais la **description** est
   à requalifier.
2. **BW0457 « la parcelle de la capture Kelfoncier »** : quatre `…BW0457` existent (Saint-Benoît,
   Saint-Paul, Saint-Pierre-du-… non, Le Tampon). Faute de la capture, l'audit retient **Saint-Paul**
   (calibré, cas propre live=servi) comme témoin bâti principal et **Saint-Benoît** comme témoin de
   contrôle (divergence §2.3). À confirmer laquelle vise la capture.
3. **Run servi = 5 (clippé)**, pas 2 : `config/served_manifest.json` est périmé vs la base (§2.2).

---

## Annexe — reproduire

```
PYTHONPATH=src LABUSE_DATABASE_URL="postgresql+psycopg://openclaw@localhost:5432/labuse" \
  ~/Desktop/labuse/.venv/bin/python docs/audit-2026-09/faisabilite-1/verif_temoins.py
```
Sortie brute conservée dans ce dossier. Base `labuse`, run résiduel servi seq 5, PLU calibrés
(millésimes `config/plu_millesimes.yaml`, ex. Saint-Denis approbation 05/08/2026).
