#!/usr/bin/env bash
# RACINE-1 rangement — git mv des archives C sous docs/archive/<chantier>/,
# git rm des D, fix citations doublon. Exécuté sur décision de Vic.
set -eu
R=/Users/openclaw/Desktop/labuse-racine
cd "$R"

python3 - <<'PY'
import csv, re, subprocess, os
rows = [r for r in csv.DictReader(open("reports/racine-1/INVENTAIRE.csv"))]

def bucket(n):
    if re.match(r'RAPPORT_M5[5-9]|RAPPORT_M[6-8]\d', n): return "mandats-M55-M85"
    if n.startswith("RAPPORT_M_V") or n.startswith("RAPPORT_M_W"): return "carte-maplibre"
    if re.match(r'RAPPORT_(3[ACD]|CERCLE|DISPO|LOT|PHASE1|DECISIONS)', n): return "cercles-dispo-juin"
    if n.startswith("MANDAT_FABLE") or n.startswith("RAPPORT_WAVE") or "HABITAT" in n or "SEGMENTS" in n or n.startswith("PROMPT-FABLE") or "DATA-GAP" in n: return "fable-waves-juillet"
    if n.startswith("NOTES_"): return "notes-sources-juillet"
    if any(n.startswith(p) for p in ("COUCHES-","FICHE-COUCHES","CRON-1","PAGE-SOURCES","PAGES-AUDIT","FILTRES-AUDIT","COMMUNE-","COHERENCE","SOURCES-","COPILOTE-AUDIT","PLU-CALIBRAGE","NETTOYAGE","FICHE-AUDIT","FICHE-SOURCES")): return "chantiers-sept-2026"
    if "DEMO" in n or n == "CLIENT_DEMO_CHECKLIST.md": return "demos"
    if any(k in n for k in ("UX","DESIGN","POLISH","CREDIBILITE","INSPECTION","TERMINAL")): return "ux-design"
    if any(k in n for k in ("PILOT","DEPLOY","RESTORE")): return "exploitation-pilote"
    if n.startswith("AUDIT") or n in ("DIAGNOSTIC.md","STATUS.md","BUGS.md","ETAT_DES_LIEUX_DONE.md","LISEZMOI_MATIN.md","COMMANDES.md","BILAN_ILE.md","RAPPORT_QA.md","ANNEXE_REVUE_AN_ER.md"): return "etat-diagnostic"
    return "divers-sources-recon"

DIR_TARGET = {"audit_shots": "captures-demo-juillet", "commercial": "commercial"}

moves = 0
for r in rows:
    if r["categorie"] != "C":
        continue
    nom = r["nom"]
    if r["type"] == "DIR":
        b = DIR_TARGET.get(nom, "divers")
    else:
        b = bucket(nom)
    dest = f"docs/archive/{b}"
    os.makedirs(dest, exist_ok=True)
    subprocess.run(["git", "mv", nom, f"{dest}/"], check=True)
    moves += 1
print(f"git mv C : {moves} entrées déplacées")
PY

echo "--- git rm des D versionnés ---"
git rm -q DEMO_ONE_PAGER.html DEMO_PACK_PRINT.html FICHE-COUCHES-3.md DEPLOY_RUNBOOK.md
echo "--- .DS_Store (non versionné, déjà gitignore:162) : rm simple ---"
rm -f .DS_Store
echo "rangement terminé"
