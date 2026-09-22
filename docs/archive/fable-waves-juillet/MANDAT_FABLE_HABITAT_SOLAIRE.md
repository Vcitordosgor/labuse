# MANDAT FABLE — Module "Habitat Solaire" : le pack data installateurs PV

**Repo** : `~/Desktop/labuse` · **Branche** : `feat/habitat-solaire` · **Merge** : Vic uniquement (`git merge --no-ff`) · Commits atomiques par lot, chaque lot livrable indépendamment.

---

## 1. Contexte business (pourquoi ce module)

Cible : entreprises d'installation photovoltaïque du 974 (résidentiel + tertiaire), segment solvable dépensant déjà 2-3K€/mois en acquisition de leads de mauvaise qualité. Proposition de valeur LABUSE : **le croisement** — aucune donnée ci-dessous n'a de valeur seule, mais "parking 4 200 m² assujetti APER, propriétaire SCI X (bilan sain), non équipé, échéance juillet 2026" ou "villa mutée en mars, facture élec estimée 300€/mois, toit orienté nord, pas de risque amiante, propriétaire-occupant probable" = un rendez-vous qualifié qu'aucun concurrent ne vend.

Principe d'architecture **two-tier** : une couche gratuite pré-calculée sur 100% des parcelles (PVGIS + dérivations), et une couche premium à la demande (Google Solar API, Lot 8, **conditionnel**). Tout ce qui suit reste au niveau parcelle/bâtiment — jamais de donnée nominative personne physique (RGPD) ; les personnes morales (DGFiP, INPI) sont OK.

## 2. Existant à réutiliser (ne rien re-ingérer)

- `parcels` (431K, idu 14 car., centroid), emprises bâties BD TOPO, `dvf_mutations`, DPE ADEME (avec type ECS, refroidissement, période de construction), pipeline propriétaires personnes morales DGFiP, bilans INPI RNE, couches ABF/Mérimée, `sitadel_permits`, `ingestion_runs`, pattern `seed_sources.py`, signaux dans `signals.py`, outils frontend dans `registry.ts`.
- Détection piscines : si la couche existe déjà (BD TOPO bassins ou détection ortho), la réutiliser dans le Lot 2 ; sinon utiliser la couche bassins BD TOPO seule.

## 3. Schéma cible (nouvelles tables)

```sql
solar_grid(id, geom point, prod_spec_kwh_kwc float, ghi_kwh_m2_an float, source text, fetched_at)
parcel_solar(idu PK→parcels, prod_spec_kwh_kwc float,        -- interpolé depuis solar_grid
             score_solaire int,                               -- 0-100, percentile île
             azimut_bati_deg float, azimut_confiance text,    -- 'haute'|'basse' selon élongation
             flag_abf bool, flag_amiante bool, flag_topo_ombrage bool,
             conso_est_kwh_an int, facture_est_eur_mois int,
             proba_proprio_occupant int,                      -- 0-100
             pv_existant text,                                -- null|'commune_forte_densite'|'detecte'
             repowering bool, updated_at)
parkings_aper(id, geom polygon, surface_m2, source text,      -- 'osm'|'bdtopo'
              idus jsonb, proprio_pm text, proprio_siren text,
              tranche text,                                   -- '1500_10000'|'sup_10000'
              echeance date, equipe bool,                     -- null = inconnu
              exempt_probable text)                           -- null|'arbres'|'autre'
pv_registry(id, commune, insee, filiere, puissance_kw, date_mise_service,
            individualise bool, geom nullable, raw jsonb)
grid_capacity(poste_source, geom nullable, capa_dispo_mw, source, fetched_at)  -- Lot 7, best effort
solar_api_cache(building_key PK, idu, payload jsonb, imagery_quality text,
                imagery_date date, fetched_at)                -- TTL 30 jours STRICT (ToS Google)
```

Paramètres en config (`config.py` / settings), jamais en dur : `TARIF_ELEC_EUR_KWH` (défaut 0.25, à ajuster), seuils APER, TTL cache = 30 jours.

---

## Lot 1 — Baseline PVGIS : le score solaire gratuit sur toute l'île 🔥 fondation

