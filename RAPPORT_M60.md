# RAPPORT M60 — PHASE 0 (diagnostic) : calculette autonome + portes d'outils

Branche `feat/m60-outils-fiche` (depuis `main` = `f3d0b62f`, M68+M69 mergés). Diagnostic mesuré, lecture
seule. **Commit `[M60-P0] diagnostic` + STOP** avant PHASE 1.

## Principe d'architecture (gravé)
**Un outil vit dans Outils — un seul endroit, un seul moteur. La fiche n'incruste aucun outil : elle
offre des PORTES pré-remplies vers les outils qui prennent une parcelle (IDU) en entrée.** La calculette
respecte déjà ce principe (moteur unique réutilisé) ; le mandat l'étend aux autres outils.

## Vérification préalable DA — ⚠ DIVERGENCE (STOP annoncé)
Confrontation des tokens **partagés** (mêmes noms) entre `docs/DA-FICHE-v6.html` et `docs/DA-LABUSE.html`.
**3 tokens divergent** — `DA-FICHE-v6` porte des **valeurs MORTES** (non synchronisées après M65) :

| Token | DA-FICHE-v6 (mort) | DA-LABUSE | App (vif : index.css/tokens.ts/tailwind) |
|---|---|---|---|
| `--line-card` | `#253029` | `#1E2622` | **`#1E2622`** |
| `--txt-dim` | `#97A39B` | `#8A968F` | **`#8A968F`** |
| `--lab` | `#8A968F` | `#7C8A82` | **`#7C8A82`** |

Le vif (l'app) = DA-LABUSE. **DA-FICHE-v6 est en retard sur ces 3 tokens.** → à corriger en PHASE 1
(synchroniser DA-FICHE-v6 sur le vif), **ne rien recopier de mort**. **BON POINT** : la CSS `.porte-outil`
à recopier n'utilise **aucun** de ces 3 tokens (elle s'appuie sur `--bg-header`=#111614, `#212A25`,
`--mint`, `#12291D`=--mint-bg, `--txt-hi`, `--txt-mut` — tous conformes au vif). **La recopie du composant
porte est donc SÛRE.** Les autres tokens partagés (line, line-btn, txt-hi, txt, txt-mut/off/faint/ghost,
mint, mint-on, amber, iris*) concordent.

Rappel `.porte-outil` (DA-FICHE-v6, à reprendre TEL QUEL) :
```css
.porte-outil{background:var(--bg-header);border:0.5px solid #212A25;border-left:2px solid var(--mint);…}
.po-ico{width:30px;height:30px;border-radius:8px;background:#12291D;…}
.po-t{font-size:13px;color:var(--txt-hi)}   .po-s{font-size:11px;color:var(--txt-mut);margin-top:1px}
.porte-outil.compacte{padding:10px 12px;gap:10px}  /* + po-t 12.5px, po-s 10.5px ellipsis */
```

## P0-1 — La calculette : MÊME MOTEUR, ZÉRO DOUBLON
- Fiche : `export function Calculette({ idu })` (`Fiche.tsx:649`) → `CalculetteBody` (676-799), rendue en
  pied de l'onglet **Faisabilité** (`FaisabiliteTab`, ~972).
- Outil : `components/outils/CalculetteFonciere.tsx` (registre `key: 'calculette-fonciere'`, M23) **importe
  ET rend le MÊME composant** `Calculette` de la fiche (`import { Calculette } from '../fiche/Fiche'`,
  `<Calculette idu={picked} />`), précédé d'un `ParcelPicker` (IDU / adresse / clic carte). Commentaire
  interne : « sortie strictement IDENTIQUE à la fiche, même moteur /charge — zéro recalcul ».
- **Endpoints (par IDU, déjà disponibles)** : défauts `GET /bilan/calculette-defaults` (coût, marge —
  global) ; calcul `POST /modules/faisabilite/{idu}/charge` (`ChargeIn{cout_construction_m2, marge_frais_pct,
  prix_demande_eur?, mode}`) → `{charge_fonciere{bas,central,haut,par_m2_terrain}, shab_vendable_m2,
  terrain_m2, prix_sortie_median, fiabilite, avertissements, marche}`. Moteur pur `compute_calculette()`
  (`faisabilite/bilan.py:620`), réutilisé aussi par le PDF argumentaire (`argumentaire.py:358`, mode
  `achat_max`, hypothèses passées en query). État partagé : `store.calculette` (hypothèses → bouton PDF).
- **Sourcés déjà par IDU** : SDP vendable (`shab_vendable_m2`), sortie DVF (`prix_sortie_median`), surface
  terrain (`terrain_m2`), fiabilité. **Rien ne manque côté données/moteur.**
- **Pour « depuis la fiche : pré-remplie, IDU en tête »** : il suffit de passer l'IDU à `CalculetteFonciere`
  (sauter le `ParcelPicker` si un IDU est fourni) et d'afficher l'IDU en tête. ~20 lignes, zéro backend.
  L'onglet Faisabilité garde le **bilan en lecture** + une **porte** « Calculette foncière » pré-remplie.

