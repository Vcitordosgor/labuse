# AUDIT 5 — CARTOGRAPHIE RETENUE/ÉCARTÉE : le motif est-il reconstructible ?

Test : pour chaque famille de statut, le motif exact se reconstruit-il par requête ?
| statut | source du motif | reconstructible |
|---|---|---|
| écartée étage 0 | dryrun_cascade_results (HARD_EXCLUDE, detail, source) | ✓ — testé sur 50 000 écartées : **0 sans motif trouvé** (exclusion dure OU Q<50) |
| écartée matrice (Q<50) | q_score du run | ✓ |
| declasse A/B | parcel_constructibilite (label, **motif**, cause) | ✓ |
| declasse AU (D) | parcel_au_statut (classe, **motif** sourcé règlement) | ✓ |
| declasse bâtie révélée (E) | parcel_bati_revele (**motif** daté sourcé, emprises) | ✓ |
| exceptions | served_run_exceptions (origine, servi, **motif**, date) | ✓ (1 active : CY0104) |
| chaude vs a_creuser | rang vs n_entrée + plancher C + hystérésie | ✓ mais **DÉRIVABLE seulement** : n_entrée/n_sortie/seuil-D du run ne sont PAS persistés avec le run (recalculés) — TROU n°1 |
| copro (3 424, jamais classées) | flag copro_rnic/copro_dvf | ✓ booléen, mais **sans détail de source par parcelle** en table servie — TROU n°2 (mineur) |
| intra-palier (audit 1) | tirage seedé | ✗ **TROU n°3 : « pourquoi 208ᵉ et pas 250ᵉ » n'a pas de réponse — ex aequo arbitraire** |

**Verdict : les MOTIFS d'écartement/déclassement sont intégralement reconstructibles (0 trou
sur 50 000 testées).** Les trous sont sur la TÊTE : les paramètres de coupure non persistés
par run (n_entrée, seuil-D) et l'ordre intra-palier. Reco phase 3 : persister les params de
calibrage dans p_score_v2_runs (1 colonne JSON) + départage explicite (audit 1).
