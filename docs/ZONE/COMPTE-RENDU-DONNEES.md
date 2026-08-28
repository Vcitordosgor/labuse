# ZONE-DONNÉES — COMPTE-RENDU FINAL

Branche `feat/zone-donnees`. Un commit par lot. Postgres : écriture sur NOUVELLES tables seulement
(`sirene_etablissements` étendue, `trafic_rn` créée) ; aucun run, aucune bascule, golden non touché.

## 1. Tableau par source

| Source | État | Volume | Millésime | Maille | Permet de dire | Ne permet pas |
|---|---|---|---|---|---|---|
| **SIRENE établissements** (INSEE géo × Stock, LOT 1) | **ingérée** | 158 515 actifs géolocalisés 974 | 2026-08 (mensuel) | établissement (adresse/voie 97,7 %) | concurrents par NAF fin, présence d'activités | l'effectif exact (tranche), le CA |
| **Emplois = tranches SIRENE** (LOT 2) | **ingérée** (dérivée) | — | 2026-08 | établissement | « postes salariés déclarés dans la zone » (fourchette) | un point ; les 87 % « NN » sans tranche (dits à part) |
| **Filosofi** (LOT 3, existant) | branchée + imputation | 14 773 carreaux | 2021 (dernier carroyé) | carreau 200 m | population, revenu ESTIMÉ, % < 25 | un revenu « mesuré » (53,4 % imputés → « valeur approchée ») |
| **Trafic RN** (Région Réunion SIR, LOT 5) | **ingérée** | 692 tronçons | comptages 1992–2023 | tronçon RN | trafic véhicules/jour des RN traversant/bordant la zone | flux piéton, réseau départemental/communal |
| **Zones PLU** (LOT 7, existant) | branchée | plu_gpu_zone | idurba par commune | zone PLU | tableau ZONE/PART/DOCUMENT recouvert, vigilance CDAC | les destinations fines par activité (2/24 communes calibrées) |
| **Sitadel + zones AU** (LOT 8, existant) | branchée | 50 292 permis | roulant | permis / zone AU | logements autorisés 36 mois + AU intersectantes (signal daté) | une projection de population |
| BPE / GTFS (existant) | branchée | 35 546 / 9 956 | 2025 / PAN | point | équipements, générateurs de flux | — |
| DVF / Radar (existant) | branchée | 102 551 / pige | roulant | parcelle | marché de la zone | — |

## 2. SOURCES ÉCARTÉES

- **MOBPRO** (emplois au lieu de travail) — **abandonnée** : l'INSEE ne traite pas l'emploi au lieu de
  travail à une maille infracommunale (thème absent des bases infracommunales). Un nombre d'actifs sur
  86 ha serait une invention. Remplacée par les tranches d'effectif SIRENE (LOT 2). Table conservée,
  non supprimée, marquée abandonnée au catalogue.
- **Étalab geo-sirene par département** (candidat M1-b) — **déprécié** : URLs `files.data.gouv.fr/
  geo-sirene/…` en 404, Étalab a basculé sur le fichier INSEE. Choix (a) retenu (M1).