**Source** : API PVGIS (Commission européenne, gratuite, sans clé, stockage libre) — `https://re.jrc.ec.europa.eu/api/v5_2/PVcalc` (vérifier la version courante v5_2/v5_3 sur la doc PVGIS et la base satellite couvrant l'océan Indien — SARAH2/SARAH3).

1. Grille de points sur l'emprise terrestre de l'île, pas ~400 m (≈ 16-20K points). Pour chaque point : `PVcalc` avec `peakpower=1, loss=14, angle=15` (pente toit typique), **`usehorizon=1`** → PVGIS intègre l'ombrage topographique du relief (cirques, remparts) automatiquement. Récupérer `E_y` (kWh/an pour 1 kWc = production spécifique) et l'irradiation. Respecter un rate limiting poli (~20-25 req/s max, backoff sur 429) ; run one-shot, reprise sur erreur (checkpoint).
2. Interpolation aux parcelles : plus proche voisin ou IDW sur `parcels.centroid` → `parcel_solar.prod_spec_kwh_kwc`.
3. `score_solaire` = rang percentile île (0-100).
4. `flag_topo_ombrage` = TRUE si prod_spec du point < 80% de la médiane de sa commune (capte les fonds de cirque/remparts).

**Sanity check physique obligatoire** : la médiane de prod spécifique de la côte Ouest (Saint-Gilles, Saint-Leu) doit être nettement supérieure à celle de l'Est (Sainte-Rose, Salazie). Si ce n'est pas le cas, l'ingestion est fausse — investiguer avant de continuer.

## Lot 2 — Facture d'électricité estimée : l'argument de vente n°1 🔥🔥🔥

**Sources** : portail open data EDF SEI Réunion (`opendata-reunion.edf.fr`) — identifier le dataset de consommation électrique résidentielle le plus fin disponible (IRIS si dispo, sinon commune) ; à défaut, données Agence ORE. Documenter le dataset retenu dans seed_sources.

1. Table/vue baseline : conso moyenne par logement par maille (kWh/an).
2. Modèle d'estimation par parcelle bâtie résidentielle — additif simple et documenté, coefficients en config :
   - base = baseline maille × ratio surface (surface DPE ou estimation emprise×niveaux vs surface moyenne maille)
   - `+` clim présente (DPE refroidissement) : +15-25% en zone littorale
   - `+` chauffe-eau électrique (DPE ECS) : +1 500 kWh/an
   - `+` piscine détectée : +2 000 kWh/an (pompe ; +50% si bâti haut de gamme)
3. `facture_est_eur_mois = conso_est_kwh_an × TARIF_ELEC_EUR_KWH / 12`, arrondi à la dizaine.
4. Affichage avec le libellé "estimation statistique" — jamais présenté comme une donnée réelle.

## Lot 3 — Parkings APER : le lead à deadline légale 🔥🔥🔥

**Cadre juridique** (à VÉRIFIER dans les textes avant d'implémenter — loi n°2023-175 du 10 mars 2023 "APER", art. 40, et son décret d'application de fin 2024 ; stocker seuils/dates en config) : obligation d'ombrières photovoltaïques sur ≥50% de la surface pour les parcs de stationnement extérieurs >1 500 m². Échéances de principe : **1er juillet 2026** pour les ≥10 000 m², **1er juillet 2028** pour les 1 500-10 000 m². Sanctions annuelles. Exemptions (ombrage arboré ≥50%, contraintes techniques/patrimoniales, coût disproportionné).

1. **Détection** : OSM (`amenity=parking`, polygones, via Overpass ou extract Geofabrik Réunion) ∪ couche stationnement BD TOPO si présente. Dédupliquer par recouvrement spatial. `surface_m2 = ST_Area(geom::geography)`. Ne garder que >1 200 m² (marge sous le seuil pour les cas limites).
2. **Rattachement** : jointure spatiale parcelles support → `idus` ; propriétaire via pipeline DGFiP personnes morales → `proprio_pm`, `proprio_siren`.
3. **Tranche & échéance** calculées depuis la config.
4. `equipe` : NULL par défaut (l'ombrière existante n'est pas détectable sans ML ortho — voir Lot 4.3). Si OSM porte un tag exploitable (rare), l'utiliser.
5. `exempt_probable = 'arbres'` si couverture arborée manifeste (croisement couche végétation BD TOPO si dispo, sinon NULL — ne pas sur-ingénierer).
6. Signal `aper_deadline` : parkings assujettis, non exemptés, échéance < 24 mois **OU déjà dépassée** — au 10/07/2026, l'échéance des ≥ 10 000 m² (1er juillet 2026) est PASSÉE : sanctions annuelles encourues, sous réserve d'exemptions → le lead le plus chaud du module. Badge dédié « échéance dépassée » distinct de « échéance < 24 mois ».

## Lot 4 — Parc PV existant + repowering 🔥🔥🔥

**Source** : Registre national des installations de production et de stockage d'électricité (ODRÉ, sur data.gouv.fr / opendatareseaux) — filtrer département 974, filière solaire. Les installations ≥36 kVA y sont individualisées, les petites agrégées par commune (vérifier le schéma du millésime courant).

1. Ingestion → `pv_registry`. Géolocaliser les individualisées si adresse/commune exploitable (best effort).
2. `parcel_solar.pv_existant = 'commune_forte_densite'` pour les parcelles des communes du top quartile en densité de petites installations (proxy d'équipement, honnête sur sa granularité).
3. **Repowering** : installations `date_mise_service` entre 2006 et 2013 (boom défisc + contrats d'achat 20 ans arrivant à échéance 2026-2033) → `repowering = TRUE` sur les parcelles rattachées (individualisées uniquement). Signal `repowering_candidate`.
4. **Stub détection ortho** : créer l'interface `detect_rooftop_pv(ortho_tile) -> polygons` avec NotImplementedError + docstring décrivant l'approche (segmentation sur ortho IGN 20 cm, même topologie que détection piscines). L'implémentation ML est HORS de ce mandat.

## Lot 5 — Flags de qualification (trivial, forte valeur) 🔥🔥

1. **`flag_amiante`** : période/année de construction < 1997 (source : champ période de construction du DPE ADEME déjà en base ; NULL si pas de DPE). Libellé UI : "Bâti pré-1997 — risque amiante toiture à vérifier" — un signal de prudence commerciale, PAS un diagnostic.
2. **`flag_abf`** : croisement spatial avec les périmètres ABF/Mérimée **déjà en base** → "déclaration préalable renforcée probable". Zéro ingestion, pure jointure.
3. **`azimut_bati_deg`** : orientation du grand axe de l'emprise bâtie (ST_OrientedEnvelope ou équivalent PostGIS ; azimut du côté long). `azimut_confiance = 'haute'` si ratio longueur/largeur > 1.4, sinon 'basse' (bâti carré = orientation non significative). Rappel hémisphère sud à afficher côté UI : **le versant NORD est le versant optimal au 974**.
4. **`proba_proprio_occupant`** : base infracommunale IRIS du recensement INSEE (variables de statut d'occupation des résidences principales) → taux de propriétaires-occupants par IRIS, modulé : +15 pts si mutation DVF < 24 mois sur maison individuelle, plafonné 5-95. Score statistique, jamais nominatif.

## Lot 6 — Vue tertiaire : grandes toitures × santé financière 🔥🔥

Pur croisement de l'existant, aucune ingestion :

1. Vue matérialisée `mv_toitures_tertiaires` : emprises bâties > 500 m² × parcelle × propriétaire PM (DGFiP) × dernier bilan INPI (CA, résultat si dispo) × `prod_spec_kwh_kwc` × distance au poste source (Lot 7 si dispo).
2. Tri par `surface_emprise × score_solaire`, export CSV.

## Lot 7 — Capacité d'accueil réseau (best effort) 🔥

La Réunion est une ZNI : c'est **EDF SEI** (pas Enedis/Caparéseau) qui publie les capacités. Chercher sur `opendata-reunion.edf.fr` un dataset capacités d'accueil / postes sources. **Si introuvable ou inexploitable : créer le stub `grid_capacity` vide + note dans le rapport de fin, et passer.** Ne pas y consacrer plus d'une heure — c'est du nice-to-have gros projets.

## Lot 8 — Google Solar API : la mesure fine du toit ⚠️ CONDITIONNEL

**N'implémenter ce lot QUE si Vic confirme que le quickcheck de couverture 974 est positif** (test buildingInsights en cours de son côté). Sinon : stub + le two-tier reste PVGIS pur.

1. Endpoint `buildingInsights:findClosest`, `requiredQuality=BASE`, clé en variable d'env (jamais commitée).
2. **Cache strict** : `solar_api_cache`, TTL 30 jours (conformité ToS Google : re-téléchargement 30j, pas de stockage permanent, pas de bulk). Purge des entrées > 30j par le job de refresh mensuel existant. Refresh **lazy uniquement** : on ne rafraîchit une entrée expirée que si elle est re-consultée — JAMAIS de re-scan proactif du cache.
3. Flux : consultation → cache hit (< 30j) → servir ; miss → 1 appel → stocker → servir. Champs exposés : surface exploitable, heures d'ensoleillement/an, segments de toit (pente, azimut), nb panneaux max, `imageryQuality`, `imageryDate`.
4. **Déclenchement au clic** ("☀️ Mesurer ce toit"), jamais automatique au survol/chargement.
5. Garde-fous : soft quota par compte client (100 mesures/jour, config) + compteur global journalier avec circuit-breaker (arrêt à 350/jour, config) — en plus du hard cap à poser côté console GCP (action Vic, le noter dans le rapport).
6. Attribution Google dans l'UI conformément aux ToS.

## Lot 9 — Frontend : l'outil "Solaire"

Dans le pattern des outils existants (registry.ts) :

1. **Fiche parcelle, panneau Solaire** : score_solaire, prod spécifique, facture estimée, azimut (avec mention "versant nord optimal"), badges flags (ABF, amiante, topo, PV existant, repowering), bouton mesure fine (Lot 8 si actif).
2. **Vue "Prospection PV résidentiel"** : filtres combinables (facture estimée min, score solaire min, mutation récente, proprio-occupant min, exclusions flags) + export CSV **"à l'occupant"** : adresse + caractéristiques, AUCUN nom de personne physique.
3. **Vue "Parkings APER"** : carte + table triée par échéance, badge tranche, propriétaire PM, export.
4. **Vue "Tertiaire"** (Lot 6).
5. Textes UI : sourcer chaque donnée ("PVGIS — Commission européenne", "estimation statistique", etc.). Pas de sur-promesse.

---

## Critères d'acceptation

```sql
-- Lot 1 : couverture et physique
SELECT count(*) FROM parcel_solar WHERE prod_spec_kwh_kwc IS NOT NULL;   -- ≥ 95% des parcelles
SELECT c.cote, percentile_cont(0.5) WITHIN GROUP (ORDER BY prod_spec_kwh_kwc)
FROM parcel_solar ps JOIN (VALUES ('Saint-Paul','ouest'),('Sainte-Rose','est')) c(commune,cote) ON ...
-- médiane Ouest > médiane Est, sinon FAIL

-- Lot 2 : distribution plausible
SELECT min(facture_est_eur_mois), percentile_cont(0.5) WITHIN GROUP (ORDER BY facture_est_eur_mois),
       max(facture_est_eur_mois) FROM parcel_solar WHERE facture_est_eur_mois IS NOT NULL;
-- médiane attendue grossièrement 80-180€ ; si médiane > 400€ ou < 30€, revoir le modèle

-- Lot 3 : volumétrie et rattachement
SELECT tranche, count(*), count(proprio_siren) FROM parkings_aper GROUP BY 1;
-- ordre de grandeur attendu : dizaines à petites centaines de parkings assujettis sur l'île

-- Lot 4 : repowering
SELECT count(*) FROM pv_registry WHERE date_mise_service BETWEEN '2006-01-01' AND '2013-12-31';

-- Lot 8 (si actif) : conformité cache
SELECT count(*) FROM solar_api_cache WHERE fetched_at < now() - interval '30 days';  -- = 0 après purge
```

+ QA frontend Playwright sur les 3 vues (chargement, filtre, export non vide) aux viewports habituels.

## Contraintes

- RGPD : aucun nom/coordonnée de personne physique nulle part (ni en base au-delà de l'existant, ni dans les exports). Personnes morales OK.
- ToS Google (Lot 8) : TTL 30j strict, pas de bulk, pas de scan proactif, attribution.
- Tout paramètre métier (tarif élec, seuils APER, quotas, coefficients conso) en config, pas en dur.
- Réseau : PVGIS, EDF SEI open data, ODRÉ/data.gouv, OSM/Geofabrik, INSEE, Google Solar (si Lot 8). Rien d'autre.
- Chaque lot = commits séparés, testables indépendamment. Ordre de réalisation conseillé : 5 → 1 → 2 → 6 → 3 → 4 → 9 → 7 → 8.

## Rapport de fin attendu

Volumétries par table, résultat du sanity check Ouest/Est, dataset EDF SEI retenu (maille), nb parkings par tranche + taux de rattachement propriétaire, présence ou non des capacités réseau, statut Lot 8 (implémenté/stub), et liste des paramètres config avec leurs valeurs par défaut à faire valider par Vic.
