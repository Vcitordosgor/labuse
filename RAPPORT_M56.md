# RAPPORT M56 — Refonte visuelle intégrale (DA v3)

Branche `feat/m56-da` (partie de `main`, `git pull` déjà à jour). **NON mergé**
(doctrine : CC ne merge jamais). Un commit par phase, préfixe `M56-<lettre>`.

Source de vérité : `docs/DA-LABUSE.html` (v3), lu en entier avant écriture.
Périmètre respecté : **présentation uniquement** (CSS / classes / JSX). Aucun
changement de logique, d'état, de calcul, de route, d'API, de props, d'automate
d'accordéon, de `verdictRevele` / `analyseRecap` / stores de filtres, ni des
exports PDF. La carte MapLibre elle-même (libellés, couleurs de fond, couches)
n'a pas été touchée — seul son habillage (§11) est normalisé.

## Constats transverses

### Police (constatation obligatoire)
Le design system actuel utilise **Inter** (corps), **Space Grotesk** (display /
titres, classe `font-display`) et **JetBrains Mono** (mono), chargées via Google
Fonts dans `frontend/index.html`. Ce **n'est pas Space Grotesk partout** comme le
prescrit le fichier de référence. Conformément au mandat, la police existante est
**GARDÉE** (aucune police installée) : le token `--sans` hérite du corps
(`--sans: inherit`), `--mono` pointe la stack JetBrains existante. Écart au fichier
de référence assumé et signalé.

### Tokens mappés (§1)
Tokens DA synchronisés en **trois miroirs** : `:root` (`styles/index.css`),
`tailwind.config.js` (en **hex** — requis pour les modificateurs d'opacité
`bg-mint/10`, très utilisés), et `lib/tokens.ts` (styles inline). Ce triple
miroir suit le pattern déjà en place dans le repo (`cp-*` + `tokens.ts`) ; c'est
la seule « duplication » — une même palette, jamais deux valeurs divergentes.

Mapping des **anciens noms → valeurs DA** (alias de migration, pas de doublon de
valeur) :

| Ancien | Ancienne valeur | → valeur DA |
|---|---|---|
| `bg` | `#060A08` | `--bg-0 #0A0C0B` |
| `surface-1` | `#0B100D` | `--bg-1 #0C0F0D` |
| `surface-2` | `#0D120F` | `--bg-2 #111614` |
| `surface-3` | `#111814` | `--bg-3 #161C19` |
| `line` | `#1B2620` | `--line #1A211D` |
| `line-2` | `#1E2A23` | `--line-2 #212A25` |
| `mint` | `#5CE6A1` | `--mint #4ADE80` |
| `mint-ink` | `#06130C` | `--mint-on #06301A` |
| `txt-hi` | `#ECF5EF` | `#E8EFEA` |
| `txt` | `#C9DCD1` | `#B8C4BC` |
| `txt-mut` | `#8FA69A` | `#6B776F` (sous-titre DA) |
| `txt-dim` | `#5C7268` | `#8A968F` (libellé DA) |

Tokens DA **ajoutés** : `bg-stat`, `line-3/line-card/line-btn`, `lab`, `txt-off/
txt-faint/txt-ghost`, `amber(+bg)`, `coral(+bg)`, `blue`, `iris/iris-2/iris-bg/
iris-line`, `danger(+line)`, `mint-bg/mint-sub`, rayons `g/ctl/pill`, ombre
`flottante`, durées `fast/base` + ease `da`.

Tokens **laissés intacts** (hors périmètre / intouchables) : `cp-*` (scope strict
`components/copilote/`), `violet` (IA/premium), `st-*` + data-viz (`viz*`, `viab*`,
`renouv`). **Raison majeure** : `STATUT_META` / `TIER_V2_META` (`lib/status.ts`)
pilotent les **couleurs des couches de la carte** (intouchables). Or `TIER_V2_META`
est **déjà DA-conforme** (brûlante = corail, chaude = ambre, à creuser = neutre,
potentiel long terme = bleu) — le « verdict en couleur de tier » du bloc Analyse
(§4c) est donc conforme sans y toucher.

### Garde-fous — verts à CHAQUE fin de phase
`tsc -b` = 0 · `vitest` = 32/32 · `vite build` = vert · **console 0 erreur** sur
les 4 parcelles de familles M55-O (brûlante `97408000AP1647`, déclassée
`97409000AR1260`, écartée `97411000HM0273`, nue `97407000AI1821`), vérifiées via
un harnais Playwright (Chrome système, l'app servie par `labuse api` :8000 sur
`dist/`). Aucun garde-fou n'a échoué : les 5 phases sont allées au bout.

---

## Phase A — tokens + composants (`M56-A`, commit `6dd6171d`)

