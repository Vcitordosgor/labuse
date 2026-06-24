# Audit scoring / produit post-16 — pourquoi le cluster faible-opportunité reste NO-GO en l'état

> **Décision du 2026-06-23 : 🟢 scoring global OK — NO-GO next commune confirmé.**
> Le quasi-0 d'opportunité du cluster est **structurel + limité par la donnée** (couverture PPR, zonage A/N),
> **pas** un bug ni une sévérité arbitraire. On **ne baisse pas le seuil**, on **ne neutralise pas le PPR à
> l'aveugle**. Audit **strictement lecture seule** (aucune ré-cascade, aucune mutation DB/code/config).

## Contexte

| Élément | Valeur |
|---|---|
| `main` | **`cca1093`** |
| Communes **gold** | **16 / 24** |
| Verdict stratégique | **NO-GO next commune** (cf. `POST_16_STRATEGIC_INVENTORY.md`) |
| Cluster audité | **La Plaine-des-Palmistes · Entre-Deux · Les Trois-Bassins · Sainte-Rose** |

## Rappel du modèle de scoring (lecture du code)

- **Score d'opportunité** = `base 50 − Σpénalités + Σbonus + ai_adjustment`, borné [1, 100] ; HARD_EXCLUDE → 0.
- Pénalité = `5 × sévérité` (faible×1 / moyen×2 / **fort×3 = −15**). Bonus (plafonds) : potentiel_foncier 12,
  proprietaire 12, surface 8, zonage_u_au 8, dvf 8, sitadel 8, accès 3.
- **Seuil opportunité = 65** ; complétude floor = 50.
- **`has_fort_flag` BLOQUE `opportunite`** (un seul SOFT_FLAG **fort** suffit, quel que soit le score) — `status.py`.
- Zonage : **A/N ≥ 90 % de recouvrement = HARD_EXCLUDE** ; **N-zone (sans U/AU) = SOFT_FLAG FORT** ; U/AU = bonus +8.
- **PPR : zone rouge = HARD_EXCLUDE ; périmètre PPR (assiette PM1, rouge/bleu inconnu) = SOFT_FLAG FORT** (prudent).

## Tableau de synthèse (dernière éval/parcelle)

| Commune | parcelles | opp | taux | max score | hard-exclude | **PPR fort** | U/AU constr. | Bloqueur dominant |
|---|---|---|---|---|---|---|---|---|
| **La Plaine-des-P.** | 6 450 | **0** | 0,00 % | **53** | 2 104 (33 %) | **6 450 (100 %)** | 4 454 (69 %) | PPR périmètre **100 %** + zonage A/N (1 996) |
| **Les Trois-Bassins** | 5 314 | 1 | 0,02 % | 77 | 2 179 (41 %) | **5 260 (99 %)** | 3 213 (60 %) | PPR 99 % + zonage A/N (2 101) |
| **Sainte-Rose** | 6 287 | 8 | 0,13 % | 70 | 2 838 (45 %) | 3 029 (48 %) | 3 498 (56 %) | zonage A/N (2 789) + parc (531) + PPR |
| **Entre-Deux** | 6 312 | 9 | 0,14 % | 69 | 761 (12 %) | 0 | 3 319 (53 %) | **N-zone fort** (1 849) + parc (611) + forêt (311) |
| _Saint-André (gold)_ | 22 600 | 54 | 0,24 % | 79 | 2 394 (11 %) | 20 900 (92,5 %) | 20 221 (89 %) | _repère_ |
| _Saint-Denis (gold)_ | 38 138 | 84 | 0,22 % | 72 | 4 950 (13 %) | — | — | _repère_ |

## Diagnostic

- **PPR périmètre = driver principal.** La couche `risques` pose un **SOFT_FLAG FORT** sur toute l'assiette
  PPR approuvée → pénalité −15 **et** blocage `opportunite` (`has_fort_flag`). À La Réunion l'assiette PPR
  couvre presque tout.
