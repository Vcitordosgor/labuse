# KELFONCIER-1 — « ça existe déjà ou pas ? »

**Audit LECTURE SEULE** — 8 features retenues sur l'audit fonctionnel de Kelfoncier du 27/09/2026.
Aucun code modifié, aucune migration, aucun run, aucun merge. Seul ce rapport est commité.

- **Branche** : `audit/kelfoncier-1` (base `origin/main`) · worktree `~/Desktop/labuse-kelfoncier` · ports **8535** (API) / **5735** (front).
- **Run servi** : `q_v11_m137` (résiduel `residuel_runs` run_seq **10**, `is_served=t`).
- **Parcelles témoins** : `97410000AN0347` (Saint-Denis, zone N) · `97415000BW0102` (Saint-Paul, U6c, à cheval) · **`97415000AB0134`** (Saint-Paul, **zone AU1est** — parcelle AU témoin choisie par l'audit, propriété EPFR, 2,04 ha).
- **Légende effort** : S = < 1 session · M = 1-2 sessions · L = source à créer / batch île.
- **Captures** : `docs/audit-2026-09/KELFONCIER-1/captures/`.

Toutes les valeurs `count` ci-dessous ont été relues en direct sur la base servie (psql), et les faits d'écran vérifiés dans l'app lancée (8535/5735).

---

## 1. SAR en couche + condition d'ouverture des zones AU

### Verdict : **PARTIEL**
Le SAR n'existe **que comme proxy dérivé** (pas la couche réglementaire officielle). En revanche la **condition d'ouverture des zones AU EXISTE**, complète, calculée à l'échelle parcelle — mais elle n'est pas exposée en clair comme attribut de fiche.

### Preuves
- **`data_sources`** : la table réelle a les colonnes `name`/`status` (pas `nom`/`statut`). Le SAR n'a **pas de ligne autonome « a_faire »** ; il est porté par la source « potentiel foncier Région ». La sentinelle amont (`src/labuse/.../sentinelle.py:776`) note : *« Couche SIG officielle NON diffusée (Carmen 29, Lizmap DEAL, Sextant WMS image seule, ODS Région : 0 vecteur au 07/09/2026) ; demandée à la Région (lot 7). Suivre révision SAR 2050. »* → **amont non diffusé en vecteur libre**.
- **Géométrie SAR** : **`spatial_layers` kind=`sar` = 2 453 géométries** (vérifié psql). Dérivées du champ `espacesar` du *potentiel foncier Région ODS* (`ingestion/layers_ingest.py:583,610`), réparties en 6 vocations (urbaine 1083, continuité 461, mixte 380, agricole 345, rurale 106, naturelle 57, coupure 21). Pas de table dédiée (`pg_tables ~ 'sar'` = vide). Le code marque explicitement que ce proxy **ne prouve ni constructibilité ni interdiction** (`layers_ingest.py:587`).
- **Cascade / zonage** : le SAR est câblé comme critère (`demo.py:160,184` `crit_present`, `state.py:68` couche critique). Il agit sur le verdict, non comme règle réglementaire.
- **Zones AU (témoin `97415000AB0134`)** : la fiche §Urbanisme sert la règle PLU calibrée (`Zone iAU1est à urbaniser`, PLU approuvé le 2025-12-17, hauteur max 4 m, emprise/reculs « non réglementé », « 22 interdites · 1 sous condition »). **§Potentiel / SDP résiduelle = « 0 m² — rien à construire », en-tête « zone non constructible ».** Capture `captures/q1-fiche-AU-97415000AB0134.png`.
- **Le moteur d'ouverture AU EXISTE et est peuplé** : `faisabilite/au_ouverture.py` + `au_statut.py`, table **`parcel_au_statut`** (colonne `classe`) :
  `conditionnelle_operation` **7 400** · `au_sous_plancher` **1 275** · `declasse_au_statut_inconnu` **810** (phasage 2AU→1AU) · `générique` 596 · `declasse_au_fermee` **456**. Config par commune × préfixe : `config/calibrage/au_ouverture_planchers.yaml`.
  Le témoin AB0134 = `conditionnelle_operation`, motif servi : *« Zone à urbaniser — ouverture conditionnée à une opération d'aménagement d'ensemble et/ou à une modification du PLU. Constructibilité à confirmer auprès de la commune. »* → la distinction 1AU/2AU et « AU fermée » **est** modélisée.
- **Limite** : `parcel_au_statut` agit en amont (scoring/assemblage) ; il **n'est pas exposé comme clé JSON de la fiche** (`.au_statut = null` dans le payload parcelle).

### Ce qui manque exactement
- **Donnée SAR** : la couche vecteur **SAR réglementaire officielle** (source DEAL/Région, non diffusée en WFS à ce jour, demandée lot 7). Le servi aujourd'hui n'est qu'un proxy de vocations. **Effort : L** (dépend d'une source externe à obtenir ; sinon rien à coder, le proxy tourne).
- **Règle d'ouverture AU** : **déjà faite** au moteur. Il ne manque que **l'exposition du statut AU en clair dans la fiche parcelle** (motif + classe) si le client doit le lire. **Effort : S.**

