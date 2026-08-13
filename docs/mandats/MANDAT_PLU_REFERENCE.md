# M-PLU-REF — La référence Saint-Paul figée pour les hypothèses de constructibilité

> Mandat dédié, issu du diagnostic M79 (dette de méthode signalée par Vic). **Écrit, NON lancé.**
> Même biais que le DVF (M79) appliqué aux **hypothèses de constructibilité/faisabilité** : une
> référence figée sur UNE commune (Saint-Paul), calée quand elle était le seul territoire calibré,
> qui n'a plus le même sens depuis que 23/24 communes sont couvertes.

## Précondition git
```
cd ~/Desktop/labuse && git status         # propre, sur main
git branch --show-current                 # DOIT afficher « main » — sinon STOP
git pull && git checkout -b feat/plu-ref
git branch --show-current                 # DOIT afficher « feat/plu-ref »
```
**Vérifier `git branch --show-current` en tête ET avant chaque commit — bloquant** (incidents M73/M79 ;
voir la mémoire `feedback-verif-branche-avant-commit`).

## Le constat qui déclenche ce mandat
**12 communes** lisent les **hypothèses GLOBALES de `config/plu_saint_paul.yaml`** (bloc
`hypotheses_faisabilite`) au lieu des leurs : `bras_panon, cilaos, le_port, le_tampon,
la_plaine_des_palmistes, les_avirons, les_trois_bassins, petite_ile, saint_benoit, saint_denis,
saint_louis, saint_pierre`. Le moteur de faisabilité (`src/labuse/faisabilite/`) en tire :
`coef_rendement` (0.80), `densite_logts_ha_par_niveau` (30), `cout_construction_m2` (2300–2800),
`marge_promoteur_pct` (0.09), etc. Certains de ces paramètres sont **île-génériques** (coûts de
construction, marge promoteur — défendables en commun) ; d'autres touchent la **constructibilité
même** (densité, rendement) et **devraient venir du règlement de chaque commune**. C'est cette
frontière que la Phase 0 doit tracer avec des chiffres.

## PHASE 0 — Mesure de l'écart (STOP obligatoire)
Ne rien corriger. Mesurer, sur les 12 communes :

1. **Inventaire précis** : quels paramètres exacts chaque commune emprunte à Saint-Paul (vs ce qu'elle
   surcharge déjà), et **par quel chemin de résolution** (repli registre ← global `'*'` ← secteur —
   cf. `bilan_params.py`). Distinguer nettement **hypothèses ÉCONOMIQUES** (coûts, marge : plausiblement
   île-génériques) des **hypothèses de CONSTRUCTIBILITÉ** (densité, rendement, hauteur/emprise par zone :
   commune-spécifiques par nature).

2. **L'écart au règlement réel** : pour les paramètres de constructibilité, comparer la valeur
   Saint-Paul empruntée à la valeur RÉELLE du règlement de la commune (règlement PLU graphique/écrit,
   OAP, densités autorisées par zone). Où l'écart est-il significatif ? Chiffrer (ex. densité
   Saint-Paul 30 logts/ha/niveau vs densité réelle commune X).

3. **Combien de parcelles affectées** : par commune, combien de parcelles voient leur
   faisabilité/capacité/bilan calculés avec un paramètre emprunté à Saint-Paul plutôt qu'au règlement
   local. Distribution sur le parc de ces 12 communes.

4. **L'effet sur la sortie client** : sur un échantillon, de combien la capacité (logements, SDP) et le
   bilan (charge foncière) bougent si on substitue le paramètre réel de la commune au paramètre
   Saint-Paul. Est-ce marginal ou structurant ?

5. **Le vrai correctif** : pour chaque paramètre, trancher s'il doit être **île-générique explicite**
   (alors le SORTIR de `plu_saint_paul.yaml` vers un `config/hypotheses_ile.yaml` neutre, pour qu'il ne
   soit plus « la valeur de Saint-Paul » par accident) ou **commune-spécifique** (alors le calibrer par
   commune, comme la calibration PLU premium). Proposer la répartition, chiffrée.

Rapport `RAPPORT_PLU_REF.md`. **STOP.** Vic arbitre au vu de l'écart mesuré avant toute correction.

## PHASE 1 — Correction (après arbitrage)
- Les paramètres île-génériques quittent `plu_saint_paul.yaml` pour une source **neutre nommée**
  (`hypotheses_ile.yaml`) — plus jamais « hérité de Saint-Paul par défaut ».
- Les paramètres commune-spécifiques sont calibrés par commune (ou, à défaut de donnée, la sortie DIT
  « hypothèse générique, non calibrée pour cette commune » — jamais un chiffre présenté comme local
  alors qu'il vient d'ailleurs).
- Documenter le nouveau chemin de résolution dans `PRE_VOL_ILE.md` (comme le recalage DVF de M79).

## Interdits
- Aucun paramètre commune présenté comme « local » alors qu'il vient de Saint-Paul.
- Aucune correction avant que Vic ait vu l'écart mesuré (Phase 0).

## Garde-fous
tsc 0 · vitest vert · pytest sans régression nouvelle · golden = baseline ·
`git branch --show-current` vérifié avant chaque commit · **NE PAS MERGER.**

## Livraison
Commit par phase. `RAPPORT_PLU_REF.md` avec l'inventaire par commune, l'écart au règlement chiffré, le
nombre de parcelles affectées, et la répartition proposée (île-générique vs commune-spécifique).
NE PAS MERGER.
