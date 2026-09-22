# NOTES — Clôture Vague B (Saint-Philippe + ABF + ENS)

## État : TEMPS 1 (reco) fait — STOP validation Vic
Branche `ingestion/vague-b-cloture` (jamais mergée). Base `openclaw@…/labuse`.

## 1a. Saint-Philippe (97417) — état des lieux transverse
| Couche | 97417 | moy. 23 autres | verdict |
|---|--:|--:|---|
| parcels | 4 162 | 18 587 | OK (petite commune) |
| parcel_vue_mer | **0** | 6 375 | **TROU — fixable** (warm-vue-mer jamais lancé ; commune côtière) |
| sitadel_permits | **0** | 861 | **TROU — fixable** (ODS a **169** permis pour 97417 ; ingestion jamais lancée) |
| parcelle_personne_morale | **0** | 3 569 | **TROU — fixable** (ingest-personnes-morales jamais lancé pour 97417) |
| dvf_mutations | 165 | 1 278 | OK (présent, faible — rural) |
| dpe_records | 7 | 39 | OK (présent, faible — base DROM jeune) |
| cascade_results | 87 675 | 396 460 | OK |
| parcel_evaluations | 8 324 | 43 187 | OK |
→ **3 trous, tous fixables** (jointures jamais passées, sources couvrent 97417). Plan TEMPS 2 :
  `warm-vue-mer 97417`, `ingest-permits 97417`, `ingest-personnes-morales 97417`. Chunké, err comptées.

## 1b. ABF / Monuments historiques — source fraîche trouvée
- **Actuel : 6 objets** seulement (kind='abf'), issus du GPU `assiette-sup-s` filtre AC1 (communes
  DÉMATÉRIALISÉES uniquement) → Saint-Denis (le plus dense en MH) a **0**. Couche quasi vide.
- **Source fraîche : base Mérimée** — data.culture.gouv.fr (Opendatasoft) :
  `…/datasets/liste-des-immeubles-proteges-au-titre-des-monuments-historiques/records`
  filtre `region="La Réunion"`. **204 MH pour le 974.** Champs : `denomination_de_l_edifice`,
  `commune_forme_editoriale`, `cog_insee_lors_de_la_protection` (['97411']), `nature_de_la_protection`,
  géométrie `coordonnees_au_format_wgs84` (dict {lat,lon}).
- Format vérifié : **coordonnées 50/50 valides Réunion** (WGS84 propre, PAS le problème DPE).
- **Échantillon Saint-Denis : 64 MH** (vs 0 actuel). Pas de périmètre délimité publié → tampon
  **500 m** (abords) autour de chaque point MH → polygone → intersection parcelles.
- Volumétrie île : 204 MH → 204 tampons 500 m → intersection parcelles (dense au chef-lieu).
- Plan TEMPS 2 : ingérer les 204 MH, buffer 500 m → spatial_layers kind='abf' (remplace les 6 GPU),
  intersection parcelles. **FLAG QUALITÉ étage 1, PAS exclusion étage 0** (# TODO étage 1).

## 1c. ENS — 3 communes manquantes
- Présentes : 21/24. **Manquantes : Le Port, Saint-André, Sainte-Suzanne.**
- Vérifié : ces 3 communes ont parc_national (3) + forêt publique + 23k-72k autres spatial_layers
  → la passe ENS (`ingest_espaces_proteges`, proxy INPN patrinat : APB/RNN/RNR/RB/CEN/CDL) A BIEN
  TOURNÉ mais renvoie **0 espace protégé** : ces communes n'en ont structurellement pas
  (Le Port = port 100 % urbain ; Saint-André / Sainte-Suzanne = plaines côtières agricoles).
- **ENS départemental propre : INTROUVABLE en open data** (confirmé, déjà noté dans data_sources).
- → **« vérifié, N/A »** pour ces 3 communes. Recherché le 05/07/2026 : INPN/patrinat (0 objet),
  data.regionreunion.com (pas de couche ENS départementale), AGORAH (non public). **Proposer
  l'ajout au mail AGORAH/DEAL en attente** (couche ENS départementale officielle).

## TEMPS 2 — passes FAITES (05/07)
### 1a. Saint-Philippe — 3 jointures comblées
- **permits** : 169 chargés (ODS), géolocalisés par IDU. (était 0)
- **parcelle_personne_morale** : 614 chargées (DGFiP). (était 0)
- **parcel_vue_mer** : **4 007 calculées** (RGE ALTI live, 0 erreur ; oui=3178 / partielle=372 /
  non=457). (était 0)
→ Saint-Philippe : **plus aucun trou transverse** (vue mer 4007, permits 169, PM 614).

### 1b. ABF Mérimée — île entière
- **200/204 MH → 200 abords** (tampon 500 m ; 4 MH sans coords valides). **60 618 parcelles
  intersectées** (le tampon sur-couvre largement — d'où le flag « covisibilité à instruire »).
- spatial_layers kind='abf' (remplace les 6 GPU AC1). Rattachement 100 % géométrique. # TODO étage 1.
- data_sources → Mérimée, fraîcheur posée.

### 1c. ENS — N/A documenté
- 3 communes (Le Port, Saint-André, Sainte-Suzanne) : « vérifié N/A 05/07 » dans data_sources.
  Aucune ingestion (rien à inventer). À demander au mail AGORAH/DEAL (couche ENS départementale).

Amendements Vic appliqués : flag ABF « covisibilité à instruire » + rattachement géométrique pur
(pas cog_insee). Tests : ABF 3 verts. Branche NON mergée.

## Plan de passe recommandé (TEMPS 1 — archive)
1. Saint-Philippe : 3 jointures manquantes (vue mer, permits, PM), chunké, err comptées.
2. ABF : connecteur Mérimée + buffer 500 m + intersection parcelles île entière, kind='abf'. # TODO étage 1.
3. ENS : rien à ingérer (N/A documenté) → NOTES + data_sources « vérifié N/A 05/07 » + mail AGORAH/DEAL.
4. data_sources fraîcheur pour chaque couche touchée. Tests connecteur ABF + jointures. NOTES finales.
