# PHASE A-1 — BILAN : « fenêtre de tir · sortie de défiscalisation »

Premier challenger de la Phase A (cycle d'ablation n°1). Objectif : instruire une idée — la propension de
revente saute à l'expiration de l'engagement fiscal (Girardin/Scellier/Duflot/Pinel) — puis la **prouver ou la
tuer** avant toute intégration, et si elle survit, la servir **sans jamais fabriquer de faux positif**.

**Résultat : cycle 1 = VICTOIRE.** L'idée a survécu à l'instruction, le juge dédié l'a validée, le badge et la
composante V sont livrés et basculés en production, le run servi versionné (`q_v7_defisc`) est gelé et gardé en
hystérésis. Le compteur d'ablation « deux cycles sans victoire = plateau » est **réinitialisé**.

---

## Le fil : instruction → juge → badge + V

### 1. Instruction (étape 1, lecture seule) — `A1_CADRAGE_DEFISC.md`
Backtest sur nos données (DVF 2014-2025 = `dvf_mutations_histo` ∪ `dvf_mutations_parcelle`). Proxy neuf = VEFA
(label DVF direct) + Vente ≤ 3 ans après achèvement PC. Grâce 2 ans obligatoire (l'acte de livraison VEFA, 821/1063
événements < 6 mois à prix constant, n'est pas une revente). Verdict :
- **Mécanisme prouvé** au niveau **lot appartement** (surface-matché) : OR 5,96 [5,15;6,90] à +6/+8 ; 6,22 [4,24;9,62]
  à +9/+11. Les courbes de hazard se croisent : le neuf verrouillé jusqu'à +5, dump à +7…+11.
- **Tension** : le signal fort est en **copro/appartement** (non actionnable au niveau parcelle — revendre un lot ne
  libère pas la parcelle). La tranche **actionnable (maison/mono)** montre la même direction mais était **sous-alimentée**
  (n=107, DVF tronqué à 2014 → cohortes +9 = 2014-2016 seules).
- Décision copro : signal **restreint mono** ; copro-immeuble « grappe de lots » = piste future.
- **Réserve §7 (devenue doctrine)** : un signal à horizon **forward** (fenêtre 2026-2028) ne peut pas être jugé au
  ΔRR de l'arène (label ~2025) — instruments temporellement orthogonaux.

### 2. Le juge (étape 2, volet 1) — `scripts/a1_walkforward.py`
Puisque l'arène ne peut juger un signal forward, on bâtit le **walk-forward dédié**, as-of strict, folds 2021-2025 :
P(mutation année N | maison/mono **en fenêtre** +6/+11) vs **hors fenêtre**, bootstrap cluster/parcelle, seed 974.
- Poolé : **0,033 vs 0,014** · **LIFT 2,38 [1,48;4,20]** · **OR 2,43 [1,49;4,34]** · direction positive **sur les 5 folds**.
- **IC exclut 1 → PASSÉ.** L'instrument correct valide ce que le backtest rétrospectif ne pouvait pas alimenter :
  **≈ ×2,4** de propension de mutation en fenêtre de sortie. Le juge, pas l'enthousiasme, décide.

### 3. Le badge (étape 2, volet 2) — table `defisc_fenetres`
GO ferme. Table additive (maisons/mono), CLI `labuse defisc-fenetres`, fenêtre [Y+6,Y+11] **Estimée** ancrée sur
`ref_year` (jamais `now()`). **1 166 parcelles, 797 fenêtre active 2026-2028.** Wording factuel sourcé, **jamais une
date de vente, jamais une personne physique**. Exposé fiche + filtre + CSV. Tests 6/6.

### 4. La composante V (étape 2, volet 3) — challenger `q_v6_m8_Vdefisc` → servi `q_v7_defisc`
Contrainte dure garantie **par construction** : triplet (tier · statut · matrice) **gelé verbatim** ; V ne module que
le rang `p_raw` (+0,01 plafonné) sur **131** parcelles défisc-actives ∩ mono ∩ **non-écartées**. Donc le signal défisc
seul **ne peut jamais franchir un seuil de tier**. Arène en **garde-fou** : boussole **0/64**, ECE **non dégradée**,
churn **0 %** ; ΔRR non significatif → REJETÉ **mais hors critère** (forward, documenté). **Bascule** : nouveau label
servi versionné `q_v7_defisc`, gelé, `q_v6_m8` conservé en hystérésis (rollback écrit). Golden **116/116** sur le
nouveau label (neutralité structurelle : zéro ancre ne bouge, les triplets sont copiés verbatim).

*(Chaîne des volumes 578 → 797 → 131 réconciliée dans `A1_ETAPE2_DEFISC.md`.)*

---

## Doctrine posée (cycle 1) — `PHASE0_BILAN.md`

> Par défaut, l'arène juge. Un signal à **horizon forward** se juge par un **walk-forward dédié** (folds as-of, lift +
> IC bootstrap seed 974) ; l'arène reste le **portier** (boussole 0/64 trois axes, ECE, churn), mais son **ΔRR n'est pas
> le critère** de victoire pour ce challenger. **L'exception est documentée explicitement par challenger, jamais implicite.**

Premier cas d'application intégral : ce challenger (juge `a1_walkforward.py`, note d'exception
`reports/arene/20260720_q_v6_m8_Vdefisc_DOCTRINE.md`).

---

## Findings ouverts

| # | Sujet | Statut |
|---|---|---|
| **A1-F1** | DVF tronqué à 2014 : Girardin/Scellier (gros volumes ≲ 2012) invisibles ; puissance maison bornée (backtest n=107). Le walk-forward pooling contourne, mais la queue reste sous-observée. | `accepté` — limite de donnée, pas de correctif |
| **A1-F2** | VEFA = date de signature, pas de livraison : les bosses peuvent être décalées de ~1 an. Grâce 2 ans absorbe l'essentiel. | `accepté` — caveat documenté |
| **A1-F3** | Copro-immeuble « grappe de lots en sortie simultanée » = signal fort (OR ~10) mais autre unité d'analyse, non actionnable au niveau parcelle. | `reporté` — piste future (frère A-1 ou A-3) |
| **A1-F4** | `docs/ROADMAP_ALGO.md` cité par le mandat absent du dépôt ; règles liantes appliquées via le mandat. | `signalé` — à créer/retrouver côté Vic |
| **A1-F5** | Dette front réglée : label servi lu depuis config/env (fin du `SOURCE` codé en dur). | `résolu` (clôture) |

Aucun S1. Boussole intacte (golden 116/116, gate 0/64). Run servi bascule proprement, rollback disponible.

---

## Cycle 1 — verdict

**VICTOIRE.** Une idée forward, réputée « invendable / risquée » par l'audit produit initial, a été **instruite,
prouvée par le bon instrument, servie sans faux positif**, et a fait émerger une **doctrine réutilisable** (walk-forward
vs arène) qui servira à tous les challengers forward suivants. **Compteur d'ablation réinitialisé.**

**Suite** : prochains challengers de la famille A-1 — **PC caducs**, puis **passoires DPE F/G** (calendrier DOM à
vérifier) — chacun avec son propre procès. Le juge est prêt : arène pour les signaux in-sample, walk-forward dédié pour
les signaux forward.
