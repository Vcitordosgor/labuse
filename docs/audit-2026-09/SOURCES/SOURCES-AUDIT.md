# SOURCES-AUDIT — les 116 sources par famille

> Généré par `scripts/audit_sources` (lecture seule, rejouable). Verdict en tête de ligne. Détail : `fiches/<id>.md`. Données : `SOURCES-AUDIT.csv`.

**Légende** : 🟢 PLEINE · 🟡 PARTIELLE · 🔵 BRANCHÉE INVISIBLE · 🟠 SERVIE HORS REGISTRE · ⚫ RETIRÉE/PÉRIMÉE · 🔴 À RETIRER · ⬜ À DEMANDER/BRANCHER · 🟣 MANUELLE · 🔗 ALIAS · 🏛 HUB

## Compte des verdicts

| Verdict | Nombre |
|---|---|
| PLEINE | 62 |
| PARTIELLE — champs manquants | 10 |
| PARTIELLE — couverture incomplète | 14 |
| SERVIE HORS REGISTRE | 4 |
| À DEMANDER / À BRANCHER | 10 |
| MANUELLE | 5 |
| RETIRÉE (déjà) | 5 |
| ALIAS (doublon) | 3 |
| HUB (catalogue) | 3 |
| **Total** | **116** |

## Parcelles et propriété

| | Source | Verdict | Millésime base | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **Cadastre (API Carto PCI)** (`1`) | PLEINE | PCI Parcellaire Express (DGFiP) — « latest » ingérée | oui | — | 18 | fiche, outil, PDF, copilote, scoring |
| 🔗 | **Cadastre Etalab (bulk DGFiP/Etalab)** (`2`) | ALIAS (doublon) | Etalab cadastre — « latest » ingérée (DGFiP) | oui | KO | 0 | — |
| 🟡 | **data.regionreunion.com — Potentiel foncier** (`15`) | PARTIELLE — couverture incomplète | — | oui | — | 0 | carte |
| 🟣 | **Fichiers fonciers (Cerema)** (`27`) | MANUELLE | convention non instruite (FF 2024 au portail Cerema) | oui | — | 0 | — |
| 🟢 | **Cartofriches (Cerema)** (`35`) | PLEINE | — | oui | OK | 0 | carte |
| 🟢 | **DGFiP — parcelles des personnes morales** (`71`) | PLEINE | Panel millésimes 2019→2025 (situation 1ᵉʳ janvier) | oui | OK | 4 | fiche, outil, copilote |
| ⚫ | **BDNB** (`89`) | RETIRÉE (déjà) | 2026-02-a (métropole seule — 974 absent) | oui | — | 0 | — |
| 🟢 | **DFI — documents de filiation informatisés (DGFiP)** (`132`) | PLEINE | situation 19/06/2026 — 409 623 liens 974 (1989→2025) | oui | OK | 1 | fiche |

- **Cadastre (API Carto PCI)** — Socle parcellaire complet (431 663 parcelles, 24/24), lu par la quasi-totalité des moteurs. À plein potentiel.
- **Cadastre Etalab (bulk DGFiP/Etalab)** — Canal bulk du MÊME réservoir que Cadastre API Carto (id 1). Alias correctement déclaré (alias_de=1). Rien à faire.
- **data.regionreunion.com — Potentiel foncier** — DOUBLON à trancher avec id 9 (même producteur Région ODS, familles `potentiel` vs `urbanisme`). Licence « à confirmer ». 4 906 objets en couche potentiel_foncier+sar. Voir S3.
- **Fichiers fonciers (Cerema)** — Fichiers fonciers Cerema — SOUS CONVENTION, non instruite. Aucune donnée ingérée. En attendant : DVF ouvert. Voir Lot 3 + DEMANDE.
- **Cartofriches (Cerema)** — Cartofriches Cerema (372 friches). Couche + signal foncier.
- **DGFiP — parcelles des personnes morales** — Cœur de Scan patrimoine / propriétaire. 7 millésimes empilés, sert le moteur propriétaire_historique.
- **BDNB** — BDNB — ne couvre pas le 974 (métropole seule, 0 ligne 974 vérifié). Retirée 06/09/2026 ; sentinelle+cron conservés pour un futur millésime 974. NB (lot 5) : LABUSE NE possède PAS BDNB.
- **DFI — documents de filiation informatisés (DGFiP)** — 409 623 liens 974 ingérés (job_sur_clic). Sert la reconstitution de propriété. Coverage insulaire complète.

## Urbanisme et règles

