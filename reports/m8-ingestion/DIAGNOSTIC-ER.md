# M8 — DIAGNOSTIC ER : le mapping `typepsc→ER` calibré Saint-Paul appliqué aux 24 communes

**Date** : 2026-07-14 · **Branche** : `feat/m8-ingestion` · **Run servi** : `q_v5_m6b` (PAS de re-run) · **Modèle P M3.6 GELÉ**.

⚠️ **DIAGNOSTIC, LECTURE SEULE.** Aucune modif de `config/cascade_rules.yaml` ni de code. Que des SELECT + GPU en lecture.
Ce document CHIFFRE les dégâts et propose un mapping. **Vic décide. STOP après le rapport, pas de fix.**

---

## 0. Méthode & travail existant réutilisé (Lot 0)

**Logique ER en place** (`src/labuse/cascade/layers/phase1.py:353-423`, `PrescriptionPluLayer`) :
pour chaque prescription intersectant la parcelle, matching **par code `typepsc` (= `spatial_layers.subtype`)** :
- `subtype ∈ emplacement_reserve_typepsc` (`["05"]`) → recouvrement (par feature, aire∩/aire parcelle, **en 2975**)
  ≥ `er_hard_exclude_pct` (**50 %, PLACEHOLDER**) → **HARD_EXCLUDE** `faux_positif` ; sinon → **SOFT_FLAG** (surface ER déduite).
- `∈ ["01"]` → EBC (SOFT_FLAG fort) · `∈ ["07"]` → patrimoine L151-19 (SOFT_FLAG moyen) · `16/17` mixité, `18` OAP, `48` eaux → PASS.
- **`else` (code non mappé) → SOFT_FLAG FAIBLE « Prescription PLU … à vérifier »** (le fallthrough qui « avale » les ER mal codés).

**Config auditée** (`config/cascade_rules.yaml:96-105`) : `emplacement_reserve_typepsc: ["05"]`, `boise_classe_typepsc: ["01"]`,
`patrimoine_bati_typepsc: ["07"]`, `er_hard_exclude_pct: 50`. Le commentaire dit explicitement **« CALIBRÉ sur … Saint-Paul »**.

**Existant réutilisé (non refait)** :
- `RAPPORT_DECISIONS_1_4.md` §D3.a + `ANNEXE_REVUE_AN_ER.md` : la logique ER (D3.a) a été **calibrée sur les 3 000
  parcelles de Saint-Paul seul** ; les 10 ER-HARD témoins sont **tous 97415**, **9/10 déjà faux positifs** par d'autres
  signaux, seuil 50 % = **PLACEHOLDER** validé « ne frappe que des emprises massivement grevées » (sur SP). → **je ne
  re-justifie pas le seuil ni ne le déplace** (aucune donnée hors-SP pour le recalibrer ici ; cf. §5).
- `tests/test_decisions_1_3.py:33-36,143-156` : fige le mapping SP (`["05"]`) et le format de motif. **Tout changement de
  mapping fera évoluer ces tests** — à intégrer au futur fix.

**Reproduction de l'état servi** : les verdicts cascade **ne sont PAS persistés** (recomputés à la volée ; `parcel_source_results`
= fetch par source, aucune ligne ER ; témoin `97415000BO0376` absent). L'« état servi » est donc **reproduit en PostGIS**
avec la **formule EXACTE de la cascade** (`ST_Area(ST_Intersection(p.geom_2975, sl.geom_2975)) / ST_Area(p.geom_2975)`,
recouvrement **par feature**). Comme les couches spatiales n'ont pas bougé depuis le run (aucune ré-ingestion M8),
cette reproduction = l'état servi `q_v5_m6b`.

---

## 1. SYNTHÈSE EXÉCUTIVE — les 3 chiffres

