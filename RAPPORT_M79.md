# RAPPORT M79 — DVF : le prix au m² doit être un prix de terrain
## PHASE 0 — Mesure d'impact (mesure pure, lecture seule) — **STOP, arbitrage attendu**

Branche `feat/m79-dvf`. Run servi `q_v8_calibre`. Parc 431 663 parcelles. Aucune écriture, aucun commit.
Canari : 97415000AC0253 (ligne cascade 379 €/m² vs secteur 173).

---

## Le constat central (encadre tout le reste)

**La table `dvf_mutations` — seule source lue par le calcul cascade (`context.py::dvf_stats` →
`phase2.py::DvfLayer`) — est BÂTI-ONLY.** 29 565 des 29 566 lignes sont Maison/Appartement avec
`surface_reelle_bati > 0` ; **0 mutation de terrain nu** (1 ligne NULL anormale, 31 « terrain à bâtir »).
La médiane `median_eur_m2 = valeur_fonciere ÷ surface_terrain` est donc, à **100 %**, une valeur de bien
BÂTI étalée sur le foncier. **La pollution n'est pas partielle, elle est totale** : le rayon ne peut
structurellement PAS produire un prix de terrain, puisqu'il n'y a aucun terrain dans la table qu'il lit.

Le vrai prix de terrain nu existe déjà en base, dans une source SÉPARÉE jamais consultée par la cascade :
`dvf_mutations_parcelle` (+ `_histo`), agrégée en `dvf_secteur_medianes` (type_bien='terrain'). C'est le
« 173 » du canari, et c'est aussi ce que consomme déjà le modèle P (feature `med_pm2_terrain_36m`).

---

## Architecture vérifiée — 3 axes, le bug n'en touche qu'un

| Axe | Table | Source du prix DVF | Affecté par le 379 ? |
|---|---|---|---|
| **1. tier / rang SERVI** | `parcel_p_score_v2` (modèle P) | `med_pm2_terrain_36m` (`pm2_terrain = valeur/s_terrain WHEN NOT bati`, `p_model_ext_mut_l2`) — **terrain nu, 36 083 mutations réelles** | **NON — déjà terrain-correct** |
| **2. opportunity q/a + matrice** | `dryrun_parcel_evaluations` | bonus cascade `contexte_dvf_favorable` (poids 8, `DvfLayer`) = le 379 | **OUI** — `dvf` est une **couche A** (pèse sur le score **A**) |
| **3. challengers** | `arene.py` gate boussole | lit `matrice_statut='chaude'` (dépend de A) | indirect via l'axe 2 |

Vérifié par grep exhaustif : `scoring/p_v2/` et `p_model/` ne contiennent **aucune** occurrence de
`q_score`/`matrice_statut`/`weight_applied`/`contexte_dvf`. La seule lecture de `dryrun_parcel_evaluations`
par le pipeline P (pipeline.py:328) ne prend que `status IN ('exclue','faux_positif_probable')` (garde
étage 0 binaire). **Le rang servi ne dépend en rien du bonus cascade.**

---

## Q1 — Où le €/m² CASCADE est consommé (rayon d'impact RESTREINT)

Le 379 (médiane cascade) n'est consommé QUE par :
1. **`DvfLayer`** (`phase2.py`) → la ligne servie « Marché : N mutation(s) ≤ R m / 5 ans, médiane terrain
   X €/m² » **+ la magnitude** du bonus (poids 8, axe A).
2. **Affichage** : **fiche écran** (lines, onglet marché) et **fiche premium** (rend l'onglet marché).
   *Le premium affiche même DEUX prix à la fois : 379 (cascade) et 3 322 €/m² appartement (bloc M-U).*
3. **Magnitude → q/a score opportunity** (`dryrun_parcel_evaluations`) → matrice → arène.

**Ne consomment PAS le 379** (déjà terrain-corrects ou sources séparées, à laisser) :
- **dossier / banquier** marché : `_marche` lit `dvf_mutations`/`dvf_secteur_medianes`/`sector_price` ;
- **one-pager** marché : `voisinage_proche` (<100 m) ;
- **filtres/listes** : `v_parcel_dvf_last.prix_m2_terrain` (dernière mutation de LA parcelle, terrain) ;
- **modèle P** (tier/rang) : `med_pm2_terrain_36m` ;
- **projets.py** : médiane bâti €/m² habitable par commune (bornée 200–8000), explicitement bâti.

> Blast radius : **fiche + premium (affichage) + bonus opportunity (axe A)**. Rien d'autre.

## Q2 — Contribution réelle du bonus DVF au scoring

Couche `dvf` sur `q_v8_calibre` : **77 139 POSITIVE** (75 766 avec `weight_applied > 0`), 169 PASS.
Distribution `weight_applied>0` : p10=2, p25=4, **médiane=5**, p75=6, p90=8 (moyenne 5,04). Le bonus dvf
représente en moyenne **18 %** de la somme des poids positifs d'une parcelle (contribution réelle mais
minoritaire). Il ne pilote AUCUN tier/rang servi (Q2a confirmé ci-dessus).

