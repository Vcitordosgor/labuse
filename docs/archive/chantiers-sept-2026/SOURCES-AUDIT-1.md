# SOURCES-AUDIT-1 — Chaque source sert-elle à quelque chose de visible ?

**Branche** `feat/sources-audit-1` — étape 0 : `main 2cedd096` (`2cedd096541621ceb30a976229509d0e04a3e8d7`). Lecture seule, aucune
correction, aucun retrait, aucun rattachement. Un commit (ce rapport). « Ne merge pas. »

## Le chiffre

# **86 sources sur 94 sont vertes aux quatre contrôles** (Remplie · Lue · Visible · Réinjectable).

Les 8 autres se répartissent en quatre listes courtes (ci-dessous) — aucune n'est un bug caché :
une quasi-vide, deux lues par personne, une sans vanne, et quatre sans table propre *par conception*
(hub, règles code, API en direct, saisie dans une table partagée) qui servent bien le client mais
ne peuvent être « remplies » au sens d'une table à elles.

## La méthode (par la preuve, pas par le code)

- **Remplie** — la table du réservoir a des lignes en base (comptage SQL réel ; `qa/out/bind.tsv`).
  Une table de maille commune à **24 lignes** est *complète* (24 communes), pas vide. Une source
  connectée mais quasi-vide (cas `dpe_ademe`, 16 lignes) est un **non**.
- **Lue** — au moins un *robinet* la lit vraiment (couche carte, donnée de fiche parcelle/commune,
  outil, export, cascade), **nommé** file:symbole → écran. Tracé sur le code réel (`src/labuse/`,
  `frontend/src/`) par 4 passes croisées ; le registre `registre/robinets.py`+`lectures.py` sert de
  contre-vérité. Une source lue par personne, ou seulement par un fabricant/scoring/QA non servi, est **non**.
- **Visible** — le robinet affiche quelque chose à l'écran sur un témoin choisi par SQL pour être
  concerné. **Capture** dans `captures/sources-audit/`. Témoins : parcelle `97410000AN0347`,
  commune `97411` (Saint-Denis), et pour chaque couche le centroïde de sa plus grande entité.
- **Réinjectable** — une vanne fonctionnelle existe (job/commande d'ingestion pour les robots, dépôt
  pour les manuelles) **et** sa dernière exécution a réussi. Preuve : registre CRON-1 (`labuse jobs`),
  `data_sources.last_sync_at`, `ingestion_runs.ok` — `qa/out/jobs_dernier_passage.txt`.

> Légende verdict : 🟢 vert aux 4 · 🟡 au moins un contrôle non/n-a. Cellule : ✅ oui · ❌ non ·
> ➖ n/a (sans objet par conception) · ✅* visible via export seulement.

## Les quatre listes

1. **Vides** (connectée mais table sans lignes utiles) — **DPE ADEME (logements existants)** (`dpe_ademe`).
2. **Lues par personne** (aucun robinet ne la sert à un écran) — **Cadastre d'époque (Etalab / PCI vecteur DGFiP)** (`cadastre_epoque`), **Sudocuh (procédures d'urbanisme)** (`sudocuh`).
   - `cadastre_epoque` : lue **seulement** par un fabricant d'ingestion (`cadastre_historique.py:rattacher_par_geometrie`, qui corrige `sitadel_permits.geom`) ; aucun endpoint ne SELECT la table, la fiche n'affiche qu'une prose statique.
   - `sudocuh` : lue **seulement** par le modèle candidat `scoring/p_v2/qv14.py` (feature `anciennete_plu`) ; le run servi en prod est `q_v11_m137`, où cette feature ne contribue pas → 0 surface client.
