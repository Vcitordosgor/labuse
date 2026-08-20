# M127-BIS — LES TROIS RÉPARATIONS : RE-EXAMEN (STOP)

*Branche `exp/m127bis-reparations` (empilée sur exp/m127). Même protocole, même métrique, même
fold : **RR@1158 hors copro, fold 2025, référence 6,73**. Sorties : `reports/m127bis/`.
Rien de servi n'a bougé.*

---

## PREMIÈRE LIGNE

**Toujours pas de promotion : la meilleure échelle (C, +features bâti) fait 6,50 (−3,4 % vs 6,73,
IC [5,3-7,5] — indistinguable statistiquement, mais sous la barre au point).**
**MAIS la réparation 3 a fait ce qu'on lui demandait : le segment bâti remonte de 5,85 → 6,48
(+11 %)** — c'est le chiffre qui compte pour le vivier M129. Détail et recommandation ci-dessous.

## L'ÉCHELLE COMPLÈTE (RR@1158 hors copro ; ancre A re-mesurée dans le même cadre)

| Fold | A · ancre (22) | B · +causes cat | C · +bâti | D · +proc daté | Réf. servie |
|---|--:|--:|--:|--:|--:|
| 2020 | 9,36 | 9,52 | 9,09 | 9,41 | 9,41 |
| 2021 | 8,97 | 8,97 | 8,79 | 8,92 | 8,61 |
| 2022 | 8,63 | 8,54 | 8,49 | 8,45 | 8,63 |
| 2023 | 7,40 | 7,35 | 7,40 | 7,30 | 7,30 |
| 2024 | 6,96 | 6,67 | **7,49** | 7,37 | 7,08 |
| **2025** | **6,44** | 5,93 | **6,50** | 6,38 | **6,73** |

**Segments fold 2025 (nu / bâti, k proportionnel)** :

| Échelle | nu | bâti |
|---|--:|--:|
| A | 9,66 | 5,85 |
| B | 9,50 | 5,40 |
| **C** | 8,57 | **6,48** |
| D | **9,81** | 6,30 |

## Verdict par réparation

**R1 — propriétaire historisé : infaisable aujourd'hui, mesuré.** `date_prise_fonction` couvre
**2 %** (458/23 095) ; `pm_millesimes` absente. Seul `proc_collective` (événement BODACC daté
2008+) a concouru — **il n'apporte rien de mesurable** (D 6,38 ≈ A 6,44 ; TRUE = 5 618
parcelle-années, trop rare pour bouger un RR@1158). Les 3 instantanés (âge, succession, PM nue)
ne concourent pas — **faits affichés / bonus cascade, comme la dalle le prescrit**. Pour les faire
concourir un jour : **ingérer l'historique RNE des dirigeants** (mandat dédié).

**R2 — causes en catégories : RÉFUTÉE.** B fait **5,93** (−0,51 vs A) — pire que les zéros nus du
M127 sur ce cadre. Ni le zéro plat ni la cause-catégorie ne récupèrent l'information du « trou »
v1 : l'ABSENCE de ligne était un proxy compact de « parcelle écartée par la cascade » que le
modèle exploitait tel quel ; l'expliciter fragmente le signal. **Conclusion ferme : au modèle, le
résiduel reste à l'état v1 (troué) jusqu'à compréhension ; la vérité M125 (zéros + causes) reste
acquise pour la fiche, la cascade et les facettes — elle n'a jamais été faite pour le modèle.**

**R3 — features bâti : LA réparation qui marche.** C gagne le fold 2024 (**7,49**, meilleur de
tout M127+bis, réf 7,08) et remonte le **segment bâti de 5,85 → 6,48 (+11 %)** avec la meilleure
calibration de l'examen (ECE 0,0009). Prix payé : le nu descend (9,66 → 8,57) — le modèle
réalloue sa capacité. Sur LA métrique (6,50 vs 6,73) : pas suffisant pour promouvoir.

## Les poids du meilleur modèle (C, fold 2025 — `model-card-C_bati-2025.csv`)

Les entrantes bâti pèsent : `taux_occupation`, `nb_batiments`, `usage_dominant` et
`pct_potentiel_v2` prennent des amplitudes matérielles (détail au CSV) — le signal bâti existe,
il était simplement absent du modèle. `hauteur/étages/logements` (couverture 54-66 %) apportent
peu au-delà.

## Recommandation (la décision est à Vic)

1. **NE PAS PROMOUVOIR** — la règle de la dalle est claire (« remplace si et seulement si la note
   dépasse 6,73 dans les mêmes conditions ») : 6,50 ne la passe pas. La référence servie reste.
2. **Ce que M127+bis a établi de solide** : la référence est au PLAFOND de la donnée actuelle sur
   le fold 2025 — sept variantes sérieuses (nettoyage, zéros, causes, bâti, propriétaire daté,
   pondération, GBM) atterrissent toutes à 5,4-6,7. Le levier n'est plus dans la mécanique ni
   dans ces features-là.
3. **Garder C_bati au chaud pour M129** : quand le vivier intègre les 181 k bâties, le modèle qui
   les juge 11 % mieux (6,48 vs 5,85) à calibration égale devient le bon candidat — l'examen de
   promotion se rejouera à ce moment-là, sur un univers qui ressemblera au produit.
4. **Deux mandats de donnée AVANT tout nouvel examen** : (a) l'historique RNE des dirigeants
   (débloque les signaux propriétaire comme features datées) ; (b) le cadastre multi-millésimes
   (débloque division_recente). Sans donnée neuve, re-examiner ne changera rien — c'est la leçon
   des deux examens.
5. Résiduel : v1 au modèle, vérité M125 partout ailleurs (cf. R2).

---

*Interdits respectés : rien promu, métrique/fold inchangés, aucune feature propriétaire non
historisée n'a concouru (proc = événement daté, lien-snapshot consigné), résultats décevants en
première ligne. Sorties : echelle-bis.csv, segments-bis-2025.csv, model-card-C_bati-2025.csv,
artifact-m127bis-C_bati-fold2025.joblib (artefact d'EXAMEN, jamais servi), manifest-bis.json.*
