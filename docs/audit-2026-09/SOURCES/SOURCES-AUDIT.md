# SOURCES-AUDIT — les 121 sources par famille

> Généré par `scripts/audit_sources` (lecture seule, rejouable). Verdict en tête de ligne. Détail : `fiches/<id>.md`. Données : `SOURCES-AUDIT.csv`.

**Légende** : 🟢 PLEINE · 🟡 PARTIELLE · 🔵 BRANCHÉE INVISIBLE · 🟠 SERVIE HORS REGISTRE · ⚫ RETIRÉE/PÉRIMÉE · 🔴 À RETIRER · ⬜ À DEMANDER/BRANCHER · 🟣 MANUELLE · 🔗 ALIAS · 🏛 HUB

## Compte des verdicts

| Verdict | Nombre |
|---|---|
| PLEINE | 72 |
| À DEMANDER / À BRANCHER | 11 |
| PARTIELLE — champs manquants | 10 |
| PARTIELLE — couverture incomplète | 8 |
| ALIAS (doublon) | 5 |
| MANUELLE | 5 |
| RETIRÉE (déjà) | 5 |
| HUB (catalogue) | 3 |
| BRANCHÉE INVISIBLE (vide) | 1 |
| RETIRÉE | 1 |
| **Total** | **121** |

## Parcelles et propriété

| | Source | Verdict | Fiche remplie (4 témoins) | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **Cadastre (API Carto PCI)** (`1`) | PLEINE | 4/4 témoins | oui | — | 18 | fiche, outil, PDF, copilote, scoring |
| 🔗 | **Cadastre Etalab (bulk DGFiP/Etalab)** (`2`) | ALIAS (doublon) | 4/4 témoins | oui | KO | 0 | — |
| 🟢 | **data.regionreunion.com — Potentiel foncier** (`15`) | PLEINE | 3/4 témoins | oui | — | 0 | carte |
| 🟣 | **Fichiers fonciers (Cerema)** (`27`) | MANUELLE | n.a. (API/règles) | oui | — | 0 | — |
| 🟢 | **Cartofriches (Cerema)** (`35`) | PLEINE | 3/4 témoins | oui | OK | 0 | carte |
| 🟢 | **DGFiP — parcelles des personnes morales** (`71`) | PLEINE | 3/4 témoins | oui | OK | 4 | fiche, outil, copilote |
| ⚫ | **BDNB** (`89`) | RETIRÉE (déjà) | n.a. (API/règles) | oui | — | 0 | — |
| 🟢 | **DFI — documents de filiation informatisés (DGFiP)** (`132`) | PLEINE | 4/4 témoins | oui | OK | 1 | fiche |
| 🟢 | **BAN PLUS — lien adresse ↔ bâtiment (IGN)** (`147`) | PLEINE | 4/4 témoins | oui | OK | 1 | fiche |

- **Cadastre (API Carto PCI)** — Socle parcellaire complet (431 663 parcelles, 24/24), lu par la quasi-totalité des moteurs. À plein potentiel.
- **Cadastre Etalab (bulk DGFiP/Etalab)** — Canal bulk du MÊME réservoir que Cadastre API Carto (id 1). Alias correctement déclaré (alias_de=1). Rien à faire.
- **data.regionreunion.com — Potentiel foncier** — SOURCES-3 lot 0.5 (arbitrage Vic) : le producteur UNIQUE du potentiel foncier Région. Un seul chiffre servi, un seul producteur : id 9 (« Potentiel foncier Région (ODS) », famille urbanisme) devient son ALIAS. 4 906 objets en couche potentiel_foncier+sar.
- **Fichiers fonciers (Cerema)** — Fichiers fonciers Cerema — SOUS CONVENTION, non instruite. Aucune donnée ingérée. En attendant : DVF ouvert. Voir Lot 3 + DEMANDE.
- **Cartofriches (Cerema)** — Cartofriches Cerema (372 friches). Couche + signal foncier.
- **DGFiP — parcelles des personnes morales** — Cœur de Scan patrimoine / propriétaire. 7 millésimes empilés, sert le moteur propriétaire_historique.
- **BDNB** — BDNB — ne couvre pas le 974 (métropole seule, 0 ligne 974 vérifié). Retirée 06/09/2026 ; sentinelle+cron conservés pour un futur millésime 974. NB (lot 5) : LABUSE NE possède PAS BDNB.
- **DFI — documents de filiation informatisés (DGFiP)** — 409 623 liens 974 ingérés (job_sur_clic). Sert la reconstitution de propriété. Coverage insulaire complète.
- **BAN PLUS — lien adresse ↔ bâtiment (IGN)** — NOUVELLE (SOURCES-2 lot 3) : l'ID-RNB devient la clé de jointure DPE ↔ RPLS ↔ BAN (mandat). Donnée ban_plus_adresses_bati servie au bloc « Le bien » (/parcels/{idu}), filtre (0 hors 974, part RNB), sonde data.gouv last_update.

## Urbanisme et règles

