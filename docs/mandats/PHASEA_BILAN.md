# PHASE A — BILAN & CLÔTURE

Phase A = cycles d'ablation : instruire des idées de signal, les **prouver ou les tuer** avec un juge dédié,
et ne servir que ce qui gagne **sans jamais fabriquer de faux positif**. Règle de sortie : **deux cycles
consécutifs sans victoire de scoring = plateau → M7 (mise en ligne)**.

**État : compteur 2/2 → 🛑 PLATEAU ACTÉ. La Phase A se clôt ; le mandat M7 suit.**

---

## Les trois cycles

| # | Idée | Juge légitime | Verdict scoring | Livré |
|---|---|---|---|---|
| **1** | **Défisc** — revente à l'expiration de l'engagement fiscal | walk-forward dédié (signal *forward*) | ✅ **VICTOIRE** (OR 2,43 IC95 [1,49;4,34]) | **V basculée** → `q_v7_defisc` + badge |
| **2** | **PC caducs** — permis octroyé jamais réalisé | arène (signal *rétrospectif*, juge de plein droit) | ❌ **REJET** (ΔRR −0,11, vrai rejet) | **badge seul** ; V en réserve |
| **3** | **Passoires DPE F/G** — pression réglementaire | infaisable (couverture anecdotique) | ❌ **NO-GO** (7 actionnables, 2 juges morts) | rien servi ; badge+V réservés |

Chaque cycle a produit une **preuve d'instruction** (`A1_CADRAGE_DEFISC.md`, `A1_PC_CADUCS_CADRAGE.md`,
`A1_DPE_CADRAGE.md`) — y compris les rejets : une idée tuée proprement est un actif.

---

## Ce qui est SERVI (production, `q_v7_defisc`)

- **Run champion `q_v7_defisc`** (bascule protocolée cycle 1) : `q_v6_m8` en hystérésis, label servi
  configurable (`LABUSE_SERVED_RUN` / `VITE_RUN_LABEL`), golden 116/116, baseline arène régénérée, rollback
  écrit (`A1_BASCULE_ROLLBACK.md`). Modèle P M3.6 gelé — la composante V ne module que le rang, jamais le tier.
- **Badge défisc** (`defisc_fenetres`, ~1 166 mono, 797 fenêtre active) — court + survol, décote de revente
  **recalculée 68 %** (n=122), fiche + filtre + export.
- **Badge PC caducs** (`pc_caducs`, ~2 164) — factuel non-accusatoire, greffé au bloc permis, fiche + filtre.
- **Score É v1** (`score_e`, marge € = charge foncière supportable − prix probable) — fiche + filtre
  `marge_min`. ⚠ note de sensibilité : la négativité de masse vient du **prix de sortie** (médianes DVF de
  l'existant, pas neuf/VEFA) → calibration prix par secteur = priorité avant exposition client large.

## Ce qui est EN RÉSERVE (datée)

- **Composante V « PC caducs »** → **réserve M4.0** (rejetée à l'arène mais signal réel OR 1,62 ; vit sous le
  top-1158). Challenger `q_v7_defisc_Vcaduc` conservé comme preuve.
- **Badge + V « DPE F/G »** → **réserve M4.0 avec critère de réveil** : réévaluation à chaque refresh DPE,
  **réveil dès que `F/G ∩ mono ∩ non-écarté ≥ 200 parcelles`** (aujourd'hui 7).
- **Score É — calibration prix de sortie par secteur (neuf/VEFA)** + modificateur rareté ZAN (N1b) → V2.

## Ce qui est REPORTÉ post-M7 (pas abandonné)

- **A-2 · Score V v2** (recalibration vendabilité) — reprendra avec le feedback client.
- **A-3 · matrice Q×A** (challengers matrice) — le 3ᵉ axe du gate boussole les attend déjà.

---

## La doctrine établie (réutilisable)

- **Quel juge pour quel signal** (`PHASE0_BILAN.md`) : par défaut l'**arène** juge (ΔRR apparié IC excluant
  zéro, gate boussole 0/64 trois axes, ECE, churn). Un signal à **horizon forward** (mutations futures) ne
  peut pas être jugé au ΔRR (label passé, orthogonal) → **walk-forward dédié** (folds as-of, IC bootstrap
  seed 974) ; l'arène reste le **portier**. **Exception documentée par challenger, jamais implicite.**
- **Montage V sûr** : triplet (tier · statut · matrice) copié verbatim, V module le seul `p_raw`, plafonné,
  restreint aux non-écartés → gate boussole 0/64 **par construction** ; le signal seul ne franchit jamais un
  seuil de tier. Poids **calibré pré-label** (anti-leakage).
- **Instruction avant intégration** : couverture chiffrée en premier (fragilité n°1) ; un croisement
  anecdotique tue un cycle en une heure, sans rien servir.

## Findings (état)

- Phase 0 F0–F5 traités ; **F7/F8/F9/F10/F11 résolus** (nuit 2026-07-21 + clôture) ; findings A1-F1..F5
  documentés (`A1_BILAN.md`). Aucun S1 ouvert. Boussole intacte.
- `docs/ROADMAP_ALGO.md` (cité par les mandats) reste absent du dépôt — à créer/retrouver côté Vic.

---

## État final

**Le champion est `q_v7_defisc`. Le juge est opérationnel** (arène + walk-forward dédié, gate boussole 3 axes,
golden 116). **La prochaine phase est la mise en ligne (M7).** La Phase A a livré trois badges/scores servis,
une composante V validée et basculée, une doctrine de jugement réutilisable, et deux réserves datées — sans
jamais servir un faux positif.