---

## 2. Établissements occupants sur la parcelle

### Verdict : **PARTIEL**
La donnée SIRENE existe et est riche, mais **aucune affectation établissement→parcelle** n'est matérialisée ni servie, et le géocodage INSEE ne tombe presque jamais *dans* l'emprise cadastrale.

### Preuves
- **`sirene_etablissements` = 158 515 lignes** (établissements **actifs** 974 uniquement — `sirene_etablissements.py:1`). Colonnes utiles : `actif`, `naf` (APE fine), `tranche_effectif`, `date_creation`, `denomination`, `enseigne`, `diffusible`, `geom` (Point 4326), `qualite_xy`.
- **Précision de positionnement = `qualite_xy`** (codes INSEE) : `11` (meilleure, plaque adresse) **144 458** · `12` 8 413 · `21` 2 867 · `33` 1 649 · `22` 1 128.
- **Aucune jointure établissement→parcelle** : pas de table `sirene_*_parcelle`, pas de colonne `idu` sur `sirene_etablissements`. Lecteurs actuels : Étude de zone (`zone.py:242,284,334` — comptage concurrents/emplois par NAF dans une **isochrone** `ST_Contains(zone, geom)`, jamais par parcelle) et enrichissement propriétaire **par SIREN** (`app.py:1678,5221`). **Aucun `ST_Within(geom, parcelle)` nulle part.**
- **Témoins (ST_Within réel, `parcels.geom`)** : adresse-only (`qualite_xy='11'`) et adresse+voie (`11,12,21`) → **0 / 0 / 0** sur les 3 témoins. Les points `11` les plus proches de BW0102 sont **à 28-54 m** de la parcelle (`ST_Distance::geography`). Le ST_Within fonctionne île-wide (ex. Saint-Denis ≈ 28 981 établissements tombent dans *une* parcelle) mais **rate systématiquement les témoins** : le géocodage pointe le centroïde d'adresse/voie, pas l'emprise.
- **Fiche** : aucune ligne établissement. §Bâti (témoin BW0102) = *« Emprise bâtie —, Nombre de bâtiments 0, Hauteur non déterminée, Nature du toit non disponible »* — capture `captures/q2-fiche-bati-97415000BW0102.png`. `grep 'etablissement|sirene|naf'` sur le JSON fiche = aucune clé « occupants ».

### Ce qui manque exactement
- La **jointure matérialisée établissement↔parcelle** + la ligne de fiche. **Mais le `ST_Within` pur n'est PAS servable tel quel** (0 sur les témoins alors que des établissements existent à ~30 m) : les positions `voie` — et souvent `adresse` — sont **trop grossières**. Il faut une règle « plus proche parcelle dans un rayon » (`ST_DWithin` + accroche à `adresse_parcelles`/BAN), pas un `ST_Within`. La sortie doit afficher `qualite_xy` et masquer le nom si `diffusible=false`. **Effort : M** (vue matérialisée + règle d'affectation défendable) + **S** pour la ligne fiche une fois la table prête.
- **Précision « voie »** : servable seulement via affectation par rattachement adresse, **pas** par géométrie du point. À dire au client.

---

## 3. Permis annulés + permis d'aménager (Sitadel)

### Verdict : **PARTIEL**
Les 4 fichiers sont ingérés (PC logements, PC locaux, **PA**, **DP** + PD). Les permis **annulés existent en base (4 324)** mais **aucune surface d'affichage ne les distingue** — tout est ramené à « autorisé » / « achevé ».

