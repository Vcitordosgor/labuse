# RAPPORT M55-I — Retrait du tri Mutation + 4 correctifs (12/08/2026)

**Branche** : `feat/m55-i` (base : main `ef4983bf` = M55-H mergé — précondition vérifiée).
**5 commits, un par point** (`b2214482` → `6ada4437`) + ce rapport. CC ne merge jamais.
**Captures** : `reports/m55-i/captures/` (harnais `frontend/qa/m55i_captures.mjs`, rejouable).
**Périmètre** : FRONT uniquement. Aucun changement moteur, aucun endpoint.

## 1. Logo accueil coupé — cause corrigée
**Cause mesurée** (avant) : le conteneur `AccueilPreuves` était `flex justify-center overflow-y-auto`.
`justify-content: center` + overflow **clippe le haut** du contenu qui déborde et le rend
inatteignable au scroll (bug flexbox connu) — le logo, en tête, se retrouvait au-dessus du
bord haut (offset mesuré −2 / −33 / −64 px à 900 / 800 / 700 px, `scrollTop` bloqué à 0).
**Correctif structurel** (pas une marge) : le conteneur scrolle (`justify-start`), le CONTENU
est centré par **marges automatiques** (`my-auto` sur un wrapper) — elles centrent quand il y
a de la place ET se réduisent à 0 quand ça déborde, laissant le logo défiler depuis le haut.
`pt-6` garde une respiration au sommet.
**Vérifié** : logo `logoFullyVisible: true`, `logoClippedTop: false` aux 6 tailles
(1440×900 / 1200×800 / 1024×700 / 900×700 / 768×800 / 480×700). Captures `i1_avant_*` /
`i1_apres_*`.

## 2. Accordéon — automate à deux états, point final
**Chasse préalable** — tableau des chemins d'ouverture/fermeture, tous testés :

| # | Chemin | État visé | Conforme |
|---|--------|-----------|----------|
| 1 | Démarrage / rechargement / lien partagé (défaut store) | A (Couches) | ✓ |
| 2 | Clic titre Couches (`ouvrirCouches`) | A | ✓ |
| 3 | Clic titre Filtres (`ouvrirFiltres`) | B (Filtres) | ✓ |
| 4 | Chevron (dans le `<button>` du titre) | = clic titre | ✓ |
| 5 | Badge « N actives/actifs » (dans le `<button>`) | = clic titre | ✓ |
| 6 | Re-clic sur la section DÉJÀ ouverte | reste (no-op) | ✓ |
| 7 | « Commencer → » (`openFiltres`) | B | ✓ |
| 8 | Header CommuneSelect multi (`openFiltres`) | B | ✓ |
| 9 | Allumage analyse (`verdict` false→true) | A | ✓ |
| 10 | Retour post-analyse (`onRetract`) | A | ✓ |

**Implémentation** : l'état `panneauSection` est du type `'couches' | 'filtres'` (JAMAIS
`null`, acquis M55-H point 8) ; `couchesOpen` / `filtresOpen` en DÉRIVENT — exactement une
section ouverte à tout instant. L'impossibilité (2 ouvertes / 2 fermées) est **structurelle
(le type)**, pas une garde. M55-I durcit : handlers renommés `ouvrirCouches`/`ouvrirFiltres`
(ils ouvrent, ne « togglent » jamais vers du vide) + invariant documenté. `panneauSection`
n'est ni persisté en URL ni en localStorage → un rechargement/lien partagé retombe toujours
sur le défaut A (le `al=1` allume l'analyse, dont l'effet ramène à A).
**Validation** : sonde `_i2_automate` = 8 chemins, tous « 1 seule section ouverte » ; sonde
`_i2_reload` (pages fraîches) = A pour tous les liens de rechargement. Aucun état à 2 ouvertes
ni à 2 fermées reproductible. Captures `i2_etatA_couches` / `i2_etatB_filtres`.
*(Nota QA : un `page.goto` Playwright vers une URL qui ne diffère que par le hash ne recharge
pas — false positif écarté en repassant sur des pages fraîches.)*

