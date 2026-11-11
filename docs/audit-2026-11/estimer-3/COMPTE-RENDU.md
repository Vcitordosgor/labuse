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

**Banc permanent étendu aux niveaux d'information** (no-leak, ventes 2025, île entière, n = 1 500/type) —
écart médian · part à ±20 % :

| Type | sans rien saisir | + surface habitable | + nombre de pièces |
|---|---|---|---|
| **Maison** | **30 %** · 34 % | **24 %** · 43 % | 25 % · 41 % — *aucun gain → non posée* |
| **Appartement** | *sans objet¹* | **15 %** · 61 % | **15 %** · **62 %** *(Q3 28→27)* |
| **Terrain nu** | **35 %** · 34 %² | *— pas de question mesurable —* | |

¹ L'appartement n'a **pas de surface mesurable sans saisie** (l'emprise×ratio est une formule *maison*) :
son estimation commence à « surface connue ». ² Terrain : repère de secteur ESTIMER-2 (rayon adaptatif +
repli commune) ; la seule caractéristique candidate (viabilisé) n'est **pas une donnée** → non posée.

**Ce que ça change, prouvé :** répondre la **surface** fait passer la maison de **30 % → 24 %** d'écart
médian et **34 % → 43 %** à ±20 % — le plus gros gain, robuste 2024 **et** 2025. Les autres questions ont
été **mesurées une par une** et la plupart **écartées faute de gain** (§4). La précision n'est **jamais un
chiffre fixe** : à Saint-Denis une maison « surface connue » porte **±43 %** (commune dispersée, mesuré
sur 156 ventes), un appartement de Saint-Pierre (97410) **±21 %** — chacun sa mesure.

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
(type, commune, niveau d'information) elle porte l'**écart médian** (la fourchette « ± X % » typique qui
se resserre), le **Q3** (bande prudente ~75 % des ventes) et la **part à ±20 %**. Repli commune → île du
type ; banc jamais passé → bande prudente, **jamais de 500**.

Le niveau suit le **contenu d'information RÉEL** : une surface connue d'une vente DVF antérieure vaut
« surface connue » (la précision le reflète, sans que l'utilisateur ait rien tapé). La maison **plafonne à
« surface »** (les pièces n'y ajoutent rien). Exemple servi (commune) : Saint-Denis maison surface **±43 %**
(méd 28 %, 156 ventes) ; l'Entre-Deux appartement surface **±21 %** — chacun sa mesure, jamais un ±30 % fixe.

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

- **Surface habitable** — maison : écart médian **30 % → 24 %**, part ±20 % **34 % → 43 %** ; appartement :
  indispensable (pas de total sans elle). *Posée pour les deux types.*
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

- **Python unitaire** : **3 257 passed, 0 failed** (famille sans base) ; scan de secrets OK.
- **Tests ESTIMER-3** (`tests/test_estimer3.py`) : 14 verts (pondération par ressemblance, questions
  prouvées par type, écartement qui recalcule, précision par niveau mesurée, Radar, repli bande) ;
  canary du banc étendu + job de nuit verts. Graphe des lecteurs fins (G6) : dette 0, périmées 0.
- **Front NON touché** (mandat) ; `tsc -b` + `vitest` verts (inchangés).

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
