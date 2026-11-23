# OUTIL-SCAN-FIX-1 — Compte-rendu

> Worktree `~/Desktop/labuse-scan-fix`, branche `fix/outil-scan-1` (depuis `origin/main`, base `79153bb21`).
> Base locale `postgresql://openclaw@localhost:5432/labuse` (lecture seule pour l'instant). API 7540 / front 10340 (non démarrés au LOT 0).
> Périmètre = liste fermée du contre-audit `~/Desktop/audit-outils/04-SCAN-PATRIMOINE-ASTRA.md` (bloquants 1-6, à corriger 7-9, mineur 10).
> Point par point, tableaux avant/après, requêtes rejouables. Captures dans `~/Desktop/outil-scan-fix-1/`.

---

## LOT 0 — Plan (lecture seule) — rendu AVANT toute écriture de code

### 0.1 État « avant » mesuré en base (requêtes rejouables)

```sql
-- une seule ligne par parcelle : rows = idu distincts (PK sur idu)
SELECT count(*) rows, count(DISTINCT idu) idu, count(DISTINCT siren) siren,
       min(millesime), max(millesime) FROM parcelle_personne_morale;
-- → 82701 | 82701 | 12605 | 2025 | 2025

SELECT siren, count(*) FROM parcelle_personne_morale
WHERE siren IN ('452038805','310863592') GROUP BY siren;
-- CBO 452038805 → 1871   |   SIDR 310863592 → 4241

SELECT count(*) FROM parcelle_personne_morale pm JOIN parcels p ON p.idu=pm.idu
WHERE pm.siren='452038805';   -- rattachées cadastre → 1833
```

| Fait mesuré | Valeur |
|---|---|
| Lignes `parcelle_personne_morale` | **82 701** |
| idu distincts | **82 701** (= lignes → strictement **1 ligne / parcelle**, PK `idu`) |
| Millésime présent | **2025 seul** |
| SIREN distincts | 12 605 |
| CBO `452038805` / SIDR `310863592` | 1 871 / 4 241 (recensées) ; CBO rattachées cadastre = 1 833 |
| Répartition `groupe` | 0=33 921 · 1=5 804 · 2=90 · 3=3 960 · 4=24 536 · 5=7 681 · 6=4 128 · 7=359 · 8=9 · 9=2 213 |

**Mécanisme du bloquant 1 (code).** `src/labuse/ingestion/personnes_morales.py` :
- dé-doublonnage par parcelle à l'ingestion : `if idu in seen: continue` (l.62) → **la 1re ligne rencontrée gagne**, choix non déterministe (ordre du CSV) ;
- `INSERT … ON CONFLICT (idu) DO UPDATE` (l.88) → **une seule ligne par idu** garantie ;
- `_COL` (l.31) ne mappe **pas** le code droit (indices lus : siren=19, groupe=20, forme=22, denomination=23 ; **l'index 21 — le code du droit DGFiP — est sauté**). Le droit (propriétaire / gestionnaire / bailleur à construction / usufruitier / emphytéote / copropriétaire…) **n'est jamais chargé**.

→ C'est exactement ce que décrit l'ASTRA §1 : « LABUSE conserve la première ligne par parcelle et ne conserve pas le code droit », et « 5 322 parcelles du fichier 2025 ont plusieurs identifiants de personnes morales » (chiffre à re-mesurer sur le fichier **2026** au LOT 1).

### 0.2 Tous les lecteurs de `parcelle_personne_morale` (+ vue `v_foncier_sous_pression`, table sœur `pm_proprietaires_millesimes`)

Inventaire exhaustif issu de trois relectures croisées du back (aucun fichier modifié). La question posée à chaque requête : **si la table passait à plusieurs lignes par idu, cette requête multiplierait-elle / fausserait-elle un COUNT/SUM/une liste, ou casserait-elle un write ?**

**A. Lecteurs SÛRS tels quels (agrègent par `siren`, `DISTINCT idu`, `EXISTS`, `GROUP BY`, `LIMIT 1`, `max()/min()`)** — insensibles au nombre de titulaires :

| Écran / feature | Fichier:ligne | Clé | Pourquoi sûr |
|---|---|---|---|
| Scan — recherche nom | `modules.py:232` | GROUP BY siren | agrégat |
| Scan — Possession (SIREN) | `modules.py:327/346/352` | `WHERE siren=:s` | sélectionne une société, dédup idu indifférent |
| Construction — opérations | `veille_promoteurs.py:79` | DISTINCT ON(permis) | regroupé par siren ensuite |
| Construction — frise / acquisitions | `veille_promoteurs.py:218/290/292` | siren ; GROUP BY commune ; LIMIT 1 | agrégat |
| Communes — dashboard | `fiche_commune.py:567` | `count(DISTINCT idu)` | dédup idu |
| Communes — acquisitions / timeline | `proprietaire_historique.py:85/146` | `WHERE idu` / préfixe commune, UNION | filtre 1 parcelle |
| Recherche / suggestions | `recherche.py:277` | GROUP BY siren | agrégat |
| Accueil — compteurs | `accueil.py:100` | GROUP BY siren, `count(DISTINCT idu)≥3` | double dédup |
| Fiche parcelle — cluster / carte | `app.py:4108/4517`, `fiche_blocs3.py:158/185` | GROUP BY siren | agrégat |
| Filtres socle (type/denom/forme/siren/public…) | `app.py:1966/1995/2133/2135/2138/2145/2170/2176/2182` | `EXISTS` | booléen |
| Scoring V (lecture liste) | `score_v.py:82` | 1 ligne/idu ORDER BY idu | liste, pas de count |
| Acquérabilité | `lignee_tete.py:97` | `DISTINCT ON (idu)` | dédup idu |
| Blocs — identité société | `blocs.py:115`, `n_blocs.py` | GROUP BY siren, max() | agrégat |
| Zone — propriétaires | `zone.py:756` | GROUP BY siren + SUM | agrégat |
| Signaux de vie | `signaux_vie.py:78` | GROUP BY siren, `count(DISTINCT idu)` | dédup |
| Implantation / assiette | `assiette.py:255` | `count(DISTINCT siren)` | dédup |
| Ingestion BODACC / dépôts / RNE / score_v_fetch | `bodacc.py:84/122`, `deposants_actifs.py:46`, `inpi_rne.py:41/234`, `score_v_fetch.py:40/104` | `DISTINCT siren` / `count(DISTINCT idu)` | dédup |
| Courrier — dashboard | `courrier.py:369` | `count(DISTINCT denomination)` | dédup |

**B. Lecteurs/writes qui CASSERAIENT si on ajoutait des lignes à la table (join direct par `idu` sans dédup, write par idu, ou garde-fou)** — ce sont eux qui dictent l'architecture :

| Écran / feature | Fichier:ligne | Problème si ≥2 lignes/idu |
|---|---|---|
| **GARDE-FOU service** | `bascule_gardes.py:735` | `GROUP BY idu HAVING count(*)>1` → **refuse de servir le run** (bloquant dur) |
| Seed démo Saint-Paul (WRITE) | `demo_saint_paul.py:239` | `INSERT … (idu…)` suppose idu unique → conflit PK / écrasement |
| Fiche parcelle — propriétaire | `app.py:6769` (`_pm_bloc`), `enrichment.py:373`, `events.py:489` | `.first()` masque mais **perd** les autres titulaires ; choix arbitraire |
| Références propriétaires | `app.py:10132` (`_refs`) | dict `pm[idu]` = **dernier gagne** → perte de données silencieuse |
| Propriétaire public (CRM) | `app.py:10156` | `.first()` sans tri → arbitraire |
| Cascade — sondage BODACC | `cascade/context.py:305` | JOIN idu puis JOIN siren=bodacc → **multiplie** les sondages |
| Cascade — owner_pm | `cascade/context.py:615` | `LIMIT 1` → perd les titulaires minoritaires |
| Suivi parcelle — notif | `events.py:477` | JOIN idu + JOIN siren=bodacc → **notifs dupliquées** |
| Voisinage | `moteurs.py:374` | LEFT JOIN idu sans dédup → voisins **gonflés** |
| Scoring — dryrun | `dryrun.py:226` | LEFT JOIN idu → matrice de simulation **dédoublée** |
| Blocs — construction géom. | `blocs.py:71-82` | table temp par idu → **cardinalité de bloc gonflée** |
| Copilote — « possède N parcelles » | `copilote_v2/outils.py:327` | `count(*)` GROUP BY siren → **compte gonflé** si plusieurs droits/parcelle |
| Filtres socle avec JOIN bodacc/SIRENE | `app.py:1985/2159/2162/2188/2194/2216` | `EXISTS … JOIN siren` → matches incohérents |
| Projets — signaux | `projets.py:1130` | DISTINCT final OK mais JOIN intermédiaire scanné N× |

**Conclusion de l'inventaire.** Le schéma « 1 ligne = 1 parcelle » est une **invariante de tout le socle**, garantie par un garde-fou qui bloque le service. **Ajouter des lignes dans `parcelle_personne_morale` est exclu.**

### 0.3 Proposition de chargement DGFiP 2026 — garder **tous** les titulaires et **tous** leurs droits sans rien casser

Deux tables, séparation nette entre « vérité complète » et « compat lecteurs » :

1. **Nouvelle table complète des droits** `parcelle_pm_droit` (toutes les lignes du fichier, rien jeté) :
   `id` (surrogate PK) · `idu` · `siren` · `denomination` · `forme_juridique` · `groupe` · `groupe_label` · **`droit_code`** · **`droit_label`** · `ordre_titulaire` (rang du principal, calculé) · `millesime` · `source` · `url_source` · `date_import`. Index sur `idu` et sur `siren`. Unicité `(idu, siren, droit_code)`.
   → lue **uniquement** par le nouveau Scan (Possession : séparer propriété / gestion / autres droits, dans les comptes **et** la liste) et par la preuve de recontrôle CBO/SIDR. **Aucun lecteur existant n'y touche.**

2. **`parcelle_personne_morale` conservée telle quelle** (PK `idu`, 1 ligne/parcelle, même colonnes) = **le « titulaire principal »**, désormais **peuplée par dérivation déterministe** depuis `parcelle_pm_droit` (au lieu du « 1re ligne du CSV »). Ajout possible de 2 colonnes **nullable** `droit_code` / `droit_label` du principal (additif, aucun `SELECT *` concerné → sans risque). Le garde-fou `bascule_gardes.py:735` reste vert.

**Règle écrite et déterministe du « titulaire principal »** (propriétaire avant gestionnaire), appliquée par parcelle :
tri par **priorité de droit** croissante → `1 Propriétaire` · `2 Usufruitier` · `3 Nu-propriétaire` · `4 Bailleur à construction` · `5 Emphytéote` · `6 Fiduciaire` · `7 Copropriétaire` · `8 Gestionnaire / mandataire / gérant` · `9 autres/inconnu` ; **départage à droit égal** : `groupe` croissant puis **`siren` croissant** (numérique, les `U…` après) puis `idu`. Deux exécutions ⇒ **même principal** (tri total, aucun aléa). La correspondance exacte `droit_code → label → priorité` sera **lue sur le descriptif DGFiP et l'entête du fichier 2026** au LOT 1 (l'index de colonne du droit — vraisemblablement 21, aujourd'hui sauté — sera confirmé sur l'entête réel, pas deviné).

**Étapes de migration (ordre impératif, LOT 1) :**
1. **Archiver le 2025 courant** dans `pm_proprietaires_millesimes` (millesime=2025) **avant** d'écraser, sinon la timeline/acquisitions Communes (qui UNIONne millésimes historiques + table servie) perd le 2025. *(à vérifier : si 2025 déjà archivé là, no-op.)*
2. Charger le fichier **2026** dans `parcelle_pm_droit` (toutes lignes, tous droits).
3. Recalculer `parcelle_personne_morale` depuis `parcelle_pm_droit` via la règle du principal + poser `millesime=2026`.
4. Rejouer le garde-fou unicité + recompte CBO/SIDR **par droit** contre le fichier officiel (preuve bloquante).

### 0.4 Ce qui change pour chaque lecteur

| Lecteur / écran | Change-t-il ? | Détail |
|---|---|---|
| **Tous les lecteurs du groupe A+B** | **Forme : rien** | lisent toujours `parcelle_personne_morale`, 1 ligne/idu, mêmes colonnes, mêmes comptes. Aucune requête réécrite, aucun risque de multiplication. |
| **Fiche parcelle** (`app.py:6769/4103`, `enrichment.py`, `moteurs`, `served_cascade`, `fiche_blocs3`) | **Fond, borné** | le propriétaire affiché = désormais **le principal par la règle** (propriétaire-first) au lieu de la 1re ligne CSV arbitraire → **ne change que pour les parcelles multi-titulaires** ; là où une ligne « gestionnaire » était retenue, c'est maintenant le propriétaire. Option (non requise) : afficher « + N autres titulaires » depuis `parcelle_pm_droit`. |
| **Blocs fonciers** (`blocs.py`, `n_blocs.py`) | **Fond, borné** | regroupe par `siren` du principal ; une parcelle multi-titulaire peut changer de bloc (vers le propriétaire). Borné aux parcelles multi-titulaires ; à quantifier au LOT 1. |
| **Successions** (`n_successions_veille`, `modules.successions`) | **Forme : rien** | filtre par signal, lit le principal ; forme identique, principal plus correct. |
| **Communes** (`fiche_commune:567`, `proprietaire_historique` acquisitions) | **Forme : rien** *si* l'archivage 2025 (étape 1) est fait | `DISTINCT idu` sûr ; acquisitions compare millésimes → **dépend de l'archivage 2025**. Le passage 2025→2026 fera apparaître de **vrais** mouvements de titulaires (attendu, pas un bug). |
| **Classement / scoring** (`score_v:82`, `scenarios_v2_build`, `dryrun`, `lignee_tete`) | **Fond, borné** | 1 ligne/idu → forme inchangée ; pour les parcelles multi-titulaires le `groupe`/`siren` du principal peut changer (vers le propriétaire) et donc le type de propriétaire utilisé au score. Borné, à quantifier. |
| **Copilote** (`outils.py:327`) | **Forme : rien** (+ LOT 5) | `count(*) GROUP BY siren` reste juste (1 ligne/idu). Le champ valorisation sera retiré au LOT 5. |
| **Nouveau Scan Possession** | **Nouveau** | seul lecteur de `parcelle_pm_droit` : comptes et liste séparés propriété / gestion / autres droits ; en-tête = périmètre (ce SIREN seul, filiales non comprises) + millésime 2026 + surface réellement rattachée. |

**Effet net.** Une seule famille d'effets de fond, **bornée aux parcelles multi-titulaires** (≈ 5 322 au fichier 2025 selon l'ASTRA, à re-mesurer), et toujours **dans le sens « propriétaire plutôt que gestionnaire »** — une correction, pas une régression. Le volume exact de principaux qui changent sera chiffré au LOT 1 (avant/après) et versé en preuve.

