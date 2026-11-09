# ALGO-FIX-1 (P3) — mesure du double retrait des contraintes superposées

Chemin de repli `residuel_legacy` : **53923 parcelles** au run servi q_v20.
Échantillon mesuré : **1500** (tirage md5 reproductible).

« Touchée » = prescription (ER/EBC) ∩ PPR rouge (INTERDICTION) à l'intérieur de la parcelle > 5 m² (surface doublement soustraite par db.py:629 puis 638).

| | Estimés (capacité servie > 0) | Zéros (capacité servie = 0) | Total |
|---|---:|---:|---:|
| Exposées (chevauchement > 0) | 110 | 34 | 144 |
| **Touchées (> 5 m²)** | 101 | 30 | 131 |

- Taux de parcelles touchées dans l'échantillon : **8.7 %** → extrapolation île ≈ **4709** parcelles legacy touchées (estimés ET zéros compris).
- Surface doublement soustraite (parcelles touchées) : médiane **261 m²**, max **156430 m²**.
- **Faux zéros potentiels** : les **30** parcelles touchées dont la capacité servie est nulle — la double soustraction peut avoir vidé une assiette réelle. À examiner SANS reclassement automatique (avis Astra §2).

Méthode : chevauchement mesuré entre `plu_gpu_prescription` (ER+EBC) et `ppr/INTERDICTION` (zone rouge) clippé sur la parcelle. C'est un **majorant** du seul chevauchement EBC∩PPR (les prescriptions incluent ER). La correction de fond (union globale ou soustractions successives sur le reliquat) est un geste au niveau du moteur `db.py`, hors de ce mandat isolé ; la V2 marque entre-temps ces capacités « À vérifier » (P3).
