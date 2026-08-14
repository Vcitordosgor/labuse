# PRE_VOL_ILE — Le chemin de résolution des hypothèses de faisabilité (M-PLU-REF)

> Comme le recalage DVF de M79, ce document fige le nouveau chemin après correction de la référence
> Saint-Paul gelée. **Correction de CHEMIN, pas de calibration** : aucune valeur n'a bougé (golden = baseline).

## Avant (le biais)
Les hypothèses de faisabilité de Saint-Paul (`coef_occupation 0,45`, `densite 30/niveau`,
`coef_rendement 0,80`, coûts, marge…) étaient la valeur **universelle** : copiées dans les 12 YAML
communaux ET posées comme défauts du dataclass `Hypotheses`. Une commune obtenait Saint-Paul des deux
côtés ; les paramètres île-génériques s'appelaient « Saint-Paul par défaut » ; la constructibilité
empruntée était présentée comme locale. 53 % des parcelles concernées.

## Après (le chemin corrigé)
`Hypotheses.charger(commune)` (faisabilite/engine.py) résout dans cet ordre :

1. **BASE île-générique** ← `config/hypotheses_ile.yaml` (source NEUTRE nommée, `_hypotheses_ile()`).
   Contient les params qui ne dépendent PAS d'un règlement : `etage_m`, `coef_rendement`,
   `coef_plancher_habitable`, `logement_m2_bas/haut`, `cout_construction_m2_bas/haut`,
   `marge_promoteur_pct`, `frais_annexes_pct`, `dvf_radius_m`, `dvf_min_ventes`. Ils ne s'appellent
   plus « Saint-Paul ».
2. **OVERRIDE commune** ← section `hypotheses_faisabilite` du YAML de la commune (`_hypotheses_faisabilite`).
   Porte les params COMMUNE-SPÉCIFIQUES (issus du règlement) : `coef_occupation`,
   `densite_logts_ha_par_niveau`, `place_m2` — plus toute valeur qu'une commune calibre.
3. **Params économiques** (cout/marge) : en plus, `bilan_params` (registre ← global `'*'` ← secteur).

## Le marquage (doctrine Sourcé / Estimé / Absent)
La constructibilité (emprise au sol + densité) est **Sourcée** SEULEMENT si la commune DÉCLARE
`constructibilite_source_ref` dans son YAML (ex. Saint-Paul : « Règlement PLU Saint-Paul »). Sans cette
clé, les valeurs sont **génériques (île), non calibrées** pour la commune → la sortie l'écrit :
« ⚠ Emprise au sol et densité : hypothèse GÉNÉRIQUE (île), non calibrée au règlement de {commune}… (Estimé) ».

**Un critère = un seul endroit** : le marquage est ajouté UNE fois, dans la liste `hypotheses` de
`estimate_capacity` (engine.py), commune-aware (`hyp.constructibilite_source_ref` / `hyp.commune`). Il
voyage donc avec la valeur — la fiche, la faisabilité, l'assemblage et les 5 PDF rendent cette liste,
personne ne rajoute la mention à la main. Même doctrine que `mixite_source_ref` (M-N P1-13).

## Ce qui reste à Vic (CALIBRATION, pas correction)
Établir les **valeurs réelles** de `coef_occupation` / `densite` / `place_m2` par commune (mesure du
règlement graphique/écrit). Tant qu'une commune n'est pas calibrée + ne déclare pas
`constructibilite_source_ref`, sa sortie reste marquée « générique ». `capacité ∝ coef_occupation ×
densité` (linéaire) : l'écart au règlement réel est structurant (±33 % mesuré pour ±10 de densité).

## Suivi (mécanique, non fait ici)
Les 12 YAML communaux contiennent encore les COPIES redondantes des params île-génériques (mêmes
valeurs → sans effet, `hypotheses_ile` étant la base). Un ménage ultérieur peut les retirer pour que
`hypotheses_ile.yaml` soit la source unique visible. Aucune urgence (aucun effet de calcul).