| | Source | Verdict | Fiche remplie (4 témoins) | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **Urbanisme PLU/GPU (API Carto)** (`3`) | PLEINE | 3/4 témoins | oui | KO | 24 | fiche, carte, outil, PDF, copilote, scoring |
| 🔗 | **Potentiel foncier Région (Région ODS)** (`9`) | ALIAS (doublon) | 3/4 témoins | oui | KO | 0 | carte |
| 🟡 | **DEAL Réunion (WMS/WFS)** (`13`) | PARTIELLE — champs manquants | 2/4 témoins | oui | — | 0 | carte |
| 🟢 | **QPV 2024 (ANCT)** (`38`) | PLEINE | 3/4 témoins | oui | OK | 3 | fiche, carte |
| 🟢 | **RTAA DOM (textes réglementaires)** (`43`) | PLEINE | n.a. (API/règles) | non | — | 1 | outil |
| 🟡 | **SUP — assiettes GPU (API Carto)** (`44`) | PARTIELLE — couverture incomplète | 3/4 témoins | oui | OK | 2 | fiche, carte |
| 🟢 | **Classement sonore ITT (Cerema)** (`46`) | PLEINE | 3/4 témoins | oui | OK | 1 | carte |
| 🟢 | **50 pas géométriques — limite haute (DEAL)** (`47`) | PLEINE | VIDE sur 4/4 | non | OK | 1 | carte |
| 🟡 | **Sudocuh (procédures d'urbanisme)** (`62`) | PARTIELLE — champs manquants | 4/4 témoins | non | — | 6 | fiche, outil, copilote |
| 🟡 | **GPU — zonages d'assainissement** (`63`) | PARTIELLE — couverture incomplète | 4/4 témoins | non | OK | 1 | fiche, carte |
| 🟢 | **ZFANG — zone franche d'activité nouvelle génération (Légifrance)** (`72`) | PLEINE | 4/4 témoins | non | OK | 2 | fiche, carte |
| 🟢 | **FRR ex-ZRR — zone spéciale d'action rurale (Légifrance)** (`73`) | PLEINE | 4/4 témoins | non | OK | 2 | fiche, carte |
| 🟢 | **Consommation d'espaces NAF (Cerema — portail de l'artificialisation)** (`102`) | PLEINE | 4/4 témoins | non | — | 2 | fiche, outil |
| 🟢 | **GPU — emplacements réservés (prescriptions CNIG)** (`105`) | PLEINE | 3/4 témoins | non | KO | 3 | fiche, carte |
| 🟢 | **GPU — espaces boisés classés (prescriptions CNIG)** (`106`) | PLEINE | 3/4 témoins | non | KO | 3 | fiche, carte |
| 🟡 | **GPU — droit de préemption urbain (info-surf)** (`107`) | PARTIELLE — couverture incomplète | 2/4 témoins | non | KO | 3 | fiche, carte |
| ⬜ | **SAR — schéma d'aménagement régional (Région/DEAL)** (`118`) | À DEMANDER / À BRANCHER | 3/4 témoins | oui | — | 1 | fiche, carte, scoring |
| ⬜ | **Périmètres de ZAC (EPCI / communes / EPF Réunion)** (`136`) | À DEMANDER / À BRANCHER | n.a. (API/règles) | non | — | 0 | — |

- **Urbanisme PLU/GPU (API Carto)** — Zonage + prescriptions servis sur toute l'île, cœur de la faisabilité et du scoring. Interrogé en direct (GPU).
- **Potentiel foncier Région (Région ODS)** — SOURCES-3 lot 0.5 (arbitrage Vic) : même jeu Région ODS « potentiel foncier » que id 15, qui fait foi. Devient son ALIAS (alias_de=15). Un seul chiffre servi, un seul producteur.
- **DEAL Réunion (WMS/WFS)** — DEAL WMS/WFS — canal servi par proxys ; les tables sont portées par qpv/npnru. Peu autonome comme « source ».
- **QPV 2024 (ANCT)** — QPV 2024 (70 objets couche). Sert défiscalisation/TVA primo. À jour.
- **RTAA DOM (textes réglementaires)** — RTAA DOM = règles portées PAR LE CODE (aucune table), servies dans la faisabilité (contraintes construction DOM). 0 chiffre attaché car ce sont des règles, pas une donnée mesurée — ce n'est pas « invisible ». Textes Légifrance vérifiés « en vigueur ».
- **SUP — assiettes GPU (API Carto)** — 9 catégories SUP en vigueur ; T5/PT1/PT2 restreintes, AS1 (captages) NON publiée par le producteur. Couverture bornée par la publication GPU, pas par nous.
- **Classement sonore ITT (Cerema)** — Classement sonore ITT (arrêtés déc. 2023, 1 004 objets). Couche bruit routier.
- **50 pas géométriques — limite haute (DEAL)** — 50 pas géométriques (cadastre 1877 géoréf.). Limite littorale servie. Couche.
- **Sudocuh (procédures d'urbanisme)** — État 31/12/2024 (dépôt manuel). Sert les procédures PLU. À voir : fraîcheur (dépôt manuel, cadence non tenue automatiquement).
- **GPU — zonages d'assainissement** — GPU zonages d'assainissement — SIG complet 4/24 communes seulement (11/07/2026). Les 20 autres à demander (id 134). Couche zonage_assainissement (258 objets).
- **ZFANG — zone franche d'activité nouvelle génération (Légifrance)** — ZFANG (décret 2026-421). Zonage fiscal servi (couche + territoire fiscal). À jour.
- **FRR ex-ZRR — zone spéciale d'action rurale (Légifrance)** — FRR ex-ZRR (Légifrance). Zonage fiscal rural servi.
- **Consommation d'espaces NAF (Cerema — portail de l'artificialisation)** — Conso ENAF 2021-2024 par commune (portail artificialisation). Sert le contexte ZAN commune.
- **GPU — emplacements réservés (prescriptions CNIG)** — Emplacements réservés (typepsc 05) servis par commune via GPU. Couche + cascade.
- **GPU — espaces boisés classés (prescriptions CNIG)** — EBC (typepsc 01) servis par commune via GPU. Couche + cascade.
- **GPU — droit de préemption urbain (info-surf)** — SOURCES-2 lot 2 (balayage des 24 partitions, 13/09/2026) : publient au GPU — Saint-Denis 41, Saint-Paul 158 (délégations nommées), Sainte-Marie 1, Le Tampon 2 = 202 périmètres. « Jamais pas de DPU » est GRAVÉ dans la fiche : Saint-Pierre/Saint-Benoît = DPU institué, délégataire EPF documenté (hors GPU) ; Saint-Philippe = RNU ; les 17 autres = phrase EPF >80 % (Cour des comptes). TYPEINF 03 vérifié ≠ DPU (préemption ENS de L'Étang-Salé).
- **SAR — schéma d'aménagement régional (Région/DEAL)** — SAR — couche SIG officielle NON diffusée par la Région (recherche 07/09/2026). Un proxy vocations existe (sar_region). À demander à la Région (lot 7). Non opposable directement.
- **Périmètres de ZAC (EPCI / communes / EPF Réunion)** — Périmètres de ZAC — pas d'open data 974 fiable. À demander (EPCI/communes/EPF). Standard CNIG ZAC.

## Risques, nature, patrimoine

| | Source | Verdict | Fiche remplie (4 témoins) | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **Géorisques** (`4`) | PLEINE | 3/4 témoins | oui | KO | 2 | fiche, carte, outil, scoring |
| 🟡 | **Parc National de La Réunion (INPN)** (`7`) | PARTIELLE — champs manquants | VIDE sur 4/4 | oui | — | 1 | carte |
| 🟢 | **Forêts publiques (ONF)** (`8`) | PLEINE | 3/4 témoins | oui | — | 0 | carte |
| 🟡 | **RPG — déclarations agricoles (IGN/ASP)** (`10`) | PARTIELLE — champs manquants | 3/4 témoins | oui | — | 1 | carte |
| 🟢 | **OpenStreetMap / Overpass** (`19`) | PLEINE | 3/4 témoins | non | OK | 2 | fiche, carte |
| 🟢 | **ABF / Monuments historiques** (`24`) | PLEINE | 3/4 témoins | oui | OK | 1 | fiche, carte, outil, scoring |
| 🟡 | **INPN / patrinat — espaces protégés** (`25`) | PARTIELLE — champs manquants | 3/4 témoins | non | — | 1 | carte |
| 🟢 | **Cerema / GéoLittoral — indicateur d'érosion côtière** (`28`) | PLEINE | 3/4 témoins | oui | — | 0 | carte |
| 🟢 | **DEAL Réunion — PPR / aléas** (`30`) | PLEINE | 3/4 témoins | oui | — | 6 | fiche, carte, outil, scoring |
| 🟢 | **Géorisques — sites et sols pollués** (`32`) | PLEINE | 3/4 témoins | oui | OK | 0 | carte |
| 🟢 | **Géorisques — cavités souterraines** (`33`) | PLEINE | 2/4 témoins | oui | OK | 0 | carte |
| 🟢 | **Géorisques — ICPE** (`34`) | PLEINE | 3/4 témoins | oui | OK | 0 | carte |
| 🟢 | **Géorisques — mouvements de terrain** (`36`) | PLEINE | 3/4 témoins | oui | OK | 0 | carte |
| 🟢 | **ZNIEFF (INPN/MNHN)** (`76`) | PLEINE | VIDE sur 4/4 | oui | OK | 2 | fiche, carte, outil, scoring |
| ⚫ | **ZNIEFF (INPN / Région)** (`80`) | RETIRÉE (déjà) | n.a. (API/règles) | non | — | 0 | — |
| 🟢 | **CatNat (arrêtés GASPAR / Géorisques)** (`97`) | PLEINE | 4/4 témoins | non | KO | 1 | fiche |
| 🟢 | **PEB — plans d'exposition au bruit (DGAC via annexes GPU)** (`108`) | PLEINE | 1/4 témoins | non | OK | 3 | fiche, carte |
| ⬜ | **ZPPA — zones de présomption de prescription archéologique (Atlas des patrimoines)** (`110`) | À DEMANDER / À BRANCHER | n.a. (API/règles) | oui | — | 0 | — |
| 🟢 | **Ravines — domaine public fluvial (DEAL Carmen)** (`111`) | PLEINE | VIDE sur 4/4 | non | OK | 1 | carte |
| 🟡 | **Zones humides — inventaires DEAL (Carmen)** (`112`) | PARTIELLE — couverture incomplète | VIDE sur 4/4 | non | OK | 1 | carte |
| 🟢 | **Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)** (`113`) | PLEINE | 3/4 témoins | non | OK | 1 | carte |
| 🟢 | **AZI / TRI — inondation (Géorisques GASPAR)** (`114`) | PLEINE | 4/4 témoins | oui | KO | 1 | fiche, carte |
| 🟡 | **Géorisques — secteurs d'information sur les sols (SIS)** (`115`) | PARTIELLE — couverture incomplète | 3/4 témoins | oui | KO | 3 | fiche, carte |
| 🟢 | **Géorisques — CASIAS (anciens sites industriels)** (`116`) | PLEINE | 3/4 témoins | non | KO | 3 | fiche, carte |
| 🟡 | **DEAL — cartes de bruit stratégiques (CBS)** (`117`) | PARTIELLE — couverture incomplète | VIDE sur 4/4 | non | OK | 1 | carte |
| ⬜ | **ENS du Département (Conseil départemental)** (`139`) | À DEMANDER / À BRANCHER | n.a. (API/règles) | non | — | 0 | — |
| 🟢 | **Systèmes d'endiguement et zones protégées (DEAL Lizmap)** (`145`) | PLEINE | 3/4 témoins | non | OK | 0 | carte |
| ⬜ | **Carte hypsométrique du littoral (DEAL Lizmap)** (`146`) | À DEMANDER / À BRANCHER | n.a. (API/règles) | non | — | 0 | — |

