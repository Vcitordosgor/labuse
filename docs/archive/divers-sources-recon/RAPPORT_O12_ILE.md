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

## E — Correctifs de revue 2-3-4 (3e itération) : activité, compacité, littoral

**Pool final : 308 → 17 candidats (16 libres + 1 démolition).** Attribution (détail par candidat :
`reports/o12-ile/analyse_correctifs_234.csv`) :

| Correctif | En isolation (sur 308) | Séquentiel |
|---|---:|---:|
| (2) Bâti d'activité — `ensemble_bati` cascade : ≥ 3 bâtiments (intersection ≥ 10 m², comptage `bati.stats_batch`) OU un bâtiment ≥ 400 m² | **287** | 308 → **21** |
| (3) Compacité du lot < 0,25 (Polsby-Popper) | 181 | 21 → **17** |
| (4) Littoral / domaine public (50 pas · trait de côte · forêt domaniale · cœur du Parc) | 14 | 17 → **17** (0 résiduel) |

- **(2) est le grand faucheur — et c'est structurel** : le plafond ratio ≤ 50 % (correctif A2)
  ne garde que des parcelles déjà à moitié occupées par le bâti+buffer, donc mécaniquement des
  ensembles multi-bâtiments — exactement ce que la revue a vu (cartes 4/7/14/20). Constat carte
  par carte : les 20 cartes du dossier précédent avaient TOUTES ≥ 3 bâtiments — le correctif
  élimine aussi des cartes non signalées (8, 9, 19, d'apparence résidentielle saine). Les 17
  survivants sont des parcelles à 1-2 bâtiments : le profil « maison + jardin divisible » visé.
- **(3) compacité — distribution rapportée AVANT le seuil** (sur les 308) : min 0,037 · P25 0,114 ·
  médiane 0,212 · P75 0,372 · max 0,757. Cartes « lanière » de la revue : 6 = 0,189, 18 = 0,064,
  mais **16 = 0,368** — Polsby-Popper seul ne sépare pas la carte 16 des cartes saines
  (12 = 0,308, 15 = 0,429) ; elle tombe par le correctif activité (14 bâtiments). Seuil retenu
  **0,25** (≈ rectangle 1:10) : tue 6 et 18, et retire 4 lanières du pool post-activité
  (compacités 0,186–0,205). Après correctifs : min 0,280 · médiane 0,505.
- **(4) littoral** : le corridor des 50 pas a des **trous de couverture** — la carte 3 (front de
  mer du Barachois) n'y est PAS ; son lot touche en revanche le **trait de côte** (distance 0,
  vérifié) — couche cascade ajoutée au garde (contact ≤ 1 m), qui l'exclut indépendamment du
  flag activité. En isolation : 12 lots dans les 50 pas, 4 au contact du trait, 1 en forêt
  domaniale, 0 au cœur du Parc. Résiduel séquentiel nul : les candidats littoral tombaient déjà
  par (2)/(3) — le garde reste nécessaire (sans (2), la carte 3 ne serait éliminée que par lui).

Effectifs finaux par commune (9 communes en portent, 15 à zéro) : Sainte-Marie 4 · Saint-Leu 3 ·
Saint-Paul 3 (dont la démolition) · Saint-Pierre 2 · L'Étang-Salé, La Plaine-des-Palmistes,
Saint-Denis, Saint-Joseph, Sainte-Suzanne 1. Lots : 509–898 m² (médiane 590) — le pool a changé
de nature : petits lots nus compacts au lieu de grands résiduels d'ensembles bâtis.

Dossiers régénérés pour la revue unique : **`O12_ILE_REVUE.pdf` (16 cartes libres, île entière)**
+ **`O12_ILE_DEMOLITION_REVUE.pdf` (1 carte)**. Golden re-passé : **116/116 PASS**. Tests : 7/7.

## F — Viabilité du LOT RESTANT (4e itération) : 17 → 15