| | Source | Verdict | Millésime base | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **Urbanisme PLU/GPU (API Carto)** (`3`) | PLEINE | GPU/PLU par commune (révisions — détail en fiche) | non | KO | 24 | fiche, carte, outil, PDF, copilote, scoring |
| 🟠 | **Potentiel foncier Région (Région ODS)** (`9`) | SERVIE HORS REGISTRE | îlots non urbanisés — estimation Région (ODS, non versionné) | oui | KO | 0 | carte |
| 🟡 | **DEAL Réunion (WMS/WFS)** (`13`) | PARTIELLE — champs manquants | NPNRU — QP génération 2024 (DEAL/ANCT) | oui | — | 0 | carte |
| 🟢 | **QPV 2024 (ANCT)** (`38`) | PLEINE | génération 2024 | oui | OK | 3 | fiche, carte |
| 🟢 | **RTAA DOM (textes réglementaires)** (`43`) | PLEINE | — | non | — | 0 | — |
| 🟡 | **SUP — assiettes GPU (API Carto)** (`44`) | PARTIELLE — couverture incomplète | — | oui | OK | 2 | fiche, carte |
| 🟢 | **Classement sonore ITT (Cerema)** (`46`) | PLEINE | arrêtés déc. 2023 | oui | OK | 1 | carte |
| 🟢 | **50 pas géométriques — limite haute (DEAL)** (`47`) | PLEINE | cadastre 1877 (géoréf. 2012/1950) | non | OK | 1 | carte |
| 🟡 | **Sudocuh (procédures d'urbanisme)** (`62`) | PARTIELLE — champs manquants | Sudocuh — état au 31/12/2024 (Licence Ouverte 2.0) | non | — | 6 | fiche, outil, copilote |
| 🟡 | **GPU — zonages d'assainissement** (`63`) | PARTIELLE — couverture incomplète | GPU — idurba par commune ; SIG 4/24 au 11/07/2026 | non | OK | 0 | carte |
| 🟢 | **ZFANG — zone franche d'activité nouvelle génération (Légifrance)** (`72`) | PLEINE | Décret n° 2026-421 du 29 mai 2026 (LF 2026, art. 18) | non | OK | 2 | fiche, carte |
| 🟢 | **FRR ex-ZRR — zone spéciale d'action rurale (Légifrance)** (`73`) | PLEINE | ZSAR 1978 · FRR 01/07/2024 · réf. ZRR 2017 (Région) | non | OK | 2 | fiche, carte |
| 🟢 | **Consommation d'espaces NAF (Cerema — portail de l'artificialisation)** (`102`) | PLEINE | conso ENAF 2021-2024 (portail artificialisation, Cerema) | non | — | 2 | fiche, outil |
| 🟢 | **GPU — emplacements réservés (prescriptions CNIG)** (`105`) | PLEINE | GPU — prescriptions typepsc 05 (idurba par commune) | non | KO | 3 | fiche, carte |
| 🟢 | **GPU — espaces boisés classés (prescriptions CNIG)** (`106`) | PLEINE | GPU — prescriptions typepsc 01 (idurba par commune) | non | KO | 3 | fiche, carte |
| 🟡 | **GPU — droit de préemption urbain (info-surf)** (`107`) | PARTIELLE — couverture incomplète | GPU typeinf 04 — partiel, non-publiées listées | non | KO | 3 | fiche, carte |
| ⬜ | **SAR — schéma d'aménagement régional (Région/DEAL)** (`118`) | À DEMANDER / À BRANCHER | couche SIG officielle NON diffusée (recherche 07/09/2026) | oui | — | 1 | fiche, carte, scoring |
| ⬜ | **Périmètres de ZAC (EPCI / communes / EPF Réunion)** (`136`) | À DEMANDER / À BRANCHER | en attente de la demande (pas d'open data 974 fiable) | non | — | 0 | — |

- **Urbanisme PLU/GPU (API Carto)** — Zonage + prescriptions servis sur toute l'île, cœur de la faisabilité et du scoring. Interrogé en direct (GPU).
- **Potentiel foncier Région (Région ODS)** — DOUBLON de id 15 (même jeu Région ODS « potentiel foncier »), rangé en famille `urbanisme`. Aucun slug réservoir distinct servi. À fusionner avec 15 — voir S3.
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
- **GPU — droit de préemption urbain (info-surf)** — GPU typeinf 04 — seulement 4/24 communes ont publié leur DPU au GPU (06/09/2026). Là où c'est absent, ne pas affirmer « pas de DPU ». Les non-publiées sont listées.
- **SAR — schéma d'aménagement régional (Région/DEAL)** — SAR — couche SIG officielle NON diffusée par la Région (recherche 07/09/2026). Un proxy vocations existe (sar_region). À demander à la Région (lot 7). Non opposable directement.
- **Périmètres de ZAC (EPCI / communes / EPF Réunion)** — Périmètres de ZAC — pas d'open data 974 fiable. À demander (EPCI/communes/EPF). Standard CNIG ZAC.

## Risques, nature, patrimoine

| | Source | Verdict | Millésime base | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **Géorisques** (`4`) | PLEINE | — | oui | KO | 2 | fiche, carte, outil, scoring |
| 🟡 | **Parc National de La Réunion (INPN)** (`7`) | PARTIELLE — champs manquants | millésime 2021 | oui | — | 1 | carte |
| 🟢 | **Forêts publiques (ONF)** (`8`) | PLEINE | BD TOPO® V3 — forêt publique (IGN) | oui | — | 0 | carte |
| 🟡 | **RPG — déclarations agricoles (IGN/ASP)** (`10`) | PARTIELLE — champs manquants | proxy RPG (IGN) — RPG.LATEST, année non pinnée | oui | — | 1 | carte |
| 🟢 | **OpenStreetMap / Overpass** (`19`) | PLEINE | — | non | OK | 2 | fiche, carte |
| 🟢 | **ABF / Monuments historiques** (`24`) | PLEINE | — | oui | OK | 1 | fiche, carte, outil, scoring |
| 🟡 | **INPN / patrinat — espaces protégés** (`25`) | PARTIELLE — champs manquants | INPN/patrinat espaces protégés — passe 05/07/2026 | non | — | 1 | carte |
| 🟢 | **Cerema / GéoLittoral — indicateur d'érosion côtière** (`28`) | PLEINE | millésime 2018 | oui | — | 0 | carte |
| 🟢 | **DEAL Réunion — PPR / aléas** (`30`) | PLEINE | PPR/PPRL approuvés 2011–2026 (arrêtés, DEAL Lizmap) | oui | — | 6 | fiche, carte, outil, scoring |
| 🟢 | **Géorisques — sites et sols pollués** (`32`) | PLEINE | — | oui | OK | 0 | carte |
| 🟢 | **Géorisques — cavités souterraines** (`33`) | PLEINE | — | oui | OK | 0 | carte |
| 🟢 | **Géorisques — ICPE** (`34`) | PLEINE | — | oui | OK | 0 | carte |
| 🟢 | **Géorisques — mouvements de terrain** (`36`) | PLEINE | — | oui | OK | 0 | carte |
| 🟢 | **ZNIEFF (INPN/MNHN)** (`76`) | PLEINE | INPN, mise à jour 29/08/2025 | oui | OK | 2 | fiche, carte, outil, scoring |
| ⚫ | **ZNIEFF (INPN / Région)** (`80`) | RETIRÉE (déjà) | — | non | — | 0 | — |
| 🟠 | **CatNat (arrêtés GASPAR / Géorisques)** (`97`) | SERVIE HORS REGISTRE | GASPAR — arrêtés CatNat 974 (paginés, 06/09/2026) | non | KO | 0 | — |
| 🟡 | **PEB — plans d'exposition au bruit (DGAC via annexes GPU)** (`108`) | PARTIELLE — couverture incomplète | Roland-Garros B/C/D (GPU) ; Pierrefonds non publié | non | KO | 3 | fiche, carte |
| ⬜ | **ZPPA — zones de présomption de prescription archéologique (Atlas des patrimoines)** (`110`) | À DEMANDER / À BRANCHER | aucune donnée — Atlas injoignable (06/09/2026) | oui | — | 0 | — |
| 🟢 | **Ravines — domaine public fluvial (DEAL Carmen)** (`111`) | PLEINE | DPF arrêté 06-3077 du 21/08/2006 — 275 tronçons + 6 plans | non | OK | 1 | carte |
| 🟡 | **Zones humides — inventaires DEAL (Carmen)** (`112`) | PARTIELLE — couverture incomplète | inventaires 2003/2009/2011/2019 par secteurs (partiels) | non | OK | 1 | carte |
| 🟢 | **Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)** (`113`) | PLEINE | Ramsar 1 · sites classés/inscrits 7 · RN 3 (07/09/2026) | non | OK | 1 | carte |
| 🟢 | **AZI / TRI — inondation (Géorisques GASPAR)** (`114`) | PLEINE | GASPAR azi+tri par commune (07/09/2026) | oui | KO | 1 | fiche |
| 🟡 | **Géorisques — secteurs d'information sur les sols (SIS)** (`115`) | PARTIELLE — couverture incomplète | 4 SIS 974 (MultiPolygon) — canal SSP, vu 07/09/2026 | non | KO | 3 | fiche, carte |
| 🟢 | **Géorisques — CASIAS (anciens sites industriels)** (`116`) | PLEINE | 453 sites 974 (435 points, 18 emprises) — canal SSP, 07/09/2026 | non | KO | 3 | fiche, carte |
| 🟡 | **DEAL — cartes de bruit stratégiques (CBS)** (`117`) | PARTIELLE — couverture incomplète | CBS 2022 — 6 zones de dépassement Lden/Ln (RN/RD/VC) | non | OK | 1 | carte |
| ⬜ | **ENS du Département (Conseil départemental)** (`139`) | À DEMANDER / À BRANCHER | en attente de la demande (non diffusés en open data) | non | — | 0 | — |

