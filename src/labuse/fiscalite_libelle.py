"""RETOUCHES-1 point 2 — LE libellé unique de la taxe foncière (bâti / non bâti).

Un seul producteur : la fiche, le Dossier et le Copilote affichent la MÊME ligne. Le taux servi
par le REI (DGFiP) est la seule PART COMMUNALE ; on le DIT explicitement (« hors part
départementale, TEOM et taxes spéciales ») au lieu d'énumérer « EPCI 0,00 % · TEOM 16,00 % »
comme s'ils s'additionnaient à un total — le lecteur croyait lire la taxe foncière entière alors
qu'il manquait la part départementale (et les taxes spéciales).
"""
from __future__ import annotations

#: ce que le taux communal NE comprend PAS — dit une seule fois, partout pareil.
_HORS = "hors part départementale, TEOM et taxes spéciales"


def _pct(v) -> str | None:
    """« 48,68 % » depuis un nombre ; None si absent/illisible. Deux décimales, virgule décimale."""
    if v is None:
        return None
    try:
        n = float(v)
    except (TypeError, ValueError):
        return None
    return f"{n:.2f}".replace(".", ",") + " %"


def lignes_taxe_fonciere(fisc) -> list[dict]:
    """[{label, detail, ligne}] — bâti (TFPB) puis non-bâti (TFPNB) si servi. `ligne` = label + ' — '
    + detail, la chaîne canonique affichée à l'identique par les trois surfaces. `[]` si rien à dire."""
    if not isinstance(fisc, dict):
        return []
    out = []
    for pct, label in ((_pct(fisc.get("tfpb_commune_pct")), "Taxe foncière (bâti)"),
                       (_pct(fisc.get("tfpnb_commune_pct")), "Taxe foncière (non bâti)")):
        if pct:
            detail = f"part communale {pct} · {_HORS}"
            out.append({"label": label, "detail": detail, "ligne": f"{label} — {detail}"})
    return out
