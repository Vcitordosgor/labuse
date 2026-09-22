# RAPPORT M55-D — stage 7 : le funnel vivant + dernier ménage

Branche `feat/m55-d-stage7` (base `main` acefb7ec, **stage 6 mergé — précondition vérifiée**).
Front + un appel count annulable — aucun moteur. tsc 0, vitest 32/32, build vert.

## 1. Le compteur vivant (livré)
- **« N parcelles correspondent »** en bas de la section Filtres, visible dès qu'un filtre est
  posé. Mise à jour à chaque changement : `getFiltreCount` (nouveau — `/filtre` limit 0,
  **annulable**), **debounce 400 ms + AbortController** (les appels obsolètes sont annulés),
  nombre en **opacité réduite** pendant le fetch (aucun spinner). Toujours la réponse `/filtre`
  réelle. **0 → « Aucune parcelle ne correspond — élargissez vos critères »** (capture `s7_zero`).
- **Bouton contextuel** : « **Analyser ces 9 822 parcelles** » — même compteur, **égalité
  prouvée** (9 822 == 9 822, DOM). Zéro filtre → « **Analyser les 431 663 parcelles** » (parc du
  périmètre ; nota : une commune posée compte comme filtre — Communes est le rang 1 — d'où
  « Analyser ces 51 129 » quand Saint-Paul est cochée).
- **Rituel 3 s intact** : mesuré **3,01 s**. Deux registres — le compteur discret, la cérémonie à
  l'analyse.

## 2. Retraits (décisions Vic)
- **« Contraintes de secteur »** a quitté le panneau Filtres (les flags restent en fiche et en
  couches, rien n'y change). **Aucun état orphelin** : plus aucun writer UI de `filters.flags`
  (vérifié 0-caller) ; la clé URL legacy **`fl=` est ignorée proprement à la lecture** — vieux
  lien `fl=pente,ravine&smin=2000` → **0 erreur page**, compteur = surface seule (9 822). Le
  param backend `flags` reste intact (API).
- **« Puis-je construire ? »** et toute pédagogie résiduelle retirées (`DROIT_DIFFERES`,
  `VIGILANCES`, `CONTRAINTES` supprimés, 0-caller).

## Non-régression (vert)
- **5 combinaisons `/filtre` identiques** (états reproduits — C4 porte des flags, testée au
  niveau API puisque l'UI/URL ne les portent plus) : 9822 · 188 · 1710 · 3770 · 51129.
- Vieux liens compatibles, **y compris ceux portant des flags contraintes** (ignorés sans erreur).
- **Compteur vivant = N du bouton** (test d'égalité) ; rituel 3,0 s ; **mobile vérifié**
  (compteur visible, capture `s7_mobile`).
- Captures : `s7_compteur_bouton`, `s7_zero`, `s7_panneau_sans_contraintes`, `s7_mobile`.

CC ne merge jamais.
