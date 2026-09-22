# FICHE-AUDIT-1 — Inventaire complet de la fiche parcelle

Branche `feat/fiche-audit-1`, départ `main` **6eb14b01**. **Inventaire en LECTURE SEULE — aucun
déplacement, aucun renommage, aucune correction.** Ce document sert à écrire le mandat de
rangement. `tsc -b` vert (exit 0).

## Les trois chiffres

| | | |
|---|---:|---|
| **N tiroirs** | **12** | accordéon exclusif (un seul ouvert à la fois), **tous repliés par défaut**, sous deux intertitres muets « Le terrain » / « Le contexte ». S'y ajoutent **5 sections hors-accordéon** (en-tête 6 tuiles · carte Analyse · Signaux · rangée IA · Exports/actions). |
| **M lignes affichables** | **111** | données du registre câblées à une surface de la fiche (robinets ∪ déclarations). Réparties : **63 parcelle** · 41 commune · 4 propriétaire · 2 zone · 1 annonce. La fiche rend en plus des éléments **hors-registre** (portes/liens, prose, exports) non comptés ici. |
| **K données parcelle absentes** | **60** | sur les **123** données à la maille parcelle du registre, **63 sont câblées** à la fiche, **60 ne le sont nulle part dans la fiche**. |

> Méthode. La **vérité de structure** (ordre des tiroirs, état par défaut, ce qui est caché) est
> lue dans `frontend/src/components/fiche/Fiche.tsx` et ses sous-composants, **prouvée par capture**
> sur deux parcelles témoins. La **vérité de câblage** (quelle donnée alimente quelle surface) est
> lue dans le registre : `src/labuse/registre/robinets.py` (les endroits qui affichent) et
> `declarations/fiche/*.yaml` (les câbles déclarés). Le registre des données est
> `src/labuse/registre/donnees.py` (253 données, dont 123 à `niveau='parcelle'`).

## Les deux parcelles témoins (choisies par SQL)

| rôle | IDU | commune | zone | signature |
|---|---|---|---|---|
| **fortement contrainte** | `97410000AN0347` | Saint-Benoît | **Nerl** (naturelle/ERL littoral) | 6 aléas · 3 SUP · propriétaire moral (COMMUNE) · territoire fiscal · 2 bâtiments · verdict **Écartée** |
| **simple, zone U** | `97422000AK0924` | Le Tampon | **Ub** | 1 aléa · 0 SUP · propriétaire physique · verdict **Sans signal** |

Sélection SQL : `parcel_zone_plu.zone_fam` + surface, richesse confirmée par l'API `/parcels/{idu}`.
Le tiroir conditionnel **Réhabilitation** n'apparaît sur aucune des deux → prouvé en bonus sur
`97415000DI0183` (Saint-Paul, U2d, `mode_b.disponible=true`).

**Preuve** : `captures/fiche-audit/{constrained,simple}/` — un PNG pleine hauteur par tiroir déplié
(00 = en-tête + Analyse ; 01→12 = tiroirs), `captures/fiche-audit/rehabilitation/`, et
`captures/fiche-audit/manifest.json`. Script rejouable : `frontend/qa/fiche_audit1.mjs`.

---

## 1. Les tiroirs, dans l'ordre d'affichage

Mécanisme : primitive `RefDrawer` (`primitives.tsx:79`) lisant un **accordéon exclusif**
(`FicheAccordionCtx`, `primitives.tsx:69`) ; l'état vit dans le store `s.ficheTiroir[idu]`
(`Fiche.tsx:596`). L'auto-ouverture historique a été retirée (`Fiche.tsx:654`) → **tout est replié
au départ**. Un tiroir n'est cliquable que s'il a un `id` **et** des enfants (`primitives.tsx:103`).

**Sections hors-accordéon (toujours dans le flux, de haut en bas) :** bannière Événement (si
`f.evenement==='rouge'`) · bloc Module (si `modBlock`) · **carte En-tête** (IDU, adresse, 6 tuiles)
· **CTA « Demander à LABUSE d'analyser la parcelle »** → **carte Analyse** (verdict) · bannière RNU
(si `f.rnu`) · rangée IA · groupe **Signaux** (badges EBC/ER, si `presc`).

Puis les **12 tiroirs** de l'accordéon :

