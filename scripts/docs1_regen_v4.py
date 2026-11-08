"""DOCS-1 (2e passe, décision Vic) — RÉGÉNÉRATION V4 : tous les documents servis, corrigés à la
source, dans ~/Desktop/LABUSE-EXPORTS-2026-11-07-V4/ + un SOMMAIRE.md. Différences avec la V2 :

  * le **Flash** est le VRAI produit 79 € (`flash.report.generate_flash_report`, son propre moteur),
    plus jamais une copie du Dossier ;
  * témoin PPR = une parcelle en **zone U partiellement en zone ROUGE de PPR** (97415000CY0275) ;
  * une parcelle en **zone N** (97421000AB0133) montre que le **Gabarit** rend un DOCUMENT de refus
    propre (jamais un 422) ;
  * le **Bilan** reprend la contenance en ligne « Terrain » et, sans coût majeur saisi, affiche
    « non calculable — saisissez vos coûts » (jamais un bénéfice).

En process (TestClient, base locale `labuse`), rendu PDF in-process (venv weasyprint). AUCUNE écriture
prod, AUCUN mail.

    PROJ_DATA=$HOME/miniforge3/envs/labusedb/share/proj PYTHONPATH=$PWD/src \
      ~/Desktop/labuse/.venv/bin/python scripts/docs1_regen_v3.py
"""
from __future__ import annotations

import os
from pathlib import Path

os.environ.setdefault("LABUSE_DATABASE_URL", "postgresql+psycopg://openclaw@localhost:5432/labuse")
os.environ.setdefault("LABUSE_PDF_PROCESS_ISOLE", "0")
os.environ.setdefault("KMP_DUPLICATE_LIB_OK", "TRUE")

OUT = Path.home() / "Desktop" / "LABUSE-EXPORTS-2026-11-07-V4"

CIBLE = "97411000BZ1065"                 # Saint-Denis (La Montagne) — bâtie, Uh, PPR bleue (référence)
VOISINES = ["97411000BZ1066", "97411000BZ1288"]
NUE_U = "97409000AK0804"                 # Saint-André — nue, UB
PPR_U = "97415000CY0275"                 # zone U partiellement en zone ROUGE de PPR (~29 %)
ZONE_N = "97421000AB0133"                # Salazie — zone N : le Gabarit rend un refus propre


def _compte_actif(db) -> int:
    from sqlalchemy import text
    r = (db.execute(text("SELECT id FROM comptes WHERE statut='actif' ORDER BY id LIMIT 1")).scalar()
         or db.execute(text("SELECT id FROM comptes ORDER BY id LIMIT 1")).scalar())
    return int(r) if r else 1


#: saisies ILLUSTRATIVES du Bilan : programme saisi, POSTES de charges vides → sans coût majeur, le
#: Bilan imprime « non calculable — saisissez vos coûts » (jamais un bénéfice), et la ligne « Terrain »
#: reprend la contenance de la fiche. Démontre « aucune hypothèse inventée ».
_BILAN_ILLUSTRATIF = {
    "programme": {"terrain": None, "surface_taxable": 65, "sdp": 35},
    "produits": [{"libelle": "Logement", "lots": 1, "suv": 65, "prix_ttc_m2_suv": 4500, "tva": 0.021}],
    "postes": {}, "mode": "marge", "marge_cible": 9, "calendrier": {},
}


def regen() -> list[str]:
    from fastapi.testclient import TestClient

    from labuse.api import bilan as _bilan, tenant
    from labuse.api.app import app
    from labuse.db import session_factory, session_scope
    from labuse.flash.report import generate_flash_report

    cid = _compte_actif(session_factory()())
    tenant.current_compte = lambda request=None: cid     # type: ignore[assignment]
    _bilan.current_compte = lambda request=None: cid      # type: ignore[assignment]
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

    tags = {CIBLE: "", NUE_U: " [nue zone U]", PPR_U: " [zone U, PPR rouge partielle]",
            ZONE_N: " [zone N — Gabarit refus]"}
    for idu in (CIBLE, NUE_U, PPR_U, ZONE_N):
        tag = tags[idu]
        _doc_get("01", f"Dossier{tag}", idu, f"/dossier/{idu}.pdf")
        # 02 — Flash : le VRAI produit 79 € (son propre moteur), jamais une copie du Dossier.
        try:
            with session_scope() as db:
                fp = generate_flash_report(idu, order_ref="V4", force=True, db=db, with_map=True)
            _ecrire(f"02 — Flash{tag} — {idu}.pdf", fp.read_bytes())
        except Exception as exc:  # noqa: BLE001
            produits.append(f"02 — Flash — {idu} : NON RENDU ({exc})")
        # 03/04 Bilan (PDF + Excel)
        g = client.post(f"/bilan/{idu}/generer", json=_BILAN_ILLUSTRATIF)
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
        e = client.post("/modules/etude/pdf", json={"idus": [idu]})
        if e.status_code == 200 and e.content[:4] == b"%PDF":
            _ecrire(f"10 — Etude de faisabilite{tag} — {idu}.pdf", e.content)
        else:
            produits.append(f"10 — Etude de faisabilite — {idu} : NON RENDU ({e.status_code})")
        _doc_get("12", f"Estimer un bien{tag}", idu, f"/analyse-annonce/{idu}.pdf")
        cpdf = client.post("/courrier/pdf", json={"idu": idu})
        if cpdf.status_code == 200 and cpdf.content[:4] == b"%PDF":
            _ecrire(f"13 — Courrier{tag} — {idu}.pdf", cpdf.content)
        else:
            produits.append(f"13 — Courrier — {idu} : NON RENDU ({cpdf.status_code})")

    _doc_get("08", "Comparatif", CIBLE, f"/comparatif.pdf?idus={CIBLE},{VOISINES[0]},{VOISINES[1]}")
    return produits


