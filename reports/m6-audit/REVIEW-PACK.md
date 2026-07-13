# M6 — REVIEW PACK Phases 2a + 2b (GO Vic du 13/07/2026, garde-fous renforcés)

Branche `audit/grand-check` — **aucun merge** ; chaque correction = un commit atomique.
Sections d'audit Phase 1 : `reports/m6-audit/sections/` (committées). Ce pack = delta 2a,
delta statuts 2b, échantillons vérifiés, captures, compteurs avant/après.

## Garde-fous (état)

| Garde-fou | État |
|---|---|
| Snapshot gelé AVANT 2b (état post-2a) | ✅ `m6_snapshot_mvt_post2a` (431 663 lignes) + label cascade `q_v4_m6a` immuable + snapshot v2 `m5-2026-07-12` inchangé |
| Commits atomiques par correction | ✅ un commit par critère (voir « Journal des commits ») |
| Seuil 15 000 parcelles retirées (A-01) | ✅ 1 254 réelles (prévu 1 297) |
| Seuil 10 % de bascule de tiers (2b) | ⏳ contrôlé au delta 2b (run en cours) |
| Doute d'interprétation PLU | ✅ un seul levé : identité d'A-03 — tranché par Vic (zones « e » Saint-Paul) |

---

## PHASE 2a

### A-01 (P0) — Emprise routière / équipements publics

**Diagnostic** : aucune fuite « propriétaire public » dans l'univers servi (l'étage 0
`foncier_public` couvre déjà les propriétaires PM connus, requête au pack). La fuite = parcelles
**routières sans fiche PM** (voirie communale non recensée au fichier PM 2024, rétrocessions).

**Critère technique documenté** (couche étage 0 `emprise_routiere`, `etage0_ext.py`) :
1. axes routiers BD TOPO carrossables **dédoublonnés md5** (M6-01), longueur clippée ≥ 30 m ;
2. densité d'emprise (longueur × 6 m nominale / surface) ≥ 0,5 ;
3. emprise bâtie dédoublonnée < 10 % ;
4. **aucun signal privé** (ni PM privée propriétaire, ni mutation DVF 2014-2025) → HARD_EXCLUDE ;
   **avec signal privé** → SOFT_FLAG « voirie/délaissé privé potentiel », parcelle **CONSERVÉE**.

