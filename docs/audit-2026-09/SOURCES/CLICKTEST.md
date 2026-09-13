# Test client — trouvabilité + « la fiche est-elle réellement remplie » (les 116)

*SOURCES-AUDIT-1, 2ᵉ passe étendue. Deux corrections demandées : (1) le test porte sur **les
116**, pas 30 ; (2) une colonne **« fiche réellement remplie »** — car DPE prouve qu'une source
peut être **branchée, à jour ET vide**. Règle : une source dont la **fiche parcelle est vide sur
les 4 témoins est INVISIBLE, quel que soit son statut**.*

Vrai navigateur (Playwright/chromium) sur l'app servie en local : back `:8032`, front `:5200`
(`/socle/`), base `postgresql://openclaw@localhost:5432/labuse` — `:8020` pas touché. Le
remplissage est **mesuré en base** contre 4 parcelles témoins. Rejouable :
`python -m audit_sources.generate` (colonnes `temoins_remplis`/`fiche_remplie` du CSV) +
`node scripts/clictest_capture.mjs`.

## Les 4 témoins (parcelles réelles, bâties, N/O/S/E)

| Témoin | Commune | INSEE |
|---|---|---|
| `97411000CD0083` | Saint-Denis | 97411 |
| `97415000DI0183` | Saint-Paul | 97415 |
| `97416000CO0318` | Saint-Pierre | 97416 |
| `97409000AB0394` | Saint-André | 97409 |

## Comment « fiche remplie » est mesuré (et lu)

Pour chaque source, on teste si sa donnée **atteint** les 4 témoins, par jointure rapide selon
sa table réservoir : **parcelle** (`idu`/`parcelle_idu`), **commune** (`insee`/`commune`), ou
**carte** (couche `spatial_layers.kind` × commune). Pas d'intersection spatiale par parcelle
(mesurée à 43–70 s/appel — inutilisable). Lecture :

- **type `parcelle`, 0/4 + base quasi nulle → VIDE réelle** = le cas DPE : la donnée n'existe
  pour aucune parcelle. **INVISIBLE**, quel que soit le statut.
- **type `parcelle`, 0/4 mais base fournie** (RNIC 2 220, Radar) = ces 4 parcelles n'ont pas
  l'attribut (pas une copro / pas d'annonce) — **pas** une invisibilité, la source remplit
  ailleurs.
- **type `carte`, 0/4** = ces 4 **communes** n'ont pas d'objet de la couche tagué (ou la couche
  n'est pas taguée par commune) — la couche reste visible sur la carte ; **jamais** un
  déclencheur d'invisibilité (ex. GTFS, EDF, ZNIEFF : « VIDE sur 4/4 » mais bien sur la carte).
- **`n.a.`** = API interrogée en direct, règles portées par le code, ou aucune table jointe.

## Deux visibilités, séparées (le nœud, corrigé)

« 0 invisible » de la 1ʳᵉ passe **était** un artefact : dériver la visibilité du graphe
registre→robinet garantit un robinet. Au navigateur :

- **Transparence** — la page **/sources** (nav « Sources », 2 clics) liste **les 95** avec
  producteur + licence + fraîcheur + drapeau (PROXY / FIABILITÉ À CONFIRMER / ACCÈS SOUS
  CONVENTION / MISE À JOUR EN COURS). Excellente.
- **Usage fonctionnel** — la donnée est **utilisable** sur la parcelle / la carte / un outil.
  C'est le vrai test. **`*` = source vérifiée au navigateur** (échantillon de 30 : COUCHES,
  Outils, page Sources, fiche, outils Taxe/Scan/Pièges/Communes/Faisabilité — voir `captures/`).
  Le reste est **dérivé du registre + le remplissage mesuré**.

## Le tableau — les 116