| # | id | Titre | Défaut | Condition d'apparition | Corps (composant) | Témoin contraint | Témoin simple |
|---|---|---|:--:|---|---|:--:|:--:|
| — | | *Le terrain* (intertitre) | — | toujours | `GroupLabel` `Fiche.tsx:1291` | — | — |
| 1 | `regles` | **Urbanisme** | replié | **toujours** | inline `Fiche.tsx:1295` | ✅ | ✅ |
| 2 | `faisabilite` | **Constructibilité** | replié | **toujours** | `ConstructibiliteSection` `constructibilite.tsx:826` | ✅ | ✅ |
| 3 | `dispositifs` | **Dispositifs et périmètres** | replié | si `f.dispositifs` | `DispositifsDrawer` `constructibilite.tsx:718` | ✅ | ✅ |
| 4 | `mode-b` | **Réhabilitation** | replié | **si `f.mode_b.disponible`** | `ModeBDrawer` `constructibilite.tsx:528` | ❌ | ❌ (→ `97415000DI0183`) |
| 5 | `le_bien` | **Le bien** | replié | si `f.le_bien.disponible` | `LeBienSection` `leBien.tsx:34` | ✅ | ✅ |
| 6 | `risques` | **Risques et protections** | replié | **toujours** | `RisquesSection` `risques.tsx:32` | ✅ | ✅ |
| — | | *Le contexte* (intertitre) | — | toujours | `GroupLabel` `Fiche.tsx:1422` | — | — |
| 7 | `marche` | **Marché et secteur** | replié | **toujours** | `MarcheSection` `marche.tsx:35` | ✅ | ✅ |
| 8 | `viabilisation` | **Réseaux et accès** | replié | **toujours** | `ReseauxSection` `reseaux.tsx:58` | ✅ | ✅ |
| 9 | `autour-zone` | **Autour de cette parcelle** | replié | **toujours** | `AutourSection` `autour.tsx:24` | ✅ | ✅ |
| 10 | `territoire` | **Dispositifs territoriaux** | replié | si `f.territoire_fiscal` | inline `Fiche.tsx:1443` | ✅ | ✅ |
| 11 | `proprio` | **Propriétaire** | replié | **toujours** | inline `Fiche.tsx:1491` | ✅ | ✅ |
| 12 | `confiance` | **Données et méthode** | replié | **toujours** | inline `Fiche.tsx:1590` | ✅ | ✅ |

**Sections hors-accordéon en pied :** rangée d'actions (CRM · Projet) · grille **Exports** (Dossier ·
Financier · Apporteur · Pré-dossier PC · Courrier · Remonter le temps) · mentions légales ·
« Signaler une erreur ».

> **Écart de rangement n°1 (structure).** Les **16 surfaces déclarées** dans `declarations/fiche/`
> (`fiche_parcelle_fibre`, `_filiation`, `_score`, `_solaire`, `_division`, `_confiance`…) **ne
> correspondent pas 1:1 aux 12 tiroirs rendus** : Fibre et Solaire sont rendus **dans** Réseaux ;
> Filiation **dans** Le bien ; Division **dans** Propriétaire ; Score **dans** la carte Analyse ;
> Confiance **dans** Données et méthode. Le découpage déclaré ≠ le découpage vu.

---

## 2. Les lignes, tiroir par tiroir

Légende colonnes — **donnée** = id du registre (`donnees.py`) ; **niv** = maille ; **source** =
réservoir(s) ; **état** = `en_tête` (visible tiroir ouvert) / `replié` (sous un `<details>`, après
clic) ; **YAML** = fichier de `declarations/fiche/` qui la câble, ou **« robinet seul »** = rendue
mais **non déclarée** dans un YAML de la fiche.

### En-tête — 6 tuiles (hors-accordéon) · preuve `00_entete_analyse.png`
| Ligne | donnée | niv | source | YAML |
|---|---|---|---|---|
| Surface | `surface_parcelle_m2` | parcelle | cadastre_api_carto | entete_tuiles.yaml |
| Zone | `zone_plu_famille` | parcelle | gpu_plu_api_carto | entete_tuiles.yaml |
| Pente | `pente_deg` | parcelle | rge_alti | entete_tuiles.yaml |
| Exposition | `exposition_versant` | **ORPHELIN** | (lazy `getParcelExposition`) | entete_tuiles.yaml |
| Taxe foncière | `tfpb_taux_pct` | commune | dgfip_rei | entete_tuiles.yaml |
| SDP restante | `sdp_residuelle_m2` | parcelle | cosia, gpu_plu_api_carto | entete_tuiles.yaml |
| (Adresse) | `adresse_ban` | parcelle | ban | robinet seul |
| (Géométrie) | `parcelle_geometrie` | parcelle | cadastre_api_carto | robinet seul |

