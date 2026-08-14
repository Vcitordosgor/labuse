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
**M-PLU-REF-B (correction du marquage)** : la mesure (AUDIT_PLU_REF_B) a montré que le marquage initial
était FAUX PAR EXCÈS. L'emprise au sol RÉGLEMENTAIRE (`rules.emprise_sol_pct`) est captée par zone —
**64 % chiffrées** (Sourcé, consommées par le moteur l.255), **35 % explicitement « non réglementées »**
(silence documenté). `coef_occupation` (0,45) est un facteur de MODÉLISATION appliqué EN PLUS, sans
équivalent réglementaire ; aucune commune n'a de densité réglementaire (le 30 est un filet ex-COS). Le
flag commune `constructibilite_source_ref` a donc été RETIRÉ (il sonnait même sur une zone chiffrée).

Le marquage est désormais **ZONE-AWARE et VRAI**, dans la liste `hypotheses` de `estimate_capacity`
(écrit UNE fois, voyage avec la valeur) :
- zone à emprise **chiffrée** → **Sourcé** (l'étape « emprise bâtie » cite `surface × emprise%`), aucune
  mention « générique » ;
- zone à emprise **non réglementée** → « Emprise au sol non réglementée par le PLU de {commune} (silence
  du règlement) : occupation du gabarit ~45 % par hypothèse de modélisation ; capacité bornée par reculs,
  hauteur, pleine terre » ;
- densité → « filet de MODÉLISATION (ex-COS) — le PLU ne fixe aucune densité ».

## Ce qui reste à Vic (CALIBRATION, pas correction)
Presque rien : l'emprise réglementaire est déjà captée (99 % chiffrée ou silence documenté). Restent **2
zones** null-sans-source à préciser (**Saint-Paul U1lec + AU5e**, `emprise_sol_pct='a_verifier'`) et
l'extraction chiffrée m²/place du **stationnement** (norme en ratio texte partout — autre mandat). `capacité
∝ coef_occupation ×
densité` (linéaire) : l'écart au règlement réel est structurant (±33 % mesuré pour ±10 de densité).

## Suivi (mécanique, non fait ici)
Les 12 YAML communaux contiennent encore les COPIES redondantes des params île-génériques (mêmes
valeurs → sans effet, `hypotheses_ile` étant la base). Un ménage ultérieur peut les retirer pour que
`hypotheses_ile.yaml` soit la source unique visible. Aucune urgence (aucun effet de calcul).
