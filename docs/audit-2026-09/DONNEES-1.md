# DONNEES-1 — Lot 1 : la matrice données × surfaces

*Chaque donnée en base est-elle montrée quelque part ?* — audit en lecture seule.

- **Branche** : `feat/donnees-1` (worktree `labuse-donnees`), depuis `main` **373a8833** (HEAD après merge de `feat/outils-audit-2`).
- **Aucune correction dans ce lot.** Généré par `scripts/donnees1_matrice.py` (données mécaniques) + traçage manuel des verdicts (preuves : `qa/lue_verdicts.py`, agents de traçage DONNEES-1). Volumes = `count(*)` réel (le `n_live_tup` de `pg_stat_user_tables` est périmé — piège connu).

## Méthode

Deux populations, deux niveaux de lecture :

1. **Le registre — 261 données** (`src/labuse/registre/donnees.py`). Le mandat en annonçait 258 ; `main` en compte **261** depuis `OUTILS-FIX-5 lot 6` (Successions M28 / Blocs fonciers M29 au registre des robinets) et les lots EXPORTS/COMMUNE mergés après l'écriture du mandat. J'audite les 261 réellement présentes.
2. **Les 89 tables de réservoir** (`src/labuse/registre/tables.py`, hors `spatial_layers`). C'est **là** que se cache le « travail pour rien » : le registre est discipliné (test `test_circuit2_lot1`, garde G6) — *toute* donnée déclarée est servie par ≥1 robinet — donc une donnée « à zéro croix » au sens strict n'existe pas au registre. Le gisement de données ingérées-mais-jamais-montrées est au niveau des **colonnes/tables physiques** qui n'ont jamais donné lieu à une donnée affichée.

**Surfaces (colonnes)** : fiche parcelle · fiche commune · les 17 outils (registre front `frontend/src/components/outils/registry.ts`) · les 4 documents (Dossier, Financier, Apporteur, Pré-dossier PC) · Copilote · carte (couches + fonds). Une colonne **« Autres écrans »** rattrape ce qui s'affiche hors mandat (Radar/veille, Projets, CRM, notifications, page client, admin) pour qu'aucun affichage ne soit compté « nulle part » à tort.

**Verdict par table** : `DISPLAYED` (sert directement une donnée du registre) · `DERIVE` (brute lue par l'ingestion, servie via un cache/table dérivée — p. ex. le cache nocturne fiche-commune, `parcel_ocsge`, `parcel_solar`) · `MACHINERIE` (lue par l'app mais pour une jointure/QC/scoring, jamais un champ montré) · `DARK` (ingérée, mise à jour, surveillée — atteint **aucun** écran) · `RETIRE` (orpheline documentée dans `tables.py`, conservée sans lecteur).

## Les trois chiffres

**Au niveau des 261 données du registre :**

- **N — affichées quelque part : 259.** 212 sur ≥1 surface du mandat, 47 uniquement sur des écrans secondaires (voir Partie A bis — toutes correctement placées : 23 saisies du questionnaire Financier + 24 compteurs admin/notifications/accueil).
- **Lues mais jamais affichées : 0** (le registre garantit un robinet par donnée).
- **Déclarées « en attente » (servies par personne, par dessein) : 2** — `mixite_seuil_m2`, `mixite_quota_pct` (chantier réglementaire EXPORTS-2, verrouillées par test).

**Au niveau des 89 tables de réservoir (le vrai gisement) :**

- **Affichées (DISPLAYED + DERIVE) : 66.**
- **K — lues mais jamais un champ montré (MACHINERIE) : 17.** Légitime (jointures spatiales, caches de scoring, QC ML, journaux) — détaillé en Partie C.
- **M — ingérées/surveillées, lues par aucun code de service (DARK + RETIRE) : 6.** C'est le « travail pour rien » : **4 DARK vivantes** + **2 RETIRE** déjà documentées.

Les 4 DARK vivantes : `bodacc_depots` · `rp_logement_commune` · `parcel_cosia_couverture` · `vegetation_zonal_acc`. Les deux premières sont les cibles du **Lot 2** ; les deux autres sont des artefacts de précalcul (raison de ne pas les montrer, Partie C).

---
<!-- généré par scripts/donnees1_matrice.py — ne pas éditer à la main -->
- Données du registre : **261**
- Affichées sur ≥1 surface du mandat (N) : **212**
- Affichées UNIQUEMENT hors mandat (autres écrans) : **47**
- Déclarées en attente (servies par aucun robinet, par dessein) : **2** mixite_seuil_m2, mixite_quota_pct

Codes colonnes : `FP`=Fiche parcelle · `FC`=Fiche commune · `Et`=Étudier un bien · `Fa`=Faisabilité · `Tx`=Taxe d'aménagement · `Pg`=Pièges et risques · `PL`=PLU · `Cp`=Comparer des parcelles · `As`=Assemblage · `Sc`=Scan patrimoine · `Cr`=Courrier propriétaire · `So`=Prospection solaire · `Cm`=Communes · `Pm`=Permis · `De`=Densifier l'existant · `EZ`=Étude de zone · `Tp`=Remonter le temps · `Bl`=Blocs fonciers · `Su`=Successions à venir · `D1`=Dossier · `D2`=Financier · `D3`=Apporteur · `D4`=Pré-dossier PC · `Co`=Copilote · `Ca`=Carte (couche) · `Au`=Autres écrans


### niveau parcelle (127)

