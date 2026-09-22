# RACINE-1 — Ce qui sert encore à la racine du dépôt

**Branche** `audit/racine-1` · worktree `~/Desktop/labuse-racine` · base main `a272d4a5`
**Lecture seule.** Aucun `git mv`, `git rm`, déplacement ni suppression n'a été fait. Ce document *propose* ; les gestes restent à la décision de Vic.
Livrables : ce rapport + [`reports/racine-1/INVENTAIRE.csv`](../../reports/racine-1/INVENTAIRE.csv) (212 lignes, une par entrée de profondeur 1).

---

## 1. Compteurs

**212 entrées** à la racine (profondeur 1, hors `.git` / `node_modules` / `.venv`) : **196 fichiers + 16 dossiers**.
- **Tout est versionné sauf un** : `.DS_Store` (junk macOS, `.gitignore:162`).
- **Pas de `node_modules` ni de `.venv` à la racine** (uniquement `frontend/node_modules`, hors périmètre).

| Catégorie | Fichiers | Dossiers | Total |
|---|---:|---:|---:|
| **A — INDISPENSABLE** | 14 | 14 | **28** |
| **B — LU/CITÉ PAR LE CODE** | 10 | 0 | **10** |
| **C — ARCHIVE** | 167 | 2 | **169** |
| **D — MORT** | 5 | 0 | **5** |

Le désordre = **167 fichiers .md d'archive** (rapports/notes/mandats de chantiers terminés) + 5 morts. Poids de ces 172 fichiers : **≈ 1,5 Mo**. Les deux dossiers C (`audit_shots/` 28 Mo, `commercial/` 60 Ko) pèsent l'essentiel.

---

## 2. A — INDISPENSABLE (28)

**Fichiers (14)** : `README.md`, `README_DEV.md`, `deploy.sh`, `Dockerfile`, `docker-compose.yml`, `docker-compose.pilot.yml`, `docker-compose.caddy.yml`, `pyproject.toml`, `requirements.txt`, `requirements-ml.txt`, `.gitignore`, `.dockerignore`, `.env.example`, `.env.pilot.example`.
**Dossiers (14)** : `src/`, `tests/`, `config/`, `frontend/`, `scripts/`, `deploy/`, `docs/`, `data/`, `declarations/`, `qa/`, `captures/`, `reports/`, `outputs/`, `.claude/`.

Note sur trois dossiers qui *ressemblent* à des sorties mais sont des **chemins par défaut lus/écrits par le code** (donc A, pas D) :
- `outputs/` — `src/labuse/config.py:160` (`flash_storage_dir = "outputs/flash"`) + `cli.py:3688` (`--dry-dir outputs/radar-digests`). *Son contenu* (PDF, `.log`) est régénérable, mais le dossier est un point d'écriture.
- `captures/` — contient des fixtures de test : `tests/test_copilote2_routeur.py:11` lit `captures/copilote2/routeur_jeu.json`.
- `reports/` — chemins cités (`src/labuse/models.py:354` `reports/m1-v13/…`, `cli.py:2816` `reports/arene/`).

---

## 3. B — LU / CITÉ PAR LE CODE (10) — avec preuve

**Fait capital : les 10 sont des CITATIONS en commentaire ou docstring. Aucune n'est un `open()`/`read_text` fonctionnel.** J'ai grep-é tout `tests/ scripts/ deploy/ .github deploy.sh` pour `open(` / `read_text` / `Path(` : **aucun** ne vise un `.md`/`.html` de la racine. Supprimer l'un d'eux ne casse donc **aucun** test, build, verrou ou CI — mais **orpheline la citation** (un commentaire pointant vers un fichier disparu). D'où le classement B (« référencé, à ne pas supprimer à l'aveugle »), distinct de C.

