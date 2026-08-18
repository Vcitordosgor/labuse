# État des sources LABUSE — tableau de référence

*Toutes les cases viennent de mesures existantes (mandat M123, audit sources/score, radar réparé).
Une case jamais mesurée porte « À MESURER » — rien n'est inventé.*

**Lecture des colonnes**
- **Utilité** — ce que la source fait dans l'app, en clair. Trois rôles possibles : elle **nourrit le
  score** (le calcul de chances de mutation), elle **exclut / signale un risque** (elle écarte ou
  marque une parcelle), ou elle **informe la fiche** (contexte affiché, sans peser sur le tri).
- **Fraîcheur** — le millésime réellement en base + comment on suit sa mise à jour (sonde automatique,
  ou vérification manuelle à cadence dite).
- **Dernière version dispo ?** — sommes-nous sur la version la plus récente du producteur ? **OUI** /
  **NON** (une plus récente existe) / **NON VÉRIFIABLE** (avec la raison). D'après le radar réparé
  (sonde) et les vérifications amont menées en M123.
- **Couverture** — pour une donnée *par parcelle* : nombre de communes couvertes / 24 et % de parcelles
  renseignées. Pour une *couche d'exclusion* : elle couvre un **territoire**, pas des parcelles — on dit
  alors l'emprise.

**54 sources servies** (celles de la vitrine) + **8 en annexe** (doublons fusionnés, retirées, dormantes).

---

## A. Elles nourrissent le score (chances de mutation)