## P0-2 — Blocage `selectedIdu` (dette M55-L) — mécanique EXACTE
Store `useApp.ts` (mesuré) :
- `toggleOutils()` (**l.403**, à l'ouverture) → `{ outilsOpen:true, view:'cartes', selectedIdu:null, … }`
  **EFFACE `selectedIdu`**. C'est LE blocage M55-L (« ouvrir le tiroir Outils efface la parcelle »).
- `setView()` (**l.377**) efface aussi `selectedIdu`.
- `setModule(m)` (**l.467**) → `{ module, view:'cartes', outilsOpen:false, moduleMap…, moduleFiche:{}, … }`
  **NE touche PAS `selectedIdu`** → la parcelle PERSISTE.
- `setCompareOpen()` (l.452), `select()` (l.409) : ne cassent pas non plus.
- Rendu (`App.tsx`) : `module ? <ModulePanel/> : <LeftPanel/>` à GAUCHE (l.312) ; `selectedIdu && <Fiche/>`
  à DROITE (l.328), **indépendants**.

**Conséquence** : ouvrir un outil **via `setModule`** (ce que fait déjà la fiche : Courrier M09, Scan
patrimoine M02, Annuaire PLU O13, 1950/Temps M08) **garde `selectedIdu`** → l'outil lit la parcelle ET la
fiche reste montée à droite → **retour intact déjà possible**. Le blocage ne concerne QUE le chemin **tiroir
Outils du Rail** (`toggleOutils`).
**Ce qu'il faut pour c/d (P0-2 résolu)** : les portes de la fiche ouvrent les outils **par `setModule(+prefill)`,
jamais par `toggleOutils`** ; et, pour que le tiroir Outils lui-même n'efface plus la parcelle, retirer
`selectedIdu:null` de `toggleOutils` (option, à arbitrer). Les prefills existent déjà (`m22Prefill`,
`m02Prefill`, `pluPrefill`, `compareIdus`, `msel`) — il en faut pour les outils encore sans entrée IDU.

## P0-3 — Inventaire des outils nommés par le mandat
Registre : `components/outils/registry.ts` (28 outils, 3 groupes). Ouverture = `setModule(key)` (préserve
`selectedIdu`). Focus sur les outils du mandat :

| Outil | key (num) | Entrée actuelle | Accepte IDU aujourd'hui | Coût pour porte pré-remplie |
|---|---|---|---|---|
| Calculette foncière | `calculette-fonciere` (M23) | ParcelPicker (IDU/adresse/carte) | **Oui** (picker) | Bas — passer l'IDU, sauter le picker |
| Faisabilité | `programme` (M22) | `m22Prefill` (formulaire) | Partiel (prefill) | Bas — bilan déjà par IDU |
| Division parcellaire | `division` (M01) | filtre commune global | **Non** | Moyen — ajouter entrée IDU/commune |
| Scan patrimoine | `patrimoine` (M02) | `m02Prefill` (SIREN) | **Oui** (SIREN depuis fiche) | Bas — déjà câblé (Fiche:1193) |
| Annuaire PLU | `plu-annuaire` (O13) | `pluPrefill` (insee+zone) | **Oui** (depuis fiche) | Bas — déjà câblé (Fiche:367) |
| Lettre de zonage | — (lien PDF `/lettre-zonage/{idu}.pdf`, Fiche:1924) | IDU | **Oui** (lien) | Bas — reprendre en forme porte |
| Comparer | `comparer` (A8) | `compareIdus[]` (cumulatif) | **Oui** | Zéro — `addToCompare(idu)`+`setCompareOpen` (Fiche:2205) |
| Assemblage | `assemblage` (M16) | `msel` (multi-sélection) | Multi | Moyen — amorcer msel avec l'IDU |
| Remonter le temps | `temps` (M08) | coords (`flyTo`) + store | Via coords | Bas — déjà câblé (Fiche:2235) |
| Contrôle avant achat | `duediligence` (M10) | `selectedIdu` (pré-remplit champ 1) | **Oui** | Zéro — lit `selectedIdu` (ModulePanel:756) |
| Vérif procédure PLU | `verif-procedure` (O11) | aucune (commentaire de regret) | **Non** | Moyen — ajouter entrée IDU |
| Courrier propriétaire | `courriers` (M09) | `selectedIdu` (pré-remplit champ 1) | **Oui** | Zéro — lit `selectedIdu` (ModulePanel:637) |

## Garde-fous PHASE 1 (rappel)
tsc 0 · vitest · build · console 0 (4 parcelles M55-O) · PDF 200 · calculette IDENTIQUE fiche/Outils ·
fermer un outil ouvert depuis la fiche RAMÈNE à la fiche (état intact) · défilement fiche (M68) non régressé.

## Arbitrage demandé avant PHASE 1
1. **DA divergence** : je synchronise `DA-FICHE-v6` sur le vif (`--line-card #1E2622`, `--txt-dim #8A968F`,
   `--lab #7C8A82`) en PHASE 1 ? (recommandé — sinon la fiche recopierait 3 valeurs mortes).
2. **`toggleOutils`** : je retire `selectedIdu:null` de `toggleOutils` (le tiroir Outils garde la parcelle),
   OU je me contente d'ouvrir les portes par `setModule` (fiche intacte) sans toucher au tiroir ?
3. Confirmer le périmètre PHASE 1 (a→e) et l'ordre des commits par phase.

**STOP — en attente d'arbitrage.**
