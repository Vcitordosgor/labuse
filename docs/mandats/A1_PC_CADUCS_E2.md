# PHASE A cycle 2 — ÉTAPE 2 : badge « PC caducs » + composante V

**Branche `phaseA/pc-caducs-e2`.** GO scindé : badge (GO ferme) + composante V (challenger). Signal
**RÉTROSPECTIF** → **l'arène est juge de plein droit**. Runs servis `q_v7_defisc`/`q_v6_m8` intouchés.
**Vic merge — je ne merge pas ; aucune bascule sans sa décision explicite.**

> ## ⚖️ CYCLE 2 ACTÉ (clôture, décision Vic)
> - **Badge `pc_caducs` : CONSERVÉ SEUL** — signal de prospection tracé, factuel, greffé au bloc permis
>   (livré, utile, non-actionnable au niveau RR@1158).
> - **Composante V : REJETÉE par l'arène** — juge légitime (signal rétrospectif, pas d'exception forward),
>   **VRAI REJET** (ΔRR apparié −0,11 IC95 [−0,91 ; +0,73], churn 1 % non nul). Non basculée.
> - **Compteur d'ablation : 1 / 2.** Cycle 1 (défisc) = victoire (walk-forward) → réinitialisé ; cycle 2
>   (caducs) = pas de victoire arène → **+1**. **Prochaine défaite = plateau = déclenchement de M7.**
>   (Compteur canonique tenu dans `A1_BILAN.md`.)

---

## Volet 1 — LE BADGE (table additive `pc_caducs`)

GO ferme. `src/labuse/ingestion/pc_caducs.py`, CLI `labuse pc-caducs`, rebuild idempotent, FK `parcels(idu)`.
- **Définition** (état Sitadel — cf. cadrage §3.2) : caduc = PC **octroyé** (`etat∈{4,6}`) MAIS **aucun réalisé**
  (`etat=6`/DAACT), **Y+4 dépassé** (Y ≤ ref_year−4). Rejetés/en-instruction exclus. Restreint aux idus
  présents dans `parcels`. **2 164 parcelles** caduc probable (Y 2013-2022).
- **Wording factuel, NON accusatoire** — autorisation **Sourcé** (Sitadel), caducité **Estimé** (inférée) :
  > **« PC autorisé 2019 · jamais commencé · caduc probable »**
  > détail (survol) : *« PC autorisé en 2019 (Sitadel, Sourcé), sans achèvement déclaré ni réalisation —
  > caducité probable depuis 2022 (Estimé). Ce profil — constructibilité déjà prouvée, projet non mené —
  > revend ×1,6 plus qu'un PC réalisé comparable (backtest apparié, seed 974). Faits datés uniquement :
  > aucun jugement du propriétaire, aucune date de vente, aucune personne. »*
  **Jamais** « échec/abandon/renoncement », jamais le demandeur (personne physique possible).
- **Exposition** : greffé au **bloc permis M10** de la fiche (`renderCaduc`) ; filtre `pc_caduc` + export CSV.
  Zéro touche aux runs servis. Tests `tests/test_pc_caducs.py` **5/5** (wording non-accusatoire, build
  caduc/réalisé/rejeté, PC récent non-caduc, idempotence, filtre).

---

## Volet 2 — LA COMPOSANTE V (challenger + arène)

Montage **identique au défisc** : triplet (tier · statut · matrice) **gelé verbatim** ; V ne module que le
rang `p_raw`. Gate boussole 0/64 **par construction** ; le signal caduc seul ne franchit jamais un seuil de
tier. Périmètre : **947 parcelles** caduc ∩ non-écarté dans `q_v7_defisc` (`scripts/pc_caducs_challenger.py`).

### Poids calibré PRÉ-LABEL — décision de fenêtre & sensibilité chiffrée