| Source | Utilité | Fraîcheur | Dernière version dispo ? | Couverture |
|---|---|---|---|---|
| **DVF / valeurs foncières** *(le cœur)* | Nourrit le score : historique des ventes (rotation, prix, ancienneté de détention) — le signal le plus lourd du calcul. | Millésimes 2021–2025 · **sonde auto** hebdo (mer.) | **OUI** (sonde à jour) | **24/24** · 29 566 mutations |
| **SITADEL (autorisations d'urbanisme)** | Nourrit le score : permis de construire déposés autour de la parcelle (dynamique de construction). | 2026-06 · **sonde auto** quotidienne | **OUI** (sonde à jour) | **24/24** · 50 292 permis |
| **Urbanisme PLU/GPU (API Carto)** | Nourrit le score (et peut exclure) : la zone du PLU (constructible ou non) de chaque parcelle. | GPU/PLU par commune · vérif manuelle (grande passe) | **NON VÉRIFIABLE** — révisions PLU non datables auto, vérif producteur au geste dédié | **24/24** · 5 845 zones · 10 490 prescriptions |
| **BD TOPO IGN** | Nourrit le score (et cascade) : le bâti et la voirie (empreinte construite, accès). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — IGN, publication continue non datable auto | Île · 817 506 bâtiments · 235 643 voies |
| **RGE ALTI — canal MNT 5 m** | Nourrit le score (et cascade) : la pente du terrain (une forte pente pèse contre la constructibilité). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — IGN, référentiel non daté en base | **24/24** · pente sur 147 398 mailles |
| **Filosofi INSEE (carreaux 200 m)** | Nourrit le score : le tissu social/économique local (revenus, densité). | Millésime 2021 · vérif manuelle | **OUI** — vérif amont M123 : 2021 = dernier millésime publié | Île · 14 773 carreaux |
| **LiDAR HD — MNH 50 cm (IGN)** | Nourrit le score : la hauteur de végétation (canopée) sur la parcelle. | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — IGN, dalles LiDAR non datées en base | **24/24** · 431 663 parcelles (100 %) |
| **OpenStreetMap / Overpass** | Nourrit le score : la distance aux équipements (école, santé, commerce) — l'accès. | Base OSM vivante · vérif manuelle | **NON VÉRIFIABLE** — base OSM continue, sans millésime | **24/24** · 431 663 parcelles (100 %) |
| **Cartofriches (Cerema)** | Nourrit le score (et cascade) : les friches recensées (terrain à recycler). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — Cerema, publication non datable auto | Île · 372 friches |
| **BD ORTHO 20 cm (IGN)** | Nourrit le score (détection) : repère les piscines par photo aérienne (indice d'usage résidentiel). | IGN 974 millésime 2025 · vérif manuelle | **NON VÉRIFIABLE** — prochaine campagne ortho non datable | Île · piscines détectées 90,7 % |
| **BD ORTHO IRC (IGN)** | Nourrit le score (détection) : la vigueur de végétation (NDVI infrarouge). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — prochaine campagne ortho non datable | Île |

---

## B. Elles excluent ou signalent un risque (cascade territoriale)

| Source | Utilité | Fraîcheur | Dernière version dispo ? | Couverture |
|---|---|---|---|---|
| **DEAL Réunion — PPR / aléas** | Exclut les parcelles en zone de risque naturel réglementé (PPR). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — DEAL, révisions PPR non datables auto, vérif producteur au geste dédié | Île · 164 PPR · 993 aléas |
| **Parc National de La Réunion (INPN)** | Exclut les parcelles en cœur de parc national (inconstructible). | Millésime 2021 · vérif manuelle | **NON VÉRIFIABLE** — INPN, périmètre non daté en base | Île · 3 emprises (cœur/adhésion) |
| **Géorisques (BRGM)** | Signale les risques géologiques (base de rattachement des couches ci-dessous). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — BRGM, endpoint non sondable (500) | Île |
| **Géorisques — ICPE** | Signale les installations classées à proximité. | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — BRGM, endpoint non sondable (500) | Île · 1 261 sites |
| **Géorisques — cavités souterraines** | Signale les cavités sous la parcelle. | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — BRGM, endpoint non sondable (500) | Île · 151 cavités |
| **Géorisques — mouvements de terrain** | Signale les mouvements de terrain (informatif, ne retire pas). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — BRGM, endpoint non sondable (500) | Île · 3 085 mouvements |
| **Géorisques — sites et sols pollués** | Signale les sols pollués recensés. | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — BRGM, endpoint non sondable (500) | Île · 513 sites |
| **DEAL Réunion — trait de côte** | Signale le recul du trait de côte (risque littoral). | Millésime 2018 · vérif manuelle | **OUI** — vérif amont M123 : 2018 = dernier trait national Cerema | Île · 24 168 segments |
| **Forêts publiques (ONF)** | Signale les parcelles en forêt publique (contrainte d'usage). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — ONF/BD TOPO, non datable auto | Île · 65 emprises *(dédoublonnées M123)* |
| **OCS GE (IGN)** | Signale l'occupation du sol (naturel/agricole/urbain). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — proxy BDCARTO, non natif OCS GE | Île · 1 643 emprises *(dédoublonnées M123)* |
| **ENS (Département)** | Signale les Espaces Naturels Sensibles (préemption possible). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — dispositif départemental non public | **21/24** · 73 emprises *(3 communes = 0 ENS réel)* |
| **Classement sonore ITT (Cerema)** | Signale l'exposition au bruit routier (contrainte de construction). | Arrêtés déc. 2023 · vérif manuelle | **OUI** — vérif amont M123 : arrêtés 2023 en vigueur *(volet aérien PEB non intégré)* | Île · 1 004 tronçons |
| **SUP — assiettes GPU (API Carto)** | Signale les servitudes d'utilité publique (contraintes réglementaires). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — GPU, non datable auto | Île · 417 assiettes |
| **Zonage SAFER (DAAF)** | Signale les terres à vocation agricole (droit de préemption SAFER). | Proxy RPG/IGN · vérif manuelle | **NON VÉRIFIABLE** — source DAAF non publique, proxy RPG | Île · 38 460 emprises (proxy) |
| **50 pas géométriques — limite haute (DEAL)** | Signale la zone des 50 pas géométriques (régime foncier littoral spécifique). | Cadastre 1877 (géoréf. 2012) · vérif manuelle | **NON VÉRIFIABLE** — limite historique figée | Île · 163 emprises |
| **ABF / Monuments historiques** | Signale les abords de monuments (avis Architecte des Bâtiments de France). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — base Mérimée, endpoint décommissionné *(covisibilité non instruite)* | Île · 200 périmètres |
| **SAR Réunion (PEIGEO)** | Signale les grandes orientations du Schéma d'Aménagement Régional (informatif). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — PEIGEO host down, fallback Région ODS | Île · 2 453 emprises (proxy) |
| **data.regionreunion.com — Potentiel foncier** | Signale un potentiel foncier repéré par la Région (bonus informatif). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — Région ODS, non datable auto | Île · 2 453 emprises |
| **GPU — zonages d'assainissement** | Informe : le mode d'assainissement de la zone (collectif / individuel). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — GPU, couverture SIG producteur partielle | **4/24** en SIG · 258 zones *(20 communes en repli taux)* |

---

## C. Elles repèrent le propriétaire et filtrent

| Source | Utilité | Fraîcheur | Dernière version dispo ? | Couverture |
|---|---|---|---|---|
| **BODACC (procédures collectives)** | Repère les propriétaires en procédure collective (redressement, liquidation) — sert de **filtre** et de bonus de contexte. | **Sonde auto** quotidienne | **NON** — nouvelle publication amont détectée | Île · 1 418 propriétaires |
| **INPI RNE (dirigeants)** | Repère l'âge du dirigeant d'une société propriétaire (indice de transmission) — bonus de contexte + fiche. | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — INPI, endpoint non sondable (404) | Île · 9 730 enrichissements |
| **DGFiP — parcelles des personnes morales** | Repère les parcelles détenues par une personne morale (société) — sert de **filtre**. | Millésime 2025 · vérif manuelle | **NON VÉRIFIABLE** — DGFiP, prochaine livraison non datable | **24/24** · 82 701 parcelles |
| **Recherche d'entreprises (DINUM)** | Informe la fiche : identité de la société propriétaire (raison sociale, état). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — API DINUM en continu, sans millésime | Île · via 9 730 enrichissements |
| **SIRENE** | Informe la fiche : rattachement de l'établissement propriétaire (indirect, via Recherche d'entreprises). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — INSEE/annuaire en continu | Indirect |
| **DPE ADEME (logements existants)** | Prévu pour l'étiquette énergie (passoires) — **quasi vide au 974**, sert nulle part aujourd'hui. | **Sonde auto** hebdo | **OUI** (sonde à jour) — *mais source amont quasi vide : 17 logements, 2 passoires* | Île · 17 lignes (**fantôme**) |
| **NPNRU (DEAL / ANCT)** | Repère les quartiers du renouvellement urbain (opportunité / filtre) + fiche. | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — DEAL/ANCT, liste non datable auto | 8 quartiers |
| **Inventaire SRU (DHUP)** | Repère la carence en logement social de la commune (contexte de pression). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — DHUP, bilan annuel non daté en base | **24/24** communes |

---

## D. Elles informent la fiche (contexte, accès, fiscal, ANC)

| Source | Utilité | Fraîcheur | Dernière version dispo ? | Couverture |
|---|---|---|---|---|
| **Cadastre — canal Etalab bulk** | Le **socle** : la géométrie et la référence de chaque parcelle (tout part de là). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — IGN/Etalab, millésime non daté en base | **24/24** · 431 663 parcelles |
| **Base Adresse Nationale** | Informe la fiche : géocode et affiche l'adresse de la parcelle. | Last-Modified 17/08/2026 · **sonde auto** mensuelle | **NON** — nouvelle publication amont détectée | **24/24** · 416 357 adresses (96 %) |
| **Contours IRIS (IGN/INSEE)** | Informe la fiche : maille statistique pour le taux d'assainissement du secteur. | Géographie 2024 · vérif manuelle | **NON VÉRIFIABLE** — IGN/INSEE, prochaine géo non datable | Île · 344 IRIS |
| **Office de l'eau Réunion — Chroniques de l'eau** | Informe la fiche : taux d'assainissement à l'échelle commune (donnée fine, quelques communes). | Chronique n°149 — données 2023 · vérif manuelle | **NON VÉRIFIABLE** — Office de l'eau, prochaine chronique non datable | **6 communes** |
| **INSEE RP2022 — détail Logements (EGOUL)** | Informe la fiche : structure du parc de logements (base du taux ANC). | RP2022, publié 16/10/2025 · vérif manuelle | **NON VÉRIFIABLE** — INSEE, prochaine vague RP non datable | Île · 330 IRIS |
| **INSEE RP Logement 2023** | Informe la fiche : complément parc de logements (ANC). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — INSEE, prochaine vague non datable | À MESURER |
| **Parkings OSM (loi APER)** | Informe la fiche : parkings soumis à l'obligation d'ombrières photovoltaïques (loi APER). | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — base OSM continue, sans millésime | Île · 901 parkings (450 conformes) |
| **FRR ex-ZRR (Légifrance)** | Informe la fiche : classement France Ruralités Revitalisation (avantage fiscal). | FRR 01/07/2024 · vérif manuelle | **NON VÉRIFIABLE** — Légifrance, prochain zonage non datable auto | **24/24** communes (attribut) |
| **QPV 2024 (ANCT)** | Informe la fiche : quartier prioritaire de la ville (contexte fiscal/social). | Génération 2024 · vérif manuelle | **OUI** — vérif amont M123 : génération 2024 courante | **13/24** · 57 quartiers |
| **ZFANG (Légifrance)** | Informe la fiche : zone franche d'activité nouvelle génération (avantage fiscal). | Décret 2026-421 du 29/05/2026 · vérif manuelle | **NON VÉRIFIABLE** — Légifrance, prochain texte non datable auto | 6 communes de l'Est (attribut) |
| **PLH des 5 EPCI (extraction documentaire)** | Informe la fiche : objectifs du Programme Local de l'Habitat (contexte intercommunal). | Extraction documentaire (config) · vérif manuelle | **NON VÉRIFIABLE** — documents EPCI, révision non datable | 5 EPCI |
| **RTAA DOM (textes réglementaires)** | Informe le calcul de faisabilité : normes de construction outre-mer (référence texte). | Textes Légifrance (config) · vérif manuelle | **NON VÉRIFIABLE** — texte réglementaire de référence | Référence (île) |
| **Transport public — GTFS (PAN, 7 réseaux)** | Informe la fiche : desserte en transport en commun (arrêts, lignes). | 7 jeux PAN, màj 2025-12→2026-08 · **sonde auto** | **OUI** (sonde à jour) | 7 réseaux · À MESURER (communes desservies) |
| **OSM — transport (pôles d'échange & téléphérique)** | Informe la fiche : proximité d'un pôle d'échange multimodal. | Extraction Overpass · vérif manuelle | **NON VÉRIFIABLE** — base OSM continue, sans millésime | Île · 61 pôles · 9 956 arrêts |
| **DEAL Réunion (WMS/WFS)** | Informe la fiche : emprises ANRU et couches DEAL diverses. | Vérif manuelle (grande passe) | **NON VÉRIFIABLE** — DEAL, services non datables auto | Île · 8 emprises ANRU |
| **Sudocuh (procédures d'urbanisme)** | Informe la veille : suit les procédures PLU en cours par commune (squelette du registre de veille). | État au 31/12/2024 · vérif manuelle | **NON VÉRIFIABLE** — Sudocuh annuel, prochain état non datable auto | **24/24** (registre curaté) |

---

## Annexe — hors vitrine (le client ne les voit pas, mais elles existent en base)

**Doublons fusionnés** — même donnée qu'une ligne servie, canal masqué qui alimente réellement le moteur :

| Source (canal masqué) | Sert en réalité | Ligne vitrine qui l'affiche |
|---|---|---|
| **Cadastre Etalab (bulk DGFiP/Etalab)** | le socle `parcels` (431 663) | « Cadastre — canal Etalab bulk » |
| **RGE ALTI 5 m (IGN)** | la pente scorée (`rgealti_pente_5m`) | « RGE ALTI — canal MNT 5 m » |
| **GPU — zonages d'assainissement (info-surf typeinf 19)** | même couche GPU, canal info-surf | « GPU — zonages d'assainissement » |

**Retirées** — abandon arbitré (M123), raison écrite, reprise possible :

| Source | Raison du retrait |
|---|---|
| **EDF SEI Réunion — open data** | Amont 410 Gone (jeu retiré par EDF ~24/12/2025), aucun usage identifié. À reprendre si republié. |
| **Fichiers fonciers (Cerema)** | Convention Cerema requise (démarchage commercial interdit) → table vide. À reprendre si convention signée. |
| **Registre national des installations (ODRÉ)** | Jamais branché, aucun usage identifié. |

**Dormantes** — ingérées ou déclarées mais servies nulle part (dites dormantes, pas un faux « servi ») :

| Source | État |
|---|---|
| **PVGIS (Commission européenne)** | Signal PV candidat mort (0 validé / 23 529, feature retirée M71). Conservée, non servie. |
| **VRD / assainissement (SPANC)** | Manuel EPCI, aucune table ni chemin servi (le « VRD » du bilan est un poste de coût, pas cette source). |

**À bâtir** — au catalogue en `a_faire`, ingester inexistant (mandat propre recommandé, cf. M123) :
**BPE INSEE** (chevauche le signal d'accès déjà servi par OSM) et **ZNIEFF** (connecteur vivant, 0 donnée
ingérée). Non affichées tant qu'elles ne servent pas.

---

*Sources des mesures : `docs/audits/AUDIT_M123_SOURCES.md` (fraîcheur/couverture/branchement, radar réparé,
vérifs amont), `docs/audits/AUDIT_SOURCES_SCORE.md` (rôle dans le score), table `data_sources` + `source_radar`
en base. Généré à l'état du catalogue au 18/08/2026.*
