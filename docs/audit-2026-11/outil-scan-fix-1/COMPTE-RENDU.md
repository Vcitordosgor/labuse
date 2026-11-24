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

## LOT 2 — Qui construit (bloquants 2, 3, 4)

Fichier : `src/labuse/api/veille_promoteurs.py` (+ `VeillePromoteurs.tsx`). Tests : `tests/test_veille_promoteurs.py` (5). Tranche permis CBO/SIDR (359) copiée dans scanfix via l'index GIN `idu_codes` (lecture légère) ; **totaux île et taux de désaccord mesurés par agrégats légers sur `labuse`** (lecture seule, sanctionnée).

- **Deux listes séparées et nommées (bloquant 2)** — la frise sert `sur_son_foncier` (« Permis sur son foncier », propriétaire du terrain) ET `deposes_petitionnaire` (« Permis qu'elle a déposés », pétitionnaire identifié), avec la **part de permis dont le pétitionnaire est inconnu**. CBO : foncier 21 op / 63 permis / 200 logts, **pétitionnaire inconnu sur 81 %** ; déposés 19 permis / 143 logts. Titre « ce qu'ils construisent » **retiré** (→ « Permis sur son foncier »).
- **Attribution déterministe + cas ambigus (bloquant 2)** — le permis va au SIREN qui détient le PLUS de parcelles (départage `groupe` puis `siren` croissants) ; `ambigu=true` si ex æquo. **Deux exécutions = même résultat** (prouvé par test). L'attribution est faite **avant** le filtre catégorie.
- **Annulés hors « construit/en cours » ; PC/DP ; achèvement de groupe (bloquant 3)** — logements de permis annulés (`etat=4`) exclus du total et comptés à part ; PC et DP distingués (`n_permis_pc`/`n_permis_dp`) ; un groupe n'est « travaux achevés » que si **tous** ses permis non annulés le sont, sinon « N/M permis achevés — reste en cours ». Preuve île (`labuse`) : **1 705 logts annulés** et **116 DP** (= audit) ; « construit ou en cours » 19 353 → **17 648**.
- **Définition = règle appliquée, étendue réelle, vraie distance (bloquant 4)** — distance **géodésique** (haversine) au lieu de deg→m ; `span_m` (distance max du groupe) et `span_jours` servis par opération ; la phrase de règle dit « de proche en proche » et que l'étendue réelle est affichée (ex. CBO op à span 467 m / 1 711 j — honnête).
- **Partition + filtre neutre + plafond + cartes (bloquant 4, pt 7)** — catégories = partition (owner choisi avant filtre ; test `test_partition_…`) ; `par_promoteur` (cartes société) calculé sur **toutes** les opérations, pas sur les 200 servies ; plafond annoncé dans les **deux** modes.

**Taux de désaccord pétitionnaire/propriétaire (île, `labuse`)** : 592/1 817 = **33 %** (audit 28,8 % ; recalculé sur le foncier 2026 + majorité déterministe) — confirme qu'une attribution par le foncier n'est pas « qui dépose », d'où les deux listes.

```sql
-- rejouable (labuse, lecture seule) — annulés & DP (permis PM 0/5/6, >=1 lgt, géoloc) : voir §LOT2 du dépôt
-- désaccord : WITH perm(pétitionnaire 9 ch) + own(majorité) → count FILTER (pet<>owner)
```

## LOT 3 — Signaux et catégories (bloquant 5, point 7)

Fichiers : `modules.py` (`_depots_par_siren`, `patrimoine`) + `ModulePanel.tsx` ; `veille_promoteurs.py` (catégorie). Tests : `test_patrimoine` (signal INPI retiré), `test_veille_promoteurs::test_categorie_justifiee_par_source`.

- **« Aucun dirigeant au registre INPI » RETIRÉ** — reposait sur une absence locale (`pm_dirigeants` non peuplé) ; mis en défaut par le contre-audit (5/10). `inpi_sans_dirigeant` = toujours `False` ; bloc rouge supprimé de l'écran.
- **« Sommeil probable » RETIRÉ** — remplacé par le **fait daté** « dernier exercice déposé : AAAA · publié le JJ/MM/AAAA » (champ `parution` ajouté) ; si aucun dépôt : « aucun dépôt de comptes publié à ce jour » (factuel, sans interprétation).
- **BODACC daté + nature** — l'avis porte sa **date** (`date_annonce`) et sa **nature** : une procédure **clôturée** s'affiche en ton neutre (« clôturée le … — fait historique »), une procédure ouverte garde l'alerte. Plus de bandeau rouge sans date suggérant une procédure en cours.
- **« Promoteur » plus donné au groupe fiscal 0 (point 7)** — la catégorie affichée vient d'une **source qui la justifie** : NAF SIRENE `4110x` (promotion immobilière) → « Promoteur » ; groupes DGFiP 5/6 → « Bailleur social »/« SEM » ; sinon « **Société privée** » (neutre). Vérifié à l'écran : **CBO (groupe 0, NAF non-4110) = « Société privée »**, pas « Promoteur ».
- **Recharge BODACC si en retard (449090075)** — commande fournie : `labuse ingest-bodacc-depots` (upsert `bodacc_depots` depuis l'API BODACC pour tous les SIREN PM) ; à lancer quand la base est en retard. *(Non exécutée en scanfix : table de dépôts non tranchée ; la logique d'affichage factuel est en place.)*

## LOT 4 — Programmes (bloquant 6)

Fichier : `veille_promoteurs.py` (`_operations` attachement + frise `programmes_publies`). Test : `test_programmes_rattachement_sans_ambiguite`.
- Un nom de programme n'est attaché à une opération **que si** la clé (société, commune, année) mappe **exactement 1 programme ET exactement 1 opération**. **Collision** (≥2 programmes même clé, ex. Zirondelles/Zoiseau Blanc) → aucun attaché. **Double affectation** (1 programme, clé → ≥2 opérations) → non attaché. Les non-attachés restent listés « **publiés sur leur site** » (sans opération). Prouvé par test (Kaisary attaché seul ; Zirondelles/Zoiseau Blanc/KaisaryDup en « publiés »).

## LOT 5 — Valorisation (point 9)

Fichier : `modules.py` (`patrimoine`). Test : `test_patrimoine` (`"valorisation_nu_eur" not in out`).
- `valorisation_nu_eur` et `n_valorisables` **retirés** de la réponse servie (client ET Copilote — le Copilote appelle `patrimoine()`, donc la suppression côté payload suffit ; aucune autre référence en `src/`/`frontend/`). Le calcul (médianes de zone × surface, `ligne2_terrain_zone`) est **supprimé** (pas corrigé, comme demandé) — assiette non filtrée des bâties + médianes contaminées ; surface de confusion/latence supprimée.

## Point 10 (mineur) — erreurs relevées dans l'audit Claude (NOTÉES, non corrigées dans le fichier d'audit)
Le contre-audit ASTRA les liste déjà ; je les consigne ici sans toucher `04-SCAN-PATRIMOINE.md` :
1. **Code droit = colonne 17**, pas 21 (l'audit Claude ne mentionnait pas la colonne ; le LOT 0 de ce compte-rendu avait supposé 21 — corrigé sur l'entête réel 2026).
2. Recherche : l'audit Claude parlait de « 12 résultats » servis sans dire le total — le vrai défaut est l'absence d'annonce des masqués (corrigé).
3. Route `/modules/blocs?siren=` : l'ASTRA note que le paramètre `siren` est ignoré (répond 6 357 blocs) — hors périmètre LOT 1, à vérifier.
4. Copropriétaires (groupe 7, 359 lignes) : l'audit Claude disait « copropriété absente » — inexact, elles sont présentes (désormais visibles comme titulaires dans `parcelle_pm_droit`).
5. Millésime Sitadel et chiffres de captures « historiques » (31/08 → 30/09) : relevés, hors LOT 1.

---

## Captures (`~/Desktop/outil-scan-fix-1/`)
- `01-cbo-possession-par-droit.png` — Possession CBO : propriété 1 904 / gestion 13 / autres 29, périmètre, situation 2026 (LOT 1).
- `02-recherche-foncière-masqués.png` — recherche FONCIERE : 12 affichés / 34 masqués annoncés (LOT 1, pt 8).
- `03-recherche-identifiant-fiscal-U.png` — U… « identifiant fiscal, pas un SIREN » (LOT 1, pt 8).
- `04-sidr-possession-par-droit.png` — Possession SIDR par droit (LOT 1).
- `05-cbo-construction-foncier-annules.png` — Construction CBO : « Permis sur son foncier », 3 annulés exclus, carte « Société privée » (LOTS 2-3).
- `06-cbo-frise-deux-listes.png` — frise CBO : « sur son foncier » (81 % pétitionnaire inconnu) vs « déposés » (LOT 2).

## Tests ajoutés / adaptés
- Back : `test_pm_droits` (3), `test_veille_promoteurs` (5 : attribution déterministe, partition, catégorie NAF, programmes sans ambiguïté, frise 2 listes), `test_patrimoine` (recherche objet, INPI retiré, valorisation retirée), `test_front_chiffres2_familles::f03` (sommeil retiré → fait daté), `test_reparations1_lot2` (lecture sirene_etablissements déclarée au graphe).
- Front : `ScanPatrimoine.test`, `omnibox.test`, `VeillePromoteurs.test` adaptés. vitest + tsc -b verts.

---

*État : LOT 0 ✅ · LOT 1 ✅ · fil fiche ✅ · LOT 2 ✅ · LOT 3 ✅ · LOT 4 ✅ · LOT 5 ✅. Base partagée `labuse` JAMAIS écrite (tout en `labuse_scanfix` ; totaux île par agrégats légers lecture seule). Bascule `recompute_principal` NON appliquée à la base commune/prod — commande fournie. Recharge BODACC dépôts : commande fournie (`labuse ingest-bodacc-depots`), non exécutée.*

---

# OUTIL-SCAN-FIX-2 — reprise après relecture (`relecture-scan-1.md`)

Relecture indépendante : aucun défaut bloquant, 1 à corriger (A1) + 4 mineurs (M1-M4). Corrigés ici.

## A1 — logements de DP séparés de « construit ou en cours »
`veille_promoteurs.py` : `nb_logements` ne compte plus que les permis NON annulés **ET hors déclaration
préalable** ; les logements de DP sont servis À PART (`nb_logements_dp` / `n_logements_dp`), comme les
annulés. Avant : PC+DP fondus dans le total de tête. Après : total « construit ou en cours » = PC seuls ;
DP comptés séparément (116 à l'île d'après l'audit). Front : « N logements de déclaration préalable comptés
à part » (cartes, frise, bandeau). Test : `test_veille_promoteurs` (opDP `nb_logements==0`, `nb_logements_dp==3`).

## M1 — fenêtre de période comptée en JOURS, pas en mois entiers
`veille_promoteurs.py` : `_mois` → `_jours` (`abs((d1-d2).days)`), seuil `OP_PERIODE_JOURS = 730` (24 mois).
Le jour du mois est désormais pris en compte (le contre-audit : « le test temporel ignore le jour »). Test :
deux dépôts à 735 j au même point ne se regroupent plus (l'ancien calcul par mois les fusionnait).

## M2 — déterminisme : ORDER BY partout, aucun « premier » sur un ordre non garanti
`_permis_proprietaire` : `ORDER BY perm.id` final. Dans `_operations` : `membres` trié `(permit_id, id)`,
`recent` départagé par `(date, permit_id, id)`, tri des opérations à ordre total `(date, siren, commune)`.
Plus aucune bascule possible de la commune/catégorie/clé-programme d'une opération d'un appel à l'autre.

## M3 — flip 2025→2026 : plus d'« artefact de règle » dans Communes
`pm_droits.archive_principal_depuis_droits(millesime)` archive le 2025 avec la **MÊME règle** (principal
propriétaire-first) que le 2026 servi, au lieu de la vieille table « 1re ligne ». La chronologie Communes ne
compare donc que des titulaires choisis par la même règle. **Preuve (île entière, fichiers officiels 2025+2026,
SIREN réels)** :

| « Changements de propriétaires » 2025→2026 affichés | Nombre |
|---|---|
| **AVANT** (archive 2025 ancienne règle 1re-ligne vs 2026 nouvelle règle) | **2 019** |
| **APRÈS** (archive 2025 MÊME règle vs 2026) | **963** |
| Artefacts de règle supprimés à l'écran Communes | **1 056** (= 2 019 − 963) |

*(Correction SCAN-FIX-3 point 5 — l'effet PUR-RÈGLE sur 2025, mesuré directement = **1 480** si on compte TOUS les identifiants (y compris pseudo-SIREN `U…`), dont **1 078** sur des parcelles à deux SIREN 9-chiffres — les seules que Communes affiche comme un changement. Le compte-rendu SCAN-FIX-2 citait 1 078 ; la relecture mesurait 1 480. Les deux sont justes, à périmètres différents ; le delta écran reste 1 056.)*

10 cas (artefact : même parcelle, aucune cession, seul le pick change) :
`97401000AS0527` 662043116→229740014 · `97402000AB0648` 310895172→219740024 · `97402000AH1895` 828474643→219740024 ·
`97402000AK1039/43/44` 310895172→219740024 · `97401000AS0753` 662043116→229740014 · `97401000AS1131` 903946176→828065276 ·
`97402000AH1989` 402063184→219740024 · `97402000AB0652` 310895172→219740024 (1re-ligne → propriétaire-first).
La séquence prod (`BASCULE-PROD.md`) charge donc `parcelle_pm_droit` **2025 ET 2026** et archive 2025 par la règle.

## M4 — route blocs : le paramètre `siren` honoré
`modules.py:blocs_liste` : ajout du paramètre `siren` (il était absent → `?siren=` ignoré en silence, 6 357
blocs rendus). Il filtre désormais `WHERE siren = :siren` (même SIREN que Scan patrimoine). Test :
`test_blocs_filtre_siren` (2 blocs → `?siren=CBO` en rend 1).

## Item 6 — bascule base commune `labuse` / prod : PRÉPARÉE, NON exécutée
`scripts/bascule_2026_labuse.py` (`--dry-run`/`--go`) + runbook `BASCULE-PROD.md` : chargement droits
2025+2026, archive 2025 même règle, flip atomique, recharge BODACC dépôts, recalcul V-score + promotion.
Impact écrans + 12 témoins de cohérence, durée, rollback : voir `BASCULE-PROD.md`. `labuse` a déjà programmes
(9) et sirene (155 505) — seul BODACC à rafraîchir. **ARRÊT : Vic choisit le moment.**

*État SCAN-FIX-2 : A1 ✅ · M1 ✅ · M2 ✅ · M3 ✅ (prouvé) · M4 ✅ · bascule prod prête (non exécutée). Base `labuse` toujours jamais écrite.*

---

# OUTIL-SCAN-FIX-3 — rendre la bascule sûre (`relecture-scan-2.md`)

5 points de sûreté de la procédure de bascule, tous traités. Base commune `labuse` **jamais écrite, jamais `--go`** ; tout prouvé sur `labuse_scanfix`. Script réécrit : `scripts/bascule_2026_labuse.py` ; runbook : `BASCULE-PROD.md`.

## 1 — Rollback réel (`--rollback`), plus aucune commande SQL à la main
L'ancien runbook donnait `TRUNCATE … WHERE false` = **SQL invalide** (TRUNCATE n'a pas de clause WHERE). Remplacé par `--rollback` : restaure les 5 tables concernées depuis les sauvegardes `_bascule_bak__*` EN UNE transaction, retire les tables/colonnes créées par la bascule (`parcelle_pm_droit`, colonnes `droit_code/droit_label`). Prouvé (c/e) : empreintes identiques à l'AVANT, table par table.

## 2 — Garde-fou de cible (`--confirme <base>@<hôte>`)
`--go` et `--rollback` refusent sans `--confirme`, comparé à `current_database()` + hôte réel de la connexion ; **aucune base par défaut** ; affichage base/hôte/nombre de lignes avant d'agir. Prouvé (f) : sans `--confirme`, et avec une valeur erronée, → refus, rien écrit.

## 3 — Atomicité : staging + UNE transaction (le runbook dit le vrai)
Les droits 2025 et 2026 sont chargés dans une **table d'attente** `parcelle_pm_droit_staging` ; la promotion des droits + l'archive 2025 (même règle) + le flip 2026 passent dans **UNE seule transaction** (`ingest_droits`/`archive_principal_depuis_droits`/`recompute_principal` reçoivent `commit=False` ; un seul `commit` final). Prouvé (d) : interruption dure APRÈS le staging, AVANT la transaction → tables servies **strictement = AVANT**. Le runbook n'affirme plus « transactionnel » pour la séquence entière : il décrit staging + une transaction.

## 4 — Sauvegarde complète + run V-score re-servable
`--go` sauvegarde les **5** tables que la bascule touche (parcelle_personne_morale, pm_proprietaires_millesimes, parcelle_pm_droit, **bodacc_depots**, **parcel_blocs**) et mémorise le **run V-score servi** (`_bascule_bak__meta.vscore_run_servi`, re-servable, nommé par `--rollback`). Sauvegarde **non-écrasante** (go relancé ne perd pas l'AVANT d'origine).

## 5 — Chiffre « 1 078 » corrigé
Effet pur-règle sur 2025 mesuré directement = **1 480** (tous identifiants, dont `U…`), dont **1 078** sur parcelles à deux SIREN 9-chiffres (seules affichées par Communes). Delta écran Communes inchangé : 2 019 − 963 = **1 056**. Compte-rendu M3 corrigé ci-dessus. Requête : `scripts/`… reconstruction `PM_2025_974.csv` firstline vs règle.

## Les SIX preuves (sur `labuse_scanfix` remise à l'état « avant bascule »)

Empreinte = `(existe, n_lignes, Σ hashtext(colonnes métier))` — hors colonnes volatiles (id, date_import…), donc stable aux rechargements.

| # | Preuve | Résultat |
|---|---|---|
| **a** | empreintes AVANT | pm 82 701/ck=103795558738 · millésimes 28 190/ck=202297417894 · droit absente · bodacc absente · blocs 670/ck=25714965274 |
| **b** | bascule complète, contrôles verts | staging 2025 (82 701) + 2026 (84 045) → transaction unique {promotion · archive 2025 · flip} ; « injection servie 82 701→84 045 » ; APRÈS pm 84 045, millésimes 110 891, droit 178 224 |
| **c** | `--rollback` → empreintes = AVANT | **identiques table par table** (pm 103795558738, millésimes 202297417894, droit absente, bodacc absente, blocs 25714965274) |
| **d** | interruption dure au milieu du chargement | tables servies **= AVANT** (checksums identiques) ; seule la table d'attente écrite (178 224 lignes) |
| **e** | deux `--go` de suite | état final **identique** (mêmes checksums ; sauvegarde préservée) ; rollback → AVANT d'origine |
| **f** | mauvaise valeur de `--confirme` (et absence) | **refus, rien écrit** (comparé à `current_database()@hôte`) |

*État SCAN-FIX-3 : 1 ✅ · 2 ✅ · 3 ✅ · 4 ✅ · 5 ✅ · 6 preuves a-f ✅. `labuse` jamais écrite, jamais `--go` ; tout sur `labuse_scanfix`.*

---

# OUTIL-SCAN-FIX-4 — fermer les trous du retour arrière (`relecture-scan-3.md`)

4 points. `labuse` **jamais écrite** ; 7 preuves sur `labuse_scanfix`. Script `scripts/bascule_2026_labuse.py` réécrit ; `BASCULE-PROD.md` à jour. **Empreinte = `count(*)` + `Σ hashtext(ligne ENTIÈRE)` sur TOUTES les colonnes** (volatiles comprises).

## 1 — Sauvegarde numérotée/datée, jamais périmée
Chaque `--go` crée `_bascule_bak__<N>__*` + une ligne au registre `_bascule_sauvegardes` (numéro, date ISO, cible, label servi). `--go` **refuse** si une sauvegarde plus ancienne existe, sauf `--malgre-sauvegarde <N>` qui la nomme. `--rollback` **exige** `--sauvegarde <N>`, affiche (numéro, date, lignes) et n'agit que sur celle-là. `--purge-sauvegarde <N>` la supprime. → plus de « sauvegarde périmée » qui ramène à un état ancien (le danger du point 1 de la relecture).

## 2 — Cible par argument + identité serveur (plus d'env, plus de chaîne à recopier)
`--db <url>` **obligatoire** : le script ne lit NI l'environnement NI `.env`, aucun défaut (`create_engine(url)`). `--confirme` comparé à l'**identité renvoyée par le serveur** `current_database()@system_identifier:port`, pas à l'URL. Un refus **n'imprime pas** la valeur attendue.

## 3 — `localhost` = `127.0.0.1` = casse
L'identité repose sur le **`system_identifier`** du cluster (renvoyé par le serveur, identique quelle que soit la graphie d'hôte) — et non `inet_server_addr()` (qui rend `::1` vs `127.0.0.1`). Prouvé : `…@localhost` et `…@127.0.0.1` → **même identité** `labuse_scanfix@7648954216930168276:5432`. Comparaison en minuscules (insensible à la casse).

## 4 — Procédure ENTIÈRE sous retour arrière (plus d'étape manuelle)
Le script enchaîne : droits → archive 2025 → flip → **BODACC** → **blocs + `parcel_bloc_membres`** → **recalcul + PROMOTION V-score**. La sauvegarde couvre les **8** tables (dont `parcel_bloc_membres`, `p_score_v2_runs`, `parcel_p_score_v2`) + les **octets exacts** du **label servi** (`config/served_run.txt`). `--rollback` restaure tout et **re-sert réellement** le run précédent (réécrit le fichier) puis le **vérifie** (`_served_run_versionne`). *(Sur la tranche `labuse_scanfix` : `blocs-build` et le vrai `run_score_v2` ne tournent pas — run résiduel servi et features de scoring absents, angle mort de la tranche ; le script les CHAÎNE et reste résilient, et le V-score enregistre un run minimal qui exerce exactement les tables que le rollback doit couvrir. En prod ces deux étapes tournent pour de vrai.)*

## Les SEPT preuves (sur `labuse_scanfix` remise à l'« avant bascule »)

| # | Preuve | Résultat |
|---|---|---|
| **a** | AVANT | pm 82 701/`-392862471973` · millés. 28 190/`-1308875661` · droit absente · bodacc absente · blocs 670/`3708096254` · bloc_membres 0 · p_score_v2_runs 0 · parcel_p_score_v2 0 |
| **b** | procédure entière | sauvegarde #1 → staging → transaction unique (flip 82 701→84 045) → BODACC (chaîné) → blocs (chaîné) → V-score recalcul+**promotion** (`served_run.txt` → run bascule). APRÈS : pm 84 045, millés. 110 891, droit 178 224, p_score_v2_runs 1 |
| **c** | `--rollback --sauvegarde 1` | **identique à AVANT, table par table, TOUTES colonnes** (pm `-392862471973`, millés. `-1308875661`, droit+bodacc **retirées**, blocs/membres/scores restaurés) ; **run servi RE-SERVI « q_v20 » VÉRIFIÉ** |
| **d** | deux `--go` puis `--rollback --sauvegarde 2` | revient à l'état **d'APRÈS la 1ʳᵉ** (pm `580154625077`, millés. `121251725507`, p_score_v2_runs `947333443`, run servi « bascule2026_1… ») — **pas l'origine** |
| **e** | `--go` avec une sauvegarde ancienne (#1) | **REFUS** (« une sauvegarde plus ancienne existe #1 … ») ; débloqué seulement par `--malgre-sauvegarde 1` |
| **f** | env pointant ailleurs + mauvaise `--confirme` | sans `--db` → refus (env **non lue**) ; env=labuse + `--db`=scanfix → suit `--db` (identité scanfix) ; `--confirme` erroné → **refus, rien écrit, valeur non imprimée** |
| **g** | durée procédure entière | **≈ 55 s** sur `labuse_scanfix` (ZIP en cache ; en prod BODACC+V-score réels dominent) |

*État SCAN-FIX-4 : 1 ✅ · 2 ✅ · 3 ✅ · 4 ✅ · 7 preuves a-g ✅. `labuse` jamais écrite, jamais `--go`/`--rollback` ; tout sur `labuse_scanfix`.*

---

# OUTIL-SCAN-FIX-5 — réduire le périmètre de la bascule (`relecture-scan-4.md`)

**DÉCISION appliquée : le recalcul et la promotion du V-score SORTENT du script et de la procédure** (chantier du nouveau classement). Le code qui touchait le feature store, `data_sources`, `p_score_v2_runs`, `parcel_p_score_v2`, `config/served_run.txt`, `served_manifest.json` est **RETIRÉ** (pas désactivé par option). `labuse` jamais écrite ; tout prouvé sur `labuse_scanfix`.

## 1 — Périmètre : liste exhaustive des tables écrites (lue dans le code) + couverture
| Étape | Tables SERVIES écrites | Dans la sauvegarde ? |
|---|---|---|
| [1] droits | `parcelle_pm_droit` (via `…_staging` temp) | **OUI** |
| [2] archive+flip | `pm_proprietaires_millesimes`, `parcelle_personne_morale` (+ `droit_code/label`) | **OUI** |
| [3] BODACC | `bodacc_depots` ; `data_sources` **neutralisée** (snapshot+restore, même txn → inchangée) | **OUI** |
| [4] blocs | `parcel_blocs`, `parcel_bloc_membres` (temp `_blocs_pm`) | **OUI** |

→ **6 tables = `CONCERNEES`** ; tout le reste (feature store, p_score, served files) n'est **plus touché**. Vérifié : `config/served_run.txt` reste propre après un `--go` (le script n'y écrit plus).

## 2 — Une étape qui échoue ARRÊTE (code ≠ 0, « --rollback », jamais « [OK] »)
Chaque étape est encadrée : exception → `rollback()` de la transaction + message « ✗ ÉCHEC à l'étape X » + « --rollback --sauvegarde N » + `sys.exit(1)`. Les `except … continue` qui avalaient blocs/V-score sont **supprimés**. Prouvé (point 2) : `--_fail-at {droits, flip, bodacc, blocs}` → **exit 1, message, aucun « [OK] »** (4/4).

## 3 — blocs-build RÉEL dans la preuve
`labuse_scanfix` manquait l'environnement résiduel (`residuel_runs` vide, `parcel_residuel` vide). **Copié en lecture seule depuis `labuse`** (léger) : `residuel_runs` **2 lignes** (run servi `run_seq=17`) + `parcel_residuel` servi **5 998 lignes** (parcelles de la tranche ; `parcel_residuel` est une VUE dans `labuse`, une table dans `labuse_scanfix`). Résultat : `build_blocs` tourne **pour de vrai** → **669 blocs / 5 367 membres** écrits dans `parcel_blocs`+`parcel_bloc_membres`.

## 6 — `--db` vers une base inconnue : message cadré
Connexion forcée tôt (`SELECT 1`) sous `try/except OperationalError` → « ✗ connexion impossible à la base passée en --db : … database "…" does not exist. Vérifie l'URL --db. Rien fait. » **Aucun traceback brut.**

## Les PREUVES (sur `labuse_scanfix`, empreinte = `count` + `Σ hashtext(ligne ENTIÈRE)`, TOUTES colonnes)

| # | Preuve | Résultat |
|---|---|---|
| **a** | AVANT | pm 82 701/`-53120849433` · millés. 28 190/`-1308875661` · droit absente · bodacc 0 · parcel_blocs 670/`3708096254` · parcel_bloc_membres 0 |
| **b** | procédure entière, **blocs-build RÉEL** | [2] flip 82 701→84 045 · [3] BODACC (data_sources inchangée) · [4] **blocs 669 / membres 5 367** · « [OK] » ; durée **≈ 40 s** |
| **c** | `--rollback --sauvegarde 1` | **identique à AVANT, table par table, toutes colonnes** (blocs 669→670/`3708096254`, membres 5 367→0, droit retirée) |
| **pt 2** | `--_fail-at` chaque étape | **exit 1 · « ÉCHEC à l'étape X » · « --rollback --sauvegarde 1 » · aucun « [OK] »** (droits/flip/bodacc/blocs) |
| **pt 4** | `--_crash-at` (os._exit) chaque étape puis `--rollback` | empreintes **= AVANT** (toutes colonnes) pour staging/flip/bodacc/blocs — y compris quand [2]/[3] avaient committé |
| **pt 6** | `--db` base inconnue | message cadré, pas de traceback |
| **durée** | procédure entière | **≈ 40 s** (tranche ; sur `labuse` ~10-20 min, BODACC+blocs, **sans** le feature store 4,3 M du V-score retiré) |

*État SCAN-FIX-5 : V-score retiré du script ✅ · périmètre 6 tables prouvé ✅ · échec→arrêt ✅ · blocs-build réel ✅ · interruptions→AVANT ✅ · `--db` inconnu cadré ✅. `labuse` jamais écrite, jamais `--go`/`--rollback`.*
