# La Plaine-des-Palmistes — résultats import gold standard (2026-06-22T21:06:59)

- **Commune / INSEE** : La Plaine-des-Palmistes / 97406
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 6450 → **6450**
- Sections : **18**
- Bâti (couche) : 0 → **7618**
- Évaluées : **6450 / 6450** (100 %)

## Couches

- batiment : 7618
- voirie : 3178
- pente : 5146
- plu_gpu_zone : 340
- ppr : 2
- sar : 133
- ravine : 504
- plu_gpu_prescription : 986
- osm_faux_positif : 103
- abf : absent

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **0**
- À creuser : **2013**
- Écartée : **415**
- Faux positif probable : **4022**
- Taux d'opportunité : **0.0 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 0

## Temps d'exécution

- parcelles : 14s
- couches : 133s
- cascade : 463s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (6450) — 6450 (min 6450)
- ✓ OK   sections présentes — 18
- ✓ OK  [critique] 0 doublon IDU — 6450/6450
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 6450/6450
- ✓ OK  [critique] bâti présent (> 0) — 7618
- ✓ OK  [critique] zonage PLU présent — 340
- ✓ OK  [critique] pente présente — 5146
- ✓ OK  [critique] voirie présente — 3178
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 133 features
- ✓ OK   ravine : complet — 504 features
- ✓ OK   plu_gpu_prescription : complet — 986 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 6450/6450
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.0 % (None opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Notes & point de vigilance

- **Voirie 3 178 — garde adaptée (type Le Port) VALIDÉE** : `voirie > 0` ✓, `voirie != 5000` ✓, aucune chute vs pré-vol (3 178 → 3 178, drop 0). **Non tronquée** : 3 178 < 5000 (page_size WFS) ⟹ première page incomplète ⟹ page unique complète ; **aucun warning « voirie tronquée »** (garde-fou `max_total=60000` non atteint). La garde standard `> 5000` n'a délibérément PAS été exigée (petite commune de montagne).
- **Zonage — 100 % total ET 100 % propre** : couverture réelle 6 450/6 450 (100 %) **et** couverture par le PLU propre `DU_97406` (idurba `97406_PLU_20230527`) = 6 450/6 450 (**100 %**). Jamais jugé sur `plu_gpu_zone > 0`.
- **DVF présent — 271 mutations** : bascule de l'ancien flux ODS (736) vers **geo-dvf Etalab** (fenêtre 5 ans, 2021-01-19 → 2025-12-19). Non-critique, conservé/présent.
- **⚠️ Point de vigilance — 0 opportunité** (104 → 0) : le bâti 7 618 réactive les faux positifs (`faux_positif_probable` 4 022) ; le reste bascule en « à creuser » (2 013) / « écartée » (415). Garde QA passée (0,0 % = non explosif), mais **seul cas à 0 opp** parmi les communes traitées → **à arbitrer explicitement AVANT tout passage gold**.
- ℹ️ **Évaluations stale ×2** (12 900 lignes / 6 450 parcelles) : 2ᵉ jeu ajouté par le cascade sans suppression de l'ancien (ex-`partiel_evalue`) ; verdicts canoniques = dernière éval/parcelle → impact fonctionnel nul. Non nettoyé (hors périmètre).

## Conclusion : SUCCÈS technique (exit 0, tous les contrôles verts) — passage gold NON décidé à ce stade : arbitrer d'abord le point de vigilance « 0 opportunité ».

