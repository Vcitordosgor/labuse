"""RETOUCHES-1 point 2 — LE libellé unique de la taxe foncière (bâti / non bâti).

Un seul producteur : la fiche, le Dossier et le Copilote affichent la MÊME ligne. On sert la PART
COMMUNALE et, quand elle est connue, la TEOM (taux réel, utile), puis on DIT ce qui manque encore
(« hors part départementale et taxes spéciales ») — au lieu d'énumérer « EPCI 0,00 % » (part nulle,
bruit) comme si tout s'additionnait à un total. La TEOM s'affiche quand on l'a et disparaît sinon ;
elle ne s'applique qu'au bâti (TFPB), jamais au non-bâti (TFPNB).
"""
from __future__ import annotations

#: ce que le taux affiché NE comprend PAS — dit une seule fois, partout pareil.
_HORS = "hors part départementale et taxes spéciales"


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
    """[{label, detail, ligne}] — bâti (TFPB, avec TEOM si connue) puis non-bâti (TFPNB) si servi.
    `ligne` = label + ' — ' + detail, la chaîne canonique affichée à l'identique par les trois
    surfaces. `[]` si rien à dire."""
    if not isinstance(fisc, dict):
        return []
    teom = _pct(fisc.get("teom_pct"))
    out = []
    bati = _pct(fisc.get("tfpb_commune_pct"))
    if bati:
        bits = [f"part communale {bati}"]
        if teom:                       # la TEOM s'affiche quand on l'a, disparaît sinon (bâti seul)
            bits.append(f"TEOM {teom}")
        detail = " · ".join(bits) + f" · {_HORS}"
        out.append({"label": "Taxe foncière (bâti)", "detail": detail,
                    "ligne": f"Taxe foncière (bâti) — {detail}"})
    nonbati = _pct(fisc.get("tfpnb_commune_pct"))
    if nonbati:                        # la TEOM ne grève pas le non-bâti : jamais listée ici
        detail = f"part communale {nonbati} · {_HORS}"
        out.append({"label": "Taxe foncière (non bâti)", "detail": detail,
                    "ligne": f"Taxe foncière (non bâti) — {detail}"})
    return out
