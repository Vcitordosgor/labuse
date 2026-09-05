"""CIRCUIT-1 — LE REGISTRE (lot 1). Le socle : chaque chiffre est défini UNE fois
(chiffres.py), chaque robinet déclare ce qu'il sert (robinets.py), le graphe
réservoir → chiffre → robinet est DÉRIVÉ ici, la base n'en est qu'un miroir (sync.py).
"""
from __future__ import annotations

from .chiffres import ALIAS_TRANSITION, CHIFFRES, Chiffre, VERSION_DEF, resoudre   # noqa: F401
from .robinets import ROBINETS, Robinet                  # noqa: F401
from .valeur import Valeur, probleme_couverture, tampons_pour     # noqa: F401


def aretes() -> dict[str, list[tuple[str, str]]]:
    """Le graphe dérivé — jamais saisi deux fois : chiffre→robinet vient des déclarations des
    robinets, réservoir→chiffre des déclarations des chiffres."""
    c2r = sorted({(cid, rid) for rid, r in ROBINETS.items() for cid in r.chiffres})
    r2c = sorted({(res, cid) for cid, c in CHIFFRES.items() for res in c.reservoirs})
    return {"reservoir_vers_chiffre": [list(x) for x in r2c],
            "chiffre_vers_robinet": [list(x) for x in c2r]}


def verifier() -> list[str]:
    """Intégrité du registre (mêmes règles que valide_circuit.py de CIRCUIT-0) : chaque chiffre
    référencé existe, chaque chiffre est servi par ≥ 1 robinet, un robinet sans chiffre porte sa
    raison `hors_registre`. Rend la liste des problèmes (vide = OK)."""
    pb: list[str] = []
    servis: set[str] = set()
    for rid, r in ROBINETS.items():
        for cid in r.chiffres:
            if cid not in CHIFFRES:
                pb.append(f"robinet {rid} : chiffre inconnu {cid}")
            servis.add(cid)
        if not r.chiffres and not r.hors_registre:
            pb.append(f"robinet {rid} : ni chiffre ni raison hors_registre")
    for cid in CHIFFRES:
        if cid not in servis:
            pb.append(f"chiffre {cid} : servi par aucun robinet")
    return pb
