# RAPPORT O12-ÎLE — Extension et durcissement du détecteur Division en or

Branche `feat/o12-ile` (aucun merge). **EXPOSE reste `False`** — la décision d'exposition viendra
après la revue visuelle du nouveau dossier 20 cartes. Golden **116/116 PASS**.

Contexte : la revue des 20 cartes (Entre-Deux 72 + Bras-Panon 51 candidats) a identifié trois
défauts. Ce mandat les corrige, exécute le détecteur sur les 24 communes et regénère le dossier.

---

## A — Correctifs de la formule (`src/labuse/ingestion/division_or.py`)

| # | Défaut (revue) | Correctif |
|---|---|---|
| A1 | Carte 01 (`97402000AK0873`, façade 465 m) : la façade voirie dominait le score de clarté → une bande linéaire le long d'une route sortait en tête | Façade **plafonnée à 30 m** dans le score : `clarte = rayon×2 + LEAST(façade, 30)`. La façade reste un filtre (≥ 12 m) et une métrique affichée telle quelle sur la carte. |
| A2 | Un « lot » de 4 748 m² détaché d'une parcelle de 5 433 m² (87 %) est un démembrement, pas une division | Filtre **`free_m2 ≤ surface_m2 × 0.5`** (dans la CTE `acces`, avant le calcul de façade — le plus tôt possible). |
| A3 | Des candidats en zone A et N — une division urbaine n'y a pas de sens | **Zone dominante du LOT** (plus grande intersection avec `plu_gpu_zone`) : gardé si `U` ou `AU*` ; **A/N exclus** ; lot **sans zonage** (commune RNU, `rnu_communes.yaml`) gardé **seulement si la parcelle est dans la PAU estimée** (`parcel_pau`, méthode validée du mandat RNU) — sinon exclu. Si la table `parcel_pau` n'existe pas, le prédicat devient `false` (conservateur). |

Le test porte sur le **lot** (le résiduel), pas la parcelle : c'est lui qui doit être constructible.
Nouvelle colonne `zone` sur `division_or_candidates` (DDL additif, `ADD COLUMN IF NOT EXISTS`),
affichée sur chaque carte de revue (« RNU — PAU estimée » quand NULL).

Tests : `tests/test_division_or.py` — nouveau `test_correctifs_o12_ile_dans_detect` (les trois
gardes verrouillées dans le SQL) + les gardes existantes inchangées. **5/5 PASS.**

## B — Run île entière (24 communes)

`scripts/o12_ile_bilan.py` : phase 1 rejoue l'**ancienne formule annotée** (lecture seule) pour
attribuer chaque élimination ; phase 2 `TRUNCATE` + **`build_divisions`** (formule corrigée) sur
les 24 communes, 5 en parallèle. Contrôle de non-régression : Entre-Deux 72 et Bras-Panon 51
**reproduits à l'identique** par la phase 1.

| Commune | Avant | Après | | Commune | Avant | Après |
|---|---:|---:|---|---|---:|---:|
| Bras-Panon | 51 | 1 | | Saint-André | 252 | 30 |
| Cilaos | 97 | 3 | | Saint-Benoît | 267 | 16 |
| Entre-Deux | 72 | 2 | | Saint-Denis | 545 | 18 |
| L'Étang-Salé | 129 | 7 | | Saint-Joseph | 423 | 17 |
| La Plaine-des-Palmistes | 110 | 2 | | Saint-Leu | 284 | 19 |
| La Possession | 146 | 10 | | Saint-Louis | 395 | 14 |
| Le Port | 24 | 11 | | Saint-Paul | 745 | 65 |
| Le Tampon | 720 | 6 | | Saint-Philippe | 40 | 4 |
| Les Avirons | 114 | 0 | | Saint-Pierre | 404 | 30 |
| Les Trois-Bassins | 115 | 1 | | Sainte-Marie | 278 | 20 |
| Petite-Île | 204 | 3 | | Sainte-Rose | 56 | 0 |
| Salazie | 265 | 5 | | Sainte-Suzanne | 180 | 10 |

**Total : 5 916 avant → 294 après (−95 %).**

