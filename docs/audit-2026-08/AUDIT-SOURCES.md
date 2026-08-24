# AUDIT — Page « Sources » (vitrine de la doctrine data)

**Branche** : `audit/sources` · **Date** : 2026-08-24 · **Nature** : AUDIT SEUL (aucun code modifié, un seul fichier livré).
**Postgres** : lecture STRICTE (SELECT uniquement). App laissée tourner (:8000 + vite), non redémarrée.

> Cette page est la vitrine de « chaque donnée est datée à sa source ». Une seule erreur ici décrédibilise
> l'ensemble. Audit *impitoyable* : chaque chiffre affiché a été recoupé à la base réelle et au code servant.

---

## 0. Méthode & surface

- **Surface produit** : `frontend/src/components/sources/SourcesPage.tsx` (rendu), `GET /sources` (`app.py:592-681`, sélection + fraîcheur), `POST /sources/{id}/test` (`app.py:709`, testeur), table `data_sources` (**69 lignes**, 19 colonnes dont `source_millesime` = millésime AMONT, `last_sync_at` = date d'ingestion).
- **Filtre d'affichage** : `sources_catalog.WHERE_AFFICHEES` / `est_affichee()` (doctrine M123).
- **Recoupements** : dump intégral `data_sources` ; comptes réels par table (`dvf_mutations`, `dpe_records`, `m10_permit_delais`, `cascade_results`, `dryrun_cascade_results`) ; `docs/audit-2026-08/AUDIT-COUCHES-CARTE.md` (23 couches) ; deux agents (rendu front + croisement couches↔sources).
- **Enum** : `DataSourceStatus.CONNECTE = "connecte"` (minuscule, `enums.py:59`).

**Verdict global** : le socle est **honnête** (rien d'inventé, dérivés non maquillés en sources, doublons/retirés tagués, dates lues et jamais codées). Mais **la vitrine est incohérente avec elle-même** : le compteur d'accueil annonce **58**, la page en montre **56**, et une source réellement servie (CoSIA) est **invisible partout** à cause d'un statut mal casé. Aucune donnée *fausse*, mais un **écart de comptage** et des **angles morts** (fiabilité et millésime amont non exposés) sur la page censée prouver la rigueur.

---

## 1. LE CŒUR — écart de comptage vitrine (le point qui décrédibilise)

| Mesure | Valeur | Filtre |
|---|---|---|
| Compteur **accueil** (bandeau « N sources ») | **58** | `WHERE_AFFICHEES` = `status IN ('connecte','manuel')` − DOUBLON/RETIRÉ/DORMANT (`sources_catalog.py:24`) |
| **Page** `/sources` (lignes réellement rendues) | **56** | endpoint `.where(status == CONNECTE)` **strict** (`app.py:601`) puis `est_affichee()` |
| **Écart** | **2** | les `manuel` : **Fichiers fonciers** (27) + **VRD/SPANC** (26) |

**S1 — Bandeau 58 ≠ page 56 · GRAVITÉ MOYENNE.**
Le commentaire M123 (`sources_catalog.py:15-19`) dit explicitement que la vitrine a cessé de filtrer `status='connecte'` STRICT *« car une source `manuel` câblée et alimentée était invisible — cas Fichiers fonciers »*. **Mais l'endpoint `/sources` n'a jamais adopté cette règle** : il filtre toujours `status == DataSourceStatus.CONNECTE` (`app.py:601`) et n'applique `est_affichee()` qu'en *masquage post-hoc* (`app.py:652`) — un filtre qui ne peut que RETRANCHER, jamais ré-ajouter les `manuel`. Résultat : les deux sources que M123 voulait rendre visibles sont **comptées dans le 58 mais absentes des 56 affichées**. Le chiffre de la vitrine ne correspond pas à ce qu'elle montre.
→ *Correctif candidat* : sélectionner les lignes via `WHERE_AFFICHEES` (ou `est_affichee` en amont du SELECT), pas via `status==CONNECTE` en dur. Alors page == accueil.

**S2 — CoSIA (id 83) invisible partout · GRAVITÉ MOYENNE.**
`data_sources.status = 'CONNECTE'` (MAJUSCULES) pour CoSIA — valeur **hors enum** (`CONNECTE = "connecte"`). Conséquence :
- Compte accueil (`status IN ('connecte','manuel')`) : **exclut** CoSIA → le « 58 » sous-compte de 1.
- Endpoint (`status == 'connecte'`) : **exclut** CoSIA → absente de la page.

Or CoSIA **sert** : réconciliation bâti « désaccord BD TOPO/CoSIA » (`app.py:798`, `app.py:1051`), ingérée le 2026-08-22, millésime « CoSIA 2025 (PVA juil.-août 2025, 20 cm) ». Une source servie, récente, **n'apparaît nulle part** sur la vitrine — et son `reliability_level` est vide (seule ligne sans niveau). Hygiène : casse de statut non normalisée.
→ *Correctif candidat* : `UPDATE data_sources SET status='connecte' WHERE id=83` + normaliser la casse à l'écriture (ingestion CoSIA). Le « 58 » devient « 59 ».

---

## 2. Tableau source par source (les 58 affichées + anomalies)

Colonnes : **millésime annoncé** = `source_millesime` (ou date d'ingestion si vide) · **fiab.** = `reliability_level` en base (⚠ **jamais affiché**, cf. S4) · **licence** = mention servie · **verdict**.
Légende verdict : ✓ conforme · ⚠ écart/à surveiller · ✗ faux. Les écarts *systémiques* (S1-S10) ne sont pas re-signalés ligne à ligne.

### acces
| Source | Millésime annoncé | Fiab. | Licence | V |
|---|---|---|---|---|
| Base Adresse Nationale | ingéré 2026-08-19 | vérifié | Licence Ouverte | ✓ |
| Transport public — GTFS (PAN, 7 réseaux) | 7 jeux PAN, màj 2025-12-29→2026-08-17 | vérifié | LO v2.0 | ✓ |
| OSM — transport (pôles & téléphérique) | extraction Overpass (ODbL) | à confirmer | ODbL 1.0 | ⚠ 19/61 pôles sans source (P5 couches) |

### agricole / assainissement
| Source | Millésime annoncé | Fiab. | Licence | V |
|---|---|---|---|---|
| RPG — déclarations agricoles (IGN/ASP) | proxy RPG — RPG.LATEST, **année non pinnée** | à confirmer | **à confirmer** | ⚠ millésime non figé + licence non confirmée |
| GPU — zonages assainissement (typeinf 19) | GPU idurba, SIG 4/24 au 11/07/2026 | vérifié | LO (GPU) | ✓ (⚠ homonyme id 63, cf. S10) |
| INSEE RP2022 — Logements (EGOUL) | RP2022, publié 16/10/2025 | vérifié | LO Etalab | ✓ |
| Office de l'eau — Chroniques | Chronique n°149 — données 2023 | à confirmer | **à confirmer** | ✓ démasquée (servie via ANC) ; licence ⚠ |

### attractivite / cadastre / dynamique
| Source | Millésime annoncé | Fiab. | Licence | V |
|---|---|---|---|---|
| BPE INSEE | millésime 2025 (géo. 01/01/2025) | à confirmer | LO Etalab 2.0 | ⚠ troncature couche 20 000/35 546 (P1) ; « i » 36 821 (P2) |
| Contours IRIS (IGN/INSEE) | géographie 2024 | vérifié | LO 2.0 | ✓ |
| Filosofi INSEE (carreaux 200 m) | millésime 2021 | vérifié | LO | ✓ |
| Cadastre (API Carto PCI) | PCI Parcellaire Express « latest » | vérifié | LO 2.0 | ✓ |
| SITADEL (autorisations) | 2026-06 | vérifié | LO | ✓ **recoupé : max `date_depot` = 2026-06-01** |

### economie / energie
| Source | Millésime annoncé | Fiab. | Licence | V |
|---|---|---|---|---|
| BODACC / INPI RNE / SIRENE / Recherche entreprises (DINUM) | état courant / ingérés 07-08/2026 | vérifié | LO / INPI RNE 2024 | ✓ |
| DPE ADEME (logements existants) | ingéré 2026-08-18 | vérifié | LO | ✓ **NON orpheline** — `dryrun_cascade_results` la référence **77 308×** (cf. S réfutations) |
| PVGIS (Commission européenne) | PVGIS v5.3 · SARAH3 · run builder | vérifié | **CC BY 4.0** | ✓ sert SOLAIRE via `solaire_note()` (hors cascade, cf. S9) |
| Parkings OSM (loi APER) | ingéré 2026-07-11 | à confirmer | ODbL 1.0 | ✓ |

### environnement / fiscal / foncier
| Source | Millésime annoncé | Fiab. | Licence | V |
|---|---|---|---|---|
| Forêts publiques (ONF) | BD TOPO V3 forêt publique | vérifié | LO 2.0 | ✓ |
| INPN/patrinat — espaces protégés | passe 05/07/2026 | à confirmer | **à confirmer** | ⚠ licence |
| Parc National de La Réunion (INPN) | millésime 2021 | vérifié | **à confirmer** (jeu pnrun_2021) | ⚠ licence |
| ZNIEFF (INPN/MNHN) | INPN, màj 29/08/2025 | vérifié | LO Etalab | ✓ (homonyme a_faire id 80 non affiché) |
| FRR ex-ZRR (Légifrance) | ZSAR 1978 · FRR 01/07/2024 | à confirmer | texte réglementaire | ⚠ couche `data_source_id` NULL (P4, S8) |
| QPV 2024 (ANCT) | génération 2024 | vérifié | LO | ✓ |
| ZFANG (Légifrance) | Décret 2026-421 du 29/05/2026 | vérifié | texte réglementaire | ⚠ couche `data_source_id` NULL (P4, S8) |
| Cartofriches (Cerema) | ingéré 2026-08-13 | vérifié | LO 2.0 | ✓ |

### imagerie / logement / marche / occupation_sol
| Source | Millésime annoncé | Fiab. | Licence | V |
|---|---|---|---|---|
| BD ORTHO 20 cm (IGN) | millésime 2025 (piscine, 90,7 %) | vérifié | LO Etalab (usage comm.) | ✓ |
| BD ORTHO IRC (IGN) | *(vide)* | vérifié | LO Etalab | ⚠ millésime non tracé |
| INSEE RP Logement 2023 / SRU / NPNRU / PLH | ingérés 07/2026 | vérifié | LO / docs publics | ✓ |
| DVF / valeurs foncières | géo-DVF Etalab **2021–2025** + archives DGFiP **2014–2020** | vérifié | LO + art. L.112 A LPF | ⚠ **cf. S3** (archives 2014-2020 : 0 ligne < 2021 en base ; front code « 2025–2026 » en dur) |
| CoSIA (couverture sol IA, IGN) | CoSIA 2025 (PVA 2025, 20 cm) | *(vide)* | LO 2.0 | ✗ **invisible (S2)** |
| IGN BD CARTO V5 — occupation sol | BD CARTO V5 (proxy) | à confirmer | LO 2.0 | ✓ |

### patrimoine / potentiel / proprietaire / reglement(aire)
| Source | Millésime annoncé | Fiab. | Licence | V |
|---|---|---|---|---|
| ABF / Monuments historiques | ingéré 2026-07-05 | vérifié | LO (POP) | ✓ |
| data.regionreunion.com — Potentiel foncier | *(vide)* | vérifié | **à confirmer** | ⚠ doublon possible id 9 (S10) |
| Potentiel foncier Région (Région ODS) | *(vide)* | à confirmer | **à confirmer** | ⚠ doublon possible id 15 (S10) |
| DGFiP — parcelles des personnes morales | situation 2025 | vérifié | LO v2 | ✓ |
| Fichiers fonciers (Cerema) | *(non intégré)* | sous convention | **NON INTÉGRÉ — aucune donnée** | ⚠ **comptée (58) mais absente page (56)** — S1 |
| 50 pas géométriques (DEAL) | cadastre 1877 (géoréf. 2012/1950) | à confirmer | données État — LO | ✓ |
| Classement sonore ITT (Cerema) | arrêtés déc. 2023 | vérifié | LO 2.0 | ✓ |
| SUP — assiettes GPU (API Carto) | ingéré 2026-07-10 | vérifié | LO (GPU) | ✓ |
| RTAA DOM (textes) | ingéré 2026-07-08 | vérifié | Légifrance | ✓ (licence **front en dur**, S6) |

### reseaux / risques / signal / terrain / topographie / urbanisme
| Source | Millésime annoncé | Fiab. | Licence | V |
|---|---|---|---|---|
| VRD / assainissement (SPANC) | *(vide)* | à confirmer | **à confirmer** | ⚠ **comptée (58) mais absente page (56)** — S1 |
| Cerema/GéoLittoral — érosion côtière | millésime 2018 | vérifié | LO 2.0 | ✓ |
| DEAL — PPR / aléas | PPR/PPRL approuvés 2011–2026 | vérifié | données État — LO | ✓ (licence **front en dur**, S6) |
| Géorisques (+ ICPE, cavités, mvt, sols pollués) | ingérés 07-08/2026 | vérifié | LO 2.0 | ✓ |
| OpenStreetMap / Overpass | ingéré 2026-07-06 | vérifié | ODbL 1.0 | ✓ |
| LiDAR HD — MNH 50 cm (IGN) | dalles publiées 25/06/2025 | vérifié | LO Etalab | ✓ |
| RGE ALTI 5 m / RGE ALTI | édition non enregistrée | vérifié | LO Etalab | ✓ (id 65 tagué DOUBLON, non affiché) |
| BD TOPO IGN | BD TOPO V3 — édition non enregistrée | vérifié | LO 2.0 | ✓ |
| DEAL Réunion (WMS/WFS) | NPNRU — QP génération 2024 | à confirmer | données État — LO | ✓ (licence **front en dur**, S6) |
| GPU — zonages assainissement | GPU idurba, SIG 4/24 au 11/07/2026 | vérifié | LO (GPU) | ✓ |
| Potentiel foncier Région (ODS) | *(vide)* | à confirmer | à confirmer | ⚠ cf. S10 |
| Sudocuh (procédures urbanisme) | état au 31/12/2024 | vérifié | LO 2.0 | ✓ |
| Urbanisme PLU/GPU (API Carto) | GPU/PLU par commune | vérifié | LO (GPU) | ✓ |

**Non affichées (correctement écartées)** : Cadastre Etalab (2, DOUBLON), RGE ALTI 5 m (65, DOUBLON), GPU info-surf (67, DOUBLON), ODRÉ (50, RETIRÉ 410 Gone), EDF SEI (49, RETIRÉ), Géoplateforme/PEIGEO/Région ODS/hub (HUB), ZNIEFF a_faire (80), BPE a_faire doublon-catalogue. **Tags corrects.**

---

## 3. Écarts détaillés (gravité décroissante)

**S3 — DVF : millésime annoncé ⟂ données servies · FAIBLE-MOYENNE.**
`source_millesime` annonce *« géo-DVF Etalab 2021–2025 + archives DGFiP 2014–2020 »*. Recoupement `dvf_mutations` : 2021→2025 = 29 565 lignes (cœur exact ✓), **2026 = 1 ligne isolée**, **rien avant 2021**. La mention « archives 2014–2020 » n'a **aucune ligne** dans la base auditée. En parallèle, le front code **« 2025–2026 » EN DUR** (`SourcesPage.tsx:299`, réserve méthodo prix) — un troisième millésime, non servi par la base. Trois formulations pour une même source.
→ Aligner : soit ingérer/servir les archives 2014-2020, soit retirer la mention ; sortir « 2025–2026 » du code (le lire du modèle, comme `modele.avertissement_censure`). *À confirmer en prod* (la base auditée peut ne pas porter les archives).

**S4 — `reliability_level` jamais affiché · FAIBLE.**
Les niveaux (vérifié / à confirmer) existent, sont corrects, et **ne sont jamais rendus** (`SourcesPage.tsx` — aucune occurrence). La vitrine ne peut donc pas signaler qu'une source est « à confirmer ». Sur une page qui prouve la rigueur, taire l'incertitude est un angle mort. → Exposer un badge fiabilité (au moins pour « à confirmer »).

**S5 — Licences « à confirmer » sur des sources qui nourrissent un produit commercial · MOYENNE (gouvernance, hors bug page).**
~10 sources affichées portent une licence non confirmée : RPG, Office de l'eau, INPN/patrinat, Parc National (pnrun_2021), Potentiel foncier ×2, VRD/SPANC, DEAL WMS, parkings OSM. La page est **honnête** (elle affiche « Licence à confirmer », `licence()` ne fabrique jamais un libellé — défaut sûr). Mais l'**exposition juridique** demeure : réutilisation commerciale sans droit confirmé. → Trancher chaque licence (arbitrage Vic/juridique) ; ce n'est pas un défaut de la page mais de la donnée.

**S6 — `LICENCE_PAR_SOURCE` : 7 licences codées EN DUR au front · FAIBLE.**
`SourcesPage.tsx:22-30` court-circuite `legal_notes` (la vérité base) pour DVF, INPI, PLH, RTAA DOM, DEAL WMS, DEAL PPR, 50 pas. Reformatage **cohérent aujourd'hui**, mais si `legal_notes` est corrigé en base, le front ne suivra pas → divergence latente + doctrine « rien en dur ». → Servir la licence depuis la base (ou déplacer la carte de reformatage côté back).

**S7 — Millésime amont vs ingestion : la page ne les distingue PAS · FAIBLE.**
`versionMeta()` produit **un libellé unique** (priorité `derniere_donnee` → `source_millesime` → date d'ingestion → « millésime non tracé »). Les couches, elles, exposent `source_millesime` **et** « intégré le » séparément (FIX-COUCHES P3, `/map/layers.geojson`). Le libellé de la vitrine n'est pas *faux*, mais moins granulaire que la fiche — un lecteur peut lire « jusqu'au 19/08 » ici et « intégré le 23/08 » là sans réconciliation explicite. → Afficher les deux dates distinctement, comme les « i » des couches.

**S8 — zfang / frr : source cataloguée & affichée, couche `data_source_id` NULL · FAIBLE.**
Les deux sources fiscales sont affichées, mais la couche (`spatial_layers`) ne les relie pas → la couche ne peut pas résoudre leur millésime amont (P4, déjà pointé par FIX-COUCHES). Cohérence : la vitrine annonce, la couche ne raccroche pas. → Rattacher `data_source_id` à l'ingestion `build_zfang_frr` (déjà proposé P4).

**S9 — PVGIS servie hors cascade · FAIBLE.**
PVGIS nourrit l'outil SOLAIRE (`solaire_note()`, `app.py:2935`) mais **pas** via `cascade_results.data_source_id` (0 ligne). Elle n'apparaît donc **pas** dans `_data_sources_fiche()`. Pas orpheline (elle sert), mais sa provenance n'est pas tracée dans la fiche parcelle. → Optionnel : tracer PVGIS dans la cascade solaire pour que la fiche la cite.

**S10 — Doublon potentiel non déclaré : Potentiel foncier id 9 & id 15 · FAIBLE.**
Deux entrées « potentiel foncier » Région ODS (id 9 « Potentiel foncier Région (Région ODS) » urbanisme + id 15 « data.regionreunion.com — Potentiel foncier » potentiel), **aucune taguée DOUBLON** → toutes deux affichées. À vérifier : jeux distincts ou doublon à taguer `DOUBLON de …` (comme Cadastre/RGE ALTI/GPU). → Recouper les endpoints ; taguer si identique.

---

## 4. Faux positifs réfutés (M123 / agent — vérifiés en base, écartés)

- **DPE ADEME « fantôme/orpheline »** (agent, audit M123) → **RÉFUTÉ** : `dryrun_cascade_results` (run servi) la référence **77 308 fois**. Elle alimente les fiches. (Le débat « 17 records réunionnais » est un sujet M-V distinct, pas une orpheline.)
- **PVGIS « servi ZÉRO »** (agent, M123) → **RÉFUTÉ** : sert SOLAIRE (`solaire_note`). Reclassé en S9 (hors cascade), pas orphelin.
- **Duplicatas RGE ALTI / GPU / ZNIEFF** → **écartés** : correctement tagués DOUBLON (65, 67) ou a_faire non affiché (80). Seul reste ouvert Potentiel foncier (S10).

Aucune donnée dérivée n'est maquillée en source amont (score/tiers, tva_primo « Estimé », renouvellement « Analyse LABUSE » — déclarés honnêtement). La page liste **uniquement des sources réellement ingérées**.

---

## 5. Ce qui est SAIN (à créditer)

- Compteurs d'accueil **100 % dynamiques** (aucun chiffre en dur, mesurés en base).
- Millésime amont lu de `source_millesime` (M86) ; dates d'ingestion lues d'`ingestion_runs` (jamais inventées) ; SITADEL recoupé exact (2026-06 == max réel).
- DOUBLON / RETIRÉ correctement tagués et écartés ; `SOURCES_MASQUEES` vide **cohérent** (Office de l'eau démasquée car servie via ANC).
- `licence()` a un **défaut sûr** (« Licence à confirmer », jamais un libellé fabriqué).
- Bouton `POST /sources/{id}/test` : back câblé (`app.py:709`), champ `testable` servi mais **jamais rendu** au front → code dormant (aucun risque, mais dette).

---

## 6. Correctifs candidats (par gravité — NON appliqués)

| # | Écart | Correctif candidat | Portée |
|---|---|---|---|
| S1 | Bandeau 58 ≠ page 56 | Endpoint `/sources` : sélectionner via `WHERE_AFFICHEES`/`est_affichee` (connecte ∪ manuel), pas `status==CONNECTE` strict | back (1 requête) |
| S2 | CoSIA invisible | `UPDATE data_sources SET status='connecte' WHERE id=83` + normaliser la casse à l'ingestion | data + ingestion |
| S3 | DVF millésime ⟂ données | Aligner mention archives vs base ; sortir « 2025–2026 » du front (lire du modèle) | data + front |
| S4 | Fiabilité invisible | Rendre un badge `reliability_level` (au moins « à confirmer ») | front |
| S5 | Licences à confirmer | Arbitrage juridique par source (hors page) | gouvernance |
| S6 | 7 licences front en dur | Servir la licence depuis la base | front/back |
| S7 | Amont vs ingestion fondus | Afficher les deux dates distinctes (comme « i » couches) | front |
| S8 | zfang/frr NULL | Rattacher `data_source_id` (P4) | ingestion |
| S9 | PVGIS hors cascade | Tracer PVGIS dans la cascade solaire | back |
| S10 | Potentiel foncier ×2 | Recouper, taguer DOUBLON si identique | data |

**Priorité** : S1 + S2 (cohérence du chiffre affiché — le cœur de la crédibilité). Le reste est de la transparence et de la gouvernance.

---

## 7. Conclusion

La page Sources ne **ment** pas : pas de date inventée, pas de dérivé déguisé, doublons et retraits tagués, défaut de licence sûr. Mais elle **ne se compte pas juste** — **58 annoncés, 56 montrés** (S1) — et **oublie une source qu'elle sert** (CoSIA, S2), le tout par deux défauts mécaniques (endpoint jamais aligné sur la règle M123 ; statut mal casé). Sur une vitrine dont l'unique fonction est de prouver la rigueur, ces deux écarts priment. Les autres (fiabilité et millésime amont non exposés, licences à confirmer, licences front en dur) relèvent de la **transparence** et de la **gouvernance**, pas du mensonge. **Corriger S1+S2 d'abord** : c'est le chiffre de la promesse.

*Aucun fichier hors ce rapport n'a été modifié. Aucune écriture en base. App non redémarrée.*
