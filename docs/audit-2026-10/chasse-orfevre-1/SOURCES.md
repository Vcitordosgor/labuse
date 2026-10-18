# CHASSE-ORFEVRE-1 — Bilan par source (volumes · couverture · fantômes · poids mort)

18/10/2026 — script rejouable : `scripts/angle_b_sources.py` (base ; `--en-ligne` pour interroger les producteurs).
Registre : 129 lignes `data_sources` (97 connectées, 14 partenariat_requis, 6 alias, 5 retirées, 4 hub, 2 manuel, 1 interne).
Producteurs interrogés en GET légers (~1 req/s) : API Carto IGN, Géorisques v1, ADEME data-fair, BODACC ODS, plateforme BAN, files.data.gouv (geo-DVF).
Renvois : `ORF-xx` → `ECARTS.md` ; détail → `brouillons/ANGLE-B.md` et `brouillons/SOURCES-BRUT.md`.

| Source | Table(s) | Volume base | Producteur / annoncé | Couverture 24 | Fantômes | Poids mort | VERDICT |
|---|---|---|---|---|---|---|---|
| Cadastre PCI/Etalab | parcels (+geometrie, mvt) | 434 582 dont 433 229 vivantes | API Carto **432 330** (18/10) | 24/24, aucun trou | 899 vivantes déjà retirées du PCI courant (ORF-26) ; mécanisme « disparues » en place (1 353) | `origine` 100 % NULL mais lue (ORF-49) | **CONFORME** (dérive d'édition 0,21 %, à résorber au prochain sync) |
| DVF géo Etalab 2021-2025 | dvf_mutations_parcelle | 102 551 | fichiers communaux officiels rejoués : 97403/2024 et 97411/2023 **identiques ligne à ligne** | 24/24 | 0 hors fenêtre ; 116 idu → parcelles disparues (ventes historiques, légitime) | — | **CONFORME (exact, octet pour octet)** |
| DVF archives DGFiP 2014-2020 | dvf_mutations_histo | 110 477 | NON_VÉRIFIABLE (millésimes retirés du « latest ») | 24/24 | 0 hors fenêtre, 0 recouvrement avec le flux actuel | lon/lat 100 % NULL ; `source_archive` jamais lue | **CONFORME** (fenêtre propre) |
| DVF « fenêtre » servie | dvf_mutations | 29 566 | dérivée du flux géo (max réel 2025-12-31) | 24/24 | **1 mutation inventée** (vestige démo Saint-Paul — ORF-06) | — | **GÊNANT : 1 ligne fictive** (contournée par dvf_fenetre.py) |
| GPU/PLU (API Carto) | parcel_zone_plu, plu_gpu_zone (5 841), plu_reglement_extrait (3 258) | 430 320 parcelles zonées | NON_VÉRIFIABLE en léger (WFS par document) | 23/24 — **97417 Saint-Philippe : 0 couche, 9 parcelles** ; verbatims à 0 pour 97409/97413/97417 | — | — | **CONFORME au connu** (K-5, VERITE-TERRAIN-3) |
| PPR / GASPAR CatNat (Géorisques) | catnat_arretes 426 ; couches ppr 164 + ppr_etat 24 ; azi/tri 128 | 426 arrêtés | API v1 : **427** (23 communes exactes, 97412 +1 depuis le sync 06/09 — ORF-48) | 24/24 | 0 arrêté futur | — | **CONFORME** (1 arrêté de retard) |
| Sitadel (SDES) | sitadel_permits | 50 809 | NON_VÉRIFIABLE (CSV national DIDO) | 24/24 | 0 date future ; max 2026-08-31 = millésime 2026-08 déclaré | — | **COHÉRENT** |
| SIRENE géolocalisé (INSEE) | sirene_etablissements | **158 515** (173 524 le matin même — ORF-11) | NON_VÉRIFIABLE sans jeton INSEE | 24/24 | 9 dates futures + 1 an « 0026 » (producteur — ORF-48) ; politique « actifs seulement » non documentée | `qp24` jamais lue | **À SURVEILLER : purge de 15 009 lignes non journalisée** |
| BODACC (DILA) | bodacc_depots | 14 078 (1 938 sirens) | ODS par siren : 205/34/23 vs base 204/33/23 (publications post-sync) | n/a (ciblée par siren, by design) | 0 | 4 colonnes jamais lues | **CONFORME** |
| DPE ADEME (3 jeux) | dpe_records | 1 123 (914+179+30) | data-fair `code_insee_ban:974*` : **915/179/30** | 19/24 — 5 communes à 0, cohérent PAR CONSTRUCTION (seuls les DPE géocodés BAN 974 sont authentiques) | 2 idu → parcelles disparues | `geocode_score` jamais lue | **CONFORME (1 de retard)** |
| RNB | rnb_batiments | 414 081 | NON_VÉRIFIABLE (API alpha sans count) | 24/24 | 0 inactif conservé | — | **COHÉRENT** |
| BAN | adresses 339 915 ; adresse_parcelles 418 346 | 339 915 | lookup BAN : **340 764** | 24/24 | **266 fantômes à Petite-Île** (base > producteur, BAL certifiée) ; 2 043 idu → parcelles disparues (ORF-26) | — | **À SURVEILLER** (re-sync + rattachement) |
| BAN PLUS (IGN) | ban_plus_liens | 738 540 | millésime déclaré (27/08/2026), pas de compteur | 24/24 | — | `type_lien/nb_adr/nb_bat` jamais lues | **COHÉRENT** |
| RPLS (SDES) | rpls_commune | 24 lignes / 87 553 logements | NON_VÉRIFIABLE (fichier national) | 24/24 | — | `dpe_classes`/`pct_passoires` 100 % NULL ET jamais lues ; 2 autres jamais lues | **COHÉRENT**, 4 colonnes mortes |
| Piscines (ortho/CoSIA) | piscines 50 516 | produit INTERNE | — | 24/24 | 0 `disparue` | millésimes jamais lus | **COHÉRENT** (ORF-14 : 15 servies sans idu) |
| LiDAR HD MNH (IGN) | batiment_hauteur_lidar | 303 452 | produit INTERNE (dalles 2023) | 24/24 | — | `rnb_cause` jamais lue | **COHÉRENT** (bornes : K-1) |
| DGFiP parcelles PM | parcelle_personne_morale 82 701 ; pm_proprietaires_millesimes 461 570 | 2025 + panel 2019-2024 | = « Panel 2019→2025 » déclaré | 24/24 | 0 hors fenêtre | — | **CONFORME** (ORF-13 : 601 idu orphelins côté cadastre) |
| DFI (DGFiP) | dfi_filiation | 409 623 | **= 409 623 annoncé** | 24/24 | — | `identifiant_dfi` jamais lue (traçabilité) | **CONFORME** |
| Fibre Arcep | arcep_immeubles | 330 310 | **= 330 310 annoncé** (2026_T2) | 24/24 | — | 3 colonnes × 330 k jamais lues | **CONFORME**, 3 colonnes mortes |
| RNIC (Anah) | rnic_coproprietes | 2 220 | **= 2 220 annoncé** (re-sync 10/10) | n/a | — | `mandat_en_cours` jamais lue | **CONFORME** |
| QPV 2024 (ANCT) | couche qpv | 57 QPV / 13 communes | = geojson national filtré 974 | 13 communes (les 11 autres sans QPV, attendu) | génération 2024 seule | — | **CONFORME** |
| ORT/ACV-PVD · PLH · ANRU | commune_ort 19 ; plh_epci 5 ; anru 8 | 19 / 5 / 8 | = déclaré | — | — | — | **CONFORME au déclaré** |
| ZNIEFF (INPN) | couche znieff | 162 | NON_VÉRIFIABLE en léger | île entière | millésime 29/08/2025 (fraîcheur = VT-3) | — | **COHÉRENT** |
| GéoLittoral / bruit / PEB / DPF | trait_de_cote 24 168 ; bruit 1 004+6 ; peb 8 ; dpf 281 | — | bruit 6 = « 6 zones CBS » ; dpf 281 = « 275+6 » déclaré | — | — | — | **CONFORME au déclaré** (retards amont = VT-3) |

## Synthèse
- **Volumes** : partout où un compteur producteur existe (cadastre, DVF, GASPAR, ADEME, BODACC, BAN) ou un compte auto-déclaré chiffré (Arcep, DFI, RNIC, CBS, DPF, QPV, ORT), la base colle à ±1 unité ou ±0,25 %. **Une seule vraie ligne fantôme trouvée (ORF-06)** — et elle est d'origine interne (démo), pas producteur.
- **Couverture** : aucune commune anormalement vide sur aucune source ; les seuls zéros (DPE ×5, GPU Saint-Philippe, verbatims ×3) sont par construction ou déjà connus (K-5).
- **Fantômes** : 266 adresses BAN à Petite-Île, 899 parcelles en sursis d'édition PCI, 2 043 adresses sur parcelles disparues (ORF-26), 1 mutation fictive (ORF-06). Fenêtres de dates toutes propres.
- **Poids mort** : ~20 colonnes jamais lues + 5 colonnes 100 % NULL (ORF-49).
- **Vigilance transverse** : la base dev bouge sans journal (ORF-11).

## NON_VÉRIFIABLE en ligne (raisons)
- SIRENE géolocalisé : fichier national, API INSEE à jeton.
- Sitadel : CSV national DIDO, pas de compteur filtré départemental léger.
- RNB : API alpha paginée par curseur, sans champ count.
- RPLS / BAN PLUS / DFI / Arcep / RNIC : fichiers nationaux ; compte retenu = millésime chiffré déclaré au registre (contrôlé).
- Piscines / LiDAR / CoSIA : produits LABUSE dérivés d'images, pas de compteur producteur.
- dvf_mutations_histo : millésimes DGFiP retirés du « latest » Etalab.

## Pièges de méthode
- Le venv n'a pas de chaîne de certificats → le script charge `certifi`.
- geo-DVF : fichiers communaux servis en `.csv` NON gzippé derrière un 302 (`curl -L`) ; l'URL `.csv.gz` répond NoSuchKey.
- Grep « colonne jamais lue » : exclure `models.py` et les écrivains (`ingestion/`, `connectors/`) ; méthode conservatrice (toute occurrence texte = « lue »).
- La base est VIVANTE pendant l'audit : dater chaque compte.
