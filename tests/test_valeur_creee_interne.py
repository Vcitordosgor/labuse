"""URGENCE-1 (Décision 5 / NU-E-012) — GARDE : la « valeur créée » du scoring reste INTERNE.

`valeur_creee_eur` (et ses bornes) est un CA brut sans aucun coût (jusqu'à ~878 M€) : utile au
classement interne, JAMAIS un chiffre à montrer. Elle ne doit apparaître nulle part côté client —
écran (frontend), PDF (exports/builders), Copilote, ni API servie. Ce test échoue si une surface
client la nomme. Elle reste libre dans le module de calcul (`scoring/p_v2/`) et l'outillage CLI admin.
"""
from __future__ import annotations

from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]

# surfaces CLIENT : tout ce qui peut atteindre un écran, un PDF ou le Copilote.
_SURFACES = (
    "frontend/src",
    "src/labuse/api",
    "src/labuse/exports",
    "src/labuse/copilote_v2",
)
_EXTS = (".py", ".ts", ".tsx")
_INTERDITS = ("valeur_creee", "valeur créée", "valeur cree", "indice_opportunite", "indice d'opportun")


def test_valeur_creee_absente_des_surfaces_client():
    fautes: list[str] = []
    for d in _SURFACES:
        base = _ROOT / d
        if not base.exists():
            continue
        for p in base.rglob("*"):
            if p.suffix not in _EXTS or "node_modules" in p.parts or "__pycache__" in p.parts:
                continue
            txt = p.read_text(encoding="utf-8", errors="ignore").lower()
            for mot in _INTERDITS:
                if mot in txt:
                    fautes.append(f"{p.relative_to(_ROOT)} contient « {mot} »")
    assert not fautes, ("« valeur créée » (CA brut du scoring) fuit sur une surface client — "
                        "doit rester interne (Décision 5 / NU-E-012) :\n" + "\n".join(fautes))