| donnée | FP | FC | Et | Fa | Tx | Pg | PL | Cp | As | Sc | Cr | So | Cm | Pm | De | EZ | Tp | Bl | Su | D1 | D2 | D3 | D4 | Co | Ca | Au |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tier_opportunite | ✕ |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  | ✕ | ✕ |
| zone_plu_famille | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  | ✕ | ✕ |
| classe_residuel |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| surface_parcelle_m2 |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |
| capacite_logements | ✕ |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| sdp_residuelle_m2 | ✕ |  |  | ✕ |  |  |  |  |  |  |  |  |  |  | ✕ |  |  | ✕ | ✕ | ✕ |  |  |  |  |  |  |
| potentiel_verdict | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |
| charge_fonciere_eur | ✕ |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| taxe_amenagement_eur |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| taxe_amenagement_estimee_eur | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| rtaa_exigences | ✕ |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| radar_annonces_liste | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| n_vigilances | ✕ |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| sar_divergence | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| aleas_parcelle_liste | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| prod_spec_kwh_kwc | ✕ |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| azimut_bati_deg |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| n_parcelles_bloc |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |
| rang_tier | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| prix_terrain_secteur_eur_m2 | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ | ✕ |  |  |  | ✕ |
| prix_sortie_bati_eur_m2 | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ventes_100m_n | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| pente_deg | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| piscine_m2 | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| exposition_versant | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| cosia_detecte_m2 | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| distance_arret_m | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| tcsp_stationnement_allege | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| n_permis_proximite | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| verdict_icd | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| divisible_classe | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| destination_statut |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |
| assemblage_parcelles_n |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| assemblage_surface_m2 |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| mixite_clause | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| cout_construction_saisi_eur_m2 |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| marge_frais_saisie_pct |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| prix_demande_saisi_eur |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| prix_achat_revente_saisi_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| travaux_revente_saisi_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| prix_revente_saisi_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| scenario_saisi |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| logements_vises_saisi |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| typologie_moyenne_saisi |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| part_sociale_saisi_pct |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| stationnement_type_saisi |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| prix_refuse_saisi_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| frais_acquisition_saisi_pct |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| commission_apporteur_saisi_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| honoraires_techniques_saisi_pct |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| vrd_saisi_eur_m2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| cout_place_stationnement_saisi_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| aleas_saisi_pct |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| taxe_amenagement_saisi_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| prix_sortie_saisi_eur_m2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| prix_vente_bailleur_saisi_eur_m2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| marge_visee_saisi_pct |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| regime_tva_saisi |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| duree_portage_saisi_mois |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| apport_saisi_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| taux_apport_saisi_pct |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| verdict_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| zonage_plu_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  | ✕ | ✕ |
| densifier_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| limites_parcelles_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| dpe_connu | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| adresse_ban | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| parcelle_geometrie | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| reglement_plu_bloc | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| historique_permis_liste | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| voisinage_100m_liste | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| dvf_parcelle_liste | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| coproprietes_liste | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| viabilisation_verdict | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| equipements_proximite_liste | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| perimetres_dispositifs_liste | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| surface_vendable_m2 | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |
| surface_plancher_m2 | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| marge_surelevation_m | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| part_logements_egout_pct | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ventes_retenues_n | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ventes_ecartees_n | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| bilan_ca_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| bilan_cout_construction_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| bilan_vrd_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| bilan_marge_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| bilan_frais_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| ecart_prix_demande_pct |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| bilan_demolition_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| sensibilite_cout_construction |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| bilan_frais_acquisition_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| bilan_honoraires_techniques_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| bilan_stationnement_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| bilan_aleas_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| bilan_depollution_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| bilan_portage_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| redevance_archeologie_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| charge_fonciere_basse_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| charge_fonciere_haute_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| sensibilite_prix_sortie |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| seuil_rentabilite_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| prix_revient_eur_m2 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| prix_achat_historique_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |
| mixite_seuil_m2 ⏳ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| mixite_quota_pct ⏳ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| emprise_batie_m2 | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| hauteur_bati_m | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| part_artificialisee_pct | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| usage_sol_dominant | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ban_plus_adresses_bati | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| rnb_batiments_liste | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| n_batiments | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| surface_libre_sol_m2 | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| nature_toit | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| pente_toit_deg | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| er_emplacement_reserve | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ebc_classe | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| dpu_perimetre | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| peb_zone | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| dispositifs_parcelle | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| fibre_parcelle | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| sis_classe | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| casias_statut | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| endiguement_zone_protegee | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| sols_parcelle | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| filiation_parcelle | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| iris_quartier | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |

### niveau commune (80)

| donnée | FP | FC | Et | Fa | Tx | Pg | PL | Cp | As | Sc | Cr | So | Cm | Pm | De | EZ | Tp | Bl | Su | D1 | D2 | D3 | D4 | Co | Ca | Au |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| tranche_prix_vefa |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| n_extraits_plu |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| simulplu_resultat |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| comparateur_composite |  |  |  |  |  |  |  | ✕ |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |
| stock_opportunites |  | ✕ |  |  |  |  |  | ✕ |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |
| velocite_delai_median_mois |  | ✕ |  |  |  |  |  | ✕ |  |  |  |  | ✕ | ✕ |  |  |  |  |  |  |  |  |  | ✕ |  |  |
| permis_5a_n |  |  |  |  |  |  |  | ✕ |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |
| deficit_sru_pts |  | ✕ |  |  |  |  |  | ✕ |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |
| pression_zan_ha |  |  |  |  |  |  |  | ✕ |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |
| prix_neuf_vefa_acte_eur_m2 |  | ✕ |  |  |  |  |  | ✕ |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |
| prix_neuf_observe_eur_m2 | ✕ | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |
| prix_ancien_median_eur_m2 |  | ✕ |  |  |  |  |  | ✕ |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |
| n_piscines |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |
| mutations_12m_n |  | ✕ |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |
| acquisitions_pm_n |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |
| permis_12m_n |  | ✕ |  |  |  |  |  |  |  | ✕ |  |  |  | ✕ |  |  |  |  |  |  |  |  |  | ✕ |  |  |
| point_mort_n |  | ✕ |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |
| n_densifiables |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |
| n_successions_veille |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |
| n_blocs_pm |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |
| annonces_actives_n |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| prix_demande_median_eur_m2 |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| delai_vente_median_j |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| ecart_demande_acte_pct |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| statut_plu |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| zan_reste_ha |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| taux_lls_pct |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |
| lls_inventaire_n |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| plh_objectif_logements_an |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| parc_social_rpls_logements | ✕ | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| prix_terrain_zone_eur_m2 |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| loyer_median_eur_m2 |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| n_parcelles_commune |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| part_zone_U_pct |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| part_zone_AU_pct |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| part_zone_A_pct |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| part_zone_N_pct |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ppr_pct |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| catnat_n |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| catnat_arretes_liste |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| habitants_n |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| vacance_pct |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| qpv_n |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| n_procedures_plu |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| couverture_commune_pct |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| autres_loges_pct |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| parcelles_par_zone_n |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| gpu_brut_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| cinquante_pas_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| znieff_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| bpe_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| alea_inondation_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| alea_mvt_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| transport_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| axes_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| lignes_ht_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| tcsp_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| dispositifs_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| vefa_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| ppr_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| parc_national_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| equip_osm_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| mairie_coordonnees |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| zan_evolution_commune |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| zonage_abc_logement |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| zfang_regime_commune |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| frr_classement_commune |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| er_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| ebc_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| dpu_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| sup_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| rpg_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| azi_tri_commune |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| tfpb_taux_pct |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| tfpnb_taux_pct |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| ort_statut |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| sis_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| casias_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| bruit_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| iris_commune_quartiers |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

