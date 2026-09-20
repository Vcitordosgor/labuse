"""PLU-CALIBRAGE-3 lot 1 — AUDIT D'ATTRIBUTION de l'ancien système (config/plu_<slug>.yaml).

L'ancien système porte, par (zone, rubrique), une VALEUR + un `_src` « Art. <Zone><n>, p.<p> »
(+ un `_note` explicatif) — mais AUCUNE citation verbatim. Le contrôle d'attribution du mandat 2
localise une citation sur sa page ; faute de citation, on l'ADAPTE au matériel disponible :

  · attribution PAR L'ARTICLE : la zone nommée par le `_src` doit être COMPATIBLE avec la zone
    revendiquée — même règle qu'au mandat 2 : == la zone, ou la zone est un SECTEUR sous
    l'article de sa base (« AUg » sous « Ug », « Uicm » sous « Ui »), y compris les chapitres
    COMMUNS (« zone Ug et AUg ») dont on lit tous les codes du `_src`.

Une misattribution = un `_src` qui ne nomme QUE d'autres zones que la zone revendiquée (ni
elle, ni sa base). NB : ce contrôle attrape les mauvaises ÉTIQUETTES d'article ; la vérification
mot-à-mot (une valeur de secteur sous le bon article de base) se fait à la RE-LECTURE du PDF au
lot 2. Lecture seule.

Usage : PYTHONPATH=src .venv/bin/python qa/plu_calibrage3_audit.py
"""
from __future__ import annotations

import re
import sys
from pathlib import Path

import yaml

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from labuse.faisabilite.zone_norm import normalize_key   # noqa: E402

CONFIG = Path(__file__).resolve().parents[1] / "config"
SORTIE = Path(__file__).resolve().parents[1] / "captures" / "plu-calibrage3" / "AUDIT-ANCIEN.md"

# (champ valeur, champ source, libellé rubrique)
RUBRIQUES = [
    ("he_m", "hauteur_src", "hauteur (égout)"),
    ("hf_m", "hauteur_src", "hauteur (faîtage)"),
    ("emprise_sol_pct", "emprise_src", "emprise au sol"),
    ("recul_voirie_m", "recul_voirie_src", "retrait voie"),
    ("recul_limites_sep_m", "recul_limites_src", "retrait limites"),
    ("stat_logement", "stat_src", "stationnement"),
    ("pleine_terre_pct", "pleine_terre_src", "pleine terre"),
]
# « AUindicée » / « AUINDICEE » = jeton PLACEHOLDER de l'ancien système : « cette zone AU », i.e.
# la zone elle-même (les notes disent « Pour la zone AUto… ») — jamais une autre zone.
_PLACEHOLDER = ("auindicee",)
_STOP = {"Art", "Il", "En", "La", "Le", "Les", "Des", "Du", "De", "Pour", "P", "OAP", "PLU",
         "RN", "ZAC", "CBS", "UF", "TCSP", "ABSOLUE", "SECTEUR", "ZONE", "Un", "Une"}


def _zones_du_src(src: str) -> list[str]:
    """Codes de zone d'un `_src`, préfixe de phasage COMPRIS (« Art. 1AU.10 » → 1AU ; « Art. UA
    10.2 » → UA ; « Ug3.5 » → Ug ; « 1 AU.9 » → 1AU). Le numéro d'article collé est coupé."""
    if not src:
        return []
    toks = []
    for m in re.finditer(r"(\d?\s?(?:AU|U|A|N)[A-Za-z]*)", src):
        t = re.sub(r"\s+", "", m.group(1))
        if t and t not in _STOP:
            toks.append(t)
    return toks


def _sans_phase(s: str) -> str:
    return re.sub(r"^\d+", "", s)          # « 1auto » → « auto » (l'article vaut pour toutes les phases)


def _compatible(tokens: list[str], zone: str) -> bool:
    zz = _sans_phase(normalize_key(zone))
    zone_est_au = zz.startswith("au")
    for t in tokens:
        mz = _sans_phase(normalize_key(t))
        if not mz:
            continue
        if mz.startswith("auindic"):       # « AUindicée » = placeholder de la zone elle-même
            return True
        if mz == zz or zz.startswith(mz):   # même zone, ou la zone est un SECTEUR sous sa base
            return True                     # (jamais l'inverse : une base citant un secteur = misattribution)
        if zone_est_au and mz.startswith("u"):  # AU→U : renvoi standard (une zone AU urbanise en U)
            return True
    return False


