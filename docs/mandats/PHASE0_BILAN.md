# PHASE 0 « LE JUGE » — BILAN

Objectif du mandat : **avant tout candidat, bâtir le juge** — le filet de tests du chemin critique,
l'outil de verdict champion/challenger, et le golden élargi. À la clôture : n'importe quel run candidat
se juge contre le run servi **en une commande**, et le chemin critique du scoring est sous tests.

Zones gelées respectées de bout en bout : modèle P M3.6 (sha256), `Q_A_RUN_LABEL = q_v6_m8`,
noyau golden, boussole (un faux positif servi = péché mortel). **Zéro re-scoring, zéro touche modèle.**

---

## Ce qui a été construit

### J1 — Le filet du chemin critique (≈77 tests)
- **J1.a (41)** — couches à pouvoir d'exclusion, tests PURS (ctx stubé) : `test_etage0_ext.py`
  (EmpriseLineaire seuils stricts, FoncierPublic groupes DGFiP, EmpriseRoutiere franche vs garde-fou
  privé, ResiduelSocle barème/bornes/monotonie), `test_cascade_engine.py` (HARD_EXCLUDE coupe la phase 2),
  `test_phase2_layers.py` (SITADEL rattaché-IDU vs signal-de-zone, Proprietaire, DVF).
- **J1.b (13)** — SQL du modèle P : label **L2-F** (lot copro exclu, immeuble entier conservé), union
  copro RNIC∪DVF, **fenêtres as-of anti-leakage** (aucune fuite année N/futur ; `DVF_START` 2021 vs
  `EXT_DVF_START` 2014).
- **J1.c (16)** — fonctions pures : composite équipements `exp(-d/800)`, shrinkage gamma-Poisson ; ICD
  borné 0-100 et invariant `POIDS_TOTAL == 100` ; `decide_status` (3 règles dures).
- Baseline pytest passée de **852 → 929** verts (0 failed ; rouges pré-existants résorbés en fix trivial
  ou skip documenté).

### J2 / J2-bis — L'arène à verdict apparié
- `scoring/arene.py` + CLI **`labuse arene`** : SOUDE les métriques existantes (`p_model/evaluate.py` :
  rr_at_k, bootstrap_rr, lift, ece, churn_topk, ventilation, permutation ; seed 974) + le protocole M3.6
  (label L2-F, RR@1158, hors copro) en **un** outil de verdict. **LECTURE SEULE** ; n'écrit que dans
  `reports/arene/` ; ne lance jamais `score-v2`.
- Rapport : contrôle d'univers, **gate golden/boussole (éliminatoire)**, RR@1158, lift, ventilations,
  ECE, churn, contrôle négatif par permutation, **AVIS** (indicatif — la bascule reste humaine).
- **J2-bis** : (1) réconciliation RR — le RR absolu est **in-sample** (features as-of 2026 vs label 2025),
  NON comparable au walk-forward OOS 6,73 ; caveat en tête de baseline. (2) **bootstrap APPARIÉ** de ΔRR
  (mêmes parcelles, seed 974) → le critère RR de `decide_avis` = l'IC de la différence exclut zéro.
  (3) **canari** de dégradation (challenger dégradé → REJETÉ) en test permanent.

### J3 — Le golden 116 à triplet
- Proposition de **84 additions** stratifiées (24 communes ≥2, 5 tiers ≥5, 10 motifs ≥8, 6 cas limites),
  validée par Vic **sur preuves** (dossier `reports/j3-revue/DOSSIER-REVUE-J3.pdf` : vignette ortho +
  contour, sources tracées, **3 contre-vérifications** — source en base, verdict recalculé isolé = servi,
  mesure PostGIS directe).
- **Gel** : 32 sentinelles d'origine INCHANGÉES + 84 **ancres** gelant le **triplet** (statut cascade,
  matrice_statut, tier v2) + `validation` (53 factuelle / 31 coherence). `golden_check.py` **116/116**.
