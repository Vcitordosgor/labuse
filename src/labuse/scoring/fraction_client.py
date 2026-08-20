"""M135 — la probabilité calibrée servie (p_raw) dite en FRACTION humaine (« 1/5 sous 1 an »).

AUCUN calcul du modèle ne change : p_raw est la sortie calibrée du run servi, on la RESTITUE.
Règle (config/scoring_client.yaml) : le palier humain dont la probabilité (1/d) est la plus
proche de p. Garde-fous de véracité :
  · le plus grand palier PLAFONNE (1/2) — la saturation isotonique connue aux extrêmes (p→1,0)
    ne devient JAMAIS « 1/1 » ;
  · sous le plus petit palier (p < 0,02) : pas de fraction, un tiret « — » (« peu probable »).
Calculé UNE fois côté serveur → carte de tri, fiche et PDF disent la MÊME fraction (cohérence).
"""
from __future__ import annotations

from ..config import load_yaml_config


def _cfg() -> dict:
    f = load_yaml_config("scoring_client")["fraction"]
    return {"paliers": [int(d) for d in f["paliers"]], "seuil_bas_p": float(f["seuil_bas_p"])}


def fraction_humaine(p_raw: float | None, cfg: dict | None = None) -> dict | None:
    """(p_raw) → {'denominateur': d, 'texte': '1/d'} ou None (= « — », peu probable).

    None si p manquant/≤0 ou sous le seuil bas. Le palier retenu = nearest-en-probabilité
    (le 1/2 plafonne, jamais 1/1)."""
    c = cfg or _cfg()
    if p_raw is None or p_raw <= 0:
        return None
    if p_raw < c["seuil_bas_p"]:
        return None
    d = min(c["paliers"], key=lambda k: abs(1.0 / k - p_raw))   # palier le plus proche en proba
    return {"denominateur": d, "texte": f"1/{d}"}


def fraction_sql_case(col: str, cfg: dict | None = None) -> str:
    """M135 — le MÊME arrondi que fraction_humaine, en SQL (pour le geojson carte, assemblé et
    caché en SQL). GÉNÉRÉ depuis la config (mêmes paliers) → aucune dérive : un test compare
    fraction_sql_case et fraction_humaine sur toute la plage. Renvoie une expression texte
    ('1/d' ou NULL). Les bornes sont les milieux en probabilité entre paliers consécutifs ;
    le plus grand palier plafonne (jamais 1/1), sous le seuil bas → NULL (« — »)."""
    c = cfg or _cfg()
    paliers = c["paliers"]
    seuil = c["seuil_bas_p"]
    # milieux décroissants : (palier_i, borne_basse en p) — au-dessus de la borne → ce palier
    bornes = []
    for i, d in enumerate(paliers):
        p_i = 1.0 / d
        lo = (p_i + 1.0 / paliers[i + 1]) / 2 if i + 1 < len(paliers) else seuil  # dernier : jusqu'au seuil
        bornes.append((d, lo))
    whens = "\n".join(f"WHEN {col} >= {lo:.6f} THEN '1/{d}'" for d, lo in bornes)
    return (f"CASE WHEN {col} IS NULL OR {col} < {seuil:.6f} THEN NULL\n{whens} ELSE NULL END")