### niveau zone (6)

| donnée | FP | FC | Et | Fa | Tx | Pg | PL | Cp | As | Sc | Cr | So | Cm | Pm | De | EZ | Tp | Bl | Su | D1 | D2 | D3 | D4 | Co | Ca | Au |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| population_zone | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  | ✕ |
| n_concurrents_zone |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |
| emplois_fourchette |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |
| revenu_approche_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |
| trafic_mja |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |
| depots_secteur_n | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

### niveau proprietaire (5)

| donnée | FP | FC | Et | Fa | Tx | Pg | PL | Cp | As | Sc | Cr | So | Cm | Pm | De | EZ | Tp | Bl | Su | D1 | D2 | D3 | D4 | Co | Ca | Au |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n_parcelles_pm |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  | ✕ |
| type_proprietaire | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ | ✕ |  |  |  |  |  |  |  |
| evenements_proprietaire_liste | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| dirigeant_pm_signal |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| proprietaire_timeline_liste | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |

### niveau annonce (1)

| donnée | FP | FC | Et | Fa | Tx | Pg | PL | Cp | As | Sc | Cr | So | Cm | Pm | De | EZ | Tp | Bl | Su | D1 | D2 | D3 | D4 | Co | Ca | Au |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| prix_demande_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |

### niveau global (42)

| donnée | FP | FC | Et | Fa | Tx | Pg | PL | Cp | As | Sc | Cr | So | Cm | Pm | De | EZ | Tp | Bl | Su | D1 | D2 | D3 | D4 | Co | Ca | Au |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| n_communes_rnu |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| copilote_compte_parcelles |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |
| n_veilles |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| projet_cadrage_n |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| projet_retenues_n |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| crm_cartes_n |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| n_notifications |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| n_bascules_7j |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| n_biens_du_jour |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| n_biens_veille |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| n_parcelles_ile |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| n_sources |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| run_label_servi |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| prix_flash_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| n_a_faire |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| n_sources_surveillees |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| ecart_candidat_pct |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| ia_cout_eur |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| n_depots_a_verifier |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| n_comptes_actifs |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| courrier_demandes_n |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| annee_ortho |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |
| pipeline_entrees_n |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| usage_outil_n |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |
| communes_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| tuiles_plan_ign |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| tuiles_ortho_2025 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| tuiles_ortho_1950_1965 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| tuiles_ortho_2000_2005 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| tuiles_ortho_2006_2010 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| tuiles_ortho_2011_2015 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| tuiles_ortho_2016_2020 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| tuiles_ortho_2021_2023 |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| copilote_texte_web |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |  |
| peb_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| dpf_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| zone_humide_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| artificialisation_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| batiments_3d_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| enp_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |
| cout_construction_ref_eur_m2 |  |  |  | ✕ |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |
| bruit_carte_couche |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  |  | ✕ |  |

## Partie B — lignage des tables de réservoir → affichage réel

Verdicts : **DISPLAYED** 33 · **DERIVE** 33 · **MACHINERIE** 17 · **DARK** 4 · **RETIRE** 2

