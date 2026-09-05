# CIRCUIT-3 lot 3 — Échantillons à valider

Ce document liste, source par source, ce qui demande soit **des yeux humains** (Stéphanie), soit
**des identifiants** (API authentifiée), soit **plus de budget d'appels producteur** que la session
du mandat, pour compléter l'échantillon vérifié contre le producteur. Chaque ligne porte la
**proposition de CC** et l'**URL du producteur**. Tant qu'une source n'est pas validée, son
échantillon `filtres/echantillons/<source>.json` **vit sans lignes** (le contrôle `d_echantillon`
skip proprement) — **rien n'attend**.

## Déjà fait — vérifié en direct chez le producteur (05/09/2026)

| Source | Producteur | Enreg. | Résultat |
|---|---|---|---|
| **cadastre_etalab** | IGN — API Carto Cadastre (contenance DGFiP) | 20 parcelles (4 témoins + 16 golden, 1 par commune) | **2 écarts / 20** : `97403000AH0341` (nous 113,5 m² vs 168 producteur) et `97404000AC0011` (72 vs 150) — notre `surface_m2` géométrique diverge > 10 % de la contenance cadastrale sur 2 petites parcelles. Signal réel. |
| **ban** | BAN — api-adresse (reverse geocode) | 24 adresses (1 par commune) | **0 écart / 24** : l'INSEE (citycode) du producteur = le nôtre partout. |
| *communes* (référence) | INSEE COG via geo.api.gouv.fr | 24 communes (nom + population) | référence partagée `echantillons/communes.json`, sert de témoin aux contrôles commune. |

## À valider — yeux humains (Stéphanie)

- **lidar_hd** : les **50 toits contrôlés au seuil de confiance 0,70** (RETOURS-14 : 0 faux sur 50).
  LiDAR HD est servi EN DIRECT (WMS 974, aucune table à échantillonner) — la vérité de la nature
  d'un toit demande l'œil. *Proposition CC* : figer les 50 toits déjà contrôlés comme échantillon.
- **cosia** : 20 bâtiments CoSIA confirmés sur la PVA (couverture raster IA — la nature d'un
  polygone demande l'œil).
- **flair** : 20 détections d'occupation du sol confirmées.

## À valider — API authentifiée (identifiants requis)

- **sirene_etablissements** : le NAF **par SIRET** exige l'API Sirene INSEE (clé). Testé via
  `recherche-entreprises` (public) : renvoie le NAF du **siège**, ambigu pour un établissement —
  plusieurs faux écarts (ex. `4711B` vs `47.11B` = format ; `6820B` vs `7010Z` = siège≠étab.).
  *Proposition CC* : 20 SIRET témoins, NAF normalisé sans point, contre l'API Sirene INSEE.
- **dgfip_parcelles_pm** (MAJIC) : denomination par SIREN — `recherche-entreprises` donne le siège
  (SIREN 239740012 → REGION REUNION, cohérent) ; la vérité par SIRET exige Sirene INSEE.
- **inpi_rne** : l'API RNE INPI (dirigeants) est authentifiée (compte INPI).

## À valider — faisable, budget d'appels producteur

- **dpe** : API ADEME par numéro DPE (faisable) ; la base LOCALE ne porte que 17 DPE — l'échantillon
  complet viendra avec l'ingestion DPE complète. *Proposition* : 20 numéros DPE témoins → `etiquette_dpe`.
- **dvf** : géo-DVF renvoie des listes par commune/parcelle ; apparier une disposition = budget.
  *Proposition* : `valeur_fonciere` + surface d'une mutation sur une parcelle témoin.
- **gpu_plu** : /gpu/zone-urba s'interroge par géométrie (une requête par témoin). *Proposition* :
  la famille de zone servie de 20 parcelles témoins vs le GPU.
- **georisques_mvt** : /gaspar/risques par commune (le degré est déjà gardé bloquant par
  `d_alea_non_retrograde`). *Proposition* : présence de l'aléa mvt par commune.
- **sitadel** : le CSV Sit@del brut (pas d'API unitaire). *Proposition* : type+commune+date de 20 permis.
- **bodacc** : API BODACC ODS (faisable). *Proposition* : type_procedure + date de 20 annonces.
- **filosofi** : fichier Filosofi brut (i_est_200 = secret statistique). *Proposition* : `ind` de 20 carreaux.
- **edf / osm_overpass / osm_transport / gtfs_pan / bpe_insee / trafic_rn** : appariement
  géométrique ou fichier brut / base OSM vivante. *Proposition* dans chaque `echantillons/<source>.json`.

## Comment valider (pour Vic / CC plus tard)

1. Remplir `filtres/echantillons/<source>.json` → `lignes` : `{cle, colonne, attendu, origine{url,champ}}`,
   `attendu` **lu chez le producteur**, jamais dans nos tables ; passer `a_valider` à `false`, dater `lu_le`.
2. `labuse filtre jouer <source>` — le contrôle `d_echantillon` rejoue l'échantillon ; tout écart
   = KO avertissant avec les deux valeurs.