### 0.5 Questions ouvertes (ne bloquent pas la suite, à confirmer)

1. Ordre de priorité des droits ci-dessus : OK, ou faut-il remonter l'usufruitier/emphytéote ? (défaut proposé : propriétaire d'abord, gestionnaire dernier.)
2. Faut-il afficher « + N autres titulaires » sur la fiche parcelle (enrichissement), ou garder la fiche strictement sur le principal ?
3. Nom de la table de droits : `parcelle_pm_droit` proposé.

---

---

## LOT 1 — Qui possède (bloquant 1, points 7 et 8)

### 1.0 Isolation (condition « laisse-les tranquilles »)
Base partagée `labuse` = 38 Go, interdite à l'écriture (confirmé par le classifieur). Travail isolé dans une base dédiée **`labuse_scanfix`** (`.env` du worktree → cette base). `parcelle_pm_droit` chargée EN ENTIER depuis le CSV officiel (aucune lecture de `labuse`) ; tranches CBO/SIDR copiées depuis `labuse` par lectures **indexées** (idu/siren), jamais de scan complet. `parcels` 6 083 · zone 6 077 · bâti 4 177 · millésimes 28 190 · blocs 670.

### 1.1 Fichier DGFiP 2026 chargé, tous titulaires et droits conservés
- Source officielle : `fichiers des parcelles dpts 61 à 976 (situation 2026).zip` (149 Mo), membre `PM_26_NB_974.csv` (18 Mo). Descriptif 2026 officiel : **24 colonnes**, **code droit = colonne 17** (« Code droit - par », ex. `P - Propriétaire`). *(Correction du LOT 0 qui supposait l'index 21 — c'est 17 ; 21 = forme juridique non-abrégée.)*
- Table complète `parcelle_pm_droit` : **89 793 lignes (parcelle,titulaire,droit) distinctes**, **84 045 parcelles**. Code module : `src/labuse/ingestion/pm_droits.py` (loader + règle principal + archive).
- Table des droits DGFiP (col. 17) rencontrés sur le 974 : P propriétaire, G/Q/**Z (« gestion d'un bien de l'État »)** gestion, B bailleur à construction, R preneur à construction, U/N usufruit/nue-propriété, E emphytéote, F/D/T foncier, S syndic, V/W bail réhab…

```sql
-- rejouable (base labuse_scanfix)
SELECT droit_code, count(DISTINCT idu) FROM parcelle_pm_droit WHERE siren='452038805' GROUP BY 1 ORDER BY 2 DESC;
SELECT droit_code, count(DISTINCT idu) FROM parcelle_pm_droit WHERE siren='310863592' GROUP BY 1 ORDER BY 2 DESC;
```

### 1.7 Preuve — recontrôle CBO et SIDR contre le fichier officiel 2026, PAR DROIT

| Société | Total idu 2026 | **Propriété (P)** | Gestion (G) | Bailleur constr. (B) | Preneur (R) | Emphyt. (E) | Syndic (S) | DB 2025 (avant) |
|---|---|---|---|---|---|---|---|---|
| **CBO** 452038805 | 1 946 | **1 904** | **13** | 29 | — | — | — | 1 871 |
| **SIDR** 310863592 | 4 140 | **4 114** | 8 | 4 | 12 | 1 | 1 | 4 241 |

→ **CBO « possède » 1 904 parcelles** (droit P), pas 1 871/1 946. Les **13 parcelles où CBO n'est que gestionnaire** (+ 29 bailleur à construction) ne sont plus comptées comme propriété — exactement le défaut relevé par le contre-audit (§1 : « gestionnaire ou mandataire sur 14 »).

### Conditions posées — PROUVÉES
**Condition 1 — archive 2025 avant écrasement + timeline garde 2025.** Avant : `pm_proprietaires_millesimes` = 2019-2024. Après `archive_2025_courant` : **2019-2025** (6 112 lignes 2025 copiées depuis la table servie). Puis `recompute_principal(2026)` → `parcelle_personne_morale` = 2026, **0 idu dupliqué** (invariante garde-fou intacte). Timeline d'une parcelle CBO (97415000BI0007) via le vrai code `proprietaire_historique.historique` : **8 millésimes 2019→2026, 2025 ET 2026 présents**.

**Condition 2 — nombre exact de parcelles dont le principal change (effet millésime vs effet règle), + impact classement.**

| Effet | Parcelles |
|---|---|
| Millésime 2026 — ajoutées | **2 909** |
| Millésime 2026 — retirées | **1 565** |
| Millésime 2026 — même idu, SIREN changé par le contenu | **1 282** |
| Règle de priorité seule (même fichier 2026, 1re-ligne → propriétaire-first) | **1 496** |
| Combiné (DB2025 → 2026+règle) — SIREN principal différent | **2 711** |
| Combiné — `groupe` différent (impact classement) | **3 989** |

**Le classement lit bien cette table** : via `score_v._load_owner_links` (`scoring/score_v.py:82`) qui lit **idu, siren, denomination, groupe, forme_juridique** → alimente le V-score (propension à vendre) → classement. Parcelles concernées : **2 711** changent de SIREN attribué (rattachement enrichissement/BODACC/propension), **3 989** changent de `groupe` (pondération type-propriétaire). Effets matérialisés seulement après le flip + recalcul V-score (différé).

### 1.5 Écran Possession — propriété / gestion / autres droits (code livré)
- Back `modules.py:patrimoine` : requête pilotée par `parcelle_pm_droit` (repli `parcelle_personne_morale` si table absente → **prod non migrée reste servie**). Nouveaux champs servis : `par_droit` {propriete, gestion, autres : recensees/rattachees/surface_rattachee_m2}, `surface_rattachee_m2`, `perimetre` {siren_seul, filiales_incluses:false}, et `droit_code`/`droit_label` par item (liste).
- Front `ModulePanel.tsx` : 3 tuiles **Propriété / Gestion-mandat / Autres droits** (recensées + surface rattachée), ligne **« Périmètre : ce SIREN seul — filiales non comprises »**, pied **« situation 2026 »**, et le droit affiché par parcelle dans la liste quand ≠ propriété simple.
- Capture `01-cbo-possession-par-droit.png` : CBO **Propriété 1 904 · Gestion 13 · Autres 29**, situation 2026, périmètre. `04-sidr-possession-par-droit.png` : SIDR **Propriété 4 114 · Gestion 9 · Autres 17**.

### 1.6 Recherche (point 8, code livré)
- Back `modules.py:patrimoine_search` : renvoie `{resultats, total, affiches, masques, plafond}` ; `n` = parcelles **recensées** (= scan, via `parcelle_pm_droit`), `siren_reel` par résultat. Consommateurs adaptés (`api.ts`, `ScanPatrimoine.tsx`, `Header.tsx`).
- Front : **« N autres résultats non affichés — précisez le nom »** (capture `02`, FONCIERE : 12 affichés / **34 masqués** / 46 total) ; un **U…** est dit **« identifiant fiscal, pas un SIREN »** (capture `03`) ; une **adresse à plusieurs parcelles propose le choix** (idu · commune) au lieu de prendre la première ; le compte de la recherche (CBO 1 946) = celui du scan.

### 1.8 Fiche parcelle — autres titulaires (écran seulement)
- Back `modules.py:/modules/parcelle/{idu}/titulaires` : endpoint **dédié à l'écran** (n'alimente aucun export PDF/Excel — `_pm_block` partagé non touché) renvoyant `{n_autres, titulaires:[{siren, denomination, droit_label, siren_reel}]}` depuis `parcelle_pm_droit` (titulaires hors principal). Testé (`test_pm_droits.py`).
- **Reste à câbler (front)** : la ligne discrète « + N autres titulaires (droits) » + bulle « i » dans le tiroir Identité (le composant Fiche appellera cet endpoint). Backend + test prêts ; le fil UI est le seul reliquat LOT 1.

### Tests (hook)
- Back `tests/test_pm_droits.py` (3 tests) : règle de priorité (P < G), familles, ventilation Possession (CBO P=2/G=1), autres titulaires fiche, recherche recensées+U…+masqués. `tests/test_patrimoine.py` adapté à la nouvelle forme de recherche. Front : `ScanPatrimoine.test.tsx` / `omnibox.test.tsx` adaptés ; **vitest 345/345, tsc -b vert**.

### Commandes prod (FOURNIES, NON EXÉCUTÉES)
```bash
# 1) Charger le fichier DGFiP 2026 (tous droits) dans parcelle_pm_droit (additif, sans risque lecteurs) :
labuse python -c "from labuse.ingestion import pm_droits as p; from labuse.db import get_session; \
  s=get_session(); p.ingest_droits(s, p.fetch_974_csv(), '2026')"
# 2) Archiver la situation 2025 SERVIE avant tout écrasement (timeline Communes garde 2025) :
labuse python -c "from labuse.ingestion import pm_droits as p; from labuse.db import get_session; \
  s=get_session(); p.archive_2025_courant(s)"
# 3) FLIP (fenêtre contrôlée, hors heures) — titulaire principal 2026 dans parcelle_personne_morale,
#    PUIS recalcul V-score/classement (2 711 SIREN / 3 989 groupes changent) :
labuse python -c "from labuse.ingestion import pm_droits as p; from labuse.db import get_session; \
  s=get_session(); p.recompute_principal(s, '2026')"
# (adapter l'accès session au runner prod ; vérifier ensuite le garde-fou unicité bascule_gardes.)
```

## Point 10 (mineur) — erreurs relevées dans l'audit Claude (NOTÉES, non corrigées dans le fichier d'audit)
Le contre-audit ASTRA les liste déjà ; je les consigne ici sans toucher `04-SCAN-PATRIMOINE.md` :
1. **Code droit = colonne 17**, pas 21 (l'audit Claude ne mentionnait pas la colonne ; le LOT 0 de ce compte-rendu avait supposé 21 — corrigé sur l'entête réel 2026).
2. Recherche : l'audit Claude parlait de « 12 résultats » servis sans dire le total — le vrai défaut est l'absence d'annonce des masqués (corrigé).
3. Route `/modules/blocs?siren=` : l'ASTRA note que le paramètre `siren` est ignoré (répond 6 357 blocs) — hors périmètre LOT 1, à vérifier.
4. Copropriétaires (groupe 7, 359 lignes) : l'audit Claude disait « copropriété absente » — inexact, elles sont présentes (désormais visibles comme titulaires dans `parcelle_pm_droit`).
5. Millésime Sitadel et chiffres de captures « historiques » (31/08 → 30/09) : relevés, hors LOT 1.

---

*État : LOT 0 ✅ · LOT 1 ✅ (données + Possession par droit + recherche + endpoint fiche + preuves + captures ; reliquat = fil UI fiche). LOTS 2-5 non commencés (checkpoint demandé par la structure du mandat). Base partagée `labuse` NON modifiée — tout en `labuse_scanfix`.*