### Carte Analyse (hors-accordéon, **derrière le CTA**) · preuve `00_entete_analyse.png`
| Ligne | donnée | niv | source | état |
|---|---|---|---|---|
| Verdict / classement | `tier_opportunite` | parcelle | bd_topo,cosia,dvf,filosofi_carreaux,sitadel | en_tête (après CTA) |
| Rang dans le tier | `rang_tier` | parcelle | interne | replié |
| Probabilité / percentile / « Pourquoi ce score » | (score_v2, `ScoreV2Block`) | parcelle | — | replié |
| « Pourquoi pas ? » | (`PourquoiPasTab`) | parcelle | — | si Écartée/SOFT_FLAG |
| « Vérifications d'éligibilité — ✓ N passées » | lignes `result==='PASS'` | parcelle | — | **replié `<details>`** |

### Signaux (hors-accordéon) · badges
| Ligne | donnée | niv | source | YAML |
|---|---|---|---|---|
| Emplacement réservé (badge) | `er_emplacement_reserve` | parcelle | gpu_prescriptions_er | robinet seul |
| Espace boisé classé (badge) | `ebc_classe` | parcelle | gpu_prescriptions_ebc | robinet seul |

### Tiroir 1 — Urbanisme · preuve `01_Urbanisme.png`
| Ligne | donnée | niv | source | YAML |
|---|---|---|---|---|
| Règlement de la zone (extraits) | `reglement_plu_bloc` | parcelle | gpu_plu_api_carto, sudocuh | sections_restantes.yaml |
| Zonage PLU (par type) | `zone_plu_famille` | parcelle | gpu_plu_api_carto | (voir en-tête) |
| Règles d'urbanisme (statut commune) | `statut_plu` | commune | gpu_plu_api_carto, sudocuh | robinet seul |
| APER / PLU fraîcheur / Radar procédure / Traducteur IA | *(hors-registre : `f.aper`, `f.plu_fraicheur`, `f.radar_procedure`, `TraducteurBloc`)* | — | — | — |

### Tiroir 2 — Constructibilité · preuve `02_Constructibilite.png`
| Ligne | donnée | niv | source | YAML |
|---|---|---|---|---|
| Potentiel (verdict) | `potentiel_verdict` | parcelle | bd_topo,cosia,gpu_plu_api_carto | sections_restantes.yaml |
| Capacité (logements) | `capacite_logements` | parcelle | bd_topo,cosia,gpu_plu_api_carto | sections_restantes.yaml |
| SDP résiduelle | `sdp_residuelle_m2` | parcelle | cosia,gpu_plu_api_carto | (voir en-tête) |
| Surface vendable (estimé) | `surface_vendable_m2` | parcelle | bd_topo,cosia,gpu_plu_api_carto | robinet seul |
| Surface de plancher (table rase) | `surface_plancher_m2` | parcelle | bd_topo,cosia,gpu_plu_api_carto | robinet seul |
| Marge de surélévation | `marge_surelevation_m` | parcelle | lidar_hd_mnh,bd_topo,gpu_plu_api_carto | robinet seul |
| Mixité sociale (clause) | `mixite_clause` | parcelle | gpu_plu_api_carto | robinet seul |
| Charge foncière | `charge_fonciere_eur` | parcelle | cadastre_api_carto,dvf | sections_restantes.yaml |
| Prix du neuf — observé | `prix_neuf_observe_eur_m2` | commune | dvf | robinet seul |
| Taxe d'aménagement — taux communal | `taxe_amenagement_estimee_eur` | parcelle | taxe_amenagement | sections_restantes.yaml |
| Rappel RTAA DOM | *(`RtaaBlock` ; cf. `rtaa_exigences`, déclarée « outil » — voir §3-absentes)* | — | rtaa_dom | robinet seul |

### Tiroir 3 — Dispositifs et périmètres · preuve `03_Dispositifs_et_pe_rime_tres.png`
| Ligne | donnée | niv | source | YAML |
|---|---|---|---|---|
| Dispositifs (QPV, ANRU, ZFANG, FRR…) | `perimetres_dispositifs_liste` | parcelle | qpv_2024,npnru,zfang,frr_ex_zrr | sections_restantes.yaml |
| Prescriptions du droit des sols | `dispositifs_parcelle` | parcelle | gpu_prescriptions_er/ebc, dpu_perimetres, peb_dgac, sup_gpu | sections_restantes.yaml |
| Emplacement réservé | `er_emplacement_reserve` | parcelle | gpu_prescriptions_er | robinet seul |
| Espace boisé classé | `ebc_classe` | parcelle | gpu_prescriptions_ebc | robinet seul |
| Droit de préemption urbain | `dpu_perimetre` | parcelle | dpu_perimetres | robinet seul |
| Plan d'exposition au bruit | `peb_zone` | parcelle | peb_dgac | robinet seul |
| Servitudes d'utilité publique (SUP) | *(inclus dans `dispositifs_parcelle`, `d.sup`)* | parcelle | sup_gpu | — |

