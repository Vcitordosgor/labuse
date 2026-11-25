# OUTIL-PLU-FIX-11 — compte-rendu

Branche `fix/outil-plu-1`. Périmètre : la liste fermée (3 points) de `~/Desktop/relecture-plu-8.md`.
`origin/main` fusionné dans la branche avant correction. Toute règle vérifiée au PDF officiel
(`~/Desktop/labuse/data/plu_reglements`, page = page PDF). Corpus réingéré : **3222 extraits · 21 communes**.

Chiffres par script : `scripts/plu_fix11_chiffres.py` (synthèse), `scripts/plu_fix11_ordre.py` (balayage
ordre), `scripts/plu_fix10_scan_tronques.py --strict` (scan troncatures, enrichi « valeurs-fuitees »).

## LOT 0 — filet (commit séparé `13cd7af18`, rouge avant correction)

Les tests témoins affirment une **valeur précise** (plus de « OU » permissif), leur docstring dit
exactement ce qu'ils vérifient. 7 rouges au départ (points 1-3). Les deux tests p6 de FIX-10 (qui
passaient par un `OR`) sont réécrits : `..._bareme_article_page` (valeur + réf + lien) **séparé** de
`..._ligne_logement_social` / `..._ligne_logement_locatif_social` (la condition sociale précise).

## LOT 1 — valeurs rattachées au mauvais article (point 1, bloquant)

**Saint-Denis Up.10 (Hauteur, p.34)** servait la règle sans ses valeurs : l'extrait s'arrêtait sur
« …au point le plus défavorable est dans le secteur **:** » (530 car.). Les cellules du tableau de
valeurs (H : **Upr 16 m / Upi 11 m** ; égout : **RDC+3…12 m / RDC+1…6 m 50**) sont rendues, dans l'ordre
brut de `get_text()`, **après** le titre de l'article suivant Up.11, qui les captait. Même défaut que
Sainte-Marie U8, dans une commune majeure.

Correction : lecture en **ordre de position** (`get_text(sort=True)`), qui rattache chaque cellule de
tableau à son article. Le tri est **réservé** aux règlements porteurs du défaut (`_SORT_INSEE = {97411}`,
seul cas trouvé) : appliqué partout il dérègle la détection d'en-têtes d'autres communes (Saint-Paul
livrets, Le Port — vérifié par le filet). Après correction : **Up.10 porte 16 m et 11 m** (798 car.) ;
**Up.11 ne les porte plus**.

### Statut de CHAQUE ligne du scan de troncatures (`--strict`, 31 lignes)

Up.10 n'y figure plus (corrigé). Le scan est enrichi du motif **« valeurs-fuitees »** (un article au
titre chiffré sans chiffre alors que l'article suivant en contient avant son propre titre). Classement :

| Commune | Article / zone | Motif | Sort |
|---|---|---|---|
| 97403 Entre-Deux | « Article N11 » p.4-8 | deux-points | **faux positif** — bloc de dispositions générales étiqueté à tort N11, finit sur le « : » du préambule listant les chapitres (pas une règle de zone) |
| 97406 La Plaine ×14 | « ART ICLE U a - »… p.119-171 | puce | **artefact d'extraction** — PDF à **lettres espacées** (« ART ICLE »), en-têtes non détectés ; réserve déjà déclarée (FIX-10), non corrigé (hors témoins) |
| 97408 La Possession | ARTICLE UA 15 p.24-25 | deux-points | **faux positif** — article complet (3931 car.) ; le « : » final précède ARTICLE UA 16 (vérifié PDF p.25) |
| 97408 La Possession | ILLUSTRATION D'APPLICATION p.102-109 | deux-points | **faux positif** — annexe d'illustration (IUCN), pas une règle |
| 97410 Saint-Benoît ×3 | Article U–6 / A–5 / N–6 | deux-points | **faux positif** — règle de recul (75 m) **présente** ; le « : » précède un SCHÉMA (image non indexable) puis l'article suivant (vérifié PDF p.10-11) |
| 97410 Saint-Benoît | « DES VOIRIES » p.152-158 | deux-points | **faux positif** — annexe (profils de voiries) |
| 97411 Saint-Denis | XIII. INDICATIONS GRAPHIQUES p.16 | deux-points | **faux positif** — dispositions générales (indications graphiques), pas une règle de zone |
| 97412 Saint-Joseph ×2 | « ARTICLE 3 - » / « ARTICLE 4 - » p.5-12 | puce | **artefact d'extraction** — PDF à lettres espacées, en-têtes dangling ; réserve déclarée (FIX-10) |
| 97415 Saint-Paul | U6 « Article 10- » p.281-282 | puce | **faux positif** — phrase complète (« …limite de la zone. »), le « - » final est un reliquat de puce sans contenu |
| 97416 Saint-Pierre | DISPOSITIONS DELIVREES p.47 | deux-points | **faux positif** — dispositions générales |
| 97418 Sainte-Marie | préambule p.1-8 | deux-points | **faux positif** — préambule (« organisées en cinq chapitres : ») |
| 97419 Sainte-Rose | ANNEXES p.81-84 | deux-points | **faux positif** — annexe |
| 97420 Sainte-Suzanne | Titre I - Dispositions p.3-7 | deux-points | **faux positif** — préambule |
| 97414 Saint-Louis / 97423 Trois-Bassins | AUINDICEE 14 (COS) | valeurs-fuitees | **faux positif** — l'article 14 (coefficient d'occupation du sol) est un **renvoi** sans valeur (« se reporter… ») ; le motif se déclenche sur le titre « coefficient » + les chiffres de l'article AUs suivant |

