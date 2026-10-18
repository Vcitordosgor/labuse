# FIX-PRIX-ET-OPPORTUNITES — lot 2 : diagnostic des permis au-dessus de la capacité LABUSE

**Lecture seule. Aucune règle n'a été modifiée.** Ce document classe les deux gisements signalés par
VERITE-TERRAIN-2 volet D et chiffre, pour les erreurs réelles, la correction proposée et le nombre de
parcelles concernées. **STOP ensuite : Vic décide des règles avant toute modification.**

Source : `docs/audit-2026-10/verite-terrain-2/PERMIS-VS-CAPACITE.csv` (6 601 permis post-PLU comparés à
la capacité servie q_v19). Reproductible : `PYTHONPATH=src python scripts/diagnostic_opportunites_lot2.py`
→ `CLASSIFICATION-LOT2.csv` (une ligne par permis, famille + détail).

## Les deux gisements (rappel)

| Gisement | n | ce que dit LABUSE |
|---|--:|---|
| **densité > calibrage** | 913 | parcelle servie, capacité positive mais l'autorisé la **dépasse** |
| **non constructible** (« rédhibitoire ») | 418 | capacité **nulle** alors qu'un permis logements a été autorisé |

## Méthode de classement — et sa limite d'honnêteté

Deux des quatre familles demandées sont **observables** dans la donnée :
- **réunion de parcelles** : `n_parcelles > 1` (somme des capacités incomplète si des parcelles ont
  disparu, ou gabarit mutualisé sur foncier regroupé) ;
- **antérieur au PLU** : date d'autorisation ≤ **12 mois** après l'entrée en vigueur du PLU → le projet a
  presque sûrement été **déposé/instruit sous l'ancien règlement** (l'instruction d'un PC prend des mois).
  Sensibilité donnée à 6 et 24 mois.

Les deux autres ne le sont **pas** directement : **la « dérogation » n'est pas un champ Sit@del.** Elle se
cache, avec l'erreur réelle de calibrage et le redécoupage foncier, dans le **résidu mono-parcelle bien
postérieur au PLU**. On le **sépare par des indices mesurables** (ampleur du dépassement, sous-cause de
non-constructibilité, famille de zone) **sans jamais affirmer une dérogation qu'on ne peut prouver** : les
familles « dérogation ou … » sont des **bornes hautes**, pas des certitudes.

---

## 1. Gisement « densité > calibrage » (913)

| Famille | permis | parcelles IDU | lecture |
|---|--:|--:|---|
| **erreur réelle LABUSE** (gabarit trop bas, ratio 1,2–2) | **372** | **372** | le max modélisé est sous le réel |
| antérieur au PLU (≤12 mois) | 201 | 252 | ancien règlement — pas la calibration actuelle |
| réunion de parcelles (toutes servies) | 124 | 271 | gabarit mutualisé > somme unitaire — grain |
| dérogation ou densité réelle (ratio 2–3) | 105 | 105 | ambigu — dérogation ou densité réelle > gabarit |
| dérogation ou bruit (ratio ≤1,2) | 66 | 66 | dans le bruit de conversion SDP (coef 1,15) |
| dérogation ou redécoupage (ratio >3) | 45 | 45 | écart très fort — foncier redécoupé probable |

**Erreur réelle = 372 parcelles, très concentrées :** Saint-Leu **260** (zone **UD 205**, UC 51), loin
devant Saint-Pierre (27), Saint-André (25). Ce n'est **pas** un défaut systémique du moteur : c'est un
**calibrage de gabarit trop bas sur quelques zones**, au premier rang **Saint-Leu UD** (PLU 2007, le plus
ancien). Un permis mono-parcelle, bien postérieur au PLU, qui bâtit 1,2 à 2× le **maximum** que LABUSE
sert, signale que la hauteur/emprise modélisée de la zone est **sous** la règle réelle.

> **Correction proposée (à décider) :** re-lire au règlement et recalibrer le gabarit (hauteur, emprise,
> et le cas échéant la densité) des zones concernées, **en priorité Saint-Leu UD puis UC**. Changerait les
> **372 parcelles-témoins** directement ; par extension, **toutes les parcelles de ces zones** (gisement
> plus large, à chiffrer par un run — non fait ici, lecture seule).

---

## 2. Gisement « non constructible / rédhibitoire » (418)