- **Géorisques** — Aléas Géorisques servis (couche + fiche Pièges + cascade). Complété par 8 sources Géorisques sœurs.
- **Parc National de La Réunion (INPN)** — Parc National servi (3 objets couche). Licence « à confirmer » (jeu pnrun_2021 via Région ODS) — provenance à clarifier.
- **Forêts publiques (ONF)** — Alimente 0 chiffre(s) du registre ; visible dans : 1 couche(s) carte. *(raison auto — champs producteur non vérifiés, cf. mandat)*
- **RPG — déclarations agricoles (IGN/ASP)** — RPG déclarations agricoles servi via un PROXY IGN (RPG.LATEST, année non pinnée) ; le vrai RPG DAAF n'est pas public. Licence « à confirmer ». Code culture servi (canne). Couche « cultures déclarées » + cascade zone A.
- **OpenStreetMap / Overpass** — OSM/Overpass — aménités (21 561 objets). Signal. ODbL (share-alike) respecté.
- **ABF / Monuments historiques** — ABF/Monuments historiques (Mérimée, 200 périmètres). Couche + contrainte patrimoine.
- **INPN / patrinat — espaces protégés** — Espaces protégés INPN servis (couche ens). Licence « à confirmer ».
- **Cerema / GéoLittoral — indicateur d'érosion côtière** — Trait de côte / érosion côtière 2018 (24 168 objets). Couche carte. Millésime ancien (2018) à re-sonder. SOURCES-2 lot 6 : le fichier Réunion dédié existe bien chez le producteur (HTTP 200, Last-Modified 27/06/2018) — la couverture 974 est CONFIRMÉE, seul l'âge (8 ans) reste le point de vigilance (sentinelle octets en veille).
- **DEAL Réunion — PPR / aléas** — WFS Lizmap 01risque : PPR zonage + aléas inondation (76), mouvement de terrain (917) et — SOURCES-2 lot 3 — SUBMERSION MARINE (50 + 50 changement climatique) = 1 093 zones. + couche « état des PAC/PPR/PPRL » (24 communes, statuts et dates) qui sert le millésime PRODUCTEUR : PPR le plus récent approuvé le 16/04/2026.
- **Géorisques — sites et sols pollués** — Sites et sols pollués (513 objets). Couche + Pièges.
- **Géorisques — cavités souterraines** — Cavités souterraines (151 objets). Couche + Pièges.
- **Géorisques — ICPE** — ICPE (1 261 objets). Couche + Pièges + cascade.
- **Géorisques — mouvements de terrain** — Mouvements de terrain (3 085 objets). Couche + Pièges + cascade (RETOURS-13).
- **ZNIEFF (INPN/MNHN)** — ZNIEFF servies (162 objets, maj 29/08/2025). Canonique face à id 80 (canal Région, retiré). Voir S3.
- **ZNIEFF (INPN / Région)** — ZNIEFF canal Région — endpoint vivant mais 0 donnée. Retirée 06/09/2026. Canonique : id 76.
- **CatNat (arrêtés GASPAR / Géorisques)** — SOURCES-3 lot 1 : RATTACHÉE au registre — le chiffre `catnat_n` (« Arrêtés CatNat », fiche commune / Pièges) déclare `reservoirs=(catnat_gaspar,)`, table `catnat_arretes` : la provenance est tracée (l'arête posée en CIRCUIT-6 lot 0, confirmée ici). SOURCES-2 lot 1 : recoupement de l'export CSV national GASPAR à chaque ingestion (CSV 426 = base 426, écart 0 — garde « l'API a perdu des arrêtés » en place).
- **PEB — plans d'exposition au bruit (DGAC via annexes GPU)** — SOURCES-2 lot 2 : les DEUX PEB servis — Roland-Garros (annexes GPU) ET Pierrefonds (4 zones A/B/C/D en VECTEUR, DGAC/STAC via GetFeatureInfo dgac_peb_plan_wmsv Géoplateforme ; arrêté 29/03/2017, maj STAC 12/04/2022 ; zonage complet exigé à l'ingestion sinon échec franc). Le trou du sud est comblé — le géoréférencement du plan PDF était inutile.
- **ZPPA — zones de présomption de prescription archéologique (Atlas des patrimoines)** — Atlas des patrimoines injoignable au 06/09/2026 — aucune donnée. Sentinelle de rappel 180 j posée. Pas d'accès officiel stable constaté.
- **Ravines — domaine public fluvial (DEAL Carmen)** — Ravines DPF (arrêté 2006, 275 tronçons + 6 plans). Couche dpf. Le DPE (privé État) non diffusé.
- **Zones humides — inventaires DEAL (Carmen)** — Inventaires DEAL 2003/2009/2011/2019 par secteurs — partiels par construction (le producteur n'a pas inventorié toute l'île). 3 122 objets. SOURCES-2 lot 1 : migrées du WFS Carmen au WFS LIZMAP de la DEAL (GeoJSON natif, mêmes comptes vérifiés).
- **Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)** — Espaces protégés complémentaires (Ramsar 1, sites classés/inscrits 7, RN 3). Complète le kind ens INPN.
- **AZI / TRI — inondation (Géorisques GASPAR)** — AZI/TRI inondation par commune (GASPAR). Fiche commune risques.
- **Géorisques — secteurs d'information sur les sols (SIS)** — Définitifs : Ouest seul arrêté (réalité producteur, canal SSP). SOURCES-2 lot 2 : + les 7 PROJETS Nord-Est/Sud du dossier préfecture (arrêtés 19/02/2026, consultation close 07/05/2026) servis sol_pollue/sis_projet « non opposable » (6 points posés, 1 CRS de PDF non identifié — dit) ; sentinelle octets sur le ZIP préfecture.
- **Géorisques — CASIAS (anciens sites industriels)** — 453 anciens sites industriels servis (couche sol_pollue). Couverture conforme au producteur.
- **DEAL — cartes de bruit stratégiques (CBS)** — Cartes de bruit stratégiques CBS 2022 — 6 zones de dépassement seulement (échéance 4, RN/RD/VC). Partiel par construction.
- **ENS du Département (Conseil départemental)** — ENS du Département — non diffusés en open data. À demander au Conseil départemental (droit de préemption ENS).
- **Systèmes d'endiguement et zones protégées (DEAL Lizmap)** — NOUVELLE (SOURCES-2 lot 3) : le risque inondation RÉSIDUEL derrière les digues — couche carte complète (aplat zones + trait digues, popup classe/niveau/population), statut « inondation résiduelle au-delà du niveau de protection » TOUJOURS porté. Licence Lizmap : courrier DEAL (lot 5).
- **Carte hypsométrique du littoral (DEAL Lizmap)** — SOURCES-2 lot 3 : la carte EXISTE (projet Lizmap 04tsunami) mais le producteur ne la sert qu'en WMS IMAGE — la couche des courbes de niveau est REFUSÉE en WFS (vérifié 13/09/2026). Vecteur demandé à la DEAL (courrier lot 5). La donnée de submersion est servie À LA PLACE par l'aléa PPRL vecteur (georisque_alea/submersion_marine + cc, 100 zones).