| # | Dégât | Chiffre (borne haute de l'effet propre*) | Où |
|---|-------|------|-----|
| **(1)** | **FAUSSES OPPORTUNITÉS** (ER non captés → jamais exclus) | **60 parcelles** (+ 55 en soft) chiffrées, **+ trou non chiffrable** | Saint-Louis (ER codés `02`) ; + Saint-André & Saint-Leu (0 prescription ingérée) |
| **(2)** | **FAUSSES ÉCARTÉES** (non-ER sous code `05` → HARD_EXCLUDE injustifié) | **16 parcelles** | Sainte-Marie 9 (périmètre d'attente L.151-41) + Saint-Benoît 7 (corridors écologiques) |
| **(3)** | **Ma reco de mapping** | **Hybride per-commune (code vérifié) + garde par libellé** (rescue ER mal codés / veto non-ER sous 05). PAS « libellé seul ». Seuil 50 % conservé. | §5 |

\* Borne haute : le HARD_EXCLUDE ER produit un `faux_positif` ; certaines de ces parcelles sont déjà écartées par d'autres
signaux. Le chiffre isole l'effet **propre au mapping ER**, pas le net sur le tier final.

**Contexte servi (référence)** : la couche ER (code `05`, seuil 50 %) produit aujourd'hui **~5 221 HARD_EXCLUDE** et
**~31 785 SOFT_FLAG** sur l'île. Les deux dégâts ci-dessus sont donc **petits en volume** — mais **ciblés et corrigibles**,
et le trou d'ingestion (SA/SL) est **structurel**.

> **Nuance qui recadre la crainte initiale** : dans les données **servies** (21 communes ingérées), les codes sont
> **bien plus cohérents** que redouté — **ER = `05` sur 20/21 communes, EBC = `01` partout, patrimoine = `07`**.
> Le mapping global `["05"]` n'est donc **pas** une catastrophe généralisée. MAIS il est **faux par principe** (un code
> global calibré sur une commune ne peut pas être universel — preuve : `02`=ER à Saint-Louis mais `02`=« secteur
> environnemental » à Bras-Panon → un simple `["05","02"]` créerait de NOUVELLES fausses écartées). Le fix doit être
> **per-commune + garde libellé**, pas un élargissement de liste globale.

---

## 2. LOT 1 — État servi ER (reproduit sur `q_v5_m6b`, par commune)

Parcelles dont le recouvrement max par une prescription **code `05`** atteint le seuil.

| Commune | ER hard (≥50 %) | ER soft (<50 %) |
|---|--:|--:|
| Saint-Denis | 1 843 | 9 054 |
| Saint-Pierre | 779 | 6 142 |
| Le Tampon | 445 | 2 225 |
| Saint-Paul | 367 | 2 060 |
| Saint-Louis | 276 | 3 058 |
| Le Port | 205 | 646 |
| Saint-Joseph | 180 | 1 453 |
| La Possession | 179 | 392 |
| La Plaine-des-Palmistes | 129 | 558 |
| Salazie | 114 | 864 |
| Sainte-Suzanne | 113 | 393 |
| Saint-Benoît | 109 | 613 |
| Cilaos | 96 | 1 336 |
| Les Avirons | 85 | 215 |
| Les Trois-Bassins | 79 | 785 |
| Entre-Deux | 76 | 1 336 |
| Bras-Panon | 65 | 336 |
| Sainte-Marie | 56 | 151 |
| L'Étang-Salé | 22 | 154 |
| Sainte-Rose | 3 | 10 |
| Petite-Île | 0 | 4 |
| **ÎLE** | **~5 221** | **~31 785** |
| Saint-André · Saint-Leu · Saint-Philippe | **— (0 prescription ingérée)** | — |

---

## 3. LOT 2 — Le VRAI mapping par commune (classé par LIBELLÉ, pas par code)

Source : inventaire `spatial_layers.kind='plu_gpu_prescription'` (base = ce que le run servi a lu), libellés classés par regex.

