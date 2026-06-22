# Le Port — résultats import gold standard (2026-06-22T14:33:18)

- **Commune / INSEE** : Le Port / 97407
- **Stratégie appliquée** : re_couches_re_cascade
- **Verdict** : SUCCÈS — commune prête au standard Saint-Paul (code de sortie 0)

## État avant → après

- Parcelles : 10195 → **10195**
- Sections : **26**
- Bâti (couche) : 0 → **15828**
- Évaluées : **10195 / 10195** (100 %)

## Couches

- batiment : 15828
- voirie : 4897
- pente : 768
- plu_gpu_zone : 159
- ppr : 2
- sar : 84
- ravine : 66
- plu_gpu_prescription : 218
- osm_faux_positif : 516
- abf : 1

- Couverture zonage PLU : **100.0 %**
- Duplication de couches : 0 groupe(s)
- Index GIST présents : 3/3

## Verdicts & opportunités

- Opportunité : **74**
- À creuser : **2281**
- Écartée : **912**
- Faux positif probable : **6928**
- Taux d'opportunité : **0.7 %** (repère Saint-Paul ≈ 1 % ; seuil QA ≤ 5 %)
- Micro-opportunités (251–500 m²) : 2

## Temps d'exécution

- parcelles : 25s
- couches : 177s
- cascade : 209s

## Contrôles

- ✓ OK  [critique] parcelles ≥ attendu (10195) — 10195 (min 10195)
- ✓ OK   sections présentes — 26
- ✓ OK  [critique] 0 doublon IDU — 10195/10195
- ✓ OK  [critique] 0 géométrie invalide — 0
- ✓ OK  [critique] 100 % geom_2975 — nuls : 0
- ✓ OK  [critique] 100 % évaluées — 10195/10195
- ✓ OK  [critique] bâti présent (> 0) — 15828
- ✓ OK  [critique] zonage PLU présent — 159
- ✓ OK  [critique] pente présente — 768
- ✓ OK  [critique] voirie présente — 4897
- ✓ OK  [critique] couverture zonage ≥ 99 % — 100.0 %
- ✓ OK  [critique] aucune duplication de couche — 0 groupes (kind,géom) dupliqués
- ✓ OK   ppr : complet — 2 features
- ✓ OK   sar : complet — 84 features
- ✓ OK   ravine : complet — 66 features
- ✓ OK   plu_gpu_prescription : complet — 218 features
- ✓ OK  [critique] index GIST présents — tous
- ✓ OK  [critique] verdicts cohérents (Σ = évaluées) — 10195/10195
- ✓ OK  [QA] taux d'opportunité non explosif (≤ 5 %) — 0.7 % (74 opp)
- ✓ OK  [critique] pipeline conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] feedback conservé (≥ avant) — 0 → 0
- ✓ OK  [critique] alertes conservé (≥ avant) — 0 → 0

## Notes (Le Port)

- **Backup pré-commune** : `/var/backups/labuse/labuse-pre-le-port-20260622-140616.dump` (sha256 `e6a2503e78c52298a67268d64f77e58503c4a7b7d3b17950fea76487c1420213`).
- **Voirie 4 897 — NON tronquée** : Le Port (plus petit territoire de La Réunion) a `< 5000` voies ; le re-fetch paginé a confirmé **4 897** (= pré-vol), première page WFS complète. Garde adaptée « voirie > 0 et ≠ 5000 » validée (pas de plafond 5 000).
- **DVF re-fetché** : l'ingestion DVF du run a échoué (erreur transitoire) → 0 ligne ; un re-fetch ciblé a restauré **526 mutations** (Le Port n'est plus la seule commune sans DVF). Aucune re-cascade.
- **Faux positif dédup corrigé** : le run sortait exit 1 sur « aucune duplication de couche » à cause de **deux prescriptions GPU distinctes superposées** (OAP sectorielle subtype 18 + règle de mixité logement subtype 37, même surface « Ex ZI sud »). La clé de détection des doublons a été enrichie (`kind, géom, subtype, name, attrs`) → ces objets distincts ne sont plus comptés comme doublon, **sans suppression de donnée** ; les vrais doublons exacts (Saint-Denis/Saint-Joseph) restent détectés.
- **Lignes d'évaluation « stale »** : Le Port était `partiel_evalue` (verdicts ×2, dernière éval/parcelle faisant foi) ; non nettoyées (hors périmètre).

## Conclusion : SUCCÈS — commune prête au standard (peut être marquée gold)

