# M141 — Le baromètre n'est plus exportable · « officiel » ne ment plus (`fix/m141-barometre-libelle`)

Branché sur `origin/main` @ `ae09f3d9`. L'avance depuis M140 (`FILTRE — retrait section « Le bien »`
+ merge `lot-ui-final`) **ne touche pas** le périmètre (moteurs.py / Fiche.tsx / baromètre / Évolution)
— signalé. `90d17b93` (baromètre → onglet Évolution, avec son PDF) est bien dans main : ce mandat ne
le défait pas, l'onglet Évolution reste à l'écran, seule la sortie PDF disparaît. CC ne merge jamais.

---

## Partie 1 — Le baromètre cesse d'être exportable en PDF

### 1.A — Points d'entrée localisés (exhaustif)

| Rôle | `fichier:ligne` | Sort | Devenir |
|---|---|---|---|
| Bouton « ⬇ Rapport PDF » (onglet Évolution, composant `M18`) | `frontend/src/components/outils/moteurs.tsx:383-384` | **PDF** | **retiré** |
| Route export | `src/labuse/api/moteurs.py:545` `GET /barometre.pdf` → `barometre_pdf` (546-631) | **PDF** | **supprimée** (route + générateur) |
| Générateur fpdf | inline dans `barometre_pdf` (546-631) | **PDF** | **supprimé** avec la route |
| Données écran (à GARDER) | `moteurs.py:428` `_barometre_data`, `moteurs.py:532` `GET /barometre`, `api.ts:763` `motBarometre()` | JSON | **intacts** — l'onglet Évolution vit dessus |
| Routage d'affichage (à GARDER) | `registry.ts:97` (`hidden: true`), `ModulePanel.tsx:962` (`barometre → Communes`) | écran | **intacts** — alias vers le hub Communes |

**Autres canaux vérifiés = AUCUN.** Grep `barometre.pdf` / `barometre_labuse` sur tout le repo :
zéro lien Copilote, zéro `ReponseInline`, zéro entrée de menu, zéro job/envoi, zéro dépendance
d'un autre document. **L'export ne servait QUE le bouton** → aucun cas STOP de 1.B.

### 1.B — Contrôles STOP : non déclenchés
- L'export ne sert rien d'autre que le bouton (pas de job/envoi/dépendance). ✓ pas de STOP.
- Le retrait ne dégrade pas l'onglet au-delà du bouton : le bouton était dans une ligne flex avec
  la légende « Île entière (DVF 24 communes…) » ; retiré, la légende reste, la ligne tient. ✓

### Ce qui a été fait
- **Front** (`moteurs.tsx`) : le `<a href="/moteurs/barometre.pdf">⬇ Rapport PDF</a>` est retiré ;
  la légende demeure. Rien d'autre de l'onglet Évolution n'est touché (trois séries, trimestre
  partiel signalé, prix neuf unifié — tout reste).
- **API** (`moteurs.py`) : `barometre_pdf` **supprimée en entier** (route + générateur fpdf). La
  fonction était **self-contained** — `from fpdf import FPDF` et `from .pdf_premium import …` étaient
  des imports LOCAUX, les helpers `table`/`_tri`/`_pct` internes — donc **aucun code mort** ne
  subsiste. Suppression triviale et **sans effet de bord** (autorisée par le mandat).
- **Imports de module devenus inutilisés → retirés** : `from datetime import date` (l. 9) et
  `from fastapi.responses import Response` (l. 12), utilisés uniquement par `barometre_pdf`.
  Vérifié : `date` n'apparaît plus qu'en TEXTE SQL (`date_trunc('quarter', date)`), `Response` nulle
  part ailleurs. Import du module **OK**, `router` ne porte plus que `/moteurs/barometre` (JSON).

**Devenir du générateur** : supprimé dans ce mandat (trivial, self-contained, sans effet de bord).
`_barometre_data` reste — c'est la donnée de l'écran, jamais un chemin PDF.

---

## Partie 2 — « PDF officiel » n'est pas vrai

### La faute corrigée (la seule menteuse du dépôt)

`frontend/src/components/fiche/Fiche.tsx:2066` — tuile ✉ « Lettre de vérification de zonage » :

- **avant** : `PDF officiel — zone X de cette parcelle` / `PDF officiel de vérification de zonage`
- **après** : `PDF de vérification de zonage — zone X de cette parcelle` / `PDF de vérification de zonage`