- **La Plaine** : **PPR 100 %** des parcelles → **0 parcelle hors PPR** → **0 opportunité, max 53** (structurel).
- **Les Trois-Bassins** : **PPR 99 %** + zonage A/N massif (2 101 hard-exclude) → **1 opportunité**.
- **Sainte-Rose** : zonage A/N (2 789) + parc (531) + PPR 48 % → **8 opportunités** (volcanique, très contrainte).
- **Entre-Deux** : pas de PPR-blanket, mais **N-zone fort** (1 849) + parc (611) + forêt (311) → **9 opportunités**.
- **Comparaison gold (Saint-André / Saint-Denis)** : **mêmes règles** (Saint-André a aussi 92,5 % de PPR fort),
  mais il leur reste des **poches hors PPR** (~7,5 % à Saint-André, ~1 700 parcelles) d'où viennent les
  opportunités. La Plaine / Trois-Bassins n'ont **aucune** poche hors PPR → 0.
- **Bonus manquants (donnée, pas règle)** : `proprietaire` (+12) = **0 partout, gold compris** (Fichiers
  Fonciers non branchés) ; `sitadel` = 0. U/AU, surface, DVF sont bien servis (comparable au gold) → le
  déficit n'est **pas** un manque de bonus propre au cluster.

## Simulations (lecture seule, bornes — aucune ré-cascade)

| Scénario | La Plaine | Trois-Bassins | Sainte-Rose | Entre-Deux | Lecture |
|---|---|---|---|---|---|
| **Seuil 65 → 60** | 0 | 0 | +27 | +41 | aide les **non-PPR** ; **nul** sur les PPR-saturées ; **baisse le seuil gold global** (risqué) |
| **PPR fort → moyen (+5)** | 0 | +9 | 0 | 0 | quasi inutile (scores trop bas) |
| **PPR retiré du blocage (+15, borne haute)** | +12 | **+32** | +3 | 0 | **suppose tout bleu** — surfacerait des parcelles potentiellement **ROUGES** (dangereux) |

**Conclusion des simulations** : seul le levier **PPR** débloque vraiment quelque chose (surtout Les
Trois-Bassins, ~+32), **mais le faire à l'aveugle est dangereux** sans distinguer le PPR **rouge/bleu** (on
n'a que le périmètre). Baisser le seuil n'aide que les non-PPR et dégrade la qualité gold globale.

## Décision

- ❌ **Ne pas baisser le seuil global** (dégrade la qualité gold, surfacerait des zones N/relief).
- ❌ **Ne pas neutraliser le PPR à l'aveugle** (surfacerait des parcelles en PPR rouge non constructibles).
- ❌ **Pas de ré-cascade, pas de passage gold.**
- ✅ **Documenter NO-GO en l'état** pour le cluster.

## Recommandation

- **Scoring OK en l'état** : ni bug, ni sévérité arbitraire ; le quasi-0 est **structurel** (PPR total,
  zonage A/N, parc/relief/volcan) **+ limite de granularité de données** (PPR périmètre sans rouge/bleu).
- **Chantier éventuel = DONNÉE, pas pondération** : ingérer le **zonage PPR rouge/bleu** (Géorisques) pour que
  `risques` ne flague fort **que sur le rouge** (bleu → moyen/pass). C'est la **seule** voie de récupération
  saine (débloque le bleu sans exposer le rouge).
- **Meilleur candidat si chantier PPR : Les Trois-Bassins** (~32 parcelles U/AU sous périmètre PPR,
  débloquables si bleu).
- **Secondaire (plus tard)** : brancher **Fichiers Fonciers** (bonus `proprietaire` +12, uplift universel) et
  **SITADEL** — utiles partout, pas spécifiques au cluster.
- **La Plaine-des-Palmistes / Sainte-Rose / Entre-Deux restent NO-GO durable en l'état** (contraintes réelles ;
  même les scénarios les plus généreux ne rendent que 0–12 parcelles marginales).

**On ne relance une commune qu'APRÈS** un éventuel chantier data (PPR rouge/bleu), **jamais** en abaissant le seuil.

---

### Provenance (lecture seule)

- Code : `config/opportunity_weights.yaml`, `config/cascade_rules.yaml`, `scoring/{opportunity,status,declassement}.py`,
  `cascade/layers/{phase1,phase2}.py`.
- DB (SELECT only) : `parcel_evaluations` (status, score, complétude — dernière éval/parcelle) et
  `cascade_results` (verdicts par couche — dernière passe/parcelle). Aucune écriture, aucune ré-cascade.
