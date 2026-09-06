# MANDAT CIRCUIT-5b — Les restes tranchés

Branche : `feat/circuit-5b`, worktree `~/Desktop/labuse-audit`, depuis `main` (CIRCUIT-5 mergé).
Compte-rendu : chapitre « 5b » dans `docs/CIRCUIT/COMPTE-RENDU-CIRCUIT-5.md`.
Autonomie : mêmes règles (aucune question, doutes écrits, branche jamais rouge, un commit et un push par lot, rien mergé, aucun `DROP`, aucune source effacée). Les décisions ci-dessous sont prises par Vic le 06/09/2026 ; CC les applique et vérifie avec `labuse circuit verrous` en fin de chaque lot.

## Lot 1 — Les quatre « à rattacher » : ce sont des sources, elles entrent au catalogue

Pour chacune : une ligne `data_sources` complète (id, nom affiché, producteur, mode de remplissage, cadence, sonde sentinelle réellement appelée ou raison de son absence — le seed refuse le reste), un slug au registre, la carte table → réservoir mise à jour, les données qui la lisent déclarées.
- `mairies` → `annuaire_service_public` (DILA, annuaire de l'administration ; API, cadence mensuelle).
- `rnic_coproprietes` → `rnic_anah` (registre national des copropriétés, Anah ; data.gouv, cadence annuelle).
- `rpls_commune` → `rpls_sdes` (répertoire des logements locatifs des bailleurs sociaux, SDES ; annuel). C'est la source des chiffres SRU servis dans la fiche commune, le Flash et les PDF : elle porte les données `taux_lls_pct` et voisines.
- `commune_conso_enaf` → `enaf_cerema` (consommation d'espaces NAF, portail de l'artificialisation, Cerema ; annuel), lue par `pression_zan_ha` et `zan_reste_ha`.
Résultat attendu : 72 réservoirs servis, 72 = 72 = 72 (V2a), `VERROUS.md` et la page mis à jour.

## Lot 2 — Les huit réservoirs muets

Avant tout retrait, CC vérifie par grep (moteurs, ingestion, couches, `layers.ts`, jobs) qu'aucun lecteur n'existe ; s'il en trouve un, la source est **rattachée** (lecteur déclaré) au lieu d'être retirée, et le compte-rendu le dit.
- **À rattacher** : `cadastre_epoque` (lecteur : le rattachement géométrique des permis orphelins, RETOURS-14 — à déclarer comme réservoir des données permis) · `inpi_rne` (lecteur : dirigeants du Scan patrimoine et de la fiche propriétaire) · `lidar_hd_mnh` si `hauteur_bati_m` ou la fiche soleil le lisent, sinon retirer.
- **À retirer** (`statut = retiree`, date du jour, raison) : `mobpro` (abandonné par ZONE-DONNÉES) · `bd_ortho_irc` (servait aux indices de végétation, variables mortes depuis SCORING-3) · `office_eau_chroniques` · `parkings_osm_aper` · `recherche_entreprises_dinum`.
Résultat attendu : V1d sans ligne « à décider ».

## Lot 3 — La ligne SIRENE au code INSEE invalide

V4a a trouvé une ligne héritée dans `sirene_etablissements` hors du référentiel des 24. La corriger si le code est une coquille identifiable (adresse, coordonnées), la supprimer sinon, avec la ligne au compte-rendu ; puis `VALIDATE CONSTRAINT` pour que V4a passe de « not_valid » à « valide ».

## Lot 4 — `bascule_gardes` débranchée des photos pré-v8

`bascule_gardes` lit encore `p_model_static_pre_v8` et `parcel_residuel_pre_v8`. La garde doit comparer le candidat au run servi et au précédent via le manifeste (CIRCUIT-1 lot 3), jamais à une photo. Réécrire cette comparaison, test, puis les deux tables redeviennent des orphelines ordinaires listées par `labuse tables purger` (Vic les poussera en poubelle lui-même).

## Lot 5 — Vérification

`labuse circuit verrous --complet` sur la base locale : 0 cassé, et « à décider » réduit aux seules orphelines qui attendent le geste de Vic. Sortie au compte-rendu, `VERROUS.md` à jour (72 réservoirs), capture du Résumé avant/après.