def sommaire(produits: list[str]) -> str:
    return (
        "# LABUSE — Tous les documents (V4, DOCS-1 3e passe), par parcelle\n\n"
        "**Mandat DOCS-1 (décision Vic)** — des documents qui disent tous la même chose : un fait a\n"
        "UNE valeur (celle de la fiche), aucun mot de cuisine interne, un seul format. V4 = après la\n"
        "3e passe. Le **banc des documents** rejoue TOUS les documents (Étude, Courrier, Bilan, **Flash**\n"
        "réel compris) sur 13 parcelles témoins, et confronte en plus la **marge de surélévation**, la\n"
        "**surface vendable**, la **SDP maximale** et le **permis à moins de 100 m** → **0 écart**.\n\n"
        "## Ce que la V4 corrige en plus de la V3\n"
        "- **Flash — faits du MÊME lecteur que la fiche** (entrés dans le banc) : marge de surélévation\n"
        "  (−3,3 m sur BZ1065, négative = le bâti dépasse déjà), SDP maximale et surface vendable\n"
        "  (lues du bloc `potentiel_transformation`, comme le Dossier — « non calculable » quand la\n"
        "  capacité est nulle, plus un « 118 m² » de scénario table-rase divergent).\n"
        "- **Flash — langage et format** : plus de « calibré / calibrage » (règles du PLU) ; codes bruts\n"
        "  en clair (« mouvement de terrain », « très forte », « zone de transition ») ; format français\n"
        "  (« −0,3 % », « 3 169 € », « 1 234 ventes » — signe moins, virgule, séparateur de milliers).\n"
        "- **Permis à moins de 100 m** : la ligne datée du marché (« < 100 m, 36 mois ») est la seule\n"
        "  autorité « même valeur » entre documents ; le faisceau de viabilisation NOMME sa fenêtre\n"
        "  (« toute période »), pour ne plus être lu comme le même chiffre.\n"
        "- **Étude de zone** : la tuile sans imagerie en haut à gauche de la carte se FOND dans la\n"
        "  mosaïque (plus de carré blanc tranché).\n"
        "- **Gabarit 3D** : les deux légendes empilées (jamais superposées) ; l'enveloppe RÉELLEMENT\n"
        "  réduite au plafond d'emprise (socle compact, pas la zone entière).\n"
        "- **Comparatif** : le tableau commence en page 2 (avec son titre) s'il ne tient pas sous la carte.\n"
        "- **Bilan** : « Taxe d'aménagement » en toutes lettres ; plus aucun « 0 € » (→ « — »).\n"
        "- **Gabarit en refus** : la VRAIE raison (« Zone non constructible (N) », « zone trop étroite »…),\n"
        "  jamais « donnée manquante » quand la cause est connue.\n"
        "- **Étude de faisabilité** : un document de refus PROPRE quand le moteur ne trouve aucune\n"
        "  implantation (comme en zone N), jamais une 400.\n\n"
        "## Parcelles\n"
        f"- `{CIBLE}` — Saint-Denis (La Montagne), bâtie, Uh, PPR bleue (témoin de référence).\n"
        f"- `{NUE_U}` — Saint-André, **nue en zone U**.\n"
        f"- `{PPR_U}` — **zone U partiellement en zone ROUGE de PPR** : le Gabarit déduit le rouge ; "
        "l'Étude rend un refus propre (« zone trop étroite » — aucune parcelle zone U ∩ PPR rouge de la\n"
        "  base locale ne porte un scénario d'implantation).\n"
        f"- `{ZONE_N}` — Salazie, **zone N** : le Gabarit et l'Étude rendent un document de refus motivé.\n\n"
        "## Documents produits\n" + "\n".join(f"- {p}" for p in produits) + "\n\n"
        "*Généré en process (base locale `labuse`), prod jamais touchée. DOCS-1 3e passe.*\n"
    )


if __name__ == "__main__":
    prods = regen()
    (OUT / "SOMMAIRE.md").write_text(sommaire(prods), encoding="utf-8")
    print(f"=== V4 → {OUT} ===")
    for p in prods:
        print(" ", p)
    print(f"\nSOMMAIRE.md écrit ({len(prods)} entrées).")
