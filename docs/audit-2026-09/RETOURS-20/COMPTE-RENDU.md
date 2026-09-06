# RETOURS-20 — COMPTE-RENDU (Z1 · Z2 sur deux sections · Z3)

Branche `fix/retours-22`, partie de `origin/main` à jour. Un commit, **rien n'est mergé, rien n'est
poussé**. Z4 (scrollbar Veille + survol des icônes d'accordéon) était **déjà livré** par RETOURS-21
lot C (sur main : `94eee23e`) — non refait ici. Les captures « avant » de RETOURS-21 lot C servent de
référence (`docs/audit-2026-09/RETOURS-21/captures/reglement-avant.png`, `reseaux-avant.png`).

La maquette fixe la structure et les espacements ; **couleurs et polices = variables de l'app**
(`--mint`, `--amber`, `--txt-*`, `--line`, `--mono`…), **aucun hex recopié** depuis le fichier de
maquette. **La donnée ne bouge pas** : mêmes chiffres, mêmes libellés, mêmes sources, mêmes CTA — ce
sont des changements de PRÉSENTATION (les expressions de données et les conditions sont intactes).

## Z1 — les six composants partagés

Quatre existaient déjà (RefDrawer, GroupLabel, PorteOutil, StepProv) ; ils sont **alignés** sur la
grammaire, et **deux blocs manquants** (ligne de fait, vigilance/rappel) sont **créés**. Tout vit dans
`frontend/src/components/fiche/primitives.tsx` (+ la grammaire CSS scopée `.fiche-v6` dans
`frontend/src/styles/index.css`).

| # | Bloc | Composant | Ce qui a changé |
|---|------|-----------|-----------------|
| 01 | **En-tête** | `RefDrawer` (`.tiroir`) | déjà conforme (icône 32 · titre 14 · sous-titre · un seul objet à droite · chevron ; survol Z4 déjà livré). Inchangé. |
| 01b | **Statut** | `StatusLine` (`.f-status`) | **créé** — puce + phrase, jamais une boîte (maquette `.status`). |
| 02 | **Kicker** | `GroupLabel` (`.sec`) | **slot droit optionnel** ajouté (renvoi d'article / badge d'état) ; le filet pousse le slot à droite. |
| 03 | **Ligne de fait** | `FactRow` (`.f-row`) | **créé** — libellé gauche gris · valeur mono à droite (chiffres tabulaires, unité en `<small>`) · source SOUS la ligne · filet entre lignes ; `tone` `mute` (absent, gris atténué) / `warn` (à vérifier, ambre). |
| 04 | **Badges** | `StepProv` (`.b`) + `RefLink` (`.f-ref`) | badge **aligné** : mono 10 px, contour (plus d'aplat), même taille partout ; bordures dérivées des tokens (`color-mix`), jamais un hex. Renvoi d'article = lien mono `↗`. |
| 05 | **Vigilance / rappel / note** | `Vigilance` (`.f-vig`) · `Rappel` (`.f-rappel`) · `FactNote` (`.f-note`) | **créés** — vigilance = filet ambre à gauche (pas de boîte) ; rappel = fond un cran plus clair, sans bordure ; note de méthode 11,5 px sous la ligne. |
| 06 | **Action** | `PorteOutil` (`.porte-outil`) | inchangé (déjà en pied de section, gabarit unique). |

`StatusLine` et `Vigilance` sont exportés mais pas encore appelés dans les deux sections traitées (le
`plu_fraicheur`/`aper`/`radar_procedure` sont dé-boxés en filet gauche inline, cf. Z3) — ils sont prêts
pour les sept sections restantes.

## Z2 — deux sections passées sur les nouveaux blocs

### Règlement et zonage (tiroir « Urbanisme », `Fiche.tsx`)
- **`ReglementPluBlock`** : la carte encadrée « RÈGLEMENT PLU » (`card-elev`) disparaît. Chaque zone
  est un **kicker** « Règlement — zone U4c » avec le renvoi « voir l'article » dans le **slot droit**,
  suivi de **lignes de fait** (`FactRow`) : Hauteur max · Emprise · Reculs · Pleine terre ·
  Stationnement — valeur mono à droite, **article `↗` en source sous la ligne**. « non réglementé » /
  « à vérifier » restent dits (`tone="mute"`), jamais comblés. La ligne Destinations et le disclaimer
  passent en note.
- **`plu_fraicheur` / `aper` / `radar_procedure`** : dé-boxés (cf. Z3).

### Réseaux et accès (`reseaux.tsx`, `GestionnairesBlock.tsx`, `ViabilisationBlock.tsx`)
- Les sous-titres mono (Accès, Axes et nuisances) deviennent des **kickers** (`GroupLabel`).
- **`GestionnairesBlock`** : plus de `card-elev` ; kicker + lignes gestionnaires (grammaire `.gest` de
  la maquette : libellé gris à largeur fixe, opérateur en clair) ; la confiance devient une **pastille
  standard** (`pill-mint` / `pill-amber`, tokens) au lieu d'une couleur composée à la main
  (`TOKENS.viab* + alpha`) ; note et disclaimer en `FactNote`.
- **`ViabilisationBlock`** : plus de `card-elev` ni de sous-boîtes `rounded-lg bg-surface-3`. En-tête =
  kicker + pastille de bande à droite ; « Pourquoi cet indicateur », « Raccordement (qualitatif) »,
  « Assainissement (zonage) » deviennent des kickers ; le faisceau de preuves et le badge ANC (dans le
  slot droit du kicker) sont conservés ; phrases de méthode en note.

## Z3 — ce qui disparaît (dans ces deux sections)
- **Boîtes imbriquées à bordures différentes** : `card-elev` (Règlement PLU, Gestionnaires,
  Viabilisation) et boîtes `rounded-lg border` (TCSP, Axes/nuisances, `aper`, `plu_fraicheur`,
  `radar_procedure`, Raccordement, ANC) → remplacées par kickers + filets + rappels + filet gauche.
- **Sources collées en fin de phrase** → source SOUS la ligne de fait, avec son renvoi `↗`.
- **Valeurs en milieu de ligne** → valeurs alignées à droite en mono (toute la section s'aligne sur
  cette colonne).
- **Chips de tailles différentes** → une seule taille de badge (`.b`) et de pastille.

## Là où le texte servi diffère de la maquette (gardé : le texte servi)
- Les **badges « Sourcé »** que la maquette pose sur chaque ligne du Règlement ne sont **pas ajoutés** :
  les `regles_valeurs` servies ne portent pas de champ de provenance — le **renvoi d'article `↗`** EST
  la source (Z1·04 : « les renvois d'article sont des liens mono avec ↗ »). Rien n'est inventé.
- La maquette montre une seule ligne de statut « PLU à jour » ; le servi porte un `plu_fraicheur`
  multi-lignes (document servi · fait foi · en cours · action) — **conservé**, seulement dé-boxé.
- Réseaux garde le transport riche (arrêt · pôle · téléphérique · TCSP) et l'axe/nuisances que la
  maquette raccourcit — **conservés**, re-dressés dans la grammaire.
- Zone/surface réelles de la parcelle de recette (U4c, 761 m²), pas les valeurs d'exemple de la
  maquette (U6c, 601 m²).

## Captures — largeur réelle du panneau (400 px), SANS backend
Consigne respectée : **aucune app de captures qui touche au schéma de la base** (ce qui avait tué le
run RETOURS-21 lot A). Les captures « après » sont rendues par un **harness statique**
(`frontend/qa/retours20_harness.html`) qui charge le **CSS RÉEL COMPILÉ de l'app**
(`dist/assets/index-*.css` → tokens `:root` + utilitaires + classes `.fiche-v6` neuves) et reproduit le
DOM des composants refondus avec la **donnée de la parcelle de recette** (97415000AH0674). Script :
`frontend/qa/retours20_shots.mjs` (Playwright, Chrome système, `file://`, 400 px, ×2).

- Avant : `docs/audit-2026-09/RETOURS-21/captures/{reglement,reseaux}-avant.png`
- Après : `docs/audit-2026-09/RETOURS-20/captures/{reglement,reseaux}-apres.png`

## Vérification
- `npx tsc -b` : **0 erreur**. `npx vite build` : **OK** (200 modules, CSS 85,85 kB ; `color-mix`
  et les classes `.f-row` / `.b.s` présents dans le bundle).
- Pas de backend lancé, pas de base touchée.

## Fichiers
- `frontend/src/styles/index.css` — grammaire Z1 (`.f-row`, `.b`, `.f-ref`, `.f-vig`, `.f-rappel`,
  `.f-note`, `.f-status`, slot droit `.sec > .sec-r`).
- `frontend/src/components/fiche/primitives.tsx` — `FactRow`, `RefLink`, `StatusLine`, `Vigilance`,
  `Rappel`, `FactNote` ; `GroupLabel` (slot droit) ; `StepProv` (aligné `.b`).
- `frontend/src/components/fiche/Fiche.tsx` — `ReglementPluBlock` refait ; `plu_fraicheur`/`aper`/
  `radar_procedure` dé-boxés.
- `frontend/src/components/fiche/reseaux.tsx`, `GestionnairesBlock.tsx`, `ViabilisationBlock.tsx`.
- `frontend/qa/retours20_harness.html`, `frontend/qa/retours20_shots.mjs` — outillage de capture.
- `docs/audit-2026-09/RETOURS-20/captures/{reglement,reseaux}-apres.png`.

## Arrêt
Les **sept autres sections attendent la validation de Vic** (Constructibilité, Risques, Marché, Autour,
Dispositifs, Propriétaire, Données et méthode). Les six composants partagés sont en place ; les
appliquer aux sept restantes fera l'objet d'un mandat de suite. **Rien n'est mergé, rien n'est poussé.**
