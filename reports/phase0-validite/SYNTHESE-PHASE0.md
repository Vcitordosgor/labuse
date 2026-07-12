# PHASE 0 — VALIDITÉ DU SIGNAL · Synthèse (12/07/2026, lecture seule)

Cohorte réutilisée telle quelle : `reports/score-v/backtest_cohorte.csv` (20 768 vendues +
83 072 non-vendues, seed 974, V recalculé à T−12 avec signaux datés ≤ T). Recomputs = miroir
exact du moteur daté du backtest (0 écart sur 20 768 vendues re-scorées, sanity vérifiée).
Tous les IC95 : Wilson (taux) et Katz log-ratio (RR exposés vs non-exposés). Aucune écriture
hors `reports/phase0-validite/`. Scripts complets : `annexe/`.

**Correction préalable au mandat** : le « 2,65× (193/364) » de l'extraction était calculé sur
la tranche NON-écartée/non-chaude seulement (binning par statut). Sur la cohorte scorée
entière (n = 91 791), V@T ≥ 1 = 1 798 vendues / 4 953 exposées = 36,3 % [35,0–37,7] vs base
20,2 % → lift 1,82, RR 1,90 [1,83–1,98]. C'est CE chiffre que la Phase 0 décompose.

## LOT 1 — Test acheteur/vendeur

**1.1 MILLESIME_REF = situation au 01/01/2025.** Sources : (a) URL du dataset ingéré
`fichier_des_parcelles_situation_2025_dpts_57_a_976_zip` (data.economie.gouv,
`src/labuse/ingestion/personnes_morales.py:26`) ; (b) colonne `millesime='2025'` sur les
82 701 lignes de `parcelle_personne_morale` (import du 05/07/2026) ; (c) convention DGFiP :
les fichiers des parcelles PM sont « à la situation du 1er janvier » du millésime.
Couverture : 82 701 / 431 663 parcelles avec ligne PM (19,2 %). Cohorte par owner_type :
pp/non-identifiée 82 172 (79,1 %) · pm 9 441 · public 8 937 · bailleur 3 112 · copro 178.

**1.2 Partition** : VENDEUR_CERTAIN = date de vente > 01/01/2025 → **6 269 vendues** (30,2 %) ;
ACHETEUR_PROBABLE = 14 499. T_réf des non-vendues côté VC = 2024-07-15 (médiane VC − 12,
même protocole que le backtest ; négatifs intégralement re-scorés à cette date).

**1.3 Ventilation des vendues V@T ≥ 1** (`lot1_ventilation_vendues_Vpos.csv`, n = 1 798) :

| période | total V≥1 | fam. A | B | C | D | E | pm | pp | copro |
|---|---|---|---|---|---|---|---|---|---|
| ACHETEUR_PROBABLE | 1 386 | 13 | 326 | **1 148** | 1 302 | 0 | 1 337 | 37 | 12 |
| VENDEUR_CERTAIN | 412 | 78 | 154 | 208 | 368 | 0 | 387 | 25 | 0 |

La signature de l'artefact est visible : en période acheteur, 83 % des positifs ont la
famille C allumée (siège ailleurs) et 96 % sont des PM — le profil type de l'ACQUÉREUR
(SCI/structure récente, siège hors commune) lu dans un fichier post-vente.

**1.4-1.5 Lifts recalculés** (`lot1_lifts.csv`) :

| sous-ensemble | exposition | taux exposés [IC95] | base | lift vs base | RR Katz [IC95] |
|---|---|---|---|---|---|
| **VENDEUR_CERTAIN** | V ≥ 1 | 9,9 % [9,0–10,8] | 7,0 % | **1,40×** | **1,44 [1,31–1,58]** |
| VENDEUR_CERTAIN | identitaires A+B+C | 9,9 % [9,0–10,9] | 7,0 % | 1,41× | 1,44 [1,30–1,59] |
| VENDEUR_CERTAIN | actif D+E | 9,6 % [8,7–10,5] | 7,0 % | 1,36× | 1,38 [1,25–1,53] |
| ACHETEUR_PROBABLE | V ≥ 1 | 30,5 % [29,2–31,9] | 15,0 % | 2,04× | 2,17 [2,07–2,27] |
| VC · PM seulement | V ≥ 1 | 9,9 % [9,0–10,9] | 9,1 % (base PM) | **1,09×** | 1,22 [1,05–1,42] |
| VC · PP seulement | V ≥ 1 | 9,5 % [6,5–13,7] | 6,8 % | 1,39× | 1,40 [0,96–2,03] (NS) |

Réserve documentée : même en VC, les attributs de la fiche RNE (siège, état) sont un
snapshot 2026 du VENDEUR — l'identité est propre, ses attributs peuvent avoir bougé.