| Famille | permis | parcelles IDU | lecture |
|---|--:|--:|---|
| dérogation ou exception | 145 | 145 | zone A/N (94), rédhibitoire non urbain (48), PPR/ER (3) |
| **erreur réelle LABUSE** | **133** | **133** | terrain_exigu (46) + rédhibitoire **urbain** (87) |
| antérieur au PLU (≤12 mois) | 95 | 112 | souvent **dézoné** depuis : constructible hier, A/N/rédhibitoire aujourd'hui — LABUSE a raison |
| réunion de parcelles | 45 | 99 | 31 à somme incomplète + 14 mutualisées — grain |

L'erreur réelle (133 parcelles) se scinde en **deux corrections distinctes** :

**2a — seuil `terrain_exigu` trop strict : 46 parcelles** (34 en zone U). Un permis logements a été
autorisé sur une parcelle que LABUSE déclare trop petite. Communes : Saint-Leu 16, Saint-André 12…
> **Correction proposée :** relâcher le seuil `terrain_exigu` (taille minimale / noyau usuel), dans la
> lignée de PLU-CALIBRAGE-10 (noyau ramené à 20 m²). Changerait les **46 parcelles-témoins** + le gisement
> complet des parcelles aujourd'hui `terrain_exigu` (à chiffrer par un run).

**2b — exclusion « rédhibitoire » trop agressive en zone URBAINE : 87 parcelles.** LABUSE exclut
totalement des parcelles **urbaines** (Ub 31, UC 23, UD 9…) où un permis logements a bien été accordé.
Communes : Saint-Benoît 26, Saint-Leu 17, Sainte-Rose 12. **La cause servie est générique (« rédhibitoire »)
et ne nomme pas la règle déclenchée** (PPR ? accès ? pente ? servitude ?).
> **Correction proposée :** identifier, via le **détail cascade** de ces 87 parcelles (nécessite la base,
> non fait ici), **quelle** règle rédhibitoire les exclut, puis juger si elle est trop large en zone U.
> Borne haute : **87 parcelles**.

Le reste (**dérogation ou exception, 145**) n'est **pas** corrigeable par calibrage : zone A/N (94) =
exception agricole/STECAL **ou** donnée de zonage à vérifier au cas par cas ; rédhibitoire non urbain (48)
et PPR/ER (3) = plutôt légitimes.

---

## 3. Synthèse chiffrée

| | réunion | antérieur PLU | dérogation / exception / ambigu | **erreur réelle LABUSE** |
|---|--:|--:|--:|--:|
| densité > calibrage (913) | 124 | 201 | 216 | **372** |
| non constructible (418) | 45 | 95 | 145 | **133** |
| **total (1 331)** | **169** | **296** | **361** | **505** |

**Erreurs réelles = 505 parcelles-témoins**, en **trois corrections** indépendantes à arbitrer :

| # | correction proposée | parcelles-témoins | priorité / concentration |
|---|---|--:|---|
| A | recalibrer le gabarit (hauteur/emprise) des zones sous-calibrées | **372** | **Saint-Leu UD (205)** + UC (51) |
| B | relâcher le seuil `terrain_exigu` | **46** | Saint-Leu 16, Saint-André 12 |
| C | resserrer l'exclusion « rédhibitoire » en zone U (règle à nommer d'abord) | **87** | Saint-Benoît 26, Saint-Leu 17 |

Les « parcelles-témoins » sont les parcelles des permis observés ; le **gisement complet** que chaque
correction ferait bouger (toutes les parcelles des zones/seuils concernés, pas seulement celles ayant eu un
permis) **se chiffre par un run** — non fait ici (lecture seule).

## 4. Sensibilité & limites

- **Seuil « antérieur au PLU »** (permis ≤ N mois du millésime) : densité 105 / 189 / 292 à 6 / 12 / 24
  mois ; non constructible 49 / 97 / 180. À 24 mois, une partie du résidu « erreur réelle » bascule en
  « antérieur » — la borne d'erreur réelle est donc **plutôt haute** à 12 mois.
- **Dérogations non observables** : aucune certitude, seulement des bornes (familles « dérogation ou … »).
- **SDP habitable → plancher** (coef 1,15) : le ratio densité est **légèrement conservateur** (il tend à
  sous-dire les dépassements) — l'erreur réelle « gabarit trop bas » est donc, si biais il y a, **sous**-estimée.
- **Capacité = SDP max** (gabarit), pas résiduelle : on teste ce que la parcelle peut porter au total.
- **Cause « rédhibitoire » générique** : le CSV ne nomme pas la règle exacte → la correction C exige
  d'abord une lecture du détail cascade (base).

## STOP

Diagnostic terminé. **Aucune règle modifiée.** Les trois corrections (A gabarit, B terrain_exigu,
C rédhibitoire urbain) attendent la décision de Vic avant toute implémentation.
