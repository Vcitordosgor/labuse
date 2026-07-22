# REVUE UI/UX — PERFECTION DES 71 SURFACES (rapport vivant, protocole multi-sessions)

**Branche `tech/revue-uiux-fix` · un commit par surface `[Sxx]` · REFONTE = proposition écrite,
jamais de correction autonome.** Atlas de référence (« avant ») :
`~/labuse-atlas/2026-07-22-11-10__local/index.html`.

## ⟪ CURSEUR ⟫ dernière surface traitée : **S15** · **VERDICT VIC (22/07) : vague 1 VALIDÉE
INTÉGRALEMENT, zéro rejet — le style est verrouillé.**

Session 4 en cours : S17, S19-S20 (fin vague 1) → vague 2 (S21-S57) → vague 3 (S58-S71).
**Plus de checkpoint intermédiaire : prochain arrêt = livrable final §8** (atlas après
complet + `index_avant_apres.html` des 167 paires AVEC LÉGENDES, modèle = la v2 du
checkpoint, générateur dans le transcript session 3) puis STOP final.
Filet sessions 3-4 : e2e_m9_fiche = 9 échecs pré-existants exacts, e2e_429 = 1, tsc+build
verts. Serveurs de capture : `labuse api` (env labusedb,
`LABUSE_DATABASE_URL=postgresql+psycopg://…` — le schéma `postgresql://` nu casse sur
psycopg2 absent) + instance 8021 avec `LABUSE_AUTH_PASSWORD` pour la porte Coffre.

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
- **[LOI-3] Formats** — FAIT (lib/format.ts) : fmtInt/Dec/Eur/M2/Pct/Date/DateNum fr-FR
  + `fmtEurCompact` (450 k€ / 2,4 M€ — session 3). Adopté : liste résultats, bloc
  projets/CRM. Le reste au fil des surfaces.
- **[LOI-4] Métadonnées** — FAIT : title « LABUSE — Radar foncier · La Réunion », meta
  description, theme-color #060A08, robots noindex (rideau pilote).
- **[LOI-0 bis] Token `violet`** — FAIT (session 3) : #B497F0 (accent premium/IA/outils)
  entre dans tailwind.config ; 73 usages en dur migrés au fil des surfaces (S12-S15 faits).

## Surfaces traitées (3 lignes max chacune)

- **S01 `nav__dashboard`** — Labels → .label-caps ; rangées couches min-h 28 px (tactile) ;
  bandeau « analyse affichée » : bordure dure → élévation ; ombres → tokens ; pastille commune
  mint décorative → neutre (vert = signal). Lois : 2, 3, 4, 7 + cockpit vert-signal/élévation.
- **S18 `liste__resultats`** — fmtInt central (LOI-3), veille + badge proprio en Tip, surfaces
  m² tabulaires ; état vide déjà EmptyState (LOI-2). Lois : 4, 5, 8.
- **S02 `fiche__synthese`** — tous les blocs en élévation `card-elev` (fin des bordures dures) ;
  Tips tactiles sur les badges info (V, P v2, équipements, ICD, matrice historique) ; labels →
  `.label-caps` ; jauge complétude en instrument (valeur au centre de l'anneau) ; ISO → fr ;
  emojis 💧🚰⚡ → glyphes. Lois : 2, 3, 4, 6, 7 + élévation/typo-instrument.
- **S03-S05 `fiche__regles/risques/marche`** — libellés FRANÇAIS des couches (`lib/layers.ts`,
  44 clés ; la clé technique reste en Tip audit + trace `table#id`) ; dates fr ; séparateurs en
  token ; la recherche fiche matche aussi les libellés. Loi 5/8 (zéro texte technique qui fuit).
- **S06 `fiche__proprio`** — cartes en élévation, label-instrument DGFiP ; le reste hérité S03.
- **S07 `fiche__faisabilite`** — ErrorState standard (LOI-2), labels-instrument, étapes en
  élévation ; le résultat garde sa bordure mint (signal légitime).
- **S08 `fiche__bilan`** — ErrorState, sections `card-elev` + label-caps, médiane fmtInt,
  `non_applique` → « non appliqué », RTAA aligné (sous-cartes sans bordure).
- **S09 `fiche__calculette`** — label-instrument + recalc pulse, carte en élévation, chiffre-clé
  `.num-key`, fmtInt partout (SDP/prix/terrain/€ au m²).
- **S10 `fiche__pourquoi-pas`** — ErrorState avec sortie, labels teintés en `.label-caps`,
  motifs sans bordure dure, `#E8B44C` → token `st-creuser`.
- **S11 header + exports** — Tips sur les 3 badges d'en-tête (verdict rang/×N, signaux vendeur,
  ICD), surface en fmtM2, bouton fermer en cible 28 px, popover apporteur en `.floating`.
  Barre d'actions h-8 CONSERVÉE (dessin P6 revu par Vic) — noté, pas retouché.