**Verdict LOT 1 : ni le GO, ni l'effondrement.** Le lift vendeur-certain est **1,44
[1,31–1,58]** — l'IC exclut 1 (signal réel) mais on est très loin du critère « ≥ 2× » : environ
la moitié du lift apparent (2,17 en période acheteur) est de l'artefact. Nuances qui comptent :
(a) A/B/C ne s'allument PAS que côté acheteur (78 A + 154 B + 208 C chez les vendeur-certain) ;
(b) chez les PM, V ≥ 1 n'ajoute presque rien (1,09× vs base PM) — « être une PM » porte déjà
l'essentiel ; (c) le détail par signal (LOT 2) montre que la famille A « cession de fonds »
est très prédictive quand les stacks dirigeant/SCI ne le sont pas.

## LOT 2 — Anatomie des bandes V

**2.1 Effectifs exacts** (cohorte scorée entière, `lot2_bandes.csv`) :

| bande | n | vendues | taux [IC95 Wilson] | lift vs base | RR Katz vs reste |
|---|---|---|---|---|---|
| V = 0 | 86 838 | 16 650 | 19,2 % [18,9–19,4] | 0,95× | 0,53 [0,51–0,55] |
| V 1-7 | 206 | 72 | 35,0 % [28,8–41,7] | 1,74× | 1,74 [1,45–2,10] |
| V 8-24 | 3 025 | 1 375 | **45,5 % [43,7–47,2]** | 2,26× | **2,36 [2,27–2,46]** |
| V 25-49 | 1 692 | 346 | 20,4 % [18,6–22,4] | **1,02×** | 1,02 [0,93–1,12] |
| V ≥ 50 | 30 | 5 | 16,7 % [7,3–33,6] | 0,83× | 0,83 [0,37–1,85] |

(Le « 25-49 : n=104 » du mandat venait du binning par statut ; en pur V la bande pèse 1 692.)

**2.2 Composition** (`lot2_bande_25_49_composition.csv`, 1 692 lignes ; + 8-24 en
`lot2_bande_8_24_composition.csv`) — l'anatomie de la non-monotonicité :

| combo dominant | bande | n | taux de vente |
|---|---|---|---|
| tenure + GEO_AUTRE_COMMUNE | 8-24 | 1 690 | **56,6 %** |
| tenure + GEO_HORS_ILE | 8-24 | 203 | 53,7 % |
| tenure + BODACC_CESSION_FONDS | 8-24 | 97 | **72,2 %** |
| tenure + DIRIGEANT_65 | 8-24 | 322 | 29,2 % |
| tenure + DIRIGEANT_70 | 25-49 | 356 | 22,2 % |
| tenure + DIRIGEANT_75 | 25-49 | 352 | 17,0 % |
| tenure + SCI_DORMANTE | 8-24 | 273 | 12,5 % |
| tenure + CESSATION | 25-49 | 57 | 7,0 % |

Lecture : les points ÉLEVÉS de V sont portés par dirigeant 70-75 ans, SCI dormante,
cessation — du **patrimoine gelé** (succession non ouverte, structures mortes) qui ne vend
pas ; les points moyens sont portés par le détachement géographique et la cession de fonds —
de **vrais vendeurs**. ⚠ La part géo est partiellement gonflée par l'artefact acheteur
(cohorte mixte, cf. 1.3) : à re-mesurer sous panel point-in-time.

**2.3 Verdict : non-monotonicité RÉELLE, pas un petit-N.** Fisher exact 8-24 (1 375/3 025)
vs 25-49 (346/1 692) : **p < 10⁻⁴**. Le barème actuel est inversé sur son haut de gamme.

## LOT 3 — Sensibilité du label

**3.1** (`lot3_natures_par_an.csv`) : Vente terrain à bâtir 138-340 parcelles/an ; VEFA
62-137 ; Échange 79-108 ; Adjudication **18-53/an** ; Expropriation 0-38. « Licitation »
n'existe pas comme nature en base (6 natures seulement).

**3.2** (`lot3_bandes_labels.csv`) : re-flag des non-vendues → L2 : +106 · L3 : +115.
Lift V≥1 : L1 RR 1,90 [1,83–1,98] → L2 1,90 [1,83–1,98] → L3 1,91 [1,83–1,98]. Bande
25-49 sous L3 : 348/1 692 (20,6 %) — **inchangée**. La non-monotonicité ne vient PAS du
label : les cessions contraintes sont trop rares en 974 pour peser.

## LOT 4 — Barre « chaudes » décontaminée

**4.1** (`lot4_snapshots.csv`) : TOUS les snapshots datent de juillet 2026 (baseline/etape*
/p1_gardes : 06/07, périmètre Saint-Paul 51 129 ; q_v2 : 06-07/07 ; q_v3_datagap : 10/07,
431 663). Dernière vente DVF en base : **31/12/2025**.