- **Géorisques** — Aléas Géorisques servis (couche + fiche Pièges + cascade). Complété par 8 sources Géorisques sœurs.
- **Parc National de La Réunion (INPN)** — Parc National servi (3 objets couche). Licence « à confirmer » (jeu pnrun_2021 via Région ODS) — provenance à clarifier.
- **Forêts publiques (ONF)** — Alimente 0 chiffre(s) du registre ; visible dans : 1 couche(s) carte. *(raison auto — champs producteur non vérifiés, cf. mandat)*
- **RPG — déclarations agricoles (IGN/ASP)** — RPG déclarations agricoles servi via un PROXY IGN (RPG.LATEST, année non pinnée) ; le vrai RPG DAAF n'est pas public. Licence « à confirmer ». Code culture servi (canne). Couche « cultures déclarées » + cascade zone A.
- **OpenStreetMap / Overpass** — OSM/Overpass — aménités (21 561 objets). Signal. ODbL (share-alike) respecté.
- **ABF / Monuments historiques** — ABF/Monuments historiques (Mérimée, 200 périmètres). Couche + contrainte patrimoine.
- **INPN / patrinat — espaces protégés** — Espaces protégés INPN servis (couche ens). Licence « à confirmer ».
- **Cerema / GéoLittoral — indicateur d'érosion côtière** — Trait de côte / érosion côtière 2018 (24 168 objets). Couche carte. Millésime ancien (2018) à re-sonder.
- **DEAL Réunion — PPR / aléas** — Alimente 6 chiffre(s) du registre via cascade, commune_compteurs ; visible dans : 2 section(s) de fiche, 2 couche(s) carte, 1 outil(s). *(raison auto — champs producteur non vérifiés, cf. mandat)*
- **Géorisques — sites et sols pollués** — Sites et sols pollués (513 objets). Couche + Pièges.
- **Géorisques — cavités souterraines** — Cavités souterraines (151 objets). Couche + Pièges.
- **Géorisques — ICPE** — ICPE (1 261 objets). Couche + Pièges + cascade.
- **Géorisques — mouvements de terrain** — Mouvements de terrain (3 085 objets). Couche + Pièges + cascade (RETOURS-13).
- **ZNIEFF (INPN/MNHN)** — ZNIEFF servies (162 objets, maj 29/08/2025). Canonique face à id 80 (canal Région, retiré). Voir S3.
- **ZNIEFF (INPN / Région)** — ZNIEFF canal Région — endpoint vivant mais 0 donnée. Retirée 06/09/2026. Canonique : id 76.
- **CatNat (arrêtés GASPAR / Géorisques)** — 426 arrêtés servis (fiche commune / Pièges) MAIS aucun chiffre du registre ne déclare le réservoir `catnat_gaspar` (le chiffre `catnat_n` a `reservoirs={}`). La donnée coule, la provenance n'est pas tracée — trou de registre à combler.
- **PEB — plans d'exposition au bruit (DGAC via annexes GPU)** — PEB Roland-Garros B/C/D via annexes GPU ; PEB de Pierrefonds NON publié. Trou connu au sud.
- **ZPPA — zones de présomption de prescription archéologique (Atlas des patrimoines)** — Atlas des patrimoines injoignable au 06/09/2026 — aucune donnée. Sentinelle de rappel 180 j posée. Pas d'accès officiel stable constaté.
- **Ravines — domaine public fluvial (DEAL Carmen)** — Ravines DPF (arrêté 2006, 275 tronçons + 6 plans). Couche dpf. Le DPE (privé État) non diffusé.
- **Zones humides — inventaires DEAL (Carmen)** — Inventaires DEAL 2003/2009/2011/2019 par secteurs — partiels par construction (le producteur n'a pas inventorié toute l'île). 3 122 objets.
- **Espaces protégés complémentaires — Ramsar, sites classés/inscrits (DEAL Carmen)** — Espaces protégés complémentaires (Ramsar 1, sites classés/inscrits 7, RN 3). Complète le kind ens INPN.
- **AZI / TRI — inondation (Géorisques GASPAR)** — AZI/TRI inondation par commune (GASPAR). Fiche commune risques.
- **Géorisques — secteurs d'information sur les sols (SIS)** — 4 SIS 974 seulement (c'est la réalité du producteur, pas un manque LABUSE). Canal SSP partagé.
- **Géorisques — CASIAS (anciens sites industriels)** — 453 anciens sites industriels servis (couche sol_pollue). Couverture conforme au producteur.
- **DEAL — cartes de bruit stratégiques (CBS)** — Cartes de bruit stratégiques CBS 2022 — 6 zones de dépassement seulement (échéance 4, RN/RD/VC). Partiel par construction.
- **ENS du Département (Conseil départemental)** — ENS du Département — non diffusés en open data. À demander au Conseil départemental (droit de préemption ENS).

