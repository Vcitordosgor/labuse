# ÉTUDE V6-2 — Lot 4 : jauge d'enveloppe estimée à l'étape 3

Donner, **avant le calcul complet**, un repère instantané : le programme saisi tient-il dans l'enveloppe
que le terrain peut offrir ? Sans lancer le moteur.

## Endpoint rapide (sans moteur)
`POST /modules/etude/jauge {idus, type_projet}` → `jauge_payload` : même chargement que la règle de
stationnement (terrain + règles, **sans LiDAR ni recherche**) → **~0,2 s**. Renvoie zone d'implantation,
niveaux (hauteur PLU / étage), coef plancher, barème places par type, et `estimable`.

## Formule (étiquetée « estimé »)
**enveloppe ≈ (zone d'implantation − sol du stationnement aérien) × niveaux (hauteur PLU) × coef plancher.**
Le sol du stationnement est estimé en direct depuis le programme saisi : `places = Σ nb[t] × barème[t]`,
`sol = places × 18 m²/place` (aérien). Le programme saisi (m²) est comparé à cette enveloppe.
- Étang-Salé UA, 23 T2 + 6 T3 : programme **1 708 m²** vs enveloppe **(1 155 − 576) × R+3 × 0,8 = 1 854 m²**
  → **92 %, vert** (tient).

## Comportements (mandat)
- **Jauge grise « non estimable »** si une donnée manque (zone d'implantation ou hauteur) — `estimable=false`,
  le(s) champ(s) manquant(s) listés.
- **Bandeau rouge** si le programme dépasse l'enveloppe estimée (barre + message « réduisez ou testez le
  sous-sol »).
- **Étiquette « estimé »** toujours visible (jamais présentée comme un chiffre servi).
- Le détail du calcul est affiché (zone − stationnement × niveaux × coef).

## Divergence estimation ↔ calcul (> 20 %)
Au RÉSULTAT, si l'enveloppe estimée (étape 3) et la capacité maximale CALCULÉE (SDP) s'écartent de plus
de **20 %**, le résultat le dit explicitement (récit « Capacité maximale », ligne ambre) : la jauge était
*optimiste* ou *prudente*, fiez-vous au calcul. Vérifié Étang-Salé : estimation ≈ 1 854 m² vs calcul
≈ 1 952 m² → **5 % (< 20 %)**, pas de note (l'estimation est fidèle).

## Tests
- `EtudeV6.test.tsx` (Lot 4) : jauge OK sous l'enveloppe (vert, « estimé », R+3) + rouge au dépassement ;
  jauge « non estimable » (grise) quand une donnée manque ; divergence > 20 % signalée au résultat.
- `tests/test_etude_v6_capacite.py::test_jauge_enveloppe_estimee` (reel) : rapide, estimable, R+3, coef,
  barème (T2=1, T3=1,5).

## Vérifié
tsc 0 · vitest 296/296 (EtudeV6 18/18) · pytest implantation · chasse_docs 20·0 · chasse_donnees 23·0·2 SKIP.
Capture `captures/lot4-jauge-etape3.png`.