### Preuves
- **Ingestion** : `src/labuse/ingestion/permits_sdes.py` (SDES/Dido, Sitadel3, dép. 974). 4 datafiles (`permits_sdes.py:57-66`) : `logements`, `locaux`, `pa`, `pd` → **PC-logements ✓ · PC-locaux ✓ · PA ✓ · DP ✓** (les DP arrivent via les datafiles logements/locaux par `TYPE_DAU`), plus PD. L'ancien chemin ODS-Région (`permits.py`) est mort depuis 2023-09.
- **Base `sitadel_permits` = 50 545 lignes.** Pas de colonne `etat_dau` : l'état vit dans **`raw->>'etat'`** (code Sitadel3). Répartition vérifiée psql : `2` autorisé **14 076** · `4` **annulé 4 324** · `5` commencé 11 166 · `6` terminé 20 979 (codes 1/3/7 absents pour le 974).
- **Types** vérifiés psql : `PC` **46 157** · `DP` **2 437** · `PD` **1 136** · `PA` **815**. Les PA et DP **sont bien là**.
- **Surfaces d'affichage — aucune ne montre/filtre l'état, aucune ne se limite au PC** :
  - Fiche « permis à proximité » : `_statut()` (`ingestion/permits.py:183-187`) renvoie *« autorisé le … »* (+ « travaux achevés » si DAACT) — **ignore `etat`** ; la requête (`permits.py:243-260`) n'a **ni filtre état ni filtre type**.
  - Frise (`api/moteurs.py:410-434`) : émet « Permis … autorisé » sans lire `etat` ; le commentaire `moteurs.py:409` invoque un `_ETAT_LABELS` **qui n'existe nulle part** dans le code.
  - Outil Permis / VeillePromoteurs (`api/veille_promoteurs.py:121-136`) : lit `raw->>'etat'` mais le **réduit délibérément** à un binaire `autorisé`/`achevé` (décision OUTILS-FIX-4 A4) → **etat=4/annulé s'affiche « autorisé »**.
  - Signal `permis_actif` (`signaux_vie.py:49-60`), séries Zone (`zone.py:451,546,663`), série marché commune (`moteurs.py:818-820`) : **aucun filtre état** → les annulés gonflent l'activité.
  - `pc_caducs.py:53-56` : traite `etat IN ('4','6')` comme « octroyé » → **mélabellise l'annulé (4) en permis octroyé**.

