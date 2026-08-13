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