Le critère vérifiait le lot détaché, jamais ce qui reste au propriétaire. Correctif :
**l'emprise bâtie résultante du lot restant** (bâti conservé ÷ surface restante — pour une
démolition, le bâti à démolir est déduit) **est plafonnée** :

- **emprise max CALIBRÉE de la (sous-)zone** quand elle existe — lookup `config/plu_<slug>.yaml`
  (`emprise_sol_pct` chiffré, clé = libellé de zone) via `plu_rules.load_rules`, injecté en SQL
  (`CASE zone_lib …`) par commune. Le libellé vient de `attrs->>'libelle'` (code seul —
  `name` mélange parfois « code : description » selon la commune, piège constaté à Saint-Denis) ;
- sinon **plancher prudent 60 %** (`EMPRISE_RESTANTE_MAX`). État calibrage : Saint-Denis
  20 zones chiffrées (30–80 %), Saint-Paul 0 (tout `null`/`a_verifier`) → plancher partout sauf
  Saint-Denis, aujourd'hui.

**Retire 2 candidats sur 17 — exactement les cartes 1 et 11 de la revue** :
`97418000BT0459` (Sainte-Marie, emprise résultante 0,796) et `97406000AE0276`
(La Plaine-des-Palmistes, 0,804). Le suivant est à 0,595 — sous le plancher. Le candidat de
Saint-Denis (`97411000BP0363`, 0,355) est jugé contre son plafond CALIBRÉ (zone Ua : 70 %) et
survit. Colonnes ajoutées : `zone_lib`, `emprise_restante` (traçabilité carte/table).

**Pool final : 15 candidats (14 libres + 1 démolition), 8 communes.** Emprises restantes
0,307–0,595, lots 509–898 m² (médiane 590), compacité 0,280–0,717. Golden : **116/116 PASS**.
Tests : 8/8. Dossiers PDF **non régénérés** (demande explicite — session d'affichage saturée).

## Session neuve — mode d'emploi (dossiers à régénérer)

La table `division_or_candidates` est À JOUR (15 candidats, formule complète). Il ne reste qu'à :
```bash
DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib \
LABUSE_DATABASE_URL=postgresql+psycopg://openclaw@localhost:5432/labuse PYTHONPATH=src \
~/miniforge3/envs/labusedb/bin/labuse division-or-review \
  --out docs/mandats/O12_ILE_REVUE.pdf --limit 20 --type libre        # 14 cartes
# idem --type demolition --out docs/mandats/O12_ILE_DEMOLITION_REVUE.pdf   # 1 carte
```
(Les PDF versionnés datent de l'itération E — 16 + 1 cartes — et contiennent donc 2 cartes
retirées depuis : `97418000BT0459` et `97406000AE0276`. Les cartes affichent maintenant aussi
zone_lib/emprise via la table.) Golden local : API `uvicorn labuse.api.app:app --port 8010`
avec la même DATABASE_URL, puis `PYTHONPATH=src python qa/golden_check.py`.

## Ce que la revue devra trancher

Après les vagues de correctifs (A2/A3, D, 2-3-4, viabilité du restant), le vivier est passé de
5 916 à **15** candidats — très haute précision visée, rappel sacrifié. Deux effets structurels se cumulent :
le ratio ≤ 50 % ne garde que des parcelles déjà à moitié occupées, et le filtre activité (≥ 3
bâtiments) écarte ces mêmes parcelles très bâties — l'intersection des deux est étroite, et la
configuration « petit bâti en coin d'une GRANDE parcelle U » (division réelle la plus fréquente)
reste hors de portée car le détecteur ne sait proposer que le résiduel ENTIER, jamais un lot
partiel. Si la revue des 15 est bonne mais le vivier jugé trop maigre pour exposer, la piste
n'est ni d'assouplir le ratio ni le critère activité : c'est le **découpage de lot proposé**
(sous-polygone du résiduel côté voirie, ~600-900 m², compacité imposée) — il rouvrirait les
grandes parcelles U sans réintroduire les démembrements ni les ensembles bâtis.
