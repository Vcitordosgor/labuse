"""ETUDE-STATIONNEMENT-FIX-3 (reliquat) — régénère, DEPUIS LE MÊME COMMIT, les 3 Études ET les 3 Dossiers
des parcelles témoins, pour que les deux documents portent la même version de calcul (dégagement dur, haie
mesurée, premier rideau, exigences de sol séparées, plafond national) et la MÊME surface à retenir.

  PYTHONPATH=src LABUSE_PDF_PROCESS_ISOLE=0 python scripts/stationnement_fix3_regen_dossiers.py
"""
import os
import sys
from datetime import datetime
from pathlib import Path

os.environ.setdefault("LABUSE_PDF_PROCESS_ISOLE", "0")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from labuse.db import session_scope  # noqa: E402
from labuse.exports import builder  # noqa: E402
from labuse.exports.etude_faisabilite import rendu_etude  # noqa: E402
from labuse.exports.rendu import render_pdf  # noqa: E402
from labuse.implantation import revisions as _rev  # noqa: E402
from labuse.implantation.service import etudier_payload  # noqa: E402

TEMOINS = ["97422000BW2635", "97416000HT0538", "97422000AD0887"]
OUT = Path(os.path.expanduser("~/Desktop/exports-audit-4"))
OUT.mkdir(parents=True, exist_ok=True)

# config PAR DÉFAUT COMPLÈTE de l'Étude (même clés/défauts que scenario_etude_persiste → même study_id).
CFG = lambda idu: {"idus": [idu], "type_projet": "collectif", "objectif": "equilibre",
                   "stationnement": "aerien", "terrain": "libere",
                   "niveaux_sous_sol": None, "programme": None, "hypotheses": None}


def main() -> int:
    genere_le = datetime.now().strftime("%d/%m/%Y")
    # 1) Études : rendu PDF + PERSISTANCE de la révision (pour que le Dossier lise le MÊME scénario).
    with session_scope() as s:
        try:
            from labuse.api.app import vider_fiche_cache_partage
            vider_fiche_cache_partage()
        except Exception as e:  # noqa: BLE001
            print(f"  (cache fiche non vidé : {e})")
        for idu in TEMOINS:
            payload = etudier_payload(s, CFG(idu))
            try:
                from labuse.api.modules import _attach_contraintes_signalees
                _attach_contraintes_signalees(s, payload, [idu])
            except Exception as e:  # noqa: BLE001
                print(f"    (alertes non enrichies {idu} : {e})")
            sid = _rev.enregistrer(s, payload)
            rendu = rendu_etude(payload, genere_le=genere_le)
            (OUT / f"etude_{idu}.pdf").write_bytes(render_pdf(rendu["html"]))
            print(f"  ✓ ÉTUDE {idu} → etude_{idu}.pdf (révision {sid}, verdict {payload.get('verdict')})",
                  flush=True)
        s.commit()
    # 2) Dossiers : construire(dossier) lit la révision persistée (surface à retenir identique à l'Étude).
    with session_scope() as s:
        from labuse.api.app import parcel_fiche
        for idu in TEMOINS:
            print(f"  … DOSSIER {idu} : fiche…", flush=True)
            fiche = parcel_fiche(idu, db=s)
            print(f"  … DOSSIER {idu} : construire…", flush=True)
            res = builder.construire(s, idu, "dossier", fiche=fiche)
            (OUT / f"dossier_{idu}.pdf").write_bytes(render_pdf(res.html))
            print(f"  ✓ DOSSIER {idu} → dossier_{idu}.pdf", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