## Marché, logement, permis

| | Source | Verdict | Fiche remplie (4 témoins) | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **DVF / valeurs foncières** (`5`) | PLEINE | 3/4 témoins | oui | KO | 23 | fiche, carte, outil, PDF, copilote, scoring |
| 🟢 | **SITADEL (autorisations d'urbanisme)** (`16`) | PLEINE | 3/4 témoins | oui | KO | 13 | fiche, outil, PDF, copilote, scoring |
| 🟢 | **Inventaire SRU (DHUP)** (`39`) | PLEINE | 4/4 témoins | non | — | 2 | fiche, outil, copilote |
| 🟡 | **NPNRU (DEAL Réunion / ANCT)** (`40`) | PARTIELLE — champs manquants | 3/4 témoins | non | — | 2 | fiche, carte |
| 🟢 | **INSEE RP Logement 2023** (`41`) | PLEINE | 4/4 témoins | non | — | 3 | fiche |
| 🟡 | **PLH des 5 EPCI (extraction documentaire)** (`42`) | PARTIELLE — champs manquants | n.a. (API/règles) | non | — | 1 | fiche |
| 🟣 | **Radar (pige d'annonces)** (`84`) | MANUELLE | VIDE sur 4/4 | oui | — | 9 | fiche, outil |
| 🟢 | **RNIC — registre national des copropriétés (Anah)** (`100`) | PLEINE | VIDE sur 4/4 | non | — | 1 | fiche |
| 🟢 | **RPLS — répertoire des logements locatifs sociaux (SDES)** (`101`) | PLEINE | 4/4 témoins | non | — | 1 | fiche |
| 🟢 | **Zonage ABC des communes (DHUP)** (`109`) | PLEINE | 4/4 témoins | oui | OK | 1 | fiche |
| 🔗 | **DVF Réunion (Région, data.regionreunion.com)** (`119`) | ALIAS (doublon) | n.a. (API/règles) | non | KO | 0 | — |
| 🟢 | **Loyers OLL — ADIL Réunion / AGORAH (réseau des observatoires)** (`129`) | PLEINE | 4/4 témoins | oui | OK | 1 | fiche |
| 🟡 | **Loyers DHUP — carte des loyers (annonces)** (`130`) | PARTIELLE — champs manquants | n.a. (API/règles) | oui | OK | 1 | fiche |
| ⬜ | **OPAH / PIG (Anah / EPCI)** (`137`) | À DEMANDER / À BRANCHER | n.a. (API/règles) | non | — | 0 | — |
| ⬜ | **Périmètres ORT infra-communaux (EPCI)** (`138`) | À DEMANDER / À BRANCHER | n.a. (API/règles) | non | — | 0 | — |
| ⬜ | **Micro-données OLL (ADIL / AGORAH)** (`140`) | À DEMANDER / À BRANCHER | n.a. (API/règles) | non | — | 0 | — |
| 🟣 | **LOVAC (logements vacants)** (`141`) | MANUELLE | n.a. (API/règles) | non | — | 0 | — |
| 🟣 | **DV3F (Cerema)** (`142`) | MANUELLE | n.a. (API/règles) | non | — | 0 | — |

- **DVF / valeurs foncières** — DVF canonique (Etalab + archives DGFiP), cœur du marché. Contrainte L.112 A LPF (pas de réidentification) respectée. Face à id 119 (DVF Région), c'est la source de référence. Voir S3.
- **SITADEL (autorisations d'urbanisme)** — 50 545 permis, cron mensuel. Sert marché, délais d'instruction, dynamique commune. À plein usage.
- **Inventaire SRU (DHUP)** — Inventaire SRU (LLS) par commune. Sert le contexte logement social. 24/24.
- **NPNRU (DEAL Réunion / ANCT)** — NPNRU quartiers (couche anru). Licence État LOv2 2022 — millésime à re-sonder.
- **INSEE RP Logement 2023** — INSEE RP Logement 2023 par commune. Contexte logement.
- **PLH des 5 EPCI (extraction documentaire)** — PLH des 5 EPCI par extraction documentaire (dépôt manuel, 07/07/2026). Chaque chiffre porte sa référence. Fraîcheur dépend d'un geste humain.
- **Radar (pige d'annonces)** — Pige d'annonces = collecte HUMAINE (dépôt manuel de pages HTML). Le client voit le Radar. Voir Lot 3 : dernière alimentation et procédure.
- **RNIC — registre national des copropriétés (Anah)** — RNIC copropriétés (2 220 copros). Sert le signal copropriété. Millésime annuel Anah.
- **RPLS — répertoire des logements locatifs sociaux (SDES)** — RPLS logements sociaux (01/01/2025). Sert SRU/contexte social par commune.
- **Zonage ABC des communes (DHUP)** — Zonage ABC 24/24 (arrêté 23/06/2026 : 4 A, 20 B1). Sert défiscalisation/éligibilités.
- **DVF Réunion (Région, data.regionreunion.com)** — SOURCES-3 lot 0.4 (arbitrage Vic) : DVF / valeurs foncières (Etalab, id 5) fait foi. DVF Réunion (Région) devient son ALIAS (alias_de=5). Le témoin de filtre qui lisait le jeu Région (figé 2014→mi-2021) pointe désormais sur Etalab. `region_dvf` = réservoir sans table.
- **Loyers OLL — ADIL Réunion / AGORAH (réseau des observatoires)** — Loyers OLL 2024 (6 zones + agglo), servis par zone/IRIS. Granularité zone respectée.
- **Loyers DHUP — carte des loyers (annonces)** — Carte des loyers DHUP 2025, extrait 974 embarqué (offline, dépôt manuel). Repli de l'OLL. Fraîcheur à surveiller. SOURCES-2 lot 6 : couverture 974 CONFIRMÉE chez le producteur — le CSV national 2025 (publié 11/12/2025) porte les 24 communes (loypredm2 vérifié ligne à ligne).
- **OPAH / PIG (Anah / EPCI)** — OPAH/PIG — pas de périmètre polygone ouvert. À demander (Anah/EPCI).
- **Périmètres ORT infra-communaux (EPCI)** — Périmètres ORT infra-communaux — à demander aux EPCI. L'éligibilité communale est déjà servie (id 128).
- **Micro-données OLL (ADIL / AGORAH)** — Micro-données OLL — accès conventionné (ADIL/AGORAH). Agrégats par zone déjà servis (id 129). À conventionner pour le détail.
- **LOVAC (logements vacants)** — LOVAC — détail RÉSERVÉ aux collectivités/État/Anah (fiche 19). Non ingéré. En attendant : vacance INSEE RP par IRIS. Voir Lot 3 : sur quelle base on la lirait (une collectivité mandante requise).
- **DV3F (Cerema)** — DV3F Cerema — même convention que les Fichiers fonciers. Non ingéré. En attendant : DVF + échantillon Région. Voir Lot 3.

## Énergie, réseaux, assainissement

| | Source | Verdict | Fiche remplie (4 témoins) | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟣 | **VRD / assainissement (SPANC)** (`26`) | MANUELLE | n.a. (API/règles) | oui | — | 0 | — |
| 🔴 | **DPE ADEME (logements existants)** (`37`) | BRANCHÉE INVISIBLE (vide) | VIDE sur 4/4 | oui | KO | 1 | fiche |
| 🟢 | **PVGIS (Commission européenne)** (`48`) | PLEINE | 4/4 témoins | non | OK | 1 | fiche, outil, scoring |
| ⚫ | **EDF SEI Réunion — open data** (`49`) | RETIRÉE (déjà) | n.a. (API/règles) | non | KO | 0 | — |
| ⚫ | **Registre national des installations (ODRÉ)** (`50`) | RETIRÉE (déjà) | n.a. (API/règles) | non | — | 0 | — |
| 🟢 | **Parkings OSM (loi APER)** (`51`) | PLEINE | n.a. (API/règles) | non | — | 1 | fiche |
| 🟢 | **INSEE RP2022 — fichier détail Logements (EGOUL)** (`66`) | PLEINE | 4/4 témoins | oui | OK | 1 | fiche |
| 🔗 | **GPU — zonages d'assainissement (info-surf typeinf 19)** (`67`) | ALIAS (doublon) | n.a. (API/règles) | non | — | 0 | — |
| ⚫ | **Office de l'eau Réunion — Chroniques de l'eau** (`68`) | RETIRÉE | 1/4 témoins | oui | — | 1 | fiche |
| 🟢 | **Fibre Arcep — Ma connexion internet (immeuble)** (`126`) | PLEINE | 4/4 témoins | oui | KO | 1 | fiche |
| ⬜ | **Zonages d'assainissement SIG complets (EPCI / régies)** (`134`) | À DEMANDER / À BRANCHER | n.a. (API/règles) | non | — | 0 | — |

- **VRD / assainissement (SPANC)** — VRD/SPANC — saisie EPCI manuelle, aucune table dédiée. Collectif/non-collectif saisi. Licence « à confirmer ». Voir Lot 3.
- **DPE ADEME (logements existants)** — SOURCES-2 lot 0 : les TROIS jeux ADEME moissonnés au CP brut (existants + neufs + tertiaire) = 93 lignes dont 16 RÉUNIONNAISES corroborées (75 « neufs ST LEU » = Saint-Leu-la-Forêt 95 — homonymie ; 2 = Montpellier/Lille). 16/16 rattachées parcelle, 8 avec ID-RNB, miroir producteur. Le vide est un TROU PRODUCTEUR (les DPE DROM ne remontent pas à l'observatoire — corollaire : DPEENERGIE vide sur les 87 553 logements RPLS 974) — pas un trou de filtre : il n'existe AUCUN champ INSEE brut au schéma, le filtre INSEE du rapport producteurs ne répare rien.
- **PVGIS (Commission européenne)** — API de calcul solaire (CC BY 4.0). Alimente productible. À plein usage ; attention libellé inclinaison (dette VERIF-1).
- **EDF SEI Réunion — open data** — EDF SEI open data — amont 410 Gone (jeu retiré par EDF ~2026). Retirée 06/09/2026. Rien à sonder. Le réseau HTA vit via id 93.
- **Registre national des installations (ODRÉ)** — Registre national installations (ODRÉ) — jamais branché, aucun usage. Retirée 06/09/2026.
- **Parkings OSM (loi APER)** — Alimente 1 chiffre(s) du registre ; visible dans : 1 section(s) de fiche. *(raison auto — champs producteur non vérifiés, cf. mandat)*
- **INSEE RP2022 — fichier détail Logements (EGOUL)** — RP2022 fichier Logements (EGOUL) → maille ANC. Sert le taux d'assainissement collectif/non collectif.
- **GPU — zonages d'assainissement (info-surf typeinf 19)** — GPU zonages assainissement (info-surf) = canal info-surf du même réservoir que id 63 (alias_de=63). Alias correct.
- **Office de l'eau Réunion — Chroniques de l'eau** — SOURCES-3 lot 0.2 (arbitrage Vic) : RETIRÉE le 2026-09-13. `anc_service.py` a été rebranché sur l'INSEE RP2022 EGOUL (variable mode d'assainissement, taux non-raccordé, anc_maille_taux) : la branche source_commune (Office de l'eau) est supprimée. Prouvé sur les 12 témoins — l'assainissement non collectif s'affiche identique ou mieux (Salazie : « intégralement ANC » → « 100 % non raccordés (INSEE RP2022, IRIS) », sourcé et daté ; les 11 autres inchangés). La table anc_office_eau_commune est conservée (données non effacées), plus aucun lecteur.
- **Fibre Arcep — Ma connexion internet (immeuble)** — Fibre Arcep 330 051 immeubles (2026_T1). Sert l'éligibilité fibre à l'immeuble.
- **Zonages d'assainissement SIG complets (EPCI / régies)** — Zonages d'assainissement SIG complets — 4/24 via GPU aujourd'hui ; les 20 autres à demander aux 5 EPCI/régies (DEMANDE-REGION-EPCI). Voir Lot 2.

## Économie, équipements, accès

| | Source | Verdict | Fiche remplie (4 témoins) | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **Base Adresse Nationale** (`18`) | PLEINE | 4/4 témoins | oui | OK | 1 | fiche |
| 🟢 | **BPE INSEE** (`20`) | PLEINE | 3/4 témoins | oui | OK | 2 | fiche, carte |
| 🟢 | **SIRENE** (`21`) | PLEINE | n.a. (API/règles) | oui | — | 0 | — |
| 🟢 | **BODACC (procédures collectives)** (`29`) | PLEINE | n.a. (API/règles) | oui | OK | 1 | fiche, scoring |
| 🟡 | **INPI RNE (dirigeants)** (`31`) | PARTIELLE — champs manquants | n.a. (API/règles) | non | OK | 1 | outil |
| 🟢 | **Recherche d'entreprises (DINUM)** (`45`) | PLEINE | n.a. (API/règles) | non | — | 1 | fiche, scoring |
| 🟢 | **Filosofi INSEE (carreaux 200 m)** (`52`) | PLEINE | 4/4 témoins | oui | OK | 5 | fiche, outil, PDF, scoring |
| 🟢 | **Contours IRIS (IGN/INSEE)** (`64`) | PLEINE | 3/4 témoins | oui | — | 1 | fiche, carte, outil |
| 🟢 | **Transport public — GTFS (PAN, 7 réseaux)** (`74`) | PLEINE | VIDE sur 4/4 | oui | OK | 4 | fiche, carte |
| 🟢 | **OSM — transport (pôles d'échange & téléphérique)** (`75`) | PLEINE | VIDE sur 4/4 | non | OK | 4 | fiche, carte |
| 🟢 | **SIRENE établissements géolocalisés** (`86`) | PLEINE | 4/4 témoins | oui | KO | 3 | fiche, outil, scoring |
| ⚫ | **MOBPRO (mobilités domicile-travail, INSEE)** (`87`) | RETIRÉE (déjà) | VIDE sur 4/4 | non | — | 0 | — |
| 🟢 | **Trafic RN (Région Réunion — SIR)** (`88`) | PLEINE | n.a. (API/règles) | oui | KO | 1 | outil |
| 🟢 | **EDF Réunion — lignes moyenne tension HTA (open data)** (`93`) | PLEINE | VIDE sur 4/4 | oui | KO | 0 | carte |
| 🟢 | **TCSP — voies bus en site propre (OSM)** (`94`) | PLEINE | VIDE sur 4/4 | non | — | 0 | carte |
| ⬜ | **Réunion Express — hypothèses de tracé (débat public CNDP)** (`95`) | À DEMANDER / À BRANCHER | n.a. (API/règles) | oui | — | 0 | — |
| 🟢 | **Annuaire de l'administration (service-public.fr / DILA)** (`99`) | PLEINE | 4/4 témoins | non | — | 1 | fiche |
| 🟢 | **INSEE RP2022 — bases IRIS (logement, population)** (`133`) | PLEINE | 4/4 témoins | oui | — | 2 | fiche, outil |
| ⬜ | **Inventaires ZAE (EPCI — loi Climat et résilience)** (`135`) | À DEMANDER / À BRANCHER | n.a. (API/règles) | non | — | 0 | — |

- **Base Adresse Nationale** — BAN — géocodage d'adresses (job sur clic). Socle adresses↔parcelles.
- **BPE INSEE** — BPE INSEE 2025 (équipements, 35 546 objets couche). Sert l'attractivité (commerces, écoles…).
- **SIRENE** — Servie via l'API recherche-entreprises EN DIRECT (Scan patrimoine, Copilote entreprise) — d'où 0 chiffre de registre attaché à `sirene_recherche_entreprises` (API à la requête, sans table). Ce n'est PAS invisible : le pro l'atteint par le Scan/Copilote. Le canal géolocalisé (id 86) est la variante à réservoir. Voir S3.
- **BODACC (procédures collectives)** — BODACC procédures collectives (job sur clic). Signal entreprise/propriétaire.
- **INPI RNE (dirigeants)** — INPI RNE dirigeants. Licence SPÉCIFIQUE homologuée (pas Licence Ouverte) — usage encadré, à respecter.
- **Recherche d'entreprises (DINUM)** — SOURCES-3 lot 0.1 (arbitrage Vic) : RETRAIT DIFFÉRÉ — reste servie jusqu'au prochain entraînement du modèle (sort avec q_v15). DINUM n'alimente PLUS que le Score V (owner_enrichment/owner_denom_lookup, `score_v.py:90,98`). Débranchée de l'affichage, de la facette et du scan : SIRENE fait foi pour tout affichage — l'APE des filtres/facette propriétaire vient de `sirene_etablissements.naf` (format pointé), l'état « cessée » est retiré (SIRENE n'ingère que les actifs, l'état administratif d'une unité légale n'y est pas lisible ; radiée/procédure BODACC restent). Verdict PLEINE, plus PARTIELLE.
- **Filosofi INSEE (carreaux 200 m)** — Filosofi 2021 (carreaux 200 m). Sert le revenu/population de zone. Millésime 2021 (le plus récent publié).
- **Contours IRIS (IGN/INSEE)** — Contours IRIS 2024. Socle géographique infra-communal (rattachements).
- **Transport public — GTFS (PAN, 7 réseaux)** — GTFS 7 réseaux (PAN, maj 2026). Arrêts/lignes de transport en couche. SOURCES-2 lot 1 : les 7 réseaux VÉRIFIÉS un par un au PAN (13/09/2026), tous valides ≥ 31/12/2026 ; GTFS-RT disponible sur 3 réseaux (Car Jaune, Alternéo, Carsud) — documenté NON ingéré (donnée d'exploitation éphémère, arbitrage).
- **OSM — transport (pôles d'échange & téléphérique)** — OSM transport (pôles d'échange, téléphérique). Couche.
- **SIRENE établissements géolocalisés** — SIRENE géolocalisé (cron mensuel), variante à réservoir de la SIRENE API (id 21). Sert l'étude de zone (concurrents). Les deux coexistent par usage distinct (direct vs snapshot géo) — voir S3.
- **MOBPRO (mobilités domicile-travail, INSEE)** — MOBPRO — abandonnée par ZONE-DONNÉES ; lecteur zone.emplois_communes sans appelant (code mort). Retirée 06/09/2026. Précédent-clé : retirée car PLUS RIEN DE SERVI.
- **Trafic RN (Région Réunion — SIR)** — Trafic RN Région (comptages par tronçon). Sert l'accessibilité/attractivité de zone.
- **EDF Réunion — lignes moyenne tension HTA (open data)** — Lignes HTA EDF (19 480 objets, publié 16/10/2025). Couche réseau. Géométrie ~02/2020 (ancienne, mais publiée telle quelle par EDF).
- **TCSP — voies bus en site propre (OSM)** — TCSP voies bus en site propre (OSM). Couche + valorisation L151-36.
- **Réunion Express — hypothèses de tracé (débat public CNDP)** — Réunion Express — hypothèses de tracé au débat public CNDP. Rien d'ingéré (ce ne sont pas des données arrêtées). À surveiller, pas à brancher.
- **Annuaire de l'administration (service-public.fr / DILA)** — Annuaire service-public (24 mairies, cron mensuel). Sert le bloc Mairie & urbanisme.
- **INSEE RP2022 — bases IRIS (logement, population)** — RP2022 bases IRIS (logement/population), géographie 2024. Sert fiche commune quartiers.
- **Inventaires ZAE (EPCI — loi Climat et résilience)** — Inventaires ZAE (L.318-8-2 CU) — à demander aux 5 EPCI. Demande prête (DEMANDE-REGION-EPCI).

## Terrain, sol, imagerie

| | Source | Verdict | Fiche remplie (4 témoins) | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **RGE ALTI (altimétrie)** (`6`) | PLEINE | 3/4 témoins | oui | — | 3 | fiche, carte, PDF |
| 🟢 | **BD TOPO IGN** (`17`) | PLEINE | 3/4 témoins | oui | — | 18 | fiche, carte, outil, PDF, scoring |
| 🟡 | **IGN BD CARTO V5 — occupation du sol** (`22`) | PARTIELLE — champs manquants | 3/4 témoins | oui | — | 0 | carte |
| 🟢 | **BD ORTHO 20 cm (IGN)** (`61`) | PLEINE | 1/4 témoins | oui | OK | 3 | fiche, outil, copilote |
| 🔗 | **RGE ALTI 5 m (IGN)** (`65`) | ALIAS (doublon) | n.a. (API/règles) | non | — | 0 | — |
| 🟢 | **BD ORTHO IRC (IGN)** (`69`) | PLEINE | 4/4 témoins | oui | KO | 1 | fiche, outil, scoring |
| 🟡 | **LiDAR HD — MNH 50 cm (IGN)** (`70`) | PARTIELLE — couverture incomplète | 4/4 témoins | oui | OK | 4 | fiche, outil, scoring |
| 🟢 | **CoSIA (couverture du sol IA, IGN)** (`83`) | PLEINE | 4/4 témoins | oui | OK | 13 | fiche, carte, outil, PDF, scoring |
| 🟢 | **Cadastre d'époque (Etalab / PCI vecteur DGFiP)** (`96`) | PLEINE | VIDE sur 4/4 | non | — | 1 | fiche |
| 🟢 | **RNB — Référentiel National des Bâtiments** (`143`) | PLEINE | 4/4 témoins | oui | — | 1 | fiche |
| 🟢 | **OCS GE (IGN) — occupation du sol et artificialisation** (`144`) | PLEINE | 4/4 témoins | oui | — | 3 | fiche, carte |

- **RGE ALTI (altimétrie)** — RGE ALTI — pente 5 m (147 398 objets). Socle topographique (pente, viabilisation).
- **BD TOPO IGN** — 1,07 M d'objets (bâti, voirie, eau, ravine). Socle géométrique lu par potentiel/solaire/viabilisation. À plein usage sur les thèmes ingérés.
- **IGN BD CARTO V5 — occupation du sol** — BD CARTO V5 occupation du sol (proxy OCS, 1 643 objets). Proxy grossier — l'OCS GE officielle est une candidate (lot 5).
- **BD ORTHO 20 cm (IGN)** — BD ORTHO 20 cm 2025. Détection piscines (90,7 %), fond ortho. À plein usage.
- **RGE ALTI 5 m (IGN)** — RGE ALTI 5 m = même réservoir que id 6 (alias_de=6). Alias correct.
- **BD ORTHO IRC (IGN)** — SOURCES-3 lot 0.3 (arbitrage Vic) : CONSERVÉE — la décision de retrait est ANNULÉE. L'infrarouge IRC alimente l'ombrage végétal du solaire et du scoring : `parcel_vegetation` (431 663 lignes) est lu par le solaire (`solaire.py:311` ombrage), le Flash (`flash/data.py:650`) et le scoring P (`p_model/sql.py:287`). Chiffre `prod_spec_kwh_kwc`, fiche Solaire. Verdict PLEINE, note de couverture retirée.
- **LiDAR HD — MNH 50 cm (IGN)** — Couverture PRODUCTEUR complète (2 665 dalles 974, mission unique 23LHDREUNION — survol 11/08–11/10/2023, édition MNx 13/03/2025, levés SOURCES-2 lot 1, affichés au registre). Le reste-à-faire est LOCAL : la hauteur mesurée couvre ~70 % des parcelles (batch achevé ; solde = parcelles sans bâti rattachable).
- **CoSIA (couverture du sol IA, IGN)** — 445 190 bâtis IA (2025), cœur du potentiel/scoring. Bâti à plein usage ; autres classes CoSIA non exploitées (par choix).
- **Cadastre d'époque (Etalab / PCI vecteur DGFiP)** — Cadastre d'époque (archives PCI 2017→2026). Sert le rattachement des permis anciens (RETOURS-14).
- **RNB — Référentiel National des Bâtiments** — Alimente 1 chiffre(s) du registre via bati_revele ; visible dans : 1 section(s) de fiche. *(raison auto — champs producteur non vérifiés, cf. mandat)*
- **OCS GE (IGN) — occupation du sol et artificialisation** — Alimente 3 chiffre(s) du registre via bati_revele, commune_compteurs ; visible dans : 2 section(s) de fiche, 1 couche(s) carte. *(raison auto — champs producteur non vérifiés, cf. mandat)*

## Hubs et catalogues

| | Source | Verdict | Fiche remplie (4 témoins) | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🏛 | **Région Réunion Open Data (Opendatasoft)** (`11`) | HUB (catalogue) | n.a. (API/règles) | oui | — | 0 | — |
| 🏛 | **PEIGEO (hub régional)** (`12`) | HUB (catalogue) | n.a. (API/règles) | non | — | 0 | — |
| 🏛 | **Géoplateforme IGN** (`14`) | HUB (catalogue) | n.a. (API/règles) | non | — | 0 | — |

- **Région Réunion Open Data (Opendatasoft)** — Portail Région ODS — hub de catalogue, jamais un réservoir. Licence par jeu à confirmer.
- **PEIGEO (hub régional)** — PEIGEO/AGORAH — hub régional, jamais un réservoir.
- **Géoplateforme IGN** — Géoplateforme IGN — hub, jamais un réservoir. Point d'accès de nombreuses sources IGN.

## Autres

| | Source | Verdict | Fiche remplie (4 témoins) | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **Taxe d'aménagement — taux communaux (délibérations)** (`98`) | PLEINE | 4/4 témoins | non | OK | 2 | fiche, outil |
| 🟢 | **Taux de taxe foncière — fichier REI (DGFiP)** (`127`) | PLEINE | 4/4 témoins | oui | OK | 1 | fiche |
| 🟡 | **ACV / PVD / ORT (DGALN — liste des communes)** (`128`) | PARTIELLE — couverture incomplète | 3/4 témoins | oui | KO | 1 | fiche |
| 🟢 | **Coût de construction (EPTB SDES + choix LABUSE)** (`131`) | PLEINE | n.a. (API/règles) | oui | OK | 1 | outil |

- **Taxe d'aménagement — taux communaux (délibérations)** — SOURCES-3 lot 1 : RATTACHÉE au registre — les chiffres `taxe_amenagement_eur` et `taxe_amenagement_estimee_eur` (outil Taxe + Financier) déclarent `reservoirs=(taxe_amenagement,)`, table `taxe_amenagement_taux` : le taux communal servi porte sa provenance (arête CIRCUIT-6 lot 0, confirmée ici).
- **Taux de taxe foncière — fichier REI (DGFiP)** — Taux taxe foncière REI 2025, 24/24. Sert l'estimation fiscale (fiche commune fiscalité).
- **ACV / PVD / ORT (DGALN — liste des communes)** — Table DGALN vivante, 19 communes. C'est l'éligibilité COMMUNALE ; le périmètre ORT infra-communal (Denormandie) est une source à part (id 138, à demander).
- **Coût de construction (EPTB SDES + choix LABUSE)** — Coût de construction (EPTB 2024 + choix LABUSE 2300-2800 €/m²). Sert le bilan promoteur. Le « choix LABUSE » est délibéré et sourcé.