**Échantillon de 20 vérifié à l'œil AVANT application** (vignettes ortho IGN + contour parcelle +
axes, jointes : `captures-2a-a01/ortho-*.png`) : **18/20 emprises viaires confirmées** (ruelles,
dessertes, réseaux internes de lotissements — Le Port BA0396 = tout le réseau viaire d'une cité) ;
**2 douteuses** (IE1899 bâti 22 %, DZ0456 bâti 14 %, toutes deux Saint-Pierre : parcelle bâtie
traversée par un axe BD TOPO mal calé) → **garde-fou bâti < 10 % calibré sur l'échantillon**
(confirmées toutes ≤ 8,8 %) qui les écarte exactement.

**Chiffres (run `q_v4_m6a`, delta vs `q_v3_datagap`)** :

| Indicateur | Valeur |
|---|---|
| Nouvelles entrées à l'étage 0 | **1 254** (1 237 à creuser, 15 réserve foncière, 2 chaudes routières, **0 brûlante**) |
| Sorties d'étage 0 | 0 |
| Délaissés privés flagués et CONSERVÉS (comptés à part) | **2 155** (dont 1 076 PM privée + 184 mutation DVF sur l'univers servi) |
| Classification complète | `sections/2a-a01-voirie-classification.csv` (2 631 lignes) |
| Compteurs v2 avant → après | brûlantes 117 → **117** · chaudes 960 → 958 · réserve 3 607 → 3 592 · à creuser 74 359 → 73 122 |

Contrôles post-bascule : golden dataset **32/32 PASS** ; `/stats` SQL-exact.

### P1 (tous traités, P1-07 Mutabilité exclu comme demandé)

| Correction | Contenu | Preuve |
|---|---|---|
| BAN partout | API : fiche, liste paginée, geojson commune, omnibox, CRM/pipeline, CSV (LATERAL après pagination, +0,03 s liste île) ; UI : tête de fiche + cartes de résultats ; « Adresse non disponible » sinon | `captures-2a/fiche-adresse-disclaimer.png`, `cartes-adresse.png` |
| Disclaimer CU | « Ces informations ne remplacent pas un certificat d'urbanisme. » AU MOT PRÈS : fiche (pied), PDF (pied commun), rapport Flash (mentions), page pilote, **CGU créées** (`docs/legal/CGU.md` — rédaction juridique complète à valider avant commercialisation) | idem + `exports-samples/2a/` |
| Encodage CSV | utf-8-sig (BOM Excel) + séparateur `;` + colonnes adresse/CP/ville | `exports-samples/2a/liste-trois-bassins.csv` |
| États vides | couche ANRU vide → toast explicite (A3) ; entonnoir sans motifs → mention dédiée | code + captures |
| Footer PDF | pied commun (`export_commun.py`) : non-garantie + CU + attributions sources + date + pagination | `exports-samples/2a/fiche-*.pdf` |
| Attributions licences | page Sources : licences réelles (plus de « Données publiques »), lien vers le texte, ligne d'attribution, INPI avec date de MAJ (art. 2.4) ; base `legal_notes` remplie (UPDATE + rollback) ; « à confirmer » honnêtes (SAR/PEIGEO/Région ODS) | `captures-2a/sources-attributions.png` (52 licences, 38 attributions) |
| P1-03 Baromètre | critère outliers documenté (Vente stricte, > 1 000 €, bande €/m²) sur médianes ET volumes + ventilation « écartées » exposée (2 007 = VEFA 1 407 + natures 260 + symboliques 26 + ratios 314) ; **fix racine** surfaces geo-DVF (dédoublonnage par local) + re-fabrication des 1 440 surfaces gonflées (backup + rollback) ; échantillon 20/20 vérifié + avant/après 3 communes | `sections/2a-p1-03-barometre.md` |

### P0 complémentaires du rapport (validés dans « les 3 P0 »)

- **Flash/Dossier raconte le v2** : verdict tier v2 en tête (étage 0 prime, rang île, ×N), grille
  matrice reléguée « historique » — plus jamais deux vérités (preuve `exports-samples/2a/flash-AB1908.html`).
- **Module Division respecte l'étage 0** (M6-INC-03) : parcelles en exclusion dure retirées du
  gisement + compteur `etage0_exclus` (Saint-Paul : 322 exclues, témoin AS0899 « score 92 en PPR
  rouge » disparu).

### Fixes triviaux au fil de l'eau (listés)

- `tests/test_shortlist.py` : libellé badge « À creuser » (lexique v2 M5.1, test non mis à jour).

### Incidents d'exécution (transparence)

- 4 agents P1 morts sur limite de session → travail repris, vérifié ligne à ligne, complété
  (branchement licence/attribution SourcesPage, Flash v2, division étage 0, front BAN) et committé.
- Matrice 97402 : 56 min (plan Postgres sur stats obsolètes après création du nouveau label) →
  `ANALYZE` → 0,9 s. **Consigne opérationnelle** : ANALYZE des tables dryrun après création d'un
  label (intégré au script de run 2b) — candidat fix CLI au backlog.
- Couche A-01 : 50 ms/parcelle au premier profil → sonde EXISTS → 1,4 ms (commit dédié).
- PDF « 500 » de l'audit = env conda sans fpdf2/WeasyPrint ; l'env canonique est `.venv`
  (les PDF y passent) — à documenter au déploiement.

---

## PHASE 2b (enchaînée sans STOP 2, garde-fous armés)

### A-02 — Doublons PLU inter-communes

- **Base** : 458 zones + 7 275 prescriptions supprimées (copies « débordement bbox » des documents
  voisins ; règle de conservation VÉRIFIÉE : `attrs.partition = DU_<insee de la commune>`) ;
  sauvegarde `m6_a02_backup_plu_dup`, rollback `sql/a02_dedup_plu_rollback.sql`.
  9 groupes sans exemplaire légitime non touchés (consignés).
- **Ingestion** : garde ajoutée (`layers_ingest.py`) — zones et prescriptions des documents voisins
  écartées à la source, les doublons ne peuvent plus revenir.
- **Témoin AB1341 réparé** : zone majoritaire AUc 52,5 % (N 47,5 %) — l'affichage « N 95 % » et le
  HARD_EXCLUDE zonage artefact disparaissent au re-run.

### A-03 — Zones « e » Saint-Paul (habitat interdit au règlement)

- YAML `plu_saint_paul.yaml` : `habitat: interdit` + source (Art. 1.2, pages citées) sur
  U1e/U1ec/U2e/U3e/AU5e ; renvois AU1e/AU1ec/AU3e propagés ; AU1est déjà couverte (AU*st).
- Cascade : zone U/AU **calibrée** habitat-interdit ≥ seuil (90 %) → HARD_EXCLUDE « exclue » avec
  source règlementaire ; entre 5 et 90 % → SOFT_FLAG FORT + bonus réduit à la part habitat-admis.
  Jamais appliqué à une estimation générique (zones non calibrées intouchées).
- Faisabilité : gate `habitat=interdit` → capacité logement zéro ; `compute-residuel` Saint-Paul
  relancé (SDP des zones e purgée).

### Delta 2b (q_v4_m6a → q_v5_m6b) — À COMPLÉTER à la fin du run

- ⏳ run île `q_v5_m6b` en cours · score-v2 · build-mvt · delta par parcelle (statut/tier,
  avant/après, motif) · contrôle seuil 10 % · snapshot gelé post-2b.

---

## Journal des commits (branche `audit/grand-check`)

À jour au moment du pack — `git log --oneline main..audit/grand-check` fait foi.

## Restes consignés (AUCUN démarré — backlog M6 annexe + nouveaux)

- ANO-1 (1.4) : pipeline v2 lit l'étage 0 du label `q_v2` codé en dur (cause du 119 vs 117) — hors périmètre validé.
- Périmètres candidats matrice des modules M06/M15/M17/M19/M22 (99/117 brûlantes invisibles de ces gisements) — décision produit.
- M6-INC-01 (usages par module « logement étudiant ») : racine = distinction d'usage moteur, traitée à Saint-Paul par A-03 ; généralisation aux 23 autres communes = calibrage YAML par commune (mandat dédié).
- M6-INC-02 (piscinistes zone A/N, parcelles nues) : calibrage des presets segments = décision produit.
- Doublons inter-communes des AUTRES kinds (M6-01 : bâtiments 303 576, voirie 90 551…) — même réparation racine, mandat dédié (impact division/emprise bâtie).
- Troncature CSV liste à 5 000 (annonce X-Rows ajoutée, avertissement UI au backlog) ; exports md/html/one-pager encore legacy (P1 consigné).
- 9 groupes PLU sans exemplaire légitime ; parc_national ×24 (A2) ; QPV 2025 ; PM 2025 ; Cerema 2025.
