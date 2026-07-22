# REVUE UI/UX — PERFECTION DES 71 SURFACES (rapport vivant, protocole multi-sessions)

**Branche `tech/revue-uiux-fix` · un commit par surface `[Sxx]` · REFONTE = proposition écrite,
jamais de correction autonome.** Atlas de référence (« avant ») :
`~/labuse-atlas/2026-07-22-11-10__local/index.html`.

## ⟪ CURSEUR ⟫ dernière surface traitée : **S01 + S18** · vague 1 (session 1)

**Reprise session suivante : S02 `fiche__synthese`** (enchaîner S02→S11 = tout le bloc fiche
d'un tenant, puis S12-S15 projets/CRM, S17, S19-S20 ; S16 login = EN ATTENTE verdict porte).
Filet e2e : les échecs e2e_m9_fiche (9-10) et e2e_429 (1) sont PRÉ-EXISTANTS sur main
(prouvé au dist près, session 1) ; `qa/e2e.mjs` vise l'ancienne UI (invalide). tsc+build verts.

---

## Ordre de bataille (le numéro EST l'ordre)

**Vague 1 — 95 % du temps d'écran** : S01 `nav__dashboard` · S02 `fiche__synthese` ·
S03 `fiche__regles` · S04 `fiche__risques` · S05 `fiche__marche` · S06 `fiche__proprio` ·
S07 `fiche__faisabilite` · S08 `fiche__bilan` (Score É) · S09 `fiche__calculette` ·
S10 `fiche__pourquoi-pas` · S11 `fiche__exports` (+ header de fiche) · S12 `projet__liste` (dédup) ·
S13 `projet__kanban` · S14 `projet__tinder` · S15 `crm__kanban` · S16 `entree__login` ·
S17 `nav__omnibox` · S18 `liste__resultats` · S19 `carte__ile` · S20 `carte__commune`

**Vague 2 — outils & pages** : S21 `outil__o2-scoreur` · S22 `fiche__askbar` ·
S23 `fiche__badge-defisc` · S24 `fiche__badge-caduc` · S25 `fiche__tiers` ·
S26 `outil__o1-banquier-pdf` · S27 `outil__scoring-v2` · S28 `outil__programme` ·
S29 `outil__division` · S30 `outil__fantome` · S31 `outil__patrimoine` ·
S32 `outil__patrimoine-recherche` · S33 `outil__bailleur` · S34 `outil__matching` ·
S35 `outil__assemblage` · S36 `outil__barometre` · S37 `outil__permis` · S38 `outil__promesses` ·
S39 `outil__velocite` · S40 `outil__simulplu` · S41 `outil__zan` · S42 `outil__temps` ·
S43 `outil__duediligence` · S44 `outil__courriers` · S45 `outil__o4-traducteur` ·
S46 `outil__o5-servitudes` · S47 `outil__o6-comparateur` · S48 `outil__o7-carnet` ·
S49 `outil__o9-rarete` · S50 `outil__o10-surface-d` · S51 `sources__page` · S52 `vues__accueil` ·
S53 `vues__preset-resultat` · S54 `ia__copilote` · S55 `ia__recherche-nl` · S56 `ia__entretien` ·
S57 `ia__mode-degrade`

**Vague 3 — secondaires & états** : S58 `nav__popover-filtres` · S59 `nav__popover-communes` ·
S60 `nav__rail-outils` · S61 `nav__contexte-commune` · S62 `nav__entonnoir` · S63 `carte__couches` ·
S64 `fiche__inconnue` · S65 `fiche__chargement` · S66 `fiche__429` · S67 `fiche__signalement` ·
S68 `entree__404-api` · S69 `etat__tooltips-natifs` (=LOI-1) · S70 `etat__error-boundary` ·
S71 `etat__rideau-basic-auth`

---

## LOIs (socle + transverses)

- **[LOI-0] Tokens** — FAIT : `shadow-elev-1/2/3` + `.card-elev`/`.floating` (profondeur sans
  bordures dures), `.label-caps`, `.num-key` (tabular), `.tnum`, `duration-quick/soft` +
  `ease-cockpit`, échelle 4/8 documentée (DERIVATIONS.md §LOI-0).
- **[LOI-1] Tip tactile** — FAIT (composant + sites clés) : survol/focus + TAP mobile, dessin
  `.floating` unique, stopPropagation. Migrés : tier-chip, ×N, complétude (liste+CRM),
  événement, même-proprio, veille, badge proprio, (matrice:X), labels Q/A/V fiche.
  **Règle posée : Tip sur l'info, jamais imbriqué dans un bouton d'action.** Reste : title
  résiduels migrés au fil des surfaces.
- **[LOI-2] États standard** — FAIT (States.tsx) : EmptyState (oiseau filigrane + sortie),
  ErrorState (sobre + Réessayer systématique). Migrés : liste vide, erreur pipeline CRM.
- **[LOI-3] Formats** — FAIT (lib/format.ts) : fmtInt/Dec/Eur/M2/Pct/Date/DateNum fr-FR.
  Adopté : liste résultats. Le reste au fil des surfaces.
- **[LOI-4] Métadonnées** — FAIT : title « LABUSE — Radar foncier · La Réunion », meta
  description, theme-color #060A08, robots noindex (rideau pilote).

## Surfaces traitées (3 lignes max chacune)

- **S01 `nav__dashboard`** — Labels → .label-caps ; rangées couches min-h 28 px (tactile) ;
  bandeau « analyse affichée » : bordure dure → élévation ; ombres → tokens ; pastille commune
  mint décorative → neutre (vert = signal). Lois : 2, 3, 4, 7 + cockpit vert-signal/élévation.
- **S18 `liste__resultats`** — fmtInt central (LOI-3), veille + badge proprio en Tip, surfaces
  m² tabulaires ; état vide déjà EmptyState (LOI-2). Lois : 4, 5, 8.

## Refontes proposées (le cœur du futur BLOC B)

_(aucune à ce stade — S01/S18 tenaient en retouches)_

## En attente d'un verdict externe

- **S16 `entree__login`** — NE PAS retoucher l'existant : la porte définitive attend le choix
  Coffre/Territoire (maquettes Bloc A, docs/mockups/). Brancher le design retenu = ce mandat
  ou consolidation, selon le verdict.

## OK — pas touché

- VerdictHero (état off) : pitch + CTA mint glow = LE point focal légitime, wording validé
  revue Vic P2 — n'y touche pas.
- Hints des couches en title : boutons d'action (règle LOI-1) + hint ancré existant pour le
  cas bloqué — suffisant.
