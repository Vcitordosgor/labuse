# MANDAT SCORING-DONNÉES-1 — ce que la base contient déjà pour nourrir le score, mesuré au banc K0

**Nature** : audit + mesure, **lecture seule sur tout ce qui est servi**.
**Modèle CC** : Fable (rapprochements sur toute la base et tout le code).
**Branche** : `audit/scoring-donnees-1` depuis `main`. **Worktree** : `~/Desktop/labuse-scdon`.
**Livrables** : `docs/audit-2026-09/SCORING-DONNEES-1.md` + `reports/score-v2-arene/donnees1/*.csv`.
**Interdits** : aucun code servi modifié, aucune table servie écrite, aucun run lancé, aucune ingestion, aucun `promote`, aucun merge. Les scripts de mesure vivent dans `scripts/audit/scoring/` (extension du harnais SCORING-1/2, banc K0).

## Étape 0 — avant toute écriture
`pwd` = `~/Desktop/labuse-scdon`, branche = `audit/scoring-donnees-1`, arbre propre. Sinon : s'arrêter et signaler, sans rien écrire.

## Règles de mesure (les mêmes pour tous les lots)
- Banc **K0** : entraîner ≤ 2023 · calibrer 2024 · tester 2025. Point de départ = candidat **K4bis global** (K2 mortes retirées + résiduel K3 + voisinage + isotonique par segment). Chaque variable est mesurée **seule, ajoutée à ce candidat**.
- Lignes lues : **préc@100/commune, lift décile sup, AUC global et par segment, ECE**. Priorité (≈ 90 parcelles) est donnée avec son bruit ±8 pts, jamais seule.
- Toute variable est construite **as-of** (état au 01/01 de l'année de la ligne). Si l'as-of est impossible, la variable est **documentée mais pas mesurée**. Test de fuite K4bis rejoué sur chaque ajout.
- Une variable couverte à < 5 % n'est pas candidate (elle peut être notée).
- Chaque affirmation cite sa preuve : `table.colonne`, `fichier:ligne`, `csv`.

## Lot A — le faux passé (priorité 1)
18 des 29 features sont l'état 2026 projeté sur 2017-2024 (bâti, nu constructible, résiduel, zone PLU, végétation). Une parcelle nue vendue en 2018 puis bâtie en 2019 apprend au modèle que « le bâti se vend ».
1. **Mesurer le biais** : sur les lignes d'apprentissage labellisées 1, part des parcelles dont l'état 2026 (bâtie / zone / résiduel) contredit l'état à la date de vente (DVF `nature` terrain vs maison, date d'achèvement Sitadel postérieure, zone AU ouverte après). Une table par variable statique.
2. **Inventorier ce qui permet de reconstruire l'as-of** : millésimes cadastre bâti en base, éditions BD TOPO, archives GPU, dates Sitadel (autorisation, DOC, DAACT). Pour chacun : années couvertes, table, clé.
3. **Si reconstruction possible** pour bâti/nu et zone : les rejouer as-of et mesurer au K0. C'est la mesure la plus importante du mandat.

## Lot B — profondeur DVF
`dvf_mutations_histo` (et tout autre historique DVF en base) : années couvertes, nombre de mutations, écart avec la fenêtre 2021+ servie. Recalculer `tenure_bin` sur l'historique profond → % informatif (17,1 % aujourd'hui) → K0.

## Lot C — gestes précurseurs déjà en base
Pour chacun : existence, couverture 974, dates disponibles, as-of possible, K0.
- **Division cadastrale** : parcelle créée ou découpée récemment (millésimes cadastre, numérotation, date de création si portée).
- **Sitadel hors PC** : déclarations préalables de division, permis d'aménager (sur la parcelle et adjacent), permis refusés / caducs.
- **PC par une personne morale sur une parcelle détenue par un particulier** (promoteur sous compromis) : type de demandeur Sitadel × propriétaire PM/PP.
- **DPE frais** (ADEME déjà ingérée) : DPE daté sur la parcelle sans vente derrière ; couverture réelle au 974 avant tout.

## Lot D — bloc propriétaire personne morale (segment PM seulement)
Ce qui existe dans le Score V et la veille succession, jamais entré dans le modèle P : âge du dirigeant (RNE), SCI dormante, événements BODACC, radiations, `parcel_veille_succession`, **entrée récente en PM** (`pm_proprietaires_millesimes` : PM propriétaire depuis < 2 ans). Plus une variable de secteur : part des ventes à un acquéreur PM sur 36 mois (as-of). K0 sur le segment PM.

## Lot E — ce que le PLU annonce
Emplacements réservés, OAP, ZAC, changement de zonage entre deux millésimes GPU, commune en procédure (données de l'outil Procédure). Existence, couverture, as-of, K0.

## Lot F — sources non ingérées : fiche seulement, pas d'ingestion
Une fiche par source (URL, millésime, volume 974, clé de jointure, licence, coût d'ingestion estimé) :
- **INSEE RP à l'IRIS** : part des ménages 75 ans et plus, ancienneté d'emménagement 30 ans et plus, vacance, résidences secondaires.
- **RPG** : parcelle déclarée / non déclarée, culture (canne).
- **BDNB** : âge du bâti, absence de DPE, vacance.
- **Radar agrégé commune × type** : état de la série en base (jours, volume par commune et type) — faisabilité seulement.

## Lot G — rapport
1. **LE tableau unique** (format SCORING-2) : candidat K4bis en colonne de base, puis une colonne par variable mesurée.
2. **Verdict par famille** : gain / neutre / impossible as-of / à ingérer, avec le chiffre qui le justifie.
3. **Recette q_v13 recommandée** = K4bis + toutes les variables à gain prouvé, et rien d'autre.
4. **Les 50 premières Priorité** du candidat recommandé face au servi `q_v11_m137`, chacune avec ses trois contributions principales en français.
5. Manifeste JSON : protocole, couvertures, variantes mesurées, verdicts.

## Ordre et arrêt
A → B → C → D → E → F → G. Si le temps manque : livrer G avec ce qui est mesuré et lister le reste en « non mesuré », plutôt qu'un lot bâclé. Rien n'est promu, rien n'est servi, `q_v11_m137` reste le run servi.
