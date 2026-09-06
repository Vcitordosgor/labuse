# COMPTE-RENDU FICHE-1 — Les trous de la fiche parcelle

Branche `feat/fiche-1`, worktree `~/Desktop/labuse-audit`, depuis `origin/main` (`aa4b520c OUTILS-FIX-4`). Rien mergé. Un commit + un push par lot.

## Environnement & pièges

- Editable install `labuse` pointe sur un AUTRE worktree (`~/Desktop/labuse`) → toujours `PYTHONPATH=src` pour tester CE worktree (piège CIRCUIT-5b).
- WeasyPrint : `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib` sinon `OSError libgobject` casse la collecte pytest (FZ-002).

## Suites de départ (avant tout changement)

- **vitest** : 187 passed (43 fichiers).
- **pytest** : `DYLD_FALLBACK_LIBRARY_PATH=/opt/homebrew/lib PYTHONPATH=src python -m pytest -q` → **2689 passed, 4 failed, 50 skipped** en 88 s.
- Les **4 échecs sont PRÉ-EXISTANTS** (base fraîche, avant toute modification FICHE-1), tous liés à l'état DB de test local (`sqlalchemy` / dashboard) :
  - `tests/test_courrier_boucle.py::test_boucle_piste_courrier_reponse`
  - `tests/test_courrier_boucle.py::test_backfill_rattache_par_idu_compte_univoque`
  - `tests/test_dashboard.py::test_ia_log_attribue_au_compte`
  - `tests/test_front_reliquats.py::test_r5_etudier_deux_marges_chacune_dit_son_referentiel`
  - Cible de non-régression : rester à ≤ 4 échecs, ces mêmes 4.

---

## Journal des lots

### Lot 1 — Le bâti (nouveau tiroir « Le bien ») ✅

Nouveau tiroir « Le bien », placé après « Constructibilité » (front + registre).

- **Producteur unique** `bati.le_bien_block(session, idu)` (aucun calcul au front) : emprise bâtie au sol, nombre de bâtiments, hauteur du bâti, surface au sol libre, nature/pente du toit.
- **Emprise bâtie** = empreinte **vecteur BD TOPO** (somme des intersections), COHÉRENTE avec le nombre de bâtiments. **Décision tranchée** : CoSIA sur-détecte à la maille parcelle (ex. 97419000AI0999 : CoSIA 29 010 m² alors que BD TOPO voit 0 bâtiment → « vacant »). Mélanger CoSIA à l'emprise donnait un bloc incohérent. CoSIA est donc servi **à part** (`cosia_detecte_m2`, « détecté non cartographié — à vérifier »), jamais confondu avec l'emprise.
- **Hauteur** = `potentiel._hauteur_bati_m` (BD TOPO, max des bâtiments). **Nb bâtiments** = `bati.fiche_block` (BD TOPO, ≥ 10 m²). **Surface libre** = max(0, surface − emprise).
- **Toit** (LiDAR HD) : nature + pente lues sur le **cache `toiture_lidar` SEUL** via `solaire_toiture.toiture_depuis_cache` — **jamais de requête WMS dans la fiche** (un fetch LiDAR de 60 s à chaque ouverture est exclu ; le cache est chauffé par la fiche soleil / le builder de nuit). Les trois états RETOURS-15 U5 (servie · « non déterminée — pans non nets » · « non calculée — LiDAR indisponible ») voyagent dans `toit.verdict/libelle`. Cache froid → ligne toit muette « non encore relevée », pas un faux.
- **Tiroir omis** si couche bâtiments non ingérée (`le_bien=null`) — jamais un bloc creux.
- **Registre** : `emprise_batie_m2`, `hauteur_bati_m`, `n_batiments` sortis d'`en_attente` (« maquettes d'exports ») et servis ; 3 nouvelles données `surface_libre_sol_m2`, `nature_toit`, `pente_toit_deg`. Robinet `fiche_parcelle_le_bien` ajouté. Les 6 sont **mono-robinet** → auto-pass V5c.
- **Vérifs** : `circuit verrous` 16/16 vert (174 données) · tsc 0 · vitest 187 · `test_fiche1_le_bien.py` 4/4 · doc registre régénéré (+19 lignes, tiroir « Le bien »).

### Lot 2 — Le DPE, rétabli ✅

`dpe_connu` était `en_attente` (« bloc payload construit mais plus affiché », Fiche.tsx:1492) : la fiche premium (`_q_v2_fiche`) ne le servait pas. Rétabli dans le tiroir « Le bien ».