## Marché, logement, permis

| | Source | Verdict | Millésime base | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **DVF / valeurs foncières** (`5`) | PLEINE | géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020 | oui | KO | 23 | fiche, carte, outil, PDF, copilote, scoring |
| 🟢 | **SITADEL (autorisations d'urbanisme)** (`16`) | PLEINE | 2026-07 | oui | KO | 13 | fiche, outil, PDF, copilote, scoring |
| 🟢 | **Inventaire SRU (DHUP)** (`39`) | PLEINE | — | non | — | 2 | fiche, outil, copilote |
| 🟡 | **NPNRU (DEAL Réunion / ANCT)** (`40`) | PARTIELLE — champs manquants | — | non | — | 2 | fiche, carte |
| 🟢 | **INSEE RP Logement 2023** (`41`) | PLEINE | — | non | — | 3 | fiche |
| 🟡 | **PLH des 5 EPCI (extraction documentaire)** (`42`) | PARTIELLE — champs manquants | — | non | — | 1 | fiche |
| 🟣 | **Radar (pige d'annonces)** (`84`) | MANUELLE | Collecte manuelle — biens en vente (faits + lien) | oui | — | 9 | fiche, outil |
| 🟢 | **RNIC — registre national des copropriétés (Anah)** (`100`) | PLEINE | RNIC (ANAH) — registre des copropriétés (extraction annuelle) | non | — | 1 | fiche |
| 🟢 | **RPLS — répertoire des logements locatifs sociaux (SDES)** (`101`) | PLEINE | RPLS — millésime 01/01/2025 (SDES) | non | — | 1 | fiche |
| 🟢 | **Zonage ABC des communes (DHUP)** (`109`) | PLEINE | arrêté 23/06/2026 en vigueur 26/06 — 24/24 (4 A, 20 B1) | oui | OK | 1 | fiche |
| 🟠 | **DVF Réunion (Région, data.regionreunion.com)** (`119`) | SERVIE HORS REGISTRE | jeu figé 2014→mi-2021 (54 449 mutations) — contrôle producteur | non | KO | 0 | — |
| 🟢 | **Loyers OLL — ADIL Réunion / AGORAH (réseau des observatoires)** (`129`) | PLEINE | OLL 2024 — Île de La Réunion (L9740, 6 zones + agglo) | oui | OK | 1 | fiche |
| 🟡 | **Loyers DHUP — carte des loyers (annonces)** (`130`) | PARTIELLE — champs manquants | carte des loyers 2025 (extrait 974 versionné, offline) | oui | OK | 1 | fiche |
| ⬜ | **OPAH / PIG (Anah / EPCI)** (`137`) | À DEMANDER / À BRANCHER | en attente de la demande (pas de périmètre polygone ouvert) | non | — | 0 | — |
| ⬜ | **Périmètres ORT infra-communaux (EPCI)** (`138`) | À DEMANDER / À BRANCHER | en attente de la demande (éligibilité communale servie) | non | — | 0 | — |
| ⬜ | **Micro-données OLL (ADIL / AGORAH)** (`140`) | À DEMANDER / À BRANCHER | en attente de la demande (agrégats par zone servis) | non | — | 0 | — |
| 🟣 | **LOVAC (logements vacants)** (`141`) | MANUELLE | convention non instruite (millésime 2025 publié) | non | — | 0 | — |
| 🟣 | **DV3F (Cerema)** (`142`) | MANUELLE | convention non instruite (DV3F 2024-2 disponible) | non | — | 0 | — |

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
- **DVF Réunion (Région, data.regionreunion.com)** — DOUBLON de DVF Etalab (id 5). Jeu Région figé 2014→mi-2021 (54 449 mutations), utilisé UNIQUEMENT comme échantillon du filtre DVF (contrôle producteur), non servi au client. `region_dvf` = réservoir sans table. Voir S3 : garder comme témoin de filtre ou retirer.
- **Loyers OLL — ADIL Réunion / AGORAH (réseau des observatoires)** — Loyers OLL 2024 (6 zones + agglo), servis par zone/IRIS. Granularité zone respectée.
- **Loyers DHUP — carte des loyers (annonces)** — Carte des loyers DHUP 2025, extrait 974 embarqué (offline, dépôt manuel). Repli de l'OLL. Fraîcheur à surveiller.
- **OPAH / PIG (Anah / EPCI)** — OPAH/PIG — pas de périmètre polygone ouvert. À demander (Anah/EPCI).
- **Périmètres ORT infra-communaux (EPCI)** — Périmètres ORT infra-communaux — à demander aux EPCI. L'éligibilité communale est déjà servie (id 128).
- **Micro-données OLL (ADIL / AGORAH)** — Micro-données OLL — accès conventionné (ADIL/AGORAH). Agrégats par zone déjà servis (id 129). À conventionner pour le détail.
- **LOVAC (logements vacants)** — LOVAC — détail RÉSERVÉ aux collectivités/État/Anah (fiche 19). Non ingéré. En attendant : vacance INSEE RP par IRIS. Voir Lot 3 : sur quelle base on la lirait (une collectivité mandante requise).
- **DV3F (Cerema)** — DV3F Cerema — même convention que les Fichiers fonciers. Non ingéré. En attendant : DVF + échantillon Région. Voir Lot 3.

## Énergie, réseaux, assainissement

| | Source | Verdict | Millésime base | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟣 | **VRD / assainissement (SPANC)** (`26`) | MANUELLE | — | oui | — | 0 | — |
| 🟡 | **DPE ADEME (logements existants)** (`37`) | PARTIELLE — couverture incomplète | — | oui | KO | 1 | fiche |
| 🟢 | **PVGIS (Commission européenne)** (`48`) | PLEINE | PVGIS v5.3 · modèle SARAH3 (relevé au run du builder solaire) | non | OK | 1 | fiche, outil, scoring |
| ⚫ | **EDF SEI Réunion — open data** (`49`) | RETIRÉE (déjà) | — | non | KO | 0 | — |
| ⚫ | **Registre national des installations (ODRÉ)** (`50`) | RETIRÉE (déjà) | — | non | — | 0 | — |
| 🟢 | **Parkings OSM (loi APER)** (`51`) | PLEINE | — | non | — | 1 | fiche |
| 🟢 | **INSEE RP2022 — fichier détail Logements (EGOUL)** (`66`) | PLEINE | RP2022 — fichier détail Logements, publié le 16/10/2025 (INSEE) | oui | OK | 1 | fiche |
| 🔗 | **GPU — zonages d'assainissement (info-surf typeinf 19)** (`67`) | ALIAS (doublon) | GPU — idurba par commune ; SIG 4/24 au 11/07/2026 | non | — | 0 | — |
| 🟡 | **Office de l'eau Réunion — Chroniques de l'eau** (`68`) | PARTIELLE — couverture incomplète | Chronique n°149 — données 2023 | oui | — | 1 | fiche |
| 🟢 | **Fibre Arcep — Ma connexion internet (immeuble)** (`126`) | PLEINE | 2026_T1 — 330 051 immeubles 974 (découpage départemental) | oui | KO | 1 | fiche |
| ⬜ | **Zonages d'assainissement SIG complets (EPCI / régies)** (`134`) | À DEMANDER / À BRANCHER | en attente de la demande aux EPCI (GPU : 4/24) | non | — | 0 | — |

- **VRD / assainissement (SPANC)** — VRD/SPANC — saisie EPCI manuelle, aucune table dédiée. Collectif/non-collectif saisi. Licence « à confirmer ». Voir Lot 3.
- **DPE ADEME (logements existants)** — ⚠ Coverage RÉELLE quasi-nulle sur la base servie : `dpe_records` = 17, `v_passoire_thermique` = 1. « Connecté » mais l'ingestion DPE (cron mensuel) n'a quasi rien chargé — ce n'est PAS un artefact de base de dev (la base porte 431 663 parcelles), c'est un vrai trou d'ingestion à investiguer (le cron tourne-t-il ? l'API ADEME répond-elle ?).
- **PVGIS (Commission européenne)** — API de calcul solaire (CC BY 4.0). Alimente productible. À plein usage ; attention libellé inclinaison (dette VERIF-1).
- **EDF SEI Réunion — open data** — EDF SEI open data — amont 410 Gone (jeu retiré par EDF ~2026). Retirée 06/09/2026. Rien à sonder. Le réseau HTA vit via id 93.
- **Registre national des installations (ODRÉ)** — Registre national installations (ODRÉ) — jamais branché, aucun usage. Retirée 06/09/2026.
- **Parkings OSM (loi APER)** — Alimente 1 chiffre(s) du registre ; visible dans : 1 section(s) de fiche. *(raison auto — champs producteur non vérifiés, cf. mandat)*
- **INSEE RP2022 — fichier détail Logements (EGOUL)** — RP2022 fichier Logements (EGOUL) → maille ANC. Sert le taux d'assainissement collectif/non collectif.
- **GPU — zonages d'assainissement (info-surf typeinf 19)** — GPU zonages assainissement (info-surf) = canal info-surf du même réservoir que id 63 (alias_de=63). Alias correct.
- **Office de l'eau Réunion — Chroniques de l'eau** — ⚠ RETRAIT EN ATTENTE (lot 0 S2). Vic avait décidé le retrait, mais `anc_service.py:57` lit encore `anc_office_eau_commune` EN DIRECT pour servir le statut ANC des 6 communes 100 % ANC (chiffre `part_logements_egout_pct`, moteur `anc`, fiche Réseaux). Retrait refusé tant que ce lecteur vit. Licence « à confirmer ».
- **Fibre Arcep — Ma connexion internet (immeuble)** — Fibre Arcep 330 051 immeubles (2026_T1). Sert l'éligibilité fibre à l'immeuble.
- **Zonages d'assainissement SIG complets (EPCI / régies)** — Zonages d'assainissement SIG complets — 4/24 via GPU aujourd'hui ; les 20 autres à demander aux 5 EPCI/régies (DEMANDE-REGION-EPCI). Voir Lot 2.

## Économie, équipements, accès

| | Source | Verdict | Millésime base | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **Base Adresse Nationale** (`18`) | PLEINE | — | oui | OK | 1 | fiche |
| 🟢 | **BPE INSEE** (`20`) | PLEINE | millésime 2025 (géographie au 01/01/2025) | oui | OK | 2 | fiche, carte |
| 🟢 | **SIRENE** (`21`) | PLEINE | Sirene INSEE — état courant (non versionné) | oui | — | 0 | — |
| 🟢 | **BODACC (procédures collectives)** (`29`) | PLEINE | — | oui | OK | 1 | fiche, scoring |
| 🟡 | **INPI RNE (dirigeants)** (`31`) | PARTIELLE — champs manquants | — | non | OK | 1 | outil |
| 🟡 | **Recherche d'entreprises (DINUM)** (`45`) | PARTIELLE — couverture incomplète | Sirene INSEE / RNE INPI (api.gouv.fr) — courant | non | — | 1 | fiche, scoring |
| 🟢 | **Filosofi INSEE (carreaux 200 m)** (`52`) | PLEINE | millésime 2021 | oui | OK | 5 | fiche, outil, PDF, scoring |
| 🟢 | **Contours IRIS (IGN/INSEE)** (`64`) | PLEINE | Contours IRIS — géographie 2024 (IGN/INSEE) | oui | — | 1 | fiche, carte, outil |
| 🟢 | **Transport public — GTFS (PAN, 7 réseaux)** (`74`) | PLEINE | 7 jeux PAN, màj 2025-12-29 → 2026-08-17 | oui | OK | 4 | fiche, carte |
| 🟢 | **OSM — transport (pôles d'échange & téléphérique)** (`75`) | PLEINE | extraction Overpass (base OSM vivante, ODbL) | non | OK | 4 | fiche, carte |
| 🟢 | **SIRENE établissements géolocalisés** (`86`) | PLEINE | SIRENE géolocalisé — publication mensuelle INSEE | oui | KO | 3 | fiche, outil, scoring |
| ⚫ | **MOBPRO (mobilités domicile-travail, INSEE)** (`87`) | RETIRÉE (déjà) | MOBPRO INSEE — fichier détail (millésime RP) | non | — | 0 | — |
| 🟢 | **Trafic RN (Région Réunion — SIR)** (`88`) | PLEINE | Trafic RN Région — comptages (millésime porté par tronçon) | oui | KO | 1 | outil |
| 🟢 | **EDF Réunion — lignes moyenne tension HTA (open data)** (`93`) | PLEINE | EDF géométrie ~02/2020 · publié 16/10/2025 | oui | KO | 0 | carte |
| 🟢 | **TCSP — voies bus en site propre (OSM)** (`94`) | PLEINE | extraction Overpass (OSM, ODbL) — voies bus 974 | non | — | 0 | carte |
| ⬜ | **Réunion Express — hypothèses de tracé (débat public CNDP)** (`95`) | À DEMANDER / À BRANCHER | — | oui | — | 0 | — |
| 🟢 | **Annuaire de l'administration (service-public.fr / DILA)** (`99`) | PLEINE | annuaire service-public.fr — 24 mairies (OUTILS K2) | non | — | 1 | fiche |
| 🟢 | **INSEE RP2022 — bases IRIS (logement, population)** (`133`) | PLEINE | RP2022 — parution 16/10/2025 (géographie 01/01/2024) | oui | — | 2 | fiche, outil |
| ⬜ | **Inventaires ZAE (EPCI — loi Climat et résilience)** (`135`) | À DEMANDER / À BRANCHER | en attente de la demande aux EPCI (L.318-8-2 CU) | non | — | 0 | — |

- **Base Adresse Nationale** — BAN — géocodage d'adresses (job sur clic). Socle adresses↔parcelles.
- **BPE INSEE** — BPE INSEE 2025 (équipements, 35 546 objets couche). Sert l'attractivité (commerces, écoles…).
- **SIRENE** — Servie via l'API recherche-entreprises EN DIRECT (Scan patrimoine, Copilote entreprise) — d'où 0 chiffre de registre attaché à `sirene_recherche_entreprises` (API à la requête, sans table). Ce n'est PAS invisible : le pro l'atteint par le Scan/Copilote. Le canal géolocalisé (id 86) est la variante à réservoir. Voir S3.
- **BODACC (procédures collectives)** — BODACC procédures collectives (job sur clic). Signal entreprise/propriétaire.
- **INPI RNE (dirigeants)** — INPI RNE dirigeants. Licence SPÉCIFIQUE homologuée (pas Licence Ouverte) — usage encadré, à respecter.
- **Recherche d'entreprises (DINUM)** — ⚠ RETRAIT EN ATTENTE (lot 0 S2). Vic avait décidé le retrait, mais `owner_enrichment`/`owner_denom_lookup` sont lus EN DIRECT par le Score V (`score_v.py:90,98`), les facettes propriétaire (`proprietaire_facettes.py:70`) et le Scan (`app.py:4695`) — chiffre `evenements_proprietaire_liste`, fiche Propriétaire. Retrait refusé tant que ces lecteurs vivent.
- **Filosofi INSEE (carreaux 200 m)** — Filosofi 2021 (carreaux 200 m). Sert le revenu/population de zone. Millésime 2021 (le plus récent publié).
- **Contours IRIS (IGN/INSEE)** — Contours IRIS 2024. Socle géographique infra-communal (rattachements).
- **Transport public — GTFS (PAN, 7 réseaux)** — GTFS 7 réseaux (PAN, maj 2026). Arrêts/lignes de transport en couche.
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

| | Source | Verdict | Millésime base | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟢 | **RGE ALTI (altimétrie)** (`6`) | PLEINE | RGE ALTI® (IGN) — édition non enregistrée | oui | — | 3 | fiche, carte, PDF |
| 🟢 | **BD TOPO IGN** (`17`) | PLEINE | BD TOPO® V3 (IGN) — édition non enregistrée | oui | — | 18 | fiche, carte, outil, PDF, scoring |
| 🟡 | **IGN BD CARTO V5 — occupation du sol** (`22`) | PARTIELLE — champs manquants | BD CARTO® V5 — occupation du sol (IGN, proxy) | oui | — | 0 | carte |
| 🟢 | **BD ORTHO 20 cm (IGN)** (`61`) | PLEINE | BD ORTHO IGN 974 — millésime 2025 (piscine, 90,7 %) | oui | OK | 3 | fiche, outil, copilote |
| 🔗 | **RGE ALTI 5 m (IGN)** (`65`) | ALIAS (doublon) | RGE ALTI® 5 m (IGN) — édition non enregistrée | non | — | 0 | — |
| 🟡 | **BD ORTHO IRC (IGN)** (`69`) | PARTIELLE — couverture incomplète | — | oui | KO | 1 | fiche, outil, scoring |
| 🟡 | **LiDAR HD — MNH 50 cm (IGN)** (`70`) | PARTIELLE — couverture incomplète | LiDAR HD MNH — dalles publiées 25/06/2025 (IGN) | oui | OK | 3 | fiche, outil, scoring |
| 🟢 | **CoSIA (couverture du sol IA, IGN)** (`83`) | PLEINE | CoSIA 2025 (PVA juil.-août 2025, 20 cm) | oui | OK | 13 | fiche, carte, outil, PDF, scoring |
| 🟢 | **Cadastre d'époque (Etalab / PCI vecteur DGFiP)** (`96`) | PLEINE | archives 2017-02 (PCI) et 2017-07→2026-06 (Etalab) | non | — | 1 | fiche |

- **RGE ALTI (altimétrie)** — RGE ALTI — pente 5 m (147 398 objets). Socle topographique (pente, viabilisation).
- **BD TOPO IGN** — 1,07 M d'objets (bâti, voirie, eau, ravine). Socle géométrique lu par potentiel/solaire/viabilisation. À plein usage sur les thèmes ingérés.
- **IGN BD CARTO V5 — occupation du sol** — BD CARTO V5 occupation du sol (proxy OCS, 1 643 objets). Proxy grossier — l'OCS GE officielle est une candidate (lot 5).
- **BD ORTHO 20 cm (IGN)** — BD ORTHO 20 cm 2025. Détection piscines (90,7 %), fond ortho. À plein usage.
- **RGE ALTI 5 m (IGN)** — RGE ALTI 5 m = même réservoir que id 6 (alias_de=6). Alias correct.
- **BD ORTHO IRC (IGN)** — ⚠ RETRAIT EN ATTENTE (lot 0 S2). Vic avait décidé le retrait, mais l'infrarouge IRC est la source du NDVI/canopée : `parcel_vegetation` (431 663 lignes) est lu EN DIRECT par le solaire (`solaire.py:311` ombrage), le Flash (`flash/data.py:650`) et le scoring P (`p_model/sql.py:287`). Chiffre `prod_spec_kwh_kwc`, fiche Solaire. Retrait refusé tant que ces lecteurs vivent.
- **LiDAR HD — MNH 50 cm (IGN)** — Correction (2ᵉ passe) : la hauteur LiDAR (faîtage/égout) couvre 303 452 parcelles (~70 %) dans `batiment_hauteur_lidar` — le batch de dalles a ACHEVÉ (les figures « 5 406 » de État-1 et « 80 905 » de RECETTE-11 sont périmées). Reste partielle car ~30 % des parcelles n'ont pas de bâti mesuré et le VERDICT de toiture (`toiture_lidar`) n'existe que sur 27 parcelles. **Provenance à corriger** : la hauteur LiDAR alimente `marge_surelevation_m`/`hauteur_bati_m` mais le registre crédite `bd_topo`, pas `lidar_hd_mnh` — la source LiDAR n'est pas tracée sur ce qu'elle sert.
- **CoSIA (couverture du sol IA, IGN)** — 445 190 bâtis IA (2025), cœur du potentiel/scoring. Bâti à plein usage ; autres classes CoSIA non exploitées (par choix).
- **Cadastre d'époque (Etalab / PCI vecteur DGFiP)** — Cadastre d'époque (archives PCI 2017→2026). Sert le rattachement des permis anciens (RETOURS-14).

## Hubs et catalogues

| | Source | Verdict | Millésime base | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🏛 | **Région Réunion Open Data (Opendatasoft)** (`11`) | HUB (catalogue) | — | oui | — | 0 | — |
| 🏛 | **PEIGEO (hub régional)** (`12`) | HUB (catalogue) | — | non | — | 0 | — |
| 🏛 | **Géoplateforme IGN** (`14`) | HUB (catalogue) | — | non | — | 0 | — |

- **Région Réunion Open Data (Opendatasoft)** — Portail Région ODS — hub de catalogue, jamais un réservoir. Licence par jeu à confirmer.
- **PEIGEO (hub régional)** — PEIGEO/AGORAH — hub régional, jamais un réservoir.
- **Géoplateforme IGN** — Géoplateforme IGN — hub, jamais un réservoir. Point d'accès de nombreuses sources IGN.

## Autres

| | Source | Verdict | Millésime base | Sentinelle | Filtre | Chiffres | Où (résumé) |
|---|---|---|---|---|---|---|---|
| 🟠 | **Taxe d'aménagement — taux communaux (délibérations)** (`98`) | SERVIE HORS REGISTRE | DGFiP DELTA — 24/24 communes en vigueur (08/09/2026) | non | OK | 0 | — |
| 🟢 | **Taux de taxe foncière — fichier REI (DGFiP)** (`127`) | PLEINE | REI 2025 (impositions primitives) — 24/24 communes | oui | OK | 1 | fiche |
| 🟡 | **ACV / PVD / ORT (DGALN — liste des communes)** (`128`) | PARTIELLE — couverture incomplète | table DGALN vivante — 19 communes 974, 13 ORT signées | oui | KO | 1 | fiche |
| 🟢 | **Coût de construction (EPTB SDES + choix LABUSE)** (`131`) | PLEINE | EPTB 2024 (contexte) ; choix promotion 2300-2800 €/m² SDP | oui | OK | 1 | outil |

- **Taxe d'aménagement — taux communaux (délibérations)** — Taux 24/24 servis (outil Taxe d'aménagement + Financier) MAIS les chiffres `taxe_amenagement_eur`/`taxe_amenagement_estimee_eur` ont `reservoirs={}` — le taux communal saisi n'est pas rattaché comme réservoir. Provenance non tracée.
- **Taux de taxe foncière — fichier REI (DGFiP)** — Taux taxe foncière REI 2025, 24/24. Sert l'estimation fiscale (fiche commune fiscalité).
- **ACV / PVD / ORT (DGALN — liste des communes)** — Table DGALN vivante, 19 communes. C'est l'éligibilité COMMUNALE ; le périmètre ORT infra-communal (Denormandie) est une source à part (id 138, à demander).
- **Coût de construction (EPTB SDES + choix LABUSE)** — Coût de construction (EPTB 2024 + choix LABUSE 2300-2800 €/m²). Sert le bilan promoteur. Le « choix LABUSE » est délibéré et sourcé.
