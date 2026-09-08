# EXPORTS — catalogue des sources LABUSE (77 + 7 à créer)

Établi le 05/09/2026 depuis `data_sources` (77 lignes), `source_veille` (49 lignes) et `SENTINELLE-INVENTAIRE.md` (01/09). Une ligne par source : ce qu'elle apporte **à une parcelle**, ce que LABUSE sert aujourd'hui comme millésime, l'état de fraîcheur et de veille, et les documents où elle va.

**Documents** : D Dossier (= Flash sans financier) · P PDF résumé · F Financier · A Apporteur · PC Pré-dossier PC · S support (nécessaire au calcul, jamais affichée) · — non servie.
**Fraîcheur** (colonne `fraicheur_statut`) : ✅ à jour · ⏰ en retard · ∅ sans échéance (la sentinelle ne peut pas dire si c'est frais) · ⚠ anomalie.

---

## Le constat d'ensemble, avant le tableau

- **44 sources sur 77 sont « sans échéance »** : elles n'ont ni cadence ni prochain millésime, donc aucun document ne peut prouver leur fraîcheur. C'est la dette que le bloc « Sources & millésimes » du Dossier rend visible (« millésime non renseigné » × 10). Le rapport d'audit dit que la date existe ailleurs pour 26 des 31 orphelines : c'est un travail de composition, pas d'ingestion.
- **Trois anomalies vivantes** : SITADEL — la sentinelle a détecté **une nouvelle version amont** (`nouvelle_version`), non injectée ; DVF — cadence semestrielle **en retard** ; DEAL WMS/WFS (NPNRU) — sonde **injoignable**.
- **Sept sources cataloguées mais jamais servies dans un export**, dont quatre utiles : Sudocuh (PLU en révision — c'est le bloc « fraîcheur du zonage »), RP2022 EGOUL (part réelle des logements raccordés à l'égout), PLH des 5 EPCI, LiDAR HD MNH (hauteur du bâti mesurée, meilleure que BD TOPO).
- **Six « à faire »** au catalogue : PEIGEO, EDF SEI open data, ODRÉ, ZNIEFF Région (doublon), BDNB (974 absent), Réunion Express.
- **Quatre manuelles** : SPANC, Fichiers fonciers (sous convention, jamais ingérés), Radar, MOBPRO (écartée).

---

## Identité, cadastre, adresse, imagerie

| ID | Source | Apport à la parcelle | Millésime servi | Fraîcheur · veille | Documents |
|---|---|---|---|---|---|
| 1 | Cadastre API Carto PCI | géométrie, IDU, contenance | « latest » | ∅ · api ok | tous |
| 2 | Cadastre Etalab bulk | idem, base locale | « latest » | ∅ · doublon de 1 | tous |
| 18 | Base Adresse Nationale | adresse rattachée | mensuel | ✅ · api ok | tous |
| 61 | BD ORTHO 20 cm | plan de situation, contour posé | 2025 | ∅ · api ok | tous |
| 69 | BD ORTHO IRC | infrarouge (végétation) | — | ∅ · api ok | S |
| 64 | Contours IRIS | géographie statistique | 2024 | ∅ · api ok | S |
| 17 | BD TOPO | bâti (emprise, hauteur, nombre), voirie, hydro, ravines | édition non enregistrée | ∅ · api ok | D P F A PC |
| 70 | LiDAR HD MNH 50 cm | **hauteur réelle du bâti et de la végétation** | dalles 25/06/2025 | ∅ · api ok | **à brancher** (hauteur du bâti existant : aujourd'hui BD TOPO) |
| 83 | CoSIA 2025 | emprise bâtie révélée (74 %), canopée (99 %) | 2025 | ∅ · api ok | D |
| 22 | BD CARTO occupation du sol | artificialisé (grain grossier) | proxy | ∅ · api ok | D (une ligne « aucun signal ») |
| 6 / 65 | RGE ALTI | pente moyenne et max | édition non enregistrée | ∅ · api ok / doublon | D PC |

## Urbanisme et règles

| ID | Source | Apport | Millésime servi | Fraîcheur · veille | Documents |
|---|---|---|---|---|---|
| 3 | PLU/GPU API Carto | zones, parts, prescriptions (**ER, EBC**, mixité, pluvial), document opposable | en direct, par commune | ∅ · non surveillable (Y3) | D P F A PC |
| 44 | SUP assiettes GPU | servitudes PM1, AC, EL… | — | ∅ · non surveillée | D PC |
| 62 | Sudocuh | **procédures en cours (PLU en révision)** | état 31/12/2024 | ∅ · — | **à brancher** au bloc « fraîcheur du zonage » (D P PC) |
| 63 / 67 | GPU zonages d'assainissement | collectif / non collectif | SIG 4/24 au 11/07/2026 | ∅ · non surveillée | D PC |
| 9 / 15 | Potentiel foncier Région | îlots « potentiel foncier » (indicatif) | — | ∅ · api ok | D (« aucun signal ») |
| 10 | RPG | parcelle déclarée agricole | RPG.LATEST, année non pinnée | ∅ · api ok | D (« aucun signal ») |
| 42 | PLH des 5 EPCI | objectifs logement par EPCI | — | ∅ · — | **à brancher** (D §8 contexte) |
| 43 | RTAA DOM | textes thermique / acoustique / aération | — | ∅ · — | PC (annexe) |
| 47 | 50 pas géométriques | zone littorale domaniale | cadastre 1877 | ∅ · — | D (« aucun signal ») |

## Risques, environnement, patrimoine

| ID | Source | Apport | Millésime servi | Fraîcheur · veille | Documents |
|---|---|---|---|---|---|
| 30 | PPR / aléas DEAL | zone PPR, prescriptions | 2011-2026 | ∅ · témoin ok | D P F PC |
| 4 | Géorisques (socle) | aléas, **CatNat (table tronquée à réparer)** | — | ∅ · api ok | D P PC |
| 32 · 33 · 34 · 36 | Géorisques SSP · cavités · ICPE · MVT | sites pollués, cavités, installations classées (régime), mouvements | — | ∅ · ok | D (« aucun signal » sauf ICPE classée) |
| 46 | Classement sonore Cerema | bruit routier, isolement acoustique | déc. 2023 | ∅ · api ok | D P F PC |
| 28 | Érosion côtière Cerema | recul du trait de côte | 2018 | ∅ · en-tête ok | D (« aucun signal ») |
| 24 | Mérimée / ABF | abords MH (nom du monument à ajouter) | — | ∅ · api ok | D P PC |
| 25 | INPN espaces protégés | espace protégé réglementaire | passe 05/07/2026 | ∅ · — | D |
| 7 | Parc national | dans / hors | 2021 | ∅ · api ok | D |
| 76 / 80 | ZNIEFF | inventaire naturaliste | 29/08/2025 / à faire (doublon) | ∅ · api ok | D |
| 8 | Forêts publiques ONF | dans / hors | BD TOPO V3 | ∅ · api ok | D |
| 35 | Cartofriches | friche recensée | — | ∅ · api ok | D (« aucun signal ») |
| 13 | DEAL WMS/WFS | NPNRU, quartiers | QP 2024 | ⚠ **injoignable** | D |
| 38 | QPV 2024 ANCT | quartier prioritaire, bande 500 m (dérivé) | 2024 | ∅ · api ok | D F |
| 40 | NPNRU | renouvellement urbain | — | ∅ · — | D |

## Marché, propriétaire, économie

| ID | Source | Apport | Millésime servi | Fraîcheur · veille | Documents |
|---|---|---|---|---|---|
| 5 | DVF | prix du secteur, comparables, tendance, neuf observé, terrain nu | 2021-2025 (ventes en base jusqu'au 10/08/2026) | ⏰ **en retard** (semestriel) · page ok | D P F |
| 16 | SITADEL | permis, offre engagée, délais d'instruction | 2026-07 | ✅ mais ⚠ **nouvelle version amont détectée, non injectée** | D P F PC |
| 71 | DGFiP parcelles PM | propriétaire personne morale, **historique 2019→2025** | panel 2019→2025 | ✅ annuelle · en-tête ok | D A |
| 21 · 86 | SIRENE · établissements géolocalisés | identité PM, emplois et concurrence de la zone | état courant / mensuel | ∅ · api ok | D A |
| 45 | Recherche d'entreprises DINUM | fiche entreprise | — | ∅ · — | D A |
| 31 | INPI RNE | dirigeants | — | ∅ · — | D |
| 29 | BODACC | procédures collectives (par SIREN connu) | — | ∅ · api ok | D F |
| 27 | Fichiers fonciers Cerema | — (sous convention, **jamais ingérés**) | — | rappel 365 j | — |
| 84 | Radar | annonces en vente (7 rattachées) | collecte manuelle | rappel quotidien | liste factuelle D A ; jamais une statistique |
| 41 | INSEE RP Logement 2023 | structure du parc communal | — | ∅ · — | D |
| 39 | Inventaire SRU DHUP | taux LLS, déficit | 2024 | ∅ · — | D P |
| 66 | INSEE RP2022 EGOUL | **part des logements raccordés à l'égout** | RP2022 | ∅ · api ok | **à brancher** (D §6) |
| 52 | Filosofi carreaux 200 m | niveau de vie, ménages, âge | 2021 | ∅ · api ok | D P |
| 20 | BPE | équipements par catégorie | 2025 | ∅ · api ok | D P |
| 87 | MOBPRO | — (écartée le 28/08) | — | manuel | **à retirer des pieds de page** |
| 88 | Trafic RN Région | flux routiers (chalandise) | comptages | ∅ · api ok | D (visage chalandise) |
| 72 · 73 | ZFANG · FRR | dispositifs fiscaux | décret 2026-421 · FRR 2024 | ∅ · — | D F |
| 37 | DPE ADEME | — (17 lignes) | — | ⏰ en retard · api ok | **retiré** |
| 89 | BDNB | — (974 absent) | 2026-02-a | à faire | **retiré** |

## Réseaux, desserte, énergie

| ID | Source | Apport | Millésime servi | Fraîcheur · veille | Documents |
|---|---|---|---|---|---|
| 26 | SPANC / assainissement EPCI | gestionnaires | saisie manuelle | rappel | D PC |
| 68 | Office de l'eau | chroniques de l'eau | n° 149, données 2023 | rappel | S |
| 93 | EDF HTA moyenne tension | lignes MT (proxy réseau électrique) | géométrie 2020, publié 2025 | vide · en-tête | **à brancher** (D §6 viabilisation) |
| 49 · 50 | EDF SEI open data · ODRÉ | énergie | — | à faire | — |
| 74 | GTFS 7 réseaux | arrêts, lignes, fréquences | màj 12/2025 → 08/2026 | ∅ · api ok | D P |
| 75 | OSM transport | pôles d'échange, téléphérique (**seuil de distance à poser**) | Overpass vivant | ∅ · — | D |
| 94 | TCSP OSM | voies bus en site propre (en service / projet) | Overpass | vide · — | **à brancher** (D desserte) |
| 95 | Réunion Express | hypothèses de tracé | — | à faire | — |
| 19 | OSM Overpass | commerces et services proches | vivant | ∅ · — | D |
| 48 | PVGIS | productible solaire | v5.3 SARAH3 | ∅ · — | D |
| 51 | Parkings OSM (loi APER) | obligation solaire si parking > 1 500 m² | — | ∅ · — | D (signal conditionnel) |
| 11 · 12 · 14 | Hubs Région ODS · PEIGEO · Géoplateforme | portails | — | hub / à faire | S |

---

## À créer (lot C de l'audit, à ajouter au catalogue avec un ID)

| Source | Apport | Effort | Documents |
|---|---|---|---|
| DPU — GPU info-surf typeinf 04 | droit de préemption urbain (4 communes téléversées, « non téléversé » ailleurs) | S | D P F A PC |
| PEB Roland-Garros et Pierrefonds — Géoplateforme DGAC | zones où le logement est interdit ou conditionné | S | D P F PC |
| Zonage A/B/C du logement — arrêté 23/06/2026 | plafonds LLS, dispositifs DOM (4 communes en A, 20 en B1) | S | D P F |
| Loyers de marché — Carte des loyers DHUP 2025 | loyer médian appartement / maison, 24 communes | S | D P F |
| Coût de construction — EPTB 2024 + dataset CDC Réunion | fourchette sourcée (2 304 → 2 842 €/m², 2021-2025) | S | F |
| Taux communaux de taxe d'aménagement | à sonder avant de faire saisir | S | F PC |
| CatNat — GASPAR (réparation de l'ingestion tronquée) | historique des arrêtés par commune | S | D |

## À clore définitivement

Captages AS1 (introuvable en open data), argiles (non pertinent au 974), volcanique (aucun zonage opposable), ECLN (métropole seule), BDNB (974 absent), DPE (17 lignes), Fichiers fonciers (convention non ingérée), MOBPRO (écartée).

---

## Addendum — vérification contre la base réelle (05/09/2026, audit EXPORTS)

*Section ajoutée par l'audit ; le texte ci-dessus est le catalogue d'origine, non modifié. Requêtes : annexe `DONNEES-ANNEXE.md` §catalogue.*

Confirmé à l'identique :

- `data_sources` = **77 lignes**, `source_veille` = **49 lignes**, colonne `fraicheur_statut` présente.
- Les 16 IDs sondés (1, 5, 16, 18, 37, 61, 70, 71, 83, 84, 87, 88, 89, 93, 94, 95) correspondent tous au nom annoncé.
- Les **trois anomalies vivantes**, mot pour mot : DVF `fraicheur_statut='en_retard'` ; DEAL WMS/WFS `dernier_statut='injoignable'` ; SITADEL `dernier_statut='nouvelle_version'` (avec `fraicheur_statut='a_jour'` — la version détectée n'est pas injectée).
- Statuts : `connecte`=65, `a_faire`=**6** ✓, `manuel`=**4** ✓, `hub`=2 ✓.
- Jamais servies dans une chaîne d'export (grep `flash/`, `briques_pdf`, `pdf_premium`, `argumentaire`, `banquier`, `pre_dossier`) : Sudocuh, PLH, LiDAR HD MNH, TCSP, Réunion Express — **0 occurrence** ✓.

Deux écarts à corriger si le catalogue est repris :

1. **« 44 sources sur 77 sans échéance » : le vrai compte est 62** (`fraicheur_statut='sans_echeance'`), plus **10 sans statut du tout** (NULL), 3 `a_jour`, 2 `en_retard`. Aucun sous-ensemble naturel ne donne 44 (sous veille : 40 ; connectées : 58). Le constat est donc **pire** que l'énoncé : 72/77 sources ne peuvent pas prouver leur fraîcheur.
2. **RP2022 EGOUL n'est pas strictement « jamais servie »** : le Pré-dossier PC la cite comme source réellement interrogée de la notice assainissement (`api/pre_dossier.py:563`, via la couche ANC probabiliste). Le « à brancher (D §6) » reste juste pour le Dossier.
