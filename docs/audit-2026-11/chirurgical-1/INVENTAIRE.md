# INVENTAIRE — AUDIT-CHIRURGICAL-1

> Tout ce que l'app LABUSE montre à un client : écrans, outils du menu, documents (PDF / ZIP+pièces / Excel / CSV), mails.
> Pour chaque sortie : d'où viennent ses chiffres (fonction backend, endpoint, table/run).
> Branche `audit/chirurgical-1`, base locale `labuse` (295 tables, 434 582 parcelles, 24 communes).
> Établi le 2026-11-14, LECTURE SEULE. Les numéros de ligne sont indicatifs (relevés par exploration, à revérifier au besoin).

---

## A. ÉCRANS (hors menu Outils)

| # | Écran | Frontend | Endpoint(s) | Fonction backend | Sources (table / run) |
|---|-------|----------|-------------|------------------|-----------------------|
| E1 | **Fiche parcelle** (verdict, double score, cascade, marché, risques, bâti, sources, IA) | `components/fiche/Fiche.tsx`, `BilanEcran.tsx`, `constructibilite.tsx`, `MarcheSecteurBlock.tsx`, `blocB.tsx`, `blocks.tsx`, `SourceDrawer.tsx` | `GET /parcels/{idu}` | `parcel_fiche()` (`api/app.py`) ; sous-blocs `_verdict_bloc`, `_marche_secteur`, `_bloc_risques`, `_bati_stats` (`bati.py`) | `parcels`, `dryrun_results` (score v2, run servi), `dryrun_parcel_evaluations`, `spatial_layers` (ppr/georisque_alea/…), `parcel_bati`, `dvf_mediane`/`dvf_quartier` |
| E2 | **Radar / Découverte** (2 portes : liste + veille) | `components/radar/RadarHub.tsx`, `RadarDeclaratif.tsx`, `VeillePromoteurs.tsx`, `RadarMarche.tsx` | `GET /discover`, endpoints veille | `discover()` (`app.py`) | `parcels`, `dryrun_results` (tier_v2), `parcelle_operations` |
| E3 | **Bilan promoteur** (calculette à rebours) | `components/fiche/BilanEcran.tsx` | `POST /bilan/{idu}/calcul`, `GET /bilan/{idu}/modele`, `GET /bilan/{idu}.pdf`, `.xlsx`, `GET /bilan-ratios` | `calculer_bilan()`, `modele_bilan()`, `bilan_pdf/xlsx` (`api/bilan.py`), moteur `faisabilite/bilan.py` + `bilan/moteur.py` | saisies utilisateur, `bilan_ratios`/`compte_bilan_ratios`, `parcel_capacite_restante`, `dvf_mediane` |
| E4 | **Liste parcelles** (panneau gauche, filtres + verdict) | `components/panel/LeftPanel.tsx` | `GET /parcels?...filters`, `GET /map/parcels.geojson` | liste pagée, tri tier v2 | `parcels`, `dryrun_results` |
| E5 | **Carte principale** (MapLibre, couches + ortho + PLU) | `components/map/MapView.tsx` | `GET /map/layers.geojson`, `GET /map/parcels.geojson` | couches GeoJSON | `spatial_layers`, `parcels` |
| E6 | **Copilote (IA restitution)** | `App.tsx` (IaRestitution) | `POST /copilote/analyser` | `api/copilote_v2.py` | LLM + critères utilisateur ; coût IA ~10,2 €/mois (hors périmètre chiffres clients) |

---

## B. MENU OUTILS

Registre : `frontend/src/components/outils/registry.ts`. Rail : `components/Rail.tsx` affiche `MODULES.filter(!hidden)`.

### Groupe « Instruire »
| Code | Outil (label client) | Frontend | Endpoint(s) | Backend | Sources |
|------|----------------------|----------|-------------|---------|---------|
| O13 | **PLU** | `Plu.tsx`, `PluAnnuaire.tsx`, `VerifProcedure.tsx`, `ProcedureChangement.tsx` | `/modules/plu-annuaire/search\|communes\|pack/{insee}`, `/modules/verif-procedure/{idu}` | `plu_annuaire_search`, `plu_communes`, `pluAnnuairePack`, `verifProcedure` (`modules.py`), `_plu_recherche_sql` (`plu_reglement.py`) | `plu_gpu_zone`, `plu_reglement`, `spatial_layers` |
| M16 | **Assemblage** | `Assemblage.tsx` (via M22) | store | `assemblage.py` | `module_assemblage` (parcelles contiguës même propriétaire) |
| A8 | **Comparer des parcelles** | `components/compare/ComparePanel.tsx` | `/comparateur/*` | `api/comparateur.py` | robinet fiche × N |
| M10 | **Pièges et risques** | `components/outils/blocB.tsx` | intégré `/parcels/{idu}` | `_bloc_risques`, `verite_terrain_plu_regles.py`, `verite_terrain.py` | `spatial_layers` (ppr, georisque_alea, abf, foret_publique, ens, safer, trait_de_cote), `dryrun_cascade_results` |
| M24 | **Gabarit réglementaire** | `Gabarit.tsx` | `/modules/gabarit` | `api/gabarit.py`, `gabarit/engine.py` | `parcel_gabarit`, PLU+PPR+BD TOPO |
| K3 | **Taxe d'aménagement** | `TaxeAmenagement.tsx` | `/modules/taxe-amenagement` | `taxe_amenagement.py` | barème commune/département |
| M23 | **Calculette foncière** (hidden) | `CalculetteFonciere.tsx` | `/bilan/{idu}/calcul` | `faisabilite/bilan.py` | idem Bilan |

