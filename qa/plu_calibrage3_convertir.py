"""PLU-CALIBRAGE-3 lot 2 — CONVERSION PRÉSERVANTE d'un ancien plu_<slug>.yaml vers le bloc
`regles` de plu_destinations. On GARDE les valeurs auditées (lot 1 : 0 misattribution) et on
RE-LIT le PDF uniquement pour la citation verbatim + le contrôle d'attribution :

  · valeur numérique + citation trouvée + attribution OK   → statut `valide` ;
  · sinon (valeur `a_verifier`, citation INTROUVABLE, ou attribution douteuse) → `propose`
    avec la raison — jamais un `valide` sans preuve (verrou V6a).

Base/secteur : on conserve les codes de zone de l'ancien système (ils distinguent déjà) ; une
citation qui relève d'un autre secteur (drapeau de la re-lecture) fait passer `propose`.

Usage : PYTHONPATH=src .venv/bin/python qa/plu_calibrage3_convertir.py <insee> <slug> <citations.json>
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

import fitz
import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labuse.plu import destinations as D          # noqa: E402
from labuse.plu import extraction as X            # noqa: E402
sys.path.insert(0, str(Path(__file__).resolve().parent))
from plu_calibrage2_sondage import _attribution, _extrait_autour  # noqa: E402

# ancien champ → (rubrique, feuille, clé de valeur, coercition)
MAP = {
    "hf_m": ("hauteur", "faitage", "m", float),
    "he_m": ("hauteur", "egout", "m", float),
    "emprise_sol_pct": ("emprise_sol", "ces", "pct", float),
    "recul_voirie_m": ("retraits", "voie", "min_m", float),
    "recul_limites_sep_m": ("retraits", "limites_separatives", "min_m", float),
    "stat_logement": ("stationnement", "par_logement", "places", "places"),
    "pleine_terre_pct": ("pleine_terre", "pct", "pct", float),
}
_SRC = {"he_m": "hauteur_src", "hf_m": "hauteur_src", "emprise_sol_pct": "emprise_src",
        "recul_voirie_m": "recul_voirie_src", "recul_limites_sep_m": "recul_limites_src",
        "stat_logement": "stat_src", "pleine_terre_pct": "pleine_terre_src"}


def _parse_src(src: str):
    """« Art. Ua 10.2, p.24 » → ('Ua 10.2', 24)."""
    if not src:
        return None, None
    page = None
    mp = re.search(r"p\.?\s*(\d+)", src)
    if mp:
        page = int(mp.group(1))
    ma = re.search(r"Art\.?\s*([A-Za-z0-9 .\-/]+?)(?:,|\s+p\.|$|\()", src)
    art = ma.group(1).strip() if ma else src.split(",")[0].strip()
    return art, page


def _places(stat: str):
    """« 1,5 place / logement » → 1.5 ; None si non chiffrable par logement."""
    m = re.search(r"(\d+(?:[.,]\d+)?)\s*places?\s*/?\s*(?:par\s*)?logement", str(stat), re.I)
    return float(m.group(1).replace(",", ".")) if m else None


def convertir(insee: str, slug: str, citations_path: str) -> dict:
    old = yaml.safe_load(Path(f"config/plu_{slug}.yaml").read_text(encoding="utf-8")) or {}
    cits = json.loads(Path(citations_path).read_text(encoding="utf-8"))
    dest = D._fichier_commune(insee)
    meta = (D._load_yaml(str(dest)).get("meta") or {})
    pdf = fitz.open(str(Path("data/plu_reglements") / meta["document"]))

    stats = {"valide": 0, "propose": 0}
    regles_par_zone: dict[str, dict] = {}
    for zone, zv in (old.get("zones") or {}).items():
        if not isinstance(zv, dict):
            continue
        regles: dict = {}
        zcit = cits.get(zone, {})
        for champ, (rub, feuille, cle, coerce) in MAP.items():
            if zv.get(champ) is None:
                continue
            art, page = _parse_src(zv.get(_SRC[champ]) or "")
            c = zcit.get(champ, {}) or {}
            citation = c.get("citation")
            page_c = c.get("page_confirmee") or page
            # valeur
            raison = None
            val_ok = True
            if coerce == "places":
                v = _places(zv[champ])
                if v is None:
                    val_ok, raison = False, f"stationnement non chiffrable par logement ({zv[champ]!r})"
            else:
                try:
                    v = coerce(zv[champ])
                except (TypeError, ValueError):
                    v = None
                    val_ok, raison = False, f"valeur non numérique ({zv[champ]!r})"
            # citation + attribution
            att = "general"
            if not citation or citation == "INTROUVABLE":
                val_ok = val_ok and False
                raison = raison or "citation INTROUVABLE à la re-lecture du PDF"
                citation = citation or None
            else:
                txt = pdf.load_page(page_c - 1).get_text() if (isinstance(page_c, int) and 1 <= page_c <= pdf.page_count) else ""
                _e, sc, bi = _extrait_autour(txt, citation)
                _m, att = _attribution(txt, citation, zone, bi)
                if sc < 0.5:
                    val_ok, raison = False, f"citation non retrouvée sur p.{page_c} (recouvrement {sc:.0%})"
                elif att == "misattribue":
                    val_ok, raison = False, f"attribution douteuse (citation sous secteur {_m})"
            feuille_d = {cle: v, "article": art, "page_pdf": page_c,
                         "citation": citation or "(à relire)",
                         "statut": "valide" if (val_ok and citation and citation != "INTROUVABLE") else "propose"}
            if feuille_d["statut"] == "propose" and raison:
                feuille_d["raison"] = raison
            stats[feuille_d["statut"]] += 1
            regles.setdefault(rub, {})[feuille] = feuille_d
        if regles:
            regles_par_zone[zone] = regles
    X._ecrire_regles(dest, regles_par_zone)
    D._load_yaml.cache_clear()
    print(f"{slug} ({insee}) : {stats['valide']} valide · {stats['propose']} propose "
          f"· {len(regles_par_zone)} zones")
    return stats


if __name__ == "__main__":
    convertir(sys.argv[1], sys.argv[2], sys.argv[3])