## Q3 — Distribution du n de ventes du €/m² cascade

Sur 431 663, **seules 77 139 portent un prix cascade (17,9 % du parc)**. Parmi elles :

| N mutations | parcelles | part |
|---|---|---|
| N=1 | 4 872 | 6,3 % |
| N=2 | 5 195 | 6,7 % |
| **N<3** | **10 067** | **13,1 %** |
| N=3 | 5 253 | 6,8 % |
| N=4–7 | 19 216 | 24,9 % |
| N≥8 | 42 603 | 55,2 % |

Rayon retenu : **250 m dans 95,1 %** des cas. Sur échantillon (2 995), **100 % des essaims sont
bâti-only** (0 parcelle n'a la moindre mutation terrain-nu dans son rayon — corollaire du constat central).

## Q4 — Effet du remplacement terrain-nu sur le CLASSEMENT — **la mesure qui décide**

Recalcul terrain-nu depuis `dvf_mutations_parcelle/_histo` (mêmes fenêtre/rayon que la cascade), échantillon
3 925 parcelles à ligne dvf positive :

| Mesure | Valeur |
|---|---|
| Δ em2 (bâti actuel − terrain nu), médiane | **+101 €/m²** (Q1/Q3 : −83 / +299) |
| % parcelles où le terrain nu < 250 → composante prix = 0 | **19,9 %** |
| Δ q_score (×8), médian / moyen | +0,14 / +0,35 (min −6,97, max +7,43) |
| \|Δq\| ≥ 1 / ≥ 2 / ≥ 4 | 57,9 % / 28,6 % / 3,9 % |
| **Effet sur le rang P v2 (tier/rang SERVI)** | **NUL — 0 parcelle, par construction** |
| Effet matrice `chaude` (axe opportunity) | **~170 parcelles chaude → non-chaude** (~0,23 % des dvf-positives, sur 945 chaude portant une ligne dvf) |
| Sens | **resserrement uniquement** — retrait de faux « marché favorable » gonflé ; jamais de création de chaude |

> **Décision Q4** : corriger le €/m² **ne bouge pas le classement servi d'une seule ligne** (le modèle P
> calcule déjà son prix sur du terrain nu). Le seul effet scoring est **~170 parcelles qui perdent le statut
> `chaude`** via la matrice opportunity — toutes dans le bon sens (un « marché favorable » surestimé
> disparaît). **La correction est sûre.**

## Q5 — Rayon 250 m vs secteur cadastral

| Critère | Rayon 250 m (`dvf_mutations`) | Secteur cadastral (`dvf_secteur_medianes` terrain) |
|---|---|---|
| Parc avec ≥3 ventes **terrain** | **0,00 %** (dvf_mutations = bâti-only) | **90,6 %** |
| Parc avec ≥5 ventes terrain | 0,00 % | 82,2 % |
| Distribution n_ventes terrain/secteur | — | min 1, **médiane 8**, max 99 ; 85,7 % des secteurs à n≥3 |

> **Décision Q5** : le rayon est **inexploitable** pour le terrain ; le **secteur cadastral** est la base
> robuste et couvrante (≥3 ventes sur 90,6 % du parc). Un seul périmètre survit : le secteur.

## Q6 — Seuil de ventes (variance mesurée)

Bootstrap sur 372 secteurs à ≥15 ventes terrain (14 099 mutations) :