### Groupe « Marché »
| Code | Outil | Frontend | Endpoint(s) | Backend | Sources |
|------|-------|----------|-------------|---------|---------|
| M03 | **Permis** (+ dormants M04) | `ModulePanel.tsx` | `/modules/permis`, `/modules/permis/{id}`, `/modules/promesses` | `permis`, `permis_fiche`, `promesses` (`modules.py`), `ingestion/permits.py` | `permits_sitadel`, `parcel_permits`, `permit_delais_m10` |
| O6 | **Communes** (fiche + évolution M18 + radar) | `Communes.tsx` | `/fiche-commune/{insee}`, `/modules/velocite` | `fiche_commune()` (`fiche_commune.py`), `velocite` | `communes`, `dvf_mediane`/`dvf_quartier`, INSEE/SIRENE, `parcel_*` |
| N1 | **Estimer un bien** | `AnalyserAnnonce.tsx` | `/analyse-annonce/{idu}.pdf`, `/analyse-annonce.pdf?url=` | `analyse_annonce_parcelle_pdf`, `analyse_annonce_lien_pdf` (`documents.py`), `radar_annonce_analyser` (`pige/api.py`) | DVF parcelle/commune, `estimer3` |
| M27 | **Étude de zone** (isochrone) | `EtudeZone.tsx` | `/modules/etude-zone` | `modules.py` + isochrone IGN + SIRENE | IGN, SIRENE, INSEE |
| S1 | **Mon secteur** (hidden, replié dans fiche) | `MonSecteur.tsx` | — | DVF secteur | `dvf_quartier` |

### Groupe « Agir »
| Code | Outil | Frontend | Endpoint(s) | Backend | Sources |
|------|-------|----------|-------------|---------|---------|
| M02 | **Scan patrimoine** | `ScanPatrimoine.tsx`, `ModulePanel.tsx` | `/modules/patrimoine/search`, `/modules/patrimoine` (+ `fmt=csv`) | `patrimoine_search`, `patrimoine` (`modules.py`) | `parcelle_personne_morale`, `parcels`, `bodacc_depots`, `parcel_blocs`, `dryrun_results` |
| M26 | **Prospection solaire** | `ProspectionSolaire.tsx` | `/modules/prospection-solaire[/parcelle/{idu}]`, `/modules/prospection-piscines[/liste]` | `prospection_solaire*`, `prospection_piscines*` (`modules.py`), `solaire_toiture.py` | `parcel_solar`, `parcel_piscines`, PVGIS |
| M29 | **Blocs fonciers** | `Blocs.tsx` | `/modules/blocs`, `/modules/blocs/{id}` | `blocs_liste`, `bloc_detail` (`modules.py`), `blocs.py` | `parcel_blocs`, `parcels`, `parcelle_personne_morale` |
| M28 | **Successions à venir** | `Successions.tsx` | `/modules/successions` | `successions_liste` (`modules.py`) | `parcelle_personne_morale`, `bodacc_depots`, INPI dirigeants |
| M09 | **Courrier propriétaire** | `ModulePanel.tsx` | `/modules/courriers`, `/modules/courrier/adressage\|composer` | `courriers` (`modules.py`), `api/courrier.py` | `parcelle_personne_morale`, adresses postales, campagne courrier |

### Groupe « Temps »
| Code | Outil | Frontend | Endpoint(s) | Backend | Sources |
|------|-------|----------|-------------|---------|---------|
| M08 | **Remonter le temps** (ortho par année) | `TimeMachine.tsx` | `/ortho/{idu}/liste`, `/ortho/{idu}/{year}.tif` | overlay MapLibre | orthos IGN multi-années |