| Fichier | Preuve (fichier:ligne qui le cite) | Nature |
|---|---|---|
| `RAPPORT_CALIBRATION_WEB.md` | `src/labuse/faisabilite/bilan_calibration.py:1,9,42` — docstring : *« Ne pas modifier une valeur ici sans mettre à jour le rapport »* ; aussi `models.py:1465` | **source de vérité** des constantes de calibration — le plus porteur |
| `NOTES_WAVE_ACI.md` | `src/labuse/courrier.py:3` et `:674` | source de l'étude DOM (facturation courrier) |
| `NOTES_GEORISQUES.md` | `src/labuse/ingestion/georisques_layers.py:13` | justification (risque ~inexistant à La Réunion) |
| `PRE_VOL_ILE.md` | `src/labuse/cascade/layers/phase2.py:37` + `config/cascade_rules.yaml:525` | règle p25/p75 — **⚠ DOUBLON divergent** (voir §5) |
| `RAPPORT_DISPO_3B.md` | `src/labuse/api/enrichment.py:53` | vérif couverture nationale |
| `RAPPORT_M78.md` | `src/labuse/copilote_v2/__init__.py:3` + `router.py:5` | doctrine du routeur Copilote |
| `RAPPORT_M_W_CARTE_NOIRE.md` | `frontend/src/components/map/MapView.tsx:1440` | raison d'un fix carte |
| `PILOT_SECURITY_DEPLOYMENT.md` | `Dockerfile:29` | renvoi `labuse doctor` |
| `CRON-1-LOT1.md` | `src/labuse/jobs.py:411` + `tests/test_circuit4_lot5.py:73` | raison de retrait d'un job du registre |
| `CRON-1-LOT2.md` | `tests/test_cron1_g8.py:4` — docstring : *« la preuve RED … est dans CRON-1-LOT2.md »* | pièce du verrou G8 (citée, pas lue) |

