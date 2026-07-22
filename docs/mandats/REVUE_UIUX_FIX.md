# REVUE UI/UX — PERFECTION DES 71 SURFACES (rapport vivant, protocole multi-sessions)

**Branche `tech/revue-uiux-fix` · un commit par surface `[Sxx]` · REFONTE = proposition écrite,
jamais de correction autonome.** Atlas de référence (« avant ») :
`~/labuse-atlas/2026-07-22-11-10__local/index.html`.

## ⟪ CURSEUR ⟫ **71/71 — MANDAT TERMINÉ (session 4, 22/07). STOP FINAL : à Vic.**

Vague 1 validée intégralement par Vic (zéro rejet, style verrouillé) ; vagues 2-3 livrées
dans la foulée (plus de checkpoint, conformément au go). **Livrable §8 :**
- **Atlas après complet** : `~/labuse-atlas/2026-07-22-15-35__apres/` (150 captures + PDF
  banquier repris, 6 impossibles documentées au manifest — les mêmes constats qu'à l'avant).
- **`index_avant_apres.html`** (même dossier) : **149 paires côte à côte + 2 captures sans
  avant + 4 surfaces sans UI**, navigables par vague S01→S71, **légende sous chaque paire**
  (quoi regarder) + provenance/heure sous chaque image (modèle v2 du checkpoint).
- **Filet final** : suite complète **1088 passed / 0 failed** (les 2 tests de caractérisation
  front réalignés sur les tokens — mêmes invariants) ; golden **116/116** sur le serveur
  retouché (8020) ; e2e_m9_fiche = 9 échecs pré-existants exacts + e2e_429 = 1 (pré-existant) ;
  tests auth 10/10 (S68 serveur) ; tsc + build verts à chaque commit.

Vic parcourt les paires, rejette commit par commit, merge le reste (§9). Refontes proposées
ci-dessous (S45-S50) = le futur BLOC B, sur son verdict uniquement.
Pièges serveurs de capture : `labuse api` env labusedb + `LABUSE_DATABASE_URL=
postgresql+psycopg://…` (le schéma nu casse sur psycopg2) ; instance 8021 avec
`LABUSE_AUTH_PASSWORD` pour la porte Coffre ; **PDF banquier : weasyprint ne s'importe pas
dans labusedb (lib native) → capturer via le serveur `.venv` (8010)**.

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

- **S17 `nav__omnibox`** — loupe en cible 28 px token, transitions, × des chips en zone de
  tap 20 px + aria-label. Surface déjà saine. Lois : 4, 7.
- **S19-S20 `carte__ile/commune`** — chrome carte en tokens : ombres élévation
  (zoom/hints/loading), badge IA violet token, readout lisible sur ortho, copyright st-none ;
  toolbar rayons 10 px → rounded-lg + actifs mint/10 (fin de 5 hex), popover fond de plan
  `.floating`, légende `.floating` + Tips (matrice Q×A, 50 pas). Lois : 3, 7 + élévation.
- **S21 `outil__o2-scoreur`** — panneau `.floating` élévation-3, fermer 28 px, « Dans le
  marché » en st-creuser, fmtEur/fmtM2. Lois : 3, 4, 8.
- **S22 `fiche__askbar`** — zone IA violette en tokens intégraux (6 hex), Loading accent
  violet, erreur avec réessai, chips provenance en fonds tokens. Lois : 3, 6, 7.
- **S23-S24 badges défisc/caduc** — chips Sourcé/Estimé/hypothèse en fonds tokens sur toute
  la fiche + panneau ; ⚠ → ▲ partout. Wording intouché. Lois : 3, 5.
- **S25 `fiche__tiers`** — TierBadge : pastille colorée + label (le langage de la légende
  et des colonnes), nowrap. Loi : 3 + détail signature sobre.
- **S27-S44 modules outils** — le SHELL entier en tokens (~55 hex éliminés sur
  ModulePanel/moteurs/ScoringV2/M22) : bannière/breadcrumb/CTA/pastilles violet, alertes
  st-ecartee, SRU carencée orange → st-creuser, V() en num-key, fmtInt central, labels-
  instrument, tiroir permis élévation-3, erreur scoring SANS fuite CLI. Lois : 2, 3, 5, 7, 8.
- **S42 `outil__temps`** — barre comparer élévation-2 + label-instrument.
- **S51 `sources__page`** — teal hors palette → neutre, focus mint/[0.06], ⚠→▲ ;
  structure imprimable conservée.
- **S52-S53 Vues** — hero mint/[0.06], ambre/rouge en tokens (~15 hex), stats tabulaires.
- **S54-S55-S57 IA** — deux portes en tokens (fin des style-props), classement num-key,
  erreur réseau avec réessai ; wording du diagnostic dégradé conservé (décision C1).
