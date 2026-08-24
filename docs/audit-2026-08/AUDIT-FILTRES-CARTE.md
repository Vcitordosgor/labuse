# AUDIT — Filtres de la barre latérale carte

**Date** : 2026-08-24 · **Branche** : `audit/filtres-carte` · **Type** : audit seul (aucune modification de code ; Postgres en lecture stricte — `SELECT`/`count` ; endpoint sondé en `GET`).
**Périmètre** : les filtres du panneau latéral de la carte (chaîne contrôle → paramètre → SQL réel). On ne juge pas le design, seulement la tuyauterie et la donnée.
**Méthode** : registre front (`FiltreLabuse.tsx`, source de vérité des contrôles rendus) → `filterParams` → endpoint `GET /filtre` (`_q_v2_where`/`_q_v2_stats`), croisé avec la base locale (run servi `q_v10_m129`, 431 663 parcelles) et des comptes réels servis par l'endpoint en marche.

> App laissée intacte (uvicorn:8000 + vite) : uniquement des `GET /filtre?...&limit=0` (compteur), aucune écriture, aucun redémarrage.

---

## 0. Ce qui est réellement exposé — **7 filtres**, pas 43

L'interface `Filters` du store compte **43 champs**, mais le panneau latéral (`frontend/src/components/panel/FiltreLabuse.tsx`) n'en **rend que 7** comme contrôles utilisateur. Les ~36 autres n'ont **aucune UI latérale** : ils vivent dans le Copilote (cadrage projet), le deep-link URL (`#f=`), le volet Surveillance, ou sont des vestiges. L'endpoint `/filtre` est donc un **sur-ensemble partagé** (50 paramètres) ; la barre latérale n'en pilote qu'une petite partie.

Les 7 contrôles latéraux : **Communes · Surface (min/max) · Zonage (familles) · Zonage (zones exactes) · État du sol · Signaux de vie · l'interrupteur Analyse LABUSE** (piloté par gestes, pas un toggle visible).

---

## 1. Tableau des filtres latéraux

| # | Contrôle | Champ `Filters` → param | Ce que le WHERE fait vraiment (table/colonne) | Compte réel servi | Verdict | Constat |
|---|----------|-------------------------|-----------------------------------------------|-------------------|---------|---------|
| 1 | Communes (chips CP ×24) | `communes` → `communes` | `p.commune = ANY(:communes)` (parcels) | — | ✓ | 24 CP, multi-select, « toute l'île » si vide. Intersection propre. |
| 2 | Surface min/max (saisies) | `surfaceMin/Max` → `surface_min/max` | `p.surface_m2 >= / <=` (parcels) | `surface_min=1000` → 128 456 | ✓ | Saisie libre, **aucun plafond UI** (donc P4 sans objet) ; réel 0–28,2 M m². ⚠ voir §2.1 (slivers <2 m²). |
| 3 | Zonage — familles (chips U/AU/A/N) | `zonagePlu` → `zonage` | `EXISTS parcel_zone_plu.zone_fam = ANY` | `zonage=U` → 306 630 | ✓ | Familles = valeurs réelles exactes (U 306 630 · A 73 946 · N 36 306 · AU 10 537). |
| 4 | Zonage — zones exactes (menu) | `zonePlu` → `zone_plu` | `EXISTS parcel_zone_plu.zone_filtre = ANY(upper(...))` | — | ✓ | Options chargées de la base (`/zonage/zones`), donc alignées. ⚠ pliage `upper()` §2.4 (risque faible). |
| 5 | État du sol (chips nu/bâti) | `etatSol` → `etat_sol` | `nu = NOT (COALESCE(taux_emprise_pct,0)≥5)` / `bati = (…≥5)` (parcel_residuel) | nu 205 594 · bâti 226 069 | ⚠ | **Partition complète (somme = 431 663), aucune exclusion silencieuse**, MAIS « nu » absorbe 177 899 emprises NULL (§2.2). |
| 6 | Signaux de vie (chips ×7) | `signaux` → `signaux` | 7 sous-clauses `OR` (parcel_signaux_vie + bodacc/pc_caducs/defisc/PM/veille) | permis_actif 7 002 · friche 1 801 | ✓ | Les 7 clés front (`pm_privee, procedure, permis_actif, permis_caduc, friche, defisc, succession`) ∈ `_SIG_SQL` : **aucune chip morte**. |
| 7 | Analyse LABUSE (gestes) | `analyseLabuse` → `tiers` | tiers appliqués seulement si l'analyse est ON ; étage 0 prime | brulante 82 · chaude 1 525 · écartée 145 882 | ✓ | Path tiers **exact** au bit près (union brulante+chaude = 1 607). ⚠ commentaire d'interface faux (§2.3). |