| Commune | ER (code:features) | EBC | Patrimoine | Anomalie |
|---|---|---|---|---|
| Bras-Panon | 05 : 50 | 01 : 53 | 07 : 33 | — |
| Cilaos | 05 : 98 | 01 : 63 | 07 : 20 | — |
| Entre-Deux | 05 : 212 | 01 : 101 | 07 : 121 | libellé **« Empalcement réservé » (typo)** ×149 |
| L'Étang-Salé | 05 : 15 | 01 : 30 | — | libellé ER = **numéro nu** (« 11 », « 7 »…) |
| La Plaine-des-Palmistes | 05 : 61 | 01 : 87 | — | — |
| La Possession | 05 : 53 | 01 : 8 | — | — |
| Le Port | 05 : 24 | 01 : 28 | 07 : 48 | — |
| Le Tampon | 05 : 158 | 01 : 41 | 07 : 82 | — |
| Les Avirons | 05 : 25 | 01 : 57 | 07 : 7 | — |
| Les Trois-Bassins | 05 : 41 | 01 : 122 | — | — |
| Petite-Île | — | — | 07 : 4 | **aucun ER/EBC vectorisé** (cf. recon Lot 1) |
| Saint-Benoît | 05 : 62 | 01 : 170 | — | **05 porte 6 « corridors éco » + 1 « périmètre projet » (non-ER)** |
| Saint-Denis | 05 : 493 | 01 : 405 | 07 : 1 978 | 07 = « SPR - Front végétalisé » (patrimoine, OK) |
| Saint-Joseph | 05 : 157 | 01 : 62 | — | — |
| **Saint-Louis** | **05 : 158 + `02` : 6** | 01 : 75 | — | **6 ER codés `02`** (fausses opportunités) ; GPU retiré |
| Saint-Paul | 05 : 155 | 01 : 12 | — | commune de calibrage |
| Saint-Pierre | 05 : 346 | 01 : 58 | — | — |
| Sainte-Marie | 05 : 15 | 01 : 221 | 07 : 11 | **05 porte 1 « périmètre d'attente L.151-41 » (non-ER)** |
| Sainte-Rose | 05 : 2 | 01 : 2 | — | — |
| Sainte-Suzanne | 05 : 27 | 01 : 50 | — | — |
| Salazie | 05 : 90 | 01 : 137 | 07 : 79 | — |
| **Saint-André / Saint-Leu / Saint-Philippe** | **0 / 0 / 0** | 0 | 0 | **aucune prescription ingérée** (AGORAH / RNU) |

**Lecture** : le mapping SP (`ER=05, EBC=01, patrim=07`) est **exact pour la quasi-totalité des communes servies**.
Les seules déviations : Saint-Louis (`02`), + surcharges de `05` par du non-ER à Saint-Benoît/Sainte-Marie,
+ pièges de libellé (typo, numéros nus) qui **n'affectent pas le code** mais **piégeraient un matching libellé naïf**.

---

## 4. LOT 3 — Les deux dégâts, chiffrés

### 4.1 FAUSSES OPPORTUNITÉS (chiffre (1) = 60)
ER réels non captés par `["05"]` → tombent dans le **fallthrough SOFT_FLAG faible**, aucune exclusion.

| Cause | Commune | Détail | Parcelles ≥50 % (manquées) | + soft |
|---|---|---|--:|--:|
| ER sous code `02` | **Saint-Louis** | 6 features « Emplacement réservé » codées `02` | **60** | 55 |
| **Trou d'ingestion** | **Saint-André, Saint-Leu** | **0 prescription ingérée** (zonage AGORAH sans annexes ; GPU vide) → **100 % des ER de ces communes sont invisibles** | **non chiffrable** | — |
| (Saint-Philippe RNU) | — | pas de PLU → sans objet | 0 | — |

→ **60 parcelles chiffrées** + un **trou structurel** à Saint-André/Saint-Leu (le plus gros gisement d'ER manqués,
mais **aucune géométrie ER n'existe en base ni au GPU** pour le mesurer — c'est une lacune d'**ingestion**, pas de mapping).
Note : Saint-Louis a son doc **GPU retiré** (cf. recon Lot 1) — les `02` viennent d'une ingestion antérieure conservée en base.

### 4.2 FAUSSES ÉCARTÉES (chiffre (2) = 16)
Features **non-ER codées `05`** couvrant ≥50 % → **HARD_EXCLUDE `faux_positif` injustifié**.

| Commune | Libellé (réel, code `05`) | Parcelles exclues à tort (≥50 %) | Gravité |
|---|---|--:|---|
| Sainte-Marie | « Périmètre d'attente de projet d'aménagement global (art. L.151-41 5°) » | **9** | ⚠ mislabel : c'est un **PAPA** (gel ~5 ans, régime distinct), pas un ER — mais **gèle réellement** la constructibilité |
| Saint-Benoît | « Corridors écologiques protégés » | **7** | ⛔ **erreur nette** : corridor écologique = contrainte environnementale (SOFT_FLAG), **jamais** une exclusion « projet public » |
| **Total** | | **16** | dont **7 clairement fausses**, 9 mal-étiquetées mais réellement contraintes |

Non retenu (vérifié, 0 impact ≥50 %) : « Perimetre de projet » Saint-Benoît (1 feature). Entre-Deux (typo « Empalcement »)
et L'Étang-Salé (numéros nus) = **bien des ER** sous `05` → **correctement** exclus (le code les rattrape).

---

## 5. RECOMMANDATION — mapping robuste (chiffre (3))

Le fix N'EST PAS « passer au libellé » (les typos « Empalcement », numéros nus et variantes de casse feraient **rater
149+15+… ER**). Ce n'est pas non plus « élargir la liste de codes » (`02` = ER à Saint-Louis mais ≠ ER ailleurs).
Reco = **hybride, code per-commune + garde par libellé** :

