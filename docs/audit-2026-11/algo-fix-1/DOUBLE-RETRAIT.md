# ALGO-FIX-1 — double retrait : EXPOSITION BRUTE À EXAMINER (pas une mesure d'impact)

Chemin de repli `residuel_legacy` : **53923 parcelles** au run servi q_v20.
Échantillon mesuré : **1500** (tirage md5 reproductible).

**Ce que ce fichier mesure (et ne mesure PAS).** On mesure un **chevauchement brut** : `plu_gpu_prescription` ∩ `ppr/INTERDICTION` à l'intérieur de la parcelle > 5 m². Ce n'est PAS la population effectivement affectée par le défaut (avis Astra passe-3 §4) : (1) il prend TOUTES les prescriptions, sans filtre des sous-types ER/EBC que le moteur applique ; (2) il mesure sur la parcelle entière, sans reculs ni restriction à l'assiette U/AU du repli ; (3) il ne compare pas l'emprise de l'ancien calcul à celle d'une union correcte, et ne propage rien jusqu'à C et R. C'est donc une **exposition à examiner**, un majorant — pas « parcelles touchées » ni « faux zéros imputables ».

| Catégorie de R | Effectif échantillon | Exposées (> 0) | Chevauchement > 5 m² |
|---|---:|---:|---:|
| R > 0 (capacité servie positive) | 1163 | 110 | 101 |
| R = 0 | 337 | 34 | 30 |
| R absent (NULL) | 0 | 0 | 0 |
| **Total** | 1500 | 144 | 131 |

- Chevauchement brut dans l'échantillon : **8.7 %** → extrapolation île ≈ **4709** parcelles legacy exposées (à examiner, pas « touchées »).
- Surface de chevauchement brut (cas > seuil) : médiane **261 m²**, max **156430 m²**.
- Les **30 cas R = 0** exposés sont des **candidats à examiner** (le double retrait a pu vider une assiette réelle), SANS reclassement automatique. Les cas **R absent (NULL)** sont comptés à part — ce ne sont pas des zéros.

## Mesure d'impact réelle → RESIDUEL-2

La mesure d'impact (emprise selon l'ancien calcul vs emprise avec union globale des contraintes ; C avant/après ; E inchangé ; R avant/après ; en séparant augmentation géométrique, capacité inchangée après plafonds, et résiduel redevenu positif ; contraintes hors PPR incluses) exige de rejouer le moteur de faisabilité sur l'assiette exacte avec ses filtres/unités/sources. Elle est **renvoyée à RESIDUEL-2** (correctif amont au niveau du moteur). En attendant, la V2 **isole** ces capacités non qualifiées en « À vérifier » (P1a), par scénario (R en conservation, C en reconstruction).
