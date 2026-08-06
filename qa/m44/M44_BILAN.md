# M44 — BILAN (sortie locative / défisc du mode B + solde dette q_v7_defisc)

**Branche `m44-sortie-locative-defisc`** · base `main` 61659b0b (M42 mergé) · commits atomiques
`[M44-Lot0/Px]`. **0 tier, 0 verdict, 0 bascule, 0 merge.** Règle fiscale tenue de bout en bout :
aucune affirmation d'éligibilité ; on sert un **bilan AU PLAFOND réglementaire Sourcé**.

---

## Lot 0 — dette technique `q_v7_defisc` soldée (commit `[M44-Lot0]`)

Sur pièces (M31 : vérifier avant d'aligner) :
- **score_e** était réellement bâti sur **q_v7_defisc** (run mort — ses 77 718 lignes = non-écartée
  de q_v7, pas q_v8 ; **428 marges servies sur des parcelles écartées en q_v8**). Défaut aligné sur
  `Q_A_RUN_LABEL` (point de vérité) + CLI + **rebuild sur q_v8 → 77 308 lignes, 0 écartée**.
- **pc_caducs** : constat — `_SELECT_RAW` **ne référence AUCUN run**. La note M31 « run servi
  q_v7_defisc » était **fausse** (doctrine : une note n'est pas une source). **Effet de l'alignement
  de run = 0** (rien à aligner ; un refresh source a bougé 2 164→2 161 = dérive de fraîcheur permis,
  pas le run). Docstring corrigée.

Golden 117/117 (golden ne capture ni score_e ni pc_caducs) · 0 tier.

---

## Dispositifs établis avec sources (Phase 0)

| Dispositif | 2026 | Source | Décision v1 |
|---|---|---|---|
| Pinel / Pinel+ OM | **clos** (fin 31/12/2024) | LF | ABSENT — non servi |
| Denormandie OM (réhab locatif) | en vigueur (→ 31/12/2027) | CGI art. 199 novovicies | éligibilité **non servie comme fait** (commune ORT/ACV + opérateur) |
| **Plafonds loyer 2026 DOM** | **oui** | **BOFiP BOI-BAREME-000017-20260310** | **SOCLE SERVI** : base 12,21 €/m², intermédiaire 12,71 €/m², coef 0,7+19/S≤1,2 |
| Girardin social / LLI / Loc'Avantages | opérateur / non établi | CGI/— | hors v1 / ABSENT |

**Architecture loyers retenue (arbitrage Vic)** : (a) **plafond réglementaire Sourcé par défaut**
(base 12,21 = le plus prudent), l'intermédiaire 12,71 sélectionnable, les deux visibles+étiquetés
BOFiP+date ; (b) **loyer de marché en paramètre CLIENT (Estimé)**. **On sert le BILAN AU PLAFOND,
jamais l'ÉLIGIBILITÉ.**

---

## PHASE 1 — Moteur (commit `[M44-P1]`)

- **`config/calibrage/defisc_2026.yaml`** — **année AU NOM DU FICHIER** (geste annuel loi de finances
  évident pour le Vic de janvier 2027). Plafonds base/intermédiaire, coef surface, rendement cible 6 %
  (Estimé, **justifié** valeur de place), mention conseil-fiscal, dispositifs non couverts. **Chaque
  paramètre porte source + date** ; **lint** (modèle M41) refuse l'incomplet.
- **Point de calcul unique `src/labuse/faisabilite/defisc.py`** :
  - `coef_surface(S)` = 0,7 + 19/S plafonné 1,2 — **testé aux bornes** (cap 1,2 pour S ≤ 38 m² ;
    descend vers 0,7 pour les grandes ; garde S=0 → cap).
  - `sortie_locative(shab, coût travaux, régime | loyer marché, rendement cible)` = loyer (plafond
    Sourcé × coef, ou marché Estimé sans coef) × surface → loyer annuel + **prix d'achat max à
    rendement cible** (= loyer annuel / rendement − coût travaux). **Héritage M33** : l'achat max
    contient les travaux (Estimé) → **toujours Estimé**, même au plafond Sourcé.
- **`compute_mode_b`** gagne `sortie_locative` **côte à côte** avec la revente, jamais fusionnée ;
  endpoint `/mode-b` gagne régime / loyer_marché / rendement (params CLIENT, **rien persisté**).

## PHASE 2 — Fiche & assistant (commit `[M44-P2]`)

- **Tiroir mode B** : section **« Sortie locative »** (front `Fiche.tsx`) + one-pager (`REVENTE` /
  `LOCATIF` distincts). Le **tier + verdict M34 restent premiers** (le locatif est un contexte du
  tiroir). Chaque composante étiquetée ; **bilan négatif dit honnêtement** ; mention conseil-fiscal visible.
- **Assistant IA** : `mode_b` restructuré en `sortie_revente` + `sortie_locative` (liste blanche,
  anti-hallucination) ; `rules_summary` cite les deux + la mention. **`/ask` : une question
  d'éligibilité (Girardin/Pinel/Denormandie/LLI/Loc'Avantages/défisc) → réponse DÉTERMINISTE
  « dispositif non couvert à ce jour »** (l'absence dite, jamais un silence, jamais une affirmation,
  jamais un appel modèle). Preuve : `qa/m44/assistant_non_couvert_evidence.json`.

---

## → DOSSIER AVOCAT (mention fiscale, à transmettre telle quelle — Vic)

> « Hypothèses fiscales indicatives — le dispositif, l'éligibilité de la parcelle et les plafonds
> applicables sont à valider avec un conseil fiscal. Ce bilan locatif est un calcul paramétré au
> plafond réglementaire affiché ; il ne vaut ni conseil fiscal, ni promesse d'éligibilité. **Les
> plafonds affichés sont ceux publiés au barème officiel en vigueur à la date indiquée.** »

Servie partout où le bilan locatif apparaît (fiche, one-pager, assistant). Config :
`config/calibrage/defisc_2026.yaml` (`mention_conseil_fiscal`).

---

## VÉRIFICATION (2026-08-06)

| Contrôle | Résultat |
|---|---|
| **Golden** | **117/117 PASS** (mode_b / score_e / pc_caducs golden-invisibles) |
| **Re-mesure M34/M35** | **0 divergence — PASS** |
| **SHA256 vigilances M37** | `482da6f6…e9abe9` — **INCHANGÉ** |
| **Tiers servis** | **0 tier modifié** |
| **Effet Lot 0 pc_caducs** | run-alignement = **0** (run-agnostique) ; score_e : 428 écartées retirées |
| **pytest** | verts + tests defisc (coef bornes, héritage étiquette, rendement borné) — 5 pré-existants |
| **tsc -b (front)** | exit 0 |

### Captures (`qa/m44/screens/`)
1. `1_deux_sorties_au_plafond.png` — one-pager : REVENTE + LOCATIF au plafond Sourcé + mention.
2. `2_tiroir_sortie_locative_front.png` — fiche : tier/verdict premiers, mode B en tiroir.
4. `4_temoin_hors_population.png` — parcelle hors population mode B : **aucun bloc**.
- Loyer marché Estimé (capture 3) : `/mode-b?loyer_marche_m2=14&rendement_cible_pct=7` → loyer
  24 151 €/an [Estimé], achat max 129 k€ @ 7 % (endpoint vérifié ; curseur UI = suite naturelle).
- Assistant non-couvert (capture 5) : `assistant_non_couvert_evidence.json` (réponse déterministe).

---

## Doctrine tenue
- **Règle fiscale** : bilan AU PLAFOND Sourcé, dispositif-agnostique, **zéro badge d'éligibilité** ;
  rien servi sans certitude 2026 (Pinel mort → absent ; Girardin/LLI/Loc'Avantages → ABSENT).
- **Héritage d'étiquette M33** : un bilan contenant un Estimé (travaux) est Estimé.
- **L'absence est dite** (assistant « non couvert à ce jour »), jamais un silence ni un chiffre orphelin.
- **Geste annuel évident** : millésime au nom du fichier config.
