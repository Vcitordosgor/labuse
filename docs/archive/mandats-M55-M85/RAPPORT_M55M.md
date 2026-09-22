# RAPPORT M55-M — Panneau : place au listing

Branche `feat/m55-m` (base `5eac45fa` = M55-K mergé sur main). **NON mergée** — Vic
valide et merge lui-même. Trois points front, un commit atomique par point.

- Précondition vérifiée : `feat/m55-k` est mergé sur main (`5eac45fa Merge branch 'feat/m55-k'`).
- `tsc -b` 0 · `vitest` 32/32 vert · `npm run build` vert · console 0 erreur nouvelle.
- Captures : `reports/m55-m/captures/` (10 PNG, dev vite HMR = code courant). Harnais
  `qa/m55m_capture.mjs` (channel chrome).

## ⚠ Fichiers PARTAGÉS avec M55-L (pour l'ordre des merges)

Zones globalement disjointes (M55-M = panneau, M55-L = fiche), **mais deux fichiers
communs** — Vic devra ordonner / re-résoudre au 2ᵉ merge :

| Fichier | Ce que M55-M y fait | Risque M55-L |
|---|---|---|
| `frontend/src/store/useApp.ts` | +`panneauSection: … \| 'listing'` ; +`analyseRecap`/`setAnalyseRecap` ; `retourFiltres` nettoie `analyseRecap` | M55-L touche aussi le store (mémoire fiche/session pt5, `tiroirOuvert` pt10) → **conflit probable**, zones distinctes de l'objet |
| `frontend/src/lib/strings.ts` | clé `revelation.relancer` → `revelation.changerFiltres` = « Changer les filtres » | M55-L fait des renommages strings (pt9 « + CRM », libellés fiche) → **conflit possible** |
| `frontend/src/lib/filters.ts` | `resumeCriteres(f, labels, max=4)` — 3ᵉ param optionnel | M55-L peu probable ici, à surveiller |

`App.tsx`, `LeftPanel.tsx`, `FiltreLabuse.tsx` : propres au panneau, aucun recouvrement attendu.

---

## Point 1 — Le listing prend la place : les deux sections se rétractent

