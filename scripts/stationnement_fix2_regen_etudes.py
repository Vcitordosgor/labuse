"""ETUDE-STATIONNEMENT-FIX-2 — régénère les 3 Études témoins APRÈS le dernier commit, pour que chaque PDF
porte la version de calcul (stamp commit) et reflète les correctifs (plafond national, barème par m² de SDP
« servi », dégagement d'allée local). À lancer depuis le worktree, base locale disponible.

  python scripts/stationnement_fix2_regen_etudes.py
"""
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("LABUSE_PDF_PROCESS_ISOLE", "0")   # rendu in-process (pas de spawn __main__)
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from labuse.db import session_scope  # noqa: E402
from labuse.exports.etude_faisabilite import rendu_etude, rendu_hors_perimetre  # noqa: E402
from labuse.exports.rendu import render_pdf  # noqa: E402
from labuse.implantation.service import etudier_payload  # noqa: E402

TEMOINS = [
    ("97422000BW2635", "Le Tampon — dégagement d'allée (LOT 3)"),
    ("97416000HT0538", "Saint-Pierre — barème par m² de SDP servi (LOT 4)"),
    ("97422000AD0887", "Le Tampon — zone humide (reprise des alertes de la fiche)"),
]

# reliquat #7 — livraison des Études régénérées dans ~/Desktop/exports-audit-4/ (emplacement demandé).
OUT = Path(os.path.expanduser("~/Desktop/exports-audit-4"))
OUT.mkdir(parents=True, exist_ok=True)


def main() -> int:
    genere_le = datetime.now().strftime("%d/%m/%Y")
    with session_scope() as s:
        for idu, note in TEMOINS:
            entree = {"idus": [idu], "type_projet": "collectif", "objectif": "equilibre",
                      "stationnement": "aerien", "terrain": "libere"}
            try:
                payload = etudier_payload(s, entree)
            except ValueError as e:
                print(f"  {idu} : entrée refusée — {e}")
                continue
            try:
                rendu = rendu_etude(payload, genere_le=genere_le)
            except ValueError:
                # parcelle non constructible / hors périmètre : document de refus (toujours un PDF honnête)
                rendu = rendu_hors_perimetre(payload, genere_le=genere_le) \
                    if payload.get("verdict", "").startswith("Étude hors") else None
                if rendu is None:
                    print(f"  {idu} : {payload.get('verdict')} — {payload.get('message')}")
                    continue
            pdf = render_pdf(rendu["html"])
            dest = OUT / f"etude_{idu}.pdf"
            dest.write_bytes(pdf)
            print(f"  ✓ {idu} ({note}) → {dest.name}  [{len(pdf) // 1024} Kio, n° {rendu.get('numero')}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
