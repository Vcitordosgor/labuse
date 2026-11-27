# OUTIL-PLU-FIX-10 — compte-rendu

Branche `fix/outil-plu-1`. Périmètre : la liste « C'est faux » de `~/Desktop/audit-outils/01-PLU-ASTRA-3.md`
(8 points). Toute règle est vérifiée au PDF officiel (`~/Desktop/labuse/data/plu_reglements`), article + page.

## Le critère qui change

Avant, la couverture se mesurait par « chaque zone donne au moins un résultat ». C'est ce critère qui a
produit les erreurs : des zones renvoyées **en bloc** vers le règlement d'une autre alors qu'elles ont leur
propre article (la hauteur d'AUt aux Trois-Bassins servie depuis Ub). **Nouveau critère, le seul retenu :**
pour une zone **et un article**, l'outil sert l'article **propre** à la zone s'il existe dans le PDF ; il ne
sert celui d'une autre zone que si le texte de la zone y renvoie **expressément** pour **cet** article, et il
le dit. L'ancien test « 701 sur 701 » (`test_couverture_plan_zonage_liste_nominative`) est **retiré**.

## Chiffres (script commité, sortie brute)

`PYTHONPATH=src python scripts/plu_fix10_chiffres.py` — corpus réingéré : **3226 extraits · 21 communes**.
Scripts de preuve : `plu_fix10_table_renvois.py` (LOT 1), `plu_fix10_scan_tronques.py` (LOT 2),
`plu_fix10_chiffres.py` (synthèse).

## LOT 0 — filet des témoins (commit séparé, rouge avant correction)

`tests/test_plu_fix10_lot0.py` — un test par témoin, chacun affirmant article + page + chiffre lus au PDF.
8 rouges au départ (points 1-6), 3 déjà verts (dates/badges backend, FIX-7) gardés comme garde-fous. Le test
« au moins un résultat » est retiré de `test_plu_cas_valides.py`.

## LOT 1 — renvois article par article (points 1-2)

Quatre communes (Bras-Panon, Saint-Louis, Trois-Bassins, Cilaos) ont un chapitre **générique** « ZONE AU
indicée » : un seul chapitre tient les articles de toutes les zones AU indicées, chaque article donnant la
règle **propre** d'une zone **ou** un renvoi **exprès**. Sans étiquette, ces articles tombaient en zone NULL
et le filtre AUt servait à tort la hauteur d'Ub. On les étiquette `AUINDICEE` à l'ingestion ; une zone AU
indicée sectorielle sans chapitre propre sert **ce** chapitre comme articles propres — plus de rabat en bloc
vers la zone U. Le renvoi, quand il existe, est **dans le texte** de l'article servi.

- **Trois-Bassins AUt · hauteur** → AUindicée 10, **p.69** (8 m/10 m) — PROPRE, plus jamais Ub p.32.
- **Bras-Panon AUec · hauteur** → AUindicée 10, **p.80** (18 m) — PROPRE, plus jamais UE p.71.

### Table complète des renvois (article × zone)

« PROPRE » = l'article porte une règle chiffrée pour la zone ; « renvoi→X » = renvoi exprès cité dans le
texte ; « générique » = « se reporter au règlement de la zone U indiquée en indice ». Toutes servies via le
chapitre propre `AUINDICEE` (colonne Servi).

| INSEE | Commune | Zone | Art. | Objet | Page (chapitre AU indicée) | Règle propre / renvoi | Servi |
|---|---|---|---|---|---|---|---|
| 97402 | Bras-Panon | AUA | 6 | implantation/voies | p.79 | générique | AUINDICEE |
| 97402 | Bras-Panon | AUA | 7 | implantation/limites | p.79 | générique | AUINDICEE |
| 97402 | Bras-Panon | AUA | 9 | emprise | p.79-80 | renvoi→U | AUINDICEE |
| 97402 | Bras-Panon | AUA | 10 | hauteur | p.80 | renvoi→U | AUINDICEE |
| 97402 | Bras-Panon | AUA | 12 | stationnement | p.80 | générique | AUINDICEE |
| 97402 | Bras-Panon | AUA | 13 | espaces libres | p.80 | générique | AUINDICEE |
| 97402 | Bras-Panon | AUEC | 6 | implantation/voies | p.79 | générique | AUINDICEE |
| 97402 | Bras-Panon | AUEC | 7 | implantation/limites | p.79 | générique | AUINDICEE |
| 97402 | Bras-Panon | AUEC | 9 | emprise | p.79-80 | renvoi→Ua | AUINDICEE |
| 97402 | Bras-Panon | AUEC | 10 | hauteur | p.80 | PROPRE | AUINDICEE |
| 97402 | Bras-Panon | AUEC | 12 | stationnement | p.80 | générique | AUINDICEE |
| 97402 | Bras-Panon | AUEC | 13 | espaces libres | p.80 | générique | AUINDICEE |
| 97402 | Bras-Panon | AUT | 6 | implantation/voies | p.79 | générique | AUINDICEE |
| 97402 | Bras-Panon | AUT | 7 | implantation/limites | p.79 | générique | AUINDICEE |
| 97402 | Bras-Panon | AUT | 9 | emprise | p.79-80 | renvoi→Ua | AUINDICEE |
| 97402 | Bras-Panon | AUT | 10 | hauteur | p.80 | renvoi→Ua | AUINDICEE |
| 97402 | Bras-Panon | AUT | 12 | stationnement | p.80 | générique | AUINDICEE |
| 97402 | Bras-Panon | AUT | 13 | espaces libres | p.80 | générique | AUINDICEE |
| 97414 | Saint-Louis | 1AUE | 6 | implantation/voies | p.109 | générique | AUINDICEE |
| 97414 | Saint-Louis | 1AUE | 7 | implantation/limites | p.109 | générique | AUINDICEE |
| 97414 | Saint-Louis | 1AUE | 9 | emprise | p.109-110 | renvoi→U | AUINDICEE |
| 97414 | Saint-Louis | 1AUE | 10 | hauteur | p.110 | renvoi→U | AUINDICEE |
| 97414 | Saint-Louis | 1AUE | 12 | stationnement | p.110 | générique | AUINDICEE |
| 97414 | Saint-Louis | 1AUE | 13 | espaces libres | p.111 | générique | AUINDICEE |
| 97423 | Les Trois-Bassins | AUA | 6 | implantation/voies | p.67 | générique | AUINDICEE |
| 97423 | Les Trois-Bassins | AUA | 7 | implantation/limites | p.67 | générique | AUINDICEE |
| 97423 | Les Trois-Bassins | AUA | 9 | emprise | p.68-69 | renvoi→Ub | AUINDICEE |
| 97423 | Les Trois-Bassins | AUA | 10 | hauteur | p.69 | renvoi→Uaa | AUINDICEE |
| 97423 | Les Trois-Bassins | AUA | 12 | stationnement | p.69 | générique | AUINDICEE |
| 97423 | Les Trois-Bassins | AUA | 13 | espaces libres | p.70 | générique | AUINDICEE |
| 97423 | Les Trois-Bassins | AUT | 6 | implantation/voies | p.67 | générique | AUINDICEE |
| 97423 | Les Trois-Bassins | AUT | 7 | implantation/limites | p.67 | générique | AUINDICEE |
| 97423 | Les Trois-Bassins | AUT | 9 | emprise | p.68-69 | renvoi→Ub | AUINDICEE |
| 97423 | Les Trois-Bassins | AUT | 10 | hauteur | p.69 | PROPRE | AUINDICEE |
| 97423 | Les Trois-Bassins | AUT | 12 | stationnement | p.69 | générique | AUINDICEE |
| 97423 | Les Trois-Bassins | AUT | 13 | espaces libres | p.70 | générique | AUINDICEE |

## LOT 2 — articles coupés (point 3)

À Sainte-Marie, « Article U8 - Hauteur » était coupé juste après « …limitée à : • » : le libellé de valeur
« • Zone UA : » était pris pour un **titre de chapitre** et détachait les 15/18/16 m (p.22). Garde-fou
`_looks_list_item` : un « ZONE X » précédé d'une **puce nue** est un élément de liste, pas un titre. Les deux
U8 sont désormais entiers (UA/UB/UC/UD p.22 : 2324 car. ; UEa/…/UT p.35 : 1372 car.).

Critère par zone × article — **articles concurrents** (`_filtre_scope`) : le règlement mutualisé tient deux
« Article U8 » pour des groupes de secteurs disjoints ; sous le filtre UA on ne sert que celui qui régit UA.
On écarte un article énumérant des secteurs **sans** la zone filtrée **uniquement** s'il existe un autre
article du même numéro qui, lui, la régit (sinon on garde : exception interne, renvoi AU3c→U3, article
unique). Appliqué identiquement à `search_reglement` **et** `count_reglement` (compte cohérent). Fixe aussi
**Saint-Paul U2e** (point 4 : l'article 13 propre p.99-100 passe avant celui des pages 83-87).

`scripts/plu_fix10_scan_tronques.py` scanne les 21 communes (fin en « : », puce, mot suspendu, césure) :
Sainte-Marie corrigé. Restent des deux-points de **préambule** (légitimes : « …organisées en N chapitres : »)
et des artefacts d'extraction de PDF à **lettres espacées** (La Plaine « ART ICLE U a », Saint-Joseph), hors
témoins de l'audit — listés, non corrigés (une normalisation large du lettre-espacement serait déstabilisante).

## LOT 3 — Saint-Paul : secteurs, articles, livrets (points 4-5)

- **Secteur d'abord** (point 4) : réglé par le filtre « articles concurrents » du LOT 2.
- **Articles 10 et 11 de Usdu séparés** (point 5) : le PDF colle l'en-tête à la phrase précédente
  (« …maximum Article 11- »), l'ancre de `_HEADER` le ratait → l'article 11 était fondu dans le 10. On
  accepte un en-tête collé à un mot pour la forme numérotée stricte « Article N- » (jamais un « article N »
  de prose, exclu par la casse ; renvois écartés par `_looks_cross_ref`).
- **Livrets accessibles** (point 5) : Saint-Paul réédite les articles d'une zone par bassin de vie. On capte
  le livret dans le fil d'en-tête (`_livret_par_page`), on le **stocke** (colonne `livret`) et on l'intègre à
  la clé de dédoublonnage. Les Usdu « Article 12 » sont désormais tous servis avec leur livret et leur page :
  **p.139** (Plateau Caillou), **p.200** (La Plaine–Bois de Nèfles), **p.246** (La Saline), **p.306**
  (Guillaume). L'endpoint joint la liste `livrets` {livret, page} ; le front affiche le bassin + « Aussi dans : ».

## LOT 4 — barèmes de stationnement sur la fiche (point 6)

La fiche servait la valeur de base mais perdait les **conditions** du tableau et, en barème par m² de SDP,
l'article et la page. On enrichit la ligne depuis le **même** `BaremeStationnement` que l'Étude applique :

- **Saint-Louis 97414000DK0208 (UA)** : 2 places/logt + condition « 0,5 place/logt au-delà de 10 logements,
  publique », article **UA 12.2**, lien **p.23**.
- **Saint-Pierre 97416000HT0538 (Ud)** : 1 place/75 m² + conditions (lotissement individuel, aménagement
  Ud5.1), article **Ud6** (était sans référence), lien profond **p.93**.

Front : les conditions s'affichent dans l'infobulle de la tuile Stationnement, avec l'article.

## LOT 5 — dates & avertissements (points 7-8)

Le backend sert déjà les dates distinctes (approbation écrite ≠ lot) ; corrections d'écran :

- Écran d'entrée : « Le verbatim **opposable** » → « Le texte du règlement **publié au Géoportail, lot du
  <date>** » (on ne promet plus l'opposabilité du jour).
- « approuvé le » : une couverture **sans quantième** (Saint-Denis « février 2024 », Saint-Pierre « juin
  2024 ») est rendue « approuvée en <mois> <année> (jour non précisé en couverture) » — jamais un jour
  fabriqué ; une modification ultérieure reste « modifié le ».
- **Badges de procédure** : le badge de la liste reflète la même information que le détail (procédure connue
  OU évolution postérieure) — Saint-Benoît, La Possession, Saint-Pierre, Le Tampon ne sont plus sans badge.
- **Beauvallon** (Saint-Benoît) : l'évolution 30/06/2026 (AUp→AUe, absente du lot GPU 2020) reste signalée en
  bandeau « ⚠ modification … » au-dessus des résultats.

## Tests

- `tests/test_plu_fix10_lot0.py` (témoins, famille `reel`) : **12/12 verts** après correction.
- `tests/test_plu_cas_valides.py` (filet FIX-8/9 révisé) : vert. Deux tests « 0 doublon » révisés (clé
  = zone + **livret** : les rééditions par bassin sont la structure réelle du document). Test de renvoi AU
  révisé (ancien critère « renvoi en bloc » retiré). Test « 701 sur 701 » retiré.
- Front : `tsc` vert, 109 tests vitest verts.
- Réingestion des 21 communes via `scripts/reingest_plu_outil_plu_fix_1.py`.

Commits locaux, pas de fusion dans `main`.
