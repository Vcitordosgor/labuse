# FIX COSMÉTIQUE (polish) — front pur

**Branche** : `feat/fix-cosmetique` (NON mergée — Vic valide à l'œil + merge). **Date** : 2026-07-15.
**4 commits séparés**, **front pur** (git : aucun fichier `.py`, zéro scoring/données/logique métier).
Points du check : 3, 9(→3 tri), 27, 33, 38, 40, 41.

| # | Commit | Item | Fichiers |
|---|---|---|---|
| A | `e285bc0` | Loading mauve sur outils lents (33/38/40/41) | `Loading.tsx`, `ModulePanel.tsx`, `moteurs.tsx` |
| B | `6c386ee` | Marges CRM (3) | `Kanban.tsx` |
| C | `a50478d` | Panneau RÉSULTATS/tri plus digeste | `ResultsSection.tsx` |
| D | `6e01742` | Flèche retour « ← Outils » (27) | `ModulePanel.tsx` |

---

## FIX A — Indicateur de chargement mauve (réutilisable)
**Problème** : mode bailleur (M06), promesses mortes (M04), simulateur PLU (M15), ZAN (M17) n'affichaient **rien** pendant le fetch → perçus « cassés ».
**Fix** : le composant existant `Loading` gagne un prop **`accent='violet'`** (`#B497F0`, charte outils) — **un seul composant réutilisable**, pas 4 spinners. Branché sur les 4 outils avec un message honnête (« Analyse en cours… » / « Recalcul à blanc en cours… »). Réutilisable pour tout autre outil lent (même API `<Loading accent="violet" label="…" big />`).
**Preuve** : `fixA-loading-bailleur.png`, `fixA-loading-promesses.png`, `fixA-loading-zan.png`, `fixA-loading-simulplu.png` (3 points mauves + label, capturés **pendant** le chargement via délai réseau injecté).

## FIX B — Marges CRM
**Problème** (point 3) : cartes du Kanban trop serrées / mal alignées.
**Fix** (fonction inchangée) : padding carte `p-3→p-3.5` ; interlignes `mt-0.5→mt-1` (IDU→surface) et `mt-2→mt-2.5` (→ ligne tier) ; ligne tier/score en `flex-wrap gap-x-2 gap-y-1` (aligné, respire, ne crame pas sur carte étroite) ; priorité `shrink-0` à droite ; écart entre cartes `gap-2→gap-2.5`, container `px-2→px-2.5`.
**Preuve** : `fixB-crm-avant.png` / `fixB-crm-apres.png`.

## FIX C — Panneau RÉSULTATS / tri (point 3, « pas très joli »)
**Problème** : « triés par rang P · ×N · surface · commune » flottait collé à droite, sans alignement ni hiérarchie ; manque d'air.
**Fix** (fonction inchangée — `setSort`/`counts` intacts) : label **« TRIER »** + **contrôle segmenté** (pastilles, actif en menthe `bg-mint/15`), aligné à gauche sous « RÉSULTATS » ; **séparateur** (`border-t`) + air avant les compteurs de tiers → **hiérarchie nette** « trier » vs « compteurs ». Charte sombre respectée (menthe = accent de la partie carte/résultats, comme l'existant).
**Preuve** : `fixC-tri-avant.png` / `fixC-tri-apres.png` (les compteurs à 0 sur la capture = état de chargement du headless ; la logique des compteurs est inchangée).

## FIX D — Flèche retour « ← Outils »
**Problème** (point 27) : la flèche retour vers le menu Outils était un texte mono 10 px inline dans le fil d'Ariane → on la cherchait.
**Fix** : **pastille bordée mauve**, plus grosse, zone de clic élargie (`px-2.5 py-1`), libellé « ← Outils » clair, hover qui allume la bordure `#B497F0`. Le reste du fil d'Ariane (« › MODE BAILLEUR ») inchangé.
**Preuve** : `fixD-retour-avant.png` / `fixD-retour-apres.png`.

---

## Non-régression & garanties
- **Front pur** : `git diff --name-only main..HEAD` = 5 fichiers `.tsx`, **aucun `.py`**, zéro scoring/cascade/étage 0/run/données. Aucune logique métier touchée (que du style + états d'affichage).
- `tsc --noEmit` vert. Les outils aboutissent toujours au bon résultat après le loading ; les compteurs/tri fonctionnent ; carte/fiches intactes.
- Le loading (A) est **un seul composant** (prop `accent`), pas 4 implémentations.
- Tout se valide **à l'œil** (captures avant/après fournies) — Vic est juge, notamment sur C (subjectif).

*4 commits séparés sur `feat/fix-cosmetique`. Pas de merge. Pas de logique d'outil touchée (faisabilité ranking = LOT 3, séparé).*
