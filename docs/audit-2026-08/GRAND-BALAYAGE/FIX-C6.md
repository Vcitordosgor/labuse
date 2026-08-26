# FIX-C6 — solder les réserves de la certification cycle 6

Branche `fix/c6-reserves` (depuis `origin/main`). Audit-seul terminé au cycle 6 ; ici on CORRIGE. App :8000 laissée en route (jamais tuée) ; preuves d'installation sur base éphémère :8001+ détruite.

## Demandé → traité

### Point 1 — Installation autonome (GB-047/048/049 🟠, PRIORITÉ) — **SOLDÉ**
Le boot amorce un Postgres NU de bout en bout, aucun module en 500 sur base neuve.
- **GB-047** — `models.ensure_schema` appelle désormais `db.ensure_postgis` AVANT `create_all` (les tables ORM portent des colonnes `geometry` → sans PostGIS, `type "geometry" does not exist`). Tous les chemins (boot uvicorn + CLI) convergent.
- **GB-048** — heal réordonné : `comptes+scoping` AVANT `crm_columns` (FK `crm_columns.compte_id → comptes`). Plus de « relation "comptes" does not exist » au 1er boot.
- **GB-049 + extension** — les endpoints lisaient des tables DÉRIVÉES/d'ingestion absentes d'une base neuve → 500 `UndefinedTable`. Corrigé par le heal :
  - `m10_permit_delais` créée vide (`ingestion.permit_delais_m10.ensure_tables`) + garde `dmax IS NULL` sur `/modules/permis` (le `max(date)` NULL cassait `date >= NULL - interval`).
  - Copilote v2 : `historique.ensure_tables` + `telemetrie.ensure_tables` câblés au heal (conversations/messages/télémétrie).
  - Stubs vides au heal (`ensure_derived_read_stubs`) : `parcel_zone_plu`, `entonnoir_motifs`, `mvt_meta`, `commune_contexte_sru`, `commune_insee_logement`, `commune_conso_enaf`, `dvf_prix_sortie_neuf` (DDL ingester), `parcel_equipements` (DDL ingester), `p_model_bati`, `parcel_terrain`.
  - Piège évité : `parcel_zone_plu` a un builder « si absente » (tiles) — le déclencheur build-mvt reconstruit désormais si la table est ABSENTE **ou VIDE** (le stub n'inhibe pas le vrai build). `p_model_bati` et `parcel_zone_plu` sont en DROP+CREATE → stub remplacé sans dommage.
- **Preuve** : protocole LOT AJ rejoué sur base éphémère nue (`labuse_fix_test*` + uvicorn :800x), balayage exhaustif des GET métier → voir verdict final ci-dessous. Base réelle jamais touchée, tout détruit.

### Point 2 — Fuite orphelins snap (GB-063 🟠) — **SOLDÉ**
`watch_zone_zonage_snap` n'avait pas de FK vers `watch_zones` → orphelins à chaque suppression de veille (3 330 constatés).
- `delete_watch_zone` purge les snaps DANS LA MÊME TRANSACTION (garde IDOR : seulement si `n>0`).
- FK `ON DELETE CASCADE` posée à la création paresseuse (`alertes._ensure_secteur_schema`) ET en migration idempotente (`models.ensure_watch_snap_no_orphans`, au filet `_ensure_schema_steps`).
- Migration appliquée à la base réelle : **3 330 → 0 orphelins**, FK `fk_snap_zone` (CASCADE) posée, idempotence confirmée.
- Gardée permanente : `tests/test_alertes.py::test_suppression_veille_purge_le_snap_zonage_zero_orphelin`.

### Point 3 — Autres 🟠 — **SOLDÉS / justifiés**
- **GB-041** (seuil DPE) — `ligne8_pression_dpe` : seuil d'honnêteté `n≥30` (aligné sur la tendance). Sous le seuil → `calculable=False` « échantillon insuffisant » au lieu d'un « % F/G sur 1-4 DPE » en fiabilité « moyenne ».
- **GB-054** (backup-db sature le disque) — `labuse backup-db` par défaut « lean » : `--exclude-table-data` des 8 tables reconstructibles (~16 Go) ; garde d'espace disque AVANT écriture (refus < 2 Go) ; nettoie le fichier partiel en cas d'échec ; `--full` pour tout inclure.
- **GB-059** (état zombie clé outil) — `App.tsx` valide `#m=` contre le registre `MODULES` (alias hidden compris) ; clé inconnue ignorée (retour à l'accueil), plus de colonne gauche vide muette.
- **GB-066** (export sert le code tier) — `/parcels/export.csv` sert le LIBELLÉ M137 (`TIER_LABELS`, source unique), en-tête renommé `classement` : même mot que la fiche/carte/Copilote.
- **GB-053** (🔴 backup/RPO) — **CLOS HORS CODE** : backup complet 6,0 Go vérifié et externalisé par Vic le 26/08. Aucune action code (opérationnel).

### Point 4 — Triage des 17 🟡
**Soldés (mécaniques) :**
- **GB-056** — `projet.csv` émet un BOM UTF-8 (accents intacts sous Excel FR).
- **GB-057** — en-tête `projet.csv` : « cadrage NON figé (jamais exécuté) » quand non figé (fin de « cadrage figé le non figé »).
- **GB-058** — perf : index `ix_p_v2_run_computed (run_id, computed_at)` (plan `/map/tiles/meta` : Seq Scan coût 501082 → Index Only 0,76) + `/stats/entonnoir` mémorisé 30 s (comme `/stats`).

**Dette datée (raison) — 2026-08-26 :**
- **GB-042/043** (recherche : jokers LIKE `%%%` confiants ; `/parcels/search` ne matche que la fin d'IDU) — 🟡 sans faille (paramétré, 0 exfiltration). NON corrigé ICI : le chemin passe par `sql_plie` (pliage accents/casse/ligatures) ; y injecter un échappement + `ESCAPE` sur un cœur de recherche d'adresse est plus risqué que le défaut. À traiter dans un mandat recherche dédié.
- **GB-044/045/046** (vestiges : run démo `q_v2_demo` 8 lignes ; `ortho_tiles.nb_detections` périmé ; `ingestion_runs.parcels_count` sémantique) — cosmétiques, aucun chiffre servi. Purge/renommage = mandat ménage données, pas une réserve de certification.
- **GB-050** (install mineurs : messages dev sur /stats vide, lien compte-invite :8000, env=local auth off) — annexes du déploiement, couverts par le runbook.
- **GB-051/052** (PDF : date de run jamais imprimée = design M125-C2 assumé ; section SDP absente sans libellé) — arbitrage Vic (design), pas un bug.
- **GB-055** (a11y : 4 familles serious, 0 critical) — chantier accessibilité dédié (contrastes Rail, nested-interactive CRM, aria-hidden Copilote, landmarks) ; un fix par famille, hors périmètre « réserves ».
- **GB-060** (écritures non bornées : nom/notes 1 Mo acceptés) — durcissement d'entrée, 0 corruption/500 constatés ; mandat hardening.
- **GB-061** (PATCH/DELETE d'un id inexistant → 200 au lieu de 404) — contrat REST, honnête (rien modifié) ; à rejouer à 2 comptes (IDOR M45) avant.
- **GB-062** (= GB-040 : 500 sous 50 connexions // = capacité mono-worker) — déploiement `--workers N`, opérationnel.
- **GB-064** (export.pdf shortlist figée 200 vs total vif) — design documenté (shortlist figée) ; à libeller, pas un faux chiffre.
- **GB-065** (routage Copilote : 6 sous-réponses) — 0 invention/faux chiffre ; affinage lexique/routage, mandat Copilote.

## Verdict d'installation (LOT AJ rejoué) — voir section finale après le dernier rejeu.