**Compteur vivant** (`getFiltreCount`, `limit=0`) : `total = COUNT(*)` avec **le même WHERE** que la liste, **aucun LIMIT**, mémorisé 30 s. Sans filtre → **431 663** (tout le cadastre, écartées incluses). Sur combinaison → intersection propre (ex. `signaux=permis_actif & etat_sol=nu` = **3 009**, cohérent avec 7 002 ∩ nu). **Le compteur est fiable** (pas de divergence liste/compte, pas de plafond qui masquerait).

---

## 2. Détail (là où il y a quelque chose à dire)

### 2.1 — Slivers <2 m² comptés mais non affichés ⚠ (faible)
`MIN_DISPLAY_SURFACE_M2 = 2.0` masque **850** parcelles de la liste ET de la carte, mais elles restent **comptées** par le compteur vivant. Donc « N parcelles correspondent » peut dépasser de ~850 ce que l'utilisateur voit à l'écran (île entière, sans filtre de surface). Écart marginal, jamais un faux positif ; mais compteur ≠ visible.

### 2.2 — « Terrain nu » absorbe les emprises inconnues ⚠ (faible)
Le filtre `etat_sol=nu` est `NOT EXISTS (… COALESCE(taux_emprise_pct,0) ≥ 5)`. Or **177 899** parcelles (41 %) ont `taux_emprise_pct` **NULL** → `COALESCE(…,0)=0 < 5` → classées **nu**. La partition reste exacte et disjointe (nu 205 594 + bâti 226 069 = 431 663, **aucune exclusion silencieuse**), et le choix est **documenté** (`app.py:1046` « nu = pas d'emprise ≥ 5 % connue »). Vérification rassurante : 173 502 de ces NULL portent une `sdp_residuelle` calculée (cause NULL) → NULL = **aucun bâti détecté** (≈ 0 %), pas « non calculé » → le classement en « nu » est défendable. Reste que l'étiquette client « Terrain nu » ne dit pas qu'elle inclut « emprise bâtie non connue » ; la fiabilité (désaccord BD TOPO/CoSIA) vit dans le motif de fiche, pas au filtre. Étiquette à clarifier, pas un bug de données.

### 2.3 — `analyseLabuse` : commentaire d'interface contradictoire ⚠ (cosmétique)
`useApp.ts:65` déclare `analyseLabuse` « ON par défaut » ; `EMPTY_FILTERS` (`:98`) le pose **`false`** (« ÉTEINT par défaut », M55-D stage 4). Le défaut réel est **false** (tri factuel) — le commentaire ligne 65 est obsolète. Sans effet fonctionnel (le défaut appliqué est bien false), mais trompeur à la lecture.

### 2.4 — Zones exactes : pliage `upper()` PG vs Python ⚠ (faible, théorique)
Le filtre `zone_plu` compare `zone_filtre` via `upper()` côté Postgres (locale C) et un pliage Python côté chargement des options : un libellé accentué pourrait ne pas se replier identiquement (`NDé` vs `NDÉ`). En pratique les codes de zonage PLU réunionnais (UA, 1AU, Nh…) sont **sans accent** → risque quasi nul ici, mais la double normalisation reste un point de fragilité si un libellé accentué apparaissait.

### 2.5 — Combinaisons, exclusivité, reset (RAS)
- **Combinaisons** : `ET` entre groupes, `OU` dans le groupe Signaux. Intersections vérifiées propres (3 009 ; union tiers 1 607). Aucun filtre n'en écrase un autre, l'ordre est indifférent (clauses `conds` cumulées).
- **Zonage familles vs zones exactes** : **mutuellement exclusifs dans l'UI** (choisir une zone vide les familles). ⚠ mais l'endpoint accepte `zonage` ET `zone_plu` simultanément (deux `EXISTS`, en `ET`) : un deep-link forgé pourrait poser les deux et les intersecter — inaccessible depuis la barre latérale.
- **Reset** (`resetTout`) : `setFilters(EMPTY_FILTERS)` + verdict off + phase idle + snapshot/recap nuls → **remise à zéro complète, aucun état résiduel**. (Masqué pendant l'analyse figée : il faut « Changer les filtres » d'abord.)

### 2.6 — Interaction filtre × couche (croisement demandé)
Les filtres ne pilotent que la **couche Parcelles** (run servi, tuiles/GeoJSON). Les couches d'overlay auditées dans AUDIT-COUCHES / FIX-COUCHES (zonage, PPR, équipements, aléas, dispositifs…) sont **découplées des filtres** : elles affichent leur contexte **entier** quels que soient les filtres actifs. C'est un choix (contexte permanent), mais un utilisateur qui restreint les parcelles peut croire à tort que les équipements/zonages affichés sont eux aussi filtrés. Aucun couplage buggé détecté ; à signaler comme comportement (non couvert par les deux rapports précédents, qui n'auditaient pas cette intersection). Cas particulier cohérent : la couche `couleurs_verdict` peint **tout** le classement indépendamment des filtres (déjà noté côté couches) — à ne pas confondre avec le rendu filtré du mode analyse.

### 2.7 — Endpoint sur-ensemble : 43 paramètres non exposés en latéral (structurel)
Depuis la **barre latérale**, ~43 des 50 paramètres de `/filtre` ne sont **jamais envoyés** (ils le sont par le Copilote / deep-link / Surveillance). Ce n'est pas du code mort — sauf **`score_min`**, seul paramètre **globalement mort** : accepté pour compat URL, **aucune clause SQL** (matrice morte M129-B), plus envoyé par aucune surface. Les filtres reposant sur `score_e`/`v_parcel_dvf_last`/`dvf_secteur_medianes` (budget, charge, prix marché, marché fiable, mode B…) excluent en silence les parcelles sans ligne dans ces tables (`EXISTS`), mais **aucun de ces filtres n'est exposé en barre latérale** — l'observation vaut pour le Copilote, hors périmètre strict de cet audit.

---

## 3. Classement des problèmes par gravité

| Gravité | # | Problème | Impact |
|---------|---|----------|--------|
| **Faible** | F1 | « Terrain nu » inclut 177 899 emprises NULL (§2.2) | Étiquette ne dit pas « ou emprise inconnue » ; classement défendable (NULL = pas de bâti détecté), pas un faux positif. |
| **Faible** | F2 | Slivers <2 m² comptés mais non affichés (§2.1) | Compteur > visible de ~850 en île entière. |
| **Cosmétique** | F3 | Commentaire `analyseLabuse` « ON par défaut » ≠ défaut réel `false` (§2.3) | Trompeur à la lecture du code, sans effet. |
| **Faible** | F4 | `zonage` + `zone_plu` cumulables côté endpoint (§2.5) | Inaccessible depuis la barre latérale (UI exclusive) ; deep-link seul. |
| **Faible** | F5 | Double normalisation `upper()` PG/Python sur zones exactes (§2.4) | Théorique (codes PLU sans accent) ; fragile si libellé accentué. |
| **Info** | F6 | `score_min` mort ; endpoint sur-ensemble ; couches découplées des filtres (§2.6-2.7) | Structurel, par conception. |

Aucun filtre latéral **cassé**, aucune chip **morte**, aucun compteur **faussé**, aucun **plafond de slider** masquant des parcelles, aucun **état résiduel** après reset. Le path tiers (analyse LABUSE) est exact au bit près, et les combinaisons s'intersectent proprement.

---

## 4. Correctifs candidats à mandater (non faits)

1. **F1** — Clarifier l'étiquette/tooltip « Terrain nu » : préciser « aucune emprise bâtie ≥ 5 % connue » (ou surfacer un état « emprise inconnue » distinct), pour que 41 % de parcelles à emprise NULL ne se lisent pas comme « terrain vide confirmé ».
2. **F2** — Réconcilier compteur et affichage sur les slivers <2 m² : soit exclure les <2 m² du compte (comme de la liste/carte), soit l'annoncer (« N affichées, dont 850 slivers masqués »).
3. **F3** — Corriger le commentaire `useApp.ts:65` (`analyseLabuse` défaut = `false`, aligné sur `EMPTY_FILTERS`).
4. **F4** — Rendre `zonage` et `zone_plu` mutuellement exclusifs **côté endpoint** (refléter l'exclusivité UI) ou documenter l'intersection voulue.
5. **F5** — Unifier la normalisation des zones exactes (même casse/accents PG et Python) si des libellés accentués venaient à exister.
6. **F6** — Retirer `score_min` (paramètre mort M129-B) du contrat de `/filtre`, ou le documenter explicitement comme no-op de compat. (Hors barre latérale.)

---

## 5. Synthèse

**7 filtres latéraux**, tous branchés à une clause SQL réelle et vérifiés sur la base : communes, surface, zonage (familles + zones exactes), état du sol, signaux de vie, et l'interrupteur Analyse LABUSE. **Tuyauterie saine** — compteur exact (même WHERE, sans plafond, path tiers au bit près : 82/1 525/145 882), combinaisons en intersection propre, reset complet sans résidu, bornes de saisie sans plafond caché, chips alignées sur les valeurs réelles en base. **Cinq écarts faibles/cosmétiques** (étiquette « nu », slivers comptés, commentaire de défaut, exclusivité zonage côté endpoint, normalisation `upper()`) et un constat structurel (`/filtre` est un sur-ensemble partagé ; `score_min` seul paramètre globalement mort). Les couches d'overlay restent **découplées** des filtres — comportement à connaître, non couvert par les audits couches précédents. **N filtres, largement RAS** — les écarts sont de l'étiquetage et de la dette de contrat, pas des faux positifs servis.
