# SYNTHÈSE M3.5 — LOT A : PROFONDEUR HISTORIQUE DVF + PM · 12/07/2026

**Branche `feat/m35-histo-dvf` — aucun merge.** Nouvelles données en tables SÉPARÉES :
`dvf_mutations_histo` (créée) et millésimes 2019-2020 ajoutés à
`pm_proprietaires_millesimes` (table M2, clé millésime — millésimes M2 intacts).
`dvf_mutations_parcelle`, les tables `p_model_*` du worktree, le moteur V, Q/A et les
snapshots : **non touchés**. Le worktree `../labuse-m3` n'a été consulté qu'en lecture
(vérification du statut M3).

## A1 — Reconnaissance : couverture 2014-2020 COMPLÈTE (détail `RECONNAISSANCE.md`)

Etalab et data.gouv.fr ne servent plus rien ≤ 2020 (vérifié par probes : 404). Le mirror
communautaire cquest (`data.cquest.org/dgfip_dvf/`) archive toutes les publications
brutes DGFiP depuis 2019 → les 7 millésimes 2014-2020 sont récupérables en année pleine.
Constat critique : **les actes réunionnais sont transcrits avec ~2-3 ans de retard**
(2020 : ×3,0 de lignes entre l'édition 202104 et 202504) → règle « dernière édition
couvrant le millésime » appliquée partout. DV3F/Cerema documenté sans être engagé.

## A2 — Ingestion `dvf_mutations_histo` (module `src/labuse/ingestion/dvf_histo.py`)

Granularité mutation × parcelle identique à la prod + `source_archive` (URL exacte) +
`millesime_source` (édition AAAAMM). Idempotent, garde-fou : toute année ≥ 2021 refusée
(prod fait foi — aucune réingestion d'année en prod). Harmonisation champ par champ
documentée dans le module ; points saillants :

- id parcelle reconstruit `974 + commune(2) + préfixe(3) + section(2) + plan(4)` ;
- id mutation reconstruit (heuristique geo-DVF : date + n° disposition + valeur),
  préfixé `H` → aucune collision possible avec la prod ;
- natures de culture code → libellé (référentiel DGFiP) : valeurs strictement incluses
  dans celles de la prod ; natures de MUTATION identiques aux libellés prod (vérifié
  par EXCEPT après correction d'encodage UTF-8 — le mirror est transcodé) ;
- longitude/latitude NULL : les archives brutes ne sont pas géolocalisées ;
- une seule évolution de format constatée entre éditions : colonne 1 renommée
  (vide, non exploitée) — entête verrouillée, tout autre écart LÈVE.

**110 463 lignes / 48 732 mutations ingérées** :

| Millésime | Lignes 974 | Mutations | dont Ventes | Parcelles | Édition |
|---|---|---|---|---|---|
| 2014 | 11 541 | 5 647 | 4 981 | 6 320 | 201910 |
| 2015 | 12 017 | 5 953 | 5 361 | 6 674 | 201910 |
| 2016 | 13 549 | 6 770 | 6 175 | 7 360 | 202110 |
| 2017 | 15 597 | 7 475 | 6 630 | 8 021 | 202204 |
| 2018 | 16 631 | 7 185 | 6 451 | 7 962 | 202304 |
| 2019 | 19 171 | 7 969 | 7 256 | 8 448 | 202404 |
| 2020 | 21 957 | 7 733 | 7 041 | 8 281 | 202504 |

Tests parsing : `tests/test_dvf_histo.py` (5 verts, + garde d'entête).

## A3 — QA d'intégrité (CSV dans ce répertoire)

**Volumétrie** (`volumetrie_par_an.csv`) : pas de statistique officielle annuelle 974
directement machine-lisible pour ≤ 2020 (le retrait DGFiP emporte aussi les stats) —
contrôle par **source croisée indépendante** (consolidé cquest, chaîne de traitement
distincte, éd. 201904) : écarts **0,0 / 0,0 / +0,1 %** sur 2014-2016 → tolérance 5 %
respectée. Les écarts 2017 (+6,8 %) et 2018 (+206 %) mesurent l'immaturité de l'édition
201904, pas un défaut d'ingestion (cf. RECONNAISSANCE) ; ils VALIDENT le choix des
éditions tardives.

**Continuité 2020→2021** (`jonction_2020_2021.csv`) : médiane prix/m² bâti 2 192 →
2 304 €/m² (+5,1 %, dans la tendance), médiane valeur 149 k€ → 150 k€ (+0,7 %) —
**aucune rupture à la jonction archive/prod**. Volumes ventes 7 041 → 9 028 (+28 %) :
creux COVID 2020 puis rebond record 2021, cohérent au national ; 2019→2021 = +24 %.
Les deux régimes de marché visés sont bien couverts : **plat 2014-2019 (~2 050-2 100
€/m²), haussier 2020-2025 (2 192 → 2 724 €/m²)**.

**Rattachement parcellaire** (`rattachement_parcelles.csv`) : 92,6 % (2014) → 97,4 %
(2019), monotone croissant vers 99,6 % (2025) — dérive attendue du parcellaire
(remembrements), même profil que le panel PM de M2.

**Natures de mutation** (`natures_par_an.csv`) : Vente, VEFA, Vente terrain à bâtir,
Adjudication, Échange présents CHAQUE année 2014-2025 (Expropriation absente en 2017
seulement) — **le label L2 est constructible sur toute la profondeur**.

**Couverture tenure** (`couverture_tenure.csv`) : parcelles de `p_model_frame` avec
≥ 1 mutation observable : 37 314 (8,64 %) sur 2021-2025 seule → **73 897 (17,12 %) sur
2014-2025, soit ×1,98**.

## A4 — Panel PM : 7 points annuels 01/01/2019 → 01/01/2025 (`pm_panel_2019_2020.csv`)

Millésimes 2019 (84 902 lignes → 72 709 parcelles) et 2020 (86 377 → 74 029) ingérés
par le pipeline M2 inchangé (attachments ajoutés à `MILLESIME_ATTACHMENTS`, mêmes
contrôles, format 24 colonnes conforme). Jointure `parcels` : 94,8 % / 95,6 % — la
série 2019→2025 est monotone (94,8 → 99,2 %), même dérive parcellaire que DVF. SIREN
9 chiffres : 77,5 % / 83,6 % (vs 87-88 % en 2021+) — la qualité SIREN se dégrade en
remontant, à retenir pour les features propriétaire des folds anciens. Churn :
2019→2020 = 94,2 % même propriétaire ; 2020→2021 = 90,2 % — churn apparent gonflé par
le saut de couverture SIREN (83,6 → 87,8 % : des correspondances basculent sur la
comparaison stricte par dénomination), à traiter comme artefact de mesure, pas comme
signal marché.

## Statut M3 et suite

**SYNTHESE-M3 non livrée à ce jour** (worktree `../labuse-m3`, dernier commit f2ff373
« module M3 » — aucun rapport de synthèse dans `reports/`). Conformément au mandat :
**le LOT B (dataset étendu p_model_ext_*, walk-forward 6 folds, verdict comparatif)
N'EST PAS ENGAGÉ**. Tout le nécessaire du lot B est prêt côté données : vue UNION
possible immédiatement (schémas alignés), fenêtres 36 mois complètes dès l'année
d'observation 2017, deux régimes de marché couverts.

## Reproductibilité

- DVF : `src/labuse/ingestion/dvf_histo.py` (parse + garde d'entête + ingestion
  idempotente) ; fichiers sources en cache `/tmp/m35_dvf_histo/` ; téléchargement
  documenté dans RECONNAISSANCE.md (URL exactes + éditions).
- PM : `src/labuse/ingestion/pm_millesimes.py` (M2, +2 attachments).
- Tests : `tests/test_dvf_histo.py` + `tests/test_pm_millesimes.py` (9 verts).
