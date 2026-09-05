# RETOURS-18 — panneau Permis en accordéon

Branche `fix/retours-12`, **un commit** + ce compte-rendu.
Captures : `docs/audit-2026-09/RETOURS-18/captures/` — `avant-{900,560}` (RETOURS-17, tout ouvert) et
`{etat,affiner,liste}-{900,560}-apres` (les trois états × deux hauteurs).
Script de recette : `qa/retours18_shots.mjs` (copie locale dans `frontend/` pour l'exécution).

Contexte : RETOURS-17 a rendu le panneau juste, mais **tout est ouvert d'un coup** (bloc total,
segment à 5 états, bandeau, filtres, liste) — à 560 px « on ne voit pas le bas, c'est bloqué » (Vic).

## Une ligne par travail

- **X1 — accordéon à un seul bloc ouvert** : FAIT. Le bloc total (50 544) et le bandeau Sitadel restent
  **visibles en permanence**. En dessous, trois blocs repliables dont **un seul est ouvert** (ouvrir l'un
  referme les autres) : **Filtrer par état** (ouvert par défaut) · **Affiner** · **Voir les permis**.
  Chaque barre repliée dit son contenu — « Filtrer par état · Récent — 5 580 », « Affiner · aucun filtre »
  (ou « … · PC · 24 m · Saint-Denis »), « Voir les permis · 5 580 dans la sélection ». La liste ne s'affiche
  **plus d'emblée**. Chevron `ChevronSection` (le patron de l'app), clavier (Entrée/Espace ouvrent — bouton
  natif ; **Échap referme**), survol conforme (`.hover-fill`, aplat vert, encre sombre). Aucune couleur
  nouvelle : pastilles des états depuis `lib/permisEtats.ts`, barres au style repliable existant.
- **X2 — le panneau défile jusqu'en bas** : FAIT (cause ci-dessous). Le bloc « Voir les permis » ouvert
  prend **toute la hauteur restante** et défile **seul, verticalement** (pagination par 200 inchangée) ;
  la région d'accordéon défile en secours quand la fenêtre est courte. Vérifié : à **900 / 700 / 560 px**,
  dans les trois états, le **dernier élément est atteignable** (liste `scrollHeight` 7 842 px, dernière
  ligne visible après défilement aux trois hauteurs).

## X2 — la cause du blocage

Le wrapper d'outil qui contient le panneau est **`overflow-hidden`** (`ModulePanel.tsx`, l'`aside` →
`<div class="flex min-h-0 flex-1 flex-col … overflow-hidden p-4">`). Le panneau **ne défile donc jamais
comme un tout** : il comptait uniquement sur le défilement interne de la liste (`flex-1 overflow-y-auto`).
En RETOURS-17, **tout était ouvert en même temps** : à 560 px, la pile fixe (recherche + total + bandeau +
les 5 lignes d'état + barre Affiner + pied) consommait toute la hauteur ; la liste `flex-1` se retrouvait
**écrasée à ~0 px** sous une pile plus haute que la fenêtre, et comme le wrapper est `overflow-hidden`, le
bas (liste + pagination) **n'était pas atteignable** (capture `avant-560` : la barre « Affiner » est déjà
coupée en bas, la liste est hors champ).

Correctif : **l'accordéon supprime la cause** (une seule section ouverte → la pile permanente est réduite
au total + bandeau + trois barres) ; le bloc ouvert reçoit la hauteur restante (`min-h-0 flex-1`) et défile
seul. En secours (fenêtres très courtes), la **région d'accordéon** est `overflow-y-auto` — avant, aucun
conteneur intermédiaire ne pouvait défiler. Les items permanents sont épinglés `shrink-0` (jamais compressés).

## Réutilisation

- **Composant** : la barre repliable réutilise **`ChevronSection`** (`components/panel/ChevronSection.tsx`),
  le patron de chevron de l'app (Couches, Filtres, légende Verdict, cartes de la fiche commune). Note : l'outil
  « Scan patrimoine » cité au mandat fonctionne en **onglets**, pas en accordéon — il n'y avait pas de
  composant d'accordéon « à réutiliser » ; j'ai donc repris le **même geste et le même style de barre
  repliable** que le reste de l'app (en-tête cliquable : titre + résumé + `ChevronSection`, corps sous filet,
  `.hover-fill`) via un petit composant `BlocAccordeon`, et la coordination « un seul ouvert » vit dans M03.
- **Couleurs** : aucune teinte nouvelle — pastilles d'état depuis `lib/permisEtats.ts` (RETOURS-17), barres
  en `border-line-2` / `hover-fill`, comme les tiroirs existants.

## Recette

- **Tests** : `PermisDouble.test.tsx` mis à jour (la liste vit désormais dans le bloc « Voir les permis »,
  replié par défaut → on l'ouvre avant d'attendre des lignes) + **3 tests neufs** : la liste ne s'affiche
  pas d'emblée · accordéon un-seul-ouvert (ouvrir Affiner referme Filtrer par état, la barre repliée dit son
  état + compte) · Échap referme le bloc ouvert. `vitest` : **174 passed** (36 fichiers). `tsc` : 0.
  `vite build` : OK.
- **Gardes RETOURS-16/17** (lisent `ModulePanel.tsx`) : **10 passed** — le refactor n'a pas laissé tomber
  les chaînes requises (états, définitions sur les lignes, total nommé, source unique des couleurs).
- **Backend** : **aucun fichier touché** ce mandat (front seul) — golden et suite pytest inchangés.
- Captures Playwright (`chromium-1217`, 1440×{900,560}, ×2) : les trois états à 900 et 560, + `avant-*`.

## Pièges

- Playwright ne se résout que depuis `frontend/` (copie locale du script, comme RETOURS-16/17).
- Le clic Playwright fait défiler l'élément visé → les captures remettent l'accordéon `scrollTop = 0` avant
  la prise (sinon la barre d'en-tête ouverte disparaît vers le haut).
- Ancien `uvicorn` sur `:8000` (code périmé) → tué et relancé (`DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`).
- Captures « avant » via `git stash` du panneau + rebuild + relance, puis `git stash pop` + rebuild.
- Leftover `frontend/retours16_shots.mjs` (mandat précédent) NON commité.

Un commit pour le lot. **Je ne merge pas.**
