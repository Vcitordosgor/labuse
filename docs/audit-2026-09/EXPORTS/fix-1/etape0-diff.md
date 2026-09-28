# Étape 0 — Diff fiche ↔ Dossier


## 97408000AO1424

| section | id | libellé fiche | valeur servie (type) | rendu PDF |
|---|---|---|---|---|
| identite | divisible_classe | Divisibilité | — | — |
| identite | adresse_ban | Adresse | str=54 Rue Mahatma Gandhi, 97419 La Possess | oui |
| identite | secteur_lieu_dit | Secteur (lieu-dit) | — | — |
| identite | type_proprietaire | Type de propriétaire | — | oui |
| identite | coproprietes_liste | Copropriétés (RNIC) | — | oui |
| identite | filiation_parcelle | Filiation cadastrale | dict[4] | oui |
| identite | prix_achat_historique_eur | Dernière vente (DVF) | — | oui |
| identite | parcelle_geometrie | Géométrie de la parcelle | — | oui |
| identite | historique_permis_liste | Sur cette parcelle (permis) | — | oui |
| identite | proprietaire_timeline_liste | Historique de détention (PM) | — | oui |
| terrain | surface_libre_sol_m2 | Surface au sol libre | int=24303 | oui |
| terrain | part_artificialisee_pct | Part artificialisée (OCS GE) | float=14.5 | oui |
| terrain | usage_sol_dominant | Usage du sol dominant (OCS GE) | str=US1.1 | oui |
| terrain | part_impermeabilisee_cosia_pct | Part imperméabilisée (CoSIA) | float=7.9 | oui |
| terrain | part_vegetalisee_cosia_pct | Part végétalisée/boisée (CoSIA) | float=92.0 | oui |
| terrain | part_sol_nu_cosia_pct | Part sol nu (CoSIA) | float=0.0 | oui |
| terrain | piscine_m2 | Piscine détectée | — | oui |
| bati | n_batiments | Bâtiments | int=6 | oui |
| bati | emprise_batie_m2 | Emprise bâtie | int=743 | oui |
| bati | hauteur_bati_m | Hauteur du bâti | float=8.4 | oui |
| bati | etablissements_parcelle_liste | Établissements sur la parcelle | — | — |
| bati | cosia_detecte_m2 | Bâti détecté CoSIA (hors BD TOPO) | — | oui |
| bati | pente_toit_deg | Pente du toit | — | oui |
| bati | nature_toit | Forme du toit | — | oui |
| bati | dpe_connu | DPE connu | — | — |
| bati | rnb_batiments_liste | Identifiants RNB | list[4] | oui |
| bati | ban_plus_adresses_bati | Adresses liées au bâti (BAN PLUS) | int=4 | oui |
| urbanisme | reglement_plu_bloc | Règlement de la zone (extraits) | dict[16] | oui |
| urbanisme | au_ouverture_statut | Ouverture de la zone AU | — | — |
| urbanisme | rtaa_exigences | Rappel RTAA DOM | — | oui |
| urbanisme | dispositifs_parcelle | Prescriptions du droit des sols | list[2] | oui |
| urbanisme | scot_parcelle | SCOT | str=SCOT TCO — approuvé le 2022-10-03 | oui |
| urbanisme | statut_plu | PLU | dict[11] | oui |
| urbanisme | er_emplacement_reserve | Emplacement réservé (ER) | — | oui |
| urbanisme | ebc_classe | Espace boisé classé (EBC) | list[1] | oui |
| urbanisme | dpu_perimetre | Droit de préemption urbain (DPU) | — | oui |
| urbanisme | peb_zone | Plan d'exposition au bruit (PEB) | — | oui |
| urbanisme | mixite_clause | Mixité sociale (clause) | — | oui |
| urbanisme | sar_divergence | Divergence SAR (indication) | — | oui |
| risques | n_vigilances | Points de risque | int=11 | oui |
| risques | aleas_parcelle_liste | Aléas | list[2] | oui |
| risques | sis_classe | Sols pollués (SIS) | — | oui |
| risques | endiguement_zone_protegee | Système d'endiguement | — | oui |
| risques | casias_statut | Anciens sites industriels (CASIAS) | — | oui |
| risques | enr_exclue_parcelle | EnR au sol interdites (APER) | — | oui |
| risques | mesures_compensatoires_parcelle | Mesure compensatoire (GéoMCE) | — | oui |
| risques | sols_parcelle | Sols (SIS/CASIAS, parcelle) | — | oui |
| reseaux | fibre_parcelle | Fibre (FTTH) | dict[6] | oui |
| reseaux | viabilisation_verdict | Viabilisation | dict[7] | oui |
| reseaux | distance_arret_m | Arrêt de transport le plus proche | dict[6] | oui |
| reseaux | part_logements_egout_pct | Logements raccordés à l'égout | dict[9] | oui |
| reseaux | tcsp_stationnement_allege | Stationnement allégé (TCSP, L151-36) | dict[5] | oui |
| reseaux | prod_spec_kwh_kwc | Productible solaire | — | oui |
| fiscalite | tfpb_taux_pct | Taxe foncière (TFPB) | dict[9] | oui |
| fiscalite | perimetres_dispositifs_liste | Dispositifs (QPV, ANRU, ZFANG, FRR…) | dict[6] | oui |
| fiscalite | taxe_amenagement_estimee_eur | Taxe d'aménagement — taux communal | dict[14] | oui |
| marche | prix_terrain_secteur_eur_m2 | Terrain nu — secteur | — | oui |
| marche | prix_sortie_bati_eur_m2 | Ancien bâti — secteur | dict[24] | oui |
| marche | ventes_retenues_n | Ventes retenues | dict[2] | oui |
| marche | prix_neuf_vefa_acte_eur_m2 | Neuf VEFA — commune | — | oui |
| marche | ventes_ecartees_n | Ventes écartées | dict[2] | oui |
| marche | dvf_parcelle_liste | Ventes de cette parcelle | list[4] | oui |
| marche | radar_annonces_liste | Annonces en cours (Radar) | — | oui |
| marche | ventes_100m_n | Ventes à moins de 100 m (36 mois) | dict[9] | oui |
| quartier | iris_quartier | Quartier (IRIS) | dict[14] | oui |
| quartier | population_zone | Population du secteur | — | — |
| quartier | voisinage_100m_liste | Ventes voisines (100 m) | dict[9] | oui |
| quartier | n_permis_proximite | Permis à proximité | dict[4] | oui |
| quartier | equipements_proximite_liste | À proximité (équipements) | list[4] | oui |
| potentiel | potentiel_verdict | Potentiel (verdict) | — | oui |
| potentiel | capacite_logements | Capacité (logements) | — | oui |
| potentiel | gabarit_implantation_m2 | Zone d'implantation | — | — |
| potentiel | gabarit_plan_2d | Plan 2D | — | — |
| potentiel | gabarit_emprise_plafond_m2 | Plafond d'emprise | — | — |
| potentiel | gabarit_hauteur_m | Hauteur réglementaire | — | — |
| potentiel | gabarit_motif_blocage | Gabarit — calcul incomplet | str=PLU non calibré pour la zone A (estimat | oui |
| potentiel | gabarit_couverture_verdict | Couverture réglementaire | — | — |
| potentiel | surface_plancher_m2 | Surface de plancher créée (table rase) | — | oui |
| potentiel | surface_vendable_m2 | Surface vendable (Estimé) | — | oui |
| potentiel | marge_surelevation_m | Marge de surélévation (au faîtage) | — | oui |
| simulation | verdict_icd | Indice de confiance (ICD) | — | — |
| simulation | charge_fonciere_eur | Charge foncière (indicative) | — | — |

## 97415000EO0796

| section | id | libellé fiche | valeur servie (type) | rendu PDF |
|---|---|---|---|---|
| identite | divisible_classe | Divisibilité | — | — |
| identite | adresse_ban | Adresse | str=6 Chemin Grand Contour, 97422 Saint-Pau | oui |
| identite | secteur_lieu_dit | Secteur (lieu-dit) | — | — |
| identite | type_proprietaire | Type de propriétaire | str=Personne morale — SOCIETE IMMOBILIERE D | oui |
| identite | coproprietes_liste | Copropriétés (RNIC) | — | oui |
| identite | filiation_parcelle | Filiation cadastrale | dict[4] | oui |
| identite | prix_achat_historique_eur | Dernière vente (DVF) | — | oui |
| identite | parcelle_geometrie | Géométrie de la parcelle | — | oui |
| identite | historique_permis_liste | Sur cette parcelle (permis) | — | oui |
| identite | proprietaire_timeline_liste | Historique de détention (PM) | list[7] | oui |
| terrain | surface_libre_sol_m2 | Surface au sol libre | int=320 | oui |
| terrain | part_artificialisee_pct | Part artificialisée (OCS GE) | float=100.0 | oui |
| terrain | usage_sol_dominant | Usage du sol dominant (OCS GE) | str=US5 | oui |
| terrain | part_impermeabilisee_cosia_pct | Part imperméabilisée (CoSIA) | float=78.9 | oui |
| terrain | part_vegetalisee_cosia_pct | Part végétalisée/boisée (CoSIA) | float=21.1 | oui |
| terrain | part_sol_nu_cosia_pct | Part sol nu (CoSIA) | float=0.0 | oui |
| terrain | piscine_m2 | Piscine détectée | — | oui |
| bati | n_batiments | Bâtiments | int=1 | oui |
| bati | emprise_batie_m2 | Emprise bâtie | int=159 | oui |
| bati | hauteur_bati_m | Hauteur du bâti | float=3.3 | oui |
| bati | etablissements_parcelle_liste | Établissements sur la parcelle | — | — |
| bati | cosia_detecte_m2 | Bâti détecté CoSIA (hors BD TOPO) | — | oui |
| bati | pente_toit_deg | Pente du toit | — | oui |
| bati | nature_toit | Forme du toit | — | oui |
| bati | dpe_connu | DPE connu | — | — |
| bati | rnb_batiments_liste | Identifiants RNB | list[3] | oui |
| bati | ban_plus_adresses_bati | Adresses liées au bâti (BAN PLUS) | int=2 | oui |
| urbanisme | reglement_plu_bloc | Règlement de la zone (extraits) | dict[16] | oui |
| urbanisme | au_ouverture_statut | Ouverture de la zone AU | — | — |
| urbanisme | rtaa_exigences | Rappel RTAA DOM | — | oui |
| urbanisme | dispositifs_parcelle | Prescriptions du droit des sols | — | oui |
| urbanisme | scot_parcelle | SCOT | str=SCOT TCO — approuvé le 2022-10-03 | oui |
| urbanisme | statut_plu | PLU | dict[11] | oui |
| urbanisme | er_emplacement_reserve | Emplacement réservé (ER) | — | oui |
| urbanisme | ebc_classe | Espace boisé classé (EBC) | — | oui |
| urbanisme | dpu_perimetre | Droit de préemption urbain (DPU) | dict[3] | oui |
| urbanisme | peb_zone | Plan d'exposition au bruit (PEB) | — | oui |
| urbanisme | mixite_clause | Mixité sociale (clause) | — | oui |
| urbanisme | sar_divergence | Divergence SAR (indication) | — | oui |
| risques | n_vigilances | Points de risque | int=2 | oui |
| risques | aleas_parcelle_liste | Aléas | list[1] | oui |
| risques | sis_classe | Sols pollués (SIS) | — | oui |
| risques | endiguement_zone_protegee | Système d'endiguement | — | oui |
| risques | casias_statut | Anciens sites industriels (CASIAS) | — | oui |
| risques | enr_exclue_parcelle | EnR au sol interdites (APER) | — | oui |
| risques | mesures_compensatoires_parcelle | Mesure compensatoire (GéoMCE) | — | oui |
| risques | sols_parcelle | Sols (SIS/CASIAS, parcelle) | — | oui |
| reseaux | fibre_parcelle | Fibre (FTTH) | dict[6] | oui |
| reseaux | viabilisation_verdict | Viabilisation | dict[7] | oui |
| reseaux | distance_arret_m | Arrêt de transport le plus proche | dict[3] | oui |
| reseaux | part_logements_egout_pct | Logements raccordés à l'égout | dict[7] | oui |
| reseaux | tcsp_stationnement_allege | Stationnement allégé (TCSP, L151-36) | — | oui |
| reseaux | prod_spec_kwh_kwc | Productible solaire | — | oui |
| fiscalite | tfpb_taux_pct | Taxe foncière (TFPB) | dict[9] | oui |
| fiscalite | perimetres_dispositifs_liste | Dispositifs (QPV, ANRU, ZFANG, FRR…) | dict[6] | oui |
| fiscalite | taxe_amenagement_estimee_eur | Taxe d'aménagement — taux communal | dict[14] | oui |
| marche | prix_terrain_secteur_eur_m2 | Terrain nu — secteur | — | oui |
| marche | prix_sortie_bati_eur_m2 | Ancien bâti — secteur | dict[24] | oui |
| marche | ventes_retenues_n | Ventes retenues | dict[2] | oui |
| marche | prix_neuf_vefa_acte_eur_m2 | Neuf VEFA — commune | — | oui |
| marche | ventes_ecartees_n | Ventes écartées | dict[2] | oui |
| marche | dvf_parcelle_liste | Ventes de cette parcelle | list[3] | oui |
| marche | radar_annonces_liste | Annonces en cours (Radar) | — | oui |
| marche | ventes_100m_n | Ventes à moins de 100 m (36 mois) | dict[9] | oui |
| quartier | iris_quartier | Quartier (IRIS) | dict[14] | oui |
| quartier | population_zone | Population du secteur | — | — |
| quartier | voisinage_100m_liste | Ventes voisines (100 m) | dict[9] | oui |
| quartier | n_permis_proximite | Permis à proximité | dict[4] | oui |
| quartier | equipements_proximite_liste | À proximité (équipements) | list[4] | oui |
| potentiel | potentiel_verdict | Potentiel (verdict) | dict[28] | oui |
| potentiel | capacite_logements | Capacité (logements) | — | oui |
| potentiel | gabarit_implantation_m2 | Zone d'implantation | float=250.2 | oui |
| potentiel | gabarit_plan_2d | Plan 2D | str=<svg xmlns="http://www.w3.org/2000/svg" | oui |
| potentiel | gabarit_emprise_plafond_m2 | Plafond d'emprise | str=Non réglementé | oui |
| potentiel | gabarit_hauteur_m | Hauteur réglementaire | float=13.0 | oui |
| potentiel | gabarit_motif_blocage | Gabarit — calcul incomplet | — | — |
| potentiel | gabarit_couverture_verdict | Couverture réglementaire | str=4 familles vérifiées sur 4 (reculs, emp | oui |
| potentiel | surface_plancher_m2 | Surface de plancher créée (table rase) | — | oui |
| potentiel | surface_vendable_m2 | Surface vendable (Estimé) | — | oui |
| potentiel | marge_surelevation_m | Marge de surélévation (au faîtage) | float=6.8 | oui |
| simulation | verdict_icd | Indice de confiance (ICD) | — | — |
| simulation | charge_fonciere_eur | Charge foncière (indicative) | — | — |