### Tiroir 4 — Réhabilitation (mode B) · preuve `rehabilitation/04_Rehabilitation_97415000DI0183.png`
Corps `ModeBDrawer`. Lignes **hors-registre** (bilan de réhabilitation calculé côté client :
achat max, terrain nu au prix secteur, surface réhabilitable, prix de sortie revente, coût travaux
saisi, sortie locative). Conditionnel `f.mode_b.disponible`. Aucune ligne câblée au registre.

### Tiroir 5 — Le bien · preuve `05_Le_bien.png`
| Ligne | donnée | niv | source | YAML |
|---|---|---|---|---|
| Emprise bâtie | `emprise_batie_m2` | parcelle | bd_topo,cosia | le_bien.yaml |
| Hauteur du bâti | `hauteur_bati_m` | parcelle | bd_topo,lidar_hd_mnh | le_bien.yaml |
| Nombre de bâtiments | `n_batiments` | parcelle | bd_topo | le_bien.yaml |
| Surface au sol libre | `surface_libre_sol_m2` | parcelle | bd_topo,cosia,cadastre_api_carto | le_bien.yaml |
| Bâti détecté CoSIA (hors BD TOPO) | `cosia_detecte_m2` | **ORPHELIN** | cosia | le_bien.yaml |
| Part artificialisée (OCS GE) | `part_artificialisee_pct` | parcelle | ocsge | le_bien.yaml (replié) |
| Usage du sol dominant (OCS GE) | `usage_sol_dominant` | parcelle | ocsge | le_bien.yaml (replié) |
| Pente du toit | `pente_toit_deg` | parcelle | lidar_hd_mnh | le_bien.yaml (replié) |
| Nature/forme du toit | `nature_toit` | parcelle | lidar_hd_mnh,bd_topo | le_bien.yaml (replié) |
| DPE connu | `dpe_connu` | parcelle | dpe_ademe | le_bien.yaml (replié) |
| Identifiants RNB | `rnb_batiments_liste` | parcelle | rnb | le_bien.yaml (replié) |
| Adresses liées au bâti (BAN PLUS) | `ban_plus_adresses_bati` | parcelle | ban_plus | le_bien.yaml (replié) |
| Filiation cadastrale (DFI) | `filiation_parcelle` | parcelle | dgfip_dfi | petites_sections.yaml (replié) |

### Tiroir 6 — Risques et protections · preuve `06_Risques_et_protections.png`
| Ligne | donnée | niv | source | état / YAML |
|---|---|---|---|---|
| Points de risque / Vigilances | `n_vigilances` | parcelle | abf_merimee,deal_ppr,georisques_api,znieff_inpn | risques.yaml |
| Aléas | `aleas_parcelle_liste` | parcelle | deal_ppr,georisques_api | risques.yaml |
| Sols pollués (SIS) | `sis_classe` | parcelle | georisques_sis | risques.yaml |
| Anciens sites industriels (CASIAS) | `casias_statut` | parcelle | georisques_casias | risques.yaml (replié) |
| Sols (SIS/CASIAS, bloc) | `sols_parcelle` | parcelle | georisques_sis/casias | robinet seul |
| Divergence SAR | `sar_divergence` | parcelle | sar_region | robinet seul |
| AZI / TRI (inondation, commune) | `azi_tri_commune` | commune | georisques_azi_tri | robinet seul |
| Ligne HT / Ligne MT (proximité) | *(hors-registre : `f.proximites.ligne_ht/ligne_mt`)* | — | — | — |
| **« N couches sans objet — déplier »** | lignes `result==='PASS'` de l'onglet risques | parcelle | — | **replié `<details data-risques-sans-objet>`** — voir §5 |

> Note : `endiguement_zone_protegee` est **déclarée** dans `risques.yaml` mais **ORPHELINE** au
> registre (id absent de `donnees.py`).

