# RAPPORT M62 — Passe transverse — PHASE 0 (diagnostic)

Branche `feat/m62-passe-transverse` (de `main`, contient m59 mergé). **Diagnostic seul,
aucun correctif.** Trois axes mesurés (rail/IA, le vert, couches ANALYSE LABUSE) ; le reste
de la Phase 1 (carte, panneau, urbanisme, sélecteur) est de l'exécution UI directe, cadrée
par la maquette, non diagnostiquée ici.

---

## P0-1 — Suppression de l'entrée « IA » du rail

**Le rail aujourd'hui** (`Rail.tsx:56-63`, `ZONES`) : `ia · copilote · cartes · outils ·
projets · crm`, plus en bas `Veilles` (bascule) et `Sources` (vue). **8 boutons.** Retirer
`ia` → **7 boutons** (conforme à l'attendu P1).

**Ce que rend la page « IA »** (`view === 'ia'` → `IAStub` `App.tsx:328`,
`components/ia/IAStub.tsx`) — un écran à **DEUX PORTES** :
1. **Recherche simple** (menthe) : champ langage naturel + bouton **« Chercher »**
   (`IAStub.tsx:130`, `bg-mint`) → `iaSearch` (`POST /ia/search`, NL → filtres) + `useApplySearch`.
2. **Montage de projet** (violet) : `ProjetEntretien` (`IAStub.tsx:72`, entretien guidé),
   armé par `ouvrirEntretien()` (`useApp.ts:370`, met `view:'ia'` + `entretienDirect`), déclenché
   depuis `ProjetsPanel.tsx:142,166` (« + Décrire un projet »).

**Ce que rend « Copilote »** (`view === 'copilote'` → `CopiloteView`) : atelier de mission
(`brief` textarea **locale, vide au départ** `CopiloteView.tsx:110` ; bouton **« Instruire »**
`run.instruire(mission, brief)` ; entonnoir / fil d'instruction / résultats / livrable
`useCopiloteRun`). **Moteur différent** de `/ia/search`.

**Le Copilote couvre-t-il tout ce que faisait « IA » ? — PARTIELLEMENT, à surveiller :**
- Le **brief Copilote** couvre l'intention « décrire un besoin → parcelles » (recouvre la porte 1
  au niveau usage), mais **par un autre moteur** (mission `instruire`, pas la traduction
  NL→filtres `/ia/search`).
- **`CopiloteView` ne lit PAS `entretienDirect`** : rediriger `ouvrirEntretien` vers `copilote`
  ferait atterrir sur un brief **VIDE** — l'amorce « Décrire un projet » serait **perdue** si on
  ne câble pas l'amorce dans le brief.
- **`ProjetEntretien`** (entretien guidé) n'est utilisé QUE par `IAStub` → devient **orphelin** si
  la page IA disparaît (composant conservé mais injoignable).

**Liens à rerouter après suppression (sinon morts)** :
| Emplacement | Ligne | Action P1 |
|---|---|---|
| `useApp.ts` type `View` | 7 | retirer `'ia'` de l'union |
| `App.tsx` rendu | 328 | retirer `{view==='ia' && <IAStub/>}` |
| `Rail.tsx` ZONES | 57 | retirer l'entrée `ia` |
| `Rail.tsx` ICONS | 18-23 | **déplacer** l'icône étincelles vers `copilote` |
| `useApp.ts` `ouvrirEntretien` | 370 | `view:'ia'` → `'copilote'` **+ câbler l'amorce dans le brief** |
| `ProjetsPanel.tsx` | 142,166 | `ouvrirEntretien()` inchangé (suit la redirection) |
| QA `*.mjs` (~15 fichiers) | divers | `setView('ia')` → `'copilote'` |
| docs (`CARTO_FRONT.md`, `DERIVATIONS.md`, `M12_LOT_F.md`) | divers | maj enum/mention |

**Backend `/ia/*` (status, search, entretien, synthese, pourquoi) : à CONSERVER** — `/ia/search`
est aussi consommé hors IAStub (`App.tsx:49` `useApplySearch`, omnibox). On retire la PAGE, pas
l'API. **Aucun lien PDF/hash/deep-link** vers `view:'ia'` (navigation 100 % `setView`).

**Icône étincelles à déplacer** (`Rail.tsx:18-23`) :
`<path d="M10 3.5 L11.6 8.4 L16.5 10 L11.6 11.6 L10 16.5 L8.4 11.6 L3.5 10 L8.4 8.4 Z" …/>`.

## P0-2 — Le vert

**Vert de référence = le bouton « Chercher »** (`IAStub.tsx:130`, `bg-mint`) =
**token `--mint` = `#4ADE80`** (`tailwind.config.js:24`, `styles/index.css:20`, `lib/tokens.ts:27`,
et **déjà** `--mint:#4ADE80` dans `docs/DA-LABUSE.html:15` + `docs/DA-FICHE-v6.html:12`).

> **⚠ Écart à trancher** : la page qui porte le bouton « Chercher » est `IAStub` (dont l'en-tête
> dit « Copilote ») ; le bouton de `CopiloteView` s'appelle « **Instruire** » et utilise un vert
> DIFFÉRENT `cp-mint = #63F2B8` (`tailwind.config.js:38`). Le mandat dit « bouton **Chercher** »
> → je retiens **`#4ADE80`** comme canonique. Si le mandant visait le bouton littéral de
> CopiloteView, ce serait `#63F2B8` — à confirmer.

**Tous les verts servis (écarts vs #4ADE80)** :
| Valeur | Nom / rôle | Emplacement | Nature |
|---|---|---|---|
| **#4ADE80** | `--mint` (**canonique**) | tokens, boutons, accents actifs, docs | marque/action |
| #63F2B8 | `cp-mint` (bouton Instruire, Copilote) | tailwind:38, composants copilote | **action** (à aligner) |
| #5CE6A1 | `st-chaude` (tier « Chaude/Brûlante ») | status.ts:11, ~40 usages carte/fiche | **sémantique (échelle verdict)** |
| #4ADE96 | `st-surveiller` (tier « À surveiller ») | status.ts:12, Fiche 279/319 | **sémantique (échelle verdict)** |
| #8FD9B6 | `viabProbable` (confiance) | tokens.ts:44 | **sémantique (échelle)** |
| #2E6B4F | `vizGreenDeep` (bordures, accents) | App/MapView (×~8) | structurel |
| #7FA88F | `lien` | index.css:26, tokens.ts:24 | lien |
| #3FB56A | zone N (PLU) | status.ts:150 | **sémantique (palette zones)** |
| #6FD3C6 / #79C9A0 | équip. TCSP / collège | status.ts:166/172 | **sémantique (palette équip.)** |
| #7de3ab | accent secondaire (dossier/PDF) | Fiche 2286/2342 | action (à aligner) |
| #06301A | `mint-on` en dur | LeftPanel.tsx:209 (stroke) | à retoken |
| #5FE494 | survol bouton (doc) | DA-LABUSE.html:277 | état interactif |

> **⚠ Arbitrage majeur pour P1-l** : « toutes les autres valeurs de vert s'alignent » est
> **catastrophique si pris au pied de la lettre** — `st-chaude`/`st-surveiller`/`viab*`/zones/équip.
> sont une **échelle sémantique multi-teintes** (le verdict Brûlante ≠ À surveiller par la couleur) ;
> les collapser sur #4ADE80 **détruirait la lisibilité du classement**. **Recommandation** : « le vert »
> = le vert **de MARQUE/ACTION** (mint des boutons, états actifs, accents, `cp-mint`, `#7de3ab`,
> `mint-on` en dur) → unifier sur **#4ADE80** ; **NE PAS** toucher aux échelles sémantiques
> (tiers verdict, viabilité, palettes zones/équipements). À confirmer par le mandant.

## P0-3 — Couches « Verdict — toute l'île » et « Renouvellement »

Section « **L'analyse LABUSE** » (`LeftPanel.tsx:125`) = **exactement 2 toggles** :
`couleurs_verdict` (l.102) + `renouv` (l.117). Les deux sont **OFF par défaut**
(`useApp.ts:402`) et **togglés UNIQUEMENT par ce panneau** (`toggleLayer` ; aucun autre setter).

**`couleurs_verdict`** (« Verdict — toute l'île, indépendant des filtres ») : force la palette des
tiers sur toutes les parcelles. Seul usage : la branche OR `opinion = (verdict &&
filters.analyseLabuse) || layers.couleurs_verdict` (`MapView.tsx:241`, aussi 294/747/752,
`Legend.tsx:41`). **Retirer le toggle (état laissé à `false`) est SANS RISQUE** : le mode opinion
reste accessible par `verdict && filters.analyseLabuse` ; toutes les gardes `!layers.couleurs_verdict`
deviennent constamment vraies (comportement nominal). On perd seulement la possibilité de
**forcer** la palette île entière depuis le panneau.

**`renouv`** (couche carte, overlay cuivre `ov-renouv`) : **à distinguer** du **filtre**
`filters.renouvellement` — deux systèmes SÉPARÉS. Retirer le **toggle de couche** (`layers.renouv`)
n'affecte **PAS** :
- le **filtre** `renouvellement` (Filters UI, `filters.ts:95/180`, export CSV `api.ts:88`, URL `rnv`,
  `filters.test.ts:16`) ;
- le **module** `RenouvellementModule` (outils) ;
- le **bloc fiche** Renouvellement (`Fiche.tsx:1563-1603`).
Seul l'overlay cuivre de la carte, activable par ce toggle, disparaît.

**Conclusion P0-3 — retrait des 2 toggles SÛR** (contrairement à une lecture qui confond toggle et
feature) : supprimer les entrées `couleurs_verdict` + `renouv` de la famille « L'analyse LABUSE »
(`LeftPanel.tsx:102,117` + grouping `125`) ; **conserver les clés de store** (`layers.*` défaut
`false`) pour que `MapView`/`Legend` continuent de compiler et lire `false`. **Ne toucher NI au
filtre `renouvellement`, NI au module, NI au bloc fiche.**

---

## Synthèse
| # | Constat |
|---|---|
| P0-1 | Rail 8→7 en retirant `ia`. Page IA = 2 portes (recherche `/ia/search` + entretien projet). Copilote = atelier mission (moteur ≠). **Redirection non purement mécanique** : câbler l'amorce dans le brief Copilote (`entretienDirect` non lu), sinon « Décrire un projet » atterrit vide ; `ProjetEntretien` devient orphelin. API `/ia/*` conservée (omnibox). ~15 QA + docs à mettre à jour. |
| P0-2 | Canonique = **#4ADE80** (`--mint`, bouton « Chercher », déjà dans les 2 docs DA). Écarts listés. **⚠ Ne pas collapser les verts SÉMANTIQUES** (tiers/viab/zones/équip.) — scoper « le vert » à la marque/action. `cp-mint #63F2B8` = discordance à confirmer. |
| P0-3 | Retirer les 2 **toggles** de « L'analyse LABUSE » = **SÛR** (OFF par défaut, seuls setters = ce panneau ; filtre `renouvellement`/module/fiche INDÉPENDANTS). Garder les clés de store. |

## STOP — PHASE 0
Diagnostic terminé, aucun correctif. Points d'arbitrage ouverts :
- **P1-l** : périmètre de « un seul vert » — marque/action seulement (recommandé) ou vraiment tout
  (déconseillé : casse l'échelle verdict) ? Et vert de référence **#4ADE80** (Chercher) confirmé vs
  `#63F2B8` (Instruire) ?
- **P1-b** : la redirection IA→Copilote doit-elle **câbler l'amorce** dans le brief Copilote (garder
  « Décrire un projet » vivant) ? Le quick-search `/ia/search` est-il assumé retiré de la nav ?
- **P1-g** : confirmé sûr — retrait des 2 toggles seulement.
NE PAS MERGER.