### Ce que les correctifs ont éliminé (attribution, non exclusive — détail : `reports/o12-ile/bilan_avant.csv`)

- **Ratio lot/parcelle > 50 % : 5 562 candidats (94 %)** — dont 3 295 éliminés par ce seul critère.
  Le ratio médian « avant » était de **0,72** : le résiduel géométrique emporte naturellement
  presque toute la parcelle dès que le bâti est en coin (c'était le cœur du défaut « démembrement »).
- **Zone A/N (lot) : 2 309 candidats (39 %)** — dont 57 éliminés par la seule zone (2 252 cumulaient
  ratio + zone). Avant correctifs : 1 712 lots en zone A, 597 en N.
- **RNU hors PAU estimée : 18** (Saint-Philippe passe de 40 à 4 — les 4 restants sont dans la PAU).
- Les deux faux positifs types du mandat sont éliminés :
  `97402000AK0873` (façade 465 m, ratio 0,905) et `97403000AP2213` (4 748/5 433 m², ratio 0,874) —
  tous deux par A2.
- A1 (plafond clarté) n'élimine personne par construction : il **retrie** le dossier de revue
  (une façade de 102 m ne « gagne » plus que 30 points, le rayon inscrit redevient discriminant).

### Distribution après correctifs (n = 294)

- **Surfaces de lot** : min 501 · P25 775 · **médiane 1 052** · P75 1 739 · max 2 885 m² —
  plus aucun lot au-delà de 50 % de sa parcelle (ratio moyen 0,43, max 0,50).
- **Zones** : U = 280 · AUc = 7 · AU = 3 · RNU-PAU = 4. Emprise bâtie moyenne 30 %,
  façade médiane du lot 38 m.
- Gain Score É V2 : 12 candidats estimables seulement, médiane négative (−484 k€) — cohérent avec
  le Score É île entière (marges promoteur serrées) ; le gain reste « Estimé », jamais un filtre.

## C — Nouveau dossier de revue

- **`docs/mandats/O12_ILE_REVUE.pdf`** — 20 cartes, **5 par commune dense** (Saint-Paul,
  Saint-Denis, Le Tampon, Saint-Pierre), tri clarté (plafonnée) par commune. Chaque carte affiche
  désormais le **zonage du lot**. Échantillonnage en tourniquet (`top_candidates(…, communes=…)`,
  CLI `labuse division-or-review --communes …`) : rang-1 de chaque commune, puis rang-2, etc. —
  une commune à court de candidats est compensée par les autres.
- **`docs/mandats/O12_ILE_REVUE.zip`** — le PDF + les preuves du run (`bilan_avant.csv` annoté
  candidat par candidat, `run_ile.log`).

## Preuves

- `pytest tests/test_division_or.py` : **5/5 PASS** (nouvelles gardes comprises).
- Suite complète locale : **1 114 PASS, 19 FAIL, 19 skip** — les 19 échecs sont **identiques au
  diff près sur `main` sans mes changements** (vérifié par stash/run/diff : `IDENTIQUES`) ; causes
  d'environnement poste (`pandas` absent de l'env `labusedb`, libs natives WeasyPrint) — dont
  5 modules non collectables (`test_findings_n4`, `test_arene`, `test_p_model_*`,
  `test_p_v2_statuts` ; `requirements-ml.txt` non installés sur ce poste).
- **Golden : 116/116 PASS, 0 FAIL** (API locale 8010 + base locale, run servi `q_v7_defisc`).
- La table `division_or_candidates` ne contient plus QUE des candidats post-correctifs
  (`TRUNCATE` avant le run — les 123 candidats de la revue précédente sont retirés).

## Findings d'ingénierie (hors périmètre, consignés)

1. **`python -m labuse.cli` est amputé** : un `if __name__ == "__main__": app()` au **milieu** de
   `cli.py` (ligne ~1525) lance l'app avant l'enregistrement des ~30 commandes suivantes
   (dont `division-or*`). L'entrée console `labuse` (import complet) n'est pas affectée.
   Correctif trivial (déplacer le bloc en fin de fichier) — non fait ici, hors mandat.