### Hidden (résolvants internes, pas de tuile menu)
| Code | Outil | Frontend | Endpoint(s) | Backend | Sources |
|------|-------|----------|-------------|---------|---------|
| M22 | **Étude de faisabilité** (overlay plein écran depuis Docs) | `EtudeEcran.tsx` | `/modules/etude/parcelles\|stationnement\|jauge`, `/modules/etude`, `/modules/etude/pdf` | `etude_*` (`modules.py`), `scenarios.py`, moteur `faisabilite/moteur.py` + `revisions.py` | PLU, PPR, bâti LiDAR, run capacité |
| M18 | Baromètre / Rapport | onglet Communes | voir O6 | — | DVF historique |
| S3 | Veille promoteurs | onglet Scan patrimoine | — | — | `parcelle_operations` |

---

## C. DOCUMENTS PRODUITS

| # | Document (client) | Format | Déclencheur / endpoint | Fonction de génération | Chiffres clés & source |
|---|-------------------|--------|------------------------|------------------------|------------------------|
| D1 | **Dossier parcelle** (= « Flash », même rendu/numéro) | PDF (11 sections) | `GET /dossier/{idu}.pdf` ; Flash via `facturation._flash_fulfill` | `builder.construire()` (`exports/builder.py`) → `render_pdf()` (`exports/rendu.py`), WeasyPrint | robinet unique `robinet_fiche.py` + registre `registre/lectures.py` ; surface, zone, capacité, risques, marché, taxe |
| D2 | **Note Apporteur** | PDF à champs | `GET /apporteur/{idu}.pdf` (`documents.py`) | `builder.construire(document="apporteur")`, bloc `exports/blocs/apporteur.py` | même robinet + contexte compte (`marque`, email), voisines `parcel_bloc_membres`, validité 90 j |
| D3 | **Gabarit** | PDF (SVG 2D) | `GET /gabarit/{idu}.pdf` (`documents.py`) | `builder.construire_gabarit`, `exports/blocs/gabarit.py`, `gabarit/engine.py` | enveloppe, reculs, hauteurs ; **variante refus** si inconstructible (motif lu à `potentiel_batir`) |
| D4 | **Comparatif** | PDF paysage (≤3 col) | `GET /comparatif.pdf?idus=` (`documents.py`) | `builder.construire_comparatif`, `exports/blocs/comparatif.py` | robinet × N parcelles |
| D5 | **Étude de zone** | PDF paysage (7 sections) | `GET /etude-zone.pdf?idu=&rayon_km=&sous_destination=` | `builder.construire_etude_zone`, `exports/blocs/etude_zone.py`, `faisabilite/marche_commune.py` | prix DVF rayon, PLU autour, risques secteur |
| D6a | **Estimer — parcelle** | PDF | `GET /analyse-annonce/{idu}.pdf?surface_hab=&pieces=&ecartees=` | `builder.construire_analyse_annonce_parc`, `exports/blocs/annonce.py` | scénario saisi reproduit ; DVF mutation, hauteur LiDAR, robinet |
| D6b | **Estimer — lien annonce** | PDF | `GET /analyse-annonce.pdf?url=` | `builder.construire_analyse_annonce_lien`, `radar_annonce_analyser` (`pige/api.py`) | annonce normalisée (Leboncoin), bloc commune |
| D7 | **Bilan financier** | PDF | `GET /bilan/{idu}.pdf?doc_id=` | `Moteur.calculer` → `bilan/pdf.py` ; numéro `exports/numeros.py` | saisies + ratios compte (`bilan_ratios`), TVA/HT/TTC, SDP |
| D8 | **Bilan financier (Excel)** | XLSX | `GET /bilan/{idu}.xlsx?doc_id=` | `bilan/excel.py` (openpyxl, formules conservées) | même moteur Bilan (déterministe) |
| D9 | **Pré-dossier PC** | **ZIP** | `GET /pre-dossier/{idu}.zip` (`api/pre_dossier.py`) | `pre_dossier_zip()` | voir pièces internes ci-dessous |
| D10 | **Export projet (CSV)** | CSV | `GET /projets/{pid}/export.csv` (`api/projets.py`) | — | liste parcelles du projet |
| D11 | **Export projet (PDF)** | PDF | `GET /projets/{pid}/export.pdf` | — | carnet récapitulatif |