### Tiroir 7 — Marché et secteur · preuve `07_Marche_et_secteur.png`
| Ligne | donnée | niv | source | YAML |
|---|---|---|---|---|
| Terrain nu — secteur | `prix_terrain_secteur_eur_m2` | parcelle | cadastre_api_carto,dvf | marche.yaml |
| Ancien bâti — secteur | `prix_sortie_bati_eur_m2` | parcelle | dvf | marche.yaml |
| Ventes retenues | `ventes_retenues_n` | parcelle | dvf | marche.yaml |
| Ventes écartées | `ventes_ecartees_n` | parcelle | dvf | marche.yaml (replié) |
| Ventes à moins de 100 m | `ventes_100m_n` | parcelle | dvf | robinet seul |
| Mutations de la parcelle (DVF) | `dvf_parcelle_liste` | parcelle | dvf | marche.yaml (replié) |
| Neuf VEFA — commune | `prix_neuf_vefa_acte_eur_m2` | commune | dvf | marche.yaml |
| Annonces en cours (Radar) | `radar_annonces_liste` | parcelle | radar_pige,dvf | marche.yaml (replié) |
| Parc social (RPLS) | `parc_social_rpls_logements` | commune | rpls_sdes | robinet seul |
| *(contexte commune : `prix_ancien_median_eur_m2`, `mutations_12m_n`, `prix_terrain_zone_eur_m2`, `loyer_median_eur_m2`, `annonces_actives_n`, `prix_demande_median_eur_m2`, `ecart_demande_acte_pct`)* | commune | dvf/radar_pige/loyers | robinet seul |

### Tiroir 8 — Réseaux et accès · preuve `08_Re_seaux_et_acce_s.png`
| Ligne | donnée | niv | source | YAML |
|---|---|---|---|---|
| Viabilisation | `viabilisation_verdict` | parcelle | bd_topo,rge_alti,parkings_osm_aper | reseaux.yaml |
| Pente | `pente_deg` | parcelle | rge_alti | (voir en-tête) |
| Piscine détectée | `piscine_m2` | parcelle | bd_ortho | reseaux.yaml (replié) |
| Arrêt de transport le plus proche | `distance_arret_m` | parcelle | gtfs_pan,osm_transport | reseaux.yaml (replié) |
| Stationnement allégé (TCSP) | `tcsp_stationnement_allege` | parcelle | gtfs_pan,osm_transport | robinet seul |
| Logements raccordés à l'égout | `part_logements_egout_pct` | parcelle | insee_rp2022_egoul,gpu_zonage_assainissement | robinet seul |
| Fibre (FTTH) | `fibre_parcelle` | parcelle | arcep_fibre | petites_sections.yaml |
| Productible solaire | `prod_spec_kwh_kwc` | parcelle | bd_topo,pvgis,lidar_hd_mnh,bd_ortho_irc | (rendu ici via Viabilisation) |
| Gestionnaires (eau/assainissement/élec/SPANC) | *(hors-registre : `GestionnairesBlock`, `f.gestionnaires`)* | — | — | — |

### Tiroir 9 — Autour de cette parcelle · preuve `09_Autour_de_cette_parcelle.png`
| Ligne | donnée | niv | source | YAML |
|---|---|---|---|---|
| Quartier (IRIS) | `iris_quartier` | parcelle | insee_rp_iris,contours_iris | sections_restantes.yaml |
| Population du secteur | `population_zone` | zone | filosofi_carreaux | sections_restantes.yaml (replié) |
| Ventes voisines (100 m) | `voisinage_100m_liste` | parcelle | dvf,sitadel | sections_restantes.yaml (replié) |
| Permis à proximité | `n_permis_proximite` | parcelle | sitadel | sections_restantes.yaml (replié) |
| Sur cette parcelle (permis) | `historique_permis_liste` | parcelle | sitadel,cadastre_epoque | robinet seul |
| À proximité (équipements) | `equipements_proximite_liste` | parcelle | bpe_insee,osm_overpass | robinet seul |
| Déposés sur le secteur (36 mois) | `depots_secteur_n` | zone | sitadel | robinet seul |
| Quartiers de la commune (IRIS) | `iris_commune_quartiers` | commune | insee_rp_iris | robinet seul |

