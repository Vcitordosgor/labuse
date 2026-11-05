# Harnais NU5-F — accessibilité & mise en page

Tests automatiques rejouables pour l'audit NU5-F (lecture seule). Deux volets :

1. **Verrou mobile** — un vrai iPhone/iPad (descripteurs Playwright `devices`) ne doit voir que
   l'écran `data-ecran-ordinateur` (« LABUSE est disponible sur ordinateur »), l'app n'étant jamais montée.
2. **App rendue** (fenêtre de bureau rétrécie à 390 px, non verrouillée car `window.screen.width`
   reste physique) — sur chaque vue du rail × {390, 1440} :
   - **axe-core** WCAG 2.0/2.1/2.2 niveau A + AA (violations seulement) ;
   - **débordement horizontal** (`scrollWidth − clientWidth`) ;
   - **cibles tactiles** < 24 px (WCAG 2.2 §2.5.8 AA) et < 44 px (cible du mandat) ;
   - repères : `main`, `h1`, lien d'évitement, `th` sans `scope`, champs sans nom, régions live.

Code de sortie **≠ 0** si « échec dur » : débordement horizontal à 390 px, violation axe
`serious`/`critical`, ou verrou mobile absent. C'est le garde-fou qu'une CI ferait respecter.

## Prérequis

- Backend LABUSE sur `:9780`, vite sur `:6980` (cf. `../RAPPORT.md` §Méthode).
- `npm install` ici (installe `axe-core` + `playwright` ; navigateurs via le cache ms-playwright).

## Lancement

```bash
npm install
# si le cache ms-playwright ne correspond pas à la version installée, pointer un binaire Chromium :
LABUSE_CHROMIUM="$HOME/Library/Caches/ms-playwright/chromium-1148/chrome-mac/Chromium.app/Contents/MacOS/Chromium" \
  node audit_a11y.mjs
# base personnalisable : LABUSE_SOCLE=http://127.0.0.1:6980/socle/
```

Écrit `resultats.json` (versionné : la sortie de la passe du 5/11/2026).

## Lecture des résultats

- `verrouMobile` — doit être `ecranOrdinateur:true, appMontee:false` pour iPhone **et** iPad.
- `pages[]` — une entrée par vue×viewport : `axeViolations`, `miseEnPage`, `axeSeriousPlus`.
- `echecsDurs` — liste dédupliquée des échecs bloquants.

> Note : axe ne voit que le DOM **rendu à l'instant t**. Les surfaces conditionnelles (fiche parcelle,
> fil Copilote/John actif, modales d'outils) sont à ouvrir à la main ou à scripter en plus — l'audit
> manuel du RAPPORT les couvre.
