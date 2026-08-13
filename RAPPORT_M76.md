# RAPPORT M76 — Passe globale sur la fiche : ferrage, dates, scores, IA PLU

Branche `feat/m76-fiche-globale` (fiche sert q_v9_m81). Passe **visuelle** (0 calcul, golden diff 0).
Garde-fous : tsc 0 · vitest 37/37 · build vert · **golden 119/119** (backend intact).

## Point 1 — Dates de millésime retirées (liste exhaustive)

Balayage de TOUS les blocs. Aucun littéral `30/07/2026` en dur : les dates transitent par les champs
(`line.date`, `d.millesime`, `verifie_le`, `maj`). **Retirées** (date à côté d'un libellé de source) :

| Bloc | Fichier:ligne | Avant → Après |
|---|---|---|
| Urbanisme (règles PLU) | `Fiche.tsx:1978` | `<Line hideWeight>` → `<Line hideWeight hideDate>` (**c'est le « 30/07/2026 »**) |
| Réseaux / Dépôts | `DepotsBlock.tsx:32` | `{source} · {millesime}` → `{source}` |
| Analyse / Renouvellement | `Fiche.tsx:1682` | `{source} · maj {date}` → `{source}` |
| Bilan / Marché DVF | `Fiche.tsx:1055` | `DVF … · {millesime}` → `DVF — {horizon}` |
| Constructibilité / RTAA | `Fiche.tsx:1230` | « Vérifié le {date} » → retiré |
| Bannière RNU | `Fiche.tsx:1723` | « Statut vérifié le {date}. » → retiré |

**Exception conservée (l'écran qui documente les sources)** : tiroir « Données et méthode »
(`Fiche.tsx:2237-2296`, pastilles `mill`/`tnum` par source). **Pied légal** (`Fiche.tsx:2377`) : sans date.
**Non touché** (dates FACTUELLES de contenu, pas des millésimes de source) : dates de permis « déposé/
autorisé » (`Fiche.tsx:2089`), dates de mutation DVF. **`SourceDrawer.tsx` — NETTOYÉ (arbitrage Vic,
commit `6fded0ec`)** : « Date du fait » de l'extrait + ligne « Synchronisée le … » retirées ; le nom de la
source reste (en-tête + fournisseur). L'exception « Données et méthode » ne couvre pas le drawer.

## Point 2 — Scores bruts retirés (le qualitatif reste)

| Bloc | Fichier:ligne | Avant → Après |
|---|---|---|
| Viabilisation « Pourquoi cet indicateur » | `ViabilisationBlock.tsx:43-52` | colonne `+{points}` → **▲/▽ seul** (aucun chiffre) |
| ScoreV2 « Pourquoi ce score » | `ScoreV2Block.tsx:119-124` | `{signe}{log_hazard}` → **▲/▽ + phrase** |
| Renouvellement « Pourquoi ce rang » | `Fiche.tsx:1668-1672` | barre chiffrée + `{points}/{max}` → **libellé qualitatif seul** |

**Conservés (conformes doctrine)** : `×{mult_base}` (le multiplicateur, jamais la proba brute),
`percentile`/`rang`, pastille ICD `libelle`. **Jauges** : après retrait de la barre chiffrée Renouvellement,
il ne reste QUE l'ICD (qualitative depuis M70) — **une seule jauge**, conforme M55-O.

## Point 3 — Ferrage à gauche

Colonnes de puce/score/icône résiduelles supprimées : `ViabilisationBlock` (`w-9`), `ScoreV2Block`
(`w-12`), `GestionnairesBlock` (`w-4` icône). Libellés/valeurs/sources alignés sur la verticale du titre,
dans TOUS les blocs (les 4 tiroirs M70 l'étaient déjà via `hideWeight`).

## Point 4 — Bloc « Demander à l'IA de traduire le PLU »

**`TraducteurBloc` (`Fiche.tsx:2527`) — masqué ENTIÈREMENT quand aucune règle traduisible.** Le fetch
`/traducteur-plu/{idu}` (déterministe, pas d'IA sur `{}`) est **avancé** (`enabled: true`) pour connaître
`regles_appliquees` avant de rendre ; `if (!d || regles_appliquees.length === 0) return null`. Plus de bloc
qui s'affiche pour annoncer son vide (« Aucune règle traduite » + pastille « zone non calibrée » supprimés).

**Mesure (ta question) — zones calibrées vs non :**
- **U/AU (constructibles, traduisibles) : 338 591 parcelles.**
- **A/N (non constructibles, non traduisibles) : 152 638 parcelles** → c'est là que le bloc se masquait pour
  rien. **Les zones A et N sont bien le cas principal** : elles n'ont pas d'articles indexés dans le corpus
  (`plu_reglement.py:80-83` : « A/N n'ont pas d'articles indexés »). Cas secondaire possible : une zone U/AU
  d'une commune non outillée (repli générique) — là `zone_calibree=False` mais `regles_appliquees` peut être
  non vide (valeurs génériques) → le bloc reste affiché avec la mention « Estimé », ce qui est correct.

## Point 5 — Couleur des portes d'outil : **VÉRIFICATION, RIEN CHANGÉ**

**Ce que prescrit la référence** (`styles/index.css:251-259`, composant `PorteOutil` `Fiche.tsx:900-913`) :
- `.porte-outil` : **tranche gauche `border-left: 2px solid var(--mint)`** (= `#4ADE80`), fond `var(--bg-2)`,
  bord `#212A25`, radius `0 10px 10px 0`.
- `.po-ico` : pastille 30×30, **`background:#12291D`**, icône `var(--mint)`.
- `.po-arrow` : `var(--mint)`. → **tranche + icône + flèche VERTES sur pastille `#12291D`.** Aucun jaune.

**Le conflit signalé (tu tranches)** : le jaune `#F5C518` est le token **`--pj-jaune`**, défini
`styles/index.css:27-28` avec le commentaire « autorisé UNIQUEMENT sur le lien Voir sur Pages Jaunes » (M61),
**consommé au seul endroit** `.addr-link` (`Fiche.tsx:1470`, « Voir sur Pages Jaunes »). Passer les portes
au jaune **lui ferait perdre son exclusivité** — le lien Pages Jaunes ne serait plus le seul jaune de la
fiche. La DA prescrit le vert ; **je n'ai rien changé.**

**Doublon Annuaire PLU — TRANCHÉ (arbitrage Vic, commit `6fded0ec`)** : le lien-texte **violet « Annuaire
PLU → »** (bloc Règlement PLU) est **retiré** ; la **porte** « Annuaire PLU de la commune » (forme
`.porte-outil`, grammaire officielle M60) **reste**. Une action, une seule forme. `setModule`/`setPluPrefill`
orphelins du bloc `ReglementPluBlock` supprimés. Les autres liens `↗` (Voir l'article, Voir le règlement)
sont des liens DOCUMENTAIRES externes légitimes, pas des outils.

**Chasse aux autres doublons (demande Vic) — aucun autre lien-texte ne double une porte.** Tous les
`setModule(...)` restants sont des `onClick` de `PorteOutil`. Seules deux **tuiles-icônes** de la bande
**EXPORTS** atteignent un module aussi servi par une porte : `1950`→`temps` (porte « Remonter le temps ») et
`Courrier`→`courriers` (porte SPF). C'est une **forme distincte** (tuile-icône dans la bande EXPORTS, scindée
des portes par M60 P1d), **pas « du même genre »** que le lien violet — **signalé, non touché** (si tu veux
les dédoublonner aussi, dis-le).

## Garde-fous
tsc 0 · vitest 37/37 · build vert · **golden 119/119 (diff 0, passe visuelle)** · une seule jauge (ICD) ·
portes M70 et défilement M68 non touchés (aucune modif de leur code). **NE PAS MERGER.**
