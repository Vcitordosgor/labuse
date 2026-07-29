# MANDAT « TÊTE DE LISTE NON CONSTRUCTIBLE » — SPEC

> **Statut : SPEC — mesure faite, rien implémenté. Passe DEVANT le re-run et le repli (arbitrage
> Vic 29/07).** Défaut produit PRÉSENT, indépendant de toute correction en cours : le produit
> classe en tête de liste (brûlante/chaude) du foncier que le moteur de faisabilité déclare
> NON CONSTRUCTIBLE. Découvert via le cas AD1237 (phase 1 re-run).

---

## 1. Le défaut, mesuré sur l'état SERVI (`q_v7_defisc`, lecture seule)

Sur les 1 151 parcelles servies en tête de liste (120 brûlantes + 1 031 chaudes), la faisabilité
(`parcel_faisabilite`, YAML courants) déclare **73 NON CONSTRUCTIBLES** :

| Tier | Non constructible | Total | Part |
|---|---:|---:|---:|
| **brûlante** | **2** | 120 | 1,7 % |
| **chaude** | **71** | 1 031 | 6,9 % |

Distinction faite proprement : les parcelles **constructibles à résiduel 0** (déjà bâties → mutation
légitime, P prédit une vente, PAS un défaut) sont EXCLUES du compte. Les 73 sont bien du foncier où
le règlement calibré interdit toute construction neuve.

- **2 brûlantes** : `97407000AS1056` (Le Port), `97422000AD1237` (Le Tampon, 2AUd — la golden du
  mandat repli).
- **71 chaudes** sur 16 communes : Saint-Pierre 11, Saint-Paul 10, Saint-Joseph 9, Le Tampon 8,
  Les Trois-Bassins 8, Le Port 7, Sainte-Marie 7, La Possession 4, Saint-Benoît 2, autres 1.
- **Zones** : gels (2AUb, 2AUe, 2AUd, 2AUc, AU3st, AU1st…), interdits calibrés éco (Ue, Up, UAa),
  et **15 « U » + variantes** non constructibles au règlement mais servies chaudes.

**Non trivial** : 73 parcelles en tête de liste client sans capacité constructible. Défaut à
corriger indépendamment du re-run et du repli.

## 2. Cause racine (par le maillon)

Une parcelle non constructible atteint un tier chaud parce que **l'étage 0 / la cascade ne lit
jamais la non-constructibilité** avant que le modèle P ne la score :
- La cascade classe sur le **subtype** (U/AU → positive, `phase1.py:251`).
- M6 2b n'exclut que `calibree AND habitat=="interdit" AND recouvrement≥90 %` — elle rate les gels
  (`constructible_neuf=False`) et les non-constructibles calibrés sans habitat=interdit explicite.
- `constructible_neuf` n'est lu NULLE PART dans cascade/ ni scoring/.
- Donc la parcelle n'est pas écartée → elle entre au scoring P → tier chaud possible.

C'est le même point d'étranglement que le repli non optimiste, vu du produit servi : **le
déclassement doit se faire en étage 0 (cascade), jamais par le canal résiduel** (phase 1 re-run :
le résiduel est un CONTRE-levier — mettre la SDP à 0 fait MONTER le score P).

## 3. Correctif candidat (à mesurer, PAS implémenté)

Ajouter en étage 0 une exclusion honorant le verdict de faisabilité : **une parcelle dont
`parcel_faisabilite` conclut non constructible (r is None, `not constructible_neuf`, ou
`habitat=="interdit"`) au-delà d'un seuil de recouvrement ne peut pas scorer positive.** Détecter
le gel par `calibree=True` + famille de zonage (leçon gravée : jamais `constructible_neuf` seul,
sinon 21 077 faux positifs / 13 golden — cf. `REPLI_NON_OPTIMISTE_PHASE_A_MESURE.md`).

## 4. Mesures BLOQUANTES avant tout correctif (au même rang que d'habitude)

1. **Ampleur exacte** : les 73 sont le plancher (brûlante/chaude). Étendre à réserve_foncière et
   à_creuser (une non-constructible en réserve reste un faux positif servi). Par commune, par tier.
2. **Tiers** : retirer ces positives re-classe le champ (rang global) → mesure de la matrice de
   transition, golden 116 avant/après. Un tier de tête qui se vide = arbitrage Vic.
3. **Recouvrement** : seuil (≥90 % comme M6 2b ? ou verdict binaire de faisabilité ?) à trancher —
   une parcelle à cheval sur du constructible et du gelé n'est pas un pur faux positif.
4. **Convergence avec le repli** : ce correctif EST le levier du repli non optimiste (déclassement
   des gels par l'étage 0). Un seul correctif, mesuré une fois, sert les deux mandats.

## 5. Séquencement (arbitrage Vic 29/07)

Ce mandat **passe devant**. Ordre acté : **(1) ce défaut tête-de-liste non constructible → (2)
re-dérivation du barème `residuel_socle` → (3) mesure du canal cascade (déclassement gels) → (4)
re-run complet post-calibration.** Le repli non optimiste reprend porté par (1)+(3).

*Artefacts : `/tmp/repli_nullcap.txt` (73 nominatives) ; mesure `parcel_faisabilite` sur les 1 151
tête de liste servies, lecture seule.*
