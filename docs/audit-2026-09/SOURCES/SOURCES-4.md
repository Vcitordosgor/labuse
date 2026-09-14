# SOURCES-4 — le maximum de chaque source, sans exception

Branche `feat/sources-4` (depuis `main`, SOURCES-3b + TESTS-1 mergés). Worktree `~/Desktop/labuse-etat`.
Règle Vic : **tout ce qu'un producteur publie, on l'ingère** ; une seule exception, le doublon arbitré
(EDF > BD TOPO lignes, CoSIA/LiDAR > végétation, BPE > équipements) ; les autres exceptions sont
physiques (raster nu, hub, accès restreint, flux live sans schéma).

Ce mandat est vaste (≈85 sources, 70 champs « à voir » restants). Il se livre par lots, une source à la
fois ; ce qui n'est pas atteint garde son rang dans `SCHEMAS.csv` et la session suivante reprend avec
« continue SOURCES-4 ». **Aucun run, aucune bascule, aucun rescoring, aucun merge.** Les trois fichiers
du run servi ne sont jamais commités.

## Étape 0 — les deux portes (ouverture)
- `feat/sources-4` créée depuis `origin/main` (0b24bc51), arbre propre, `.env` présent.
- `labuse circuit verrous` → **24/24 verts** (V4e compris).
- `labuse circuit suite` → **3078 passed, 55 skipped** en 2 min 02.

---

## LOT 1 — surfacer ce qui dort dans `raw` — LIVRÉ

Balayage systématique des 8 tables portant une colonne `raw`
(`bodacc_procedures, catnat_arretes, dpe_records, dvf_mutations, pm_dirigeants,
pm_dirigeant_gigogne, rnic_coproprietes, sitadel_permits`). Verdict par source :

### CatNat — arrêtés de catastrophe naturelle (GASPAR / Géorisques) → **MAXIMUM**
La fiche commune ne servait qu'un **compte** (`catnat_n`). Le détail existait en base (colonnes +
`raw`) sans place à l'écran ni identifiant au registre. Surfacé :

