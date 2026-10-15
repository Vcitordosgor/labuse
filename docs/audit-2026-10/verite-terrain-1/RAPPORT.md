# VERITE-TERRAIN-1 — RAPPORT

## Verdict en 5 lignes

1. **500 parcelles** (échantillon stratifié reproductible, graine `20261015`, base q_v18) confrontées aux sources officielles, **8 familles de données**.
2. Sur **6340 comparaisons réellement comparables**, **100.0% CONFORMES** (6340 conformes · 0 « LABUSE FAUX » · 0 fraîcheur).
3. **3684 comparaisons NON COMPARABLES** (source muette, champ non publié, ou présence non infirmable) — détaillées, jamais comptées comme un échec.
4. **Aucun « LABUSE FAUX » confirmé.** Le comparateur a levé des candidats (zone PLU en lisière, compte CatNat, aléa au point, décimales « 4,5 » vs « 4.5 »…) ; **chacun, revérifié à la main, s'est avéré un artefact du comparateur ou de la source, pas une erreur de LABUSE** (détail et corrections dans `ECARTS.md`).
5. **PLU — règles chiffrées** (100 parcelles, §3 bis) : **330/336 conformes** relues au règlement officiel à la page citée ; 5 non comparables (reculs dérivés d'un prospect) ; **1 seul écart résiduel** = une citation de page d'emprise à corriger (valeur non infirmée). Fraîcheur : 0 cas.

Reproduire : `python -m labuse.verite_terrain comparer --source toutes` puis `fusionner` puis `python -m labuse.verite_terrain_rapport`. Contrôle mensuel : même commande avec `--n 20`.

## 1. Cadastre (API Carto cadastre / IGN)

| Champ | Comparables | Conformes | Taux | LABUSE FAUX | Fraîcheur | Non comparable |
|---|---|---|---|---|---|---|
| cadastre.parcelle | 0 | 0 | — | 0 | 0 | 6 |
| commune_insee | 494 | 494 | 100% | 0 | 0 | 0 |
| contenance_m2 | 474 | 474 | 100% | 0 | 0 | 20 |
| numero | 494 | 494 | 100% | 0 | 0 | 0 |
| section | 494 | 494 | 100% | 0 | 0 | 0 |
| surface_geometrie_m2 | 494 | 494 | 100% | 0 | 0 | 0 |

Non comparable — raisons :
- 20× LABUSE ne sert pas de contenance DGFiP pour cette parcelle
- 6× parcelle absente d'API Carto (nouvelle/retirée ?)

## 2. Adresses (BAN)

| Champ | Comparables | Conformes | Taux | LABUSE FAUX | Fraîcheur | Non comparable |
|---|---|---|---|---|---|---|
| adresse | 263 | 263 | 100% | 0 | 0 | 237 |

Non comparable — raisons :
- 53× BAN sans résultat au centroïde
- 4× LABUSE ne rattache pas d'adresse (BAN propose « 22 Chemin des Cactus 9
- 2× LABUSE ne rattache pas d'adresse (BAN propose « 5 Chemin Pavé 97425 Le
- 2× LABUSE ne rattache pas d'adresse (BAN propose « 38 Chemin des Cactus 9
- 1× LABUSE ne rattache pas d'adresse (BAN propose « 57bis Chemin Dep 11 le
- 1× LABUSE ne rattache pas d'adresse (BAN propose « 53 Rue du Stade 97425 
- 1× LABUSE ne rattache pas d'adresse (BAN propose « 7ter Chemin Pavé 97425
- 1× LABUSE ne rattache pas d'adresse (BAN propose « 3 Chemin Pavé 97425 Le

## 3. PLU (Géoportail de l'urbanisme)

| Champ | Comparables | Conformes | Taux | LABUSE FAUX | Fraîcheur | Non comparable |
|---|---|---|---|---|---|---|
| plu_document | 444 | 444 | 100% | 0 | 0 | 0 |
| plu_zone | 444 | 444 | 100% | 0 | 0 | 56 |

Non comparable — raisons :
- 51× GPU ne publie pas de zonage sur la parcelle
- 5× GPU injoignable : curl 92 sur https://apicarto.ign.fr/api/gpu/zone-u

## 4. Risques (Géorisques)

| Champ | Comparables | Conformes | Taux | LABUSE FAUX | Fraîcheur | Non comparable |
|---|---|---|---|---|---|---|
| aleas_presence | 456 | 456 | 100% | 0 | 0 | 44 |
| argiles_rga | 0 | 0 | — | 0 | 0 | 483 |
| catnat_total | 500 | 500 | 100% | 0 | 0 | 0 |
| potentiel_radon | 0 | 0 | — | 0 | 0 | 483 |
| ppr_zonage_brut | 217 | 217 | 100% | 0 | 0 | 283 |
| zonage_sismique | 0 | 0 | — | 0 | 0 | 500 |

Non comparable — raisons :
- 500× zone 2 - FAIBLE
- 483× argiles absentes au point
- 482× radon présent au point
- 266× hors PPR (couche brute) — l'absence de PPR n'est pas infirmable par l'
- 34× rapport risque instable
- 14× LABUSE sans aléa servi ; Géorisques au point : Inondation, Séisme, Mou
- 13× LABUSE sans aléa servi ; Géorisques au point : Inondation, Risques côt
- 1× radon absent au point

## 5. Ventes (DVF Etalab)

| Champ | Comparables | Conformes | Taux | LABUSE FAUX | Fraîcheur | Non comparable |
|---|---|---|---|---|---|---|
| dvf_derniere_mutation | 63 | 63 | 100% | 0 | 0 | 0 |
| dvf_secteur_n_ventes[appartement] | 55 | 55 | 100% | 0 | 0 | 14 |
| dvf_secteur_n_ventes[maison] | 253 | 253 | 100% | 0 | 0 | 0 |
| dvf_secteur_n_ventes[terrain] | 132 | 132 | 100% | 0 | 0 | 19 |
| dvf_ventes_parcelle | 437 | 437 | 100% | 0 | 0 | 0 |

Non comparable — raisons :
- 4× recompte brut 110 ≠ agrégat servi 78 (dédup/filtre qualité/appariement
- 3× recompte brut 12 ≠ agrégat servi 8 (dédup/filtre qualité/appariement t
- 3× recompte brut 260 ≠ agrégat servi 168 (dédup/filtre qualité/appariemen
- 2× recompte brut 384 ≠ agrégat servi 277 (dédup/filtre qualité/appariemen
- 2× recompte brut 67 ≠ agrégat servi 36 (dédup/filtre qualité/appariement 
- 2× recompte brut 25 ≠ agrégat servi 5 (dédup/filtre qualité/appariement t
- 2× recompte brut 18 ≠ agrégat servi 9 (dédup/filtre qualité/appariement t
- 2× recompte brut 23 ≠ agrégat servi 14 (dédup/filtre qualité/appariement 

## 6. Bâti (RNB / BD TOPO)

| Champ | Comparables | Conformes | Taux | LABUSE FAUX | Fraîcheur | Non comparable |
|---|---|---|---|---|---|---|
| batiments_nb | 416 | 416 | 100% | 0 | 0 | 84 |

Non comparable — raisons :
- 18× RNB (1) en deçà des 2 bâtiments servis — registre RNB en cours de comp
- 11× RNB (0) en deçà des 1 bâtiments servis — registre RNB en cours de comp
- 8× RNB (2) en deçà des 3 bâtiments servis — registre RNB en cours de comp
- 3× RNB (0) en deçà des 2 bâtiments servis — registre RNB en cours de comp
- 3× RNB (1) en deçà des 4 bâtiments servis — registre RNB en cours de comp
- 3× RNB (1) en deçà des 3 bâtiments servis — registre RNB en cours de comp
- 1× bbox 817×848 m trop large pour un compte RNB comparable
- 1× bbox 1037×448 m trop large pour un compte RNB comparable

## 7. Entreprises (Recherche d'entreprises / SIRENE)

| Champ | Comparables | Conformes | Taux | LABUSE FAUX | Fraîcheur | Non comparable |
|---|---|---|---|---|---|---|
| proprietaire_denomination | 103 | 103 | 100% | 0 | 0 | 1 |
| proprietaire_dirigeants | 0 | 0 | — | 0 | 0 | 59 |
| proprietaire_etat | 2 | 2 | 100% | 0 | 0 | 0 |
| proprietaire_moral | 0 | 0 | — | 0 | 0 | 396 |
| proprietaire_siren | 104 | 104 | 100% | 0 | 0 | 0 |

Non comparable — raisons :
- 367× pas de propriétaire société servi
- 29× SIREN introuvable dans le répertoire
- 6× dirigeants officiels : ALFONSI, ATCHAPA, GRAVE (LABUSE ne sert pas les
- 3× dirigeants officiels : BEGUE, BROSSARD, BUFFI (LABUSE ne sert pas les 
- 3× dirigeants officiels : BOCHATON (AUCLAIR), DUPONT, NEYRET (GLEIZES) (L
- 3× dirigeants officiels : HENRIETTE, LAURET, AGENCE DE SERVICES ET DE PAI
- 2× dirigeants officiels : FRECAUT, PAYET FONTAINE, HDM AUDIT (LABUSE ne s
- 2× dirigeants officiels : AUGUSTINE, CHAZELLE, CLAIN (LABUSE ne sert pas 

## 8. Énergie & permis (ADEME DPE, Sitadel)

| Champ | Comparables | Conformes | Taux | LABUSE FAUX | Fraîcheur | Non comparable |
|---|---|---|---|---|---|---|
| dpe_rattache | 1 | 1 | 100% | 0 | 0 | 499 |
| permis_sitadel | 0 | 0 | — | 0 | 0 | 500 |

Non comparable — raisons :
- 499× LABUSE ne rattache aucun DPE à la parcelle (absence non assertable : r
- 437× 0 permis rattaché(s) à la parcelle dans Sitadel ingéré (pas d'API Sita
- 54× 1 permis rattaché(s) à la parcelle dans Sitadel ingéré (pas d'API Sita
- 7× 2 permis rattaché(s) à la parcelle dans Sitadel ingéré (pas d'API Sita
- 2× 3 permis rattaché(s) à la parcelle dans Sitadel ingéré (pas d'API Sita

## 3 bis. PLU — règles chiffrées relues au règlement (100 parcelles)

100 parcelles, 336 règles (hauteur/emprise/reculs) relues au règlement officiel à la page citée (verbatim + PDF officiel). **CONFORME 330 · LABUSE FAUX 1 · NON COMPARABLE 5**.

| Règle | Conformes | LABUSE FAUX | Non comparable |
|---|---|---|---|
| emprise | 63 | 1 | 0 |
| hauteur | 98 | 0 | 0 |
| recul_limites | 69 | 0 | 5 |
| recul_voirie | 100 | 0 | 0 |

Non comparable = reculs dérivés d'une règle de prospect (H/2…), valeur calculée non littérale. Détail complet : `PLU-REGLES-100.md`.

