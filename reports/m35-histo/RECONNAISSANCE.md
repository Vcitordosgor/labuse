# M3.5 LOT A — RECONNAISSANCE DES ARCHIVES DVF 2014-2020 (974) · 12/07/2026

Objectif : localiser les millésimes DVF retirés de la distribution DGFiP (fenêtre
glissante 5 ans) pour étendre l'historique 974 à 2014-2020. Pistes examinées dans
l'ordre du mandat ; chaque URL testée le 12/07/2026.

## Piste (a) — « DVF géolocalisés » Etalab : ÉPUISÉE pour ≤ 2020

- Index `https://files.data.gouv.fr/geo-dvf/latest/csv/` (redirigé vers le bucket
  `geo-dvf.s3.sbg.io.cloud.ovh.net`) : ne liste QUE `2021/ … 2025/`.
- Probes directs `…/csv/<annee>/departements/974.csv.gz` : **404 pour 2014-2020**,
  206/200 pour 2021+. Aucun millésime ancien n'est encore servi, sous aucune forme.

## Piste (b) — data.gouv.fr (dataset + historique) : ÉPUISÉE

- Dataset « Demandes de valeurs foncières géolocalisées » (`5cc1b94a634f4165e96436c1`) :
  3 ressources, toutes 2021-2025 (fichier unique `dvf.csv.gz` du 24/04/2026 inclus).
- Dataset source « Demandes de valeurs foncières » (`5c4ae55a634f4117716d5656`) :
  ressources « Valeurs foncières 2021 … 2025 » uniquement. Aucune ressource archivée
  ≤ 2020 dans l'API (`/api/1/datasets/...`).

## Piste (c) — Mirror communautaire cquest : ✅ COUVERTURE COMPLÈTE 2014-2020

`http://data.cquest.org/dgfip_dvf/` archive les **publications semestrielles brutes**
DGFiP (fichiers nationaux pipe « | », 43 colonnes, non géolocalisés) depuis avril 2019,
chacune couvrant ~5 ans glissants :

| Édition | Contenu (fichiers `valeursfoncieres-*.txt[.gz/.zip]`) |
|---|---|
| 201904 | 2014-2018 (+ consolidé `dvf-2014-2018.csv.gz`, 294 Mo, id parcelle reconstruit) |
| 201910 | 2014-2019s1 (.gz) |
| 202104 | 2016-2020 |
| 202110 | 2016-2021s1 |
| 202204 | 2017-2021 |
| 202304 | 2018-2022 |
| 202404 | 2019-2023 |
| 202504 | 2020-2024 (.zip) |

### Constat CRITIQUE : retard de transcription des actes à La Réunion

Le nombre de lignes 974 d'un même millésime **croît fortement d'une édition à l'autre** —
les actes DOM sont transcrits avec des années de retard :

| Millésime | éd. précoce | éd. tardive | delta |
|---|---|---|---|
| 2020 | 7 274 lignes (202104) | 21 958 (202504) | **×3,0** |
| 2019 | 17 506 (202104) | 19 172 (202404) | +9,5 % |
| 2018 | 5 435 (201904, via consolidé) → 16 582 (202104) | 16 632 (202304) | ×3,1 puis +0,3 % |
| 2017 | 14 606 (201904) → 15 581 (202104) | 15 598 (202204) | +6,8 % puis +0,1 % |
| 2016 | 13 547 (202104) | 13 550 (202110) | +0,02 % |

→ Règle d'ingestion adoptée : **pour chaque millésime, la DERNIÈRE édition qui le
contient en année pleine** (la maturité est atteinte ~2-3 ans après l'année de mutation).

### Sources retenues (URL exactes, récupérées le 12/07/2026)

| Millésime | URL | Édition | Lignes 974 |
|---|---|---|---|
| 2014 | `http://data.cquest.org/dgfip_dvf/201910/valeursfoncieres-2014.txt.gz` | 201910 | 11 541 |
| 2015 | `http://data.cquest.org/dgfip_dvf/201910/valeursfoncieres-2015.txt.gz` | 201910 | 12 017 |
| 2016 | `http://data.cquest.org/dgfip_dvf/202110/valeursfoncieres-2016.txt` | 202110 | 13 549 |
| 2017 | `http://data.cquest.org/dgfip_dvf/202204/valeursfoncieres-2017.txt` | 202204 | 15 597 |
| 2018 | `http://data.cquest.org/dgfip_dvf/202304/valeursfoncieres-2018.txt` | 202304 | 16 631 |
| 2019 | `http://data.cquest.org/dgfip_dvf/202404/valeursfoncieres-2019.txt` | 202404 | 19 171 |
| 2020 | `http://data.cquest.org/dgfip_dvf/202504/valeursfoncieres-2020.txt.zip` | 202504 | 21 957 |

Limite documentée : 2014 et 2015 n'existent que dans les éditions 2019 (dernière =
201910, maturité 4,5-5 ans) — résidu de sous-compte possible mais faible (cf. QA :
concordance < 0,2 % entre 201904 et 201910 sur ces années). CGU cquest : données
DGFiP sous conditions propres (PDF archivés dans le même répertoire) — usage interne
d'analyse, pas de rediffusion nominative.

### Format et harmonisation (constats, pas de devinette)

- 43 colonnes pipe, dates JJ/MM/AAAA, décimales à virgule, **UTF-8 sur le mirror**
  (transcodé par cquest ; repli latin-1 implémenté).
- Entêtes strictement identiques sur toutes les éditions utilisées, à UNE exception :
  colonne 1 renommée « Code service CH » (≤ 202110) → « Identifiant de document »
  (≥ 202204). Colonne vide, non exploitée. C'est la seule évolution de format
  constatée — l'« évolution 2019 » du format ne touche pas nos éditions (toutes ≥ 2019).
- Le brut n'a NI géolocalisation NI identifiant de mutation : id parcelle reconstruit
  (même convention IDU que M2), id mutation reconstruit par l'heuristique geo-DVF
  (date, n° disposition, valeur) — détail dans `src/labuse/ingestion/dvf_histo.py`.

## Piste (d) — DV3F / Cerema : documentée, NON engagée

DV3F (DVF enrichi et fiabilisé par le Cerema, historique complet depuis 2010) est
accessible par **conventionnement gratuit** réservé aux ayants droit (collectivités,
établissements publics, chercheurs) via `https://datafoncier.cerema.fr` (demande via le
portail « consultdf »). Une structure privée n'y est éligible que par partenariat de
recherche. Voie de recours si un millésime venait à disparaître du mirror cquest ;
aucune démarche engagée (hors mandat).

## Millésimes PM 2019-2020 (A4)

Confirmés au catalogue data.economie (dataset
`fichiers-des-locaux-et-des-parcelles-des-personnes-morales`, mêmes attachments que M2) :
`fichier_des_parcelles_situation_2019_dept_62_a_976_zip` et
`fichier_des_parcelles_situation_2020_dept_62_a_976_zip` — même tranche 62→976 que
2022-2023, membre `.txt` latin-1 (format 2021-2023 documenté par M2, 24 colonnes
identiques, `Département='97'` + `Code Direction='4'`).

## Verdict reconnaissance

**Aucun millésime manquant** : profondeur 2014-2020 complète depuis les archives
publiques, sans interpolation ni reconstruction. La géolocalisation n'existe pas dans
ces archives (longitude/latitude NULL en `_histo`) — le rattachement parcellaire se
fait par IDU reconstruit, vérifié à 92,6-97,4 % contre la table `parcels` (cf. QA).