| n | erreur relative médiane | p75 | CV moyen |
|---|---|---|---|
| 1 | 55,8 % | 140 % | 558 % |
| 2 | 58,1 % | 230 % | 393 % |
| **3** | **36,0 %** | 78 % | 225 % |
| **5** | **27,6 %** | 61 % | 133 % |
| 8 | 21,5 % | 49 % | 77 % |
| 10 | 18,1 % | 42 % | 60 % |

Gain majeur au passage **n≥3** (erreur médiane 56 %→36 %, p75 230 %→78 %) ; gains marginaux après n=8.

> **Décision Q6** : seuil **n≥5** (erreur 27,6 %) comme cible de qualité, **plancher dur n≥3** en deçà
> duquel la médiane est ingérable. n≥5 couvre 82,2 % du parc, n≥3 en couvre 90,6 % (via le secteur, Q5).

---

## RECOMMANDATION Phase 1 (à arbitrer)

1. **Source** : la couche cascade DVF lit le **prix terrain du secteur cadastral** (`dvf_secteur_medianes`
   type='terrain') au lieu de calculer une médiane sur `dvf_mutations` (bâti-only). Le « 173 » est le bon
   chiffre. Le prix bâti peut rester, **sous un libellé distinct** (« bâti : X €/m² »), jamais fusionné.
2. **Seuil** : **n≥5** (plancher n≥3). En dessous : « échantillon insuffisant (n ventes) », jamais un
   nombre affiché comme robuste (reprendre la formulation du one-pager).
3. **Un seul périmètre / point de calcul** : le **secteur**. Consommé par la fiche + le premium (+ à
   décider : unifier aussi le marché dossier/banquier/one-pager pour éteindre les divergences résiduelles
   du RAPPORT_M73 — ou laisser à une passe marché dédiée).
4. **Libellé** : « Prix médian terrain — N ventes, secteur, période Z ».
5. **Bascule scoring** : recalculer la magnitude sur le chiffre juste. **Attention plo=250 / phi=900** :
   avec le vrai prix terrain, **~20 % des parcelles tombent sous 250 €/m² → composante prix = 0** ; le bonus
   dvf devient alors quasi liquidité-seule. À arbitrer : recalibrer plo/phi pour des prix de TERRAIN
   (aujourd'hui calés sur des valeurs bâti-étalées). **Golden rebasé AVANT la bascule** (gelé 07/08, 33 FAIL
   préexistants), puis recoller le delta : rang servi 0, ~170 chaude en retrait.
6. **Test de non-régression** : échoue si un €/m² inclut du bâti / est affiché sous le seuil / diverge entre
   deux points de l'app pour la même parcelle.

**Ce que la mesure change au cadrage du mandat** : le titre « corriger touche le score » est vrai mais
**borné** — le CLASSEMENT SERVI ne bouge pas (0 parcelle) ; l'effet se limite à ~170 promotions `chaude` en
retrait (axe opportunity) + l'affichage fiche/premium. La bascule est donc **peu risquée pour le rang**, à
condition de trancher la recalibration plo/phi (point 5), qui est le vrai choix de fond.

### Garde-fous Phase 0
Mesure pure, 0 écriture. Deux agents de mesure (Q3/Q5/Q6 distribution ; Q2/Q4 scoring), architecture
vérifiée. **NE PAS CORRIGER — STOP. Vic arbitre au vu du delta de classement (rang 0 · ~170 chaude) avant
toute bascule.**

---

## PHASE 0 bis — Mesure `plo`/`phi` (demandée par Vic) — **STOP, arbitrage**

