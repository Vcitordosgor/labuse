# ESTIMER-3 — une estimation qui se resserre, et qui le prouve

**Branche** `fix/estimer-3` · worktree `~/Desktop/labuse-estimer3` · ports 10080/7280 · base locale
`labuse` (DVF arrêté au 31/12/2025). **Calcul et API seulement — aucun fichier du front touché. Pas de
merge, aucun accès prod.** Date : 11/11/2026. Fait suite à [ESTIMER-AUDIT-1](../estimer-1/RAPPORT.md) et
[ESTIMER-2](../estimer-2/COMPTE-RENDU.md). Maquette servie : `docs/design/maquettes/nov-2026/11-estimer-3-temps.png`.

L'outil « Estimer un bien » est servi en **trois temps** : *sans rien saisir* (LABUSE montre ce qu'il a
mesuré + une première estimation), *les questions* (qui se resserre), *l'estimation affinée* (ventes
retenues écartables + Radar). **Chaque question doit prouver son gain** au banc no-leak, sinon elle n'est
pas posée. Tout chiffre de précision est **mesuré**, par commune et par type, à chaque niveau d'information.

---

## Le verdict en une page

**L'estimation ne part plus de toutes les ventes du secteur : elle part des ventes de biens qui
RESSEMBLENT au bien** (même type, surface et terrain proches, distance, ancienneté — pondération par
ressemblance), avec repli sur le prix de secteur d'ESTIMER-2 quand il y a trop peu de semblables (et la
réponse le dit). Elle **se resserre** à chaque réponse, et **la précision servie est celle mesurée** pour
le niveau d'information réellement disponible.

**Banc permanent, MÊME échantillon no-leak** (ventes 2025, île entière, n = 1 500/type) — écart **médian**
· part à **±20 %**, pour les trois méthodes. ESTIMER-2 = **prix de secteur** (médiane simple) ;
ESTIMER-3 = **comparables semblables** (pondérée). On **SERT la meilleure des deux à chaque niveau** :

| Type | ESTIMER-2 (secteur) | ESTIMER-3 sans saisie | ESTIMER-3 + surface |
|---|---|---|---|
| **Maison** | 30,3 % · 33 % | **30,3 % · 33 %** *(= secteur : voir ci-dessous)* | **24,5 % · 43 %** *(semblable)* |
| **Appartement** | 16,4 % · 58 %¹ | *sans objet²* | **15,4 % · 61 %** *(semblable)* |
| **Terrain nu** | 35 % · 34 %³ | *— pas de question mesurable —* | 35 % · 34 % |

¹ Appartement « surface connue » (pas de niveau sans saisie, cf. ²). ² L'appartement n'a **pas de surface
mesurable sans saisie** (emprise×ratio = formule *maison*) → son estimation commence à « surface connue ».
³ Terrain : repère de secteur ESTIMER-2 (rayon adaptatif + repli commune) ; la seule caractéristique
candidate (viabilisé) n'est **pas une donnée** → non posée, et ESTIMER-3 ne change pas le terrain.

**Dit franchement : sans saisie, la méthode « semblables » ne fait PAS mieux que le prix de secteur**
(maison 30,3 % contre 30,3 %, à égalité ; le secteur l'emporte d'un cheveu à ±20 %). **À ce niveau, on sert
donc le prix de secteur** (ESTIMER-2). **Dès que la surface est connue, « semblables » gagne** (maison
25,3 % → **24,5 %** ; appartement 16,4 % → **15,4 %**) et c'est elle qu'on sert. La règle est **mesurée et
servie cellule par cellule** (colonne `methode` de la table) : ESTIMER-3 **n'est jamais pire** qu'ESTIMER-2.
*(L'audit ESTIMER-2 citait 26,7 % pour la maison ; c'était un échantillon de 200. Sur 1 500 ventes, le prix
de secteur sans saisie est à 30,3 % — le présent banc, plus large, est la mesure de référence.)*

**Ce que la surface change, prouvé :** pour la maison, l'écart médian passe de **30,3 % → 24,5 %** et la
part à ±20 % de **33 % → 43 %** — robuste 2024 **et** 2025. Les autres questions ont été **mesurées une par
une** et la plupart **écartées faute de gain** (§4). La précision n'est **jamais un chiffre fixe** (§3).

---

## 1 — Comparables SEMBLABLES (le cœur)