| table | réservoir | lignes | verdict | trace / raison |
|---|---|---:|---|---|
| `adresse_parcelles` | ban | 416 365 | DISPLAYED | sert adresse_ban |
| `adresses` | ban | 339 915 | DISPLAYED | sert adresse_ban |
| `anc_maille_taux` | insee_rp2022_egoul | 350 | DERIVE | lue par l'app (anc_service.py) — sert via une table dérivée/donnée.fonction |
| `anc_office_eau_commune` | office_eau_chroniques | 6 | RETIRE | chroniques Office de l'eau (6 l.) — RETIRÉ 13/09, supplanté par anc_maille_taux (RP2022 EGOUL), conservé sans lecteur. |
| `annonces` | bodacc | 0 | MACHINERIE | trace admin d'annonces (chaîne 3) — CREATE/INSERT, jamais lue. |
| `annuaire_services` | annuaire_service_public | 436 | DERIVE | 436 services DILA → page admin « Contacts institutionnels » SEULEMENT (hors surfaces client ; les 24 mairies passent par la table mairies). |
| `anru_quartiers` | npnru | 8 | DERIVE | lue par l'app (app.py) — sert via une table dérivée/donnée.fonction |
| `arcep_immeubles` | arcep_fibre | 330 051 | DISPLAYED | sert fibre_parcelle |
| `azi_communes` | georisques_azi_tri | 39 | DERIVE | → fiche commune Risques « AZI/TRI » (azi_tri.py:azi_tri_commune). |
| `ban_plus_liens` | ban_plus | 738 540 | DERIVE | lue par l'app (bati.py) — sert via une table dérivée/donnée.fonction |
| `batiment_hauteur_lidar` | lidar_hd_mnh | 303 452 | DISPLAYED | sert hauteur_bati_m, marge_surelevation_m |
| `bodacc_annonces_owner` | bodacc | 1 418 | DERIVE | lue par l'app (app.py) — sert via une table dérivée/donnée.fonction |
| `bodacc_depots` | bodacc | 14 078 | DARK | dépôts de comptes annuels des PM (14 k) — le frère bodacc_procedures sert les événements ; les dépôts ne sont lus par aucun écran. → Lot 2 : signal PM. |
| `bodacc_procedures` | bodacc | 674 | DISPLAYED | sert evenements_proprietaire_liste |
| `bodacc_sondages` | bodacc | 12 605 | MACHINERIE | journal de sondage BODACC (scoring/état interne). |
| `cadastre_historique` | cadastre_epoque | 6 526 | MACHINERIE | fabricant : corrige sitadel_permits.geom à l'ingestion (qa/lue_verdicts « non ») ; aucun endpoint ne la SELECT. |
| `catnat_arretes` | catnat_gaspar | 426 | DISPLAYED | sert catnat_n |
| `commune_conso_enaf` | enaf_cerema | 24 | DISPLAYED | sert pression_zan_ha, zan_reste_ha |
| `commune_contexte_sru` | sru_dhup | 24 | DISPLAYED | sert deficit_sru_pts, taux_lls_pct |
| `commune_insee_logement` | insee_rp_logement | 24 | DISPLAYED | sert autres_loges_pct, habitants_n, vacance_pct |
| `commune_ort` | anct_ort | 19 | DERIVE | → fiche commune « ACV/PVD/ORT » (fiche_commune.py:ort) + filtre Denormandie. |
| `commune_rei` | dgfip_rei | 24 | DERIVE | → fiche commune « Taxe foncière (REI) » (fiche_commune.py:fiscalite ; cache commune). |
| `commune_zonage_abc` | zonage_abc_dhup | 24 | DERIVE | → fiche commune « Zonage A/B/C » (fiche_commune.py:zonage_abc). |
| `cout_construction_ref` | cout_construction_sdes | 3 | DERIVE | → outil Faisabilité + bilan Financier (engine.py:_couts_construction_ref). |
| `dfi_filiation` | dgfip_dfi | 409 623 | DISPLAYED | sert filiation_parcelle |
| `dpe_records` | dpe_ademe | 1 123 | DISPLAYED | sert dpe_connu |
| `dvf_mutation_detail` | dvf | 55 016 | MACHINERIE | détail de mutation — compagnon « interne » (qa/lue_verdicts) ; les prix montrés viennent de dvf_mutations/_parcelle. |
| `dvf_mutations` | dvf | 29 566 | DISPLAYED | sert ecart_demande_acte_pct, prix_ancien_median_eur_m2, prix_terrain_secteur_eur_m2 … |
| `dvf_mutations_histo` | dvf | 110 477 | DERIVE | lue par l'app (moteurs.py) — sert via une table dérivée/donnée.fonction |
| `dvf_mutations_parcelle` | dvf | 102 551 | DISPLAYED | sert dvf_parcelle_liste, ecart_demande_acte_pct, mutations_12m_n … |
| `dvf_prix_sortie_neuf` | dvf | 12 | DERIVE | lue par l'app (fiche_commune.py, moteurs.py) — sert via une table dérivée/donnée.fonction |
| `dvf_secteur_medianes` | dvf | 2 359 | DISPLAYED | sert prix_terrain_secteur_eur_m2 |
| `filosofi_carreaux_200m` | filosofi_carreaux | 14 773 | DISPLAYED | sert population_zone, revenu_approche_eur |
| `iris_rp` | insee_rp_iris | 344 | DISPLAYED | sert iris_quartier |
| `lidar_dalle_grille` | lidar_hd_mnh | 2 665 | MACHINERIE | état batch des dalles LiDAR (reprise). |
| `mairies` | annuaire_service_public | 24 | DISPLAYED | sert mairie_coordonnees |
| `mobpro_commune` | mobpro | 0 | RETIRE | MOBPRO domicile-travail — RETIRÉ 06/09 (code mort, maille infra-communale absente INSEE) ; table VIDE (0 l.), remplacée par SIRENE. |
| `ocsge_evolution` | ocsge | 10 633 | DERIVE | → « Enveloppe ZAN » (artificialisation 2017→2022) via moteurs/commune.py. |
| `ocsge_sol` | ocsge | 391 803 | DERIVE | → « Le bien » (% artificialisé) via parcel_ocsge + couche artificialisation. |
| `oll_loyers` | loyers_oll | 133 | DERIVE | → fiche commune « Loyers » (marche_commune.py:ligne9_loyer). |
| `oll_zonage` | loyers_oll | 193 | DERIVE | → zonage loyer OLL, support de « Loyers » (fiche commune). |
| `ortho_detections` | bd_ortho,bd_ortho_irc | 19 919 | MACHINERIE | détections ML brutes (QC) ; les piscines servies passent par parcel_equipements. |
| `ortho_tiles` | bd_ortho | 5 041 | MACHINERIE | grille/checkpoint de tuiles pour la détection ML ; le fond ortho vient du WMTS IGN, les piscines de parcel_equipements. |
| `owner_denom_lookup` | recherche_entreprises_dinum | 2 650 | MACHINERIE | cache résolution dénomination→SIREN du Score V (2,6 k). |
| `owner_enrichment` | recherche_entreprises_dinum | 9 730 | MACHINERIE | cache enrichissement DINUM du Score V (9,7 k) — débranché de l'affichage, réservé au Score V (lectures.py). |
| `p_model_bati_cosia` | cosia | 321 314 | DISPLAYED | sert tier_opportunite |
| `p_model_filo` | filosofi_carreaux | 385 379 | MACHINERIE | jointure Filosofi par parcelle — entrée du modèle de scoring. |
| `parcel_amenites` | osm_overpass | 431 663 | DISPLAYED | sert equipements_proximite_liste |
| `parcel_anc` | gpu_zonage_assainissement | 278 685 | DERIVE | lue par l'app (anc_service.py) — sert via une table dérivée/donnée.fonction |
| `parcel_cosia_couverture` | cosia | 1 947 019 | DARK | couverture CoSIA par classe et par parcelle (1,9 M) — précalcul « interne » (qa/lue_verdicts), aucun lecteur de service. |
| `parcel_equipements` | bd_ortho | 11 558 | DISPLAYED | sert n_piscines, piscine_m2 |
| `parcel_ocsge` | ocsge | 431 663 | DERIVE | lue par l'app (bati.py) — sert via une table dérivée/donnée.fonction |
| `parcel_solar` | pvgis | 431 663 | DISPLAYED | sert prod_spec_kwh_kwc |
| `parcel_vegetation` | bd_ortho_irc | 431 663 | DERIVE | lue par l'app (data.py) — sert via une table dérivée/donnée.fonction |
| `parcelle_personne_morale` | dgfip_parcelles_pm | 82 701 | DISPLAYED | sert n_parcelles_pm, type_proprietaire |
| `parcels` | cadastre_api_carto,cadastre_etalab_bulk | 431 663 | DISPLAYED | sert assemblage_parcelles_n, assemblage_surface_m2, charge_fonciere_eur … |
| `parkings_aper` | parkings_osm_aper | 901 | DERIVE | lue par l'app (viabilisation_build.py) — sert via une table dérivée/donnée.fonction |
| `pige_annonces` | radar_pige | 108 | DISPLAYED | sert n_depots_a_verifier |
| `pige_biens` | radar_pige | 109 | DISPLAYED | sert annonces_actives_n, ecart_demande_acte_pct, n_depots_a_verifier … |
| `pige_captures` | radar_pige | 0 | MACHINERIE | captures HTML brutes de la pige (interne). |
| `pige_clics` | radar_pige | 3 | DERIVE | lue par l'app (client.py) — sert via une table dérivée/donnée.fonction |
| `pige_depots` | radar_pige | 8 | DISPLAYED | sert n_depots_a_verifier |
| `pige_faits` | radar_pige | 109 | DISPLAYED | sert ecart_demande_acte_pct, n_depots_a_verifier, prix_demande_median_eur_m2 … |
| `pige_interets_agence` | radar_pige | 0 | MACHINERIE | intérêts d'agence de la pige (interne). |
| `pige_prix_historique` | radar_pige | 0 | DERIVE | lue par l'app (intake.py, client.py) — sert via une table dérivée/donnée.fonction |
| `plh_epci` | plh_epci | 5 | DISPLAYED | sert plh_objectif_logements_an |
| `plu_reglement_extrait` | gpu_plu_api_carto | 3 258 | DERIVE | → fiche « Règlement d'urbanisme » (app.py:_reglement_plu_block) + outil PLU. |
| `pm_dirigeant_gigogne` | inpi_rne | 2 124 | MACHINERIE | dirigeants gigogne (2,1 k) → v_pm_propension → contexte cascade (drapeau 0 pt) ; le signal dirigeant montré vient de pm_dirigeants. |
| `pm_dirigeants` | inpi_rne | 27 146 | DISPLAYED | sert dirigeant_pm_signal |
| `pm_proprietaires_millesimes` | dgfip_parcelles_pm | 461 570 | DISPLAYED | sert proprietaire_timeline_liste |
| `qa_cosia_bati` | cosia | 445 190 | MACHINERIE | QA CoSIA vs BD TOPO (445 k) — « interne » (qa/lue_verdicts). |
| `radar_releves` | radar_pige | 0 | DERIVE | lue par l'app (releves.py) — sert via une table dérivée/donnée.fonction |
| `rgealti_mnt_5m` | rge_alti | 2 | DERIVE | → altitude/MNT via parcel_enrichment (exposition, viabilisation). |
| `rgealti_pente_5m` | rge_alti,rge_alti_5m | 2 793 | DERIVE | → fiche « Terrain » (pente) via parcel_terrain + couche pente + cascade. |
| `rnb_batiments` | rnb | 414 081 | DERIVE | lue par l'app (bati.py) — sert via une table dérivée/donnée.fonction |
| `rnb_rattachement_bdtopo` | rnb | 817 506 | MACHINERIE | jointure spatiale RNB↔BD TOPO (817 k) + filtre QC ; les identifiants RNB montrés viennent de rnb_batiments. |
| `rnic_coproprietes` | rnic_anah | 2 220 | DERIVE | lue par l'app (app.py) — sert via une table dérivée/donnée.fonction |
| `rp_logement_commune` | insee_rp2022_egoul | 24 | DARK | 24 variables logement RP2022 par commune — « métadonnée » (qa/lue_verdicts) ; l'égout passe par anc_maille_taux. → Lot 2. |
| `rpls_commune` | rpls_sdes | 24 | DERIVE | lue par l'app (fiche_commune.py, app.py) — sert via une table dérivée/donnée.fonction |
| `sirene_etablissements` | sirene_etablissements | 158 515 | DERIVE | lue par l'app (proprietaire_facettes.py, app.py) — sert via une table dérivée/donnée.fonction |
| `sitadel_permits` | sitadel | 50 545 | DISPLAYED | sert depots_secteur_n, historique_permis_liste, n_permis_proximite … |
| `solar_grid` | pvgis | 15 680 | MACHINERIE | grille PVGIS intermédiaire ; le productible vient de parcel_solar. |
| `sudocuh_procedures` | sudocuh | 24 | MACHINERIE | lue uniquement par le scoring du run CANDIDAT q_v14 (anciennete_plu) ; run servi q_v11_m137 → 0 surface client (qa/lue_verdicts « non »). |
| `taxe_amenagement_taux` | taxe_amenagement | 24 | DERIVE | lue par l'app (taxe_amenagement.py) — sert via une table dérivée/donnée.fonction |
| `territoire_fiscal_commune` | frr_ex_zrr,zfang | 24 | DISPLAYED | sert perimetres_dispositifs_liste |
| `toiture_lidar` | lidar_hd_mnh | 28 | DERIVE | lue par l'app (solaire_toiture.py) — sert via une table dérivée/donnée.fonction |
| `trafic_rn` | trafic_rn | 692 | DERIVE | lue par l'app (zone.py) — sert via une table dérivée/donnée.fonction |
| `vegetation_zonal_acc` | bd_ortho_irc | 1 156 556 | DARK | stats zonales végétation par parcelle (1,16 M) — étage intermédiaire « interne » agrégé dans parcel_vegetation (lui affiché). |
| `via_permits_geo` | sitadel | 47 070 | DISPLAYED | sert n_permis_proximite |

