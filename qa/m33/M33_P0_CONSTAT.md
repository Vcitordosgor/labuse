# M33 — Phase 0 : POPULATION MODE B, SURFACE RÉHABILITABLE, MESURE Q6

**Branche `m33-mode-b-rehabilitation` · base main 2097ad68 · LECTURE SEULE** (requêtes SQL,
aucune écriture, aucun tier touché). STOP en fin de phase — arbitrage Vic requis.

## 1 · Population proposée

Clarification préalable des effectifs (les « 8 031 » du cadrage mélangent deux choses) :
le TIER `declasse_bati_revele` = **4 051** parcelles (bande règle CoSIA ≥ 40 m²) ; les
« 8 031 bâties révélées » de M32 = l'ensemble à résiduel corrigé (dont bande adjudication
20-40 m², NON déclassée — servie dans son tier naturel). Le mode B au sens « parcelles
déclassées pour cause de bâti » = 4 051 + 29 907.

| Candidat | Total | Emprise ≥ 20 m² | Zone PLU connue | Prix bâti local (secteur n≥3) | + repli commune | **Complètes** |
|---|---:|---:|---:|---:|---:|---:|
| Bâti saturé | 29 907 | 29 907 (100 %) | 29 218 | 29 610 | **29 907 (100 %)** | **29 218** |
| Bâti révélé | 4 051 | 4 051 (100 %) | 4 000 | 4 010 | **4 051 (100 %)** | **3 961** |

- **Emprise : 100 %** par construction (ces tiers naissent d'une emprise mesurée).
- **Prix de sortie bâti local : 100 %** avec la préséance secteur (n≥3) → repli commune
  (338 parcelles rattrapées — même convention de préséance que le mode A/score_e).
- Le seul manque = **zone PLU inconnue (740 parcelles : 689 saturées + 51 révélées)**.
  Question d'arbitrage : la zone n'est PAS bloquante pour une réhabilitation (bâti existant,
  pas de droit à construire requis) — je propose de la servir en INFORMATIF et de ne PAS en
  faire un critère ABSENT. Selon ta réponse : population = **33 958 (100 %)** ou
  **33 179 (97,7 %)**, ABSENT explicite pour le reste.

**Proposition : population v1 = les DEUX tiers déclassés bâti (33 958), zone informative.**
Les bâties « ordinaires » servies (chaudes bâties marginales, etc.) gardent le mode A —
le mode B est la lecture des parcelles qui n'ont QUE la réhabilitation comme histoire.

## 2 · Surface réhabilitable — grandeur et statut boussole RÉEL

**Grandeur proposée : SDP existante = emprise bâtie × niveaux existants ; SHAB réhabilitable
= SDP / 1,15** (même coefficient plancher→habitable que le mode A — un point de calcul).

| Composante | Source | Statut boussole | Mesuré |
|---|---|---|---|
| Emprise bâtie | max(BD TOPO éd. 2026-06-15, CoSIA PVA 2025) — `p_model_bati` | **Sourcé** (millésimes affichés) | 100 % |
| Niveaux existants | BD TOPO `nombre_d_etages`/`hauteur` quand présents | **Sourcé** : saturé **28 332/29 907 (94,7 %)** · révélé **1 232/4 051 (30,4 %)** | mesuré |
| Niveaux (repli) | placeholder 1 niveau (`niveaux_bati_existant_defaut`) | **Estimé** (prudent — minore la surface) | le reste |
| SHAB (÷1,15) | convention mode A | Estimé (convention) | — |

→ Le statut de la surface réhabilitable est **Sourcé×convention pour ~95 % des saturées**,
**Estimé pour ~70 % des révélées** (CoSIA voit l'emprise, pas la hauteur — cohérent avec la
nature du tier). L'étiquette de fiche doit refléter CE partage, par parcelle.

## 3 · Mesure Q6 — reclassement potentiel (MESURE, rien d'implémenté)

Formule au défaut (conventions mode A : coef CA 0,79 = 1 − marge 9 % − honoraires 12 % ;
VRD 0 comme le batch) : `achat_max = SHAB × prix_bâti_local × 0,79 − SHAB × travaux`.

**Enseignement STRUCTUREL (le plus important de la mesure)** : travaux et CA étant tous deux
proportionnels à la SHAB, **le SIGNE du bilan ne dépend PAS de la parcelle — uniquement du
prix local** : positif ⟺ `prix_bâti_local > travaux/0,79` (ex. 1 899 €/m² à 1 500 de défaut).
Un « bilan mode B positif » au paramètre par défaut est donc un test de MARCHÉ (la commune/le
secteur est-il assez cher pour absorber des travaux), pas un signal parcellaire. La surface ne
joue que sur l'AMPLEUR de l'achat max, jamais sur son signe.

Comptes (parcelles avec emprise ≥ 20 ∧ prix local, « positif » = prix × 0,79 > travaux) :

| Groupe | Total | Mesurables | Positif à 1 200 €/m² | à 1 500 | à 2 000 |
|---|---:|---:|---:|---:|---:|
| Écartées | 354 355 | 231 841 | 213 053 | 180 325 | 103 430 |
| Bâti saturé | 29 907 | 29 610 | 27 609 | **23 326** | 15 682 |
| Bâti révélé | 4 051 | 4 010 | 3 789 | **3 235** | 1 994 |
| Non-constructible | 6 168 | 2 377 | 2 220 | 1 828 | 964 |
| Zone fermée | 2 804 | 1 317 | 1 217 | 1 032 | 599 |
| AU statut inconnu | 210 | 109 | 108 | 101 | 2 |
| AU fermée | 70 | 7 | 7 | 7 | 6 |

**Lecture honnête pour la décision future** : 180 325 écartées « positives » à 1 500 €/m² ne
sont pas 180 325 opportunités — c'est la photographie des marchés au-dessus de ~1 900 €/m².
Un reclassement fondé sur le signe du bilan par défaut reclasserait des communes entières.
Si un jour le mode B doit CLASSER, il lui faudra une dimension parcellaire discriminante
(prix d'acquisition observé, état, pression locale) — hors v1, conforme au cadrage (v1 =
lecture de fiche, 0 tier).

## 4 · Valeur par défaut du paramètre travaux — proposition à arbitrer

Aucune source Réunion fiable (cadrage acté). Fourchette qualitative de la cartographie :
1 200–2 000 €/m². **Proposition : défaut 1 500 €/m², libellé « coût travaux : hypothèse
~1 500 €/m² (ESTIMÉ) — à ajuster selon l'état constaté du bâti », bornes de saisie
500–4 000.** Le tableau Q6 ci-dessus donne la sensibilité du parc à ce choix.

## 5 · Ce que la Phase 1 fera (rappel de périmètre, après ton feu vert)

Extension `bilan.py` (briques mode A réutilisées : coef CA, préséance prix, conventions
d'affichage M36 — fourchette « ~X », étiquettes), ABSENT explicite hors population, panneau
de fiche subordonné au tier (M34 intact), exports/IA cohérents, paramètre non persisté.

---
**STOP — questions d'arbitrage :**
1. Population : les 2 tiers bâti (33 958) — zone PLU informative (option A, reco) ou
   exigée (option B, 33 179 + 740 ABSENT) ?
2. Défaut travaux 1 500 €/m² (bornes 500–4 000) — OK ?
3. Q6 : la mesure te suffit-elle en l'état (aucun reclassement en v1, confirmé) ?
