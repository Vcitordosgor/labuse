# AUDIT M73-E — La mesure réhabilitation (Phase 1, STOP obligatoire)

**Branche `feat/m73e-volet-b`. Aucune écriture d'affichage. Mesuré le 14/08/2026, run servi q_v9_m81.**

## Verdict en une phrase
La réhabilitation est **bien captée pour sa population** (33 897 parcelles déclassées pour cause de
bâti) — elle n'est **ni rare ni mal captée**. Le « 40/40 Non évaluée » de M73-D était un **artefact
d'échantillonnage** : les 40 parcelles étaient tirées par `emprise_bati_m2 > 150`, un critère
ORTHOGONAL à la porte d'entrée du mode B (le *tier*), donc presque toutes hors population.

## 1 — Combien de `mode_b` disponible ? (run servi q_v9_m81)

La porte d'entrée de `compute_mode_b` (bilan.py:792) est **`tier ∈ MODE_B_TIERS`** =
`{declasse_bati_sature, declasse_bati_revele}` (M33 : le mode B est RÉSERVÉ aux parcelles déclassées
pour cause de bâti — saturé ou révélé). Hors de ces tiers → `disponible=False`, motif « hors population
mode B » → l'écran affiche « Non évaluée ».

| population | parcelles | % du parc |
|---|---|---|
| **Population mode B** (declasse_bati_sature 29 883 + declasse_bati_revele 4 014) | **33 897** | **7,85 %** |
| Hors population (autres tiers) | 397 766 | 92,15 % |
| *Total* | *431 663* | *100 %* |

**Portes suivantes, sur la population :**
- emprise bâtie ≥ 20 m² (`p_model_bati`) : **33 897 / 33 897** (toutes — logique : elles sont déclassées
  POUR leur bâti) ;
- prix de sortie bâti local (`_prix_bati_local`, DVF secteur n≥3 → repli commune) : docstring « None
  hors mesure P0 : 0 cas » → passe quasi partout ;
- SHAB ≥ 50 m² (`MODE_B_SHAB_MIN`) sinon `trop_petit` (disponible=True, motif dit).

**Mesure empirique** (10 parcelles tirées DANS la population, via l'API, run servi) :

| état mode_b | n / 10 |
|---|---|
| disponible, bilan complet (montant servi) | **8** |
| disponible, `trop_petit` (SHAB < 50, DIT) | 2 |
| « Non évaluée » (hors population) | **0** |

→ Dans sa population, **~80 % ont un bilan de réhabilitation complet**, ~20 % `trop_petit`, **0 %**
« Non évaluée ». La capture fonctionne.

**Ventilation par commune (population mode B, top) :** Saint-Paul 7 067 · Saint-Pierre 3 537 ·
Saint-André 3 079 · Saint-Leu 2 943 · Saint-Joseph 2 805 · Saint-Denis 1 991 · Le Tampon 1 980 ·
La Possession 1 497. Bien réparti, pas un artefact d'une commune.

## 2 — Les 40 parcelles du test étaient-elles représentatives ?
**Non.** M73-D les a tirées par `SELECT … JOIN parcel_residuel_bati WHERE emprise_bati_m2 > 150`, sans
filtrer sur le *tier*. Or 92 % du parc est hors population mode B — un tirage par emprise tombe presque
toujours dans `ecartee`/`a_creuser`/autres → « hors population » → « Non évaluée ». Le tirage a porté
sur un segment **défavorable par construction**, pas sur la population du mode B.

## 3 — Quelle condition fait basculer en « Non évaluée » ?
**Un seul et unique filtre : `tier ∉ MODE_B_TIERS`** (bilan.py:792-795). Ce n'est **ni** une absence de
donnée, **ni** un filtre trop strict accidentel, **ni** un défaut de branchement : c'est le **périmètre
métier assumé du mode B** (M33 — la thèse de réhabilitation ne vaut que pour une parcelle déjà bâtie et
déclassée pour cette raison). Pour les 92 % restants, « Non évaluée » est **factuellement correct** :
la réhabilitation ne s'applique pas.

## 4 — Verdict
Le potentiel est **réellement capté**, pour une population précise et substantielle (33 897 parcelles,
7,85 %). Il n'est **pas** mal capté. Le bloc dit un vrai bilan pour cette population et « Non évaluée »
(à raison) pour le reste.

## Décision demandée à Vic (STOP)
Le bloc n'est PAS cassé — mais il affichera « Non évaluée » sur ~92 % des fiches (là où la réhab ne
s'applique pas). Question de fond, pas de captage :
1. **Garder tel quel** — honnête, mais « Non évaluée » très fréquent (le mandant parle de « bruit »).
2. **Reformuler le motif hors-population** en clair — p. ex. « Réhabilitation : sans objet (parcelle non
   déclassée pour cause de bâti) » au lieu de « Non évaluée » — plus informatif, toujours affiché, ne
   masque rien. *(Reformulation de libellé, pas de la logique — le calcul ne bouge pas.)*
3. **N'afficher le bloc que pour la population mode B** — mais cela **masque** un bloc, ce que la
   doctrine interdit. Déconseillé.

*Reco : option 2 (reformuler le libellé hors-population, jamais masquer).* Après arbitrage, j'enchaîne
les Phases 2 (comparables premium) et 3 (plan) du mandat.