## Partie A bis — les 47 données servies UNIQUEMENT hors surfaces du mandat

| donnée | niveau | écran(s) secondaire(s) |
|---|---|---|
| delai_vente_median_j | commune | outil:Marché |
| prix_demande_eur | annonce | fiche:Fiche bien (Radar) |
| n_veilles | global | veille:Veilles (critères + déclenchements) |
| projet_cadrage_n | global | projets:Bandeau d'analyse (compteur projet); projets:Projets (cadrage · retenues · vivier) |
| projet_retenues_n | global | projets:Projets (cadrage · retenues · vivier) |
| crm_cartes_n | global | crm:Pipeline (kanban, cartes par colonne) |
| n_notifications | global | notification:Cloche (événements) |
| n_bascules_7j | global | notification:Brief du matin; page_client:Accueil — cette semaine |
| n_biens_du_jour | global | notification:Digest quotidien (mail); notification:Radar — digest quotidien (Brevo ID 12) |
| n_biens_veille | global | notification:Radar — alerte de veille (Brevo ID 13) |
| n_parcelles_ile | global | page_client:Accueil — bloc chiffres |
| n_sources | global | admin:Données › Catalogue (sources); admin:Données › Circuit (fourmilière + Radar + cohérence); page_client:Accueil — bloc chiffres; page_client:Sources de données |
| run_label_servi | global | admin:Données › Circuit (fourmilière + Radar + cohérence); page_client:Accueil — bloc chiffres |
| prix_flash_eur | global | page_client:/flash (formulaire public) |
| n_a_faire | global | admin:Pilotage (KPI à faire / à jour) |
| n_sources_surveillees | global | admin:Données › Circuit (fourmilière + Radar + cohérence) |
| ecart_candidat_pct | global | admin:Données › Mise à jour (Injecter·Calculer·Basculer) |
| ia_cout_eur | global | admin:IA & quotas Copilote |
| n_depots_a_verifier | global | admin:Radar (dépôts à vérifier) |
| n_comptes_actifs | global | admin:Licences (comptes, essais, quotas) |
| pipeline_entrees_n | global | crm:Retour terrain (étiquettes de contact) |
| couverture_commune_pct | commune | page_client:Couverture des sources |
| parcelles_par_zone_n | commune | outil:Filtres (sélecteur de zones PLU) |
| usage_outil_n | global | admin:Données produit (usage outils + retours) |
| prix_achat_revente_saisi_eur | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| travaux_revente_saisi_eur | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| prix_revente_saisi_eur | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| scenario_saisi | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| logements_vises_saisi | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| typologie_moyenne_saisi | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| part_sociale_saisi_pct | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| stationnement_type_saisi | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| prix_refuse_saisi_eur | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| frais_acquisition_saisi_pct | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| commission_apporteur_saisi_eur | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| honoraires_techniques_saisi_pct | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| vrd_saisi_eur_m2 | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| cout_place_stationnement_saisi_eur | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| aleas_saisi_pct | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| taxe_amenagement_saisi_eur | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| prix_sortie_saisi_eur_m2 | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| prix_vente_bailleur_saisi_eur_m2 | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| marge_visee_saisi_pct | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| regime_tva_saisi | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| duree_portage_saisi_mois | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| apport_saisi_eur | parcelle | page_client:Questionnaire du Financier (4 écrans) |
| taux_apport_saisi_pct | parcelle | page_client:Questionnaire du Financier (4 écrans) |