**Constat.** Après « Voir les parcelles » (ou l'analyse révélée), la section Filtres
restait ouverte (cible M55-J) et le listing n'avait pas la hauteur.

**Modification.** L'automate d'accordéon gagne un **troisième état** à champ unique :
`panneauSection: 'couches' | 'filtres' | 'listing'`. Nouvel invariant conforme à la
décision Vic : jamais deux sections ouvertes (inchangé) ; **deux fermées légal
uniquement en `'listing'`** (quand `verdict` — un listing est affiché). Hors listing,
l'invariant M55-I tient (exactement une ouverte).

Transitions (explicites, à champ unique) :
- affichage d'un listing (`verdict` false→true, tri factuel OU analyse révélée) →
  `'listing'` (les deux sections se rétractent). Remplace la cible M55-J.
- toggles : cliquer une section **fermée** l'ouvre (exclusivité) ; cliquer la section
  **ouverte** la **referme vers `'listing'`** — seulement si un listing existe
  (`verdict`) ; sinon no-op (invariant M55-I hors listing).
- « Retour » (`store.retourFiltres`) inchangé → Filtres ouvert éditable.
- chargement sans listing → Couches ouverte (défaut inchangé).
- **rechargement avec listing** (`al=1` / `v=1` factuel) : le store boote `verdict=false`,
  l'effet de boot (App.tsx) l'allume → la transition restaure `'listing'` (plus le défaut
  Couches). Titres des sections rendus honnêtes (`closable` → « Refermer — rendre la
  place au listing »).

`sectionFill` (M55-K) inchangé : `verdict ⇒ false ⇒` sections plafonnées, `ResultsSection`
`flex-1` remplit. Chemins rejoués (captures `p1-*`) : listing → rouvre Filtres → rouvre
Couches (Filtres se referme) → referme → listing ; Retour → Filtres éditable. Jamais deux
ouvertes ; listing visible dès qu'aucune section n'est ouverte.

**Fichiers.** `store/useApp.ts`, `components/panel/LeftPanel.tsx`.
**Commit.** `9ceed191`.

---

## Point 2 — « Relancer l'analyse » → « Changer les filtres »

**Constat (imposé par le mandat, effectué AVANT tout renommage).** Le bouton principal
de l'état post-analyse était câblé sur `lancer()` = **rejouer le rituel sur les filtres
FIGÉS** (`analyseActive` gèle le formulaire). Même entrée → même résultat : le bouton ne
« changeait » rien, et surtout ne « défigeait » pas les filtres. Le libellé « Relancer
l'analyse » ne mentait pas encore, mais **« Changer les filtres » aurait menti** appliqué
à cette action (le mandat prévoit ce cas : « si l'action réelle ne correspond pas…, le
signaler avant de renommer — un libellé ne doit jamais promettre autre chose que ce que
fait le bouton »).

**Décision.** Puisque le point 3 exige par ailleurs qu'aucune chaîne ne dise plus
« Relancer l'analyse » (grep) et que la cible produit est bien « Changer les filtres »,
j'ai **rendu l'action honnête** plutôt que de laisser le point non fait : nouvelle action
`changerFiltres()` = **défiger les filtres et rendre la main** — coupe `analyseLabuse`
(le formulaire redevient éditable, `analyseActive` retombe) **sans toucher `verdict`** →
le listing reste affiché (il bascule en tri factuel) pendant l'ajustement, puis
« Demander à LABUSE » relance. Distinct de « Désactiver l'analyse » (danger rouge) qui,
lui, éteint `verdict` et quitte la vue résultats. (Capture `p2-apres-changer-filtres` :
formulaire éditable de retour, analyse coupée, listing conservé.)

Note : renommer sans changer l'action aurait rendu l'ancien « Relancer » quasi inutile
(rejouer des filtres gelés = idempotent). Le nouveau comportement est le seul qui rend le
libellé vrai. **Si Vic préfère conserver un vrai « relancer » ici, revert trivial** (une
ligne : `onClick={lancer}` + libellé).

- Libellé dans la source unique : `revelation.relancer` **renommée** `changerFiltres` =
  « Changer les filtres » (0 référence pendante). `data-relancer` → `data-changer-filtres`.
- Traitement visuel inchangé (action principale, fond vert) ; « Désactiver l'analyse »
  inchangé.
- Grep « Relancer » résiduel : `relancerCta` = « Relancer sur les nouveaux critères »
  (filet *stale* M55-J, quand un chemin externe bouge les filtres) et les relances IA
  (`relanceBudget`/`relanceCommunes`). **Actions de relance honnêtes dans leurs contextes
  propres, hors périmètre de ce renommage** — laissées telles quelles (signalé).

**Fichiers.** `lib/strings.ts`, `components/panel/FiltreLabuse.tsx`.
**Commit.** `30eeb29b`.

---

## Point 3 — Fusion des critères dans le bandeau, suppression du bloc « ANALYSE EN COURS »

**Constat.** La phrase de critères était portée par le bloc « ANALYSE EN COURS » (dans le
panneau Filtres, `data-analyse-recap`), avec « Filtres figés — Relancer ou Désactiver… ».

**Modification (décision Vic : la phrase fusionne, le reste saute).**
- `store.analyseRecap` : le récap des critères **du RUN**, figé au lancement depuis le
  **snapshot** (`snapFilters`) — jamais l'état courant des filtres (même invariant que la
  carte d'analyse M55-J p1). Écrit par `FiltreLabuse.lancer()`, nettoyé à `resetTout` /
  « Désactiver » / « Changer les filtres » / `retourFiltres`.
- `resumeCriteres(f, labels, max=4)` : `max` réglable — le bandeau stocke le récap
  **complet** (`max=∞`, aucun « … ») pour le `title` ; la troncature d'affichage est CSS
  (`truncate`).
- **Bandeau** (`VerdictHero`) : sous « ✓ Analyse LABUSE affichée » + « Retour », une ligne
  `data-analyse-criteres` — **tronquée proprement** (`truncate`, jamais de débordement qui
  casse le bandeau) + **détail complet au survol** (`title` = récap complet). Absente en tri
  factuel (pas de run décrit). Les deux entrées « Info classement » / « Info scoring »
  (M55-K) restent.
- **Rechargement** (`al=1`) : le snapshot de session est perdu → `App.tsx` réamorce
  `analyseRecap` depuis les filtres **restaurés** (= ceux du run, persistés en URL, aucune
  divergence possible à cet instant) → le bandeau porte les critères même au reload.
  L'invariant tient : dès qu'un filtre diverge **en session**, `analyseRecap` reste figé.
- **Bloc supprimé partout** : `data-analyse-recap` (« ANALYSE EN COURS / Filtres figés — … »)
  retiré du décompte ET du post-analyse (là où M55-K l'avait conservé). Quand l'analyse est
  active, le panneau Filtres ne rend plus de formulaire (il réapparaît via « Changer les
  filtres » / « Désactiver »). **Grep** : plus aucune occurrence du bloc ; les « Analyse en
  cours… » restants sont les spinners des **modules Outils** (violet), hors périmètre.

**Vérification bug M55-J** (filtre déplacé après lancement, chemin externe) : `analyseRecap`
n'est écrit que par `lancer()` → le bandeau continue d'afficher les critères **du run**.

**Captures.** `p3-bandeau-1critere` (« terrain nu »), `p3-bandeau-4criteres` (« Cilaos,
> 500 m², zone U, terrain nu »), `p3-bandeau-long-340` / `p3-bandeau-long-240` (8 critères :
affichage tronqué au panneau, `title` = récap complet identique aux deux largeurs).

**Fichiers.** `store/useApp.ts`, `lib/filters.ts`, `components/panel/LeftPanel.tsx`,
`components/panel/FiltreLabuse.tsx`, `App.tsx`.
**Commit.** `e3805d1c`.

---

## Validation

| Contrôle | Résultat |
|---|---|
| `tsc -b` | 0 |
| `vitest run` | 32/32 |
| `npm run build` | vert |
| Console (parcours analyse + Changer les filtres) | 0 erreur |
| Persistance filtres (35 champs + `al=1`) | intacte (write/read hash non modifiés ; `merged` = même valeur) |
| Accordéon : chemins rejoués | jamais 2 ouvertes ; listing visible section fermée (captures p1-*) |
| Bandeau 1 / 4 / long critères | OK, troncature + title complet (captures p3-*) |
| Non-régression sectionFill M55-K / accueil M55-I / mode factuel | OK |

**Ne pas merger.** Deux branches (M55-M puis M55-L) restent non mergées ; Vic merge les
deux dans l'ordre de son choix — attention aux fichiers partagés `store/useApp.ts` et
`lib/strings.ts` (tableau ci-dessus).
