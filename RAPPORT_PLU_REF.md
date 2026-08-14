# RAPPORT M-PLU-REF — La référence Saint-Paul figée dans les hypothèses de constructibilité (Phase 0)

**Branche `feat/plu-ref`. Aucune correction — mesure seule. STOP arbitrage Vic. Mesuré le 14/08/2026.**

## Verdict en une phrase
Le biais M79 (référence figée sur Saint-Paul) est **confirmé et plus profond qu'annoncé** : les valeurs
de constructibilité de Saint-Paul (`coef_occupation 0,45`, `densite 30 logts/ha/niveau`, `coef_rendement
0,80`, `etage_m 3,0`…) sont la valeur **universelle** — copiées à l'identique dans les 12 YAML communaux
**ET** posées comme défauts du dataclass `Hypotheses`. Quelle que soit la voie (YAML de la commune ou
repli dataclass), une commune obtient **les nombres de Saint-Paul des deux côtés**. Aucune commune n'est
calibrée à son propre règlement.

## 1 — Inventaire par commune (chemin de résolution)
`Hypotheses.charger(commune)` (engine.py:76) lit la section `hypotheses_faisabilite` du YAML de LA
commune ; paramètre absent → **défaut du dataclass** (jamais Saint-Paul explicitement… sauf que le
défaut dataclass EST la valeur Saint-Paul). Les params **économiques** (cout/marge) passent en plus par
`bilan_params` (registre ← global `'*'` ← secteur).