---

## Partie C — analyse des données à zéro écran (le « travail pour rien »)

Pour chaque table qui n'atteint aucun écran : contenu (volume · maille · fraîcheur), puis **une proposition d'emplacement** ou **la raison de ne pas la montrer**. Zéro « on ne sait pas ».

### DARK vivantes (4) — ingérées, mises à jour, surveillées, jamais montrées

#### 1. `bodacc_depots` — dépôts de comptes des personnes morales → **À BRANCHER (Lot 2)**
- **Contenu** : 14 078 annonces BODACC de dépôt de comptes (14 028 « Comptes annuels et rapports » + 50 consolidés), pour **1 938 SIREN**. Colonnes : `siren`, `date_cloture` (exercice), `date_parution`, `type_depot`, `tribunal`, `raw`.
- **Maille** : personne morale (SIREN) × exercice. **Fraîcheur** : flux BODACC continu, dernière parution **2026-09-13** — vivante et surveillée.
- **Constat** : le frère `bodacc_procedures` sert les événements (`evenements_proprietaire_liste`) ; les **dépôts**, eux, ne sont lus par aucun écran (seul `ingestion/bodacc.py` y touche).
- **Proposition (décision Lot 2)** : signal sur le propriétaire moral dans **Scan patrimoine** et **Successions** — « dernier dépôt de comptes : AAAA » / « aucun dépôt depuis N ans ». Un dépôt récent = société vivante ; un silence prolongé = société en sommeil (signal de cession/succession). Déclarer au registre (donnée + id + lecteurs).

#### 2. `rp_logement_commune` — parc de logements RP2022 par commune → **À BRANCHER ou DOUBLON (Lot 2)**
- **Contenu** : 24 lignes (une par commune), millésime **RP2022**, `n_logements` + `distributions` (jsonb) sur 24 variables INSEE : `SURF` (surface), `NBPI` (nb pièces), `ACHL` (époque d'achèvement), `CHAU`/`CHFL` (chauffage), `HLML` (HLM), `TYPL`/`TYPC` (type de logement), `VOIT` (stationnement), `ASCEN`, `CLIM`, `EAU`, `WC`, `SANI`, `BAIN`, `CUIS`, `ELEC`, `GARL`, `CMBL`, `NBPI`, `CATIRIS`…
- **Maille** : commune. **Fraîcheur** : RP2022 (millésime figé, dernier RP publié).
- **Constat** : « métadonnée » (`qa/lue_verdicts`) — l'égout passe par `anc_maille_taux` ; ces 24 variables logement ne sont lues par aucun écran.
- **Proposition (décision Lot 2)** : carte **« Population et logement »** de la fiche commune, **pour ce qui n'y est pas déjà via IRIS** (`iris_rp`) ni via `commune_insee_logement` (tenure/vacance). Candidats non couverts : structure par `SURF`/`NBPI`, époque `ACHL`, chauffage `CHAU`. Si tout est doublon → **le dire et ne rien ajouter** (à trancher à l'écran en Lot 2).