1. **Mapping `typepsc` PER-COMMUNE** (pas global). Défaut `ER=["05"], EBC=["01"], PATRIM=["07"]` (exact pour ~20 communes),
   **override Saint-Louis : `ER=["05","02"]`**. Structure config par `commune`/`insee` (le socle cascade lit déjà `commune`).
2. **RESCUE par libellé (typo-tolérant)** : toute prescription dont le libellé matche
   `emp[al]{1,4}cement\s*r[ée]serv | emplacement\s*r[ée]serv | \bER\s*n?°?\s*\d` → traitée **comme ER quel que soit le code**.
   Rattrape Saint-Louis `02` et tout futur mauvais code, **sans** dépendre d'une liste exhaustive.
3. **VETO par libellé** : une feature ER-par-code (`05`) dont le libellé indique **positivement un non-ER**
   (`corridor | continuité écolo | périmètre de projet | périmètre d'attente | L\.?151-?41 | espace boisé | réservoir`)
   → **ne PAS** hard-exclure ; router vers sa vraie famille (corridor→env SOFT_FLAG ; PAPA→flag « périmètre d'attente »).
   Corrige les 16 fausses écartées (dont L.151-41 → flag dédié plutôt qu'exclusion « ER »).
4. **Numéros nus / libellés vides sous `05`** (L'Étang-Salé) : **conserver ER** (comportement actuel) mais **loguer**
   pour revue data — ne pas les traiter en non-ER par défaut.
5. **Seuil `er_hard_exclude_pct: 50` : CONSERVER en l'état.** Aucune donnée hors Saint-Paul ne justifie de le bouger ici
   (les témoins SP ER-hard étaient à ~100 %). Reste un **PLACEHOLDER** à valider visuellement par Vic (cf. `ANNEXE_REVUE_AN_ER.md`).
6. **Trou d'ingestion Saint-André / Saint-Leu** : hors périmètre mapping — dépend de l'arbitrage **source ER hors-GPU**
   (AGORAH ne sert pas les prescriptions). À traiter dans la vague ingestion, pas dans le fix mapping.
7. **Tests** : `tests/test_decisions_1_3.py` fige `["05"]` — le fix devra ajouter des cas rescue (ER `02`) + veto (corridor `05`).

**Impact attendu du fix** (borne haute) : **+60 parcelles** correctement exclues (Saint-Louis), **−16** ré-admises
(Sainte-Marie/Saint-Benoît), + robustesse future (rescue/veto). Le trou SA/SL reste ouvert jusqu'à l'ingestion ER.

---

## 6. Ce qui n'est PAS le problème (pour éviter un sur-fix)

- **Les codes ne sont pas « anarchiques »** dans les données servies : `05`/`01`/`07` tiennent sur 20/21 communes.
- **EBC (`01`) et patrimoine (`07`) = sains** — aucun EBC détecté sous un autre code, aucun non-EBC sous `01`.
  (Saint-Denis `07`×1978 « SPR - Front végétalisé » = bien du patrimoine → SOFT_FLAG correct, pas un bug.)
- Le `07`-comme-ER redouté **n'existe pas** en base (0 commune n'a d'ER sous `07`). Donc **pas** de fausses écartées via `07`
  (et de toute façon `07`→patrimoine ne produit qu'un SOFT_FLAG, jamais un HARD_EXCLUDE).

---

*Fin du diagnostic. Rien corrigé. STOP — en attente de la décision de Vic sur le mapping.*
