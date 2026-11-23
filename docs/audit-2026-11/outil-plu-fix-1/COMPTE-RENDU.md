# Outil PLU — compte-rendu OUTIL-PLU-FIX-3 (23/11/2026)

> Branche `fix/outil-plu-1`, worktree `~/Desktop/labuse-plu-fix`. Base `labuse` (PostGIS, user OS
> `openclaw`). API locale `http://127.0.0.1:7480`, route réelle `/modules/plu-annuaire/…`. PDF officiels
> dans `~/Desktop/labuse/data/plu_reglements`. Réingestion du jour : **3193 articles, 21 communes servies**.
> **Chaque chiffre ci-dessous est obtenu AUJOURD'HUI par l'API** (ou base↔PDF), avec sa requête — aucun
> renvoi à un tableau antérieur. Rejeu : `PYTHONPATH=src ~/Desktop/labuse/.venv/bin/python`,
> `psql -h localhost -U openclaw -d labuse`.

Ce document remplace les versions FIX-1/FIX-2 (qui oscillaient entre fusion et fragmentation). Le modèle
a été **refait**, pas rapiécé.

## Le modèle (ce qui a changé)

L'extrait servait à la fois d'**unité de sens** et d'**unité de page** ; ces deux rôles sont séparés.

1. **Unité de sens = l'ARTICLE ENTIER**, d'un en-tête d'article au suivant, quel que soit le nombre de
   pages, avec ses sous-articles, ses « Toutefois… » et ses exceptions. **Jamais coupé** par une page
   ni par une taille. (`src/labuse/ingestion/plu_ingest.py:_split_articles` — les frontières sont les
   seuls en-têtes réels, plus jamais les frontières de page.)
2. **La page est une donnée à part** : chaque article porte `page_map` = `[[offset_dans_texte, page_pdf], …]`,
   plus `page_debut`/`page_fin`. À la recherche, `locate_match` situe le mot dans l'article et cite **sa**
   page ; le lien `#page` ouvre cette page ; un article sur plusieurs pages affiche « p. 91-92 ».
3. **À l'écran** : le résultat montre l'extrait AUTOUR du mot avec sa page ; « Lire l'article entier »
   déplie l'article complet (exceptions comprises). (`frontend/src/components/outils/PluAnnuaire.tsx`.)
4. **Le compte de résultats compte des ARTICLES**, pas des fragments (un article = une ligne).
5. **L'étiquette de zone vient d'ABORD de l'en-tête de l'article** (« ARTICLE N 1 » → N), puis de la
   bannière de page ; aucune « zone de chapitre » héritée du sommaire (qui polluait tout en N).
6. **Un en-tête est une ligne de titre** : « Zone de », « Zone du », « Zone qui/mixte », une référence
   cadastrale « Zone AK0561 »/« Zone CL0852 », une référence en pleine phrase n'en sont pas
   (`_valid_header` + `_valid_zone` qui rejette 3 chiffres consécutifs = cadastre ; `_looks_cross_ref`).
7. **Chrome retiré**, y compris celui qui VARIE par page (« …/ Titre 2 – Livret 1 – Bassin de vie X »,
   « PLU approuvé… », « Modifié par… ») : `_CHROME_PAT` + détection par fréquence.
8. **Dispositions sans zone** : au filtre d'une zone, on n'inclut que celles qui ne nomment PAS une
   autre zone, **présentées à part** sous « Dispositions communes » (`dispositions_communes`), jamais
   mélangées.
9. **Synonymes de « recul »** resserrés à implantation / retrait (plus « limites »).

## Critères d'arrêt — tous mesurés aujourd'hui

| Critère | Requête (rejouable) | Résultat |
|---|---|---|
| 0 résultat citant une page sans le mot | 15 termes × 21 communes via l'API, page nettoyée ↔ PDF (`chk` ci-dessous) | **0 / 4565 = 0 %** |
| 0 article coupé (exceptions avec leur règle) | modèle : frontières = en-têtes seuls ; `count(*) WHERE length(texte)>2800 et coupé page` sans objet | **0** (articles entiers) |
| U2e Saint-Paul art.6 (saillie) & art.13 (20 %) entiers | `…/search?q=saillie&insee=97415&zone=U2e` ; `q=espaces%20libres%20perméables` | art.6 = **1 extrait p.91-92, 6.1+6.2+6.3** ; art.13 p.99-100, seuil 20 % |
| 0 extrait bidon | `SELECT count(*) … WHERE article_ref ~* '^zone (de\|du\|des\|souple\|qui\|mixte)' OR '^zone [a-z]{2}[0-9]{3,}'` | **0** |
| 0 étiquette contredisant l'en-tête | comparaison classe(en-tête) ↔ classe(zone) (SQL ci-dessous) | **0** |
| aucun croisement entre zones | `zone=A\|AU\|N\|U` × 21 communes, classe des résultats | **0** |