- **S16 `entree__login`** — **verdict Vic appliqué : porte Coffre définitive, DEUX champs**
  (identifiant + mot de passe), 4 états (défaut/focus/erreur de couple neutre/chargement),
  mobile au niveau maquette, chrome de revue retiré. **Façade prête, moteur d'auth =
  premier-euro** : le POST /login actuel ignore `identifiant` (mot de passe pilote inchangé,
  tests auth 10/10) ; le futur backend d'identité lit les deux champs du même formulaire
  sans retoucher le design.

- **S12 `projet__liste`** — cartes en `card-elev` ; UN CTA mint solide par écran (« Ouvrir »
  → fantôme mint) ; compteurs tabulaires, zéros éteints (couleur = signal) ; budget
  fmtEurCompact + fmtDate ; EmptyState/Skeleton ; dédup en token violet, sans ⚠ ni « ids ».
  Lois : 1, 2, 3, 6, 7, 8 + vert-signal/élévation.
- **S13 `projet__kanban`** — colonnes en élévation (bordure = feedback de drop uniquement) ;
  accent « À trier » bleu hors palette → st-none ; 6 hex locaux → tokens ; Retenir en fantôme
  (« Trier » = LE focal) ; mobile 85vw (colonnes 34vw illisibles avant) ; fmtM2/fmtDate ;
  Tips chips. Lois : 2, 3, 4, 5, 7 + cohérence DA.
- **S14 `projet__tinder`** — carte de décision `.floating` élévation-3, stats en num-key
  neutre + label-caps (mint réservé à ✓ Retenir) ; « Tri terminé 🎉 » → oiseau mint signature ;
  ⚠→▲ st-creuser ; popover `.floating` ; Loading dignes ; tiroir sans bordures dures,
  fermer 28 px. Lois : 1, 3, 4, 6, 7 + typo-instrument/détails signature.
- **S15 `crm__kanban`** — cartes/colonnes en élévation ; titre de page en display ; ✕ retirer
  visible au doigt (opacity-40, cible 28 px — était invisible hors survol) ; badge « nouveaux »
  violet token + Tip ; fmtM2 ; wording privacy aligné (« jamais nommé »). Lois : 2, 3, 4, 5, 7.

## Refontes proposées (le cœur du futur BLOC B)

_(aucune à ce stade — S01/S18 tenaient en retouches)_

## En attente d'un verdict externe

- _(S16 soldé session 2 — verdict Coffre appliqué, cf. surfaces traitées.)_

## Findings hors périmètre front (à traiter ailleurs)

- Détails de lignes servis par le BACKEND avec du technique (« INONDATION_MOUVEMENT_DE_TERRAIN »,
  libellés de PPR en majuscules brutes) — le re-libellé à la source est un mini-mandat data,
  pas une retouche front.

## OK — pas touché

- VerdictHero (état off) : pitch + CTA mint glow = LE point focal légitime, wording validé
  revue Vic P2 — n'y touche pas.
- Hints des couches en title : boutons d'action (règle LOI-1) + hint ancré existant pour le
  cas bloqué — suffisant.
