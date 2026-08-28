# RAPPORT — HYGIÈNE TECHNIQUE : FIABILISER LE DÉPLOIEMENT

Branche `fix/hygiene-deploiement` (base `main`). Mandat court et strictement borné : H1 (figer
`anthropic`) et H2 (`deploy.sh` sur main). Aucun autre fichier touché — le reste est finding.

## H1 — Figer la version du client Anthropic
**Demandé** : figer `anthropic==0.116.0` dans le fichier de dépendances réellement lu par deploy.sh,
vérifier qu'aucun autre ne le contredit, garde-fou bruyant, lister les autres paquets critiques non
figés (sans les figer).
**Fichier réellement lu** : `deploy/scripts/deploy_vps.sh` installe `pip install -e "$APP[ai]"` →
c'est **`pyproject.toml`, extra `[ai]`** qui est lu. `requirements.txt` (`-e .`) et
`requirements-ml.txt` (`-e .[ml]`) n'installent pas anthropic → aucune contradiction. `anthropic`
n'était déclaré qu'à un seul endroit (`pyproject.toml:55`).
**Traité** :
- `pyproject.toml [ai]` : `anthropic>=0.40` → **`anthropic==0.116.0`** (pin exact ; `>=0.40` a laissé
  le VPS installer 1.1.0, incompatible — refuse `temperature` → Copilote dégradé silencieux).
- **Garde-fou** `tests/test_anthropic_pin.py` (sans base ni réseau) : (1) le pin doit être **exact**
  (`==X.Y.Z`, jamais `>=`/plage) ; (2) la version **installée** doit être celle du pin, sinon échec
  explicite citant l'incident. **Prouvé bruyant** : pin desserré `>=` → `AssertionError` (« figé à une
  version EXACTE… ») ; version fausse `0.116.99` → `AssertionError` (« VERSION ANTHROPIC INATTENDUE :
  installée=0.116.0, attendue=0.116.99… ») ; état correct → 2 passed.
- **Deuxième ceinture, au déploiement** (dans `deploy_vps.sh`, cf. H2) : après `pip install -e .[ai]`,
  le script lit le pin dans `pyproject.toml` et compare à la version installée ; divergence → **arrêt
  bruyant (exit 4)** avant de servir. Le test protège la CI, cette vérif protège la prod (le point
  exact où le venv avait dérivé). Logique prouvée localement : pin=0.116.0, installée=0.116.0 → OK.

**Finding HY-001 — autres paquets critiques NON figés** (toutes les deps sont en `>=` ; je ne fige
rien, Vic tranche). Les plus exposés à une rupture d'API silencieuse au prochain deploy, par ordre de
risque :
- **`stripe>=8`** — l'API Stripe change entre majeures (paiements) ; une 9/10 pourrait casser
  `facturation.py` sans erreur d'import.
- **`pydantic>=2.5` + `pydantic-settings>=2.14.2`** — validation/settings ; une 3.0 casserait les
  modèles et la config (tout le chargement au démarrage).
- **`fastapi>=0.110` + `starlette>=0.36`** — socle web ; couplage serré, rupture possible en majeure.
- **`SQLAlchemy>=2.0`** — ORM ; une 3.0 romprait les requêtes.
- Second rang (rupture plus visible, échoue tôt) : `uvicorn`, `weasyprint>=61`, `pymupdf>=1.24`,
  `pypdf>=6.15.0`, `numpy>=1.26`, `shapely>=2.0`, `pyproj>=3.6`.
Anthropic était le pire cas (dégradation **silencieuse**) ; les autres tendent à échouer visiblement
(ImportError/erreur de schéma). Recommandation à l'appréciation de Vic : figer au moins `stripe` et le
couple `pydantic`/`pydantic-settings`.

## H2 — deploy.sh doit déployer main
**Demandé** : `deploy.sh` se met explicitement sur `main` à jour ; affiche branche+commit avant/après ;
s'arrête proprement si obstacle (dépôt sale, conflit) ; reste idempotent/rejouable.
**Traité** (`deploy/scripts/deploy_vps.sh`, posé sur le VPS comme `/opt/labuse/deploy.sh`) :
- **Garde de propreté** (étape 0) : `git status --porcelain` non vide → refus explicite (exit 3), le
  détail est affiché, aucun déploiement. Empêche le checkout main d'écraser/échouer en silence.