3. **Jamais affichées** (lue mais rien à l'écran sur un témoin concerné) — **Cadastre d'époque (Etalab / PCI vecteur DGFiP)** (`cadastre_epoque`), **Sudocuh (procédures d'urbanisme)** (`sudocuh`).
   *(= les deux mêmes : non lues par un robinet d'écran, donc rien à afficher.)*
4. **Sans vanne** (pas de ré-injection qui marche) — **DEAL Réunion (WMS/WFS)** (`deal_wms_wfs`).
   - `deal_wms_wfs` : **hub** (canal DEAL servi par les proxys `qpv_2024`/`npnru`) — aucune ingestion propre, aucune table propre. Il s'affiche via ses proxys mais n'a pas de vanne à lui.

### Sans table propre — *par conception* (n/a sur « Remplie », mais servies au client)
**DEAL Réunion (WMS/WFS)** (`deal_wms_wfs`), **Loyers DHUP — carte des loyers (annonces)** (`loyers_dhup`), **RTAA DOM (textes réglementaires)** (`rtaa_dom`), **SIRENE** (`sirene_recherche_entreprises`), **VRD / assainissement (SPANC)** (`spanc_epci`).
Ce ne sont pas des vides : `rtaa_dom` = règles portées par le code ; `sirene_recherche_entreprises`
= API INSEE interrogée en direct ; `loyers_dhup` = repli JSON embarqué (`data/carte_loyers_reunion_2025.json`) ;
`spanc_epci` = saisie collectif/non-collectif matérialisée dans `parcel_anc` (table partagée) ;
`deal_wms_wfs` = hub. `rtaa_dom` est n/a sur les quatre (aucune donnée à lire, à afficher ou à ré-injecter).

## Le tableau (94 sources)

| Source | Remplie | Lue par (robinet nommé) | Visible (capture) | Réinjectable (vanne) | Verdict |
|---|---|---|---|---|---|
| 50 pas géométriques — limite haute (DEAL) | ✅ 163 lignes | couche `cinquante_pas`→carte | ✅ `couche_cinquante_pas.png` | ✅ labuse ingest-cinquante-pas | 🟢 |
| ABF / Monuments historiques | ✅ 200 lignes | couche `abf` couches_tuyau:couche_tuile → carte ; cascade rule abf → onglet Risques fiche | ✅ `couche_abf.png` | ✅ labuse ingest-abf | 🟢 |
| ACV / PVD / ORT (DGALN — liste des communes) | ✅ 19 lignes | fiche_commune.py:ort (commune_ort)→fiche commune 'ACV/PVD/ORT' ; filtres/sources acv→Denormandie | ✅ `fiche_commune_1.png` | ✅ labuse ingest-ort | 🟢 |
| AZI / TRI — inondation (Géorisques GASPAR) | ✅ 167 lignes | couche `tri_zone`→carte ; azi_tri.py:azi_tri_commune (azi_communes)→ContextePanel Risques fiche commune | ✅ `couche_tri_zone.png` | ✅ labuse ingest-azi-tri | 🟢 |
| Annuaire de l'administration (service-public.fr / DILA) | ✅ 460 lignes | mairies→app.py bloc K2 mairie_de→fiche commune (coordonnées) + outil pack PLU (annuaire_services=admin Contacts seul) | ✅ `fiche_commune_1.png` | ✅ labuse ingest-annuaire-services/ingest-mairies | 🟢 |
| BAN PLUS — lien adresse ↔ bâtiment (IGN) | ✅ 738540 lignes | bati.py:le_bien_block (ban_plus_liens WHERE idu)→fiche parcelle 'Le bien' | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-ban-plus | 🟢 |
| BD ORTHO 20 cm (IGN) | ✅ 36518 lignes | ortho.py:equipements + fiche_commune (n_piscines) (parcel_equipements)→fiche Réseaux + outil Piscines (ortho_tiles=build, ortho_detections=QC ML) | ✅ `fiche_commune_1.png` | ✅ labuse ortho-tiles/ortho-refresh | 🟢 |
| BD ORTHO IRC (IGN) | ✅ 1608138 lignes | ortho_detections→parcel_equipements→ortho.py:equipements→badges fiche ; parcel_vegetation→PDF (vegetation_zonal_acc interne) | ✅ `fiche_parcelle_3.png` | ✅ labuse ortho-refresh/ortho-detect | 🟢 |
| BD TOPO IGN | ✅ 1091872 lignes | couches_tuyau sert batiment/cimetiere/construction_*/zone_activite/bassin_versant/axe_structurant/ligne_ht→carte ; ravine→cascade phase1→Risques (v… | ✅ `couche_batiment.png` | ✅ labuse ingest-mvt (BD TOPO) | 🟢 |
| BODACC (procédures collectives) | ✅ 28775 lignes | projets.py:_signaux_parcelles (bodacc_procedures)→Projets/carte ; events.py→notifications ; app.py (bodacc_annonces_owner)→bloc propriétaire (bodac… | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-bodacc | 🟢 |
| BPE INSEE | ✅ 35544 lignes | couche `amenite_bpe`→carte ; app.py:_PROX_EQUIP→proximités fiche | ✅ `couche_amenite_bpe.png` | ✅ labuse ingest-amenites-affichage | 🟢 |
| Base Adresse Nationale | ✅ 756280 lignes | app.py:_ban_adresse (adresses/adresse_parcelles) → fiche parcelle ; pré-dossier PDF | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-ban | 🟢 |
| Cadastre (API Carto PCI) | ✅ 431663 lignes | couche `limites_parcelles`→carte ; parcels lue par toute fiche /parcels/{idu} (socle du produit) | ✅ `couche_limites_parcelles.png` | ✅ labuse ingest-island/ingest-real | 🟢 |
| Cadastre d'époque (Etalab / PCI vecteur DGFiP) | ✅ 6526 lignes | SEUL lecteur ingestion/cadastre_historique.py:rattacher_par_geometrie = FABRICANT (corrige sitadel_permits.geom) ; aucun endpoint ne SELECT la tabl… | ❌ `—` | ✅ labuse ingest (cadastre époque) | 🟡 |
| Cartofriches (Cerema) | ✅ 372 lignes | couche `friche`→carte ; cascade etage1 FricheLayer→fiche parcelle | ✅ `couche_friche.png` | ✅ labuse ingest-cartofriches | 🟢 |
| CatNat (arrêtés GASPAR / Géorisques) | ✅ 426 lignes | fiche_commune.py:risques (catnat_arretes) → fiche commune + outil risques | ✅ `fiche_commune_1.png` | ✅ labuse ingest-catnat | 🟢 |
| Cerema / GéoLittoral — indicateur d'érosion côtière | ✅ 24168 lignes | couche `trait_de_cote`→carte ; cascade | ✅ `couche_trait_de_cote.png` | ✅ labuse ingest-deal-carmen | 🟢 |
| Classement sonore ITT (Cerema) | ✅ 1004 lignes | couche `bruit_route`→carte ; cascade rule bruit_route → onglet Risques fiche | ✅ `couche_bruit_route.png` | ✅ labuse ingest-bruit-route | 🟢 |
| CoSIA (couverture du sol IA, IGN) | ✅ 3205312 lignes | couche `piscine_cosia`→carte + bloc fiscal ; p_model_bati_cosia→parcel_bati_revele→'Le bien' (qa_cosia_bati/parcel_cosia_couverture=interne ; batim… | ✅ `couche_piscine_cosia.png` | ✅ labuse ingest-cosia | 🟢 |
| Communes La Réunion — contours (IGN ADMIN EXPRESS via geo.api.gouv, seed) | ✅ 24 lignes | couche `limites_communes` via mvt_communes→carte (Repères) | ✅ `couche_limites_communes.png` | ✅ seed (référentiel embarqué) | 🟢 |
| Consommation d'espaces NAF (Cerema — portail de l'artificialisation) | ✅ 24 lignes | rarete.py:compute_rarete (commune_conso_enaf)→'Enveloppe ZAN' ContextePanel ; carnet secteur | ✅ `fiche_commune_1.png` | ✅ labuse ingest (ENAF) | 🟢 |
| Contours IRIS (IGN/INSEE) | ✅ 344 lignes | anc_service.statut_anc (JOIN kind=iris_insee)→Viabilisation fiche + PDF ; zone.py→étude de zone (couche iris_insee non servie sur carte, lue en joi… | ✅ `outil_etude-zone.png` | ✅ labuse ingest-iris-rp | 🟢 |
| Coût de construction (EPTB SDES + choix LABUSE) | ✅ 3 lignes | faisabilite/engine.py (cout_construction_ref)→outil Faisabilité + bilan Financier | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-cout-construction | 🟢 |
| DEAL Réunion (WMS/WFS) | ➖ hub (proxys qpv/npnru) | hub sans table propre — data servie via proxys couches qpv_2024/npnru (eux-mêmes Lus)→carte | ✅ `fiche_parcelle_3.png` | ❌ hub (aucune ingestion propre) | 🟡 |
| DEAL Réunion — PPR / aléas | ✅ 164 lignes | couche `ppr`→carte ; cascade risques (ppr) → onglet Risques fiche (verdict/exclusion) | ✅ `couche_ppr.png` | ✅ labuse ingest-georisques (ppr) | 🟢 |
| DEAL — cartes de bruit stratégiques (CBS) | ✅ 6 lignes | couche `bruit_carte`→carte ; onglet Risques fiche (cascade) | ✅ `couche_bruit_carte.png` | ✅ labuse ingest-bruit-cartes | 🟢 |
| DFI — documents de filiation informatisés (DGFiP) | ✅ 409623 lignes | moteurs.py:_filiation_parcelle (dfi_filiation)→fiche parcelle Filiation | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-dfi | 🟢 |
| DGFiP — parcelles des personnes morales | ✅ 544271 lignes | app.py:_q_v2_fiche (parcelle_personne_morale) + proprietaire_historique (pm_proprietaires_millesimes) → bloc propriétaire fiche | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-personnes-morales/ingest-pm-millesimes | 🟢 |
| DPE ADEME (logements existants) | ❌ 16 lignes (quasi-vide ; attendu : logements des 24 communes) | app.py:_dpe_connu_block (dpe_records)→payload dpe_connu→fiche 'DPE du bâtiment' leBien.tsx (robinet câblé ; table quasi-vide 16 l.) | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-dpe | 🟡 |
| DVF / valeurs foncières | ✅ 300005 lignes | moteurs.py baromètre/prix (dvf_mutations*, dvf_prix_sortie_neuf)→Baromètre/fiche marché ; couche vefa_neuf→carte+cascade Marché (dvf_secteur_median… | ✅ `couche_vefa_neuf.png` | ✅ labuse refresh-dvf | 🟢 |
| EDF Réunion — lignes moyenne tension HTA (open data) | ✅ 19480 lignes | couche `ligne_mt`→carte ; cascade fiche_couches2 ligne_mt 50m→onglet Risques fiche | ✅ `couche_ligne_mt.png` | ✅ labuse ingest (EDF HTA) | 🟢 |
| Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen) | ✅ 411 lignes | couche `ens` (via kind enp) → carte ; cascade ens → onglet Risques fiche | ✅ `couche_enp.png` | ✅ labuse ingest-deal-carmen | 🟢 |
| FRR ex-ZRR — zone spéciale d'action rurale (Légifrance) | ✅ 47 lignes | couche `frr`→carte + territoire_fiscal→bloc fiscal fiche ; territoire_fiscal_commune→fiche commune | ✅ `couche_frr.png` | ✅ labuse ingest-qpv (frr/zfang) | 🟢 |
| Fibre Arcep — Ma connexion internet (immeuble) | ✅ 330051 lignes | zone.py (arcep_immeubles, immeubles FttH)→outil Étude de zone / fiche | ✅ `outil_etude-zone.png` | ✅ labuse ingest-arcep | 🟢 |
| Filosofi INSEE (carreaux 200 m) | ✅ 400152 lignes | fiche_commune.py:population (filosofi_carreaux_200m)→ContextePanel ; marche_secteur→MarcheSecteurBlock fiche (p_model_filo=build scoring) | ✅ `fiche_commune_1.png` | ✅ labuse ingest (Filosofi) | 🟢 |
| Forêts publiques (ONF) | ✅ 65 lignes | couche `foret_publique`→carte ; cascade phase1→fiche parcelle | ✅ `couche_foret_publique.png` | ✅ labuse ingest (forêts ONF) | 🟢 |
| GPU — droit de préemption urbain (info-surf) | ✅ 202 lignes | couche `dpu`→carte ; cascade phase1 DpuLayer→fiche parcelle | ✅ `couche_dpu.png` | ✅ labuse ingest-gpu-infos | 🟢 |
| GPU — emplacements réservés (prescriptions CNIG) | ✅ 10490 lignes | couches front `er`+`ebc` (kind plu_gpu_prescription subtypes 05/01)→carte | ✅ `couche_er.png` | ✅ labuse ingest-gpu-infos | 🟢 |
| GPU — espaces boisés classés (prescriptions CNIG) | ✅ 10490 lignes | couche virtuelle `ebc`→plu_gpu_prescription(subtype 01)→carte (et `er` subtype 05) | ✅ `couche_er.png` | ✅ labuse ingest-gpu-infos | 🟢 |
| GPU — zonages d'assainissement | ✅ 278943 lignes | parcel_anc→anc_service:statut_anc→ViabilisationBlock fiche ; couche zonage_assainissement→outil Servitudes invisibles | ✅ `outil_risques.png` | ✅ labuse ingest-gpu-infos | 🟢 |
| Géorisques | ✅ 1093 lignes | couche via virtuels alea_inondation/alea_mvt (kind georisque_alea)→carte | ✅ `couche_alea_inondation.png` | ✅ labuse ingest-georisques | 🟢 |
| Géorisques — CASIAS (anciens sites industriels) | ✅ 531 lignes | couche front `casias` (kind sol_pollue subtype casias)→carte ; cascade Risques→fiche | ✅ `couche_casias.png` | ✅ labuse ingest-georisques | 🟢 |
| Géorisques — ICPE | ✅ 1268 lignes | couche `icpe`→carte ; cascade→onglet Risques fiche | ✅ `couche_icpe.png` | ✅ labuse ingest-georisques | 🟢 |
| Géorisques — cavités souterraines | ✅ 151 lignes | couche `cavite`→carte ; cascade cavite → onglet Risques fiche | ✅ `couche_cavite.png` | ✅ labuse ingest-georisques | 🟢 |
| Géorisques — mouvements de terrain | ✅ 3085 lignes | cascade etage1:MvtLayer (kind mvt, cascade_rules spatial_kind:mvt)→onglet Risques fiche (couche map alea_mvt lit un AUTRE kind georisque_alea) | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-georisques | 🟢 |
| Géorisques — secteurs d'information sur les sols (SIS) | ✅ 531 lignes | couche front `sis` (kind sol_pollue subtype sis)→carte ; cascade Risques→fiche | ✅ `couche_casias.png` | ✅ labuse ingest-sis-projets | 🟢 |
| Géorisques — sites et sols pollués | ✅ 531 lignes | couche `sol_pollue` (kinds sis/casias)→carte ; cascade sol_pollue → onglet Risques fiche | ✅ `couche_casias.png` | ✅ labuse ingest-georisques/ingest-sis-projets | 🟢 |
| IGN BD CARTO V5 — occupation du sol | ✅ 1643 lignes | couche `artificialisation`→carte ; ocs_ge→cascade phase1 OcsGeLayer→onglet Règles fiche (ZAN) | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest (BD CARTO) | 🟢 |
| INPI RNE (dirigeants) | ✅ 29270 lignes | veille_promoteurs.py + modules.py (pm_dirigeants)→outil Scan patrimoine/Veille promoteurs (pm_dirigeant_gigogne→v_pm_propension→score_v indirect) | ✅ `outil_veille-promoteurs.png` | ✅ labuse ingest-inpi-rne/ingest-inpi-gigogne | 🟢 |
| INPN / patrinat — espaces protégés | ✅ 411 lignes | couche front `enp` (kind ens)→carte | ✅ `couche_enp.png` | ✅ labuse ingest-georisques | 🟢 |
| INSEE RP Logement 2023 | ✅ 24 lignes | app.py:_compute_commune_contexte (commune_insee_logement)→ContextePanel 'Population & logement' fiche commune (tenure) | ✅ `fiche_commune_1.png` | ✅ labuse ingest-rp-logement | 🟢 |
| INSEE RP2022 — bases IRIS (logement, population) | ✅ 344 lignes | zone.py (iris_rp, P22_*)→Étude de zone ; fiche 'Autour'/quartiers | ✅ `outil_etude-zone.png` | ✅ labuse ingest-iris-rp | 🟢 |
| INSEE RP2022 — fichier détail Logements (EGOUL) | ✅ 374 lignes | anc_maille_taux→anc_service:statut_anc (taux secteur)→bloc assainissement fiche (rp_logement_commune=métadonnée) | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-rp-logement | 🟢 |
| Inventaire SRU (DHUP) | ✅ 24 lignes | fiche_commune/flash (commune_contexte_sru)→fiche commune 'SRU' + comparateur + projets | ✅ `fiche_commune_1.png` | ✅ labuse ingest (SRU) | 🟢 |
| LiDAR HD — MNH 50 cm (IGN) | ✅ 306144 lignes | solaire_toiture.py (toiture_lidar)→fiche solaire ; batiment_hauteur_lidar→bâti 3D + faisabilite constructibilité (lidar_dalle_grille=état batch) | ✅ `outil_prospection-solaire.png` | ✅ labuse ingest (LiDAR dalles) | 🟢 |
| Loyers DHUP — carte des loyers (annonces) | ➖ repli JSON embarqué | loyers.py:fiche_block (JSON embarqué)→export md/html /parcels/{idu}/export SEULEMENT (pas la fiche React live) | ✅* `(export md/html — pas d'écran React)` | ✅ dépôt manuel | 🟡 |
| Loyers OLL — ADIL Réunion / AGORAH (réseau des observatoires) | ✅ 326 lignes | regle loyer_median_eur_m2 (oll_loyers/oll_zonage)→fiche commune 'Loyers' | ✅ `fiche_commune_1.png` | ✅ labuse ingest-oll | 🟢 |
| NPNRU (DEAL Réunion / ANCT) | ✅ 16 lignes | couche `anru`→carte ; _compute_commune_contexte (anru_quartiers)→ContextePanel 'Quartiers prioritaires' fiche commune | ✅ `couche_anru.png` | ✅ labuse ingest-qpv (anru) | 🟢 |
| OCS GE (IGN) — occupation du sol et artificialisation | ✅ 846206 lignes | bati.py:le_bien_block (parcel_ocsge, % artificialisé)→'Le bien' fiche ; couche `artificialisation`→carte | ✅ `couche_artificialisation.png` | ✅ labuse ingest (OCS GE) | 🟢 |
| OSM — transport (pôles d'échange & téléphérique) | ✅ 68 lignes | couches `telepherique`+`pole_echange`→carte | ✅ `couche_telepherique.png` | ✅ labuse ingest-amenites | 🟢 |
| OpenStreetMap / Overpass | ✅ 453224 lignes | couche `amenite`→carte + score amenites cascade→onglet Marché ; osm_faux_positif→motif exclusion cascade fiche | ✅ `couche_amenite.png` | ✅ labuse ingest-amenites | 🟢 |
| PEB — plans d'exposition au bruit (DGAC via annexes GPU) | ✅ 8 lignes | couche `peb`→carte ; cascade peb → onglet Risques fiche | ✅ `couche_peb.png` | ✅ labuse ingest-gpu-infos | 🟢 |
| PLH des 5 EPCI (extraction documentaire) | ✅ 5 lignes | fiche_commune.py:plh (plh_epci WHERE epci)→fiche commune 'PLH' | ✅ `fiche_commune_1.png` | ✅ dépôt manuel (PLH) | 🟢 |
| PVGIS (Commission européenne) | ✅ 447343 lignes | modules.py:prospection_solaire (parcel_solar)→outil Prospection solaire + fiche soleil (solar_grid=intermédiaire) | ✅ `outil_prospection-solaire.png` | ✅ labuse ingest (PVGIS) | 🟢 |
| Parc National de La Réunion (INPN) | ✅ 3 lignes | couche `parc_national`→carte (tuyau) | ✅ `couche_parc_national.png` | ✅ labuse ingest-georisques | 🟢 |
| Parkings OSM (loi APER) | ✅ 901 lignes | faisabilite/viabilisation_build:aper_note (parkings_aper)→note APER tiroir Urbanisme fiche + PDF | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-amenites | 🟢 |
| QPV 2024 (ANCT) | ✅ 70 lignes | couche `qpv`→carte ; _territoire_fiscal_block (kind qpv + tva_primo)→fiche (TVA réduite/QPV) | ✅ `couche_qpv.png` | ✅ labuse ingest-qpv | 🟢 |
| RGE ALTI (altimétrie) | ✅ 150193 lignes | parcel_terrain (rgealti_pente_5m)→fiche Terrain (pente) ; couche `pente`→carte + cascade PenteLayer (couche altitude non lue ; MNT rgealti_mnt_5m v… | ✅ `fiche_parcelle_3.png` | ✅ labuse ortho-pente/ingest (RGE ALTI) | 🟢 |
| RNB — Référentiel National des Bâtiments | ✅ 1231587 lignes | rnb_batiments→bati.py:le_bien_block→bloc 'Le bien' fiche (rnb_rattachement_bdtopo=builder) | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest (RNB) | 🟢 |
| RNIC — registre national des copropriétés (Anah) | ✅ 2220 lignes | app.py (rnic_coproprietes WHERE parcelle_idu)→bloc 'Division (copropriétés)' fiche | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-rnic | 🟢 |
| RPG — déclarations agricoles (IGN/ASP) | ✅ 38460 lignes | couche `safer` (RPG/SAFER)→carte 'Foncier agricole déclaré' | ✅ `couche_safer.png` | ✅ labuse ingest (RPG) | 🟢 |
| RPLS — répertoire des logements locatifs sociaux (SDES) | ✅ 24 lignes | app.py:_q_v2_fiche (rpls_commune)→fiche 'Marché' (parc social) + PDF | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest (RPLS) | 🟢 |
| RTAA DOM (textes réglementaires) | ➖ règles portées par le code | aucune table — règles RTAA DOM portées par le code (constructibilité) ; rien à lire en base | ➖ `—` | ➖ règles code / repli embarqué (rien à réinjecter) | 🟡 |
| Radar (pige d'annonces) | ✅ 337 lignes | pige/client.py:lister/detail (pige_biens/annonces/faits/prix_historique)→Radar ; releves.py (radar_releves)→Marché (pige_captures/interets_agence=i… | ✅ `radar.png` | ✅ labuse radar-depot-html/radar-cycle-* | 🟢 |
| Ravines — domaine public fluvial (DEAL Carmen) | ✅ 281 lignes | couche `dpf`→carte ; cascade phase1 DpfLayer→fiche parcelle | ✅ `couche_dpf.png` | ✅ labuse ingest-deal-carmen | 🟢 |
| Recherche d'entreprises (DINUM) | ✅ 12380 lignes | score_v_fetch:fetch_owner_enrichment (connector live, JOB)→owner_enrichment/owner_denom_lookup→score_v→parcel_v_score→ScoreV2Block fiche (build-the… | ✅ `fiche_parcelle_3.png` | ✅ API directe (re-requête à la volée) | 🟢 |
| SIRENE | ➖ API INSEE en direct | connector live confirme la PM propriétaire ; affichage APE via table jumelle sirene_etablissements (proprietaire_facettes/_pm_identite)→carte d'ide… | ✅ `fiche_parcelle_3.png` | ✅ API directe (re-requête à la volée) | 🟡 |
| SIRENE établissements géolocalisés | ✅ 158515 lignes | zone.py:etude_de_zone (sirene_etablissements)→outil Étude de zone (concurrents/emplois) ; fiche 'Autour' + PDF Flash | ✅ `outil_etude-zone.png` | ✅ labuse ingest-sirene-etab | 🟢 |
| SITADEL (autorisations d'urbanisme) | ✅ 97615 lignes | app.py:permits_geojson→couche Permis SITADEL ; modules.py→outil Permis ; moteurs.py/events→fiche 'Autour' + baromètre commune | ✅ `outil_permis.png` | ✅ labuse ingest-permits | 🟢 |
| SUP — assiettes GPU (API Carto) | ✅ 417 lignes | couche `sup` (table tuyau_sup)→carte ; /map/couche-detail/sup→détail au clic | ✅ `couche_sup.png` | ✅ labuse ingest-sup | 🟢 |
| Sudocuh (procédures d'urbanisme) | ✅ 24 lignes | SEUL lecteur scoring/p_v2/qv14.py:226 (sudocuh_procedures)→feature anciennete_plu présente UNIQUEMENT dans le run candidat q_v14 ; run servi = q_v1… | ❌ `—` | ✅ labuse ingest-sudocuh | 🟡 |
| Systèmes d'endiguement et zones protégées (DEAL Lizmap) | ✅ 117 lignes | couche `endiguement`→carte ; cascade fiche_couches2→onglet Risques fiche | ✅ `couche_endiguement.png` | ✅ labuse ingest-endiguement | 🟢 |
| TCSP — voies bus en site propre (OSM) | ✅ 188 lignes | couche virtuelle `tcsp` (tcsp_zone+tcsp_troncon+tcsp_station)→carte | ✅ `couche_tcsp.png` | ✅ labuse ingest-amenites | 🟢 |
| Taux de taxe foncière — fichier REI (DGFiP) | ✅ 24 lignes | fiche_commune.py:fiscalite (commune_rei)→fiche commune 'Taxe foncière (REI)' | ✅ `fiche_commune_1.png` | ✅ labuse ingest-rei | 🟢 |
| Taxe d'aménagement — taux communaux (délibérations) | ✅ 24 lignes | taxe_amenagement.py:taux_communal_public (taxe_amenagement_taux)→_taxe_amenagement_block fiche + outil Financier (câblé ; table seed vide) | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-taxe-amenagement | 🟢 |
| Trafic RN (Région Réunion — SIR) | ✅ 692 lignes | zone.py:trafic_zone→POST /outils/etude-zone→outil EtudeZone 'Trafic routes nationales' (véh./j) | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest-trafic-rn | 🟢 |
| Transport public — GTFS (PAN, 7 réseaux) | ✅ 10317 lignes | couches transport_arret/transport_ligne/pole_echange→carte ; cascade transport_ligne 400m→Réseaux fiche | ✅ `couche_transport_arret.png` | ✅ labuse ingest (GTFS) | 🟢 |
| Urbanisme PLU/GPU (API Carto) | ✅ 19589 lignes | couches plu_gpu_zone/prescription→carte ; app.py:_reglement_plu_block (plu_reglement_extrait)→'Règlement d'urbanisme' fiche | ✅ `couche_plu_gpu_zone.png` | ✅ labuse ingest-gpu-infos | 🟢 |
| VRD / assainissement (SPANC) | ➖ saisie → parcel_anc (pas de table propre) | saisie collectif/non-collectif → parcel_anc.zone_anc → anc_service:statut_anc → bloc assainissement fiche | ✅ `fiche_parcelle_3.png` | ✅ dépôt manuel | 🟡 |
| ZFANG — zone franche d'activité nouvelle génération (Légifrance) | ✅ 48 lignes | couche `zfang`→carte ; territoire_fiscal (territoire_fiscal_commune)→fiche 'Dispositifs territoriaux' + fiche commune + PDF | ✅ `couche_zfang.png` | ✅ labuse ingest-qpv (zfang) | 🟢 |
| ZNIEFF (INPN/MNHN) | ✅ 162 lignes | couche `znieff`→carte ; cascade znieff → onglet Risques fiche | ✅ `couche_znieff.png` | ✅ labuse ingest-georisques | 🟢 |
| Zonage ABC des communes (DHUP) | ✅ 24 lignes | fiche_commune.py:zonage_abc (commune_zonage_abc)→fiche commune 'Zonage A/B/C' | ✅ `fiche_commune_1.png` | ✅ labuse ingest-zonage-abc | 🟢 |
| Zones humides — inventaires DEAL (Carmen) | ✅ 3122 lignes | couche `zone_humide`→carte (tuyau) | ✅ `couche_zone_humide.png` | ✅ labuse ingest-deal-carmen | 🟢 |
| data.regionreunion.com — Potentiel foncier | ✅ 2453 lignes | cascade phase2 (potentiel_foncier_region)→onglet Marché fiche (bonus potentiel_foncier_region ; pas de couche map servie) | ✅ `fiche_parcelle_3.png` | ✅ labuse ingest (potentiel foncier) | 🟢 |

## Preuves jointes
- `captures/sources-audit/` — 56 `couche_*.png` (une par couche carte, sur son témoin SQL) +
  `fiche_parcelle_1..5.png` (fiche parcelle témoin, blocs dépliés) + `fiche_commune_1..3.png`
  (contexte commune 97411) + `outil_*.png` (étude de zone, prospection solaire, permis, comparateur
  communes, veille promoteurs, patrimoine, risques/servitudes, taxe d'aménagement) + `radar.png` +
  `page_sources.png`. Chaque source du tableau pointe sa capture.
- `qa/out/bind.tsv` — le binding brut 94 sources → slug → tables/couches → comptes.
- `qa/out/jobs_dernier_passage.txt` — `labuse jobs status` + dernier passage réel (DB) des ingestions.
- Scripts (lecture seule) : `qa/sources_audit_bind.py`, `qa/sources_audit_vannes.py`,
  `qa/lue_verdicts.py`, `qa/synthese.py` ; captures : `frontend/qa/_sourcesaudit_*.mjs` (worktree couches-tuyau).

## Pièges rencontrés (pour le mandat de correction)
- **`labuse jobs status` local = « jamais »** : l'état JSON des jobs vit sur le VPS ; le dernier passage
  RÉEL se lit en base (`last_sync_at`, `ingestion_runs.ok`). Ne pas conclure « job mort » sur l'état local.
- **Notes de réservoir périmées** : `taxe_amenagement` porte encore la note « a_faire — taux à saisir »,
  mais la table est **remplie** (24 communes, part communale 5 %, DGFiP DELTA, maj 2026-09-08) et sa vanne
  `ingest-taxe-amenagement` a tourné → verte. Le verdict porte sur l'état DB, pas sur la note.
- **Kinds virtuels** (`_RESOLUTION_OVERRIDE`) : `sol_pollue`→`casias`/`sis`, `ens`→`enp`,
  `plu_gpu_prescription`→`er`/`ebc`, `georisque_alea`→`alea_inondation`/`alea_mvt`, tcsp→3 morceaux.
  Un grep du kind brut conclut faussement « non servi ».
- **24 lignes = complet** pour les tables de maille commune (ne pas les compter « presque vides »).