Le poids `W` du nudge est **calibré uniquement sur des cohortes pré-label** (fenêtres se terminant avant
l'année d'évaluation de l'arène ~2025) — jamais sur les mutations que l'arène jugera. Formule bornée :
`W = W_CAP · ln(OR_cal) / ln(3)`, `W_CAP = 0,010` (plafond, comme défisc).

| Fenêtre de calibration | OR caduc vs réalisés | IC95 | **W** |
|---|---|---|---|
| **CLEAN 2016-2018** *(retenu)* | **1,97** | [1,56 ; 2,47] | **0,0062** |
| FULL 2014-2018 (avec l'inversion 2014-2015) | 1,52 | [1,21 ; 1,84] | 0,0038 |

**Impact chiffré de la fenêtre** : inclure les cohortes **2014-2015** (qui s'inversent, cf. cadrage §3.3)
fait chuter l'OR de calibration de **1,97 → 1,52** et le poids de **0,0062 → 0,0038 (−39 %)**. L'inversion
documentée **vit donc bien dans la fenêtre de calibration** — ce n'est pas un détail « neutralisé par
l'anti-leakage » : elle dilue le signal d'un tiers si on l'y laisse entrer. **Décision : calibrer sur les
cohortes propres 2016-2018** (W = 0,0062).

### Verdict de l'arène — REJETÉ (vrai rejet)

`reports/arene/20260720_q_v7_defisc_Vcaduc.md`. Signal rétrospectif → **pas d'exception forward** : le
verdict de l'arène fait foi.

| Dimension | Résultat | Verdict |
|---|---|---|
| **ΔRR@1158 apparié** | **−0,11** · IC95 [−0,91 ; +0,73] | ❌ **non significatif** (point négatif) → REJETÉ |
| Gate boussole — 3 axes | **0 / 64** | ✅ aucun faux positif (triplet gelé) |
| ECE | 0,0167 → 0,0168 (Δ +0,0001) | ✅ non dégradée |
| **Churn top-1158** | **1 %** (9 entrants / 9 sortants, overlap 1149/1158) | ✅ **non nul** — vrai test |

**Lecture honnête.** Le churn **n'est pas nul** (9 caducs sont entrés dans le top-1158) — l'arène a donc
**réellement vu** le signal, contrairement au symptôme « pointe insensible » du défisc. Mais les 9 caducs
promus **n'ont pas capté plus de mutations 2025** que les 9 parcelles délogées → ΔRR ≈ 0 (−0,11). Le signal
caduc est réel (backtest OR 1,62) mais il vit surtout en **« à creuser » (863 des 947), sous le top-1158** que
RR@1158 mesure ; à son poids **calibré** (0,0062, non gonflé pour gagner), il ne déplace pas la pointe.

**C'est un VRAI REJET, il compte au compteur d'ablation** (pas d'exception forward invocable — le signal est
rétrospectif, l'arène est son juge légitime). La bascule de la composante V n'a **pas** lieu.

---

## Synthèse étape 2

| Volet | Livrable | Verdict |
|---|---|---|
| **1 · Badge** | table `pc_caducs` (2164) + fiche/filtre/export + tests 5/5 | ✅ **livré** (GO ferme) |
| **2 · Composante V** | challenger `q_v7_defisc_Vcaduc`, W calibré 0,0062 | ❌ **REJETÉ par l'arène** (ΔRR −0,11, vrai rejet) |

**Cycle 2 = pas de victoire arène** (compteur d'ablation **+1** ; règle : deux cycles sans victoire =
plateau). Le **badge reste livré et utile** (signal prospection tracé, greffé au bloc permis). **Décisions à
Vic** : (1) conserver le badge seul (recommandé — signal réel, non-actionnable au niveau RR@1158) ; (2) acter
le rejet de la V au compteur ; (3) prochain challenger — **passoires DPE F/G**. Aucune bascule sans décision
explicite de Vic. Runs servis `q_v7_defisc`/`q_v6_m8` intouchés.