- **Tourisme / capacité d'accueil géolocalisée** (LOT 6) — **écartée** : aucune source ouverte ne donne
  une CAPACITÉ (lits/chambres) géolocalisée FINEMENT au 974. INSEE publie la capacité hôtelière à la
  maille COMMUNE (répartir sur une zone au prorata serait exactement l'artefact interdit). La PRÉSENCE
  des hébergements reste couverte : ils sont dans `sirene_etablissements` (NAF 5510Z/5520Z) et
  ressortent par le mécanisme « concurrents » si l'utilisateur choisit cette activité. Seul le bloc
  « capacité » est écarté.
- **Dépenses de consommation** (LOT 9) — **écartée** : aucun coefficient budgétaire par poste propre au
  DOM/à La Réunion n'est publié en open data machine-lisible. Appliquer une structure de consommation
  MÉTROPOLITAINE à Saint-Paul est précisément l'artefact qu'on reproche à la concurrence (ODIL) — la
  règle du mandat l'interdit. Rien n'est codé.

## 3. Contrôle de vérité M4 — rejoué (les 4 boulangeries de Saint-Paul)

Géocodage BAN de chaque adresse → distance au 1071C le plus proche en base :

| Boulangerie | 1071C en base | Écart | Verdict |
|---|---|---|---|
| Le Pain Frotté, 25 av. P. J. Bénard | Le Pain Frotté, 25 av. P. J. Bénard (qualite 11) | **36 m** | ✓ |
| L'Île aux Pains, 46 Chaussée Royale | 46 Chaussée Royale (qualite 11) | **5 m** | ✓ |
| L'Île aux Pains Front de mer, 4 rue Rhin et Danube | 2 rue Rhin et Danube (qualite 11) | **79 m** | ✓ |
| The Bread Workshop, ch. Crève-Cœur (RD5) | « Au Four et au Levain », 19 ch. Crève-Cœur (qualite 11) | **3 m** | ✓ |

**Les 4 ressortent à moins de 200 m.** Note honnête : le premier passage a mesuré 338 m pour The Bread
Workshop parce que l'adresse du mandat (« ch. Crève-Cœur (RD5) », **sans numéro**) fait tomber le
géocodage BAN au milieu d'une voie longue ; avec le numéro exact (19, score BAN 0,98), l'écart est de
3 m. The Bread Workshop est enregistré sous sa raison sociale « Au Four et au Levain ». La couverture ne
ment pas.

**Vérif « notaire »** : `notaire` résout au code 6910Z (activités juridiques) et rend **276
établissements à Saint-Denis** (compte non nul).

## 4. Décisions prises seul (mandat autonome) et justification

1. **Fichier SIRENE = (a) INSEE**, filtré 974 par DuckDB en lecture parquet distante (pushdown), joint à
   StockEtablissement sur le SIRET. Justif : (b) déprécié ; (a) porte la qualité documentée + IRIS + QPV
   + lon/lat GPS ; le national ne se télécharge jamais (5 s pour le 974).
2. **Position en lon/lat GPS direct** (x_longitude/y_latitude), sans reprojection — bien que La Réunion
   soit en EPSG 2975 — car le fichier fournit les degrés décimaux. Piège « océan » écarté par construction.
3. **Ingestion telle quelle sans re-géocodage** : adresse+voie = 97,7 % (> seuil 80 %). La règle M2 est
   respectée sans passer par la BAN.
4. **naf_nomenclature.py GARDÉ** (pas remplacé) : il coïncide avec le NAFRev2 de SIRENE (1 seul code
   orphelin rév.1). Les synonymes continuent de résoudre.
5. **LOT 7 servi en FAIT géométrique** (tableau ZONE/PART/DOCUMENT), pas en destinations fines par
   activité : celles-ci ne sont calibrées que dans 2 des 24 communes — les mapper partout serait un faux
   positif (péché cardinal). Le libellé de zone (UA vs A) dit déjà l'essentiel ; l'absence = « non calibré ».
6. **Badge ESTIMÉ piloté par i_est_200** (LOT 3), badge maintenu (Filosofi toujours winsorisé) + « valeur
   approchée sur N/M carreaux » quand la majorité est imputée.

## 5. Dettes ouvertes

- **LOT 4 — Recensement à l'IRIS 2022** : NON livré cette session. Le rattachement IRIS est DÉJÀ acquis
  gratuitement (colonne `sirene_etablissements.iris`, issue de `plg_iris` du fichier géo). Restent à
  ingérer les 4 bases INSEE IRIS 2022 (Population/Logement/Diplômes/Activité, CSV nationaux filtrables au
  974) et à coder la pondération par carreaux Filosofi avec la maille écrite à l'écran + la liste des
  communes sans IRIS (assimilées à un IRIS unique, valeur communale dite). Chantier balisé, faisable.
- **LOT 6** — un bloc « présence d'hébergements » (comptage SIRENE NAF 55xx dans la zone) pourrait être
  servi sans capacité, si Vic le souhaite (aujourd'hui accessible en choisissant l'activité hébergement).
- **Verbatim PLU par destination** (LOT 7) : quand les 24 communes seront calibrées au format
  `destinations_*`, brancher le verbatim + article + page par zone.
- **Réseau départemental/communal** (LOT 5) : non ouvert au 974 à ce jour — à re-sonder périodiquement.

## Branchement & diffusion (LOT 10)

- Chaque bloc porte sa source/millésime/maille ; garde-fou 3 états (servie/non_couverte/erreur) intact.
- Pied de panneau = sources réellement servies (MOBPRO retiré ; SIRENE couvre concurrents + emplois).
- Fiche « Autour de cette parcelle » : même moteur (population_zone imputation-aware), libellés alignés.
- PDF Flash + PDF outil : la fourchette de postes remplace « actifs (MOBPRO) » ; règles exportables tenues.
- Scroll du panneau (corrigé en recette) tient avec les blocs supplémentaires (capture 390).

**Suite 1961 passed, 0 failed · tsc 0 · build · golden non touché.**
