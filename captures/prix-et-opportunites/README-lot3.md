# Captures AVANT / APRÈS — FIX-PRIX-ET-OPPORTUNITES lot 3 (capacité = maximum réglementaire)

Partout où une capacité constructible (SDP, logements) est affichée, elle est présentée comme le
**maximum réglementaire** avec une mention mesurée du **volet D** : les permis réellement autorisés en
utilisent **en médiane ~la moitié** (ratio médian 0,46 en surface, 0,40 en logements). Point de texte
unique : `src/labuse/capacite_max.py` + `frontend/src/lib/capaciteMax.ts`.

Captures (`png-lot3/`) rendues sans base (blocs d'export purs + page d'étiquettes) :

| Surface | AVANT | APRÈS |
|---|---|---|
| Export « Le programme » (Financier) | `Surface de plancher` / `Logements` nus | `… (maximum)` + note mesurée |
| Export Comparatif | `Logements possibles` | `SDP max estimée` + `Logements possibles (max.)` + note |
| Fiche Constructibilité | `SDP` | `SDP max` + note « maximum réglementaire … ~½ » |
| Outil Gabarit | enveloppe seule | + note courte mesurée |
| Copilote (question capacité) | `SDP résiduelle : ~X` | + « C'est un maximum réglementaire — ~½ utilisé (volet D) » |

Surfaces couvertes dans le code : fiche `constructibilite.tsx`, outil `Gabarit.tsx`, `ComparePanel.tsx`,
exports `financier.py` (programme) / `comparatif.py` / `potentiel.py`, Copilote `resume_fiche.py`.
La capacité n'est **pas** recalculée (lot 2 STOP) — seule sa présentation change.
