#!/usr/bin/env python3
"""RACINE-1 — génère reports/racine-1/INVENTAIRE.csv (lecture seule)."""
import csv, os, subprocess, sys

R = "/Users/openclaw/Desktop/labuse-racine"
os.chdir(R)

SKIP = {".git", "node_modules", ".venv", ".", ".."}

# --- classification maps -------------------------------------------------
DIR_A = {"src", "tests", "config", "frontend", "scripts", "deploy", "docs",
         "data", "declarations", "qa", "captures", "reports", "outputs", ".claude"}
DIR_C = {"audit_shots", "commercial"}

FILE_A = {
    "README.md": "README principal du dépôt",
    "README_DEV.md": "guide dev",
    "deploy.sh": "script de déploiement (lu par tests/test_cron1_lot3.py:48)",
    "Dockerfile": "image conteneur",
    "docker-compose.yml": "orchestration",
    "docker-compose.pilot.yml": "orchestration pilote",
    "docker-compose.caddy.yml": "orchestration reverse-proxy",
    "pyproject.toml": "packaging/deps Python",
    "requirements.txt": "deps Python",
    "requirements-ml.txt": "deps ML",
    ".gitignore": "infra VCS",
    ".dockerignore": "infra image",
    ".env.example": "gabarit env (docker-compose.pilot.yml:4 `cp .env.example .env`)",
    ".env.pilot.example": "gabarit env pilote",
}

# B = nom référencé dans le code/tests/config — TOUTES sont des CITATIONS en
# commentaire/docstring, AUCUN open()/read fonctionnel.
FILE_B = {
    "RAPPORT_CALIBRATION_WEB.md": "src/labuse/faisabilite/bilan_calibration.py:1,9,42 (docstring: «Ne pas modifier une valeur ici sans mettre à jour le rapport») + models.py:1465",
    "NOTES_WAVE_ACI.md": "src/labuse/courrier.py:3 et :674 (source étude DOM citée)",
    "NOTES_GEORISQUES.md": "src/labuse/ingestion/georisques_layers.py:13 (commentaire justificatif)",
    "PRE_VOL_ILE.md": "src/labuse/cascade/layers/phase2.py:37 + config/cascade_rules.yaml:525 (commentaire) — DOUBLON divergent de docs/communes/PRE_VOL_ILE.md",
    "RAPPORT_DISPO_3B.md": "src/labuse/api/enrichment.py:53 (commentaire vérif)",
    "RAPPORT_M78.md": "src/labuse/copilote_v2/__init__.py:3 + router.py:5 (docstring doctrine)",
    "RAPPORT_M_W_CARTE_NOIRE.md": "frontend/src/components/map/MapView.tsx:1440 (commentaire)",
    "PILOT_SECURITY_DEPLOYMENT.md": "Dockerfile:29 (commentaire, cf. `labuse doctor`)",
    "CRON-1-LOT1.md": "src/labuse/jobs.py:411 + tests/test_circuit4_lot5.py:73 (commentaire/test — raison de retrait registre)",
    "CRON-1-LOT2.md": "tests/test_cron1_g8.py:4 (docstring: «preuve RED … dans CRON-1-LOT2.md»)",
}

# D = mort / doublon / démo périmée / sortie régénérable
FILE_D = {
    "DEMO_ONE_PAGER.html": "démo HTML — seule occurrence = .dockerignore:15 (EXCLUE de l'image) ; servie nulle part",
    "DEMO_PACK_PRINT.html": "démo HTML — seule occurrence = .dockerignore:14 (EXCLUE de l'image) ; servie nulle part",
    "FICHE-COUCHES-3.md": "sortie RÉGÉNÉRABLE par qa/fiche_couches3_report.py (qui écrit vers un AUTRE worktree)",
    "DEPLOY_RUNBOOK.md": "DOUBLON divergent de docs/DEPLOY_RUNBOOK.md (root 223 l. vs docs 89 l., docs plus récent 2026-08-27)",
    ".DS_Store": "junk macOS, NON versionné (gitignore:162), régénéré par le Finder",
}

def versionne(path):
    r = subprocess.run(["git", "ls-files", "--error-unmatch", path],
                       capture_output=True, text=True)
    if r.returncode == 0:
        return "oui"
    # dossier avec enfants suivis ?
    if os.path.isdir(path):
        t = subprocess.run(["git", "ls-files", path], capture_output=True, text=True).stdout
        if t.strip():
            return "oui (contenu)"
    return "NON"

def last_commit(path):
    out = subprocess.run(["git", "log", "-1", "--format=%cs %h", "--", path],
                         capture_output=True, text=True).stdout.strip()
    return out or "(none)"

def du_bytes(path):
    if os.path.isdir(path):
        out = subprocess.run(["du", "-sk", path], capture_output=True, text=True).stdout.split()
        return int(out[0]) * 1024 if out else 0
    try:
        return os.path.getsize(path)
    except OSError:
        return 0

def classify(name, is_dir):
    if is_dir:
        if name in DIR_A:
            return "A", "dossier code/config/infra ou chemin par défaut lu par le code"
        if name in DIR_C:
            return "C", "archive (captures/notes de chantier terminé, non lu par le code)"
        return "C", "dossier non référencé"
    if name in FILE_A:
        return "A", FILE_A[name]
    if name in FILE_B:
        return "B", FILE_B[name]
    if name in FILE_D:
        return "D", FILE_D[name]
    return "C", "rapport/note/mandat de chantier terminé — non référencé par code/test/CI/verrou/registre"

rows = []
for e in sorted(os.listdir(".")):
    if e in SKIP:
        continue
    is_dir = os.path.isdir(e)
    cat, proof = classify(e, is_dir)
    rows.append({
        "nom": e,
        "type": "DIR" if is_dir else "FILE",
        "categorie": cat,
        "preuve": proof,
        "taille_octets": du_bytes(e),
        "dernier_commit": last_commit(e),
        "versionne": versionne(e),
    })

out_path = "reports/racine-1/INVENTAIRE.csv"
with open(out_path, "w", newline="") as f:
    w = csv.DictWriter(f, fieldnames=["nom", "type", "categorie", "preuve", "taille_octets", "dernier_commit", "versionne"])
    w.writeheader()
    w.writerows(rows)

from collections import Counter
c = Counter(r["categorie"] for r in rows)
cf = Counter(r["categorie"] for r in rows if r["type"] == "FILE")
cd = Counter(r["categorie"] for r in rows if r["type"] == "DIR")
print(f"écrit {out_path} — {len(rows)} entrées")
print("TOTAL par catégorie :", dict(sorted(c.items())))
print("FICHIERS par catégorie :", dict(sorted(cf.items())))
print("DOSSIERS par catégorie :", dict(sorted(cd.items())))
# poids C+D fichiers
poids = sum(r["taille_octets"] for r in rows if r["type"] == "FILE" and r["categorie"] in ("C", "D"))
nC = sum(1 for r in rows if r["type"] == "FILE" and r["categorie"] == "C")
nD = sum(1 for r in rows if r["type"] == "FILE" and r["categorie"] == "D")
print(f"Fichiers C={nC} D={nD} ; poids C+D = {poids/1024:.0f} Ko")
