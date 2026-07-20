# Note doctrine — challenger `q_v6_m8_Vdefisc` : ΔRR N'EST PAS le critère

**Accompagne** `reports/arene/20260720_q_v6_m8_Vdefisc.md`. Exception documentée **explicitement** (jamais
implicite), conformément à la doctrine inscrite dans `docs/mandats/PHASE0_BILAN.md`.

## Pourquoi l'arène rejette — et pourquoi ce n'est PAS un échec

Le challenger porte la composante **V « fenêtre de sortie de défiscalisation »**, un signal à **horizon
forward** : il prédit des mutations **2026-2028**. L'arène juge le classement contre les mutations
**réalisées ~2025** (label M3.6). Les deux sont **temporellement orthogonaux** : un signal forward correct
remonte dans le classement des parcelles qui, à raison, **n'ont pas encore muté** → l'arène RR ne peut, par
construction, pas les récompenser. L'AVIS `REJETÉ` (ΔRR IC95 apparié [-0,80 ; +0,91], non significatif) est
donc **attendu** et **ne juge pas** ce signal.

**Le juge de victoire est le walk-forward dédié** (volet 1, `scripts/a1_walkforward.py`) : maison/mono en
fenêtre de sortie → mutation **≈ 2,4× plus** qu'hors fenêtre (OR 2,43 IC95 [1,49 ; 4,34], seed 974, direction
positive sur les 5 folds 2021-2025). **CRITÈRE PASSÉ.** C'est lui qui valide la composante V, pas le ΔRR.

## Ce que l'arène VALIDE ici (son rôle de garde-fou)

L'arène reste le **portier obligatoire**. Sur ce challenger, tous les axes de garde-fou passent :

| Dimension | Résultat | Verdict |
|---|---|---|
| **Gate boussole — 3 axes** (tier · statut cascade · matrice Q×A) | **0 / 64** | ✅ aucun faux positif servi |
| **ECE** (calibration) | 0,0167 → 0,0167 · Δ = −0,0000 | ✅ non dégradée |
| **Churn top-1158** | 0 % (1 entrant / 1 sortant, overlap 1157/1158) | ✅ minimal, commenté |
| ΔRR@1158 apparié | +0,00 · IC95 [−0,80 ; +0,91] | ⚪ non significatif — **hors critère** (forward) |

**Boussole 0/64 par construction** : le challenger gèle le **triplet** (tier v2, statut cascade,
matrice_statut) VERBATIM depuis `q_v6_m8` ; la composante V ne module que le score de rang `p_raw`, plafonné
(+0,01), et **uniquement** sur 131 parcelles défisc-actives ∩ mono ∩ **non-écartées**. Le signal défisc seul
**ne peut donc jamais faire franchir un seuil de tier** (contrainte dure du mandat) — c'est prouvé par le
design, pas seulement mesuré.

**Churn 0 %** : cohérent — les 131 parcelles nudgées sont surtout « à creuser » (sous le top-1158) ; une seule
franchit le seuil du top-1158. Le RR@1158 est donc quasi insensible à V (+0,00), ce qui **confirme** que le
RR@1158 est le mauvais instrument pour ce signal (il ne regarde que la pointe du classement, pas la
réorganisation intra-bande que V opère).

## Conclusion

Le challenger `q_v6_m8_Vdefisc` **n'est pas basculé au run servi** (décision humaine, hors arène). La
composante V est **validée par le walk-forward** et **innocentée par le garde-fou arène** (boussole/ECE/churn).
La décision d'activer la V en production (et son wording) revient à Vic.