- **Gate boussole à 3 axes** : ne s'appuie que sur les négatives `factuelle` ; violation si le challenger
  passe la parcelle en **tier brulante/chaude** (modèle P), en **statut cascade opportunite**, OU en
  **matrice_statut chaude** (matrice Q×A — juge les challengers matrice de la Phase A-3). Les positives
  (`coherence`) = ancres de non-régression, hors gate. Live champion : 64 attendues, **0 violation**.
- Référence : `reports/arene/BASELINE_q_v6_m8.md` (bootstrap apparié + gate 0/64 sous 3 axes).

---

## Findings ouverts

| # | Sujet | Statut |
|---|---|---|
| **F6** | `test_ortho_detection::test_post_traitement_rejets` : drift ortho (hors scoring) | `reporté` — skip documenté, triage ortho interne |
| **F7** | `commit()` enfoui dans `build_copro_flags`/`build_ext_dataset` = défaut de testabilité | `reporté` — micro-refactor (session injectée, commit à la frontière CLI) |
| **F8** | `EauLayer` : libellé « majoritairement sur l'eau » vs règle réelle `centroïde OU ≥50 %` | `reporté` — wording couche, verdict inchangé |
| **F9** | Contre-vérif ③ du dossier de revue : métriques non comparables (pente °/%, eau aire/centroïde) | `reporté` — améliorer l'outil (même métrique ou « non comparable ») |
| **F10** | Wording « Propriété publique » pour DGFiP groupe 9 type coopérative (TERRACOOP) | `reporté` — reformulation à arbitrer |
| **F11** | Golden bi-niveau : couverture service end-to-end limitée aux 32 sentinelles | `reporté` — option run API complet occasionnel (rate-limit levé) en QA |

Findings antérieurs (F0–F5) : **traités** (voir `PHASE0_FINDINGS.md`). Aucun S1 ouvert ; boussole intacte
(golden 116/116, run servi q_v6_m8 inchangé).

---

## Comment juger un challenger — en une commande

```bash
labuse arene --challenger <run_id>        # champion = dernier run servi par défaut
```

Écrit `reports/arene/<date>_<run_id>.md` et affiche l'**AVIS** (`CHALLENGER RETENU` | `REJETÉ` |
`REJETÉ éliminatoire boussole`). LECTURE SEULE ; **ne bascule jamais le run servi** — la décision reste
humaine. Le challenger n'est retenu que si : **gate boussole 3 axes = 0 violation** ET l'IC apparié de
ΔRR exclut zéro ET l'ECE n'est pas dégradée (> 0,01) ET le churn ≤ budget (25 %). Référence à battre :
`reports/arene/BASELINE_q_v6_m8.md`. (Voir aussi `COMMANDES.md`.)

**Phase 0 close.** Le juge est en place : chemin critique sous filet, arène à verdict apparié, golden 116
à triplet gelé, gate boussole à 3 axes. La Phase A peut envoyer ses challengers.

---

## Doctrine — quel juge pour quel signal (établie Phase A-1)

> **Par défaut, l'arène juge.** Un signal à **horizon forward** (qui prédit des mutations *futures*, ex.
> « fenêtre de sortie de défiscalisation 2026-2028 ») **ne peut pas** être jugé au ΔRR de l'arène : celle-ci
> évalue le classement contre les mutations **déjà réalisées** (label ~2025), temporellement **orthogonal**
> au signal (même nature que la réconciliation RR in-sample de J2-bis). Un tel signal ajoute au haut du
> classement des parcelles qui, **à raison**, n'ont pas encore muté — l'arène les lit comme des faux positifs.
>
> **Règle.** Un signal forward se juge par un **walk-forward dédié** (folds as-of, lift + IC bootstrap seed
> 974) ; l'arène reste le **portier obligatoire** — gate boussole 0/64 trois axes, ECE non dégradée, churn
> commenté — mais **son ΔRR n'est pas le critère de victoire** pour ce challenger. L'exception est
> **documentée explicitement dans le rapport d'arène du challenger, jamais implicite**.
>
> Premier cas d'application : Phase A-1 « fenêtre de sortie de défisc » — juge = `scripts/a1_walkforward.py`
> (voir `docs/mandats/A1_CADRAGE_DEFISC.md`).