Le mot « officiel » disparaît, l'information de zone est conservée. Cohérent avec le PDF lui-même,
qui dit deux fois qu'il ne constitue pas un certificat d'urbanisme et renvoie à la mairie.

### Grep « officiel » / « officielle » — front + gabarits PDF : verdicts

**Menteuse (qualifie un document LABUSE) : 1 seule** — `Fiche.tsx:2066` (corrigée ci-dessus).

**Légitimes (qualifient une source publique réellement officielle, ou disclaimer honnête) — laissées telles quelles :**

| `fichier:ligne` | Ce qui est qualifié | Verdict |
|---|---|---|
| `outils/PluAnnuaire.tsx:7,106`, `lib/api.ts:262` | pack **GPU** (Géoportail de l'Urbanisme) | légitime (source publique officielle) |
| `panel/LeftPanel.tsx:96,116` | zones **PLU/GPU** (document opposable) | légitime |
| `panel/FiltreLabuse.tsx:124` | graphie officielle de commune (GPU) | légitime (commentaire) |
| `fiche/SourceDrawer.tsx:56`, `sources/SourcesPage.tsx:26,150,152` | liens vers la **documentation/source officielle** (Légifrance…) | légitime |
| `map/Legend.tsx:232`, `lib/layers.ts:110` | **GTFS** réseaux officiels (Licence Ouverte) | légitime |
| `lib/layers.ts:85`, `store/useApp.ts:24` | frontières/contours communes **IGN** | légitime |
| `lib/layers.ts:104` | **INSEE** BPE (source statistique officielle) | légitime |
| `lib/layers.ts:112` | hiérarchie routière **BD TOPO IGN** | légitime |
| `lib/layers.ts:93` | « **ce n'est pas** une source officielle » (périmètre dérivé LABUSE) | légitime (disclaimer honnête) |
| `contexte/ContextePanel.tsx:167`, `header/Header.tsx:223` | contexte officiel **SRU/ANRU/PLH/INSEE** | légitime |
| `lib/strings.ts:433,436` | **cadastre** officiel (Géoportail IGN) | légitime |
| `lib/types.ts:185` | « une source proxy ne doit pas être présentée comme la source officielle » | légitime (doctrine) |
| `fiche/Fiche.tsx:374` | « grammaire officielle M60 » (nommage interne) | légitime (commentaire) |

**Gabarits PDF backend** : `rapport.html.j2` = **0** occurrence ; `pdf_premium.py:93` = « silhouette
officielle » (chemin du **logo** de marque, commentaire) — pas une revendication d'officialité de
document. Le générateur de la lettre (`lettre_zonage.py`, `servitudes.py`) porte au contraire le
**disclaimer honnête** « certificat d'urbanisme indispensable ». **Aucune faute menteuse dans les PDF.**

---

## Contrôles

1. **Aucun chemin d'export PDF du baromètre** (front + API) : grep `barometre.pdf`/`barometre_labuse`
   = 0 (hors mon commentaire d'explication) ; `router` n'expose plus que `/moteurs/barometre` (JSON). ✓
2. **Onglet Évolution à l'identique, sans le bouton** — capture structurelle :
   - avant : `[ Île entière (DVF 24 communes…)            ⬇ Rapport PDF ]`
   - après : `[ Île entière (DVF 24 communes…) ]` (les 3 séries + trimestre partiel + neuf : inchangés) ✓
3. **Zéro « officiel » menteur** ; la tuile lettre affiche la nouvelle formulation dans ses deux
   états (zone connue → « PDF de vérification de zonage — zone X… » ; inconnue → « PDF de vérification
   de zonage »). ✓
4. **La lettre de zonage s'ouvre toujours, inchangée** : route `lettre_zonage.py:311` intacte, le
   front l'ouvre toujours (`Fiche.tsx:2067`, `/lettre-zonage/{idu}.pdf`) — aucun geste sur son contenu. ✓
5. **`tsc` vert · ruff sans nouveau warning** : `moteurs.py` = 1 E402 **pré-existant** (identique à
   origin/main), zéro nouveau. ✓

*Hors périmètre respecté : contenu de la lettre non touché, autres exports PDF non touchés, onglet
Évolution non touché (seul le bouton part). Commit sur `fix/m141-barometre-libelle`, push. CC ne merge jamais.*