## 3. Retrait du tri « Mutation » (arbitrage Vic, option A)
Le tri « Mutation » (clé `mult`, le ×N seul) est RETIRÉ — doublon prouvé du classement en
M55-H (top-50 identiques, aucune inversion stricte sur 431 663). Restent deux tris :
« **Probabilité de vente** » (l'ancien « Opportunités », renommé honnêtement — c'est ce qu'il
trie) et « **Surface** » (inversible ↓/↑, acquis M55-H). Le « i » de la barre TRIER dit le
réel : « le classement LABUSE : la probabilité de vente apprise d'abord, les ex æquo départagés
par la qualité du terrain ». `CLIENT.tri.mult` et `multTip` = 0-caller, retirés ; `multBadge`
(tooltip ×N des cartes) conservé. **Le tri n'est jamais sérialisé en URL** (aucune clé de tri
dans le hash) → aucun vieux lien ne peut le porter, rien à ignorer ; la clé serveur `mult`
reste valide côté API mais n'est plus atteignable depuis la barre. Le passage à un vrai rang
P×C reste une évolution moteur — HORS PÉRIMÈTRE. Sonde : tris = `["Probabilité de vente",
"Surface"]`. Capture `i3_tri_bar`.

## 4. Les deux « comprendre le classement »
**Vérifié** : les DEUX boutons appellent `setAlgoOpen(true)` (store partagé `algoOpen`) et
ouvrent la MÊME modale `AlgoExplainer` — même titre « Comment LABUSE classe les parcelles »
(instance unique rendue dans VerdictHero). Le bouton du HAUT (bandeau analyse) garde
« Comprendre le classement » ; le lien du BAS (avant la liste) reprend son libellé d'avant
« **comprendre le scoring →** » (`CLIENT.algo.lien`, utilisé uniquement là). Sonde :
haut = « Comprendre le classement », bas = « comprendre le scoring → », les deux ouvrent la
même modale. Capture `i4_modale`.

## 5. Le rang quitte les badges de carte de résultat
« Brûlante · 59 » → « **Brûlante** ». Le rang suggérait une précision que les ex æquo massifs
du v8 ne portent pas (15 valeurs de ×N distinctes dans le top 500, mesuré M55-H) et la liste
est déjà ordonnée. Retiré du badge ET de son infobulle de survol (le « rang 59 hors copro »
SANS dénominateur était justement la fausse précision). Restent sur la carte : le tier + le ×N
(colonne droite, son tooltip conservé). **Le rang complet avec son dénominateur reste en fiche
parcelle (ScoreV2Block) et dans les exports — non touchés.** Sonde : 0 badge portant encore un
rang. Capture `i5_carte_sans_rang`.

## Non-régression
- **5 combinaisons /filtre STRICTEMENT identiques** à M55-H (front-only, aucun endpoint
  touché) : sans filtre 431 663 (118/1038/2964/29978/354355) · Saint-Denis 38 138 ·
  tiers=brûlante,chaude 1 156 · signaux=procédure,friche 2 458 · surface+nu+Saint-Paul 948.
- **Rituel 3 317 ms** (3 000 ms d'animation + réseau).
- **Récit unique / ventilation bouclée** : 118 + 1 038 + 2 964 + 29 978 + 43 210 = 77 308
  retenues + 354 355 écartées = **431 663** ; les 6 familles affichées, mêmes nombres que la
  Révélation (source unique getFiltre).
- **Carte == liste** (M55-G) préservé : Salazie + procédure → liste 1 / peintes 1.
- **Groupement par tiers** (M55-H) intact : page 1 = Brûlante → Chaude.
- **tsc 0 · vitest 32/32 · build vert** · **mobile** vérifié (375 px) · **0 erreur console**.

## Périmètre
Front + libellés (strings.ts). Aucun changement moteur, aucun endpoint. `feat/m55-i` en
attente de merge par Vic.