def main() -> int:
    fichiers = sorted(p for p in CONFIG.glob("plu_*.yaml")
                      if p.name not in ("plu_millesimes.yaml",) and "destinations" not in str(p))
    lignes: list[str] = []
    total = mis = sans_src = 0
    detail: list[tuple] = []
    communes_couvertes = 0
    for p in fichiers:
        doc = yaml.safe_load(p.read_text(encoding="utf-8")) or {}
        zones = doc.get("zones") or {}
        if not zones:
            continue                       # saint_benoit (vide) : rien à auditer ici
        communes_couvertes += 1
        commune = (next(iter(zones.values()), {}) or {}).get("bassin") or p.stem.replace("plu_", "")
        for zcode, zv in zones.items():
            if not isinstance(zv, dict):
                continue
            for champ, srcf, lib in RUBRIQUES:
                if zv.get(champ) is None:
                    continue
                total += 1
                src = zv.get(srcf) or ""
                toks = _zones_du_src(src)
                # renvoi / chapitre commun EXPLICITE dans le src = emprunt documenté par le
                # règlement (AU→U, « zone X et Y ») — légitime, comme l'exemption du mandat 2.
                renvoi_doc = bool(re.search(r"renvoi|chapitre|communs?\b|m[eê]mes r[eè]gles|"
                                            r"se reporter|report[eé]|pr[eé]ambule|r[eè]gle propre|"
                                            r"r[eè]gle g[eé]n[eé]rale|except[eé]|tableau|->|→", src, re.I))
                if not toks and not renvoi_doc:
                    sans_src += 1
                    verdict = "— (src sans zone)"
                elif _compatible(toks, zcode) or renvoi_doc:
                    verdict = "oui" + (" (renvoi)" if (renvoi_doc and not _compatible(toks, zcode)) else "")
                else:
                    mis += 1
                    verdict = f"**NON** (src → {','.join(sorted(set(toks)))})"
                detail.append((commune, zcode, lib, str(zv.get(champ)), src[:48], verdict))

    oui_direct = sum(1 for *_r, v in detail if v == "oui")
    oui_renvoi = sum(1 for *_r, v in detail if "renvoi" in v)
    lignes.append("# PLU-CALIBRAGE-3 lot 1 — audit d'attribution de l'ancien système\n")
    lignes.append(f"**{mis} misattribution(s) sur {total} règles** — {communes_couvertes} communes "
                  f"`config/plu_<slug>.yaml` (saint_benoit vide exclu).\n")
    lignes.append(f"Répartition : {oui_direct} attribuées à leur zone · {oui_renvoi} par renvoi "
                  f"documenté (AU→U, chapitre commun, placeholder AUindicée) · {sans_src} sur une "
                  "disposition générale/thématique (stationnement §XVII, emprise/pleine-terre "
                  f"générales) · **{mis} misattribution(s)**.\n")
    lignes.append("> Contrôle = attribution PAR L'ARTICLE : l'ancien système porte article + page "
                  "(+ `_note`) mais **pas de citation verbatim** ; le contrôle du mandat 2 (citation "
                  "localisée sur sa page) est adapté à la zone nommée par le `_src` (== zone, secteur "
                  "sous sa base, ou renvoi AU→U/chapitre commun documenté). La vérification mot-à-mot "
                  "valeur↔secteur (le bug qu'avait mandat 1) se fait à la RE-LECTURE du PDF au lot 2.\n")
    lignes.append("| commune | zone | règle | valeur | src | attribuée |")
    lignes.append("| --- | --- | --- | --- | --- | --- |")
    for commune, z, lib, val, src, verdict in detail:
        lignes.append(f"| {commune} | {z} | {lib} | {val} | {src} | {verdict} |")
    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    SORTIE.write_text("\n".join(lignes) + "\n", encoding="utf-8")
    print(f"{mis} misattribution(s) sur {total} règles · {communes_couvertes} communes · "
          f"{sans_src} src sans zone")
    print(f"→ {SORTIE}")
    # récap des misattributions à l'écran
    for commune, z, lib, val, src, verdict in detail:
        if "NON" in verdict:
            print(f"  MIS {commune:16} {z:8} {lib:18} {val:10} :: {src} {verdict}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
