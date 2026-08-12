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

---

## Phase B2 — fiche conforme DA (correctif, commit `M56-B2 fiche conforme DA`)

Suite à la passe visuelle du mandant (parcelle 97415000CI0051, Saint-Paul) : six
écarts entre le rendu et la DA §4/4b/4c/§3. **Méthode appliquée** : relecture du
CODE SOURCE de la DA (§3 groupe encarté ligne 207-215, §4 ligne 318-365, §4b ligne
367-400) ; le gabarit `.gr` de la §3/§4 a été RECOPIÉ (pas réinventé) ; les vraies
données branchées dedans ; comparaison de la fiche 97415000CI0051 à la §4 jusqu'à
superposition (aux données près). Tout dans `Fiche.tsx` (présentation ; accordéon,
`verdictRevele`, calculs, exports — intouchés).

**Refactor du gabarit** : `RefDrawer` réécrit sur la `.gr` DA — la rangée fermée
porte `className="gr"` (colonne gauche `.gr-t` titre + `.gr-s` UNE ligne de contexte
grise ; colonne droite `.gr-v` valeur neutre OU `.pill` de statut, puis `.chev` avec
`›`/`⌃`). Le filet --line entre rangées vient du wrapper. `RefChevron` (SVG) supprimé
au profit de `.chev`. Nouveau prop `context` (le gr-s) ; le `micro` riche (jauge,
sparkline, segments) ne s'affiche PLUS sur la rangée fermée — il descend EN TÊTE du
tiroir ouvert. `value` : chaîne → `.gr-v` ; élément React (une `.pill`) → tel quel
(via `isValidElement`).