### Tiroir 10 — Dispositifs territoriaux · preuve `10_Dispositifs_territoriaux.png`
| Ligne | donnée | niv | source | YAML |
|---|---|---|---|---|
| Taxe foncière (TFPB) | `tfpb_taux_pct` | commune | dgfip_rei | (voir en-tête) |
| Taxe foncière non bâti (TFPNB) | `tfpnb_taux_pct` | commune | dgfip_rei | robinet seul |
| ACV / PVD / ORT (Denormandie) | `ort_statut` | commune | anct_ort | robinet seul |
| Zonage A/B/C (logement) | `zonage_abc_logement` | commune | zonage_abc_dhup | robinet seul |
| Périmètres / ZFANG / FRR / dispositifs DOM | *(hors-registre : `f.territoire_fiscal.*`)* | — | — | — |

### Tiroir 11 — Propriétaire · preuve `11_Proprie_taire.png`
| Ligne | donnée | niv | source | YAML |
|---|---|---|---|---|
| Type de propriétaire | `type_proprietaire` | proprietaire | dgfip_parcelles_pm | sections_restantes.yaml |
| Historique de détention (PM) | `proprietaire_timeline_liste` | proprietaire | dgfip_parcelles_pm | sections_restantes.yaml (replié) |
| Événements propriétaire (BODACC) | `evenements_proprietaire_liste` | proprietaire | bodacc,sirene,recherche_entreprises | robinet seul |
| Parcelles détenues (patrimoine) | `n_parcelles_pm` | proprietaire | dgfip_parcelles_pm | robinet seul |
| Divisibilité | `divisible_classe` | parcelle | cadastre_api_carto,cosia,gpu_plu_api_carto | sections_restantes.yaml |
| Copropriétés (RNIC) | `coproprietes_liste` | parcelle | rnic_anah | sections_restantes.yaml (replié) |

### Tiroir 12 — Données et méthode · preuve `12_Donne_es_et_me_thode.png`
| Ligne | donnée | niv | source | état |
|---|---|---|---|---|
| Indice de confiance (ICD) | `verdict_icd` | parcelle | interne | sections_restantes.yaml |
| Sources utilisées sur cette fiche | *(hors-registre : `f.data_sources[]`)* | — | — | en_tête |
| **« Ce que LABUSE ne peut pas savoir (N) »** | *(hors-registre)* | — | — | **replié `<details data-donnees-absentes>`** — voir §5 |

---

## 3. Ce qui manque — 60 données parcelle absentes de la fiche

Sur les 123 données à `niveau='parcelle'`, **63 sont câblées** à la fiche et **60 ne le sont
nulle part**. Chacune vit ailleurs dans le produit (colonne « vit-où » = catégorie de robinet).
Aucune n'est un « trou » silencieux : ce sont, pour l'essentiel, les **saisies du simulateur
financier** (`page_client`) et les **lignes du bilan promoteur** (`pdf`), qui n'ont pas leur place
dans la fiche par construction.

**Répartition des 60 :** `page_client` 23 · `pdf` 20 · `outil` 9 · `couche` 5 · `copilote` 1 ·
`en_attente` (nulle part) 2.

