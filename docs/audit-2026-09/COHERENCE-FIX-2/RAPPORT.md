# COHERENCE-FIX-2 — un mot, un sens

**Branche** `fix/coherence-2` · base `origin/main` (8cb9b05c) · worktree `~/Desktop/labuse-coherence2` · ports 8695/5895 · Opus · 1 session.

**Mandat** : deux notions où deux écrans emploient le même mot pour deux choses — l'**emprise bâtie** (bâti clippé à la parcelle vs bâti « autre ») et le **secteur** (rayon court du Marché vs rayon long de l'Étude de zone). Les nommer, les cloisonner, faire tomber les écarts du banc à 0. **Aucun run, aucune bascule, aucune migration destructive.**

---

## Étape 0 — point de départ

- Arbre propre, `.env` en place, venv `~/Desktop/labuse/.venv`, DB dev `labuse` (431 663 parcelles).
- Banc `--echantillon --en-process` joué : **1 384 écarts** au total sur ce worktree (la DB partagée a des caches périmés vs la DB fraîchement reconstruite de COHERENCE-FIX-1) — MAIS les **deux notions du mandat sont exactement à leur baseline : `emprise_batie_m2` = 72, `prix_median_maison_secteur` = 96** (soit 168). Ces deux notions sont *indépendantes de la fraîcheur des caches* (fiche live vs SQL live), donc mesurables sans reconstruction interdite. Les ~1 216 autres écarts sont tous des notions à cause `run_different`/`cache_perime` (vigilances, score, résiduel, zonage, surface), hors périmètre et non touchées.

### Coordination FRONT-CHIFFRES-2 (parallèle sur `fix/front-chiffres-2`)

`git log --name-only origin/fix/front-chiffres-2 -20` : FC-2 modifie activement `frontend/src/components/fiche/marche.tsx`, `frontend/src/lib/types.ts`, `src/labuse/api/app.py`, `Fiche.tsx`, `ModulePanel.tsx`, `src/labuse/api/modules.py`.

**Chevauchement sur `marche.tsx` et `types.ts`.** Décision (validée) : **le back attache le périmètre à chaque valeur ; `marche.tsx` ne fait que rendre `{perimetre}`** — aucune chaîne de périmètre en dur dans le front. Édits `marche.tsx` limités à 2 lignes de rendu (contexte + tuile terrain) ; `types.ts` = un champ optionnel additif (`DvfSecteur.perimetre`). Zéro collision de logique avec FC-2.

---

## Lot A — l'emprise bâtie : une seule définition

### Recensement (producteurs / lecteurs)

| Rôle | `fichier:ligne` | définition |
|---|---|---|
| **Producteur SERVI** | `bati.py:le_bien_block` (→ `emprise_bati_bdtopo_m2`) | **BD TOPO clippé** à la parcelle, `ST_Union` avant `ST_Area` (pas de double-compte des empreintes mitoyennes). CoSIA servi **à part** (« bâti révélé »). |
| Producteur scoring | `scoring/p_model/sql.py:build_bati` → `p_model_bati.emprise_bati_m2` | **MAX(BD TOPO, CoSIA)** — entrée du modèle P (classement nu/densité). Dans ce worktree, **table périmée** (bâtie avant le correctif `ST_Union` → double-compte, plusieurs parcelles à 2×/3×). |
| Producteur résiduel | `faisabilite/residuel.py` | `bati_ratio × surface` (SUM, double-compte) + bump CoSIA — *cache isolé du scoring*, affichage. |
| Lecteur fiche §Bâti | `frontend/.../leBien.tsx` ← `le_bien.emprise_batie_m2` | BD TOPO clippé (servi). |
| Lecteur Dossier §Potentiel | `exports/robinet_fiche.py:290` ← `le_bien.emprise_batie_m2` | BD TOPO clippé (servi). |
| **FUITE** Dossier réhabilitation | `faisabilite/bilan.py:compute_mode_b` ← `SELECT emprise_bati_m2 FROM p_model_bati` | **la colonne SCORING, servie « emprise X m² [Sourcé] »** en export (`api/export.py:100`). |
| Filtre « Déjà bâti » | `api/app.py:1652` ← `p_model_bati.emprise_bati_m2 > 0` | classification bâti/nu (booléen), pas un nombre affiché — laissé au scoring (documenté). |

### Décision (option 1 retenue)