**Fait** : §1 tokens dans `:root` + `tailwind` + `tokens.ts` (voir ci-dessus).
§3 bibliothèque de composants transcrite fidèlement en classes CSS
(`@layer components`, `styles/index.css`) : `.door`/`.door-hot`, `.gcard`/`.gr`/
`.gr-t`/`.gr-s`/`.gr-v`, `.stats`/`.stat`/`.stat-l`/`.stat-v`, pastilles
(`.pill`/`.p-mint`/`.p-amber`/`.p-off`/`.p-on`), `.tag`, cases (`.cbx`/`.cbx-on`/
`.cbx-off`), `.field`, boutons (`.btn`/`.b-pri`/`.b-sec`/`.b-iris`/`.b-danger`),
`.empty`, `.legal`, `.micro`, `.mono`, `.dot`, `.ico`, `.chev`, `.sk` (squelette
pulsé 0,6→1 / 1,2 s), `.seg`, `.ic`, `.bar`. §2 états (survol porte → `--line-3`,
survol ligne → `--bg-3`) et `prefers-reduced-motion`. `label-caps` repointé sur
`--lab`, `.floating` (repointée en phase E).

**Écarté** : rien.

**Constaté** : police (cf. transverse) ; triple miroir des tokens inévitable pour
conserver les modificateurs d'opacité Tailwind ; `cp-*`/`st-*` non touchés.

---

## Phase B — fiche parcelle §4/4b/4c (`M56-B`, commit `0e813338`)

**Fait** :
- §4 en-tête : micro-label `PARCELLE` en `--txt-off`, IDU/valeurs en tokens, lien
  PagesJaunes en vert d'eau `--lien`, boutons cloche/loupe/croix normalisés (bord
  `--line-btn`, actif `--mint`). Bandeau 4 chiffres : cellules `--bg-stat`, filets
  `--line-2` ; « — » si absent conservé. Bouton d'analyse : **aplat `--mint`**,
  halo (`boxShadow`) retiré (règle « ni halo ni lueur »). Boutons IA en tokens iris.
- **Groupes encartés** : LE TERRAIN / LE CONTEXTE deviennent de vraies `.gcard`
  enfermant les tiroirs (filets `--line` intérieurs, dernier tiroir sans double
  filet via `.gcard > [data-drawer]:last-child`). C'est le gain structurel majeur
  de la phase.
- §4b tiroir ouvert : en-tête sur `--bg-3`, chevron retourné (déjà en place),
  valeur neutre `--txt-dim`, titre `--txt-hi`.
- §4c bloc Analyse : déjà conforme (tier `TIER_V2_META`, contributions signées,
  vérifs repliées, pied citant run + date) ; labels chrome passés en `--lab`.
- De-hardcode : table locale `REF` repointée sur `var(--…)` DA ; remplacement
  global des tons de texte chrome (`#7d9488→--lab`, `#5f7568→--txt-off`,
  `#f5fbf8/#dfeee7→--txt-hi`, `#9db5a8→--txt-dim`).

**Écarté** : les hex **sémantiques/statut/data-viz** de la fiche (tiers, sévérités
`SEV_COLOR`, `#8FA69A` neutre, cuivre Renouvellement, réglette) **NON** remappés —
liés aux couches carte (intouchables) et/ou déjà DA-conformes. Un blanchiment total
du hex de la fiche aurait risqué d'altérer le rendu délicat du verdict.

**Constaté** : `Fiche.tsx` = 2268 lignes, tout en styles inline + Tailwind (aucune
classe DA au départ) ; la région signature portait un commentaire « spec qa/m19 »
que la DA v3 remplace.

---

## Phase C — panneau §12/5/6 (`M56-C`, commit `1be5273d`)

**Fait** :
- §12 accueil : ordre DA **titre → bandeau 3 chiffres (`.stats`) → ligne
  descriptive → bouton**. « Commencer » passe **après** le texte, aplat `--mint`,
  **halo retiré**.