| donnée | libellé | source | vit-où |
|---|---|---|---|
| `mixite_quota_pct` | Mixité sociale — quota de logements | gpu_plu_api_carto | **NULLE PART (en_attente)** |
| `mixite_seuil_m2` | Mixité sociale — seuil de déclenchement | gpu_plu_api_carto | **NULLE PART (en_attente)** |
| `rtaa_exigences` | Rappel RTAA DOM (exigences de conception) | rtaa_dom | outil *(⚠ or rendu dans Constructibilité via `RtaaBlock` — voir écart n°2)* |
| `taxe_amenagement_eur` | Taxe d'aménagement (montant) | taxe_amenagement | outil |
| `azimut_bati_deg` | Azimut (estimé) | bd_topo | outil |
| `assemblage_parcelles_n` | Parcelles assemblées | cadastre_api_carto | outil |
| `assemblage_surface_m2` | Surface assemblée | cadastre_api_carto | outil |
| `ecart_prix_demande_pct` | Écart au prix demandé | — | outil |
| `prix_demande_saisi_eur` | Prix demandé (saisi) | — | outil |
| `cout_construction_saisi_eur_m2` | Coût de construction (saisi) | — | outil |
| `marge_frais_saisie_pct` | Marge et frais (saisis) | — | outil |
| `destination_statut` | Peut-on ouvrir une activité ? (verdict) | gpu_plu_api_carto, sudocuh | copilote |
| `verdict_couche` | Verdict · Classement servi (couche) | bd_topo,cosia,dvf,filosofi_carreaux,sitadel | couche *(jumeau carto de `tier_opportunite`)* |
| `zonage_plu_couche` | Zonage PLU par parcelle (couche) | gpu_plu_api_carto | couche, pdf *(jumeau de `zone_plu_famille`)* |
| `classe_residuel` | Densifier l'existant | bd_topo,cadastre_api_carto,cosia | couche |
| `densifier_couche` | Densifier l'existant (couche) | — | couche |
| `limites_parcelles_couche` | Limites parcelles (couche) | cadastre_api_carto | couche |
| `prix_achat_historique_eur` | Prix d'achat historique de la parcelle | dvf | pdf |
| `charge_fonciere_basse_eur` / `charge_fonciere_haute_eur` | Charge foncière — bornes | — | pdf |
| `prix_revient_eur_m2` · `seuil_rentabilite_eur` · `redevance_archeologie_eur` | (bilan) | — | pdf |
| `sensibilite_cout_construction` · `sensibilite_prix_sortie` | Sensibilités (bilan) | — | pdf |
| `bilan_*` (13 : ca, marge, cout_construction, demolition, depollution, vrd, portage, stationnement, frais, frais_acquisition, honoraires_techniques, aleas) | Postes du bilan promoteur | dvf / rge_alti / — | pdf |
| `*_saisi*` (23 : apport, prix_revente, taux_apport, part_sociale, logements_vises, typologie_moyenne, regime_tva, scenario, duree_portage, commission_apporteur, stationnement_type, travaux_revente, vrd_saisi, prix_sortie_saisi, prix_refuse, prix_achat_revente, prix_vente_bailleur, cout_place_stationnement, frais_acquisition, honoraires_techniques, marge_visee, aleas, taxe_amenagement) | Saisies du questionnaire financier | — | page_client |

Liste complète des 60 ids reproductible : union `robinets`(catégorie `fiche`) ∪ `declarations/fiche`,
comparée à `{niveau=='parcelle'}` de `donnees.py`. **Candidats réels pour un rangement** (les seuls
qui ne vivent nulle part ou mal rangés) : **`mixite_quota_pct` + `mixite_seuil_m2`** (en attente
d'un chantier) et **`rtaa_exigences`** (déclarée « outil » alors qu'un `RtaaBlock` s'affiche dans
Constructibilité). Le reste (saisies + bilan + jumeaux carto) est **hors-fiche par construction**.

---

## 4. Les doublons — une même information dans deux endroits

**Doublons rendus (une même information dans deux surfaces vues)** — relevés dans le code, à
confirmer/arbitrer au rangement :

1. **SDP résiduelle** — tuile en-tête « SDP restante » (`sdp_residuelle_m2`, `Fiche.tsx:886`) **et**
   Constructibilité → `TransformationBlock`. Même source `f.potentiel_transformation`.
2. **Zone PLU** — tuile en-tête « Zone » **et** Urbanisme (ligne fermée + `ReglementPluBlock`).
   Même `zone_plu_famille`.
3. **Prix de sortie — bâti secteur** — Marché « Prix de sortie — bâti secteur » (`prix_sortie_bati_eur_m2`)
   **et** Constructibilité → `BilanTab` « Prix de sortie retenu ». Même médiane DVF (renvoi assumé).
4. **Pente** — tuile en-tête « Pente » (`pente_deg`, rge_alti) **et** Réseaux → `EquipementsBadges`
   (pente ortho). Deux sources pour un même fait.
5. **EBC / Emplacements réservés** — badges **Signaux** (haut de fiche) **et** Dispositifs et
   périmètres (`er_emplacement_reserve`, `ebc_classe`). Signaux = résumé dérivé des mêmes prescriptions.
6. **« Pourquoi ce score »** — deux fois dans la carte Analyse : `<details data-pourquoi>` (`f.score_v2.pourquoi`)
   **et** `ScoreV2Block` (rendu depuis `/v2/score/{idu}`).
7. **Probabilité de vente sous 1 an** — en-tête de la carte Analyse **et** de nouveau dans `ScoreV2Block`.

**Doublons de registre (une donnée servie par deux robinets `fiche`)** :