Pour une parcelle bâtie, l'estimation €/m² est désormais la **médiane PONDÉRÉE par la ressemblance** des
ventes du **même type** de la commune (`pige.estimer3.eur_m2_semblable`). Chaque vente comparable pèse selon :

- sa **distance** au bien (noyau gaussien) ;
- son écart de **surface habitable** au bien (laplacien) — **seulement si la surface est connue** (saisie
  ou vente DVF antérieure) ; pondérer par une surface *estimée* ajouterait du bruit (mesuré) ;
- pour la **maison**, son écart de **taille de terrain** (laplacien) ;
- son **ancienneté** (demi-vie) ;
- son écart de **nombre de pièces** (laplacien) — **uniquement pour l'appartement** (§4).

Le **rayon est adaptatif** (500 → 1000 → 1500 m jusqu'à 8 ventes, sinon repli commune), comme ESTIMER-2.
**Les échelles de pondération ne sont pas inventées** : distance/surface/terrain/ancienneté viennent
d'ESTIMER-PRECISION-1, l'échelle des pièces (h = 0,8) est réglée ici au banc et confirmée hors-période.

**La meilleure des deux à chaque niveau.** Le banc mesure, sur le même échantillon, **le prix de secteur**
(médiane simple = ESTIMER-2) **et** les **semblables** (pondérée = ESTIMER-3) ; pour chaque (type, commune,
niveau) il retient la **méthode la plus précise**. Au service, l'outil calcule les deux médianes et sert
celle que le banc a désignée (`methode_prix`). Conséquence mesurée : **sans saisie on sert le secteur**
(les semblables n'aident pas), **surface connue on sert les semblables** (elles gagnent) — ESTIMER-3
**n'est jamais pire** qu'ESTIMER-2.

**Repli secteur.** Quand il reste moins de 8 ventes semblables (commune/ type rare), l'outil **replie sur
le prix de secteur d'ESTIMER-2** (`comparateur_bien`) et **le dit** (`repli_secteur: true`, note servie).

**Les ventes retenues sont servies** (date, surface, terrain, prix, distance, pièces, piscine), les plus
*pesantes* d'abord. **L'utilisateur peut en écarter** : l'API accepte la liste des mutations décochées
(`ecartees`) et **recalcule** (§6).

---

## 2 — Ce que LABUSE mesure seul, servi en clair

Sans aucune saisie, l'outil sert ce que LABUSE a **mesuré** (`pige.estimer3.mesures_labuse`) : **nature**
du bien, **terrain** (contenance), **emprise bâtie au sol** (BD TOPO), **niveaux** (hauteur LiDAR),
**surface habitable estimée** (emprise × ratio communal × niveaux, hypothèse en clair), **piscine**
(couche `piscines`, détection photo aérienne, île entière), **pente** (RGE ALTI, en ° et en %), **zone**
(PLU). Rien n'est demandé qui soit déjà mesuré.

---

## 3 — La précision est mesurée par commune × type × niveau (jamais fixe)

La précision servie vient du **banc permanent** (`estimer3_precision`), écrite chaque nuit : pour chaque
(type, commune, niveau), elle porte la **méthode gagnante** (secteur / semblable), l'**écart médian**, le
**Q3** et la **part à ±20 %**. Repli commune → île du type ; banc jamais passé → bande prudente, jamais de 500.

**Ce que « ± X % » veut dire exactement.** Deux chiffres mesurés, deux percentiles de l'écart
|estimé − réel| :
- le **± servi à l'écran** (`precision_pct`) = l'écart **MÉDIAN** (50ᵉ percentile) → *une estimation sur
  deux* tombe dans la fourchette `valeur × (1 ± médian)`. C'est lui qui **se resserre** à chaque réponse ;
- le **Q3** (`precision_q3_pct`, 75ᵉ percentile) = la **bande prudente** qui enferme ~trois estimations sur
  quatre, servie à côté pour qui veut l'intervalle large.

Donc l'ancien « ± 43 % » cité pour Saint-Denis était le **Q3** : à l'écran, une maison « surface connue »
de Saint-Denis porte **± 28 %** (médian) et sa bande prudente est **56 %** (Q3). Les cinq plus grosses
communes (maison, surface connue — médian servi / Q3 prudent / part ±20 % / méthode) :

| Commune | ± servi (médian) | bande prudente (Q3) | part ±20 % | méthode servie | n |
|---|---|---|---|---|---|
| Saint-Paul (97415) | **± 20 %** | 36 % | 51 % | semblable | 153 |
| Le Tampon (97422) | **± 25 %** | 41 % | 44 % | semblable | 214 |
| Saint-Pierre (97416) | **± 20 %** | 34 % | 51 % | semblable | 181 |
| Saint-Denis (97411) | **± 28 %** | 56 % | 35 % | secteur | 156 |
| Saint-Louis (97414) | **± 22 %** | 32 % | 46 % | secteur | 99 |

Saint-Denis est la plus dispersée (habitat urbain hétérogène) — et c'est là que le **prix de secteur** bat
les semblables, donc c'est lui qu'on sert. Jamais un ±30 % fixe : chaque commune porte **sa** mesure et
**sa** méthode. Le niveau suit le **contenu d'information RÉEL** : une surface connue d'une vente DVF
antérieure vaut « surface connue » (la précision le reflète sans que l'utilisateur tape quoi que ce soit) ;
la maison plafonne à « surface » (les pièces n'y ajoutent rien).

---

## 4 — Chaque question a prouvé (ou non) son gain

Mesure no-leak, par type de bien, sur le rétro-test (gain = réduction de l'écart médian et/ou de la part
hors ±20 %). Confirmé sur **deux millésimes** (ventes 2024 **et** 2025) pour écarter le hasard.

| Caractéristique | Maison | Appartement | Décision |
|---|---|---|---|
| **Surface habitable** | −6 pts médian, +9 pts à ±20 % (robuste 24/25) | indispensable (pas de total sans elle) | **POSÉE (les deux)** |
| **Nombre de pièces** | nul : 24→25 % médian, ±20 % 43→41 (n = 1 500) ; 2024 : −0,1 pt | gain : Q3 28→27, ±20 % 61→62 ; 2024 : +0,9 pt | **POSÉE (appartement seul)** |
| **Piscine** | **aucun gain** : écart neutre, et le test « comparables à piscine » **dégrade** le sous-ensemble concerné (13 %→22 % sur les mêmes biens) ; signe qui **s'inverse** d'une année à l'autre | idem (négligeable) | **NON posée** (mesurée, servie en clair) |
| **Vue dégagée** | aucune donnée sur les comparables | aucune donnée | **NON posée** (non mesurable) |
| **État** | aucune donnée d'état sur les ventes DVF | aucune donnée | **NON posée** (non mesurable) |
| **Terrain viabilisé** | — | — | **NON posée** (aucune donnée de viabilisation) |

**Piscine, le détail (flagship de la maquette).** La piscine est bien **détectée** (44 664 parcelles,
île entière) et **servie en clair**. Son premium brut €/m² est réel (**+13,5 %** médian, maison). Mais une
fois la **localisation et la surface** prises en compte (pondération), la piscine **n'apporte plus rien** :
restreindre aux « comparables à piscine » **dégrade** l'estimation des biens poolés sur le même échantillon
(13,0 % → 22,0 % d'écart médian), et en pondération son effet est **neutre à l'île** et de **signe
instable** (−0,5 pt en 2025, +1,6 pt en 2024 = bruit). Conformément au mandat, **elle ne déplace pas le
prix** — elle est montrée, pas posée.

**Pièces, le détail.** Pour l'**appartement**, les pièces resserrent (Q3 28→27, +1 pt à ±20 %, stable
2024/2025) → **posée**. Pour la **maison**, une fois la surface connue, elles **n'ajoutent rien** de
mesurable (médiane à peine pire, ±20 % en léger recul à grand échantillon) → **non posée pour la maison**.
La question « pièces » est donc **propre à l'appartement**.

Aucun coefficient n'a été inventé : une caractéristique sans gain mesuré **ne déplace pas le prix**.

---

## 5 — Écarter une vente, et recalculer

Chaque vente retenue porte son identifiant de mutation. L'API `POST /radar/annonce/estimation3/{idu}`
accepte `ecartees: [...]` : les ventes décochées sont **retirées de l'estimation** et **marquées écartées**
dans la liste servie (jamais une disparition muette). Le €/m², la fourchette et le total **sont recalculés**.
*(test `test_ecarter_une_vente_recalcule`)*

---

## 6 — Radar : biens semblables en vente + écart affiché/vendu

L'outil sert les **biens similaires actuellement en vente** (`pige_biens`/`pige_faits`) — type, pièces,
surface, prix affiché — les plus proches en surface d'abord.

**L'écart moyen prix affiché ↔ prix vendu** n'est servi **que s'il est mesurable** sur un échantillon
suffisant (≥ 20 annonces **rattachées à une vente DVF**, `vendue_ecart_prix`). **Sur la base locale, il
n'est PAS servi** : **0 annonce rattachée à une vente** (ni par commune, ni sur l'île). L'outil l'écrit
(« Écart affiché/vendu non servi : trop peu d'annonces rattachées à une vente DVF ») plutôt qu'inventer un
chiffre. Dès que le rapprochement annonces↔DVF (job `cycle.matcher_dvf`) aura peuplé `vendue_ecart_prix`
en production, l'écart s'affichera automatiquement, par commune puis île.

---

## 7 — Le banc permanent, étendu aux niveaux d'information

`pige.banc_estimer.calcule_niveaux` rejoue **sans fuite** l'estimation **servie** (`estimer3`,
banc == servi) à trois niveaux (surface estimée / connue / + pièces), par type et commune, et écrit
`estimer3_precision` (écart médian, Q3, part ±20 %). Échantillon **1 500/type** (les grosses communes
dépassent le seuil de cellule de 25 ventes → précision commune ; les petites replient sur l'île). Le job de
nuit **`estimer-banc-precision`** (déjà au registre) persiste désormais **aussi** cette table et journalise
les écarts médians du niveau le plus informé.

---

## 8 — Bilan : questions gardées / abandonnées, chiffres à l'appui

**GARDÉES** (gain mesuré, prouvé 2024 **et** 2025) :

- **Surface habitable** — maison : écart médian **30,3 % → 24,5 %**, part ±20 % **33 % → 43 %** ;
  appartement : **16,4 % → 15,4 %** (indispensable — pas de total sans elle). *Posée pour les deux types.*
- **Nombre de pièces** — appartement : Q3 **28 → 27**, part ±20 % **61 → 62 %**, stable sur deux millésimes.
  *Posée pour l'appartement seulement.*

**ABANDONNÉES** (sans gain mesuré, ou non mesurables) :

- **Nombre de pièces — MAISON** : surface connue, les pièces n'ajoutent rien (médiane **24 → 25 %**, ±20 %
  **43 → 41 %**). *Non posée pour la maison.*
- **Piscine** : premium brut +13,5 % entièrement absorbé par la localisation ; le filtre « comparables à
  piscine » **dégrade** (13 → 22 %) ; signe instable entre années. *Mesurée et servie en clair, pas posée.*
- **Vue dégagée** : aucune donnée sur les ventes comparables → gain **non mesurable**.
- **État** (bâti) : aucune donnée d'état dans le DVF → gain **non mesurable** (comme anticipé par le mandat).
- **Terrain viabilisé** : aucune donnée de viabilisation → gain **non mesurable**.

Il reste donc **deux** questions qui déplacent le prix : **surface habitable** (les deux types) et
**nombre de pièces** (appartement). Tout le reste est soit **mesuré et montré** (piscine, pente, niveaux,
terrain, zone), soit **non posé parce que non prouvé**.

---

## Ce qui est vérifié vert

- **Python unitaire** : **3 257 passed, 0 failed** (famille sans base) ; scan de secrets OK ;
  **cohérence 6/6, 0 écart**.
- **Tests ESTIMER-3** (`tests/test_estimer3.py`) : **15 verts, 0 ignoré** — pondération par ressemblance,
  questions prouvées par type, **meilleure des deux méthodes**, écartement qui recalcule, précision par
  niveau mesurée, Radar, repli bande, **endpoint POST exécuté pour de vrai** (le conftest force l'app sur
  `labuse_test` → le test redirige la session de l'endpoint vers la base réelle, le chemin de l'endpoint
  est exercé tel quel, écartement compris). Canary du banc étendu + job de nuit verts. Graphe des lecteurs
  fins (G6) : dette 0, périmées 0.
- **Front NON touché** (mandat) ; `tsc -b` 0 + `vitest` 326 verts (inchangés).

## Fichiers

| Fichier | Rôle |
|---|---|
| `src/labuse/pige/estimer3.py` | estimation « comparables semblables », mesures LABUSE, questions prouvées, précision par niveau, Radar, assemblage servi |
| `src/labuse/pige/api.py` | endpoint `POST /radar/annonce/estimation3/{idu}` (surface, pièces, ventes écartées) |
| `src/labuse/pige/banc_estimer.py` | banc permanent ÉTENDU aux niveaux (`calcule_niveaux`/`persiste3`), table `estimer3_precision` |
| `src/labuse/jobs_impl.py` | job de nuit `estimer-banc-precision` : persiste aussi `estimer3_precision` |
| `src/labuse/registre/lectures.py` | déclaration fine des nouvelles lectures (pièces DVF, pool bâti, Radar) |
| `tests/test_estimer3.py` | recette (pur + canary + réel) |
| `docs/audit-2026-11/estimer-3/mesure.py` | prototype de mesure des gains (no-leak, par caractéristique) |

**Rejouer le banc des niveaux** :
`LABUSE_DATABASE_URL=postgresql+psycopg:///labuse ~/Desktop/labuse/.venv/bin/python -m labuse.pige.banc_estimer --niveaux`
(PYTHONPATH=src).

---

# Écran (ESTIMER-ECRAN-1)

*Mandat : l'écran Estimer sur la maquette validée `docs/design/maquettes/nov-2026/12-estimer-un-ecran.png`. Branche `fix/estimer-3`, worktree `~/Desktop/labuse-estimer3`. Calcul+API+**front**, aucun accès prod, pas de merge.*

## Étape 0 — base
`origin/main` **contient** `fix/retours-23` (`49f98abf4`, la refonte des outils) : condition remplie. `origin/main` mergé dans la branche (merge `ort`, **0 conflit** ; apporte EXIGU-FIX-1). Hook complet rejoué ensuite.

## Ce qui a été fait

### Un seul écran, autour de la boîte parcelle
`frontend/src/components/outils/AnalyserAnnonce.tsx` — le chemin **parcelle** est refondu en UN écran (plus d'étape « entrée → rapport ») :
- **Boîte parcelle (option A)** : adresse en gras + « IDU · zone · surface » + ✕ pour changer. Rendue **localement** dans l'écran (le composant partagé `EntreeParcelle` n'est PAS modifié — il sert 15 autres outils et son option A n'est pas encore mergée : la changer dépassait « l'écran Estimer » et aurait déstabilisé les autres outils). L'entrée vide reste le `ParcelInput` commun (adresse / clic carte).
- **« Ce que LABUSE a mesuré »** : en puces, UNIQUEMENT ce qui est connu — type, terrain, bâti au sol, niveaux, piscine, pente (la zone vit dans la boîte, pas en puce).
- **Une seule question** — la surface habitable, pré-remplie par l'estimation de LABUSE (badge **estimée**, hypothèse écrite dessous), saisie au clavier (`inputMode=numeric`, validée au blur/Entrée), badge **saisie** dès qu'on la change. Pour un **appartement**, s'ajoute le **nombre de pièces** (chips 2·3·4·5·6+). Pour un **terrain nu**, aucune question (ni état, ni vue, ni piscine, ni viabilisation).
- **La valeur estimée** — le montant, le badge de fiabilité, et une **jauge à deux bandes** : « 1 fois sur 2 » (écart médian) et « 3 fois sur 4 » (Q3), chacune avec ses **deux bornes en euros**. Dessous : la **méthode servie** (« Biens semblables » / « Prix du secteur ») + « mesuré sur les ventes réelles de [type] à [commune] ».
- **Les ventes retenues** — date, surface·terrain, prix, distance ; chaque ligne se **décoche** (case) → l'API **recalcule** (`ecartees`).
- **« En vente en ce moment · Radar »** — les biens similaires s'il y en a ; sinon le bloc n'apparaît pas.
- La ligne « LABUSE ne connaît ni l'état du bien ni sa vue : ce prix est un repère de marché, pas une expertise. » et l'**export PDF**.

Le chemin **lien d'annonce** (Leboncoin) n'est plus une entrée de l'écran (la maquette est parcelle-only) : il reste atteignable **depuis le Radar** (« Estimer ce bien → »), son rapport commune inchangé.

### API — deux fourchettes servies telles quelles
`src/labuse/pige/estimer3.py` : l'estimation sert désormais **`valeur_basse_q3` / `valeur_haute_q3`** (bande « 3 fois sur 4 ») à côté de `valeur_basse` / `valeur_haute` (bande « 1 fois sur 2 »), en euros, calculées à partir du même central ± l'écart **médian** / **Q3** mesuré, pour le bâti ET le terrain. Jamais une fourchette unique présentée comme sûre ; le front n'invente aucune largeur (il affiche ce que l'API sert). `frontend/src/lib/api.ts` : type `Estimer3Rapport` + `getEstimation3(idu, {surface_hab, pieces, ecartees})` (POST).

### Un seul prix partout — écran == PDF == document, 0 écart
`src/labuse/pige/api.py` : `rapport_parcelle` (le point du PDF parcelle « Estimer un bien ») lit désormais son estimation du **MÊME point que l'écran** (`estimer3.rapport3`), via l'adaptateur `_est_bloc_depuis_estimer3` (reformate ESTIMER-3 au format du bloc PDF sans rien recalculer). Le bloc PDF (`exports/blocs/annonce.py`) est **inchangé** (ses tests sur fixtures restent verts). Résultat : sans saisie, l'écran et le document affichent **exactement** le même prix.
**Banc des documents** : `tests/coherence_ecrans/test_temoins.py::test_estimer3_ecran_egale_document` — sur les 12 témoins, `estimer3.rapport3(...).estimation.valeur_eur` == la valeur **imprimée** dans le document rendu (`rendu_parcelle`), à l'euro, et réellement présente dans le texte. **0 écart** (vert). Correctif découvert par le banc : la branche **terrain** n'exposait pas `surface_utilisee_m2` → la valeur n'était pas imprimée ; corrigé.

## Preuves — captures WebKit
`docs/audit-2026-11/estimer-3/` (WebKit, DPR 2, consentement cookies pré-posé) :
- `ecran-maison-sans-saisie.png` — maison, surface **estimée** (116 m²), 417 000 €, bandes 334–501 k€ / 267–568 k€, « Biens semblables ».
- `ecran-maison-surface.png` — même maison, surface **saisie** 140 m² (badge vert), valeur recalculée 504 000 €, bandes 403–604 k€ / 322–685 k€.
- `ecran-appartement.png` — appartement, question **pièces** présente, « …ventes réelles d'appartements à Saint-Paul ».
- `ecran-terrain-nu.png` — terrain, **aucune question**, puces sans bâti/niveaux, Radar « terrains ».

## Hook
`tsc -b` 0 · `vitest` 326 · `pytest` unitaires verts (seule `test_annonce_lien` avait buté sur la phrase d'échec raccourcie → phrase du mandat restaurée) · **cohérence** 7/7 (dont le nouveau banc écran==document). Scan de secrets vert.

## Écarts / notes
- **Ports** : la maquette/mandat cite `10080/7280`. Le port **10080 est bloqué** par Chromium ET WebKit (« restricted network port ») → le front tourne sur **10800** (backend 7280 inchangé) pour les captures ; aucune incidence produit (port de dev).
- **`EntreeParcelle` option A** : rendue localement dans l'écran Estimer (composant partagé non modifié — voir ci-dessus).
- **Pré-existant** : `tests/test_pige_socle.py::test_aucune_requete_portail` (marqueur `db`, hors hook) échoue sur des libellés d'e-mails `mails_contenu.py` sans rapport avec ce mandat (fichier non touché).

## Fichiers (écran)

| Fichier | Rôle |
|---|---|
| `frontend/src/components/outils/AnalyserAnnonce.tsx` | l'écran Estimer en un seul écran (boîte option A, mesures, question unique, valeur + jauge deux bandes, ventes décochables, Radar, PDF) |
| `frontend/src/lib/api.ts` | types `Estimer3Rapport` + `getEstimation3` (POST estimation3) |
| `src/labuse/pige/estimer3.py` | `valeur_basse_q3`/`valeur_haute_q3` (bâti + terrain), `surface_utilisee_m2` terrain |
| `src/labuse/pige/api.py` | `rapport_parcelle` → estimation du PDF sourcée d'ESTIMER-3 (`_est_bloc_depuis_estimer3`) |
| `tests/coherence_ecrans/test_temoins.py` | banc des documents : écran Estimer == document, 0 écart |

---

# Raccord avec la refonte des outils + 2 défauts (ESTIMER-ECRAN-1, suite)

## Étape 0
`git merge-base --is-ancestor d8916edc0 origin/main` → **vrai** : la refonte des outils (OUTILS-REFONTE-1) est dans `origin/main`.

## (1) Merge origin/main + boîte parcelle commune
`origin/main` mergé dans `fix/estimer-3`. **Un seul conflit** (`AnalyserAnnonce.tsx`) : les deux côtés avaient refondu l'écran (le nôtre sur ESTIMER-3, celui d'`origin/main` sur l'ancien rapport). On a **gardé le nouvel écran** et remplacé sa boîte parcelle locale par le **composant commun des outils** `EntreeParcelle` (option A : adresse en gras + « IDU · zone · surface » + ✕, **affichage instantané** via `getParcelApercu`). L'écran rend `<EntreeParcelle>` en tête (recherche tant qu'aucune parcelle, boîte remplie ensuite) puis `<Estimer3>` dessous. `api.ts` a fusionné sans conflit (`getEstimation3` + `getParcelApercu` coexistent).

## (2) Deux défauts vus par Vic

### DÉFAUT A — surface inconnue + bande « 3 fois sur 4 » > ± 50 % → pas de valeur totale
Quand la surface habitable **n'est pas connue** (ni saisie, ni vente DVF : estimée au LiDAR) **et** que la bande « 3 fois sur 4 » dépasse ± 50 % (`SEUIL_Q3_MASQUE`), l'API **ne sert plus de valeur totale** (`total_masque=True`, `valeur_eur=null`). L'écran affiche le **prix au m² du secteur avec sa fourchette** (`eur_m2`, `eur_m2_bas`–`eur_m2_haut`) et **invite à saisir la surface**. Dès qu'elle est saisie (`surface_connue=True`), le masque tombe : la valeur et ses **deux bandes** reviennent. Même point partagé → le PDF se comporte pareil (pas de total imprimé, €/m² + fourchette).

### DÉFAUT B — valeur du terrain seul > estimation bâtie
**Mesuré au banc no-leak** (`docs/audit-2026-11/estimer-3/mesure_plancher.py`, 2 060 maisons) : retenir la valeur du terrain comme **plancher** `max(bâti, terrain)` **n'améliore PAS** la précision — il la **dégrade**.

| | écart médian | ±20 % |
|---|---|---|
| cas concernés « terrain > bâti » — bâti seul | 29,7 % | 35,3 % |
| cas concernés — **avec plancher** | 45,2 % | 26,9 % |
| global toutes maisons — bâti seul | 27,1 % | 38,5 % |
| global — avec plancher | 29,4 % | 36,2 % |

**Part des cas concernés (terrain > bâti) : 28,6 % des maisons (590/2 060).**

→ **Décision (correction Vic)** : puisque la mesure montre que retenir le terrain **dégrade** la précision, sur un bien **bâti** on **n'affiche plus aucune valeur de terrain — ni bandeau, ni bloc**, et la **fiabilité reste celle mesurée au banc** pour le cas (jamais rabaissée à cause du terrain). La valeur de terrain **reste servie pour les terrains nus** (inchangé). *(Version intermédiaire : un avertissement + fiabilité forcée « Limitée » avaient d'abord été ajoutés, puis retirés — la mesure ne les justifie pas.)*

**Cas témoin 97415000AW1367** : surface habitable inconnue, Q3 = 66 % → l'écran masque le total (prix au m² 3 423 €/m², de 2 946 à 4 100 €/m² + invite à saisir la surface), **sans aucune mention du terrain** ; fiabilité « Limitée » parce que le banc le mesure (écart médian élevé), pas à cause du terrain. Avec une surface saisie (90 m²), la valeur totale revient (310 000 € + deux bandes).

## Preuves — captures WebKit
`docs/audit-2026-11/estimer-3/` : `ecran-maison-sans-saisie`, `ecran-maison-surface`, `ecran-appartement`, `ecran-terrain-nu` (boîte commune EntreeParcelle), **`ecran-aw1367-masque`** (défaut A : total masqué, prix au m² + invite, aucune mention du terrain), **`ecran-aw1367-surface`** (masque levé).

## Tests / hook
Mesure : `mesure_plancher.py`. Tests reel `test_estimer3.py` : +2 (`test_defaut_a_masque_total_…`, `test_defaut_b_terrain_dominant_…`), 18/18. Banc des documents (cohérence) inchangé, vert (les témoins masqués ont `valeur_eur=null` des deux côtés → 0 écart). `tsc` 0 · `vitest` 326.

## Fichiers (raccord + défauts)

| Fichier | Rôle |
|---|---|
| `frontend/src/components/outils/AnalyserAnnonce.tsx` | boîte parcelle = `EntreeParcelle` commune ; écran masqué (prix au m² + invite) ; aucune valeur de terrain sur bâti |
| `frontend/src/lib/api.ts` | champs `total_masque`/`eur_m2_bas/haut`/`terrain_depasse`/`terrain_valeur_eur`/`plancher_terrain_applique` |
| `src/labuse/pige/estimer3.py` | DÉFAUT A (masque + €/m² fourchette) ; DÉFAUT B (aucune valeur de terrain sur bâti ; fiabilité du banc inchangée) |
| `src/labuse/pige/api.py` | adaptateur PDF : €/m² + fourchette, pas de total masqué |
| `docs/audit-2026-11/estimer-3/mesure_plancher.py` | mesure no-leak du plancher terrain (verdict : n'améliore pas) |
| `tests/test_estimer3.py` | +2 tests reel (défauts A et B sur AW1367) |

---

# Recette de l'écran Estimer (ESTIMER-ECRAN-1, suite)

Même branche `fix/estimer-3`, pas de merge, WebKit, capture par point.

1. **Dernière vente du bien** — quand la parcelle a sa propre vente DVF, elle est montrée **juste sous la boîte parcelle** : « Dernière vente de ce bien : mois/année · surface · prix » (`rapport3.derniere_vente`, composant `DerniereVente`). Elle n'entre **pas** dans le calcul, elle est affichée. (AZ1645 : « 12/2025 · 116 m² · 455 000 € » ; AW1367 : aucune vente → ligne absente.)
2. **Surface habitable — provenance** (`estimation.surface_hab_detail` {source, badge, texte}) :
   - vente DVF → badge **« connue »**, texte **« Surface de la vente de 2025 (DVF) »** ;
   - calcul depuis le bâti → badge **« estimée »**, texte avec la **formule complète** « 109 m² au sol × 1 niveau × 0,5, part habitable moyenne du secteur (LiDAR) » ;
   - saisie utilisateur → badge « saisie ». Les mots **« DVF »** et **« LiDAR »** sont écrits.
3. **Total masqué** (surface non connue, fourchette trop large) — le **champ est vide** (placeholder « à saisir »), l'**estimation de LABUSE est en indication dessous** (« LABUSE estime ≈ 54 m² — 109 m² au sol × 1 niveau × 0,5, part habitable moyenne du secteur (LiDAR). Saisissez la surface réelle… »), et l'**encadré ne dit plus « inconnue »** (il n'y a plus de champ rempli à côté). Le préremplissage est désactivé quand `total_masque`.
4. **Ventes retenues** — rien de tronqué : chaque ligne porte **date, surface habitable, surface du terrain, prix, distance**, sur **deux lignes** (prix + date en haut, « X m² hab. · Y m² terrain · Z m » en dessous).
5. **Radar** — chaque annonce porte sa **commune** et sa **distance** ; seules les **cinq plus proches** sont listées (tri par distance, rayon `_RADAR_RAYON_M` = 10 km, toutes communes confondues — une annonce voisine peut être dans une autre commune, ex. AW1367 : Saint-Paul **et** La Possession) ; le **bloc n'apparaît pas** s'il n'y en a aucune à proximité.
6. **En-tête** — le bouton est **« ← Retour »** (comme tous les outils) ; le libellé **« Une adresse ou une parcelle » au-dessus de la boîte est retiré** (le sous-titre de l'en-tête le dit déjà).

**Captures** (WebKit, panneau complet) : `ecran-maison-sans-saisie` (AZ1645 : dernière vente, « connue » DVF, ventes 2 lignes, Radar commune+distance), `ecran-maison-surface`, `ecran-appartement`, `ecran-terrain-nu`, `ecran-aw1367-masque` (champ vide + indication, pas de « inconnue », Radar multi-communes), `ecran-aw1367-surface`.

**Fichiers** : `src/labuse/pige/estimer3.py` (`_derniere_vente_bien`, `_surface_hab_detail`, `radar_semblables` distance/commune/5-plus-proches/rayon), `frontend/src/lib/api.ts` (types), `frontend/src/components/outils/AnalyserAnnonce.tsx` (`DerniereVente`, Question badge/texte + champ vide si masqué, VentesRetenues 2 lignes, RadarEnVente commune+distance, en-tête « Retour », libellé retiré).
