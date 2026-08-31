"""PROMO-1 (P3) — RATTACHEMENT programme ↔ opération. Rapprochement par PROMOTEUR (SIREN) + COMMUNE +
PROXIMITÉ DE PÉRIODE. Le score de confiance est une CONSTANTE ; en dessous du seuil, PAS de rattachement
automatique (l'admin lie à la main via un endpoint dédié). Un programme non rattaché reste visible sur la
page du promoteur, section « publiés sur leur site » (servie par l'outil).

Le rattachement est stocké sur le programme par les COORDONNÉES STABLES de l'opération (SIREN + commune +
année) — les opérations sont recalculées à la volée (union-find), elles n'ont pas d'id persistant.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

# Score de confiance du rapprochement AUTOMATIQUE (constante) : SIREN + commune valent 0,6 ; la
# proximité de période (année du programme vs année de l'opération) ajoute jusqu'à 0,4. Sous ce seuil,
# aucun rattachement auto — donc SANS année de programme (0,6 < 0,7), c'est toujours l'admin qui tranche.
SEUIL_RATTACHEMENT_AUTO = 0.7
BASE_SIREN_COMMUNE = 0.6
POIDS_PERIODE = 0.4
FENETRE_ANS = 5            # au-delà de 5 ans d'écart, la proximité de période n'apporte plus rien


def score(prog_annee: int | None, op_annee: int | None) -> float:
    """Score SIREN+commune (candidats déjà filtrés dessus) + proximité de période si l'année est connue
    des DEUX côtés. Sans année de programme, reste à 0,6 (sous le seuil → décision admin)."""
    s = BASE_SIREN_COMMUNE
    if prog_annee and op_annee:
        delta = abs(prog_annee - op_annee)
        s += POIDS_PERIODE * max(0.0, 1 - delta / FENETRE_ANS)
    return round(s, 2)


def candidats(db: Session, siren: str, commune: str) -> list[dict]:
    """Les OPÉRATIONS de ce promoteur (même SIREN) dans cette commune — l'univers du rapprochement."""
    from ..api.veille_promoteurs import _operations, _TOUS_GROUPES
    return [o for o in _operations(db, _TOUS_GROUPES, commune, None) if o["siren"] == siren]


def rapprocher(db: Session, *, siren: str | None, commune: str | None, annee: int | None) -> dict | None:
    """Rapproche un programme d'une opération. Retourne {op_siren, op_commune, op_annee, confiance,
    mode:'auto'} SI le meilleur candidat dépasse le seuil ET n'est pas à égalité avec un autre (jamais un
    rattachement ambigu) ; sinon None (l'admin liera à la main)."""
    if not siren or not commune:
        return None
    ops = candidats(db, siren, commune)
    if not ops:
        return None
    scored = sorted(((score(annee, o.get("annee")), o) for o in ops), key=lambda x: -x[0])
    best_s, best = scored[0]
    ambigu = len(scored) > 1 and scored[1][0] >= best_s     # ex æquo → on ne devine pas
    if best_s >= SEUIL_RATTACHEMENT_AUTO and not ambigu:
        return {"op_siren": best["siren"], "op_commune": best["commune"], "op_annee": best.get("annee"),
                "confiance": best_s, "mode": "auto"}
    return None
