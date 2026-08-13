"""M78 · 2e — LE HÉROS : la meilleure parcelle, une phrase française qui dit pourquoi elle gagne
Y COMPRIS ses faiblesses (« au-dessus de votre budget, mais divisible »).

VERROU ANTI-INVENTION (testé) : la phrase est générée depuis le JSON de la parcelle, puis VÉRIFIÉE —
tout nombre de la phrase doit exister dans le JSON source (tolérance d'arrondi + variante /1000 pour
les « k€ »). Nombre absent → phrase rejetée et régénérée ; deux échecs → phrase GABARIT sans modèle
(jamais l'affirmation douteuse). Sonnet.
"""
from __future__ import annotations

from sqlalchemy.orm import Session

from ..ai import core
from .answering import _nombres

SYSTEM = """Tu es le copilote foncier de LABUSE. En UNE phrase française (30 mots maximum), dis pourquoi CETTE
parcelle arrive en tête du classement, Y COMPRIS sa principale FAIBLESSE (ex. « au-dessus de votre budget »,
« accès voirie à confirmer », « plus petite »). Uniquement à partir du JSON fourni. N'invente AUCUN chiffre :
tout nombre de ta phrase doit venir du JSON. Pas de superlatif creux, pas de conseil, pas d'invention de
qualité non présente. Réponds la phrase seule, sans guillemets ni préambule."""


def _valeurs(parcelle: dict, budget_max_eur: float | None) -> set[float]:
    """Nombres légitimes = valeurs du JSON parcelle (+ budget) et leurs variantes k€ (÷1000)."""
    autor: set[float] = set()
    for v in list(parcelle.values()) + [budget_max_eur]:
        if isinstance(v, (int, float)) and not isinstance(v, bool):
            autor.add(round(float(v), 2))
            autor.add(round(float(v)))
            if abs(v) >= 1000:                       # « 480 000 € » écrit « 480 k€ »
                autor.add(round(float(v) / 1000))
    return autor


def _phrase_ok(prose: str, autor: set[float]) -> bool:
    for n in _nombres(prose):
        if n in autor or round(n) in autor or any(abs(n - a) <= 1 for a in autor):
            continue
        return False
    return True


def _gabarit(p: dict) -> str:
    """Phrase de repli DÉTERMINISTE (aucun modèle) — jamais l'affirmation douteuse."""
    bouts = [f"Parcelle {p.get('idu')} à {p.get('commune')}"]
    if p.get("surface_m2") is not None:
        bouts.append(f"{round(p['surface_m2'])} m²")
    if p.get("zone"):
        bouts.append(f"zone {p['zone']}")
    tete = " · ".join(bouts) + " — en tête du classement instruit."
    if p.get("au_dessus_charge_supportable"):
        tete += " Réserve : au-dessus de votre charge foncière supportable."
    return tete


def phrase(db: Session | None, parcelle: dict, budget_max_eur: float | None = None) -> dict:
    """Génère la phrase du héros avec le verrou. Retourne {phrase, gabarit: bool}."""
    autor = _valeurs(parcelle, budget_max_eur)
    payload = {"parcelle": parcelle, "budget_max_eur": budget_max_eur}
    for _ in range(2):
        r = core.complete(db, kind="copilote-heros", model=core.MODEL_REASONING, max_tokens=120,
                          system=SYSTEM, context=payload)
        if r.degraded:
            break
        p = (r.text or "").strip().strip('"').strip()
        if p and _phrase_ok(p, autor):
            return {"phrase": p, "gabarit": False}
    return {"phrase": _gabarit(parcelle), "gabarit": True}