### Ce qui manque exactement
- **L'état « annulé » (etat=4, 4 324 permis) n'est jamais montré** : sur la fiche, la frise, l'outil Permis, les séries Zone et commune, un permis annulé est présenté à l'identique d'une autorisation valide. **Effort : M** — mapper les codes Sitadel3 vers des libellés (créer le `_ETAT_LABELS` que le code suppose déjà), le propager dans `_statut()`, la frise et `etat_libelle` ; décision produit : filtrer l'annulé des comptages/signaux **ou** l'étiqueter ; corriger `pc_caducs`.
- **Refusé (3) / sans suite (7)** : absents du flux 974 (pas un manque code, la source n'en a pas). Aucune action.
- **PA / DP** : ingérés, mais aucune surface ne les étiquette utilement (PD s'affiche en brut « PD », pas de libellé). **Effort : S** pour libeller PD et remonter PA/DP là où c'est pertinent.

---

## 4. Filtres propriétaire dans « Plus de filtres » (personnes morales)

### Verdict : **PARTIEL**
Le **backend est complet et branché** (5 prédicats PM + « particulier »), la **sérialisation URL / Mes vues / veille est entièrement câblée** — seule **l'UI a été supprimée** le 28/08/2026 (code retiré, récupérable en git).

### Preuves
- **Backend** — fonction filtre `_q_v2_where` (`src/labuse/api/app.py`), prédicats sur `parcelle_personne_morale` (jointure `idu`) :
  - forme juridique `app.py:1667-1672` (`pm_forme`) · dénomination `:1660-1662` (`pm_denom`, + autocomplétion) · SIREN `:1663-1666` (`pm_siren`) · APE/NAF `:1673-1679` (`pm_ape`, jointure `sirene_etablissements.siren`) · **nb dirigeants** `:1680-1687` (`pm_dirig_min/max`, via vue `v_pm_propension_vendre`).
  - **âge du dirigeant = BLOQUÉ RGPD** : `FORBIDDEN_FLAGS_RGPD = {"age_dirigeant"}` (`app.py:1350`), `filtre_age_dirigeant=False` (`config.py:80`). À ne pas exposer.
  - Facettes servies : `GET /proprietaires/facettes` et `/proprietaires/autocomplete` (`app.py:2656,2667`, `proprietaire_facettes.py`).
- **Tables** : `parcelle_personne_morale` **82 701** lignes (`idu, forme_juridique, denomination, siren, millesime…`) ; dirigeants **`pm_dirigeants` 27 146** (RNE/INPI : `nom, prenoms, date_naissance, role_entreprise, date_prise_fonction, actif`) + vue `v_pm_propension_vendre`.
- **Front supprimé** : le composant `SectionProprietaire` **n'existe plus** (ni commenté, ni gaté) — tombstones `FiltreLabuse.tsx:368-371` et `~596-598` : *« SECTION PROPRIÉTAIRE (KF1) RETIRÉE DU PANNEAU (RETOURS-1 R2, Vic 28/08/2026) — FRONT SEULEMENT »*. Ajout git `91e05c85`, retrait `79523a24` → **récupérable tel quel**.
- **Hash / Mes vues / veille — déjà câblés** (aucune leçon ZFANG/FRR à refaire) : `lib/filters.ts` porte `pmForme/pmApe/pmDenom/pmSiren/pmDirigMin/pmDirigMax` dans le type `Filters` **et** `HASH_KEYS` (`pmf/pma/pmd/pms/pdmin/pdmax`, + `proprietaireType→pt`) ; `lib/api.ts:114-119` envoie `pm_*`. Les prédicats persisteraient à l'URL/Mes vues **dès que l'UI existe**.
- **« Particulier » en une ligne SQL** — déjà porté par `proprietaireType='pp'` (`app.py:1628`, `NOT EXISTS parcelle_personne_morale`). Vérifié psql : **349 597 parcelles « particulier »** / 431 663 (≈ 81 %).
- L'écran expose aujourd'hui, dans « Affiner la recherche », une bascule booléenne **« Détenu par une société »** (+ Procédure collective, Succession) — capture `captures/q4-affiner-signaux.png` — mais **aucun** des 5 prédicats fins.

### Ce qui manque exactement
- **Uniquement le remontage de l'UI** `SectionProprietaire` (récupérable depuis `79523a24`) et son branchement aux facettes déjà exposées : forme juridique (chips) · nom + autocomplétion · SIREN · APE/NAF (chips) · nb dirigeants (min/max) · « particulier » (bascule `pt='pp'`). **Effort global : S–M (front seulement)** — aucun code back requis. Décision produit : `age_dirigeant` reste bloqué RGPD.

---

## 5. Street View depuis la fiche

### Verdict : **PARTIEL**
Un **lien Google Maps** existe déjà dans l'en-tête de fiche (ouvre Maps épinglé, onglet neuf). Il n'y a **ni Street View, ni embed, ni clé Google, et le CSP bloquerait un iframe**. Ajouter un panorama Street View est du net-neuf.

### Preuves
- **Existant** : `frontend/src/components/fiche/liensExternes.ts:20-23` `googleMapsUrl()` → `https://www.google.com/maps/search/?api=1&query=lat,lon` (recherche épinglée, **pas** Street View, **pas** embed), rendu en bouton `<a target="_blank">` dans l'en-tête (`Fiche.tsx:753-757`). Vu à l'écran sur les 3 témoins. **Aucun** lien/embed Street View.
- **Clé Google : ABSENTE.** Aucune variable `GOOGLE*/GMAPS*/MAPS_API*/STREETVIEW*` définie (`.env.example`, `deploy/`, `docker-compose*.yml`, `config/`). La seule clé Google jamais envisagée est `solar_api_key` (Google Solar, endpoint stubbé 501), autre API, non configurée. Convention VPS = injection par env (aucun secret en dur).
- **CSP : bloquerait l'iframe.** Le CSP actif est posé par l'app (`src/labuse/api/app.py:309-317`) : `default-src 'self'`, **pas de `frame-src` ni `child-src`** (donc les iframes retombent sur `'self'`), `frame-ancestors 'none'`. `frontend/index.html` : aucune balise CSP. Caddy/nginx : pas de CSP (seul `X-Frame-Options`). → un `<iframe src="https://www.google.com/maps/embed/v1/streetview…">` serait **bloqué**.
- **Tarif Google (fetch 2026-09-27)** : *« The Maps Embed API is free to use with unlimited requests »* et *« There are no short-term (QPS) or long-term (QPD) limits on the Maps Embed API »* ([usage-and-billing](https://developers.google.com/maps/documentation/embed/usage-and-billing)). Le mode **Street View panorama** est un mode de l'Embed API, non facturé séparément ([quickstart](https://developers.google.com/maps/documentation/embed/quickstart)). Exige **une clé API** ([get-api-key](https://developers.google.com/maps/documentation/embed/get-api-key)) ; en prod, un **compte de facturation attaché** (sans frais pour l'Embed API) ou une *Maps Demo Key* (sans carte, prototypage). La clé partant côté client doit être **restreinte par référent HTTP** au domaine LABUSE.

### Ce qui manque exactement
1. **Clé** : projet Google Cloud + compte de facturation, clé Maps Embed API restreinte par référent, injectée par env (nouvelle variable). **Effort : M** (setup console/facturation ; gratuit mais compte requis).
2. **CSP** : ajouter `frame-src https://www.google.com https://*.google.com` à la chaîne CSP `app.py:309-317`. **Effort : S** (une ligne).
3. **Bouton / embed** : soit un simple **lien** Street View à côté du bouton Maps (`liensExternes.ts` + `Fiche.tsx:753`) — **S** ; soit un **iframe embed** inline dans la fiche (`.../embed/v1/streetview?key=…&location=lat,lon`) — **M** (composant + exposition clé + mise en page). L'embed lui-même est gratuit et sans limite.

---

## 6. Filtres bâti actuel (hauteur LiDAR, emprise au sol %, usage BD TOPO)

### Verdict : **PARTIEL**
Deux filtres touchent le bâti aujourd'hui (pas un seul). Les données existent en base à la maille parcelle, mais ne sont **pas branchées** au moteur des filtres (hauteur LiDAR), ne sont exposées **qu'en booléen** (emprise %), ou ne sont **pas attribuées à la parcelle** (usage BD TOPO).

### Preuves
- **Panneau filtre** (`frontend/src/components/panel/FiltreLabuse.tsx`) — capture `captures/q6-filtres-panneau.png`. Filtres rendus : 1·Communes ; 2·Le terrain (Surface, Zonage U/A/N/AU, **« État du sol » = Terrain nu / Terrain bâti**) ; 3·Capacité (SDP restante, case **« Déjà bâti (extension · surélévation) »**, Logements possibles, Destination) ; « Affiner la recherche » (ZFANG, FRR, 7 Signaux de vie). **Deux** filtres touchent le bâti : « État du sol » (partition emprise ≥ 5 %, `app.py:1544-1563`) et « Déjà bâti » (emprise BD TOPO > 0, `app.py:1609-1615`). **Aucun filtre hauteur LiDAR, aucun curseur % d'emprise, aucun filtre usage/nature BD TOPO.**
- **En base, à la maille parcelle** :
  - **Hauteur LiDAR** — `batiment_hauteur_lidar` = **303 452 lignes = 303 452 idu distincts** (agrégat **par parcelle** : `faitage_m, egout_m, hauteur_bdtopo_m, ecart_faitage_bdtopo_m…`). Témoin AN0347 = faîtage 4,8 m / égout 2,7 m.
  - **Emprise en %** — `parcel_filtre_bati.ratio_pct` (**294 865** lignes, toutes non-nulles) + `parcel_residuel.taux_emprise_pct` (int, run servi) déjà utilisé par « État du sol ». Colonne **prête**.
  - **Usage/nature BD TOPO** — stocké **par bâtiment** dans `spatial_layers` (kind=`batiment` : `subtype`=nature ~793 594 « Indifférenciée », 18 641 « Industriel/agricole/commercial », 4 487 « Serre »… ; `attrs->>'usage'`). **Pas d'attribution par parcelle** (aucune colonne `nature_bati/usage_bati` par idu).
- **Le moteur lit-il déjà ces tables ?** L'emprise % est **déjà** dans l'ensemble filtrable (`parcel_residuel.taux_emprise_pct`, `p_model_bati.emprise_bati_m2`), mais en **booléen** (≥ 5 %). La **hauteur LiDAR n'est PAS jointe** au moteur (`_q_v2_where`) — lue seulement par la fiche (`GET /parcels/{idu}/hauteur-lidar`, `app.py:5517`). L'**usage BD TOPO n'est joint nulle part** au moteur.
- **Surélévation** : `parcel_residuel` est une vue sur le run servi (run_seq 10). La colonne **`parcel_residuel.hauteur_source`** existe (DONNEES-FIX-1 Lot C) mais est **VIDE dans le run servi** — vérifié psql : **0 / 431 663** non-vides. Elle est peuplée dans le **run 11** (262 215), mais **run 11 n'est pas servi** (`is_served=f`) et a été rejeté (bug couverture gabarit, cf. RUN11-AUDIT). La case « Déjà bâti (… surélévation) » repose uniquement sur l'emprise BD TOPO, elle **ne lit aucun calcul de surélévation**.

### Ce qui manque exactement
- **Hauteur LiDAR** : données prêtes par parcelle (`batiment_hauteur_lidar`). Manque : (1) une jointure `bhl.idu = p.idu` dans `_q_v2_where`, (2) un contrôle min/max UI + clé hash. **Effort : S.**
- **Emprise % réelle** : colonne prête (`taux_emprise_pct`). Manque : exposer un **seuil numérique** (au lieu du booléen nu/bâti) + curseur UI. **Effort : S.**
- **Usage/nature BD TOPO** : données par bâtiment seulement. Manque : (1) attribution par parcelle (build ou sous-select `ST_Intersects` île), (2) clause filtre, (3) UI. **Effort : M.**
- **Surélévation** : `hauteur_source` vide au run servi ; run 11 (peuplé) rejeté. Manque : un run servable portant la hauteur + une logique de capacité de surélévation (n'existe pas comme colonne distincte). **Effort : L.**

---

## 7. Filtres géométrie (façade sur voie, profondeur, sans copropriété)

### Verdict : **PARTIEL**
La copropriété est **prête et déjà filtrable** (UI seulement masquée). Façade sur voie et profondeur, elles, ne sont **pas matérialisées** : la classification des limites est **calculée à la volée** (batch de plusieurs heures), et il n'existe pas de colonne de profondeur.

### Preuves
- **Classification des limites (voie / séparative / fond)** — **À LA VOLÉE, non matérialisée.** Moteur `src/labuse/gabarit/limites.py` : `classify_parcel_limits` (`:368`) lance des requêtes PostGIS par parcelle (voisins ≤ 0,5 m, voie privée, troncons BD TOPO ≤ 12 m). **Aucune colonne** de classification par parcelle (recherche `has_voie|facade|limite|separative` = néant). Débit mesuré (GEOMETRIE-1) : build gabarit 5,2 → **51,9 p/s** ; bout-en-bout résiduel **20,6 p/s → île ≈ 5,8 h mono-thread**. → **non filtrable interactivement** ; il faudrait matérialiser la classification dans le run.
- **Façade sur voie / profondeur** : la seule colonne façade est `division_or_candidates.residuel_facade_m` — **33 lignes** (jeu de niche « division en or »), pas île-wide. **Aucune colonne de profondeur** nulle part (recherche `profondeur|depth` = néant).
- **Copropriété — EXISTE et déjà filtrable.** `p_model_ext_copro (idu, copro_rnic, copro_dvf)` = **431 663 lignes (île entière)** ; **3 424** parcelles copro (rnic ou dvf) [vérifié psql] ; `rnic_coproprietes` = 2 220 immatriculations brutes. Le moteur expose déjà `s2.copro` : `hors_copro` (`app.py:1421-1422`), facette `copro` avec/sans (`:1691-1696`) ; `api.ts` envoie `hors_copro`/`copro` ; store `horsCopro`/`copro[]`. **Mais le contrôle UI est retiré du panneau** (`FiltreLabuse.tsx:599-614`, sections « Propriétaire » supprimées) → backend vivant, atteignable seulement par URL/copilote.

### Jugement (les filtres bâti Q6 rendent-ils Q7 inutile ?)
Non — ils répondent à des questions distinctes. Les filtres **bâti (Q6)** décrivent *ce qui est déjà sur la parcelle* (sous-bâti, terrain nu). Les filtres **géométrie (Q7)** décrivent *la forme de l'enveloppe constructible* : la **façade sur voie** sépare un lot desservi d'une parcelle enclavée/en drapeau ; la **profondeur** sépare un lot assez profond pour un vrai programme d'une lanière — ni l'un ni l'autre ne se déduit de l'emprise ou de la hauteur. Ils apportent donc un signal de constructibilité réellement distinct. **Exception : la copropriété est déjà couverte** (colonne île entière + clause backend vivante), il suffit de ré-exposer une case. La nuance est le coût : emprise/hauteur/copro sont à la maille parcelle aujourd'hui (bon marché), tandis que façade/profondeur exigent de matérialiser la classification à la volée (batch île ~5,8 h) avant tout filtre interactif — les plus utiles mais les plus chers.

### Ce qui manque exactement
- **Façade sur voie** : classification à la volée non stockée → matérialiser `has_voie`/longueur de façade dans le run (batch ~5,8 h) + clause + UI. **Effort : L.**
- **Profondeur** : aucune colonne → la calculer (OBB / plus longue distance intérieure) et matérialiser par parcelle + clause + UI. **Effort : L.**
- **Sans copropriété** : rien ne manque côté donnée/back (`p_model_ext_copro` 431 663 + clause `s2.copro` + `api.ts` vivants). Ré-exposer une case **« Hors copropriété »**. **Effort : S.**

---

## 8. Fiscalité (zonage A/B/C, bande TVA 2,1 %, Petites Villes de Demain, dérogation stationnement TCSP)

### Verdict : **PARTIEL**
A/B/C et QPV/TVA 2,1 % sont **présents et servis** en fiche. Petites Villes de Demain (**donnée présente, non servie en fiche parcelle**) et la **dérogation stationnement TCSP** (**seuil 800 m affiché, pas appliqué**) sont incomplets. Capture `captures/q8-fiche-fiscalite-97415000AB0134.png`.

### Preuves
- **8a — Zonage A/B/C : EXISTE et servi.** Table **`commune_zonage_abc`** = **24 lignes** (les 24 communes) : **4 en zone A** (L'Étang-Salé, Les Avirons, Saint-Leu, Saint-Paul), **20 en B1** ; millésime « arrêté du 23/06/2026, en vigueur 26/06/2026 ». Servi en fiche (`app.py:4689-4699`, `zonage_commune()`) : témoins BW0102/AB0134 → *« Zonage d'investissement locatif : A — commande PTZ neuf, plafonds loyer/ressources, prix bailleur social »*. Ingestion `ingestion/zonage_abc.py`, filtre `filtres/sources.py:583`. **Le mot « Pinel » n'est jamais servi en fiche** (choix : zonage affirmé, dispositif non affirmé). Manque éventuel = nommer Pinel/Denormandie → **S**.
- **8b — QPV 2024 / NPNRU + bande TVA 2,1 % : EXISTE.** `spatial_layers` kind=`qpv` **57** (13 communes) · kind=`anru` **8** · kind=`tva_primo` **13** (couronnes buffer **500 m** dérivées des QPV, `ingestion/dispositifs.py:28-60`). NPNRU absent de l'open data 974. **Bande déjà calculée et servie** (`app.py:4627-4680`) : 43 825 parcelles intersectent un QPV, 94 891 la bande 500 m. Fiche : *« bande de 300 m (500 m NPNRU sous convention) ; calque LABUSE dérivé à 500 m (majorant) — à confirmer »*. Manque : distinguer le **300 m réglementaire QPV** du **500 m ANRU** (aujourd'hui un seul buffer 500 m majorant). **Effort : S** (recalcul buffer, sources en base).
- **8c — Petites Villes de Demain / ORT / ACV : PARTIEL.** Table **`commune_ort`** peuplée : **11 PVD** (Bras-Panon, Cilaos, Entre-Deux, L'Étang-Salé, La Plaine-des-Palmistes, Les Avirons, Les Trois-Bassins, Petite-Île, Saint-Philippe, Sainte-Rose, Salazie), **4 ACV** (Le Port, Saint-André, Saint-Joseph, Saint-Pierre), 4 « autre ». Ingérée DGALN/ANCT (`ingestion/ort.py`). **MAIS non lue par la fiche parcelle** : `_territoire_fiscal_block` (`app.py:4616-4716`) ne lit pas `commune_ort` ; `statut_commune()` n'a de consommateur qu'en CLI/filtre/sonde ; PVD/ORT/ACV/Denormandie = 0 occurrence dans le JSON fiche. (Le statut ORT est affiché dans le ContextePanel commune, COMMUNE-FIX-1 B8, hors périmètre fiche parcelle.) La **liste ANCT est déjà en base** (pas de web requis). Manque : brancher `commune_ort` dans `dispositifs_dom`/`perimetres` (Denormandie éligible en ORT signée). **Effort : S.**
- **8d — TCSP + dérogation stationnement : PARTIEL.** Géométries en base : `tcsp_station` **44**, `tcsp_troncon` 142, `pole_echange` 61, `transport_arret` **9 956**, `transport_ligne` 300 (pas de GTFS brut, dérivé en `tcsp_station`). Le **seuil 800 m est codé** (`app.py:4787`, réf. art. L151-36 c. urb., loi 2025-1129 du 26/11/2025 art. 20), distance mesurée à vol d'oiseau. **Mais c'est un affichage de proximité** (témoin AB0134 : *« arrêt CHOR 135 m »*), **pas une dérogation de stationnement appliquée** : le moteur de places (`zonage.py`) **ne consomme pas `dist_tcsp`** pour lever/réduire l'obligation. Manque : relier le seuil 800 m au calcul de places (réduction/suppression dans les 800 m d'un TCSP en service). La donnée distance existe déjà. **Effort : M.**

### Synthèse Q8
| Sous-item | Verdict | Manque | Effort |
|---|---|---|---|
| A/B/C (Pinel/PTZ) | EXISTE | mot « Pinel » non servi (choix) | S (si nommer) |
| QPV/NPNRU + TVA 2,1 % | EXISTE | bande unique 500 m ne sépare pas 300/500 | S |
| PVD / ORT / ACV | PARTIEL | `commune_ort` non lue par la fiche parcelle | S |
| TCSP + dérogation stationnement | PARTIEL | seuil 800 m affiché mais pas appliqué en dérogation de places | M |

---

## Tableau final

| # | Feature | Verdict | Ce qui manque | Effort |
|---|---|---|---|---|
| 1 | SAR en couche + condition d'ouverture des zones AU | **PARTIEL** | Couche SAR **réglementaire** officielle (proxy dérivé seul en base, 2 453 géoms) [L] ; exposer le statut AU en fiche (moteur `parcel_au_statut` déjà complet) [S] | L (SAR) / S (AU) |
| 2 | Établissements occupants sur la parcelle | **PARTIEL** | Jointure établissement↔parcelle matérialisée par **rattachement adresse/BAN** (ST_Within pur = 0 sur les témoins) + ligne fiche ; dire la précision `qualite_xy` | M + S |
| 3 | Permis annulés + PA (Sitadel) | **PARTIEL** | L'état **annulé** (4 324) jamais montré (tout ramené à « autorisé ») ; PA/DP **ingérés** mais non libellés | M (annulé) / S (PA-DP-PD) |
| 4 | Filtres propriétaire (PM) dans « Plus de filtres » | **PARTIEL** | **UI seule** à remonter (backend + hash + facettes complets ; « particulier » = 349 597 parcelles déjà en 1 ligne SQL) ; `age_dirigeant` bloqué RGPD | S–M (front) |
| 5 | Street View depuis la fiche | **PARTIEL** | Clé Google Embed (env) [M] + CSP `frame-src google.com` [S] + bouton/embed [S/M] ; l'Embed API (mode Street View) est **gratuit, sans limite** | M + S |
| 6 | Filtres bâti (hauteur LiDAR, emprise %, usage BD TOPO) | **PARTIEL** | Brancher `batiment_hauteur_lidar` au moteur [S] ; exposer seuil % (`taux_emprise_pct`) [S] ; attribution usage BD TOPO par parcelle [M] ; surélévation = run servable portant la hauteur [L] | S / S / M / L |
| 7 | Filtres géométrie (façade voie, profondeur, sans copro) | **PARTIEL** | **Sans copro** = ré-exposer la case (back+donnée 431 663 vivants) [S] ; façade/profondeur = matérialiser la classification à la volée (batch île ~5,8 h) + colonne profondeur [L] | S / L / L |
| 8 | Fiscalité (A/B/C, TVA 2,1 %, PVD, dérogation TCSP) | **PARTIEL** | A/B/C + TVA servis ; brancher `commune_ort` (PVD) en fiche [S] ; séparer bande 300/500 m [S] ; appliquer la dérogation stationnement 800 m TCSP [M] | S / S / M |