La définition servie au client de **« emprise bâtie » = BD TOPO clippé à la parcelle (`ST_Union`)**, CoSIA servi à part. C'était déjà le cas en fiche §Bâti et au Dossier. `p_model_bati.emprise_bati_m2 = MAX(BD TOPO, CoSIA)` devient une **notion distincte nommée `emprise_bati_scoring_m2` (« Emprise bâtie (scoring, BD TOPO ∪ CoSIA) »)**, entrée du modèle P — **jamais** le libellé client. **Aucun rebuild** (renommage de *notion*, pas de colonne).

> La prémisse du mandat (« clippé vs bâti entier ») était imprécise : les deux candidats clippent à la parcelle. L'axe réel est **BD TOPO seul** vs **BD TOPO ∪ CoSIA** (+ un double-compte dans la table scoring périmée). La résolution est la même : une définition servie, une notion scoring cloisonnée.

### Ce qui a changé

1. **Producteur unique** : `bati.py:emprise_bati_bdtopo_m2` extrait la requête `ST_Union(ST_Intersection(bâtiment, parcelle))`. `le_bien_block` la lit.
2. **Fuite fermée** : `compute_mode_b` ne lit plus `p_model_bati` ; il calcule `max(emprise_bati_bdtopo_m2, CoSIA révélé)` = « emprise révélée » (nommée au libellé `source_emprise`). Corrige au passage le double-compte (**63/120 parcelles de l'échantillon**, souvent exactement ×2/×3 — cf. `CHANGEMENTS.csv`).
3. **Banc** : le jumeau SQL de `emprise_batie_m2` reproduit désormais la définition SERVIE (`round(ST_Area(ST_Union(ST_Intersection…)))`), au lieu de `p_model_bati` (la notion scoring). Vérifié : jumeau == `le_bien` à l'unité près sur les parcelles d'écart (487.12→487, 192.96→193, 0.0→0…). **72 → 0.**
4. **Registre** : définition `emprise_batie_m2` reprécisée (BD TOPO clippé, CoSIA à part, ≠ scoring) ; `tables.py` et `scoring/p_model/sql.py` documentent la notion scoring.

La valeur client **fiche §Bâti / Dossier §Potentiel ne change pas** (déjà `le_bien`). La seule valeur d'écran qui bouge est l'**emprise du Dossier réhabilitation** (mode B), qui cesse d'être gonflée — `CHANGEMENTS.csv`.

---

## Lot B — « secteur » dit toujours son rayon

### Table des emplois (avant → après)

| Emploi (`fichier:ligne`) | périmètre RÉEL | avant | après |
|---|---|---|---|
| fiche Marché, contexte (`marche.tsx:75`) | section cadastrale | « N ventes **secteur** » | « N ventes **· section cadastrale** » (servi : `dvf_parcelle.secteur.perimetre`) |
| fiche Marché, tuile Terrain nu (`marche.tsx:88`) | section cadastrale | « €/m² · N ventes » | « €/m² · N ventes **· section cadastrale** » |
| fiche Marché, tuiles Maison/Appart (`marche.tsx:89-90`) | rayon adaptatif 500→1500 m | « · 850 m » | inchangé (le rayon EST le périmètre ; FactNote « rayon adaptatif ») |
| comparateur, « Prix bâti secteur » (`ComparePanel.tsx:76`) | section cadastrale | « Prix bâti **secteur** » | « Prix bâti **· section cadastrale** » (constante `perimetres.ts`) |
| dépôts « Sur le secteur » (`DepotsBlock.tsx:53`) | section cadastrale | déjà « · section cadastrale » (permits.py) | inchangé (déjà conforme) |
| PDF « médianes du secteur cadastral » (`exports/blocs/marche.py:63`) | section cadastrale | déjà nommé | inchangé |
| export « Terrain nu au prix du secteur » (`marche.py:72`) | section cadastrale | « du secteur » | « du secteur **(section cadastrale)** » |
| registre `prix_terrain_secteur_eur_m2` | section cadastrale | « Terrain nu **secteur** » (déf. FAUSSE « rayon adaptatif ») | « Terrain nu **· section cadastrale** » (déf. corrigée) |
| registre `prix_sortie_bati_eur_m2` | rayon adaptatif | « Prix de sortie — bâti **secteur** » | « Prix de sortie — bâti **· rayon adaptatif** » |
| registre `depots_secteur_n` | section cadastrale | « Déposés sur le **secteur** » | « Déposés **· section cadastrale** » |

Le périmètre est **servi par le back** (`dvf_parcelle.secteur[].perimetre = "section cadastrale"` ajouté dans `app.py` ; `mon-secteur` `par_type[].perimetre` existait déjà via `reference_locale`/`_terrain_section`). Aucun périmètre recalculé.

### Banc

L'ancien check `prix_median_maison_secteur` comparait **deux notions distinctes sous un même mot** : fiche `dvf_parcelle.secteur[maison]` (**section cadastrale**, DVF 2021-2025) vs mon-secteur `par_type.maison` (**rayon adaptatif**). Remplacé par `prix_maison_secteur_section_cadastrale` : fiche vs la table `dvf_secteur_medianes` qu'elle lit (même périmètre → cohérence vérifiable). **96 → 0.** Le golden des 7 témoins a été renommé (clé), valeurs identiques (aucune acceptation de dérive).

---

## Lot C — permanence (V6b)

Deux mâchoires ajoutées à `verrou_coherence_banc` (`circuit_verrous.py`) :

- **« secteur » dit son périmètre** : toute notion du registre (ou id de check du banc) dont le libellé évoque un voisinage (`secteur`/`à proximité`/`autour`/`alentours`) DOIT porter un périmètre (`section`/`rayon`/`iris`/`commune`/`km`/`m`/`adaptatif`…). Liste des emplois PROPRES du mot (non-distance) : `secteur_lieu_dit` (lieu-dit), `sis_classe`/`sis_couche` (Secteur d'Information sur les Sols = nom réglementaire), `equipements_proximite_liste` (chaque item porte sa distance).
- **l'emprise scoring n'est jamais servie au client** : l'id `emprise_bati_scoring_m2` ne peut ni être une donnée client du registre, ni sourcer `emprise_batie_m2` ; aucun producteur de fiche/export (`exports/**`, `bilan.py`) ne lit `FROM p_model_bati` (la lecture SQL, pas une mention en commentaire). La donnée client `emprise_batie_m2` doit sourcer le producteur BD TOPO servi.

V6b **vert** : « périmètres « secteur » nommés, emprise scoring cloisonnée, golden 7 témoins rejoués ».

---

## Banc avant / après (notions du mandat)

| notion | avant | après |
|---|---|---|
| `emprise_batie_m2` | **72** | **0** |
| `prix_median_maison_secteur` → `prix_maison_secteur_section_cadastrale` | **96** | **0** |
| **total mandat** | **168** | **0** |

Résidu hors périmètre (caches périmés de la DB partagée, cause `run_different`/`cache_perime`, inchangé par ce mandat, exige un rebuild interdit ici) : ~899 écarts, tous sur les notions vigilances/score/résiduel/zonage/surface — le backlog de fraîcheur connu de COHERENCE-1, jamais les deux notions traitées.

---

## Vérifications

- `verrou_coherence_banc` (V6b) : **ok**.
- pytest ciblés : `test_v6b_coherence`, `test_registre`, `test_circuit2_lot1`, `tests/verrous/`, `test_reparations1_lot2`, `test_exports2_lot2`, `test_coherencefix1_lot_d_absences`, **`test_mode_b` (7/7 — fixture mise à jour : l'emprise mode B vient du CoSIA révélé, plus de la colonne scoring)**.
- Front : `tsc --noEmit` **0**, `vitest run` **225/225**.
- Banc `--echantillon` rejoué : notions du mandat à 0.

## Captures (`captures/`, 3 témoins, 1440 px)

Saint-Denis `97411000BZ1065`, Saint-Pierre `97415000EO0796`, Bras-Panon `97402000AB1117` — `*_1_fiche.png` (fiche + §Bâti) et `*_2_marche.png` (Marché déplié). On y lit « 15 ventes **· section cadastrale** · DVF », la tuile Terrain nu « · section c[adastrale] », les tuiles Maison/Appart « · 1 000 m » (rayon), et la FactNote « médiane locale par type au **rayon adaptatif** ; terrain nu = médiane de la **section cadastrale** ». Les données Étude de zone / Mon secteur sont rendues DANS le bloc Marché (rapatriées par ETUDIER-BIEN-2), donc visibles sur ces mêmes captures. Script rejouable : `captures/_shoot.mjs`.

## Résidu assumé

- `marche.tsx` conserve le libellé front « Prix de sortie — bâti secteur » (fichier FC-2, édits minimaux) : le périmètre est porté par le « i » (« rayon adaptatif ») et par la notion registre renommée. Noté pour un passage ultérieur hors collision FC-2.
