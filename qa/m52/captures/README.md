# M52 · L1 — captures écran réel (avant / après)

Lisibilité du score, carte VERDICT de la fiche parcelle. **Présentation seule — 0 tier,
0 changement de calcul.** Tout chiffre affiché vient d'un calcul existant (`parcel_p_score_v2`,
run servi `q_v8_calibre`).

## Méthode

- **Avant** = commit parent `7c7cb61c` (maquette P0, front encore sans L1).
- **Après** = `046ab315` (L1 livré).
- Pour chaque état : `npm run build` du front réel → API dev `LABUSE_DEV_MODE=1` sur :8000
  (sert la fiche premium `?source=q_v8_calibre`) → Playwright (`capture.mjs`) ouvre la fiche
  via l'omnibox (IDU → loupe) et capture la carte `[data-verdict-card]` + le panneau `aside`.
- Rendu 2×, viewport 1480×1000. Navigateur : chromium headless-shell 1228 du cache
  (`executablePath` explicite — Playwright 1.62 ne fournit plus de build pour Darwin 22 arm64).

## 3 parcelles réelles

| IDU | commune | tier | ×N | rang | percentile |
|-----|---------|------|-----|------|-----------|
| `97418000AT2379` | Sainte-Marie | brûlante | ×22,1 | 7 | 100,0 |
| `97416000EY1406` | Saint-Pierre | déclassée — bâti révélé | ×13,2 | 20 | 100,0 |
| `97416000IL0307` | Saint-Pierre | écartée | ×1,3 | 44245 | 89,67 |

## Ce que L1 ajoute (visible avant→après)

- **Vocab** : « plus probable **de muter** » → « plus probable **d'être vendue** ».
- **Mot d'échelle** sous le ×N (bandes de ×N) : « très forte probabilité relative » /
  « proche de la moyenne ». + **ⓘ** (définition : probabilité *relative*, backtest DVF, ni
  garantie ni prix).
- **Réglette** de position (percentile) — SANS note /100, SANS étoiles (doctrine).
- **Fréquence mesurée par tier**, source DITE à l'écran (« ~20 sur 100 vendues en 2 ans
  contre ~1,5 » + ⓘ « ventes de l'année en cours pas encore toutes publiées », honnêteté M38).
  Affichée seulement pour les tiers fiables (gate-IC) → absente sur déclassée/écartée.
- **« Pourquoi ce score »** : top-5 contributions traduites en FR ; déplié d'office
  brûlante/chaude, replié sinon.

## Fichiers

`L1_{avant,apres}_{brulante_AT2379,declasseB_EY1406,ecartee_IL0307}__{verdict,panel}.png`
(6 avant + 6 après). Script : `capture.mjs`.

## Corrections L1 validées par Vic (repliées dans le geste L2)

L1 validé sur brûlante + écartée. Deux corrections appliquées, re-capturées
`L1_apres_L1corr_*` :

1. **Déclassée/écartée à signal fort (EY1406) — cadrage « signal brut ».** « Déclassée » +
   « très forte probabilité relative » côte à côte = contradiction famille M48 (statut mort
   à côté d'une promesse). Corrigé : hors tiers servables (`verdict.tier == null`) ET ×N ≥ 2,
   le ×N devient **« signal brut »** (teinte terre éteinte), le mot passe **atténué** avec
   « · écartée », et un encadré dit « la parcelle porte un signal fort (×N) **mais elle est
   écartée** : [motif] — l'écartement prime. La fréquence par tier ne s'affiche pas. » + ⓘ
   doctrine étage 0 (M5). « Pourquoi ce signal (avant l'écart) » ouvert. La fréquence reste
   absente (correct). L'écartée simple ×1,3 (< 2) NE déclenche PAS ce cadrage — reste sobre.

2. **Réglette sur ×N (échelle LOG), plus le percentile rang.** Le percentile rang plaçait
   l'écartée ×1,3 à ~89,7 % (« très forte ») car mieux classée que ~90 % des parcelles —
   contradiction avec « proche de la moyenne ». Corrigé : `verbal.reglette_pct` =
   log10(×N / 1) / log10(25 / 1) × 100, bornée [1, 99], ancres en config
   (`echelle_verbale_score.yaml` → `reglette`). Résultat : IL0307 ×1,3 → **8,6 %** (près de
   « moyenne ») ; EY1406 ×13,2 → 80,0 % ; AT2379 ×22,1 → 96,2 %.
