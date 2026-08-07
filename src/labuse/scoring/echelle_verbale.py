"""M52 Lot 1 — traduit le multiplicateur ×N en MOT (échelle verbale) et rend la fréquence MESURÉE
par tier. PRÉSENTATION SEULE : ne change aucun tier, aucun calcul. Seuils/mots/phrases en config
(`config/echelle_verbale_score.yaml`). Source de la fréquence DITE (arbitrage Vic, honnêteté M38)."""
from __future__ import annotations

import functools
import pathlib

import yaml


@functools.lru_cache(maxsize=1)
def _cfg() -> dict:
    p = pathlib.Path(__file__).resolve().parents[3] / "config" / "echelle_verbale_score.yaml"
    return yaml.safe_load(p.read_text())


def mot_du_multiplicateur(mult: float | None) -> dict | None:
    """×N → {mot, cle} selon les bandes config (bandes triées décroissant par `min`)."""
    if mult is None:
        return None
    for b in _cfg()["bandes"]:
        if mult >= b["min"]:
            return {"mot": b["mot"], "cle": b["cle"]}
    return None


def frequence_du_tier(tier: str | None) -> dict | None:
    """Fréquence « X sur 100 » du tier (backtest OOS). None si le tier n'a pas d'IC fiable
    (règle Vic : pas de mesure fiable → pas de phrase) — ex. écartée (étage 0)."""
    f = _cfg()["frequence"]
    t = (f.get("tiers") or {}).get(tier)
    if not t or not t.get("ic_fiable"):
        return None
    return {
        "sur_100": t.get("sur_100"),
        "base_sur_100": f["base_sur_100"],
        "fenetre": f["fenetre"],
        "sous_moyenne": bool(t.get("sous_moyenne", False)),
        "source_dite": f["source_dite"].strip(),
    }


def enrichir_verbal(mult: float | None, tier: str | None) -> dict:
    """{mot, cle, info, frequence?} — à joindre au payload score_v2 de la fiche. Champs absents
    si non applicables (jamais approximés)."""
    out: dict = {"info": _cfg()["info_multiplicateur"].strip()}
    m = mot_du_multiplicateur(mult)
    if m:
        out.update(m)
    fr = frequence_du_tier(tier)
    if fr:
        out["frequence"] = fr
    return out