| paramètre | nature | valeur Saint-Paul | dans les 12 YAML | défaut dataclass |
|---|---|---|---|---|
| `coef_occupation` | **CONSTRUCTIBILITÉ (règlement — emprise au sol)** | 0,45 | **copié 12/12** | 0,45 (= SP) |
| `densite_logts_ha_par_niveau` | **CONSTRUCTIBILITÉ (règlement — ex-COS)** | 30,0 | **copié 12/12** | 30,0 (= SP) |
| `etage_m` | physique (hauteur d'un niveau) | 3,0 | copié 12/12 | 3,0 |
| `coef_rendement` | technique construction (SDP→habitable) | 0,80 | copié 12/12 | 0,80 |
| `logement_m2_bas/haut` | marché (surface moyenne logt) | 65/80 | copié 12/12 | 65/80 |
| `place_m2` | norme stationnement | 25 | copié 12/12 | 25 |
| `cout_construction_m2_bas/haut` | économique | 2300/2800 | 2/12 (StDenis, StPierre) | 2300/2800 (= SP) |
| `marge_promoteur_pct` | économique | 0,09 | 2/12 | 0,09 (= SP) |
| `frais_annexes_pct` | économique | 0,12 | 0/12 | 0,12 (= SP) |

Les 12 communes concernées : Bras-Panon, Cilaos, Le Port, Le Tampon, La Plaine-des-Palmistes, Les
Avirons, Les Trois-Bassins, Petite-Île, Saint-Benoît, Saint-Denis, Saint-Louis, Saint-Pierre.
(Mixité — `pct_lls`, seuils Art. 2 — déjà traitée en M-N P1-13 : seule Saint-Paul porte `mixite_source_ref`,
les autres sont « Estimé — seuils par défaut ». Ne pas redupliquer.)

## 2 — L'écart au règlement réel : NON MESURABLE en l'état (et c'est LE constat)
Pour comparer « densité Saint-Paul 30 » à « densité réelle commune X », il faudrait la valeur réelle du
règlement de X. **Elle n'est enregistrée nulle part** : la seule valeur présente dans le système EST
celle de Saint-Paul (copiée + défaut). L'écart est donc **inconnu par construction** — exactement le
biais M79 : une référence unique gelée, jamais confrontée aux 23 autres règlements. **Établir les
densités/emprises réelles par commune est une CALIBRATION (mesure documentaire du règlement), pas une
correction de chemin — elle relève de Vic** (cf. Ajout 2 du mandat : « mesurer n'est pas calibrer »).

## 3 — Parcelles affectées
**~230 539 parcelles** (les 12 communes) = **53,4 %** du parc (431 663). Ventilation :
Le Tampon 42 756 · Saint-Pierre 42 425 · Saint-Denis 38 138 · Saint-Louis 29 241 · Saint-Benoît 21 671 ·
Petite-Île 13 137 · Le Port 10 195 · Les Avirons 8 611 · Cilaos 6 560 · La Plaine-des-Palmistes 6 450 ·
Bras-Panon 6 041 · Les Trois-Bassins 5 314. Toute parcelle U/AU de ces communes calcule sa
capacité/bilan avec `coef_occupation 0,45` et `densite 30` empruntés à Saint-Paul.

## 4 — Effet sur la sortie client : STRUCTURANT, pas marginal
Formule (engine.py:290-321) :
`footprint = emprise × coef_occupation` → `SDP = footprint × niveaux` → `SHAB = SDP × coef_rendement` →
`logements = min(SHAB / logt_m2, surface_ha × densite × niveaux)`.
- **`coef_occupation`** est un **multiplicateur linéaire** de toute la chaîne (footprint→SDP→SHAB→logts→
  charge foncière). Une commune dont le règlement fixe l'emprise au sol à 0,30 (au lieu de 0,45) verrait
  **−33 %** sur capacité, SDP, et charge foncière.
- **`densite`** plafonne les logements ; quand le plafond MORD (projets denses), `logements ∝ densite`.
  Densité réelle 20 au lieu de 30 → **−33 %** de logements plafonnés.
Ces deux paramètres ne sont pas des réglages fins : ils déplacent la sortie d'un tiers. Un promoteur lit
une capacité et une charge foncière calées sur Saint-Paul, présentées comme celles de sa commune.

## 5 — Répartition proposée (île-générique vs commune-spécifique)
| paramètre | proposition | justification |
|---|---|---|
| `coef_occupation` | **commune-spécifique** | emprise au sol = règlement par zone/commune |
| `densite_logts_ha_par_niveau` | **commune-spécifique** | plafond de densité (ex-COS) = règlement |
| `etage_m` | **île-générique** | un niveau ≈ 3 m partout (physique) |
| `coef_rendement` | **île-générique** | SDP→habitable = technique de construction, non réglementaire |
| `coef_plancher_habitable` | **île-générique** | idem (murs/gaines) |
| `logement_m2_bas/haut` | **île-générique** | surface moyenne de logement = marché, pas règlement |
| `place_m2` | **île-générique** (à surveiller) | norme stationnement (peut varier au règlement — à confirmer) |
| `cout_construction`, `marge_promoteur`, `frais_annexes`, `dvf_*` | **île-générique** | économiques, déjà audités O2 (Estimé) |

### Le correctif de CHEMIN (factuel, Phase 1 — je le fais après GO)
1. Sortir les paramètres île-génériques de `plu_saint_paul.yaml` (et du défaut dataclass) vers une source
   **neutre nommée** `config/hypotheses_ile.yaml` → ils cessent de s'appeler « Saint-Paul par défaut ».
2. `coef_occupation` + `densite` : tant qu'une commune n'est pas calibrée à son règlement, la sortie
   DOIT le DIRE — « hypothèse générique, non calibrée pour cette commune » (Estimé), le marquage
   voyageant AVEC la valeur (helper unique → fiche + faisabilité + assemblage + 5 PDF), jamais un chiffre
   présenté comme local. **La calibration des valeurs réelles par commune = Vic.**

## Décision demandée à Vic (STOP)
1. Valider la **frontière** proposée (§5) : `coef_occupation` + `densite` = commune-spécifique ; le reste
   île-générique.
2. Autoriser le **correctif de chemin** (Phase 1 factuelle) : extraction vers `hypotheses_ile.yaml` +
   marquage « générique, non calibrée » sur `coef_occupation`/`densite` des 12 communes non calibrées.
3. La **calibration** des densités/emprises réelles par commune (mesure du règlement) reste à toi —
   je ne fixe aucune valeur de ma propre initiative.
