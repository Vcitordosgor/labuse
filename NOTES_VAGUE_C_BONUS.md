# NOTES — Vague C bonus (fiscal DOM + POI/aménités + VEFA)

## État : TEMPS 1 (reco) fait — STOP validation Vic
Branche `ingestion/vague-c-bonus` (jamais mergée). Base `openclaw@…/labuse`.

## 1. Fiscal DOM
### QPV (quartiers prioritaires) — source géo confirmée
- **Region ODS** `quartiers-prioritaires-de-la-politique-de-la-ville-qpv` : **49 QPV (génération 2015)**,
  géométrie PROPRE (`geo_shape` = polygones WGS84 ; champs `code_qp`, `nom_qp`, `commune_qp`,
  `code_insee`, `nom_epci`). Prêt à ingérer (même pattern que les autres couches ODS).
- ⚠ **Génération 2024 = 56 QPV / 13 communes** (~163k hab) — la version À JOUR (décret 2023-1314,
  en vigueur 01/01/2024). Source nationale ANCT (data.gouv « Carte QPV 2024 » : pas de GeoJSON
  direct ; sig.ville.gouv.fr / Géoplateforme WFS à confirmer). → **décision millésime : ingérer la
  2024 (fraîche) — URL GeoJSON ANCT à confirmer — vs 2015 ODS (immédiat mais périmé).**
- Cible : entre dans le **BILAN PROMOTEUR** (QPV → dispositifs/abattements), PAS le score. # TODO bilan.

### NPNRU
- Pas sur Region ODS (catalogue vide pour prioritaire/renouvellement/anru). Zones ANRU largement
  incluses dans les QPV. → probablement N/A comme couche séparée ; à confirmer côté ANRU si utile.

### TVA 2,1 % DOM — RÈGLE GLOBALE, PAS UN ZONAGE
- En DOM la TVA à 2,1 % s'applique à certaines opérations (logement social LLS/LLTS, accession
  sociale) — **conditionnée au TYPE d'opération, PAS géographiquement zonée**. Tout le 974 est DOM.
  → **paramètre de bilan global, AUCUNE couche à ingérer**. Documenté, pas de couche vide.

## 2. POI / aménités — signal calculé
- **Source : OSM Overpass** (machinerie `_overpass` DÉJÀ en base + détection faux positifs réutilisable).
  BPE INSEE = alternative autoritaire mais BULK CSV national (pas d'API propre) → OSM plus pratique
  pour un signal live par catégorie. (BPE en fallback si OSM trop lacunaire.)
- **Catégories proposées (courtes)** : `ecole` (school/kindergarten/college), `sante`
  (pharmacy/hospital/clinic/doctors), `commerce` (supermarket/convenience/bakery/mall), `tcsp`
  (highway=bus_stop ; + arrêts réseau Car Jaune si source dispo).
- **Méthode** : par parcelle, distance (ST_Distance en 2975 depuis le centroïde) au plus proche POI
  de chaque catégorie → signal `score_amenites` (agrégation). **Poids = # TODO étage 1** (calibrage,
  pas maintenant). Signal CALCULÉ par parcelle, PAS des couches d'icônes à la KF.
- **Échantillon Saint-Paul (centre, live)** : école 5, santé 8, commerce 2, bus 21 → OSM couvre.

## 3. VEFA / ECLN — N/A DOM
- **ECLN (SDES) conduite en France MÉTROPOLITAINE uniquement — DOM exclus** (confirmé notice méthodo
  SDES + absence sur data.gouv). → **NO-GO : « vérifié N/A/inexploitable 05/07/2026 », NE PAS
  ingérer** (syndrome KF évité). Alternative future éventuelle : permis PC ≥ 5 logts (déjà en base
  via Sitadel) comme proxy de production neuve, mais ce n'est pas de la VEFA commercialisée.

## Plan de passe recommandé (TEMPS 2, après validation)
1. **QPV** → spatial_layers kind='qpv' + intersection parcelles + fraîcheur data_sources. # TODO bilan.
   (millésime à trancher : 2024 ANCT vs 2015 ODS.)
2. **Aménités** → connecteur Overpass par catégorie + signal distance/parcelle. # TODO étage 1.
3. **VEFA** → rien (N/A documenté). NPNRU/TVA → doc, pas de couche.
