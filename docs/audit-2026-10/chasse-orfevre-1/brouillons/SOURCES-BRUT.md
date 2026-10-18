# CHASSE-ORFEVRE-1 — Angle B : bilan PAR SOURCE (volumes · couverture · fantômes · poids mort)

18/10/2026 — script `scripts/angle_b_sources.py` (sections B0-B5 ; `--en-ligne` pour les producteurs).
Registre : 129 lignes `data_sources` (97 connectées, 14 partenariat_requis, 6 alias, 5 retirées, 4 hub, 2 manuel, 1 interne).
Renvois « B-xx » → `ANGLE-B.md`. Couverture : les 24 INSEE 97401-97424 (tableau complet dans la sortie du script).

| Source | Table(s) | Volume base | Producteur / annoncé | Couverture 24 | Fantômes | Poids mort | VERDICT |
|---|---|---|---|---|---|---|---|
| Cadastre PCI/Etalab | parcels (+geometrie, mvt) | 434 582 dont 433 229 vivantes | API Carto 432 330 (18/10) | 24/24, aucun trou | 899 vivantes déjà retirées du PCI courant (B-04) ; mécanisme disparues en place (1 353) | `origine` 100 % NULL mais lue (B-06) | **CONFORME** (dérive d'édition 0,2 %, à résorber au prochain sync) |
| DVF géo Etalab 2021-2025 | dvf_mutations_parcelle | 102 551 (2021:24 198→2025:14 523) | fichiers communaux officiels : 97403/2024 et 97411/2023 **identiques ligne à ligne et mutation à mutation** | 24/24 | 0 hors fenêtre ; 116 idu → parcelles disparues (ventes historiques, légitime) | — | **CONFORME (exact)** |
| DVF archives DGFiP 2014-2020 | dvf_mutations_histo | 110 477 | NON_VÉRIFIABLE (archives DGFiP retirées du « latest ») | 24/24 | 0 hors fenêtre 2014-2020, 0 recouvrement avec le flux actuel | `longitude`/`latitude` 100 % NULL ; `source_archive` jamais lue | **CONFORME** (fenêtre propre) |
| DVF « fenêtre » servie | dvf_mutations | 29 566 | dérivée du flux géo (max réel 2025-12-31) | 24/24 (noms) | **1 mutation inventée** (vestige démo Saint-Paul, 380 000 €, 2026-08-10) — B-01 | — | **GÊNANT : 1 ligne fictive** (contournée par dvf_fenetre.py) |
| GPU/PLU (API Carto) | parcel_zone_plu, spatial_layers(plu_gpu_zone 5 841), plu_reglement_extrait 3 258 | 430 320 parcelles zonées | NON_VÉRIFIABLE en léger (WFS GPU par document) | 23/24 couches zones — **97417 Saint-Philippe : 0 couche, 9 parcelles** ; verbatims à 0 pour 97409/97413/97417 | — | — | **CONFORME au connu** (GPU vide/procédure — recroise VERITE-TERRAIN-3) |
| PPR / GASPAR CatNat (Géorisques) | catnat_arretes 426 ; spatial_layers ppr 164 + ppr_etat 24 ; azi/tri 128 | 426 arrêtés | API Géorisques v1 : **427** (23 communes exactes, 97412 +1 depuis sync 06/09) — B-07 | 24/24 | 0 arrêté futur | — | **CONFORME** (1 arrêté de retard) |
| Sitadel (SDES) | sitadel_permits | 50 809 | NON_VÉRIFIABLE (CSV national DIDO, pas de compteur filtré léger) | 24/24 (noms) | 0 date future ; max 2026-08-31 = millésime 2026-08 déclaré | — | **COHÉRENT** (volume non vérifiable) |
| SIRENE géolocalisé (INSEE) | sirene_etablissements | **158 515** (173 524 à l'angle A le matin même — B-02) | NON_VÉRIFIABLE sans jeton INSEE (fichier national) | 24/24 | 9 dates création futures + 1 an 0026 (producteur, recroise A-09) ; politique « actifs seulement » non documentée | `qp24` jamais lue (remplie 18 %) | **À SURVEILLER : purge de 15 009 lignes non journalisée** |
| BODACC (DILA) | bodacc_depots | 14 078 (1 938 sirens, 2008→2026-09-13) | ODS par siren : 205/34/23 vs base 204/33/23 (delta = publications post-sync) | n/a (ciblée par siren, by design) | 0 | `type_depot/cp_siege/commercant/tribunal` jamais lues | **CONFORME** (chargement ciblé) |
| DPE ADEME (3 jeux) | dpe_records | 1 123 (914 existant + 179 neuf + 30 tertiaire) | data-fair `code_insee_ban:974*` : **915/179/30** | 19/24 — 5 communes à 0, cohérent avec un volume minuscule PAR CONSTRUCTION (connecteur : seuls les DPE géocodés BAN 974 sont authentiques) | 2 idu → parcelles disparues ; 0 date future | `geocode_score` jamais lue | **CONFORME (1 de retard)** |
| RNB | rnb_batiments | 414 081 | NON_VÉRIFIABLE (API alpha sans compteur) ; ratio bâtiments/parcelles plausible partout | 24/24 | 0 inactif conservé | — | **COHÉRENT** |
| BAN | adresses 339 915 ; adresse_parcelles 418 346 | 339 915 | lookup BAN : **340 764** — détail B-03 | 24/24 | **266 fantômes à Petite-Île** (base > producteur) ; 2 043 idu → parcelles disparues (B-05) | — | **À SURVEILLER** (re-sync + rattachement) |
| BAN PLUS (IGN) | ban_plus_liens | 738 540 | millésime déclaré (data.gouv 27/08/2026), pas de compteur | 24/24 | — | `type_lien/nb_adr/nb_bat` jamais lues | **COHÉRENT** |
| RPLS (SDES) | rpls_commune | 24 lignes / **87 553 logements** | NON_VÉRIFIABLE en léger (fichier national SDES) ; ordre de grandeur du parc social 974 plausible | 24/24 | — | `dpe_classes`/`pct_passoires` 100 % NULL ET jamais lues ; `surfhab_moy`/`pct_dpe_renseigne` jamais lues | **COHÉRENT**, 4 colonnes mortes |
| Piscines (détection ortho/CoSIA) | piscines 50 516 (+piscine_cosia 46 599 couches) | produit INTERNE (pas de producteur) | — | 24/24 + 4 359 sans commune (A-10, connu) | 0 `disparue` | `millesime_flair/cosia` jamais lues | **COHÉRENT** (voir A-10) |
| LiDAR HD MNH (IGN) | batiment_hauteur_lidar | 303 452 | produit INTERNE (dalles IGN 2023) | 24/24 | — | `rnb_cause` jamais lue (remplie 1,4 %) | **COHÉRENT** (bornes : A-03/FIX-2 connu) |
| DGFiP parcelles PM | parcelle_personne_morale 82 701 ; pm_proprietaires_millesimes 461 570 | 2025 courant + panel 2019-2024 | = « Panel millésimes 2019→2025 » déclaré | 24/24 | 0 millésime hors fenêtre | — | **CONFORME** |
| DFI (DGFiP) | dfi_filiation | 409 623 | **= 409 623 annoncé** (data_sources, situation 19/06/2026) | 24/24 | — | `identifiant_dfi` jamais lue (traçabilité) | **CONFORME** |
| Fibre Arcep | arcep_immeubles | 330 310 | **= 330 310 annoncé** (2026_T2) | 24/24 | — | `technos`, 2 débits jamais lus (3 col × 330 k) | **CONFORME**, 3 colonnes mortes |
| RNIC (Anah) | rnic_coproprietes | 2 220 | **= 2 220 annoncé** (re-sync 10/10) | n/a (copros) | — | `mandat_en_cours` jamais lue | **CONFORME** |
| QPV 2024 (ANCT) | spatial_layers qpv | 57 QPV / 13 communes | = compte du geojson national ANCT filtré 974 (vérifié au chargement, connectors/qpv.py) | 13 communes (les 11 autres sans QPV, attendu) | génération 2024 uniquement | — | **CONFORME** |
| ORT/ACV-PVD · PLH · ANRU | commune_ort 19 ; plh_epci 5 ; anru 8 couches | 19 communes / 5 EPCI / 8 quartiers | = déclaré (« 19 communes 974, 13 ORT signées » ; 5 EPCI) | — | — | — | **CONFORME au déclaré** |
| ZNIEFF (INPN) | spatial_layers znieff | 162 (toutes distinctes) | NON_VÉRIFIABLE en léger (INPN sans compteur filtrable simple) | île entière | millésime 29/08/2025 (fraîcheur = VT-3) | — | **COHÉRENT** |
| GéoLittoral / bruit / PEB / DPF | trait_de_cote 24 168 ; bruit_route 1 004 ; bruit_carte 6 ; peb 8 ; dpf 281 | — | bruit_carte 6 = « 6 zones CBS » déclaré ; dpf 281 = « 275 tronçons + 6 plans » déclaré | — | — | — | **CONFORME au déclaré** (retards amont = VT-3) |

## Synthèse
- **Volumes** : partout où un compteur producteur existe (cadastre, DVF, GASPAR, ADEME, BODACC, BAN) ou un compte auto-déclaré chiffré (Arcep, DFI, RNIC, CBS, DPF, QPV, ORT), la base colle à ±1 unité ou ±0,25 % — **une seule vraie ligne fantôme trouvée (B-01)**, et elle est d'origine interne (démo), pas producteur.
- **Couverture** : aucune commune anormalement vide sur aucune source ; les seuls zéros (DPE ×5, GPU Saint-Philippe, verbatims PLU ×3) sont expliqués par construction ou déjà connus (VT-3).
- **Fantômes** : 266 adresses BAN à Petite-Île (B-03), 899 parcelles en sursis d'édition PCI (B-04), 2 043 adresses sur parcelles disparues (B-05), 1 mutation fictive (B-01). Fenêtres de dates toutes propres.
- **Poids mort** : ~20 colonnes jamais lues + 5 colonnes 100 % NULL (B-06) — cosmétique, dont 4 sur rpls_commune et 3 × 330 k sur arcep_immeubles.
- **Gros point de vigilance transverse** : la base bouge sans journal (B-02) — 15 009 lignes SIRENE évaporées dans la journée, `job_runs` réduit à 1 ligne.

## NON_VÉRIFIABLE en ligne (raisons)
- SIRENE géolocalisé : fichier national, API INSEE à jeton.
- Sitadel : CSV national DIDO, pas de compteur filtré par département accessible en léger.
- RNB : API alpha paginée par curseur, sans champ count.
- RPLS / BAN PLUS / DFI / Arcep / RNIC : fichiers nationaux ; le compte producteur retenu est le millésime chiffré déclaré au registre (contrôlé en B1).
- Piscines / LiDAR / CoSIA : produits LABUSE dérivés d'images, pas de compteur producteur.
- dvf_mutations_histo : millésimes DGFiP retirés du « latest » Etalab.