2. **Golden sans `PYTHONPATH=src` = faux échec trompeur** : l'import de `Q_A_RUN_LABEL` échoue
   silencieusement → repli sur le run mort `q_v5_m6b` → « −1/116 PASS, 117 FAIL » qui ressemble à
   une vraie casse. Toujours lancer `PYTHONPATH=src python qa/golden_check.py` en local.
3. **WeasyPrint sur ce Mac** exige `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` (libgobject).
4. Le run île a mis en évidence de fortes variations de durée par commune (7 s à 16 min) selon
   l'état du cache Postgres — le script est parallélisé (5 communes, `O12_WORKERS`) et trie les
   grosses communes en premier.

## D — Le bâti dans le lot : classé, pas exclu (2e itération du mandat)

Deux types de division, distincts partout (table, tri, cartes) :

- **`libre`** (lot nu — le cas classique, **prioritaire au tri** du dossier) : lot = plus grand
  résiduel après retrait de TOUT le bâti. Inchangé — les **294 candidats sont reproduits à
  l'identique**, aucun n'est requalifié.
- **`demolition`** : lot = plus grand résiduel après retrait du seul bâtiment **PRINCIPAL**
  (plus grande emprise au sol sur la parcelle) — le lot peut contenir du bâti **secondaire**,
  chiffré (`bati_lot_m2`, « dont N m² à démolir ») et **tracé en rouge** sur la carte.
  Parcelle mono-bâtiment : variante sautée (identique à libre). Une parcelle qui passe en libre
  **reste libre** (dédoublonnage, la démolition ne remplace jamais une division sans démolition).

### Garde anti-« découpage inversé » (critère proposé et appliqué)

Deux niveaux :
1. **Par construction** : le bâtiment principal est retiré du lot avec son buffer de 3 m —
   le lot ne peut JAMAIS contenir la maison principale.
2. **Critère de secondarité** : `bati_lot × 3 ≤ bati_total`, c.-à-d. **le bâti à démolir pèse au
   plus la moitié du bâti conservé** (équivalent : ≤ 1/3 du bâti total de la parcelle). Au-delà,
   le « lot » emporte l'essentiel des constructions et le reste est du jardin → découpage
   inversé, candidat **rejeté**.
   Limite honnête : « principal » = plus grande **emprise au sol** (pas de notion d'usage — un
   grand hangar peut dominer une petite maison) ; c'est précisément ce que la revue visuelle voit.

### Chiffres île entière (preuves : `reports/o12-ile/bilan_demolition.csv` + `run_demolition.log`)

- Variante démolition brute (géométrie + zonage, sans garde) : **30 lots**, dont **19 parcelles
  nouvelles** (les 11 autres passaient déjà en libre et y restent).
- Garde de secondarité : **14 gardés · 5 rejetés** (découpage inversé — le critère travaille).
- **Table finale : 294 libres + 14 démolitions = 308 candidats.** Bâti à démolir : min 6 ·
  médiane 138 · max 501 m² (le max reste ≤ moitié du bâti conservé, par construction du critère).
- Dossiers : `O12_ILE_REVUE.pdf` régénéré (type affiché sur chaque carte) + nouveau
  **`docs/mandats/O12_ILE_DEMOLITION_REVUE.pdf`** (les 14 cartes, bâti à démolir en rouge) —
  la classe nouvelle a son propre dossier de validation. CLI : `division-or-review --type demolition`.
- Golden re-passé après D : **116/116 PASS**. Tests : 6/6 (nouvelles gardes verrouillées).

## Ce que la revue devra trancher

Le ratio ≤ 50 % est **le** filtre dominant (94 % des éliminations) : il ne garde que les parcelles
dont le bâti + son buffer occupent déjà ≈ la moitié de l'emprise. C'est le durcissement demandé et
il tue les démembrements — mais il écarte aussi la configuration « petit bâti en coin d'une grande
parcelle U », où une division réelle découperait un lot PARTIEL du résiduel (le détecteur ne sait
proposer que le résiduel entier). Si la revue des 20 nouvelles cartes juge le reste sain mais le
vivier trop maigre (294 sur l'île), la piste suivante est un **découpage de lot proposé**
(sous-polygone du résiduel côté voirie) plutôt qu'un assouplissement du ratio.
