# CHASSE-CALCULS-1 — ÉCARTS

Gravité : **FAUX-CLIENT** (chiffre faux/trompeur servi) · **DIVERGENT** (deux outils, deux valeurs) · **PÉRIMÉ** (donnée gelée) · **MUET** (limite non déclarée) · **RENDU** (affichage/pied/arrondi).
Base `labuse` locale, run q_v18. Chaque ligne : lot · gravité · témoin · attendu · obtenu · règle · fichier:ligne · reproduction.

| id | lot | gravité | témoin | attendu | obtenu | règle citée | fichier:ligne | reproduction |
|---|---|---|---|---|---|---|---|---|
| **E-A1** | A | **DIVERGENT / MUET** | collectif 20 lgt = 1 400 m² RP, com 3 % | TA **34 342 €** (abattement 100 m² **par logement** ⇒ tout à −50 %) | TA **66 231 €** (abattement 100 m² une seule fois) — **sur-taxe ~×2** | CGI art. 1635 quater I, I-2° « cent premiers mètres carrés … logement par logement » ; BOFiP BOI-IF-TU-10-30-20 (non mutualisable) | `src/labuse/taxe_amenagement.py:245-252` ; endpoint sans `nb_logements` `src/labuse/api/app.py:3047` | `calculer(surface_taxable_m2=1400, residence_principale=True, taux_communal_pct=3)` → total 66 231 ; manuel 1 400×892×0,5×1,055 = 34 342 |
| **E-A2** | A | **MUET** | abri de jardin 15 m² (cas 5) ; stationnement | mention « exonérations communales facultatives et stationnement majoré non modélisés » | taxé plein (735,90 €) et stationnement figé à 2 928 €/place | CGI art. 1635 quater E (exo facultatives) ; art. 1635 quater J (max délib. 5 857 €/place) | `src/labuse/taxe_amenagement.py` (aucun chemin exo facultative) ; `config/taxe_amenagement.yaml` (`stationnement_ext_place_max_delib: 5857` non utilisé par `calculer()`) | comparer la note A4 de l'outil : aucune de ces deux limites n'y figure |
| **E-A3** | A | **RENDU** | tous les cas TA | montant arrondi à l'**euro inférieur** | montant au **centime** (ex. 3 434,20 €) | CGI art. 1635 quater I, III « arrondies à l'euro inférieur » | `src/labuse/taxe_amenagement.py:167` (`_eur = round(x,2)`) | déjà noté FAIBLE par TAXE-AUDIT-1 ; cosmétique |
| **E-B1** | B | **PÉRIMÉ** (par conception) | toute parcelle | valeurs servies à jour dès qu'une règle PLU change | fiche/Dossier/Flash/Copilote servent un **run gelé** (`parcel_residuel`, `is_served`, run_seq 15) ; inchangées tant qu'un nouveau run n'a pas rebasculé. L'**outil Faisabilité (enveloppe)** recalcule en direct ⇒ fenêtre de divergence outil-live ↔ fiche-gelée | B4 du mandat | `src/labuse/faisabilite/db.py` (vue `parcel_residuel`) ; `scenarios.py` (ALGO-FIX-1 : lit le run gelé sans saisie) ; `bascule_flux.py` (is_served) | modifier `plu_exceptions_effet.json` en local ⇒ l'enveloppe de l'outil bouge, la SDP servie de la fiche non (non exécuté cette passe — mécanisme prouvé par lecture code) |
| **E-C1** | C | **MUET / RENDU** | parcelle en pente forte | 3D reflétant le terrain naturel (RGE ALTI) ou mention « terrain supposé plat » | volume 3D = **extrusion à plat** `emprise × hauteur` ; le MNT ne sert qu'à la **hauteur du bâti existant**, pas à l'assise du gabarit 3D ; `pente_pct` est servi sur la fiche mais le 3D n'avertit pas | C3 du mandat | `src/labuse/faisabilite/db.py:749` (`volume_m3 = emprise × hauteur`) ; `:869` (commentaire « extrusion emprise × hauteur ») | `volume3d_payload()` ; comparer à `pente_pct` servi (`db.py:854`) |
| **E-D1** | D | **RENDU** (risque faible) | pré-dossier PC | tout chiffre via le payload fiche partagé | **hybride** : valeurs calculées (SDP, zone, potentiel) via `parcel_fiche()` ✅ ; mais dimensions terrain (largeur, surface, emprise) en **SQL direct** (`ST_Area`, `ST_Intersection`) → hors cribble de provenance | D1 du mandat ; EXPORTS-AUDIT-2 (« pré-dossier hors circuit ») | `src/labuse/api/pre_dossier.py:128-130,343-345` (parcel_fiche) ; `:621-633,682-688` (SQL direct) ; note CERFA délibérée `:214` | relire `pre_dossier.py` : les nombres réglementaires viennent de la fiche, seules les cotes géométriques CERFA sont requêtées |

## Écarts CONNUS déjà CORRIGÉS (vérifiés sur le code courant — pas de nouvel écart)

| id | lot | état | preuve |
|---|---|---|---|
| K-A1 | A | **corrigé** (TAXE-FIX-1 pt 1) — exonérations de plein droit (agricole 3°, PLAI 2°, reconstruction 9°) | `taxe_amenagement.py:181-186` `_MOTIFS_EXONERATION` ; endpoint `surface_exoneree_m2`/`motif_exoneration` |
| K-A2 | A | **corrigé** (TAXE-FIX-1 pt 2) — RAP : l'ancien forfait 0,68 €/m² du Dossier supprimé, désormais 0,40 % de l'assiette TA, **identique outil ↔ Dossier** | `exports/financier_bilan.py:31-34,143-145` ; `taxe_amenagement.py:196,309` |
| K-A3 | A | **corrigé** (TAXE-FIX-1 pt 3) — secteurs à taux majoré ingérés et servis (10 465 parcelles / 6 communes) | table `taxe_amenagement_secteur` ; `taux_parcelle()` `taxe_amenagement.py:149-159` |
| K-A4 | A | **corrigé** (TAXE-AMÉNAGEMENT-1) — 24/24 taux communaux sourcés+datés DGFiP DELTA ; part dép 2,5 % confirmée | table `taxe_amenagement_taux` (SELECT 24 lignes, source+delib_date+maj_at) |
| K-C1 | C | **à jour** — surface Gabarit = contenance cadastrale = fiche (CONTENANCE-1 **LIVE sur q_v18**) | 3 témoins §Lot B/C de CALCULS-MANUELS (27 862 / 25 633 / 991 identiques fiche=Gabarit=base) |

## Zones vertes (vérifiées, aucun écart)

- Constantes TA 2026 : 892 €/m², piscine 251, PV 10, stationnement 2 928, éolienne 3 000, abattement 50 %/100 m², exo < 5 m², part dép 2,5 %, RAP 0,40 % → **toutes conformes** aux textes officiels (CALCULS-MANUELS §A1).
- 9/10 cas TA recalculés à la main **identiques au centime**.
- Banc de recalcul indépendant : 494 comparaisons, **1 seul écart tolérable** (arrondi score).
- Gabarit : écran = PDF (source unique `compute_gabarit`) ; exports : builder partagé `construire/collecte` lisant le payload fiche ; millésime « Données LABUSE au {promoted_at} » rendu en pied `@page` WeasyPrint ; réserves par document.
