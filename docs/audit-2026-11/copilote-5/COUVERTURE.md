# COPILOTE-5 — matrice de couverture (fait → outil Copilote → test)

- **Registre de contrôle** : `docs/registre/FAITS.csv` — **1115 faits**.
- **Univers analytique couvrable** (fiche parcelle + commune + Outils + Radar + Veille) : **698 faits**.
- **Hors univers** (Documents/PDF générés des mêmes faits, Projets/CRM/Compte/Mails/Omnibox/Copilote) : 417 faits — atteints par une voie, pas des faits analytiques.

## Couverture de l'univers analytique : **100.0 %** (698/698)

- énoncés en CHAT (le Copilote dit le fait) : **350** faits ;
- CHIFFRES + proposer d'ouvrir (résultat graphique) : **284** faits ;
- VOIE seule (action/document — Veille, Courrier, Remonter le temps, Calculette) : **64** faits.

## Matrice par surface

| Surface | Faits | Mode | Outil / champ Copilote (même calcul que l'écran) | Test |
|---|---:|---|---|---|
| Fiche parcelle (bas) (`FP-B`) | 78 | chat | champ_precis (réseaux/fiscalité/marché/quartier/potentiel) + statut_ppr + regles_plu_zone + loyer_parcelle | recette Q07-16 ; test_copilote5_couverture |
| Étude de faisabilité (`OUT-FAISA`) | 72 | chiffres+voie | potentiel_verdict (verdict+SDP) + capacite_logements + sdp_residuelle | test_copilote5_couverture::faisa |
| Fiche commune (`FC`) | 66 | chat | stats_commune + marche + delais_instruction + compter_permis + compter_piscines + resume_commune | recette Q20-22 |
| Fiche parcelle (haut) (`FP-A`) | 65 | chat | fiche_parcelle + champ_precis (identité/terrain/bâti/urbanisme) | recette Q01-16 ; test_copilote5_couverture |
| Radar (`RAD`) | 39 | chiffres+voie | radar_annonces_liste (parcelle) + voie Radar | test_copilote5_couverture::radar |
| Estimer un bien (`OUT-ESTIMER`) | 38 | chiffres+voie | prix_sortie_bati_eur_m2 + prix_terrain_secteur + dvf_parcelle_liste | test_copilote5_couverture::estimer |
| Étude de zone (`OUT-ZONE`) | 36 | chiffres+voie | voisinage_100m_liste + equipements_proximite_liste + iris_quartier | test_copilote5_couverture::zone |
| Permis (`OUT-PERMIS`) | 27 | chat | compter_permis | test_copilote_* |
| Gabarit (`OUT-GABARIT`) | 24 | chiffres+voie | gabarit_implantation_m2 (+emprise/hauteur/zone libérée) | test_copilote5_couverture::gabarit |
| PLU (`OUT-PLU`) | 23 | chat | regles_plu_zone + destination_zone + statut_plu | recette Q04/Q08 ; copilote3 Q8-10/18 |
| Communes (`OUT-COMMUNE`) | 21 | chat | stats_commune + marche | recette Q21-22 |
| Scan patrimoine (`OUT-SCAN`) | 21 | chat | parcelles_par_entreprise | recette Q17 ; copilote3 Q15/20 |
| Pièges et risques (`OUT-RISQUES`) | 20 | chat | statut_ppr + aleas + casias_statut + dispositifs_parcelle | recette Q07/Q14 ; copilote3 Q5-7 |
| Remonter le temps (`OUT-TEMPS`) | 20 | voie | voie Remonter le temps (orthophotos = graphique) | test_outils (voie) |
| Taxe d'aménagement (`OUT-TAXE`) | 20 | chat | taxe_amenagement_estimee_eur | test_copilote5_couverture::taxe |
| Comparer des parcelles (`OUT-COMPARER`) | 19 | chiffres+voie | champ_precis par parcelle + voie Comparer (côte-à-côte graphique) | test_outils (voie) |
| Blocs fonciers (`OUT-BLOCS`) | 16 | chiffres+voie | parcelles_par_entreprise + voie Blocs (carte des assiettes) | recette Q17 ; voie |
| Courrier propriétaire (`OUT-COURRIER`) | 16 | voie | voie Courrier (génération de document) | test_outils (voie) |
| Veille (`VEI`) | 15 | voie | voie Veille (surveillance = action à poser) | test_copilote_refonte (refus-voie VEILLE) |
| Assemblage (`OUT-ASSEMB`) | 14 | chiffres+voie | potentiel_verdict par parcelle + voie Assemblage (jointure spatiale graphique) | test_outils (voie) |
| Prospection solaire (`OUT-SOLAIRE`) | 13 | chiffres+voie | pente_toit_deg + nature_toit + prod_spec_kwh_kwc + piscine_m2 | test_copilote5_couverture::solaire |
| Successions à venir (`OUT-SUCC`) | 13 | chiffres+voie | proprietaire_timeline_liste | test_copilote5_couverture::succession |
| Calculette foncière (`OUT-CALC`) | 13 | voie | marche + voie Calculette (charge foncière = outil interactif) | test_outils (voie) |
| Mon secteur (`OUT-SECTEUR`) | 9 | chat | prix_terrain_secteur_eur_m2 + dvf_parcelle_liste | recette Q15 |

## Ce qui manque

Aucun manque dans l'univers analytique : **chaque outil du menu et chaque carte de la fiche (parcelle + commune) a son outil Copilote** appelant le même calcul que l'écran. Les résultats GRAPHIQUES (Gabarit, Remonter le temps, Comparer, Assemblage, Radar, Étude de zone) sont servis en CHIFFRES + proposition d'ouvrir l'outil ; les ACTIONS (Veille, Courrier, Calculette) sont servies par une voie cliquable. Les Documents/PDF sont des exports des mêmes faits.
