# SYNTHÈSE M2 — Panel point-in-time DGFiP PM 2021-2024 · 12/07/2026

**Branche `feat/m2-millesimes-pm` — aucun merge.** Table versionnée `pm_proprietaires_millesimes`
(974 entier, situation au 1ᵉʳ janvier de chaque millésime) ; la table de prod
`parcelle_personne_morale` (situation 2025) et le moteur V sont **intacts** — zéro flux modifié.

## Lot 1 — Reconnaissance (les 4 millésimes existent, +2 en bonus)

Dataset data.economie `fichiers-des-locaux-et-des-parcelles-des-personnes-morales`,
attachments réels (graphies irrégulières telles quelles) :

| Millésime | Attachment (tranche ≥ 61/62) | Membre 974 | Taille zip |
|---|---|---|---|
| 2021 | `fichier_des_parcelles_situation_2021_dept_61_a_976_zip` | `PM_21_NB_974.txt` | 131 Mo |
| 2022 | `fichier_des_parcelles_situation_2022_dept_62_a_976_zip` | `PM_22_NB_974.txt` | 111 Mo |
| 2023 | `fichier_des_parcelles_situation_2023_dept_62_a_976_zip` | `PM_23_NB_974.txt` | 114 Mo |
| 2024 | `fichiers_des_parcelles_situation_2024_dpts_61_a_976_zip` (pluriel !) | `PM_24_NB_974.csv` | 130 Mo |

**Diffs de schéma** (détail `schema_table.md`) : positions des 24 colonnes IDENTIQUES
2021→2025 (`_sniff_header` lève sur tout écart) ; différences de LIVRAISON : 2021-2023 en
`.txt` latin-1 à entête quotée avec `Département='97'` + `Code Direction='4'` (le 974 éclaté
sur deux colonnes), groupe en code nu ; 2024-2025 en `.csv` avec `974` plein et groupe
parfois libellé. **Bonus catalogué : les millésimes 2019 et 2020 existent aussi** (non
ingérés, hors mandat — le panel pourrait remonter à 01/01/2019).

## Lot 2 — Ingestion (idempotente, millésime en clé)

4/4 millésimes ingérés (aucun absent, aucun substitut nécessaire) :

| Millésime | Lignes 974 (CSV) | Parcelles distinctes |
|---|---|---|
| 2021 | 88 787 | 76 270 |
| 2022 | 90 638 | 78 056 |
| 2023 | 92 063 | 79 345 |
| 2024 | 93 958 | 81 161 |
| (2025, prod) | — | 82 701 |

## Lot 3 — QA (`couverture_par_an.csv`, `churn_proprietaires.csv`)

| Millésime | parcelles PM | jointes `parcels` | % jointure | SIREN 9 chiffres | % SIREN | % du parc (431 663) |
|---|---|---|---|---|---|---|
| 2021 | 76 270 | 73 680 | 96,6 % | 66 936 | 87,8 % | 17,07 % |
| 2022 | 78 056 | 75 895 | 97,2 % | 68 488 | 87,7 % | 17,58 % |
| 2023 | 79 345 | 77 820 | 98,1 % | 68 831 | 86,7 % | 18,03 % |
| 2024 | 81 161 | 80 094 | 98,7 % | 70 738 | 87,2 % | 18,55 % |
| 2025 | 82 701 | 82 066 | 99,2 % | 72 556 | 87,7 % | 19,01 % |

Les non-joints (1,3-3,4 %) = parcellaire qui a évolué depuis (remembrements/divisions) —
attendu et décroissant vers 2025. Le solde non-SIREN (~12 %) = pseudo-identifiants MAJIC
(`U…` : État, collectivités non sirenées) — conservés BRUTS, typables par le groupe DGFiP.

**Churn propriétaire année/année** (future feature v2 « owner_changed », pas un simple contrôle) :

| transition | parcelles an N | même propriétaire | changement | sortie du fichier PM |
|---|---|---|---|---|
| 2021 → 2022 | 76 270 | 72 618 (95,2 %) | 1 879 | 1 773 |
| 2022 → 2023 | 78 056 | 73 375 (94,0 %) | 2 290 | 2 391 |
| 2023 → 2024 | 79 345 | 75 499 (95,2 %) | 1 607 | 2 239 |
| 2024 → 2025 | 81 161 | 78 203 (**96,4 %**) | 1 314 | 1 644 |

Entrées (nouvelles parcelles PM) : 3 559 · 3 680 · 4 055 · 3 184. **Cohérence 2024↔2025 : la
plus haute continuité du panel (96,4 %)** — la jonction table versionnée ↔ table de prod est
saine. Identité comparée par SIREN normalisé, repli dénomination exacte quand non-SIREN.

## Lot 4 — Verdict : PANEL-READY ✅

Propriétaire PM identifiable à CHAQUE 01/01 de 2021 à 2025 : **5 points annuels complets**,
jointure parcelles ≥ 96,6 %, SIREN exploitable sur ~87-88 % des lignes chaque année (stable).
Le bloc O v2 peut construire des features datées à t : train ≤ 2023 (01/01/2021-2023),
val 2024 (01/01/2024), test 2025 = table courante (vendeur-certain par construction).
Limites honnêtes : (a) granularité ANNUELLE — un changement de propriétaire intra-année
n'est daté qu'au 1ᵉʳ janvier suivant ; (b) le fichier ne couvre que les PM — une vente
PM → particulier apparaît comme « sortie du fichier », c'est un SIGNAL, pas un trou.

## Reproductibilité
Module : `src/labuse/ingestion/pm_millesimes.py` (download streamé + cache
`/tmp/dgfip_pm_millesimes/`, idempotent par millésime). Tests parsing :
`tests/test_pm_millesimes.py` (4 verts). Requêtes QA : temp table + LEFT JOIN
(la variante sous-requêtes corrélées prenait > 7 min — annulée, documenté).
