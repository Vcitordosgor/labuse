# AUDIT PRODUIT — LES 27 (+1) OUTILS, UN PAR UN

## Phase 1 — Inventaire contradictoire

**L'écart « 15 dans le tiroir » expliqué nominativement** : le tiroir Outils contient
M01-M10 + M15-M19 = **15 modules**. Les 6 autres numéros vivent ailleurs PAR CONSTRUCTION :
M11 alertes = la cloche · M12 portefeuille vivant = badges du kanban CRM · M13 digest = lien
« Digest → » dans la cloche · M14 suivi = bouton 👁 de la fiche · M20 apporteur = bouton ↗ de la
fiche · M21 API = endpoint + doc `/api/v1/docs` (pas d'UI par nature). Les 6 hors-tiroir de la
roadmap : fiche, PDF, pré-instruction (onglet Risques), asymétrie (onglet Proprio), **Bilan**,
recherche NL (vue IA). Total : 21 + 6 = 27.

| Outil | Où il vit | État réel (avant ce mandat) | Ce qui manquait |
|---|---|---|---|
| M01 division | tiroir | complet | état URL du slider |
| M02 patrimoine | tiroir | complet | état URL du SIREN |
| M03 permis | tiroir | complet (zone câblée à l'inspection) | état URL période |
| M04 promesses | tiroir | complet | état URL période |
| M05 vélocité | tiroir | complet | — |
| M06 bailleur | tiroir | complet | — |
| M07 fantôme | tiroir | complet | — |
| M08 time machine | tiroir + fiche « 1950 » | complet (noir z>15 corrigé à l'inspection) | — |
| M09 courriers | tiroir | complet | — |
| M10 due diligence | tiroir | complet | — |
| M11 alertes | cloche | complet (veilles muettes corrigées à l'inspection) | — |
| M12 portefeuille vivant | kanban (badges) | complet | — |
| M13 digest | cloche → HTML | complet | envoi SMTP (assumé V1.1) |
| M14 suivi | fiche 👁 | complet | — |
| M15 simul PLU | tiroir | complet | état URL zone |
| M16 assemblage | tiroir + clic carte | complet | — |
| M17 ZAN | tiroir | complet | — |
| M18 baromètre | tiroir + PDF | complet | — |
| M19 matching | tiroir | complet (démo étiquetée) | — |
| M20 apporteur | fiche ↗ + /p/{token} | complet | révocation de lien (backlog) |
| M21 API | /api/v1 + doc | complet | gestion de clés (backlog) |
| fiche | clic parcelle | complète | ping carte au clic liste |
| PDF | fiche + due diligence + baromètre | complet | — |
| pré-instruction | fiche → Risques | complet (lignes tracées PPR/aléas/ICPE…) | — |
| asymétrie | fiche → Proprio | complet (INPI/BODACC/DPE + patrimoine via M02) | — |
| **BILAN** | fiche → Bilan | **VIDE = ABSENT** | TOUT (P0 n°2 : TA, QPV, TVA, charge foncière, vue mer) |
| recherche NL | vue IA + copilote | complète | état stub pas assez évident dans le panneau FICHE (P0 n°1) |

**Verdict Phase 1 : 25 complets, 1 partiel (recherche NL — visibilité de l'état), 1 ABSENT (Bilan).**

## Phase 2 — Les 3 P0 de la visite Vic : CORRIGÉS
1. **IA** : diagnostic = stub local (clé absente), les 3 capacités fonctionnent — le problème était
   la VISIBILITÉ de l'état. Fix : carte « Mode dégradé : stub local » + marche à suivre exacte
   (ANTHROPIC_API_KEY dans .env → relancer) dans le Copilote ET dans le panneau IA de la fiche.
2. **Bilan promoteur** : l'onglet expose enfin le moteur EXISTANT (faisabilite/engine + bilan.py,
   jamais branché) : capacité (verdict R+n, logements, SHAB, stationnement), prix de sortie secteur
   (médiane, fiabilité, tendance), charge foncière indicative (CA, CF médiane + fourchette,
   hypothèses dépliables), fiscal (QPV→TVA 2,1 %/8,5 %, TA = hypothèse étiquetée « à confirmer en
   mairie », prime vue mer). Bandeau « ne remplace pas une étude réglementaire ».
3. **Ping carte** : UN effet central sur la sélection → recentrage (zoom ≥ 16) + halo pulsé 2 s.
   Systématique par construction : résultats, modules, kanban, notifications passent tous par
   `select()`.

## Phase 3 — Notes A/B/C (« un promoteur réunionnais paierait-il ? ») + backlog
| Outil | Note | Justification / améliorations restantes (backlog priorisé) |
|---|---|---|
| M01 division | **A** | vendable (698 candidats, lot dessiné). B1 : slider surface/emprise exposés · B2 : rectangle inscrit exact |
| M02 patrimoine | **A** | le scan CBO en 2 clics est un argument démo. B1 : export CSV du patrimoine |
| M03 permis | **B** | données s'arrêtant à 01/2023 (flux à réabonner — donnée, pas code) · B2 : détail par permis |
| M04 promesses | **B** | codes état source non documentés (à confirmer auprès de la Région) |
| M05 vélocité | **B** | dépôt→décision impossible avec cette source ; brancher Sitadel national (backlog data) |
| M06 bailleur | **A** | preset + lecture LLS claire |
| M07 fantôme | **A** | verrou + levier par cas ; indivision/succession attendront les Fichiers fonciers |
| M08 time machine | **A** | le split 1950 est LE moment démo |
| M09 courriers | **A** | 15 courriers × 3 contextes vérifiés au contenu |
| M10 due diligence | **A** | refs souples, PDF/parcelle |
| M11 alertes | **A** | cloche + veilles qui notifient (corrigé à l'inspection) |
| M12 portefeuille | **B** | badges OK ; fil événementiel par carte = V1.1 (assumé) |
| M13 digest | **B** | contenu généré email-ready ; SMTP à brancher |
| M14 suivi | **A** | 👁 simple et branché aux événements |
| M15 simul PLU | **B** | analogie honnête (0,7 s) ; vrai recalcul règlementaire = prochain cycle |
| M16 assemblage | **A** | clic-carte + contiguïté + bandeau |
| M17 ZAN | **B** | indicatif (recouvrements OCS, quotas absents) — l'affiche |
| M18 baromètre | **A** | PDF distribuable |
| M19 matching | **B** | démo étiquetée ; vrais comptes à ouvrir |
| M20 apporteur | **A** | filigrane/horodatage/compteur ; révocation = backlog |
| M21 API | **B** | robinet + doc ; gestion de clés = backlog |
| **M22 faisabilité** | **A** | NOUVEAU — bidirectionnel, moteur existant réutilisé, copilote branché |
| fiche | **A** | 6 onglets pleins, tracés, ping |
| PDF | **A** | 3 types relus |
| pré-instruction (Risques) | **A** | lignes tracées PPR/aléas/ICPE/ABF |
| asymétrie (Proprio) | **A** | INPI/BODACC/DPE + M02 |
| **Bilan** | **A** | ABSENT → COMPLET (P0.2) |
| recherche NL | **A** | filtres + programme, état stub évident, refus propres |

**Backlog transverse** : paramètres de module dans l'URL (le module y est, ses réglages non —
choix assumé : la restauration du module couvre le cas partage principal) · fonds annuels IGN
2006-2015 (400 en libre sur le 974) · MVT vectoriel.

## Phase 4 — M22 (reco appliquée)
Ratios UTILISÉS et affichés : étage 3 m et place 25 m² (config PLU Saint-Paul, sourcés) ;
m²/unité par défaut 60 (hypothèse ÉTIQUETÉE, modifiable au formulaire) ; +15 % circulations
(hypothèse affichée dans le calcul). Sens 1 = moteur `estimate_capacity` existant (fourchettes
logements au sol/sous-sol, régime de stationnement Art. 12 calibré). Sens 2 = SDP min calculée
et AFFICHÉE + hauteur PLU vérifiée zone par zone (resolve_zone), « à instruire » sinon.
Copilote : l'IA TRADUIT vers le formulaire, le moteur déterministe calcule (doctrine inchangée).