Vic a confirmé : secteur cadastral, **seuil n≥5**, **plancher dur n≥3** (< 3 → « échantillon insuffisant
(n ventes) » ; entre 3 et 5 → chiffre affiché AVEC sa mention de fragilité, l'erreur médiane 27,6 % dite).
Marché dossier/banquier/one-pager = passe dédiée (M73-B partie D, qui se branche sur CE point de calcul,
jamais l'inverse). Et : **ne pas recalibrer `plo`/`phi` à l'aveugle — mesurer d'abord.**

### 1. La règle d'origine — TROUVÉE et documentée
`docs/communes/PRE_VOL_ILE.md:46-50` : « `price_lo=250 / price_hi=900 €/m²` … calée sur la distribution
**Saint-Paul p25≈312 / p75≈821** … échelle FIGÉE commune à toute l'île, pas des quantiles recalculés ».
Commit d'origine `bc2a8548c` (2026-06-08). **Règle = p25/p75 de la distribution DVF d'une commune de
référence (Saint-Paul), arrondie vers l'extérieur** (312→250, 821→900). MAIS calculée sur la grandeur
**bâti-étalée** (`dvf_mutations` bâti-only). Vérif : sur la distribution em2 actuelle (île), **250 ≈ p10,
900 ≈ p85**. La règle est donc traçable — il faut la RÉAPPLIQUER à la grandeur terrain.

### 2. Distribution réelle des prix TERRAIN par secteur (déciles, `dvf_secteur_medianes` type='terrain', n≥3)
676 secteurs. d1=114, d2=142, d3=174, d4=201, **d5(médiane)=231**, d6=267, d7=302, d8=359, d9=483 €/m².
p25=**158**, p75=**323** (île). Saint-Paul terrain (miroir de la règle d'origine, 83 secteurs) : p25=**209**,
p50=274, p75=**432**.

### 3. Où tombent `plo`/`phi` recalés au même percentile (p25/p75, arrondi extérieur)
| Base de référence | p25 / p75 terrain | `plo` / `phi` recalé |
|---|---|---|
| **Île entière** (le plus représentatif) | 158 / 323 | **≈ 150 / 325** |
| **Saint-Paul** (miroir exact de l'origine) | 209 / 432 | **≈ 200 / 450** |

### 4. Effet des deux options (parcelle-pondéré, 72 331 parcelles dvf à secteur terrain n≥3 = 93,8 % ; n≥5 = 87,6 %)
Médiane terrain assignée par parcelle = **243 €/m²**. Part des parcelles dont la composante prix tomberait à **0** :

| Option | `plo` | % parcelles composante prix = 0 | Lecture |
|---|---|---|---|
| **A — garder** | **250** | **51,8 %** | zéro-ARTEFACT (échelle bâti sur grandeur terrain) — la moitié du parc perd le signal. Interdit par la doctrine |
| **B — recaler Saint-Paul** | 200 | 34,1 % | fidèle à la règle d'origine, mais Saint-Paul est cher → plancher encore haut |
| **C — recaler île** | 150 | **17,2 %** | les 17 % sont les secteurs réellement les moins chers (sous p15-20 île) : un vrai bas, pas un artefact |

**Effet sur le CLASSEMENT** : dans les trois cas, le rang/tier SERVI (modèle P) **ne bouge pas** (immunité
établie en Phase 0). La recalibration ne joue que sur l'axe **opportunity** (magnitude du bonus A → matrice
`chaude`) : garder 250 y éteint le signal prix pour 51,8 % des parcelles (bonus quasi liquidité-seule),
le recaler île le préserve pour 82,8 %.

### Recommandation (Vic tranche)
**Option C — recaler île entière : `plo≈150 / phi≈325`** (règle d'origine p25/p75, appliquée à la vraie
distribution terrain de tout le parc, pas d'une seule commune). C'est le choix qui respecte la doctrine
(« un zéro qui EST une absence » : seuls les 17 % réellement les moins chers tombent à 0) et qui refait la
règle EXPLICITEMENT sur la bonne grandeur, au lieu d'hériter d'une échelle bâti. Garder 250/900 (option A)
est exclu (51,8 % de zéros-artefact). **Aucune bascule avant ton tranché sur A/B/C.**

### Séquence Phase 1 (rappel Vic, à respecter)
Golden gelé 07/08 avec 33 FAIL préexistants → **le rebaser PROPREMENT AVANT toute bascule** (sinon on compare
à une référence dérivée). **Si le rebase n'est pas propre → STOP.** M73-B partie D se branche sur le point de
calcul corrigé ici (dépendance à sens unique).

### Garde-fous Phase 0 bis
Mesure pure, 0 écriture, garde-fou de branche vérifié. **STOP — Vic tranche `plo`/`phi` (A/B/C) avant Phase 1.**

---

## PHASE 1 — Correction (arbitrage Vic : **Option C**, `plo=150 / phi=325`) — **CODE fait, BASCULE bloquée**

Commit `f3d4c1ec`. Vic a tranché : secteur cadastral, seuil n≥5, plancher n≥3, échelle recalée île C.

### FAIT — le calcul juste (code + test + doc)
- **Bascule de source** : `DvfLayer` (`phase2.py`) lit désormais le prix médian de **TERRAIN NU du
  SECTEUR cadastral** via `ctx.dvf_sector_terrain(idu)` (`dvf_secteur_medianes` type='terrain') — plus de
  médiane « rayon, tous biens » sur `dvf_mutations` (bâti-only). Un seul point de calcul, un seul périmètre.
- **Échelle recalée** `plo=150 / phi=325` (config `cascade_rules.yaml`), **règle d'origine p25/p75 refaite
  explicitement** sur la distribution terrain île (676 secteurs n≥3) et **documentée dans `PRE_VOL_ILE.md`**
  à côté de la règle d'origine (grandeur, percentiles, périmètre, valeurs, date).
- **Seuils** : < 3 → « échantillon insuffisant (n ventes) », aucun chiffre ; [3,5) → prix **AVEC** mention
  de fragilité (~28 % d'erreur) ; ≥ 5 → fiable. **Libellé nommé** « Prix médian terrain X €/m² — N ventes,
  secteur cadastral, période ».
- **Test de non-régression** `tests/test_dvf_terrain.py` (6/6) : échoue si un prix inclut du bâti / est
  affiché sous le plancher / si l'échelle 150/325 n'est pas appliquée.
- **Vérif d'intégration** (requête légère, sans rejeu) : `dvf_sector_terrain('97415000AC0253')` →
  `{median 173, n_ventes 3, '2021-2025'}`. **Le canari passe de 379 (bâti-étalé, n=1) à 173 (terrain, n=3,
  affiché fragile)** — exactement le « 173 » attendu.

### BLOQUÉ — la bascule (rejeu) ne peut PAS tourner proprement ici
La bascule exige de **régénérer le run servi** (`labuse dryrun-evaluate`, cascade sur 431 663 parcelles)
puis de rebaser le golden. **Tentée sur Saint-Paul (51 129 parcelles) → échec `psycopg DiskFull` : le disque
de la base est plein (`/System/Volumes/Data` à 98 %, 4,6 Gi libres)** ; Postgres ne peut plus écrire ses
fichiers temporaires (gros tris du priming SITADEL — bloc IDENTIQUE au parent, **rien à voir avec M79**).
Données de test partielles nettoyées. Par la règle Vic (« si le rebase ne passe pas net, STOP »), **je ne
force pas le rejeu** et je ne touche pas à la donnée de la base pour libérer de l'espace (ce n'est pas mon geste).

### Reste à faire (bascule, quand l'espace disque est rétabli) — dans l'ordre
1. **Libérer l'espace disque** de la base (geste opérateur — hors mandat).
2. **Rebaser le golden PROPREMENT** (`qa/golden_regen.py`, API up) sur l'état courant (pré-effet M79), le
   diff git = la revue ; comprendre/assumer les 33 FAIL préexistants.
3. **Rejeu** : régénérer le run servi avec le `DvfLayer` corrigé, puis basculer `config/served_run.txt`
   + `npm run build` + `labuse build-mvt` (procédure served_run.txt).
4. **Recoller le delta** mesuré en Phase 0 : rang servi **0** (modèle P immunisé), **~170 chaude** en retrait
   (resserrement). Si le delta diverge → STOP.
5. **Mesurer la répartition des ~17 % à composante prix nulle** (exigence Vic) : bien répartis, ou une
   commune entière en bloc ? Si une commune y passe en bloc = trou de couverture → le DIRE au client
   (« marché terrain non établi sur la commune »), pas un zéro muet.

### Dette de méthode signalée (Vic M79)
La référence **Saint-Paul figée** servait AUSSI aux **hypothèses de calcul PLU globales** : ~13 communes
lisent `plu_saint_paul.yaml` en repli (« le moteur lit les hypothèses GLOBALES de plu_saint_paul.yaml »).
Même biais que le DVF (référence figée alors que 23/24 communes sont couvertes) → **mandat PLU dédié** à
prévoir. Consigné aussi dans `PRE_VOL_ILE.md`.

### Garde-fous Phase 1
Test non-régression 6/6, tests cascade verts, vérif d'intégration canari OK, garde-fou de branche vérifié
avant chaque commit. Golden **non rebasé** (bascule bloquée disque). **NE PAS MERGER — STOP : la bascule
attend l'espace disque + ta recette du code.**