- **Bascule sur main** (étape 1) : `git fetch origin --prune` → `git checkout main` (arrêt exit 3 si
  impossible) → `git pull --ff-only origin main` (arrêt exit 3 si divergence non fast-forward). Plus
  jamais « déploie la branche courante ».
- **Annonce en clair** : « état AVANT : branche X @ commit » puis « déploiement de : branche main @
  commit ». Vic lit ce qui part en ligne.
- **Idempotent** : rejouable ; si `AVANT == APRES`, le script le dit et continue (venv/front/restart).
- Le pin anthropic est **revérifié** après `pip install` (H1, arrêt exit 4 sur dérive).
**Éprouvé localement** (dépôt git jetable, logique extraite du script) : dépôt sale → refus ✓ ;
checkout main + `pull --ff-only` depuis `feat/vps-golive` → succès ✓ ; divergence (commit local sur
main) → `pull --ff-only` refusé ✓. `bash -n` OK. **shellcheck 0.11.0 : propre (exit 0)** — au passage,
2 erreurs SC1087 (`"$APP[ai]"` → `"${APP}[ai]"`, dont une pré-existante) et 1 warning SC2034 (`for i`
→ `for _`) corrigées dans ce même fichier ; le source des secrets VPS est tu proprement (SC1091).
**Non vérifiable qu'au VPS** (Vic exécute, la sortie fait preuve) : les `sudo -u labuse`, le backup
`backup_postgres.sh`, `labuse init-db`, le build front, le `systemctl restart` + healthcheck `/readyz`,
et le `pip install -e .[ai]` réel. La logique git et la garde anthropic sont, elles, prouvées.

### Sortie attendue du deploy (ce que Vic doit lire)
Déploiement nominal (clone propre, sur une branche quelconque, main en fast-forward) :
```
▶ [AAAA-MM-JJ hh:mm:ss] deploy — état AVANT : branche feat/vps-golive @ 8270b4fcfed8
  cible : main (origin) — rollback : sudo -u labuse git -C /opt/labuse/app reset --hard <AVANT> ; voir en-tête
▶ [AAAA-MM-JJ hh:mm:ss] déploiement de : branche main @ <commit-main>
▶ backup pré-déploiement…
✓ anthropic 0.116.0 (== pin pyproject [ai])
▶ build front…            (ou : « front inchangé — build sauté »)
✓ [AAAA-MM-JJ hh:mm:ss] deploy OK — <AVANT> → <APRES>, /readyz ready=true
```
Obstacles (le déploiement s'ARRÊTE, rien n'est servi) :
- clone sale → `✗ le clone … est SALE … on REFUSE de déployer.` (exit 3)
- main injoignable → `✗ impossible de basculer sur main …` (exit 3)
- divergence → `✗ pull --ff-only origin main IMPOSSIBLE …` (exit 3)
- mauvaise version anthropic → `✗ VERSION ANTHROPIC INATTENDUE : installée=… attendue=…` (exit 4)

## Findings (hors périmètre — pas corrigés)
- **HY-001** — paquets critiques non figés (ci-dessus).
- **HY-002** — les docs `docs/DEPLOY_RUNBOOK.md`, `docs/DEPLOYMENT_OVH_VPS.md`, `docs/EXPLOITATION.md`
  décrivent le déploiement ; elles mentionnent l'ancien comportement « branche courante » par endroits.
  Non modifiées (hors périmètre : dépendances + deploy.sh + test de garde). À rafraîchir dans un mandat
  doc.
- Rappel mandat : golden à régénérer sur `q_v11_m137` et ON-002 (script inline CSP au login) sont
  **hors périmètre** — non touchés.

## Gardes
- `tests/test_anthropic_pin.py` : 2 passed, échecs prouvés sur dérive.
- `bash -n deploy_vps.sh` OK ; logique git+anthropic éprouvée localement.
- tsc/build : front inchangé (aucun fichier front touché) — restent verts.
- Golden : inchangé (aucun fichier de scoring touché).
- **Suite pytest : branche 1934 passed / 31 skipped / 0 failed** (dont les 2 tests
  `test_anthropic_pin`) ; base (worktree `f1e73834`) 1931 passed / 32 skipped / 0 failed. Au niveau
  de la base — l'écart = +2 tests de garde + 1 skip conditionnel (disponibilité DB), aucun échec.
