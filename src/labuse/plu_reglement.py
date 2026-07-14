"""Lien vers le règlement PLU par zone — M9 lot 2.

Chaque zone affichée en fiche renvoie vers la page/section exacte du règlement PLU.
La traçabilité article/page vit dans les YAML calibrés (`config/plu_<commune>.yaml`,
clés `*_src` + bloc `source`) ; ce module la relaie SANS rien inventer :

  - commune OUTILLÉE (YAML présent) → document + URL + citations article/page ;
    quand la page imprimée est connue, on construit un lien profond `…pdf#page=N`
    (N = page imprimée + `offset_pdf_vs_imprimee`).
  - commune NON OUTILLÉE → repli propre : référence GPU (idurba) + note explicite,
    jamais une page inventée.
"""

from __future__ import annotations

import re

from .faisabilite.plu_rules import _calibrated_yaml, _doc, resolve_zone

_GPU_CONSULT = "https://www.geoportail-urbanisme.gouv.fr/"


def _page_imprimee(reference: str) -> int | None:
    """Première page imprimée citée dans une référence (« Art. 10.2, p.20-21 » → 20)."""
    m = re.search(r"p\.?\s*(\d+)", reference or "")
    return int(m.group(1)) if m else None


def resolve_reglement(commune: str | None, zone_code: str | None,
                      idurba: str | None = None) -> dict | None:
    """Référence règlement d'UNE zone. None si code de zone vide."""
    if not zone_code:
        return None
    yaml_path = _calibrated_yaml(commune)
    if yaml_path is None:
        # Commune non outillée : repli propre (pas de deep link fiable).
        return {
            "zone": zone_code,
            "calibree": False,
            "document": None,
            "url": _GPU_CONSULT,
            "idurba": idurba,
            "articles": [],
            "note": "Règlement PLU non outillé pour cette commune — consultez le "
                    "Géoportail de l'Urbanisme (recherche par commune)."
                    + (f" Réf. document : {idurba}." if idurba else ""),
        }

    doc = _doc(commune)
    src = doc.get("source", {}) or {}
    base_url = src.get("url")
    offset = int(src.get("offset_pdf_vs_imprimee") or 0)
    rules = resolve_zone(zone_code, commune)

    articles = []
    if rules and rules.calibree and rules.sources:
        for regle, reference in rules.sources.items():
            pi = _page_imprimee(reference)
            url_page = (f"{base_url}#page={pi + offset}" if base_url and pi else base_url)
            articles.append({"regle": regle, "reference": reference,
                             "page_imprimee": pi, "url": url_page})
        articles.sort(key=lambda a: (a["page_imprimee"] is None, a["page_imprimee"] or 0))

    # Lien « primaire » = première page citée (sinon document nu).
    deep = articles[0]["url"] if articles else base_url
    calibree = bool(rules and rules.calibree and articles)
    return {
        "zone": zone_code,
        "calibree": calibree,
        "document": src.get("document"),
        "url": deep,
        "url_document": base_url,
        "approbation": src.get("approbation"),
        "edition": src.get("edition"),
        "idurba": idurba,
        "articles": articles,
        "note": None if calibree else
                "Zone hors périmètre calibré du règlement — lien vers le document complet ; "
                "référez-vous à l'article de la zone.",
    }


def reglement_block(zones: list[dict], commune: str | None) -> dict | None:
    """Bloc fiche : une référence règlement par zone distincte de la parcelle.

    `zones` : lignes {zone, libelle, idurba} (croisement plu_gpu_zone). Dédoublonne
    par code de zone. None si aucune zone."""
    if not zones:
        return None
    seen: dict[str, dict] = {}
    for z in zones:
        code = z.get("libelle") or z.get("zone")
        if not code or code in seen:
            continue
        ref = resolve_reglement(commune, code, z.get("idurba"))
        if ref:
            seen[code] = ref
    if not seen:
        return None
    return {
        "zones": list(seen.values()),
        "disclaimer": "Le règlement PLU fait foi ; les valeurs affichées sont une "
                      "aide à la lecture, non un certificat d'urbanisme.",
    }
