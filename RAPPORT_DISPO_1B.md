# RAPPORT DE DISPONIBILITÉ — 1.B SITADEL (historique des autorisations)

> §7. Complète C4 (ingestion SITADEL déjà livrée). Sondé le 2026-06-14.

## Source
- **Dataset** : « Liste des permis de construire et autres autorisations d'urbanisme à La Réunion »,
  **Région Réunion ODS** (data.regionreunion.com), HTTP 200.
- **Couverture Saint-Paul** : **2 529 autorisations** (comm=97415).
- **Type** : PC (permis de construire), PA (aménager), DP (déclaration préalable), PD (démolir).
- **Période** : ~2016-2023.

## Géolocalisation — limite documentée
- **Pas de coordonnées lat/lon** dans le dataset. Localisation via **références cadastrales**
  (`sec_cadastre1..3` / `num_cadastre1..3`) + adresse texte.
- Géocodage par **jointure à nos parcelles** (centroïde de la parcelle cadastrale) : précis quand
  la parcelle est au référentiel. Notre référentiel = sous-ensemble bbox (3 000 parcelles) →
  **117/2 519 permis géolocalisés**, suffisant pour donner à ~2 846/3 000 parcelles ≥ 1 permis
  ≤ 300 m. Limite assumée (pas de géocodage commune-seule ; on ne place jamais un permis au
  hasard). Géolocalisation exhaustive ⇒ ingérer tout le cadastre Saint-Paul (hors périmètre 1.B).

## Champs exploités (nature / statut)
- **Nature** : `nb_lgt_tot_crees` (nb logements créés), `surf_hab_creee` (m² habitables), `type_dau`,
  `destination_principale`. → libellé « PC · N logement(s) · ~X m² » ou « PC · projet ».
- **Statut** : le dataset liste des **autorisations accordées** (présence de
  `date_reelle_autorisation`). `etat_dau` = état du dossier ; `date_reelle_daact` = déclaration
  d'achèvement si présente. Les **refus ne figurent pas** dans ce flux d'autorisations → on
  affiche « autorisé le {date} » (+ « travaux achevés » si DAACT), jamais un faux « refusé ».

## Verdict : **GO** (enrichissement de C4) — nature + statut + indicateur de dynamique de secteur.