**4.2 Verdict : aucun lift prospectif calculable aujourd'hui** — aucun snapshot n'est
antérieur à une seule vente observable. Le 4,72 %/an des chaudes reste un chiffre contaminé
(statut post-vente) et ne doit PAS servir de barre. La barre honnête : **geler q_v3_datagap
(10/07/2026) comme point de référence** et mesurer le taux de vente des chaudes-au-10/07 sur
les ventes 2026 au prochain millésime DVF (publication ~avril 2027). D'ici là, toute
comparaison v2/v1 doit être RELATIVE (RR sur le sous-ensemble vendeur-certain).

## LOT 5 — Vérifications rapides

**5.1 Sitadel** : l'historique est DÉJÀ en base — 2013-01-02 → 2026, 3 450-4 618 permis/an
2013-2023 (2024 : 2 751 · 2025 : 2 839 · 2026 partiel : 1 111) ; `lot5_sitadel_an.csv`.
Rien à ingérer pour la profondeur.

**5.2 DPE = 914 : c'est le gisement réel, pas un filtre.** L'ingestion (`dpe.py`) ne pose
aucune clause restrictive : dédup `numero_dpe`, rattachement parcelle 100 % local. Le dataset
ADEME « logements existants » pour la Réunion est structurellement marginal (~10 DPE/mois
depuis 07/2021 — docstring vérifié + rapport couverture du 11/07 : gisement ~914 au total,
couverture bâti 0,09 %). Le dataset « neufs » ADEME est distinct et non ingéré. Les
« dizaines de milliers » attendus n'existent pas dans l'open data DROM.

**5.3 Quadrants** (définitions exactes, `scoring/dryrun.py`) : chaude = exclusion ∅ ∧
(bascule rouge OU (Q≥65 ∧ A≥60 ∧ A_hors_zone≥60 ∧ complétude≥50)) · **à surveiller = Q≥65
sans le reste** · à creuser = 50≤Q<65 · écartée = exclusion dure ou Q<50.
L'inversion à-surveiller (1,19 %/an) < écartée (1,56 %) s'explique par construction : le
quadrant est une **sélection négative sur A**, or les couches A (propriétaire, âge dirigeant,
DVF, Sitadel, BODACC, DPE) SONT les prédicteurs de vente. Décomposition chiffrée des 5 889 :
1 592 (27 %) ont A<60 ; **4 297 (73 %) ont A≥60 mais échouent au verrou « le signal de zone
ne bascule jamais seul »** (leur A tient à la dynamique Sitadel du quartier, pas au
propriétaire). Hypothèse alternative « bâti vs nu » TESTÉE ET RÉFUTÉE : les nues vendent
plus que les bâties dans tous les statuts (écartées 4,95 % vs 4,55 % ; chaudes nues 18,26 %).

**5.4 Millésimes DGFiP** : audit NON lancé (`source_checks` vide, mandat d'audit data à
venir). En base : situation_2025 uniquement. L'URL data.economie suit le motif
`fichier_des_parcelles_situation_{YYYY}` → un panel point-in-time 2021-2024 est
plausiblement re-téléchargeable ; à CONFIRMER par l'audit data (rien téléchargé ici).

## GO / NO-GO

1. **Familles identitaires A/B/C : NO-GO comme moteur de score en l'état.** RR vendeur-certain
   1,44 [1,31–1,58] (critère ≥2× non atteint) ; ~la moitié du lift apparent est un artefact
   acheteur ; les stacks à points élevés (dirigeant 70-75, SCI dormante, cessation) sont
   CONTRE-prédictifs. À conserver comme features candidates (cession de fonds : 72 % de vente ;
   géo-détachement à re-mesurer) sous panel point-in-time DGFiP — pas comme barème additif.
2. **Familles actif D/E : GO comme composante, pas comme score autonome.** RR VC 1,38
   [1,25–1,53], structurellement insensibles à la fuite d'identité (tenure/friche portées par
   la parcelle). E non testable (43 F/G sur l'île).
3. **Label recommandé v2 : L2 = Vente + Vente terrain à bâtir.** Aligné sur l'événement cœur
   du produit, +106 positifs, lifts inchangés. L3 rejeté : adjudications 18-53/an, licitation
   absente des natures DVF — aucun pouvoir statistique, et la non-monotonicité n'en vient pas.
4. **Barre chaudes décontaminée : 0 chiffre honnête disponible aujourd'hui.** Tous les
   snapshots postdatent la dernière vente observable. Décision opérationnelle : geler
   q_v3_datagap (10/07/2026) comme référence prospective ; première mesure propre au
   millésime DVF couvrant 2026. Interdiction de citer 4,72 %/an comme barre.
