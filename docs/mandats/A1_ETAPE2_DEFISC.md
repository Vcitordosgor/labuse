# PHASE A-1 — ÉTAPE 2 : le juge, le badge, la composante V

**Branche `phaseA/a1-defisc-e2`.** GO scindé (décision Vic sur l'étape 1) : le juge d'abord (walk-forward
dédié), le badge en GO ferme, la composante V **seulement si le juge passe**. Doctrine §7 acceptée et inscrite
au bilan (`PHASE0_BILAN.md`). Run servi `q_v6_m8` intouché. **Vic merge — je ne merge pas.**

---

## Volet 1 — LE JUGE : walk-forward poolé (lecture seule)

**Pourquoi pas l'arène.** L'arène juge le classement contre les mutations **réalisées ~2025** ; la fenêtre
de sortie prédit **2026-2028**. Un signal forward correct ajoute au haut du classement des parcelles qui, à
raison, n'ont pas encore muté → l'arène RR les lit comme des faux positifs. Le juge de victoire est donc un
**walk-forward dédié**, l'arène restant portier boussole/ECE/churn (doctrine, `PHASE0_BILAN.md`).

**Protocole (as-of strict, aucune fuite).** Folds N = 2021…2025. Au 1er janvier N :
- **Ensemble à risque** = parcelle **mono** (`copro_rnic = copro_dvf = false`) portant une acquisition
  **neuf** (VEFA, ou Vente logement ≤ 3 ans après achèvement PC) d'année **Y ≤ N-3** (au-delà de la grâce
  2 ans qui neutralise l'acte de livraison VEFA), **encore détenue** au 1/1/N (aucune revente logement dans
  `(acq + 2 ans, 1/1/N)`). *Rien de postérieur au 1/1/N ne sert à établir l'état.*
- `elapsed = N − Y`. **En fenêtre** = `elapsed ∈ {6..11}` (+6/+8 ou +9/+11). **Hors fenêtre** (contrôle
  apparié : même nature « logement neuf détenu », hors pic) = `elapsed ∈ {3,4,5,12,13,14}`.
- **Issue** = au moins une mutation logement (Vente/VEFA) de la parcelle **dans l'année N**.

**Mesure** : P(mutation année N | en fenêtre) vs hors fenêtre, **folds agrégés**, lift + odds ratio,
**IC95 bootstrap cluster par parcelle** (le même bien apparaît sur plusieurs folds — dépendance de panel),
seed 974, 2000 rééch. Script : `scripts/a1_walkforward.py` (reproductible, vérifié run-à-run).

### Résultat

| Fold N | n en fenêtre | mut. | taux | n hors | mut. | taux |
|---|---|---|---|---|---|---|
| 2021 | 154 | 14 | **0,0909** | 298 | 10 | 0,0336 |
| 2022 | 206 | 5 | **0,0243** | 315 | 1 | 0,0032 |
| 2023 | 318 | 7 | **0,0220** | 293 | 4 | 0,0137 |
| 2024 | 411 | 10 | **0,0243** | 302 | 5 | 0,0166 |
| 2025 | 492 | 16 | **0,0325** | 312 | 1 | 0,0032 |
| **POOLÉ** | **1 581** | **52** | **0,0329** | **1 520** | **21** | **0,0138** |

**Lift = 2,38** IC95 **[1,48 ; 4,20]** · **OR = 2,43** IC95 **[1,49 ; 4,34]** (cluster/parcelle, 860 parcelles).

**Direction positive sur les 5 folds.** L'IC95 **exclut 1** → **CRITÈRE PASSÉ**. Là où le backtest
rétrospectif de l'étape 1 ne pouvait pas alimenter le test maison (n = 107, IC incluant 1), le walk-forward
**as-of** — l'instrument correct pour un signal forward — confirme le signal : une maison/mono en fenêtre de
sortie d'engagement mute **≈ 2,4× plus** qu'une maison neuve détenue hors fenêtre. **⇒ La composante V est
validée** (volet 3 débloqué).

*Limites honnêtes (rappel étape 1)* : DVF tronqué à 2014 (Girardin/Scellier invisibles) ; VEFA = date de
signature, pas de livraison (bosse possiblement décalée de ~1 an) ; lag de publication DVF absorbé par les
folds calendaires. Le contrôle « hors fenêtre » est le plus exigeant (mêmes logements neufs, hors pic) ; le
signal survit.

---

## Volet 2 — LE BADGE (table additive `defisc_fenetres`)

GO ferme (indépendant du volet 1). Signal de **timing par parcelle**, exposé fiche + filtre, **jamais une
date de vente**, **jamais une personne physique**. **Zéro touche** aux tables servies (`parcel_p_score_v2`,
`dryrun_parcel_evaluations`, run `q_v6_m8`).

**Table dérivée `defisc_fenetres`** (`src/labuse/ingestion/defisc_fenetres.py`, CLI `labuse defisc-fenetres
--ref-year 2026`) : `CREATE TABLE IF NOT EXISTS`, rebuild complet idempotent, FK `parcels(idu)`.
- **Maisons / monopropriété uniquement** (`copro_rnic = copro_dvf = false`) — vérifié en test (0 ligne copro).
- Proxy neuf = VEFA (label DVF) ou Vente logement ≤ 3 ans après achèvement PC ; dernière acquisition retenue.
- Fenêtre = bande **[Y+6, Y+11]** (dispositif exact inconnu → « Estimé »). `fenetre_active` = bande ∩
  [ref_year, ref_year+2], **ancrée sur `ref_year` explicite (jamais `now()`, doctrine `anc.py`)**.