- `prod_spec_kwh_kwc` — `fiche_parcelle_solaire` **et** `fiche_soleil` (l'outil solaire).
- `prix_demande_median_eur_m2` — `fiche_commune_annonces` **et** `fiche_annonce` (Radar).

*(Non-doublon à ne pas confondre : la tuile « Taxe foncière » (`tfpb_taux_pct`) et la « Taxe
d'aménagement » de Constructibilité sont **deux taxes différentes**.)*

---

## 5. Les cachées — visibles seulement après un clic

**Tout l'accordéon est replié au départ** (12 tiroirs). Au-delà, contenus cachés dans un pli :

| Où | Ce qui est caché | Mécanisme | Preuve |
|---|---|---|---|
| Haut de fiche | **toute la carte Analyse** (verdict, score, pourquoi pas) | derrière le **CTA « Demander à LABUSE d'analyser »** (`verdictRevele[idu]`, `Fiche.tsx:938`) | `00_*` |
| Analyse | « Vérifications d'éligibilité — ✓ N passées » | `<details>` (`primitives.tsx:306`) | `00_*` |
| Analyse | « Pourquoi ce score » | `<details data-pourquoi>` | `00_*` |
| **Risques** | **« N couche(s) sans objet — déplier »** (toutes les couches `PASS`) | **`<details data-risques-sans-objet>`** (`risques.tsx:152`) — **c'est ici que TCSP/forêt domaniale se cachaient** (une couche évaluée sans contrainte active y tombe) | `06_*` (déplié) |
| **Données et méthode** | **« Ce que LABUSE ne peut pas savoir (N) »** | `<details data-donnees-absentes>` (`Fiche.tsx:1630`) | `12_*` (déplié) |
| Données et méthode | ICD « Ce qui manque » | `<details>` (`Fiche.tsx:38`) | `12_*` |
| Urbanisme | Traduction IA du PLU (`TraducteurBloc`) ; « Destinations · … » (`ZoneDestinationsLigne`) | bouton React « déplier ▾ » | `01_*` |
| Constructibilité | « RTAA DOM — N exigences → » | bouton `RtaaBlock` | `02_*` |
| Propriétaire | « Voir les anciens propriétaires — N millésimes » | bouton `ProprietaireHistorique` (si `n_changements>0`) | `11_*` |
| Le bien | valeurs OCS GE, toit, RNB, BAN PLUS, filiation | lignes `replié` (le_bien.yaml) | `05_*` |
| Marché | ventes écartées, mutations parcelle, annonces Radar | lignes `replié` (marche.yaml) | `07_*` |
| Autour | chaque permis → `PermitDrawer` (tiroir secondaire) ; isochrone tracée à l'ouverture | clic sur ligne | `09_*` |
| Toute la fiche | fiche `SourceDrawer` (extrait + carte source) | clic sur un nom de source | — |
| Toute la fiche | la **recherche** (loupe) remplace la pile de tiroirs par les lignes filtrées | `Fiche.tsx:807` | — |

---

## Écarts de rangement relevés (pour le mandat suivant — non corrigés ici)

1. **Surfaces déclarées ≠ tiroirs rendus** : 16 surfaces `declarations/fiche/` pour 12 tiroirs
   (Fibre/Solaire/Filiation/Division/Score/Confiance sont rendus dans un autre tiroir). §1.
2. **Sous-déclaration** : sur **111 lignes câblées, 51 sont déclarées** dans un YAML de la fiche ;
   **60 sont rendues par robinet seul** (non déclarées). Ex. parcelle : `er/ebc/dpu/peb`,
   `surface_vendable_m2`, `surface_plancher_m2`, `marge_surelevation_m`, `mixite_clause`,
   `sar_divergence`, `tcsp_stationnement_allege`, `part_logements_egout_pct`, `sols_parcelle`,
   `ventes_100m_n`, `historique_permis_liste`, `equipements_proximite_liste`,
   `evenements_proprietaire_liste`, `n_parcelles_pm`.
3. **Orphelins de registre déclarés/rendus** : `exposition_versant`, `cosia_detecte_m2`,
   `endiguement_zone_protegee` sont affichés/déclarés mais **absents de `donnees.py`**.
4. **`rtaa_exigences`** rendu dans la fiche (Constructibilité `RtaaBlock`) mais déclaré côté
   **outil** — soit un vrai câble manquant, soit deux notions homonymes à distinguer.
5. **Doublons** : 7 doublons rendus (§4) à arbitrer (surtout « Pourquoi ce score » ×2 et la
   probabilité ×2 dans la carte Analyse).

---

## Ce qu'on ne fait pas

Aucun déplacement, aucun renommage, aucune correction. Aucune tuile, aucune déclaration, aucun
robinet touché. `tsc -b` vert. Le rapport, les captures et les scripts QA (`frontend/qa/fiche_audit1.mjs`,
`fiche_audit1_rehab.mjs`) sont les seuls ajouts. « Ne merge pas. »
