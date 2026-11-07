"""DOCS-1 (décision Vic) — RÉGÉNÉRATION V2 : tous les documents SURVIVANTS sur 97411000BZ1065 (+ une
parcelle nue en zone U, + une en zone rouge partielle), dans ~/Desktop/LABUSE-EXPORTS-2026-11-07-V2/,
avec un SOMMAIRE.md. Documents supprimés par DOCS-1 : Argumentaire, Dossier banquier, Lettre de zonage,
et le Financier builder-exports (seul le Bilan de l'écran Bilan reste). En process (TestClient, base
`labuse`), rendu PDF in-process (venv weasyprint). AUCUNE écriture prod, AUCUN mail.

    PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj PYTHONPATH=$PWD/src \
      ~/Desktop/labuse/.venv/bin/python scripts/docs1_regen_v2.py
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
os.environ.setdefault("LABUSE_PDF_PROCESS_ISOLE", "0")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

OUT = Path.home() / "Desktop" / "LABUSE-EXPORTS-2026-11-07-V2"

#: la parcelle témoin + les deux parcelles supplémentaires demandées par la recette.
CIBLE = "97411000BZ1065"                 # Saint-Denis (La Montagne) — bâtie, Uh, PPR bleue
VOISINES = ["97411000BZ1066", "97411000BZ1288"]
NUE_U = "97409000AK0804"                 # Saint-André — nue, UB, PPR
ROUGE = "97421000AB0133"                 # Salazie — zone rouge PPR partielle


def _compte_actif(db) -> int:
    from sqlalchemy import text
    r = db.execute(text("SELECT id FROM comptes ORDER BY id LIMIT 1")).scalar()
    return int(r) if r else 1


def regen() -> list[str]:
    from fastapi.testclient import TestClient

    from labuse.api import tenant
    from labuse.api.app import app
    from labuse.db import session_factory

    cid = _compte_actif(session_factory()())
    # session simulée : le Bilan, l'Apporteur (émetteur) et le Courrier (marque) exigent un compte.
    tenant.current_compte = lambda request=None: cid  # type: ignore[assignment]
    client = TestClient(app)
    OUT.mkdir(parents=True, exist_ok=True)
    produits: list[str] = []

    def _ecrire(nom: str, octets: bytes):
        (OUT / nom).write_bytes(octets)
        produits.append(f"{nom} ({len(octets)} o)")

    def _doc_get(num, label, idu, route, ext="pdf"):
        r = client.get(route)
        if r.status_code == 200 and (r.content[:4] == b"%PDF" or ext != "pdf"):
            _ecrire(f"{num} — {label} — {idu}.{ext}", r.content)
        else:
            produits.append(f"{num} — {label} — {idu} : NON RENDU ({r.status_code})")

    for idu in (CIBLE, NUE_U, ROUGE):
        tag = {CIBLE: "", NUE_U: " [nue zone U]", ROUGE: " [zone rouge partielle]"}[idu]
        _doc_get("01", f"Dossier{tag}", idu, f"/dossier/{idu}.pdf")
        _doc_get("02", f"Flash (= Dossier){tag}", idu, f"/dossier/{idu}.pdf")
        # 03/04 Bilan (PDF + Excel) : généré depuis une saisie VIDE → repères sourcés + « — » (non renseigné)
        g = client.post(f"/bilan/{idu}/generer", json={})
        if g.status_code == 200 and g.json().get("doc_id"):
            did = g.json()["doc_id"]
            _doc_get("03", f"Bilan{tag}", idu, f"/bilan/{idu}.pdf?doc_id={did}")
            _doc_get("04", f"Bilan (Excel){tag}", idu, f"/bilan/{idu}.xlsx?doc_id={did}", ext="xlsx")
        else:
            produits.append(f"03 — Bilan — {idu} : NON RENDU (generer {g.status_code})")
        _doc_get("05", f"Apporteur{tag}", idu, f"/apporteur/{idu}.pdf")
        _doc_get("06", f"Pre-dossier PC{tag}", idu, f"/pre-dossier/{idu}.zip", ext="zip")
        _doc_get("07", f"Gabarit{tag}", idu, f"/gabarit/{idu}.pdf")
        _doc_get("09", f"Etude de zone{tag}", idu, f"/etude-zone.pdf?idu={idu}&rayon_km=1")
        # 10 Étude de faisabilité (POST, 1 parcelle)
        e = client.post("/modules/etude/pdf", json={"idus": [idu]})
        if e.status_code == 200 and e.content[:4] == b"%PDF":
            _ecrire(f"10 — Etude de faisabilite{tag} — {idu}.pdf", e.content)
        else:
            produits.append(f"10 — Etude de faisabilite — {idu} : NON RENDU ({e.status_code})")
        _doc_get("12", f"Estimer un bien{tag}", idu, f"/analyse-annonce/{idu}.pdf")
        # 13 Courrier (POST)
        cpdf = client.post("/courrier/pdf", json={"idu": idu})
        if cpdf.status_code == 200 and cpdf.content[:4] == b"%PDF":
            _ecrire(f"13 — Courrier{tag} — {idu}.pdf", cpdf.content)
        else:
            produits.append(f"13 — Courrier — {idu} : NON RENDU ({cpdf.status_code})")

    # 08 Comparatif (cible + 2 voisines) et 17 Export CSV (global) — une seule fois.
    _doc_get("08", "Comparatif", CIBLE, f"/comparatif.pdf?idus={CIBLE},{VOISINES[0]},{VOISINES[1]}")
    _doc_get("17", "Export signalements", CIBLE, "/signalements/export.csv", ext="csv")
    return produits


def sommaire(produits: list[str]) -> str:
    return (
        "# LABUSE — Tous les documents (V2, après DOCS-1), sur une parcelle\n\n"
        "**Mandat DOCS-1 (décision Vic)** — des documents qui disent tous la même chose : un fait a\n"
        "UNE valeur (celle de la fiche), aucun mot de cuisine interne, un seul format. Régénéré après\n"
        "les corrections à la source. Le **banc des documents** rejoue sur 12 parcelles témoins et\n"
        "refuse tout fait imprimé à deux valeurs → **0 écart**.\n\n"
        "## Supprimés par DOCS-1\n"
        "- **Argumentaire**, **Dossier banquier**, **Lettre de zonage** (routes, cartes, menus, registre, tests).\n"
        "- **Financier** (document builder-exports) : n'était plus accessible depuis l'app ; le SEUL\n"
        "  document financier qui reste est le **Bilan** (écran Bilan, `/bilan/{idu}.pdf`).\n\n"
        "## Parcelles\n"
        f"- `{CIBLE}` — Saint-Denis (La Montagne), bâtie, zone Uh, PPR bleue (témoin de référence).\n"
        f"- `{NUE_U}` — Saint-André, **nue en zone U** (UB), PPR.\n"
        f"- `{ROUGE}` — Salazie, **zone rouge PPR partielle**.\n\n"
        "## Faits unifiés (une seule valeur, celle de la fiche)\n"
        "| Fait | Valeur unique (fiche) sur `97411000BZ1065` |\n|---|---|\n"
        "| Date des données | 21/10/2026 (identique sur tous les documents) |\n"
        "| Plafond d'emprise (30 % de la contenance) | 470 m² (Dossier = Gabarit = Comparatif) |\n"
        "| Hauteur à l'égout | 4,5 m (virgule, jamais « 4.5 ») |\n"
        "| Nombre de bâtiments | 2 |\n"
        "| Servitude PPR | 1 servitude — PM1 (le Gabarit lit `dispositifs.sup` comme le Dossier) |\n"
        "| Date du PPR | jj/mm/aaaa (jamais ISO « 2026-04-16 ») |\n"
        "| SDP maximale réglementaire, terrain | la valeur de la fiche (plus de « 325 m² » inventé : le Financier est supprimé) |\n\n"
        "## Documents produits\n" + "\n".join(f"- {p}" for p in produits) + "\n\n"
        "*Généré en process (base locale `labuse`), prod jamais touchée. DOCS-1.*\n"
    )


if __name__ == "__main__":
    prods = regen()
    (OUT / "SOMMAIRE.md").write_text(sommaire(prods), encoding="utf-8")
    print(f"=== V2 → {OUT} ===")
    for p in prods:
        print(" ", p)
    print(f"\nSOMMAIRE.md écrit ({len(prods)} entrées).")