- Colonnes : `idu, proxy, achat_neuf_annee, fenetre_debut, fenetre_fin, fenetre_active, statut='Estimé',
  source_libelle, libelle_badge`.

**Volumétrie (ref 2026)** : **1 166 parcelles mono neuf**, dont **797 fenêtre active 2026-2028**
(795 VEFA + 371 permis en source). Wording servi, factuel et tracé :
> `achat neuf 2019 — DVF · fenêtre de sortie d'engagement 2025-2030 · Estimé`
> source : `DVF vente 2019 + achèvement PC 2017`

**Exposition**
- **Fiche** (`GET /parcels/{idu}` → `_build_fiche`) : bloc `defisc_fenetres` ajouté (garde `to_regclass` —
  ne casse jamais la fiche si la table n'est pas encore construite). Rendu front `web/app.js`
  (`renderDefisc`, accordéon « Propriétaire & prospection », badge « Estimé »).
- **Filtre** (`GET /parcels?defisc_active=true`, `_q_v2_where`) + export CSV : simple test de présence
  `EXISTS (… fenetre_active)`. Vérifié de bout en bout (fiche + liste sur base réelle).

**Tests** (`tests/test_defisc_fenetres.py`, 6/6) : wording/bornes/actif (pur), construction DB **mono
uniquement** (copro exclue, non-neuf exclu), idempotence, fragment de filtre SQL. Suite complète :
**948 passés** (seul `test_courrier` échoue — pré-existant, hors périmètre).

## Volet 3 — LA COMPOSANTE V (challenger arène)

Débloqué par le volet 1 (critère passé). Challenger complet dans son **propre run_id**
`q_v6_m8_Vdefisc` (`scripts/a1_challenger_v.py`), run servi `q_v6_m8` **intouché**.

**Contrainte dure honorée PAR CONSTRUCTION** — « le signal défisc seul ne peut jamais faire franchir un
seuil de tier » : le challenger **gèle le triplet** (tier v2 · statut cascade · matrice Q×A) copié
VERBATIM du champion ; la composante V ne module **que** le score de rang `p_raw`. Donc tier/statut/matrice
challenger ≡ champion → gate boussole 3 axes = **0/64 par construction**, et V ne réordonne qu'à l'intérieur
des bandes déjà servies (jamais de nouveau tier).

**V plafonnée, restreinte** : `p_raw' = p_raw + 0,01` (borné ≈ écart p50→p90 du run), appliqué **uniquement**
aux **131 parcelles** défisc-actives ∩ **mono** ∩ **non-écartées** (nudger une écartée serait absurde et
polluerait le top-1158 → exclu).

**Verdict = le walk-forward (volet 1, PASSÉ).** L'arène tourne en **garde-fou** :
`reports/arene/20260720_q_v6_m8_Vdefisc.md` (+ note doctrine `…_DOCTRINE.md`).

| Dimension garde-fou | Résultat | Verdict |
|---|---|---|
| Gate boussole — 3 axes | **0 / 64** | ✅ aucun faux positif |
| ECE | 0,0167 → 0,0167 (Δ −0,0000) | ✅ non dégradée |
| Churn top-1158 | **0 %** (1 entrant / 1 sortant) | ✅ minimal, commenté |
| ΔRR@1158 apparié | +0,00 · IC95 [−0,80 ; +0,91] → **REJETÉ** | ⚪ **hors critère** (signal forward) |

L'AVIS arène `REJETÉ` sur le ΔRR est **attendu et documenté explicitement** (doctrine) : l'arène (label 2025)
ne peut pas récompenser un signal forward 2026-2028. Le churn 0 % confirme le diagnostic — les défisc-actifs
non-écartés sont surtout « à creuser » (sous le top-1158), donc RR@1158 est quasi insensible à V. La V est
**validée par le walk-forward** et **innocentée par le garde-fou** (boussole/ECE/churn). Basculer la V en
production (et son wording) = décision Vic.

---

## Synthèse étape 2

| Volet | Livrable | Verdict |
|---|---|---|
| **1 · Juge** | walk-forward as-of (`a1_walkforward.py`) | ✅ **PASSÉ** — OR 2,43 IC95 [1,49 ; 4,34], V validée |
| **2 · Badge** | table `defisc_fenetres` + fiche + filtre + tests | ✅ livré — 1166 mono, 797 active, 6/6 tests |
| **3 · Composante V** | challenger `q_v6_m8_Vdefisc` + arène garde-fou | ✅ boussole 0/64, ECE ok, churn 0 % ; ΔRR hors critère |
| **Doctrine** | règle walk-forward vs arène (`PHASE0_BILAN.md`) | ✅ inscrite |

**Décisions restant à Vic** : (1) basculer la composante V en production (le challenger existe, prouvé,
garde-fou vert) ; (2) wording client du badge ; (3) prochain challenger A-1 (PC caducs, puis passoires DPE
F/G). Run servi `q_v6_m8` intouché. **Vic merge — je ne merge pas.**
