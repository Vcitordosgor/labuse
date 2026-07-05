# NOTES DPE ADEME (Vague C2) + bonus /mvt

## État : TEMPS 1 (reco + échantillons) fait — STOP validation Vic
Branche `ingestion/dpe-ademe` (jamais mergée). Base `openclaw@…/labuse`.

## PARTIE A — DPE ADEME

### Source (vérifié live 05/07/2026)
- Jeu **`dpe03existant`** (« DPE Logements existants depuis juillet 2021 », 3CL réformée).
  API data-fair : `GET https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines`
  (filtre `qs=`, pagination par `after` = curseur ; `size` ; `select`). Sans clé.
- **Base nationale = 15 105 023 DPE. 974 = 910** (filtre `qs=code_departement_ban:974`).
  Saint-Paul (`code_insee_ban:97415`) = **168**. (⚠ `code_postal_ban:974*` → 403, wildcard interdit.)
- Écartés (documenté) : DPE pré-2021 (méthode non fiabilisée), DPE neufs, audits — jeux séparés.

### Champs réels (schéma 230 champs, pas devinés)
`etiquette_dpe` (A–G), `etiquette_ges`, `type_batiment` (maison/appartement/immeuble),
`surface_habitable_logement`, `annee_construction`, `adresse_ban`, `code_insee_ban`,
`code_postal_ban`, `code_departement_ban`, `date_etablissement_dpe`, `numero_dpe`,
`conso_5_usages_par_m2_ep`, `emission_ges_5_usages`, `_geopoint`.

### 🚨 `_geopoint` INUTILISABLE au 974 → re-géocodage BAN obligatoire
- **100 % des `_geopoint` 974 sont HORS Réunion** (600/600 échantillon ; ex. `56.0,-3.0` = Écosse).
  Le géocodage BAN stocké par l'ADEME est systématiquement faux pour le DOM (collision codes
  postaux 974xx, incohérences `code_postal_ban` vs `code_insee_ban`).
- **Solution validée** : re-géocoder `adresse_ban` via `api-adresse.data.gouv.fr/search`
  avec `citycode=<insee>` (machinerie permis existante) → **159/168 points valides Réunion (95 %)**
  sur Saint-Paul. Scores modérés (~0,62 ; lotissements sans n° → centroïde) → rattachement
  **APPROXIMATIF, tracé `rattachement='geocode'`**. Puis `ST_Contains` sur `parcels`.

### Échantillon Saint-Paul (calculé en mémoire, RIEN persisté)
- 168 DPE. Étiquettes : A2 B6 C42 D55 E49 **F8 G6** (F+G = 8,3 %).
- Types : maison **131**, appartement 36, immeuble 1.
- **Maisons F/G (cible signal) = 10.**
- Ré-géocodés valides 159/168 → **50 parcelles distinctes** rattachées (collectifs/lotissements :
  plusieurs DPE par parcelle → le signal `passoire_thermique` dédupliquera par parcelle).
- Représentativité : base = biens diagnostiqués depuis 2021, PAS tout le parc → signal
  « positif quand présent », jamais exhaustif (à afficher dans data_sources — doctrine honnête).

### Stratégie TEMPS 2 (après validation)
- **Table dédiée `dpe_records`** (volumes + nature par-logement justifient une table vs spatial_layers) :
  numero_dpe (unique), etiquette_dpe, etiquette_ges, type_batiment, surface, annee_construction,
  adresse, code_insee, date_etablissement, lon/lat (re-géocodé), parcelle_id nullable, rattachement.
- Signal `passoire_thermique` (vue/fonction, `# TODO étage 2`) : maison F/G, DPE < 5 ans, par parcelle.
- Chunké/résumable, throttle BAN prudent. Bilan volumétrie commune × étiquette.

## PARTIE B — bonus /mvt (mouvements de terrain) — CONSTRUIT
- Connecteur Géorisques : méthode `mvt(code_insee)` (paginée). `georisques_layers.py` : `parse_mvt`
  (lon/lat → Point), `ingest_mvt_commune`, kind `KIND_SOURCE['mvt']`. Source data_sources ajoutée.
- ⚠ Le doute « point vs lieu-dit » (noté en Vague B) est LEVÉ : /mvt a bien `longitude`/`latitude`.
- Échantillon Saint-Paul (persisté, spatial_layers kind='mvt') : **160 objets**
  (Éboulement 136, Glissement 18, Coulée 5, Érosion 1 ; fiabilité Fort 100 / Faible 50 / Moyen 10) ;
  **287 parcelles croisées (≤ 50 m)**. TEMPS 2 : passe île 24/24.

## Hors périmètre
- DPE pré-2021 / neufs / audits ; UrbanSIMUL. Rien branché au scoring (# TODO étage 1/2).