| champ | d'où | avant | après |
|---|---|---|---|
| `type_peril` | colonne | jamais servi (agrégé en compte) | ligne par arrêté |
| `date_debut`, `date_fin`, `date_arrete` | colonnes | idem | dates par arrêté |
| `code_national_catnat` | **raw** | dormant | servi (id national de l'arrêté) |
| `date_publication_jo` | **raw** | dormant | servi (date JO) |

- **Registre** : nouvelle donnée `catnat_arretes_liste` (`liste`, commune, réservoir `catnat_gaspar`,
  passe-plat `fiche_commune.py:risques`), servie par le robinet `fiche_commune_risques` (mono-robinet).
- **Place** : fiche commune › carte **Risques** — 12 arrêtés les plus récents, « et N autres… » via le
  compte total. Backend `src/labuse/api/fiche_commune.py:risques`, front
  `frontend/src/components/contexte/ContextePanel.tsx` (bloc sous « Arrêtés CatNat »).
- **Preuve** (capture `captures-sources4/01-commune-risques-catnat-detail.png`, Saint-Denis) :
  « Arrêtés CatNat **21** · Mouvement de Terrain 2025-02-26 → 2025-03-01 · **INTE2519692A** · Vents
  Cycloniques 2025-02-26 → 2025-02-28 · INTE2508630A · … »
- **Rollout** : le volet contexte est servi depuis `commune_contexte_cache` (job nocturne
  `fiche-commune-cache`). Les **24 communes** ont été recalculées (`rafraichir_contexte_cache`, 260 s,
  0 KO) — ce n'est pas un run/bascule, c'est exactement ce que fait le job de nuit. Le détail est donc
  live sur toute l'île.

### RNIC — copropriétés (ANAH) → **MAXIMUM sur l'open data ingéré**
La fiche ne servait que 9 colonnes. Surfacé (colonne + `raw`, dans le respect de la règle RGPD :
`syndic_siret`/`syndic_nom` uniquement si syndic professionnel — garde d'ingestion `purge_rgpd`) :

| champ | d'où | après |
|---|---|---|
| `syndic_siret` | colonne (déjà en base) | servi — relie la copro à une société (personne morale) |
| `nombre_de_lots_de_stationnement` | **raw** | « N stationnement » |
| `nombre_total_de_lots_a_usage_d_habitation_de_bureaux_ou_de_comm` | **raw** | « N hab./bur./com. » |
| `residence_service` | **raw** | « résidence-service » si oui |
| `syndicat_cooperatif` | **raw** | « syndicat coopératif » si oui |

- **Place** : fiche parcelle › **Copropriété rattachée** (tiroir Propriétaire) + Dossier PDF.
  Backend `app.py:_q_v2_fiche` (SELECT élargi), front `CoproprietesBlock.tsx`, PDF
  `pdf_premium.py` § COPROPRIÉTÉ(S) RATTACHÉE(S). Donnée registre `coproprietes_liste` (inchangée,
  champs enrichis, même réservoir `rnic_anah`).
- **Preuve** (capture `captures-sources4/02-fiche-copropriete-rnic.png`, parcelle 97411000BH0670) :
  « LES JACQUIERS · 267 lots (dont 120 hab.), **117 stationnement**, 120 hab./bur./com. · syndic
  professionnel · VITRY · **SIRET 48086797700013** ».
- **Reste (LOT 2)** : **procédures** (art. 29-1…) et **étiquette énergie DPE copro** sont ABSENTES du
  jeu open data ANAH ingéré — elles exigent un export procédures/DPE-copro dédié. Ligne ajoutée à
  `SCHEMAS.csv` (verdict « à ingérer »).

### Les autres tables à `raw` — arbitrées, pas de surfacing LOT 1
- **INPI RNE** (`pm_dirigeants`) : `raw` porte l'**adresse du dirigeant**, un second rôle, la mention de
  démission. Ce sont des **données personnelles** ; la projection servie (nom, rôle, date) est le choix
  délibéré, conforme à la **licence RNE homologuée**. Verdict **PARTIEL — producteur (licence)**, pas un
  trou. Rien à surfacer sans élargir la licence.
- **DVF** (`dvf_mutations`) : `raw` ne contient que `id_mutation / source / vefa`. L'**adresse**, le
  **nombre de pièces** et les **surfaces Carrez** ne sont **PAS** en base (ni colonne, ni `raw`) — le
  mandat les rangeait dans « dort dans raw », mais la preuve dit le contraire : ils exigent une
  **ré-ingestion** de DVF+ avec capture de colonnes élargie → **LOT 2** (source déjà servie, ingestion
  autorisée pour la compléter). Documenté, non fait ici.
- **BODACC, DPE, SITADEL** : leur `raw` est riche mais correspond à des **schémas complets** listés « à
  ingérer » dans `SCHEMAS.csv` (DPE 230 champs, BODACC annonces, SITADEL détails permis) → **LOT 2**,
  pas un simple surfacing.

### Tests LOT 1
- `tests/test_sources4_lot1.py` : CatNat sert le détail (péril + 3 dates + code national + JO) ; la
  donnée `catnat_arretes_liste` est déclarée au registre et servie par un seul robinet.
- `tests/test_rnic.py::test_surface_champs_raw_stationnement_residence` : l'extraction depuis `raw`
  (même SELECT que `_q_v2_fiche`) tient — si l'ANAH renomme une clé ou la purge RGPD l'efface, ça casse.

---

## LOT 2 — ingérer tout ce qui manque — NON COMMENCÉ (rang conservé)
`SCHEMAS.csv` liste ~70 champs « à voir »/« à ingérer », ordonnés par utilité (mandat § LOT 2).
Ordre imposé : ICPE → SRU → CoSIA → Cartofriches → BPE → Parc national ; puis REI, BODACC, Fibre
Arcep, Loyers DHUP, DFI, Sudocuh, RP Logement, RPLS ; puis classement sonore, EDF HTA, OSM, AZI/TRI,
mvt/cavités/sols pollués/CASIAS/SIS, Mérimée, Conso NAF, personnes morales, SITADEL, Potentiel foncier,
GéoLittoral, ONF, INPN, ZNIEFF, EGOUL, DILA ; puis BD TOPO (thèmes non-doublons), BD CARTO, cadastre
d'époque. Chaque ingestion : filtre 974 au plus tôt, garde 974, sonde, registre, sentinelle, place ou
`raw`+mention. **Amorce identifiée** : DVF+ (adresse/pièces/Carrez) est le premier candidat naturel
(source déjà servie, colonnes à élargir).

## LOT 3 — cinq comparaisons DEAL — NON COMMENCÉ (rang conservé)
`DescribeFeatureType` sur PPR/aléas, cartes de bruit, ravines DPF, zones humides, Ramsar (Lizmap/Carmen).

## LOT 4 — verdict final + verrou G2 étendu — NON COMMENCÉ (rang conservé)
`SCHEMAS.csv` sans plus aucun « à voir » ; tableau des 93 en deux verdicts ; extension G2 (« une source
servie ne porte aucun champ à voir de plus de 30 jours »).

---

## Champs écartés comme doublons (règle G1)
Aucun nouveau doublon arbitré dans ce lot (LOT 1 ne fait que surfacer des champs déjà en base, sans
nouvelle source). Les arbitrages de doublon (EDF > BD TOPO lignes, CoSIA/LiDAR > végétation, BPE >
équipements) restent à écrire au fil des ingestions BD TOPO/BD CARTO du LOT 2.

## Sources arrêtées sur seuil (10 Go / 2 h)
Aucune — LOT 1 n'ingère rien (surfacing de base existante).

## Les deux portes à la clôture du LOT 1
- `labuse circuit verrous` → **24/24 verts** (V5a/b/c et G1–G7 compris, +1 donnée `catnat_arretes_liste`).
- `labuse circuit suite` → à rejouer (voir commit). vitest **207 passed**, tsc **0**.

**Rien n'est mergé.**