**Vérification du point 3 du mandat** — aucun fichier C ou D n'est lu par un test / verrou / CI / registre :
- `deploy.sh` ne lit qu'un fichier `.md` : `docs/CIRCUIT/VERROUS.md` (hors racine, catégorie A).
- Aucun workflow CI (`.github/workflows` **n'existe pas**).
- `tests/test_cron1_registre.py:15` fait `Path(fichier).exists()` sur des node-ids `tests/…`, **jamais** sur un `.md` racine.
- Le registre des jobs (`labuse.jobs.JOBS`) ne référence aucun fichier racine.

---

## 4. Les `.html` de démo — encore servis ?

**Non.** `DEMO_ONE_PAGER.html` et `DEMO_PACK_PRINT.html` n'apparaissent **que** dans `.dockerignore:14-15`, c'est-à-dire pour être **EXCLUS** de l'image. Aucun serveur, route, script ou test ne les sert. → **D**.

---

## 5. Doublons racine ↔ `docs/`

Deux fichiers portent le même nom à la racine et sous `docs/`, et les **deux paires divergent** (ce ne sont pas des copies identiques mais des versions parallèles ; la copie `docs/` est la plus récente / à sa place) :

| Racine | Copie `docs/` | État |
|---|---|---|
| `DEPLOY_RUNBOOK.md` (223 l., commit 2026-07-28) | `docs/DEPLOY_RUNBOOK.md` (89 l., commit **2026-08-27**, plus récent) | **divergent** — la racine est la vieille version → classé **D** |
| `PRE_VOL_ILE.md` (53 l., 2026-08-15) | `docs/communes/PRE_VOL_ILE.md` (97 l., 2026-08-13) | **divergent** — la racine est cité par le code (§3) mais la version canonique est sous `docs/communes/` → classé **B**, à réconcilier |

(`README.md` racine matche des `README.md` de sous-dossiers `docs/…` : ce sont des READMEs *scopés* différents, **pas** des doublons.)

---

## 6. D — MORT (5)

| Fichier | Raison |
|---|---|
| `.DS_Store` | junk macOS, non versionné, régénéré par le Finder |
| `DEMO_ONE_PAGER.html` | démo, seulement `.dockerignore` (exclue), servie nulle part |
| `DEMO_PACK_PRINT.html` | idem |
| `FICHE-COUCHES-3.md` | **sortie régénérable** de `qa/fiche_couches3_report.py` (qui écrit d'ailleurs vers un *autre* worktree) |
| `DEPLOY_RUNBOOK.md` | doublon divergent périmé de `docs/DEPLOY_RUNBOOK.md` (§5) |

---

## 7. C — ARCHIVE (169) : proposition de rangement

167 fichiers + 2 dossiers de mémoire de chantiers terminés, non lus par personne. Aucun n'est référencé par le code/test/CI/verrou/registre (grep exhaustif §3). Proposition : les regrouper sous **`docs/archive/<chantier>/`** (à créer ; `docs/archive/` n'existe pas encore) par `git mv`, **sur décision de Vic**.

| Bucket proposé `docs/archive/…` | Fichiers | Exemples |
|---|---:|---|
| `mandats-M55-M85/` | 57 | `RAPPORT_M55A_COUCHES.md` … `RAPPORT_M85B.md` |
| `chantiers-sept-2026/` | 25 | `COHERENCE-1.md`, `COMMUNE-AUDIT-1.md`, `CRON-1-LOT0.md`, `COUCHES-*`, `SOURCES-*`, `PLU-CALIBRAGE-*` |
| `cercles-dispo-juin/` | 17 | `RAPPORT_3A.md`, `RAPPORT_CERCLE_*`, `RAPPORT_DISPO_*`, `RAPPORT_LOT_*` |
| `fable-waves-juillet/` | 16 | `MANDAT_FABLE_*`, `RAPPORT_WAVE_*`, `RAPPORT_HABITAT_SOLAIRE.md`, `RAPPORT-DATA-GAP.md` |
| `etat-diagnostic/` | 14 | `AUDIT*.md`, `DIAGNOSTIC.md`, `STATUS.md`, `BUGS.md`, `BILAN_ILE.md` |
| `ux-design/` | 10 | `DESIGN_SYSTEM.md`, `TERMINAL_DESIGN.md`, `RAPPORT_UX_V1.md`, `AMELIORATIONS-UX.md` |
| `notes-sources-juillet/` | 9 | `NOTES_BODACC.md`, `NOTES_DPE.md`, `NOTES_SITADEL3.md` … |
| `demos/` | 3 | `DEMO_PACK.md`, `DEMO_SETUP.md`, `CLIENT_DEMO_CHECKLIST.md` |
| `carte-maplibre/` | 5 | `RAPPORT_M_V_*`, `RAPPORT_M_W_*` |
| `divers-sources-recon/` | 9 | `ANNONCES_RECON.md`, `CHAMPS-MORTS.md`, `PROXYS-SOURCES.md`, `RAPPORT_SOURCES.md`, `RAPPORT_PLU_REF.md` |
| `exploitation-pilote/` | 2 | `PILOT_DEPLOYMENT.md`, `RESTORE_DRILL.md` |
| **dossiers** | 2 | `audit_shots/` (27 captures, 28 Mo) → `docs/archive/captures-demo-juillet/` ; `commercial/` (5 docs de vente) → `docs/archive/commercial/` ou dossier dédié hors racine |

*(Le compte exact par bucket est reproductible via `scripts/racine1_csv.py`.)*

---

## 8. Ce qui pourrait être supprimé (à valider par Vic)

**Suppression franche — 5 fichiers D, ≈ 40 Ko + junk :**
- `.DS_Store` (non versionné — un simple `rm`, et l'ajouter au `.gitignore` global si pas déjà fait — il l'est).
- `DEMO_ONE_PAGER.html`, `DEMO_PACK_PRINT.html` (démos périmées, jamais servies).
- `FICHE-COUCHES-3.md` (régénérable).
- `DEPLOY_RUNBOOK.md` racine (doublon périmé — garder `docs/DEPLOY_RUNBOOK.md`).

**Réconciliation avant tout geste :**
- `PRE_VOL_ILE.md` — deux versions divergentes, la racine est citée par le code. Décider laquelle est vraie, garder une seule copie (idéalement `docs/communes/`), et faire pointer les 2 commentaires (`phase2.py:37`, `cascade_rules.yaml:525`) vers elle.

**Gain de rangement (déplacement, pas suppression) :** sortir **169 entrées** de la racine vers `docs/archive/` la ramène de 196 fichiers à **~24 fichiers utiles** (les 14 A + 10 B, moins les B qu'on choisira de déplacer avec mise à jour des citations). Poids déplacé : ≈ 1,5 Mo de `.md` + 28 Mo de `audit_shots/`.

---

## 9. Hors mandat (non fait)

Aucun déplacement / suppression / renommage exécuté. `docs/audit-2026-09/` non modifié sauf l'ajout de ce rapport. Pas de merge, pas de Gabarit. Les scripts d'audit (`scripts/racine1_scan.sh`, `scripts/racine1_csv.py`) et les sorties (`reports/racine-1/`) sont les seuls fichiers créés par ce mandat.
