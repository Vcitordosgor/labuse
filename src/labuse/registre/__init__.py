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
    """Intégrité du registre (règles CIRCUIT-0, élargies CIRCUIT-2 lot 1) :
    · chaque donnée référencée existe ; chaque donnée est servie par ≥ 1 robinet — SAUF
      `en_attente` (déclarée pour un chantier nommé), qui ne doit être servie par AUCUN ;
    · un robinet sans donnée n'est admis que « décor : … » (1.2 — hors_registre vidé) ;
    · le type ∈ TYPES ; une `classe` déclare son domaine (valeurs + source) ; une `couche`
      déclare sa table/tuilage et sa fabrication.
    Rend la liste des problèmes (vide = OK)."""
    from .donnees import TYPES
    pb: list[str] = []
    servis: set[str] = set()
    for rid, r in ROBINETS.items():
        for cid in r.chiffres:
            if cid not in CHIFFRES:
                pb.append(f"robinet {rid} : donnée inconnue {cid}")
            servis.add(cid)
        if not r.chiffres and not r.hors_registre:
            pb.append(f"robinet {rid} : ni donnée ni raison hors_registre")
        if not r.chiffres and r.hors_registre and not r.hors_registre.startswith("décor"):
            pb.append(f"robinet {rid} : hors_registre non-décor interdit (lot 1.2) : {r.hors_registre}")
    for cid, d in CHIFFRES.items():
        if d.en_attente:
            if cid in servis:
                pb.append(f"donnée {cid} : en_attente ({d.en_attente}) mais SERVIE par un robinet")
        elif cid not in servis:
            pb.append(f"donnée {cid} : servie par aucun robinet")
        if d.type not in TYPES:
            pb.append(f"donnée {cid} : type inconnu {d.type}")
        if d.type == "classe" and not (d.domaine or d.domaine_source):
            pb.append(f"donnée {cid} : classe sans domaine déclaré (lot 1.1)")
        if d.type == "couche" and not (d.table and d.fabrication):
            pb.append(f"donnée {cid} : couche sans table/fabrication (lot 1.1)")
    return pb