- **S56 `ia__entretien`** — fiche card-elev + label-instrument, budget fmtEurCompact,
  jauge animée duration-soft, chips min-h-7.
- **S58-S59 popovers header** — `.floating` unique, labels-instrument, orange #FF8A50 →
  st-creuser, notifs violet tokens, veille : suppression en cible ronde.
- **S60 rail + tiroir outils** — actifs mint/10, rayon normalisé, cartes phares violet
  tokens, groupes en label-instrument.
- **S61 contexte commune** — fonds SRU dérivés de la couleur de statut, liens teal → mint,
  badge intérêt bleu → violet, élévation-3 ; palette data-viz marché conservée.
- **S62-S63 entonnoir + tiroir couches** — card-elev + label-instrument + tnum, fermer 28 px.
- **S64-S67 états de fiche** — boîtes rouges en st-ecartee/10, Réessayer 28 px hover mint ;
  skeletons/429/signalement déjà au standard. + hygiène finale Fiche.tsx (0 classe hex).
- **S68 `entree__404-api`** — 404 de NAVIGATION habillé côté serveur (page cockpit, oiseau,
  sortie) ; appels API : JSON FastAPI inchangé (discriminé Accept+GET), tests auth 10/10.
- **S69 tooltips natifs** — = LOI-1 (sessions 1-4), rien de plus à faire.
- **S70 error boundary** — aligné sur l'ErrorState standard (trait discret, titre txt-hi,
  `.floating`).
- **S71 rideau basic auth** — corps 401 habillé dans Caddyfile.prod (handle_errors +
  heredoc) : oiseau, « Accès pilote », sortie — à `caddy validate` au déploiement.

## Refontes proposées (le cœur du futur BLOC B)

- **S45 `o4-traducteur` · S46 `o5-servitudes` · S47 `o6-comparateur` · S48 `o7-carnet` ·
  S49 `o9-rarete`** — AUCUNE surface front (le client voit du JSON brut, constat atlas).
  Proposition : 5 modules du registre violet (le shell tokenisé est prêt) — traducteur =
  zone PLU → français courant sur la fiche ; servitudes = liste par parcelle avec Sourcé ;
  comparateur = tableau 24 communes triable ; carnet = digest de secteur imprimable ;
  rareté = jauge d'absorption par commune. Chacun ~1 session, zéro logique nouvelle
  (les endpoints existent).
- **S50 `o10-surface-d`** — exposé uniquement via la cloche (/events). Proposition : une
  entrée « Bascules datées » dans le registre (liste des événements de bascule, lien fiche).
- _(Vague 1 : aucune — tout tenait en retouches.)_

## OK — pas touché (protège du sur-design)

- **S26 dossier banquier PDF** — artefact d'IMPRESSION (charte claire dédiée), chiffres-clés
  + Sourcé/Estimé déjà propres ; le retoucher = mandat print séparé, pas une retouche front.
- **Symboles équipements de la carte (émoji dans les marqueurs canvas)** — iconographie de
  la donnée : la légende doit matcher les marqueurs ; un jeu de pictogrammes SVG dédié
  serait une refonte d'icônes à proposer si Vic la veut.
- **Wording du mode dégradé IA (S57)** — le diagnostic opérateur (ANTHROPIC_API_KEY, .env)
  reste : décision C1 « un diagnostic, pas une devinette » ; à conditionner à un mode admin
  au premier-euro (noté ci-dessous).
- **Palette data-viz** (donut marché commune, VOLET_COLOR RTAA, accents de colonnes CRM en
  style-prop) — la donnée est le décor ; valeurs = miroirs des tokens, documentées.

## En attente d'un verdict externe

- _(S16 soldé session 2 — verdict Coffre appliqué, cf. surfaces traitées.)_

## Findings hors périmètre front (à traiter ailleurs)

- Détails de lignes servis par le BACKEND avec du technique (« INONDATION_MOUVEMENT_DE_TERRAIN »,
  libellés de PPR en majuscules brutes) — le re-libellé à la source est un mini-mandat data,
  pas une retouche front.
- Le diagnostic du mode dégradé IA (S57) expose des instructions opérateur au client —
  à conditionner à un mode admin dans le mandat premier-euro (wording conservé tel quel).
- `codes d'état Sitadel non documentés (affichés bruts)` en Promesses mortes (S38) — dit
  honnêtement dans la bannière ; un mapping de libellés serait un mini-mandat data.

## OK — pas touché

- VerdictHero (état off) : pitch + CTA mint glow = LE point focal légitime, wording validé
  revue Vic P2 — n'y touche pas.
- Hints des couches en title : boutons d'action (règle LOI-1) + hint ancré existant pour le
  cas bloqué — suffisant.