#### 3. `parcel_cosia_couverture` — couverture CoSIA par classe et parcelle → **NE PAS MONTRER (doublon interne)**
- **Contenu** : 1 947 019 lignes — surface (m²) de chaque classe d'occupation CoSIA intersectant chaque parcelle.
- **Maille** : parcelle × classe CoSIA. **Fraîcheur** : CoSIA 2025 (PVA juil.–août 2025, 20 cm).
- **Raison de ne pas la montrer** : précalcul explicitement **« interne »** (`qa/lue_verdicts.py`), aucun lecteur de service. Le bâti détecté CoSIA affiché (`cosia_detecte_m2`, « Le bien ») vient de `p_model_bati_cosia` ; la couche géométrique `batiment_cosia` n'est pas servie. La ventilation par classe n'apporte rien à l'écran au-delà de l'emprise déjà montrée — **artefact d'analyse**, maille impropre à l'affichage.

#### 4. `vegetation_zonal_acc` — stats zonales de végétation → **NE PAS MONTRER (étage intermédiaire)**
- **Contenu** : 1 156 556 lignes — statistiques zonales (px canopée, NDVI…) par parcelle et par zone (cœur / limite / bâti-adjacent).
- **Maille** : parcelle × zone. **Fraîcheur** : BD ORTHO IRC IGN 974 2025.
- **Raison de ne pas la montrer** : **étage intermédiaire « interne »** (`qa/lue_verdicts`) agrégé dans `parcel_vegetation`, laquelle **est** affichée (ombrage → fiche solaire, PDF Flash ; canopée/NDVI → features de scoring). L'utilisateur voit le résultat agrégé, pas la décomposition zonale — détail de calcul, pas une donnée.

### RETIRE (2) — orphelines déjà documentées dans `tables.py`

- **`mobpro_commune`** (0 ligne — **vide**) : MOBPRO domicile-travail, **RETIRÉ le 06/09** (lecteur `zone.emplois_communes` sans appelant, code mort attrapé par G6). Raison : l'INSEE ne publie pas MOBPRO à maille infra-communale ; l'emploi de zone passe désormais par SIRENE. Table conservée vide, plus lue.
- **`anc_office_eau_commune`** (6 lignes) : chroniques Office de l'eau, **RETIRÉ le 13/09**, supplanté par `anc_maille_taux` (RP2022 EGOUL, plus fin). Conservé (données non effacées), plus aucun lecteur.

### MACHINERIE (17) — lues par l'app, jamais un champ montré (légitime)

