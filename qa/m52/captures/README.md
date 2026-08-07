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

## ⚠ À trancher par Vic (constaté, NON corrigé — c'est une décision L1)

**Réglette incohérente sur l'écartée.** La réglette est mappée sur `percentile` (rang :
89,67 = mieux classée que ~90 % des parcelles, car rang 44245/~431 663), tandis que le
*mot* est mappé sur la bande de **×N** (×1,3 → « proche de la moyenne »). Résultat : sur
`IL0307`, le curseur blanc est collé à « très forte » alors que le libellé dit « proche de
la moyenne ». Cohérent pour brûlante/déclassée (percentile 100). Deux échelles racontent
deux histoires. Options : (a) mapper la réglette sur le ×N (log) plutôt que le percentile
rang ; (b) garder le percentile mais changer les ancres (« mieux classée que X % ») ; (c)
masquer la réglette hors tiers hauts. → arbitrage présentation.
