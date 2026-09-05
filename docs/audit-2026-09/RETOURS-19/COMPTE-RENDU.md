# RETOURS-19 — états actifs, survols et barres de défilement

Branche `fix/retours-12`, **un commit** (front seul) + ce compte-rendu.
Origine : recette Vic du 06/09. Aucune couleur nouvelle — tout sort de la DA (`--fill-mint`/`--ink`,
`--fill-mauve`/`--mauve-ink`, `--fill-amber`, `--mint`, `--pj-jaune`). Règles définies **une fois** dans
les composants/CSS partagés. Captures avant/après : `docs/audit-2026-09/RETOURS-19/captures/`.

> Note : un premier commit `ab106976` (même nom « RETOURS-19 ») avait déjà traité le chevron sans carré
> noir sur barre verte (partie de Y1) ; ce lot couvre Y1→Y5 (et généralise ce geste aux icônes).

## Une ligne par règle

- **Y1 — état actif = vert opaque, contenu inversé sombre** : FAIT. Corrigés : **rail** (`.rail-item.active`
  passait d'un fond teinté `mint-bg` — moins marqué que le survol — à **vert opaque** ; c'est LUI qui porte
  « menu Outils ouvert », mauve opaque pour l'IA) ; **fond de carte** (bouton ouvert + entrée active du menu :
  `bg-mint/10 text-mint` → `bg-mint text-mint-ink`, y compris les millésimes ortho) ; **sélecteur de périmètre**
  (« Toute l'île » : vert opaque quand le menu est ouvert OU qu'un périmètre est actif — pastille + chevron
  inversés) ; **chevrons** `ChevronSection` (pas de fond sur barre verte — déjà `ab106976` ; ici le contour
  au repos passe `border-line-2/70` → **plein**, visible sur tous les fonds) ; **chips « Affiner » du panneau
  Permis** (période/type/géocodage : teinté → vert opaque, cohérent avec les lignes d'état déjà opaques).
- **Y2 — survol = opaque de sa propre couleur, contenu inversé sombre** : FAIT. Les **icônes** ne posent plus
  de **carré sombre** sur l'aplat : `.acc-tile` (icônes des raccourcis « Explorer la carte », « Suivre le
  marché »…) et `.itile` (tuiles d'outils partagées) passent au survol en **fond transparent (le vert/mauve
  de la carte), contour + glyphe en encre sombre** — même geste que le chevron (Y1). Cela **annule
  RETOURS-11 T2** (03/09, tuile à fond sombre + glyphe vert) : voir « décision inversée » ci-dessous.
  « + CRM » / « + Projet » remplissaient déjà en vert/ambre opaque (`.hover-fill` / `.hover-fill-amber`,
  `.act-cmp` / `.act-amber-on`) — conformes, inchangés.
- **Y3 — deux actions sur une ligne = deux zones visibles** : FAIT. Dans la liste des communes (menu de
  périmètre), le `.hover-fill` (vert) est passé de **toute la ligne** à la **zone principale seule** ;
  « voir la fiche → » garde sa zone jaune (`.hover-jaune`, opaque au survol), chaque zone son arrondi, un
  léger écart les sépare. Plus de bande verte continue : le survol dit lequel des deux se déclenchera.
- **Y4 — barres de défilement** : FAIT. Style **unique** (`index.css`) : pouce `--line-2` au repos →
  **vert opaque `--mint` au survol**, transition douce `.15s`. `::-webkit-scrollbar-thumb:hover` couvre
  toutes les zones défilantes de l'app d'un coup (panneau Cartes, listes, panneau d'outil, Sources).
- **Y5 — deux corrections ponctuelles** : FAIT. (a) Panneau Permis : la phrase Sitadel est **resserrée sur
  une ligne** (« Sitadel : les permis autorisés, pas l'instruction en cours. ») + `truncate` (jamais de
  défilement latéral ; l'infobulle porte la phrase complète). (b) Bouton « ← Outils » : **infobulle
  « Revenir au menu Outils » retirée** (le libellé le dit déjà).

## Décision DA inversée (à valider)

**RETOURS-11 T2 (Vic 03/09)** avait fait passer les tuiles d'icône (accueil `.acc-tile` + outils `.itile`)
en **FOND SOMBRE avec glyphe vert** au survol. Y2 (06/09) demande explicitement l'inverse pour les icônes
(« fond vert opaque, contour et glyphe en sombre ») — c'est le **même principe que le chevron sans carré
noir** (Y1) : plus aucune pastille sombre sur un aplat vert. J'ai donc **inversé T2** pour `.acc-tile` et
`.itile`. Si le fond sombre de T2 était voulu ailleurs, le signaler — c'est une seule règle CSS à rebasculer.

## Boutons d'état — inventaire (règle Y1)

Corrigés ce lot : rail (`.rail-item.active`, toutes sections + Outils), fond de carte (bouton + menu +
millésimes), sélecteur de périmètre, chevrons (`ChevronSection`), chips « Affiner » du panneau Permis.
Déjà conformes (vert/ambre opaque quand actif) : « 3D » et outils de mesure de la carte (RETOURS-9 Q9),
lignes d'état du panneau Permis (RETOURS-17), « + CRM » / « + Projet » (fiche).

**Non traités ce lot — le MÊME motif teinté existe ailleurs** (`bg-mint/10 text-mint` en état actif) :
~90 occurrences dans ~40 écrans (onglets/segments de Radar, Étude de zone, Renouvellement, admin, fiche…).
Les basculer en bloc est risqué (chaque contenu doit être vérifié lisible sur le vert). **Recommandation** :
un passage dédié écran par écran, ou — mieux — une **classe d'état partagée** (`.seg-actif`) posée une fois
et réutilisée, pour ne plus jamais re-décider au cas par cas. Signalé ici, non corrigé en masse à l'aveugle.

## Non applicable / constaté

- **Cartes de la Veille** (Y2) : les cartes promoteur de `VeillePromoteurs` ne sont pas cliquables **en
  entier** (seul le lien parcelle l'est, style lien vert souligné) — aucun `.hover-fill` ne s'y applique
  sans en faire des boutons (changement de comportement, hors périmètre d'un lot d'états/survols). Laissé
  tel quel, signalé.
- **← Outils** (Y1) : ce fil d'Ariane est un **retour** ; ouvrir le menu Outils démonte le panneau
  (`setModule`↔`toggleOutils` s'excluent), donc il n'est jamais affiché « quand le menu Outils est ouvert ».
  L'indicateur réel d'« Outils ouvert » est l'entrée **Outils du rail** (corrigée en vert opaque). Le bouton
  de retour est conservé en pastille mint bordée (tooltip retirée).

## Recette

- `vitest` : **174 passed** (36 fichiers). `tsc` : 0. `vite build` : OK. Aucun fichier backend touché
  (front seul) — golden et suite pytest inchangés.
- Captures Playwright (`chromium-1217`, ×2) avant/après : accueil-survol (icône), commune-survol-principal
  / commune-survol-fiche (Y3), perimetre-actif, fond-carte-ouvert, rail-outils-actif, permis-sitadel.

## Pièges

- Playwright depuis `frontend/` (copie locale des scripts `qa/retours19*.mjs`).
- Captures « avant » via `git stash` des 5 fichiers + rebuild + relance, puis `git stash pop` + rebuild.
- uvicorn `:8000` périmé → kill + relance `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib`.
- Leftover `frontend/retours16_shots.mjs` (mandat antérieur) NON commité.

Un commit pour le lot. **Je ne merge pas.**