Aucune n'est « du travail pour rien » : ce sont des rouages assumés. Résumé (détail en Partie B) :
- **Jointures / fabrication spatiale** : `rnb_rattachement_bdtopo` (817 k, RNB↔BD TOPO + filtre QC), `cadastre_historique` (fabricant : corrige `sitadel_permits.geom`), `ortho_tiles` (grille/checkpoint de tuiles), `solar_grid` (grille PVGIS → `parcel_solar`), `lidar_dalle_grille` (état batch), `p_model_filo` (jointure Filosofi → modèle).
- **QC / détection** : `qa_cosia_bati` (445 k, QA CoSIA vs BD TOPO), `ortho_detections` (détections ML brutes → `parcel_equipements`).
- **Caches de scoring / cascade** : `owner_enrichment` (9,7 k, cache DINUM Score V — débranché de l'affichage), `owner_denom_lookup` (2,6 k, résolution dénomination→SIREN), `pm_dirigeant_gigogne` (2,1 k → contexte cascade, drapeau 0 pt), `bodacc_sondages` (journal de sondage), `sudocuh_procedures` (feature du run **candidat** q_v14 seul ; run servi q_v11_m137 → 0 surface client), `dvf_mutation_detail` (compagnon interne).
- **Journaux / pige** : `annonces` (trace admin, jamais lue), `pige_captures` / `pige_interets_agence` (captures brutes internes).

### Cas particulier — 2 données « en attente »

`mixite_seuil_m2` et `mixite_quota_pct` sont **déclarées** au registre mais servies par **aucun** robinet, par dessein (chantier réglementaire EXPORTS-2, verrouillées par test `test_circuit2_lot1`). Ce n'est pas une fuite : le registre les connaît, elles attendent leur écran.

### Les 47 données « hors mandat » — toutes bien placées

47 données ne s'affichent sur aucune des 7 surfaces du mandat mais bien sur un écran secondaire (Partie A bis). **Zéro anomalie** : 23 sont les **saisies du questionnaire Financier** (portée `projet`, entrées client), les 24 autres sont des **compteurs admin / notifications / accueil / Radar** (Pilotage, Cloche, Digest, page Sources, CRM…). Elles sont à leur place ; rien à rapatrier vers une fiche ou un outil.

---

## Conclusion

- **Le registre est propre** : 259/261 données affichées, 2 en attente déclarées, 0 fuite, 0 donnée orpheline à l'écran. Les 47 « hors mandat » sont correctement placées.
- **Le gisement de « travail pour rien » est au niveau des tables** : sur 89 tables de réservoir, **4 DARK vivantes** et **2 RETIRE**. Les DARK utiles (`bodacc_depots`, `rp_logement_commune`) sont branchées au **Lot 2** ; les 2 autres DARK (`parcel_cosia_couverture`, `vegetation_zonal_acc`) sont des artefacts internes dont la raison de non-affichage est gravée ici.
- **Hors périmètre** (mandat séparé, décision de Vic) : le branchement éventuel des autres tables — notamment `annuaire_services` (436 services DILA, aujourd'hui page admin Contacts seule) vers la fiche commune, et l'arbitrage purge/archive des 2 précalcs CoSIA/végétation.

---

# DONNEES-1 — Lot 2 : les quatre décisions déjà prises

Un commit par décision (2.1 → 2.4). Base : `feat/donnees-1` sur main `373a8833`.

## 2.1 — Piscines : la couche quitte le tuyau, vit dans Solaire
- **Fait** : la couche `piscine_cosia` (surface `couche_piscine`, `declarations/couches/couches_sans_toggle.yaml`) est retirée du tuyau. Le mode Piscines de Prospection solaire affichait **déjà** les piscines sur la carte par ses propres points GeoJSON (`getPiscinesPoints` → `setModuleMap`, `ProspectionSolaire.tsx:ModePiscines`) — la couche du panneau était redondante.
- **Preuve — compteur du tuyau 56 → 55** : `registre()` = **55** (était 56) ; `couches_carte()` = 52 ; `piscine_cosia` ∉ `registre()`. Le panneau Couches (`NouvellesCouches`, data-driven via `/map/tuyau/couches`) ne la liste plus, aucun changement front nécessaire.
- **Preuve — piscines toujours dans Solaire** : `ProspectionSolaire.tsx` inchangé, points servis par `/prospection-piscines/points` ; vitest `ProspectionSolaire.test.tsx` **9/9 vert**.
- **V7a rejoué** : `verrou_tuiles` est dynamique (`couches_carte()`), il ne contrôle plus les tuiles piscine. `n_piscines` / `piscine_m2` (fiche + outil) et le kind spatial_layers `piscine_cosia` restent intacts.
- Test mis à jour : `test_piscine_hors_tuyau_vit_dans_solaire` ✓.

## 2.2 — DPE : la ligne s'affiche seulement si un DPE existe
- **Fait** : plus de ligne « non déterminée — aucun DPE rattaché ». Le DPE n'est pas obligatoire dans les DROM (~0,3 % de couverture) et ne sert aucun outil ni ciblage — le dire sur 99,7 % des parcelles est un bruit trompeur.
- **Fiche parcelle** (`leBien.tsx`) : la ligne DPE n'est rendue que si `dpe` existe (`{dpe && …}`), fin de la branche « non déterminée ».
- **Dossier** : nouveau drapeau déclaratif `masquer_si_absent` (`declarations.py` + `miroir.py`) ; `le_bien.yaml` `dpe_connu` le porte. L'absence n'est plus rendue ; justification gravée dans `pourquoi`. `absence` reste renseignée (le schéma l'exige, verifier() = 0 violation).
- **Preuve** : back `_dpe_connu_block` renvoie déjà `None` sans DPE → aucune ligne ; `charger()` confirme `dpe_connu.masquer_si_absent = True`. tsc vert.

## 2.3 — bodacc_depots : signal « dépôt de comptes » sur le propriétaire PM
- **Fait** : la table `bodacc_depots` (14 078 dépôts de comptes annuels, 1 938 SIREN, flux BODACC continu — **DARK** au Lot 1) devient un signal factuel d'approche : « dernier exercice déposé : AAAA » / « aucun dépôt depuis N ans » (société en sommeil probable).
- **Back** : `modules.py:_depots_par_siren` (batch, garde `to_regclass`) → Scan patrimoine (`depot_comptes`) et Successions (par item).
- **Registre** : donnée `dernier_depot_comptes` (proprietaire, réservoir bodacc), **servie par les robinets Scan patrimoine + Successions** ; lecture fine `bodacc_depots → api/modules.py` déclarée (G6 : dette 0).
- **Front** : encart Scan patrimoine (`ModulePanel.tsx`) + motif Successions (`Successions.tsx`).
- **Preuve fonctionnelle** (base réelle) : siren `841694490` → `{annee: 2025, depuis_ans: 0}` ; siren inconnu → `{}` (aucun dépôt). Tests `test_patrimoine.py` + `test_outils_muscler1.py::test_successions_liste` **11/11 vert** ; vitest `ScanRetraits.test.tsx` vert.

## 2.4 — rp_logement_commune : âge du parc (le reste = doublon, dit)
- **Constat de doublon** : la carte « Population et logement » sert **déjà** le type maison/appartement et la tenure (`commune_insee_logement.maisons_pct` via `d.marche`), la vacance (commune + IRIS), le parc social (RPLS). Ces variables de `rp_logement_commune` sont donc **doublon — non rebranchées**.
- **Ce qui n'y était pas** : l'**âge du parc**. Ajout de `parc_ancien_pct` = part construit avant 1991 (RP2022, distribution ACHL, codes A/B = ancien), `fiche_commune.py:_parc_ancien_pct` (garde table-absente).
- **Registre** : donnée `parc_ancien_pct` (commune, réservoir `insee_rp2022_egoul`), servie par le robinet Population & logement ; lecture fine déclarée. Au passage, la lecture `rpls_commune ← fiche_commune.py` (parc social, non déclarée depuis COMMUNE-RANGEMENT-1) est **enfin déclarée → dette G6 à 0, graphe exact dans les deux sens** (le test `test_graphe_exact_dans_les_deux_sens`, rouge sur main, repasse vert).
- **Front** : ligne « Parc construit avant 1991 » dans la carte Population et logement (`ContextePanel.tsx`).
- **Preuve fonctionnelle** (base réelle) : Saint-Denis (97411) → `population.parc_ancien_pct = 45.4` ; 97416 → 35,3 ; 97409 → 34,7. Tests `test_fiche_commune2_c1_cache.py` 3/3 ✓.

## Captures écran
Preuves fonctionnelles ci-dessus (payload servi, sorties de moteurs, tests DOM/vitest). Les captures pixel des écrans (panneau Couches, mode Piscines, fiche avec/sans DPE, Dossier, Scan patrimoine, carte Population) sont laissées à l'œil de Vic sur l'app live (ports :8095 / :5295) — même contrainte de capture WebGL/live que les sessions précédentes.

## Portes de recette (gates)

- **tsc -b** : vert.
- **vitest** (composants touchés) : `ProspectionSolaire` + `ScanRetraits` 9/9 verts.
- **pytest tests/ complet** : 3133 passés. Échecs = **pré-existants** (rouges à la base `373a8833`, vérifié en isolant les 8) : `test_chaque_passe_plat_declare_sa_table` (donnée `exposition_versant` hors périmètre, sans `table=` à la base), `test_traçage_des_classes_pose` (balise Trace `zone_plu_famille`), `test_retours11f4` (×2, découpe module / socio-éco). `test_verrous_lot1_passent_sur_la_base_reelle` PASSE en isolation (rouge seulement en suite complète = pollution d'ordre de la base réelle, pré-existant). **0 échec nouveau** : les 3 tests que mes ajouts auraient cassés (`test_documents_commites_a_jour`, `V5e`, `V5c`) sont corrigés et repassent verts.
- **circuit verrous -w G8** : voir le rapport joint — V7a à **55 couches**, V5c / V5d / V5e / V5f verts.
