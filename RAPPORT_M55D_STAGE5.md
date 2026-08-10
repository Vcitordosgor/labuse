# RAPPORT M55-D — stage 5 : La Révélation

Branche `feat/m55-d-stage5` (base `main` = stage 4 mergé, dff1922d). Front seul — aucun endpoint,
aucun moteur. tsc 0, vitest 31/31, build vert.

## Le parcours livré
1. **L'appel** — l'étage ② éteint ne montre plus un interrupteur mais LE bouton chaud du panneau :
   **« Analyser les parcelles »** (mint plein, halo). Au-dessus, la ligne de contexte sobre :
   « *N* parcelles notées par LABUSE — **classement du 12/07/2026** » (date = champ `gel` du run
   épinglé, servi par `/v2/modele` ; sous-ligne « Classement versionné, recalculé à chaque mise à
   jour majeure » — jamais « chaque nuit »).
2. **Le décompte** — **3,0 s constantes** : chiffres qui accélèrent (easing cubique, rAF) vers le
   parc du périmètre, « ✓ » à l'arrivée. Pendant l'animation, la **vraie requête `/filtre` part**
   (appel direct **sans retry** — un échec interrompt le rituel sur l'état d'erreur, les retries
   react-query ne peuvent pas masquer la panne au-delà des 3 s ni révéler des nombres périmés).
   Texte : « application de vos critères aux *N* parcelles » — **jamais « calcul du score »**.
3. **La phrase** — structure fixe, **nombres réels** de la réponse : « LABUSE a analysé les *N*
   parcelles de *périmètre*. Selon vos critères : ***R* retenues** — dont *X* brûlantes, *Y*
   chaudes, *Z* en potentiel long terme. » Chaque tier **survolable** (définition d'une ligne,
   `CLIENT.revelation.defTiers`, strings.ts). 0 retenue → phrase honnête + « élargissez vos
   critères ».
4. **Le geste** — « **Voir les parcelles** » → analyse allumée (état stage 4 biunivoque, intact
   jusqu'à cet instant) + section rétractée. Rouvrir → ajuster → « Relancer l'analyse »
   (re-décompte 3 s, constant). Extinction = lien discret « désactiver l'analyse ».

## Validation (tout mesuré)
| Critère | Résultat |
|---|---|
| Chrono clic → phrase (in-page, MutationObserver) | **3,01 s / 3,01 s** (2 lancements — constant, ±0,2 tenu) |
| Nombres de la phrase = réponse `/filtre` | **prouvé** (compte 13 155 + brûlantes 23 + chaudes 188 + réserve 436, comparés à la réponse interceptée) |
| Texte du décompte sans prétention de calcul | revu — « application de vos critères », aucun « calcul du score » ; contexte « classement versionné », pas « chaque nuit » |
| Lien partagé `al=1` | **pas d'animation** : phrase directe, aucun `data-decompte`, aucun bouton d'appel |
| Échec réseau pendant le décompte (mock abort) | **état d'erreur propre** (« L'analyse n'a pas pu aboutir… Vos critères sont conservés. » + Réessayer), pas de « Voir les parcelles » |
| Compte `/filtre` — 5 combinaisons de référence | 9822 · 188 · 1710 · 3770 · 51129 **inchangés** + vieux lien `tv+smin` → 17 |
| `prefers-reduced-motion` | décompte remplacé par une transition simple (**0,41 s**), capture |
| Mobile | rituel complet vérifié (appel → décompte → phrase), capture |

Captures : `s5_appel`, `s5_decompte`, `s5_phrase` (avec un tooltip de tier capté au survol),
`s5_post_retract`, `s5_reduced_motion`, `s5_mobile`.

## Simplifications actées respectées
Pas de questionnaire préalable ; les pré-réglages restent à l'étage ③ (ils ne s'invitent pas dans
la Révélation). La Révélation est une **couche de présentation** : `filters`/`al` (stage 4)
intouchés jusqu'au geste final.

CC ne merge jamais.