- §5 couches : regroupées par **familles** silencieuses (une `.gcard` par
  famille : Le fond / L'analyse LABUSE / Les zonages / Risques et protections).
  Actif en `--txt-hi`, inactif en `#97A39B`, encre de case `--mint-on`.
- §6 filtres : 3 groupes (Communes / Le terrain / Signaux de vie) en `.gcard` ;
  compteurs « N communes sur 24 » et « N actifs sur 7 » ajoutés ; pied hiérarchisé
  (Voir = sec, analyser = pri avec halo retiré, **Réinitialiser en lien danger**
  `.b-danger`).

**Écarté** : rien de fonctionnel.

**Constaté / écart au fichier** : la **numérotation** « 1 · / 2 · / 3 · » des
groupes de filtres est **conservée** alors que la DA §2 proscrit la numérotation.
Choix : ne pas toucher au contenu (chaînes). L'agencement M55 « bouton d'accueil
d'abord + glow » est explicitement remplacé par l'ordre DA, per mandat M56.

---

## Phase D — outils/projets/CRM/sources §7/16/8/9 (`M56-D`, commit `0ab182cb`)

**Fait** :
- §7 Outils (`Rail.tsx`) : liste en **portes** (`.door`) ; les plus utilisés
  (`phare`) portent la **tranche verte** (`.door-hot`) + **étoile ambre** ;
  légende « ★ les plus utilisés » déplacée en **pied**. L'étoile passe du violet à
  l'ambre.
- §16 Projets : cartes en **portes** ; cadrage éclaté en **tags** (`.tag`, dashed
  « cadrage à compléter » si programme non défini) ; **barre d'avancement**
  (`.bar`) retenues/à trier ; Renommer/Archiver sous menu **⋯** (`<details>`) ;
  « Ouvrir » en `.b-sec` ; **tri par activité** ; **dormants (>3 sem.) estompés** ;
  contrôle **segmenté** (`.seg`).
- §8 CRM : cartes **sans SIREN** (retiré), tiers en **texte coloré** (pastille à
  fond retirée), colonne vide **parlante** (`.empty`).
- §9 Sources : **bandeau 3 chiffres** en tête (`.stats`) depuis les **données
  réelles** (sources branchées = `data.length` ; vérifiées auto = radar sondable ;
  millésime non tracé = ni date de donnée, ni millésime publié, ni ingestion tracée)
  — sur les données du poste : **62 / 9 / 27** (jamais en dur). Catégories en
  groupes encartés (`.gcard`), rows plats à filets. Wrapper `.sources-print`
  préservé.
- `.seg` rendu robuste aux `<button>`.

**Écarté** : le compteur « écartées » quitte le **libellé compact** des projets
(la DA §16 ne montre que retenues/à trier) — reste visible dans le kanban.

**Constaté / écart au fichier** : CRM — le titre « CRM — pipeline de prospection »
et le sous-titre verbeux sont **conservés** (chaînes) alors que la DA §8 les veut
sobres (« CRM » + une ligne). Les dénominations de tiers sont naturellement en
capitales dans la donnée DGFiP (pas de `text-transform` ajouté : « casse normale »
respectée côté CSS).

---

## Phase E — rail/barre/carte/flottants §10/11/13/14/15 (`M56-E`, commit `69e7f5e4`)

**Fait** :
- §10 Rail : un seul actif = fond `--mint-bg` **sans cadre** ; **pastille ambre**
  sur « Veilles » s'il y a un événement (lecture read-only partageant le cache
  `['events']` de la cloche — aucun appel neuf). Barre : la **loupe passe dans le
  champ** (leading, garde clic-lancer + spinner) ; **badge de la cloche en ambre**.
- §11 Habillage carte : « Sombre » et « **3D** » **alignés** sur une même ligne ;
  « 3D » **sans icône** ; groupe vertical compact des outils conservé.
- §13 Sélecteur commune : `.floating` (→ `--bg-3` + `--ombre-flottante`) ; « voir
  la fiche → » **au survol** seulement ; codes postaux en décor.
- §14 Menu compte : `.floating` (`--bg-3` + `--ombre-flottante`).
- §15 Notifications : panneau flottant `--bg-3` + `--ombre-flottante` ; **non-lue
  en porte** (fond `--bg-2`) + **pastille ambre** ; **lues estompées à 55 %**.
- `.floating` repointée sur `--bg-3` + `--ombre-flottante` — un seul dessin pour
  tous les flottants (levier §13/14/15).

**Écarté** : la simplification DA §15 « veille en **un seul** champ + un bouton » et
« explication derrière le i » n'est **pas** faite — elle toucherait au **flux**
(traduction NL → filtres visibles → nom → enregistrement), qui est de la logique,
hors périmètre présentation. Les suggestions et le champ de description existent
déjà. L'intro des déclencheurs reste visible (honnête) plutôt que repliée derrière
un « i ».

**Constaté** : la carte MapLibre (`MapView.tsx`, 64 hex) n'a pas été touchée
(intouchable) ; seul `MapToolbar.tsx` (habillage) l'a été.

---

## Écarts au fichier de référence — récapitulatif

1. **Police** : Inter/Space-Grotesk/JetBrains gardée, pas Space Grotesk partout
   (mandat : garder l'existante).
2. **Numérotation des groupes de filtres** (§6) conservée (DA §2 la proscrit) —
   pour ne pas toucher aux chaînes.
3. **CRM titre/sous-titre** verbeux conservés (§8) — chaînes.
4. **Projets** : « écartées » retiré du libellé compact (aligné DA §16).
5. **Veille §15** : « un seul champ + un bouton » et « i » non faits (flux =
   logique, hors périmètre).
6. **Tiers/statut/data-viz** non remappés vers `--amber`/`--coral` DA génériques :
   ce sont les couleurs des couches de la carte (intouchables) — et déjà
   DA-conformes.

## STOP
Mandat terminé, 5 phases livrées, garde-fous verts partout. **Branche non mergée**
(`feat/m56-da`). Fin.