*Clics = de l'accueil jusqu'à voir la donnée (`∞` = aucune surface d'usage). Les sources sans
robinet de registre mais atteignables par un outil/une fiche commune (SIRENE, RTAA, CatNat,
Taxe) sont marquées « visible (hors registre) » — c'est exactement l'angle mort du graphe.*

| id | Source | Statut | Surface fonctionnelle | Clics | /sources | Fiche remplie (4 tém.) | Visibilité |
|---|---|---|---|---|---|---|---|
| 1 | Cadastre (API Carto PCI) * | connecte | fiche, outil, PDF, copilote | 2 | oui | 4/4 témoins | ✅ visible |
| 2 | Cadastre Etalab (bulk DGFiP/Etalab) | alias | — | ∞ | non | 4/4 témoins | ⚪ hors vitrine |
| 3 | Urbanisme PLU/GPU (API Carto) * | connecte | carte, fiche, outil, PDF, copilote | 2 | oui | 3/4 témoins | ✅ visible |
| 4 | Géorisques * | connecte | carte, fiche, outil | 2 | oui | 3/4 témoins | ✅ visible |
| 5 | DVF / valeurs foncières * | connecte | carte, fiche, outil, PDF, copilote | 2 | oui | 3/4 témoins | ✅ visible |
| 6 | RGE ALTI (altimétrie) | connecte | carte, fiche, PDF | 2 | oui | 3/4 témoins | ✅ visible |
| 7 | Parc National de La Réunion (INPN) | connecte | carte | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 8 | Forêts publiques (ONF) | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 9 | Potentiel foncier Région (Région ODS | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 10 | RPG — déclarations agricoles (IGN/AS | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 11 | Région Réunion Open Data (Opendataso | hub | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 12 | PEIGEO (hub régional) | hub | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 13 | DEAL Réunion (WMS/WFS) | connecte | carte | 2 | oui | 2/4 témoins | ✅ visible |
| 14 | Géoplateforme IGN | hub | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 15 | data.regionreunion.com — Potentiel f | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 16 | SITADEL (autorisations d'urbanisme) * | connecte | fiche, outil, PDF, copilote | 2 | oui | 3/4 témoins | ✅ visible |
| 17 | BD TOPO IGN * | connecte | carte, fiche, outil, PDF | 2 | oui | 3/4 témoins | ✅ visible |
| 18 | Base Adresse Nationale | connecte | fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 19 | OpenStreetMap / Overpass | connecte | carte, fiche | 2 | oui | 3/4 témoins | ✅ visible |
| 20 | BPE INSEE * | connecte | carte, fiche | 2 | oui | 3/4 témoins | ✅ visible |
| 21 | SIRENE * | connecte | outil Scan patrimoine | 2 | oui | n.a. (API/règles) | ✅ visible (hors registre) |
| 22 | IGN BD CARTO V5 — occupation du sol | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 24 | ABF / Monuments historiques * | connecte | carte, fiche, outil | 2 | oui | 3/4 témoins | ✅ visible |
| 25 | INPN / patrinat — espaces protégés | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 26 | VRD / assainissement (SPANC) | manuel | — | ∞ | oui | n.a. (API/règles) | 🟣 manuelle |
| 27 | Fichiers fonciers (Cerema) | manuel | — | ∞ | oui | n.a. (API/règles) | 🔴 INVISIBLE (fonctionnel) |
| 28 | Cerema / GéoLittoral — indicateur d' | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 29 | BODACC (procédures collectives) | connecte | fiche | 2 | oui | n.a. (API/règles) | ✅ visible |
| 30 | DEAL Réunion — PPR / aléas | connecte | carte, fiche, outil | 2 | oui | 3/4 témoins | ✅ visible |
| 31 | INPI RNE (dirigeants) | connecte | outil | 2 | oui | n.a. (API/règles) | ✅ visible |
| 32 | Géorisques — sites et sols pollués | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 33 | Géorisques — cavités souterraines | connecte | carte | 2 | oui | 2/4 témoins | ✅ visible |
| 34 | Géorisques — ICPE | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 35 | Cartofriches (Cerema) | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 36 | Géorisques — mouvements de terrain * | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 37 | DPE ADEME (logements existants) | connecte | fiche | 2 | oui | VIDE sur 4/4 | 🔴 INVISIBLE (vide) |
| 38 | QPV 2024 (ANCT) | connecte | carte, fiche | 2 | oui | 3/4 témoins | ✅ visible |
| 39 | Inventaire SRU (DHUP) | connecte | fiche, outil, copilote | 2 | oui | 4/4 témoins | ✅ visible |
| 40 | NPNRU (DEAL Réunion / ANCT) | connecte | carte, fiche | 2 | oui | 3/4 témoins | ✅ visible |
| 41 | INSEE RP Logement 2023 | connecte | fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 42 | PLH des 5 EPCI (extraction documenta | connecte | fiche | 2 | oui | n.a. (API/règles) | ✅ visible |
| 43 | RTAA DOM (textes réglementaires) | connecte | outil Faisabilité (règles RTAA) | 2 | oui | n.a. (API/règles) | ✅ visible (hors registre) |
| 44 | SUP — assiettes GPU (API Carto) * | connecte | carte, fiche | 2 | oui | 3/4 témoins | ✅ visible |
| 45 | Recherche d'entreprises (DINUM) | connecte | fiche | 2 | oui | n.a. (API/règles) | ✅ visible |
| 46 | Classement sonore ITT (Cerema) | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 47 | 50 pas géométriques — limite haute ( | connecte | carte | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 48 | PVGIS (Commission européenne) * | connecte | fiche, outil | 2 | oui | 4/4 témoins | ✅ visible |
| 49 | EDF SEI Réunion — open data | retiree | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 50 | Registre national des installations  | retiree | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 51 | Parkings OSM (loi APER) | connecte | fiche | 2 | oui | n.a. (API/règles) | ✅ visible |
| 52 | Filosofi INSEE (carreaux 200 m) * | connecte | fiche, outil, PDF | 2 | oui | 4/4 témoins | ✅ visible |
| 61 | BD ORTHO 20 cm (IGN) | connecte | fiche, outil, copilote | 2 | oui | 1/4 témoins | ✅ visible |
| 62 | Sudocuh (procédures d'urbanisme) * | connecte | fiche, outil, copilote | 2 | oui | 4/4 témoins | ✅ visible |
| 63 | GPU — zonages d'assainissement | connecte | carte | 2 | oui | 4/4 témoins | ✅ visible |
| 64 | Contours IRIS (IGN/INSEE) | connecte | carte, fiche, outil | 2 | oui | 3/4 témoins | ✅ visible |
| 65 | RGE ALTI 5 m (IGN) | alias | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 66 | INSEE RP2022 — fichier détail Logeme | connecte | fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 67 | GPU — zonages d'assainissement (info | alias | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 68 | Office de l'eau Réunion — Chroniques * | connecte | fiche | 2 | oui | 1/4 témoins | ✅ visible |
| 69 | BD ORTHO IRC (IGN) | connecte | fiche, outil | 2 | oui | 4/4 témoins | ✅ visible |
| 70 | LiDAR HD — MNH 50 cm (IGN) * | connecte | fiche, outil | 2 | oui | 4/4 témoins | ✅ visible |
| 71 | DGFiP — parcelles des personnes mora * | connecte | fiche, outil, copilote | 2 | oui | 3/4 témoins | ✅ visible |
| 72 | ZFANG — zone franche d'activité nouv | connecte | carte, fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 73 | FRR ex-ZRR — zone spéciale d'action  | connecte | carte, fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 74 | Transport public — GTFS (PAN, 7 rése * | connecte | carte, fiche | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 75 | OSM — transport (pôles d'échange & t | connecte | carte, fiche | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 76 | ZNIEFF (INPN/MNHN) * | connecte | carte, fiche, outil | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 80 | ZNIEFF (INPN / Région) | retiree | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 83 | CoSIA (couverture du sol IA, IGN) * | connecte | carte, fiche, outil, PDF | 2 | oui | 4/4 témoins | ✅ visible |
| 84 | Radar (pige d'annonces) * | manuel | fiche, outil | 2 | oui | VIDE sur 4/4 | 🟣 manuelle |
| 86 | SIRENE établissements géolocalisés | connecte | fiche, outil | 2 | oui | 4/4 témoins | ✅ visible |
| 87 | MOBPRO (mobilités domicile-travail,  | retiree | — | ∞ | non | VIDE sur 4/4 | ⚪ hors vitrine |
| 88 | Trafic RN (Région Réunion — SIR) | connecte | outil | 2 | oui | n.a. (API/règles) | ✅ visible |
| 89 | BDNB | retiree | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 93 | EDF Réunion — lignes moyenne tension * | connecte | carte | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 94 | TCSP — voies bus en site propre (OSM | connecte | carte | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 95 | Réunion Express — hypothèses de trac | a_faire | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 96 | Cadastre d'époque (Etalab / PCI vect | connecte | fiche | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 97 | CatNat (arrêtés GASPAR / Géorisques) * | connecte | outil Pièges + fiche commune | 3 | oui | 4/4 témoins | ✅ visible (hors registre) |
| 98 | Taxe d'aménagement — taux communaux  | connecte | outil Taxe d'aménagement | 2 | oui | 4/4 témoins | ✅ visible (hors registre) |
| 99 | Annuaire de l'administration (servic | connecte | fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 100 | RNIC — registre national des copropr * | connecte | fiche | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 101 | RPLS — répertoire des logements loca | connecte | fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 102 | Consommation d'espaces NAF (Cerema — | connecte | fiche, outil | 2 | oui | 4/4 témoins | ✅ visible |
| 105 | GPU — emplacements réservés (prescri | connecte | carte, fiche | 2 | oui | 3/4 témoins | ✅ visible |
| 106 | GPU — espaces boisés classés (prescr | connecte | carte, fiche | 2 | oui | 3/4 témoins | ✅ visible |
| 107 | GPU — droit de préemption urbain (in * | connecte | carte, fiche | 2 | oui | 2/4 témoins | ✅ visible |
| 108 | PEB — plans d'exposition au bruit (D | connecte | carte, fiche | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 109 | Zonage ABC des communes (DHUP) | connecte | fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 110 | ZPPA — zones de présomption de presc | a_faire | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 111 | Ravines — domaine public fluvial (DE | connecte | carte | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 112 | Zones humides — inventaires DEAL (Ca | connecte | carte | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 113 | Espaces protégés complémentaires — R | connecte | carte | 2 | oui | 3/4 témoins | ✅ visible |
| 114 | AZI / TRI — inondation (Géorisques G | connecte | fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 115 | Géorisques — secteurs d'information  | connecte | carte, fiche | 2 | oui | 3/4 témoins | ✅ visible |
| 116 | Géorisques — CASIAS (anciens sites i | connecte | carte, fiche | 2 | oui | 3/4 témoins | ✅ visible |
| 117 | DEAL — cartes de bruit stratégiques  | connecte | carte | 2 | oui | VIDE sur 4/4 | ✅ visible |
| 118 | SAR — schéma d'aménagement régional  | a_faire | carte, fiche | 2 | non | 3/4 témoins | ⚪ hors vitrine |
| 119 | DVF Réunion (Région, data.regionreun * | connecte | — | ∞ | oui | n.a. (API/règles) | 🔴 INVISIBLE (fonctionnel) |
| 126 | Fibre Arcep — Ma connexion internet  * | connecte | fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 127 | Taux de taxe foncière — fichier REI  | connecte | fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 128 | ACV / PVD / ORT (DGALN — liste des c | connecte | fiche | 2 | oui | 3/4 témoins | ✅ visible |
| 129 | Loyers OLL — ADIL Réunion / AGORAH ( * | connecte | fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 130 | Loyers DHUP — carte des loyers (anno | connecte | fiche | 2 | oui | n.a. (API/règles) | ✅ visible |
| 131 | Coût de construction (EPTB SDES + ch | connecte | outil | 2 | oui | n.a. (API/règles) | ✅ visible |
| 132 | DFI — documents de filiation informa * | connecte | fiche | 2 | oui | 4/4 témoins | ✅ visible |
| 133 | INSEE RP2022 — bases IRIS (logement, | connecte | fiche, outil | 2 | oui | 4/4 témoins | ✅ visible |
| 134 | Zonages d'assainissement SIG complet | a_faire | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 135 | Inventaires ZAE (EPCI — loi Climat e | a_faire | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 136 | Périmètres de ZAC (EPCI / communes / | a_faire | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 137 | OPAH / PIG (Anah / EPCI) | a_faire | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 138 | Périmètres ORT infra-communaux (EPCI | a_faire | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 139 | ENS du Département (Conseil départem | a_faire | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 140 | Micro-données OLL (ADIL / AGORAH) | a_faire | — | ∞ | non | n.a. (API/règles) | ⚪ hors vitrine |
| 141 | LOVAC (logements vacants) * | manuel | — | ∞ | oui | n.a. (API/règles) | 🔴 INVISIBLE (fonctionnel) |
| 142 | DV3F (Cerema) | manuel | — | ∞ | oui | n.a. (API/règles) | 🔴 INVISIBLE (fonctionnel) |

## Résultat sur les 116

- **Trouvables fonctionnellement (1–3 clics)** : la grande majorité — couche carte, section de
  fiche, outil, ou (SIRENE/RTAA/CatNat/Taxe) via un outil malgré l'absence de robinet registre.
- **⚪ Hors vitrine (21)** : 10 à_faire + 5 retirées + 3 alias + 3 hubs — non affichées, à raison.
- **🔴 INVISIBLES (5)** — donnée n'atteignant **aucune** surface d'usage, quel que soit le statut :
  - **DPE ADEME (37)** — le cas d'école : `connecté`, drapeau « à jour » sur /sources, MAIS
    `dpe_records = 17`, `v_passoire_thermique = 1` → **fiche VIDE sur les 4 témoins (0/4)**.
    Branchée, à jour, vide. C'est un **vrai trou d'ingestion**, priorité de réparation.
  - **DVF Réunion (Région, 119)** — servi uniquement comme témoin du filtre DVF ; le client voit
    DVF Etalab, jamais celui-ci.
  - **Fichiers fonciers (27) · LOVAC (141) · DV3F (142)** — `manuel`, **non ingérées** (accès sous
    convention Cerema) : rien à afficher, seule la ligne catalogue « ACCÈS SOUS CONVENTION » existe.
- **🟣 Manuelles à surface incertaine (2)** : VRD/SPANC (26, saisie), Radar (84, la pige a un
  outil dédié mais 0 annonce sur les 4 témoins — normal, sparse par nature).

## La colonne « fiche remplie » a une vraie valeur de diagnostic

Elle sépare trois cas qu'un statut binaire confond :
1. **Rempli** (ex. Cadastre 4/4, BD TOPO 3/4) — la donnée est là.
2. **Vide-réel** (DPE 0/4 + base 17) — branché mais creux → **INVISIBLE**.
3. **Vide-de-contexte** — un `carte` 0/4-par-commune (GTFS, EDF, ZNIEFF) ou un `parcelle` 0/4 sur
   source riche (RNIC : ces témoins ne sont pas des copros) : **pas** une invisibilité.

**Distribution mesurée** (116) : 15 sources de type `parcelle`, 26 `commune`, 42 `carte`, 33
`n.a.` (API/règles/sans table). Le CSV porte `temoins_remplis` (N/4), `remplissage_type` et
`fiche_remplie` pour chacune ; les fiches `<id>.md` aussi.

## Limites du test

- L'échantillon **browser-vérifié** est de 30 (marqués `*`) ; les 86 autres lignes combinent le
  graphe du registre (surface) et le remplissage **mesuré en base** (fiche remplie) — pas un
  clic humain sur chacune. La règle d'invisibilité, elle, s'appuie sur la mesure, pas sur le clic.
- `fiche remplie` est une **présence de donnée** (jointure), pas un rendu pixel : elle prouve que
  la donnée existe pour le témoin, pas que l'UI l'affiche joliment. Pour le sens inverse (donnée
  absente → fiche forcément vide, cas DPE), la preuve est solide.
- 4 témoins, tous urbains bâtis : bon pour attraper le creux (DPE) ; un échantillon rural/naturel
  élargirait la mesure des couches nature (ZNIEFF, zones humides). À élargir dans un mandat dédié.