Bilan : **1 corrigé** (Up.10), **16 artefacts** de PDF à lettres espacées (La Plaine 14 + Saint-Joseph 2,
réserve déclarée), **14 faux positifs** (préambule / dispositions générales / annexe / schéma / COS-renvoi).
**Aucune ligne sans statut. 0 encore ouvert.**

## LOT 2 — ordre des résultats (point 2)

Sous une zone, l'article **propre** passe désormais **toujours** avant celui d'une zone sœur/ancêtre.
Cause : les secteurs régis par un chapitre **mutualisé** (« ZONES UA, UB, UC et UD ») sont écrits dans la
**bannière** retirée du corps à l'ingestion → `_filtre_scope` ne pouvait pas savoir que « Article U 12 »
ne concerne pas UE. On capte ces secteurs (colonne `secteurs`, `_banner_secteurs` + `sbanner`
forward-fill) ; `_filtre_scope` (a) écarte un article d'ancêtre/de secteurs disjoints quand un article
**propre du même numéro** existe, et (b) **classe les articles propres avant** les non-propres (ancêtre/
sœur), même d'un autre numéro (un « Article Um.2 » d'usage ne coiffe plus « Uma.12 » sur « stationnement »).

Témoins : **Les Avirons UE 12 (p.24)**, **Salazie UT 12 (p.26)**, **Petite-Île UEa.10 (p.62)** sont
désormais le 1ᵉʳ résultat. Balayage `plu_fix11_ordre.py` sur **TOUTES les zones des 21 communes** et les 5
articles (implantation, emprise, hauteur, stationnement, espaces libres) : **701 zones · 713 couples
(zone, article) avec article propre · 0 échec**. (Une zone servie seulement par sa famille — Ub1 → chapitre
« U » — n'a pas d'article propre : son article de famille reste légitime.)

## LOT 3 — barèmes de la fiche (point 3)

La ligne du **logement (locatif) social** est restituée sur les deux fiches, avec article et page :
- **97414000DK0208 (Saint-Louis, UA)** → « logement social : 1 place / logement » (Art. UA 12.2, p.23).
- **97416000HT0538 (Saint-Pierre, Ud)** → « logement locatif social : 1 place / logement » (Art. Ud6, p.93).

On restitue toutes les lignes **typées** du barème servi (social, locatif aidé, hébergement, étudiant) en
conditions, avec un ratio canonique. Mécanisme **général** (même `BaremeStationnement` que l'Étude) :
**20 communes** à barème multi-cas portent une ligne sociale et en bénéficient.

## Tests & non-régression

- Filet `test_plu_fix10_lot0.py` (témoins FIX-10 + FIX-11) + `test_plu_cas_valides.py` : **53/53 vert**
  (les 46 existants + les 7 nouveaux témoins FIX-11).
- Balayage ordre : 0 échec ; scan : chaque ligne a un statut.
- Régression non-reel (PLU / fiche / stationnement / Étude) : **120 tests verts**.
- Réingestion des 21 communes (97411 en ordre de position, le reste en ordre naturel).

`origin/main` fusionné ; push de la branche sans `--no-verify`. Pas de fusion dans `main`.