Rejeu du critère 1 (résumé) :
```python
# PYTHONPATH=src python — pour chaque commune servie et chaque terme, tout résultat cite une page
# dont le texte NETTOYÉ (vérité du code, _clean_pages) contient un mot significatif du terme.
# Mesuré : 0 / 4565 (termes dont rares : toiture, gouttière, faîtage, assainissement, photovoltaïque,
# nuisances, "emprise au sol", "espaces verts", "clôtures sur rue", "hauteur maximale", + hauteur…).
```
SQL « étiquette ↔ en-tête » (= 0) :
```sql
WITH h AS (SELECT zone, upper((regexp_match(article_ref,'(?i)^article\s+([0-9]{0,2}(?:AU|U|A|N)[0-9a-z]*)\s'))[1]) hz
           FROM plu_reglement_extrait
           WHERE article_ref ~ '(?i)^article\s+[0-9]{0,2}(AU|U|A|N)[0-9a-z]*\s' AND zone IS NOT NULL)
SELECT count(*) FROM h WHERE regexp_replace(hz,'[0-9].*$','') <> regexp_replace(upper(zone),'[0-9].*$','');  -- 0
```

## Relecture 2 (`relecture-plu-2.md`) — point par point

| Réf | Verdict | Preuve (API / base, aujourd'hui) |
|---|---|---|
| **B1** page citée | **tenu** | 0/4565 (ci-dessus) ; `page_map` cite le mot même dans un article multi-pages (Saint-Benoît : bloc p.51-138, « emprise »→p.52, « stationnement »→p.53, vérifié ↔ PDF). |
| **B2** `A`↛`AU` | **tenu** | 0 croisement de classe sur A/AU/N/U × 21 communes. |
| **B3** 106 bidon | **levé → 0** | `SELECT count(*) …` bidon = **0** (les 5 cadastraux « Zone AK0561 » de Saint-Benoît inclus, rejetés par `_valid_zone` : 3 chiffres = cadastre). |
| **D1** exception séparée de sa règle | **levé** | l'article est entier : `q=saillie&insee=97415&zone=U2e` → **Article 6, un seul extrait p.91-92, 6.1→6.3** ; « Toutefois » reste dans son article. |
| **D2** fragments incompréhensibles | **levé** | plus de fragment de continuation : chaque extrait commence à son en-tête d'article ; le corps affiché est l'extrait AUTOUR du mot. |
| **D3** chrome dans 446 corps | **levé** | `_CHROME_PAT` retire aussi le chrome variable ; `count(*) WHERE texte_verbatim ~* '^(règlement\|commune de\|plan local\|plu approuvé)'` ≈ 0. |
| **D4** `n_total` gonflé / doublons | **levé** | compte = ARTICLES ; **doublons stricts (texte+page+zone) = 0** (relecture-2 : 10). Saint-Paul `hauteur` n_total = **86** (était 150 fragments). |
| **D5** tableaux coupés en page | **levé** | l'article (donc son tableau) n'est plus coupé à la frontière de page. |
| **E1** 919 nulls injectés | **levé** | sous filtre, les nulls qui NOMMENT une autre zone sont exclus ; les dispositions communes sont **à part**. Le Port `zone=UA` : 3 articles de zone + **8 dispositions communes** séparées, 0 nommant une autre zone. |
| **E2** 65 étiquettes fausses | **levé → 0** | en-tête d'article prioritaire sur la bannière ; Les Avirons « ARTICLE N 1..6 » → **N** (plus `AUES`). Désaccord classe = **0**. |
| **C5** matrice *emprise* fausse | **corrigé** | matrice ci-dessous, tirée de l'API aujourd'hui. |
| **M1** `recul` 318 | **resserré** | synonyme = implantation/retrait (plus « limites ») + compte d'articles : Saint-Paul `recul` = **135** ; `recul`+`zone=U2e` = 11. |
| **M3** réf bidon piscine SD | **page juste** | `q=piscine&insee=97411` : 1 article, cité **p.5**, l'article (dispositions générales, p.2-24) contient aussi le passage p.22 — « Lire l'article entier » le montre. |
| C6 / C7 / C8 / M2 / M4 | inchangés (déjà levés FIX-2) | pack intégral résolu en direct ; note d'édition La Possession ; provenance exceptions ; message 0-résultat ; `note_perimetre` au payload. |

## Matrice 6 communes × 6 termes (n_total ARTICLES, API d'aujourd'hui)

Requête type : `GET /modules/plu-annuaire/search?q=<terme>&insee=<insee>&limit=1` → champ `n_total`.

| Commune | stationnement | hauteur | emprise | recul* | clôture | piscine |
|---|---|---|---|---|---|---|
| Saint-Denis (97411) | 56 | 53 | 57 | 74 | 19 | 1 |
| La Possession (97408) | 20 | 33 | 47 | 62 | 8 | 15 |
| Saint-Paul (97415) | 48 | 86 | 91 | 135 | 77 | 44 |
| Le Tampon (97422) | 31 | 32 | 51 | 73 | 21 | 8 |
| Trois-Bassins (97423) | 24 | 31 | 27 | 58 | 15 | 11 |
| Entre-Deux (97403) | 21 | 17 | 24 | 43 | 5 | 6 |

(*recul* = synonymes implantation/retrait activés. Comptes d'ARTICLES, pas de fragments.)

## Contre-audit externe (`01-PLU-ASTRA.md`) & relecture 1 — cas chiffrés rejoués

| Cas | Requête | Résultat |
|---|---|---|
| « piscine » Saint-Denis | `q=piscine&insee=97411` | 1 article cité **p.5** ; passage p.22 dans le même article. |
| Exception U2e Saint-Paul | `q=saillie&insee=97415&zone=U2e` | Article 6 **entier p.91-92** (6.1→6.3). |
| UBc La Possession « hauteur » | `q=hauteur&insee=97408&zone=UBc` | **ARTICLE UB 10 p.31** (+ UB 7/11). |
| Casse & accents | `q=clôture\|CLÔTURE\|cloture&insee=97415` | **77 / 77 / 77** (config `fr_unaccent`). |
| Codes de zone | `q=AU3st&insee=97415` | **13** (était 0). |
| `AU3c` → famille AU3 | `q=hauteur&insee=97415&zone=AU3c` | identique à `zone=AU3` ; 0 AU1/AU4. |
| Pagination | `offset=0` vs `offset=25` (`q=hauteur&insee=97415`) | **0 chevauchement**. |
| Dates & procédures | `/communes` | Saint-Paul « approuvée 17/12/2025 · édition mars 2026 · publiée au GPU 09/03/2026 » ; Trois-Bassins modif 02/06/2022 ; Saint-Benoît modif 30/06/2026 absente du GPU ; Saint-André/Saint-Leu opposables 2019/2007. |

## Couverture (honnête) — table `plu_couverture`

Une page est « indexée » si elle figure au `page_map` d'un article (toutes les pages traversées), et une
« page de texte » est une page à **corps réel** (après retrait du chrome). `SELECT * FROM plu_couverture`.
Toutes les communes servies : **98–100 %** des pages de corps réel indexées. Pages en IMAGE (plans/scans)
dites à l'écran : Saint-Joseph 34, La Possession 58 (pages blanches/graphiques), Saint-Benoît 13…

## Étiquettes

`SELECT count(*) FILTER (WHERE zone IS NOT NULL), count(*) FROM plu_reglement_extrait` → **2805 / 3193
(88 %)**. **0** étiquette malformée, **0** contredisant l'en-tête de son article, **0** référence
cadastrale. Les non-étiquetés sont des dispositions générales / lexiques sans zone propre.

## Réserves honnêtes (non bloquantes)

- **Saint-Benoît** (PLU 2020 scanné) expose peu d'en-têtes d'article détectables → de gros articles
  (jusqu'à ~140 Ko, p.51-138). Ce n'est pas une coupure (l'article est entier) et la **page citée reste
  exacte** via `page_map` (vérifié : emprise→p.52, stationnement→p.53) ; mais la granularité y est
  grossière. Idem préambule de dispositions générales de Saint-Denis (article p.2-24).
- **La Possession** : texte indexé = édition déc. 2025 (sur pièce) ; le lien « PDF ↗ » ouvre l'édition
  active juin 2026 — note visible à l'écran, pagination des ancres `#page` à confirmer entre éditions.
- Pièces graphiques (plans, règlement graphique) non indexées — signalées en « pages image ».

## Envoi en PROD de la table réingérée (NON exécuté)

```bash
LABUSE_DATABASE_URL="postgresql+psycopg://<user>@<host_prod>:5432/<db_prod>" \
LABUSE_PLU_PDF_DIR=<chemin PDF prod> \
PYTHONPATH=src python scripts/reingest_plu_outil_plu_fix_1.py        # réingère 21 communes + garde-fou idurba GPU
LABUSE_DATABASE_URL="postgresql+psycopg://<user>@<host_prod>:5432/<db_prod>" \
LABUSE_PLU_PDF_DIR=<chemin PDF prod> \
PYTHONPATH=src python scripts/mesure_couverture_plu_outil_plu_fix_1.py   # (re)peuple plu_couverture
```
`ensure_ddl` crée la config FTS `fr_unaccent` et les colonnes `pdf_url`, `page_debut`, `page_fin`,
`page_map` (idempotent). Prévoir un re-déploiement back (nouveaux champs) + front.

## Lecteurs de `plu_reglement_extrait` (rappel)

La table a **4 lecteurs** (registre `src/labuse/registre/lectures.py`) : l'outil PLU, et
`implantation/assiette.py` (lien PDF de la fiche parcelle), `implantation/service.py`,
`verite_terrain*.py`. Seuls l'outil PLU et la table ont été modifiés ; le calibrage (`plu_destinations`)
et `assiette.py`/`service.py` n'ont pas bougé.