**Fait, écart par écart** :
1. **Tiroirs sans conteneur** → les 7 tiroirs sont des `.gr` DANS les `.gcard`
   LE TERRAIN / LE CONTEXTE (déjà encartées en M56-B, désormais avec la vraie
   structure `.gr`/`.gr-t`/`.gr-s`/`.gr-v` à l'intérieur). Vérifié : superposable.
2. **Valeurs / couleur orpheline** → statuts en PASTILLES : Risques
   `.pill p-amber` « N vigilances » (pluriel corrigé) / `.pill p-mint` « rien à
   signaler » ; Réseaux `.pill p-mint` « confirmée » (au lieu de « confirmée par les
   faits ») ; Marché `.gr-v` « 206 €/m² » (le « terrain » retiré, contexte en gr-s) ;
   Urbanisme/Constructibilité/Propriétaire/Données en `.gr-v` neutres.
3. **Sous-titres surchargés** → UNE ligne grise (`.gr-s`) par rangée fermée :
   Urbanisme « zone U6c · 28 % SDP consommée », Constructibilité « R+1 · calcul
   tracé », Marché « N ventes secteur · DVF — … ». Les jauges/sparklines/segments
   descendent DANS le tiroir ouvert (aucune donnée supprimée).
4. **Boutons IA** → DEUX `.b-iris` côte à côte : « Poser une question » ·
   « Synthèse IA » ; les résultats (réponse, synthèse) se déploient dessous.
5. **Grille d'outils du bas** → micro-label « EXPORTS ET OUTILS » + `.gcard`
   (fond --bg-2, bord --line-card, filets --line) ; les 9 outils CONSERVÉS ; icônes
   passées de teal `#8fd8b4` à `--lab` (plus d'icônes colorées).
6. **Pastille « emplacement réservé n°73 »** → `.pill p-amber` standard (au lieu du
   badge local teinté à la main), avec le badge EBC voisin passé `.pill p-mint`.

**Écarté / constaté** :
- MicroPastilles (signaux propriétaire) normalisées en `.pill p-amber` (plus de
  puces violettes locales) — cohérent avec la bibliothèque §3.
- La pastille « emplacement réservé » reste rendue dans son bloc de prescriptions
  d'origine (sous le bouton vert) : il n'existe pas de groupe « signaux » distinct
  dans cette fiche où la déplacer ; seul le STYLE a été normalisé (l'ask concret).
- Mode B (tiroir imbriqué dans Constructibilité) aligné au passage (contexte +
  valeur en `.pill p-amber` si bilan négatif), bien que hors des 6 écarts.
- Résultats IA : quand la synthèse est déclenchée, son cadre se rend dans la cellule
  du bouton (flex) plutôt qu'en pleine largeur — séparer trigger/résultat aurait
  touché l'état du composant (hors périmètre présentation). L'état par défaut (deux
  boutons `.b-iris`) est conforme.

**Garde-fous B2** : tsc 0 · vitest 32/32 · build OK · console 0 erreur sur les 4
parcelles M55-O ET sur 97415000CI0051 · **export PDF fiche premium 97415000CT1389 :
HTTP 200 `application/pdf` 67 Ko (`%PDF-`)** — l'habillage n'a rien cassé.

---

## Phase B3 — fiche : composition (en-tête, actions, densité) (commit `M56-B3 fiche composition`)

Sept correctifs de composition constatés sur 97415000CO0032 (zone A, SDP absente).
Présentation uniquement ; aucune logique, aucune donnée supprimée. `Fiche.tsx` +
`styles/index.css`. **La référence `docs/DA-LABUSE.html` §4 est mise à jour** (les
sept correctifs reportés en commentaires + valeurs) — fichier et app restent
superposables.

**Fait** :
1. **Référence redondante** → la ligne courte `iduCourt` (« CO 0032 », fin de l'IDU
   complet) est retirée ; import `iduCourt` nettoyé.
2. **Surface écrite deux fois** → la surface quitte l'en-tête ; le bandeau la porte
   via `fmtM2` (ha dès 10 000 m² « 3,19 ha », m² en dessous, « — » si absente). Le
   lien « Voir sur Pages Jaunes » reste seul sur sa ligne.
3. **Rupture de fond** → `borderBottom` du bloc en-tête supprimé : un seul fond
   continu --bg-1 du haut au pied (l'aside est déjà `bg-surface-1`).
4. **Icône copier** → sortie de son cadre : icône seule 13px --txt-ghost collée à la
   référence (retour vert au copié). Les trois boutons d'en-tête
   (cloche/loupe/croix) passent à 27px, icônes 13px.
5. **Boutons IA trop lourds** → deux `.b-iris` allégés (padding 8px 11px), contenu
   aligné à GAUCHE, icône mauve 13px + libellé 12.5px --iris-2 : bulle de message
   pour « Poser une question », étincelles (`#i-ia`) pour « Synthèse IA ».
6. **Rangée sans valeur** → `RefDrawer` n'affiche JAMAIS une colonne droite vide :
   valeur, pastille, ou « — » (--txt-faint). Urbanisme renseigne `.gr-v` avec l'état
   de constructibilité (zone A/N → « non constructible » ; zone U → « N m max » si la
   hauteur est connue ; sinon « — »).
7. **Densité (~10 % de hauteur en moins, jamais les tailles de texte)** — via les
   espacements : padding panneau 16→14 ; `.gr` vertical 12→10 (plancher : pas plus
   bas) ; micro-label→carte 7→6 ; entre deux groupes 18→12 ; bandeau/bouton/IA 10→8.

**Écarté / constaté** :
- `.gr` (padding 12→10) est la classe DA PARTAGÉE (fiche, panneau, sources) : la
  densité s'applique donc à toutes les rangées `.gr` — cohérent, reporté au §<style>
  de la référence. Plancher 10px respecté (consigne : ne pas tasser sous 10px).
- Le bloc en-tête est en flux BLOC (pas flex) ; les écarts bandeau→bouton/verdict
  sont rendus explicites par `marginTop:8`.
- Zone A/N = inconstructible par principe (`/^[AN]/`) ; les autres zones sans hauteur
  calculée retombent sur « — » plutôt qu'un état inventé.

**Garde-fous B3** : tsc 0 · vitest 32/32 · build OK · console 0 erreur sur les 4
parcelles M55-O **+ 97415000CO0032** (zone A, SDP absente → « — » et « 3,19 ha »
vérifiés ; cas AVEC SDP + m² validé sur 97408000AP1647 : 382 m² / SDP 234 m²) ·
**export PDF premium 97415000CT1389 : HTTP 200 `application/pdf` 67 Ko**.

## STOP
Mandat terminé (M56 A→E + B2 + B3), garde-fous verts partout. Référence
`docs/DA-LABUSE.html` §4 tenue à jour. **Branche non mergée** (`feat/m56-da`). Fin.
