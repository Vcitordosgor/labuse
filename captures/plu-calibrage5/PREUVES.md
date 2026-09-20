# PLU-CALIBRAGE-5 — PREUVES

## Chiffres avant / après

Au départ (main 65cd0aa2) : **419 propose**, 1563 valide. Après les 4 lots : **150 propose**, **1832 valide**.
**269 règles propose résolues** (−64 %).

| famille (au tri) | départ | validées | reste propose | note |
| --- | --- | --- | --- | --- |
| B — écarts / attributions | 335 | 160 (v 103 · corr 41 · abs 16) | 80 | 100 reclassées formule → lot 3 ; 5 « à l'alignement » refusées (garde) |
| A — formules de recul | 43 (+100 reclassées) | 73 (formule + min_m encodés) | 19+51 | barèmes stationnement + pleine-terre conditionnelle restent propose |
| C — citation non retrouvée | 41 | 41 | 0 | toutes retrouvées (renvois 1AU→U) |
| **total** | **419** | **274** | **150** | |

## V6a — aucune règle validée sans sa preuve

**1832 règles validées · 0 sans article + page + citation.** Toute valeur validée par ce
mandat porte sa source (article, page PDF, citation retenue) ; chaque décision a été soumise à une
garde anti-invention (le nombre doit être LITTÉRAL dans la preuve) et à une contre-vérification de
la preuve contre le PDF (0 fabrication sur l'ensemble des lots).

## Une étape passe d'ESTIMÉ à SOURCÉ — parcelle 97410000AB0003 (Saint-Benoît, zone Ub)

L'emprise au sol 80 % de la zone Ub était `propose` (ignorée du calcul) ; le lot 2 l'a validée
(« L'emprise au sol des constructions ne peut excéder 80 % du terrain », Art. U 5, p.10).

| étape « Emprise au sol — % réglementé » | AVANT (main) | APRÈS (ce mandat) |
| --- | --- | --- |
| valeur | — | ~643 m² |
| source | Art. 9 | **Art. U 5 · p.10 (PLU, calibrage validé)** |

L'étape passe d'ESTIMÉE (aucune règle d'emprise appliquée) à SOURCÉE (80 % lu au règlement). Même
capture complète avant/après : `captures/plu-calibrage5/fiche_estime_vers_source.json`.
