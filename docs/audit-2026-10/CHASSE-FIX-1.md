# CHASSE-FIX-1 — corrections de CHASSE-1, écart par écart

Branche `fix/chasse-1` (base `origin/main` `182a6f88` + merge `audit/chasse-1` `4f152dd7`) ·
worktree `~/Desktop/labuse-chassefix` · 2026-10-04/05. Aucun run, aucune bascule, pas de merge.
Migration `origine` non touchée (geste Vic). Verrous : `tests/test_chasse_fix1.py` (9 tests).

Point de départ : ECARTS.csv de CHASSE-1 = 24 FAUX · 2 DISCORDANT · 12 TROMPEUR · 5 SALE ·
2 à instruire. (Le rejeu `make chasse` d'étape 0 a été invalidé en fin de course par mes
propres patchs en parallèle — la baseline de référence reste celle, identique au code près,
de l'audit CHASSE-1 ; le rejeu final fait foi.)

## Écart par écart

| id | verdict initial | état | correction / preuve |
|----|-----------------|------|---------------------|
| C01 | FAUX bloquant | **corrigé** | `site_voisinage` compte des MUTATIONS (CTE muts, médiane par mutation). Repro 97411000BC0337 : 122 → **2**. Verrou `test_c01_voisinage_compte_des_mutations` (61 lignes → 2). |
| C02 | FAUX bloquant | **corrigé** | vue `v_parcel_dvf_last` : €/m² sur TOTAUX de la mutation (bâti dédupliqué, terrain sommé par parcelle) + `n_parcelles` servi ; flash porte enfin `multi_parcelles`. DDL appliquée en base dev (réversible, pas un run). Verrou `test_c02_vue_prix_m2_sur_totaux_mutation` (5000 €/m² bâti dédup, 1000 €/m² terrain sommé). |
| C03 | FAUX | **corrigé** | courrier : `count(DISTINCT id_mutation)`. |
| C04 | FAUX | **corrigé** (touche le run : ingestion) | `layers_ingest` : terrain mutation = somme par parcelle (plus « premier bout » ≈ ÷15) ; effet au prochain rebuild dvf_mutations. |
| C05 | FAUX | **corrigé** (touche le run : non — lectures live) | module Division + division_or : `DISTINCT geom` (mêmes gardes que ORACLE-FIX-1 D) — les 303 576 doublons inter-communes ne comptent plus double. La purge amont reste à faire à l'ingestion (noté). |
| C06 | DISCORDANT bloquant | **corrigé** | décision Vic « différée, pas exclue » : règle+libellé uniques `faisabilite/au_differe.py` ; moteur résiduel pose le drapeau (payload live) ; fiche §Potentiel (`niveau=differe`, « ≈ N m² après ouverture »), Faisabilité (badge+avertissement), Gabarit (bandeau, complet ET incomplete), Copilote (fait `capacite_differee`), PDF (miroir suit la fiche ; gabarit PDF rend le bandeau). SDP INCHANGÉE (touche le run : NON). Repro 97401000AT0452 : « Fort potentiel » → « Potentiel différé — ouverture de la zone requise · ≈ 2 852 m² après ouverture ». 4 verrous. Filtres : la capacité reste filtrable (différée ≠ exclue, le verdict liste dit déjà `declasse_au_fermee`) — décision documentée. |
| C07 | FAUX | **corrigé** | accueil : protocole du run SERVI (train 2017-2024), plus celui de q_v14 jamais basculé ; « dix ans » → 2017-2025. |
| C08/C09 | FAUX | **corrigé** | compteurs figés retirés des infobulles (33 622, 227 545/« la moitié ») — le POURQUOI reste, le compte vivant est servi ailleurs. |
| C10 | FAUX | **corrigé** | VEFA : 60 mois (5 ans) / seuil 8 — libellé = code. |
| C11 | FAUX | **corrigé** | PDF premium : « niveau de vie MOYEN » (c'est ind_snv/ind). |
| C12 | FAUX | **corrigé** | PDF miroir : « section cadastrale », plus « à moins de 500 m ». |
| C13 | FAUX | **corrigé** | PDF financier : « HT (TVA 8,5 % par défaut) » — voir commit Lot 2bis. |
| C14 | FAUX | **corrigé** | copilote : « % des PARCELLES de la commune ». |
| C15 | FAUX | **corrigé** | « ~0,5 % » (réel 18,3 %) → formulation sans chiffre figé. |
| C16 | FAUX cosm. | **corrigé** | SIS « 4 périmètres » / CASIAS « 453+56 » → inventaires vivants sans compte figé (front ; le registre backend garde ses notes internes non servies). |
| C17 | FAUX | **corrigé** | export HTML : la formule affichée porte le « ÷ 1,15 » réellement appliqué. |
| C18 | FAUX | **corrigé** | partners : « permis AUTORISÉS » (le WHERE porte sur la date d'autorisation). |
| C19 | FAUX | **corrigé** | registre RAP : 0,40 % assiette TA (CGI 1635 quater F, recodif. ord. 2022-883) dans les 2 fiches (seuil_rentabilite_eur + donnees.py) — le moteur était déjà juste (TAXE-FIX-1). |
| C20 | FAUX cosm. | **corrigé** | piscines « à confirmer » : précision mesurée 30-60 %. |
| C21 | FAUX cosm. | **corrigé** | dashboard : « 03:00 UTC (07:00 Réunion) ». |
| C22 | TROMPEUR bloquant | **corrigé** (touche le run : OUI — cascade stockée) | RisquesLayer : couverture PPR/aléas testée PAR COMMUNE (gabarit EnsLayer M70) ; famille non couverte → unknown « non couvert par la source sur cette commune », jamais fondue dans « Aucun risque ». Effet au prochain run de cascade. |
| C23 | TROMPEUR bloquant | **corrigé** (cascade : prochain run ; SUP live : immédiat) | SupLayer + SolPollueLayer + FricheLayer : même garde par commune ; côté LIVE, `_dispositifs_block` sert `sup_etat` (servi/hors/non_couvert) + note, et la phrase d'absence du miroir est conditionnée aux assiettes publiées. |
| C24 | TROMPEUR | **corrigé** | en-tête fiche : « Non identifié » (plus jamais « Particulier » pour un propriétaire non résolu) — aligné sur le tiroir. |
| C25 | TROMPEUR | **corrigé** | seuil minimal des médianes de référence UNIFIÉ : `seuils_effectif.mediane_generique = 8` (yaml), lu par dvf_mediane / signaux / pige.marche / mon_secteur (plus de « 5 » en dur) ; le texte « sous N ventes » suit la constante. |
| C26 | TROMPEUR | **classé avec preuve** | corriger l'éligibilité (NULL ≠ 0 au niveau du TIER) modifierait le classement servi = décision produit + run. Preuves posées : la branche surface×U/AU garde éligibles les SDP inconnues en U/AU ; la fiche trace « Marge SDP non calculée ». Doctrine écrite au code (statuts.py). À arbitrer par Vic pour q_v16. |
| C27 | TROMPEUR | **corrigé** | mécanisme « PLU dépublié » : `config/plu_depublies.yaml` (Saint-Leu, Saint-André) + note servie sur le bloc règlement (fiche + PDF miroir) : « règles citées du dernier état connu — à confirmer en mairie ». |
| C28 | TROMPEUR cosm. | **corrigé** | portage : VRD non chiffré ⇒ la convention (assiette = construction seule) est DITE au poste. |
| C29 | SALE | **classé avec preuve** | les 7 086 doublons DVF sont la MATIÈRE amont (lots × nature_culture du fichier source) ; tous les consommateurs comptent désormais des mutations (C01/C02/C03 + verrous). Dédoublonner la table détruirait l'information lot. |
| C30 | SALE | **classé avec preuve** | emprise scoring non clippée = choix COHERENCE-FIX-2 documenté (MAX BDTOPO/CoSIA, cap 300) ; aucun lecteur n'affiche le ratio brut (grep front = 0 usage). |
| C31 | SALE cosm. | **classé avec preuve** | les 58 hauteurs LiDAR aberrantes sont TOUTES badgées « Sources discordantes » (requête CHASSE-1 : badge_faitage=58, egout_sans_badge=0) — donnée amont à nettoyer au prochain survol, aucun mensonge servi. |
| C32 | SALE cosm. | **classé avec preuve** | les 7 « médianes hors bornes » = arrondi à l'euro (med int vs max float, écart ≤ 0,5 €). |
| C33 | SALE cosm. | **classé avec preuve** | dates futures = données amont réelles (SIRENE : ouvertures programmées INSEE ; surface_d : événements dérivés) — conservées telles quelles, l'affichage les date. |
| C34 | à instruire | **instruit → classé** | la zone officielle des 50 pas (couche DEAL `corridor_limite_haute`) fait foi ; la limite légale n'est PAS 81,20 m constants (délimitations par décret, étangs) — l'invariant naïf du mandat ne tient pas juridiquement. 754 parcelles conformes à la couche. |
| C35 | à instruire | **instruit → classé** | 10 propriétaires publics dans le top 200 : le score n'exclut pas la propriété publique (le filtre PM permet de les écarter) ; comportement produit à confirmer par Vic — aucune règle écrite ne l'interdit aujourd'hui. |
| C36 | TROMPEUR | **corrigé** | sentinelles : enquête publique St-Leu sans date-butoir figée ; « 2025-2026 provisoires » → sans années en dur ; SRU sans fenêtre figée. (« 90,7 % » ×8 et autres invérifiables : consignés, non bloquants.) |
| C37 | DISCORDANT cosm. | **classé avec preuve** | SDP à 2 temporalités = design M139 voulu (fraîcheur côté projet) — documenté LECTEURS.csv. |
| C38 | TROMPEUR | **corrigé en partie** | le PDF ne dit plus « 500 m » (C12) ; les 3 périmètres de « prix » restent légitimes et étiquetés (section cadastrale / rayon adaptatif / commune — COHERENCE-FIX-2). |
| C39 | FAUX cosm. | **corrigé** | étude de zone PDF : les clés lues = les clés servies (`proprietaires`, `n_parcelles`) — les 2 sections s'impriment à nouveau. |
| C40 | FAUX cosm. | **corrigé** | le filtre « 2013+ » annoncé est appliqué (WHERE date ≥ 2013-01-01). |
| C41 | FAUX cosm. | **corrigé** | aperçu digest : « 7 derniers jours » (le défaut réel). |
| C42 | FAUX cosm. | **corrigé** | yaml TA : alinéa 10° (aligné code + docstring). |
| C43 | TROMPEUR cosm. | **corrigé** | plus jamais « secteur 0 m » : rayon inconnu ⇒ libellé sans rayon. |
| C44 | TROMPEUR cosm. | **classé avec preuve** | « 0 m² » sur micro-parcelles < 2 m² : slivers déjà masqués des listes (F2) ; l'arrondi d'affichage fiche reste (impact : parcelles non servies par les filtres). |
| C45 | TROMPEUR cosm. | **classé avec preuve** | memo compteur /filtre 30 s après bascule : retard borné documenté (le pointeur suit en ≤ 3 s) ; clé de memo sans empreinte de run — noté pour un fix de fond si Vic le veut. |

## Colonne « touche le run »

Voir `CHANGEMENTS.csv`. Résumé : **OUI** pour C22/C23-cascade (lignes stockées par run — effet
au prochain run), C04 (ingestion DVF — effet au prochain rebuild), C26 si un jour corrigé
(tiers). **NON** pour tout le reste (service/affichage/vue SQL recalculée à la lecture —
y compris C06 : la SDP servie ne change pas d'un m²).

## Vérifications de fin

(complétées en fin de mandat — voir section Résultats ci-dessous)