- **Producteur** `_dpe_connu_block(db, idu)` (passe-plat de `dpe_records`, table déjà dans la carte) : sert le **plus récent** (étiquette énergie + GES, date, type de bâtiment) et le **nombre** de DPE connus. Rattachement adresse/BAN → parcelle, donc c'est le DPE du **bâtiment**, pas de la parcelle — le libellé le dit (« DPE du bâtiment »).
- **Plusieurs DPE** → le plus récent servi + « N DPE connus, le plus récent » en source.
- **Aucun DPE** → `null` → le front dit **« non déterminée — aucun DPE rattaché »** (affiché seulement quand il y a du bâti ; jamais sur un terrain nu).
- **Registre** : `dpe_connu` sorti d'`en_attente`, fonction repointée `_dpe_connu_block`, ajouté au robinet `fiche_parcelle_le_bien` (mono-robinet → auto-pass V5c). Test guard `test_eau_dpe_attribuable_au_registre` mis à jour (rétabli, plus en_attente, dpe_ademe non muet). Commentaire mort Fiche.tsx (F2) remplacé.
- **Vérifs** : `circuit verrous` 16/16 vert · tsc 0 · vitest 187 · tests registre/verrous 41/41 · doc régénéré. Vérifié en base : 97411000AC0079 → D/GES B (2026), 97408000AO1568 → E/E (2022), 97411000BD0080 → aucun.

### Lot 3 — Les aléas en détail ✅

Dans « Risques et protections », la fiche ne servait qu'un compte (`n_vigilances`). Ajout de la **liste des aléas** en détail.

- **Producteur** `_aleas_block(db, idu, lines)` : dérivé des **mêmes lignes de cascade servies** (`layer == 'risques'`, arbitrées) que « Pièges et risques » — **doctrine M73 respectée** (aucune relecture de `spatial_layers` pour DÉCIDER un aléa ; la cascade servie est le point de vérité unique). Chaque aléa porte : **nature** (Inondation / Mouvement de terrain / PPR / …, lue sur le libellé arbitré), **niveau** (severity), **part de la parcelle concernée** (lue sur le libellé, `null` = la source ne la dit pas — honnête, jamais un faux 0).
- **Document + date d'approbation du PPR** : **décision tranchée** — la part et la décision d'aléa viennent de la cascade (M73) ; le document + date d'approbation est une **référence réglementaire de commune** (l'arrêté qui a approuvé le PPR/PPRL communal), lue via `_ppr_reference_commune` — une **citation adossée à l'aléa déjà retenu** (esprit CIRCUIT-4), PAS une seconde décision d'aléa. Cohérent avec les lecture-gardes existantes de `served_cascade` qui lisent déjà `spatial_layers`.
- **`n_vigilances` reste** au-dessus (dans le compteur du tiroir). Les aléas structurés **remplacent** les lignes brutes `risques` ; les autres vigilances (accès, sol, SUP…) restent affichées telles quelles.
- **Contrôle d'accord ajouté** (`test_fiche1_aleas.py`) : le nombre d'aléas de la fiche = le nombre de lignes `risques` servies à Pièges et risques, pour toute parcelle du run — les deux écrans ne peuvent pas se contredire. Vérifié en base : 97416000EV1725 → fiche 3 = Pièges 3 (PPR 7 % + réf. arrêtés PPR 2016 / PPRL 2018, Inondation fort, Mvt terrain moyen).
- **Registre** : `aleas_parcelle_liste` (moteur cascade) ajouté au robinet `fiche_parcelle_risques` (mono-robinet → auto-pass V5c).
- **Vérifs** : `circuit verrous` 16/16 vert (176 données) · tsc 0 · vitest 187 · tests cascade/risques 30/30 · doc régénéré.

### Lot 4 — Le stationnement allégé (TCSP) ✅