### Pièces internes du ZIP Pré-dossier (D9)
| Pièce | Fonction | Contenu & source |
|-------|----------|------------------|
| **CERFA 13406 (PCMI) ou 13409 (PC)** pré-rempli | `_cerfa_prerempli()` | ≥3 logements estimés → 13409, sinon 13406 ; champs TERRAIN cadre 2 (adresse BAN + réf. cadastrales) pré-remplis, **superficie NON pré-remplie** (à relever par pétitionnaire) ; millésime vérifié best-effort (`_millesime_perime_cache`) |
| **PCMI1 — Plan de situation** | `_pcmi1()` | vue d'ensemble + rapprochée, ortho IGN + contour cadastre, nord + échelle |
| **PCMI2 — Plan de masse existant** | `_pcmi2()` | dessin vectoriel coté, contour cadastral + bâti existant (BD TOPO) ; surface = `surface_m2`, emprise = `le_bien.emprise_batie_m2` ; partie projet vide |
| **Fiche règles & servitudes** (PCMI3 pseudo) | `_regles_et_pieces()` | zonage PLU, règles calibrées (hauteur/reculs/prospects), servitudes intersectant, alertes dormantes (zone humide/bruit/SUP/DPU/AU fermée lues en direct `spatial_layers`), destinations autorisées/interdites, taxe (non chiffrée), redevance archéo 0,40 %, capacité terrain libéré, bordereau pièces |

Rendu commun : WeasyPrint, `exports/theme.css`, cartouche `@page`, numéro `numero_rapport()`, archive JSON reproductible (`exports/archive.py`).

**Scripts de génération** : `scripts/docs1_regen_v11.py` (tous docs), `scripts/relecture_finale_docs.py`, `scripts/recette_exports1.py`.

---

## D. MAILS CLIENTS

Façade `mail.py` → file `mail_queue` (`mailfile.py`) → Brevo (template) ou SMTP (brut). Contenu rendu dans `mails_contenu.py`. 21 mails clients.

### Cycle de vie (Brevo)
| Clé | Tpl | Déclencheur | Données |
|-----|-----|-------------|---------|
| essai | 4 | admin crée essai 48 h | PRENOM, LIEN_INVITATION, FIN_ESSAI |
| souscription | 5 | admin envoi | PRENOM, LIEN_SOUSCRIPTION |
| onboarding1 | 6 | suite essai/inscription | PRENOM, LIEN_INVITATION |
| onboarding2 | 7 | J+3 auto (`licence_mails`) | PRENOM, JAMAIS_CONNECTE |
| onboarding3 | 8 | J+10 auto | PRENOM |
| relance_carte | 9 | webhook `payment_failed` / J+7 lecture seule | PRENOM, LIEN_PAIEMENT |
| suspension | 10 | webhook `subscription.deleted` / admin / essai expiré | PRENOM, LIEN_PAIEMENT |
| retablissement | 11 | webhook `invoice.paid` / admin | PRENOM, LIEN_APP |
| essai_fin_proche | 20 | job nocturne J−1 | PRENOM, DATE_FIN, LIEN_PAIEMENT |
| resiliation | 16 | webhook `subscription.deleted` | PRENOM, DATE_FIN_ACCES |

### Sécurité (Brevo)
| mdp_oublie | 14 | reset demandé | PRENOM, LIEN_RESET, VALIDITE 1 h |
| mdp_modifie | 15 | reset appliqué | PRENOM, DATE_HEURE |
| email_change | 18 | changement email — **déclencheur non trouvé dans le code** (template défini, appel invisible) | PRENOM, ANCIEN_EMAIL, NOUVEL_EMAIL |

### Transactions / rapports (Brevo)
| flash_pret | 17 | Flash payé + PDF généré | LIEN_PDF (30 j), IDU, COMMUNE |
| retour_traite | 19 | admin répond signalement | PRENOM, SON_MESSAGE, REPONSE |

### Radar / veilles
| radar_alerte | 13 (Brevo) | job `radar-cloche` + match veille | VEILLE, NB_BIENS, CRITERES, CARTES (HTML construit côté code), désinscription 1-clic |
| radar_digest | 12 | **RETIRÉ (legacy, plus envoyé)** | — |
| mise_en_vente | — (SMTP brut) | parcelle suivie + annonce | IDU, COMMUNE, TYPE, PRIX |
| suivi_digest | — (SMTP brut) | job digest | EVENEMENTS, MARCHE |

### Annonces / technique (SMTP brut)
| annonce | — | admin | TITRE, CORPS, LIEN |
| maintenance | — | admin | TITRE, CORPS, FENETRE (jamais de désinscription) |

**Annexe ops (non-client)** : `envoyer_ops()` (alertes admin/dev), journal `evenements_compte`.

---

## E. CE QUI N'AVAIT JAMAIS ÉTÉ RELU (focus mandat)
- **Bilan** (D7/D8, E3) : moteur `bilan/moteur.py`, formules HT/TVA/TTC, charge foncière à rebours.
- **Flash** : alias du Dossier (D1) — même rendu/numéro ; livré comme « Dossier sans section 9 ».
- **Apporteur** (D2) : refus 422 si parcelle disparue / compte sans nom.
- **Courrier** (M09) : coût signalé > prix dans un audit antérieur (0,19 €/courrier de perte — à revérifier).
- **Analyse par lien** (D6b) : parsing annonce externe + bloc commune.
