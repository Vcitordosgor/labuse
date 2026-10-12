# Lot 5 — donnée tierce à jour au point de lecture (après).
## D-46 SIRENE DR0219 — AVANT identite.actif=true (SCI cessée)
APRÈS:
actif False | etat C | Société propriétaire : société cessée (état administratif C, mise à jour INSEE 2026-10-12).
## D-47 BODACC FREYNEAU — AVANT « dernière annonce 2024-10-08 » (table gelée)
APRÈS:
Société propriétaire : procédure collective (dernière annonce 2026-08-21).
## C-45 cloche — AVANT dernière bascule q_v10 (août)
APRÈS: detect_events rejoué q_v16->q_v18 = 54 bascules (cloche sur run servi)
## D-54 RPLS — AVANT littéral « 01/01/2025 » (×5)
APRÈS (dérivé table):
['RPLS 01/01/2025', 'RPLS)']
## D-57 PM millésime — AVANT constante _MILLESIME_SERVI=2025 → dérivé max(millesime)
