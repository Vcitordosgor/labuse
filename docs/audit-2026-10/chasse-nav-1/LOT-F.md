# LOT F — mobile (émulation iPhone 390×844)

Critère du mandat : sur iPhone, les pages publiques « rien ne déborde, chaque bouton est atteignable ».

| Page (mobile 390px) | Débordement horizontal | Boutons atteignables | Rendu | Verdict |
|---|---|---|---|---|
| `/flash` | NON (scrollW=390=innerW) | « Voir ma parcelle » + saisie adresse/IDU dans le viewport | page complète (79 €, 11 volets) | **PASS** — capture `F-flash-iphone.png` |
| `/reset?token=…` | NON (390=390) | lien Contact atteignable | **gate « disponible sur ordinateur »** | PASS (critère respecté) — capture `F-reset-gate-ordinateur-iphone.png` |
| `/invitation?token=…` | NON | Contact atteignable | gate « disponible sur ordinateur » | PASS (critère respecté) |
| `/login` → `/` → app | — | — | gate « disponible sur ordinateur » (app <1024) | PASS (critère respecté) |

## F-obs1 ⚪ (comportement ASSUMÉ, pas un écart) — reset/invitation/login gatés sur mobile, /flash exempté

- Sur mobile (`screen.width<1024` OU UA mobile OU iPad), les pages d'ENTRÉE dans l'app (reset, invitation, et `/login`→app) affichent l'écran **« LABUSE est disponible sur ordinateur. Ouvrez app.labuse.immo depuis votre ordinateur. »** (+ lien Contact). `/flash` (tunnel de vente autonome) est **exempté** et pleinement utilisable sur mobile.
- **Intentionnel** : `src/labuse/api/onboarding.py:124-143` (`/ordinateur.js` détecte mobile et remplace le body) ; `src/labuse/api/coffre_ui.py:219` « le blocage « disponible sur ordinateur » ne concerne QUE l'app du tunnel ». Cohérent avec CHARGEMENT-1 (gate ordinateur seulement). La page gate ne déborde pas et son unique lien (Contact) est atteignable.
- **À l'attention de Vic** : un client qui clique un lien de **réinitialisation** ou d'**invitation** depuis son téléphone verra « disponible sur ordinateur » et devra basculer sur un ordinateur pour terminer. C'est le parti pris produit (LABUSE = desktop). Si l'on voulait permettre au moins la réinitialisation de mot de passe sur mobile, il faudrait exempter `/reset` comme `/flash`. Signalé, non classé en écart (design explicite).

## Verdict Lot F
**PASS** — aucune page publique ne déborde en iPhone, les boutons/liens visibles sont atteignables. Une observation de design (F-obs1) : seules les pages d'entrée app sont volontairement gatées mobile ; `/flash` fonctionne. Aucun écart dur.