**Constat affiné** : le bloc TCSP L151-36 était **déjà calculé et affiché** (`_proximites_block` → `f.proximites.tcsp`, rendu dans Réseaux) mais **hors registre** (aucune donnée déclarée — violation de « rien ne s'affiche hors registre »). Lot 4 = fermer le trou + rendre le fait scannable.

- **Registre** : donnée `tcsp_stationnement_allege` (classe, domaine sous_800m/au_dela/aucune_station) déclarée dans `fiche_parcelle_reseaux`, moteur `parcelle_proximites`, fonction `_proximites_block` (drapeau `sous_800m` STRICT). Mono-robinet → auto-pass V5c.
- Le bloc porte déjà tout ce que demande le mandat : **dans le rayon** (sous_800m), **distance** à vol d'oiseau, **station nommée**, **plafond** (1 place/logement, 0,5 en social), **référence d'article** (L151-34 à 36, loi n° 2025-1129). Seuil **800 m strict** (`d < 800`, correction E1 CIRCUIT-4), distance depuis la station (CE 2022).
- **Front** : pastille « dans le rayon 800 m » / « hors rayon » + station + distance en tête, le libellé (plafond + article) conservé dessous.
- **Vérifs** : `circuit verrous` 16/16 vert (177 données) · tsc 0 · vitest 187 · `test_fiche1_tcsp.py` + `test_distance_knn` 3/3 · doc régénéré. Vérifié en base : 97415000AB0790 → station « Karting » à 120 m, sous_800m=vrai, plafond L151-36 servi.

### Lot 5 — La taxe d'aménagement estimée ✅

Servie dans « Constructibilité » pour le scénario table rase du potentiel.

- **Producteur** `_taxe_amenagement_block(db, idu, parcel_id)` : assiette = **surface de plancher du scénario table rase** (`bloc_potentiel.table_rase.plancher_m2`), passée au moteur `taxe_amenagement.calculer` (aucun calcul dans l'endpoint). Sert : assiette (m² + €), taux communal + départemental (avec source), total, lien vers l'outil.
- **Doctrine « aucun taux inventé »** (CIRCUIT-3 lot 6.2) : la table `taxe_amenagement_taux` est seedée VIDE → le taux communal PUBLIC est inconnu → **« taux communal non renseigné »**, le **total n'est pas calculé** (jamais un taux deviné). Le taux départemental = plafond légal 2,5 % « à confirmer ». Dès que SOURCES-1 ingère les délibérations, le total s'affiche.
- **Omise** si le scénario table rase n'est pas constructible (pas d'assiette → `null` → bloc absent).
- **Distincte** de `taxe_amenagement_eur` (outil, taux SAISI) : nouvelle donnée `taxe_amenagement_estimee_eur` (taux PUBLIC), définition différente (V5a OK), mono-robinet `fiche_parcelle_constructibilite`. Lien `PorteOutil` vers l'outil taxe (prefill parcelle) pour changer les hypothèses.
- **Vérifs** : `circuit verrous` 16/16 vert (178 données) · tsc 0 · vitest 187 · `test_fiche1_taxe.py` 3/3 · doc régénéré. Vérifié en base : 97415000BH0057 → assiette 10 084 m², total « non calculable sans taux communal ».

### Lot 6 — Les annonces Radar ✅

Dans « Marché et secteur », la **liste des annonces Radar rattachées** à la parcelle.

- **Producteur** `_radar_annonces_block(db, idu)` : biens VALIDÉS rattachés (`f.valide_at IS NOT NULL`, RADAR P3), datés, avec prix demandé, type, **statut lisible** (en cours / retirée / vendue), lien **fiche annonce interne** (`setRadarToOpen(bien_id) + openRadar()`) et lien portail secondaire (clic logué `radarClic`).
- **Écart demandé/acté** : pour une annonce **en cours** avec une **mutation DVF** sur la parcelle, l'écart prix demandé vs acté (sur €/m² si dispo, sinon total). **Décision tranchée** (écrite) : je réutilise le **concept `ecart_demande_acte_pct`** à la maille parcelle **dans l'item de liste** (champ `ecart_demande_acte_pct`), sans créer un id parcelle-grain dupliqué ni rattacher la donnée commune-médiane (grain différent) au robinet parcelle — V5a préservé.
- **Restructuration** : l'ancien bloc `radar_bien` (un seul bien, dans Propriétaire, **lien portail seulement**, et **hors registre**) est retiré ; la liste complète (tous statuts, **lien fiche annonce interne**) le remplace dans Marché et est **déclarée** (`radar_annonces_liste` → `fiche_parcelle_marche`, mono-robinet).
- **Vérifs** : `circuit verrous` 16/16 vert (179 données) · tsc 0 · vitest 187 · `test_fiche1_radar.py` 3/3 (écart +25 % €/m², retirée → pas d'écart) · doc régénéré. Vérifié en base : 97411000AE0568 → maison 417 500 €, en cours, lien annonce leboncoin.
