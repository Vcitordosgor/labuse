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

from .faisabilite.zonage import A_VERIFIER, est_outillee, reglement_source, resolve_zone

_GPU_CONSULT = "https://www.geoportail-urbanisme.gouv.fr/"


def _page_imprimee(reference: str) -> int | None:
    """Première page imprimée citée dans une référence (« Art. 10.2, p.20-21 » → 20)."""
    m = re.search(r"p\.?\s*(\d+)", reference or "")
    return int(m.group(1)) if m else None


def _fmt_valeur(v, unite: str) -> tuple[str | None, str]:
    """RETOURS-11F3 F4 — formate une valeur de règle PLU + son état. Jamais une valeur inventée :
    None = « non réglementé » (le PLU dit « il n'est pas fixé de règle »), a_verifier = « à vérifier »
    (présent mais ambigu, on ne comble pas). Retourne (texte | None si à masquer, etat)."""
    if v is None:
        return "non réglementé", "absent"
    if v == A_VERIFIER:
        return "à vérifier au règlement", "a_verifier"
    if isinstance(v, (int, float)):
        n = int(v) if float(v).is_integer() else v
        return f"{n} {unite}".strip(), "chiffre"
    return str(v), "texte"   # ex. stationnement « 1 place / logement »


def _regles_valeurs(rules, base_url: str | None, offset: int) -> list[dict]:
    """Le TABLEAU des règles clés de la zone AVEC leurs VALEURS (F4) — pas seulement des références
    d'articles. Chaque ligne : libellé · valeur formatée · état · source (article/page) + lien profond.
    Une hauteur combine faîtage (hf) et égout (he) quand les deux sont chiffrés."""
    def _url(ref):
        pi = _page_imprimee(ref or "")
        return f"{base_url}#page={pi + offset}" if base_url and pi else base_url

    src = rules.sources or {}
    exc_all = getattr(rules, "exceptions", None) or {}

    def _exc(cle: str) -> list[dict]:
        # PLU-EXCEPTIONS-1 — les exceptions de la règle, servies AVEC elle (id `<cle>.exception`),
        # relayées telles quelles (texte verbatim + article + page + porte). Jamais recomposé.
        return [{"id": f"{cle}.exception", **e} for e in (exc_all.get(cle) or [])]

    out: list[dict] = []
    # Hauteur — faîtage prioritaire, égout en complément (le règlement raisonne au faîtage par défaut).
    htxt, hetat = None, "absent"
    if isinstance(rules.hf_m, (int, float)) or isinstance(rules.he_m, (int, float)):
        parts = []
        if isinstance(rules.hf_m, (int, float)):
            parts.append(f"{int(rules.hf_m) if float(rules.hf_m).is_integer() else rules.hf_m} m au faîtage")
        if isinstance(rules.he_m, (int, float)):
            parts.append(f"{int(rules.he_m) if float(rules.he_m).is_integer() else rules.he_m} m à l'égout")
        htxt, hetat = " · ".join(parts), "chiffre"
    elif rules.hf_m == A_VERIFIER or rules.he_m == A_VERIFIER:
        htxt, hetat = "à vérifier au règlement", "a_verifier"
    else:
        htxt, hetat = "non réglementé", "absent"
    ref_h = src.get("hauteur")
    out.append({"cle": "hauteur", "libelle": "Hauteur max", "valeur": htxt, "etat": hetat,
                "reference": ref_h, "url": _url(ref_h), "exceptions": _exc("hauteur")})
    for cle, libelle, val, unite, skey in (
        ("emprise", "Emprise au sol max", rules.emprise_sol_pct, "%", "emprise"),
        ("recul_voirie", "Recul sur voie", rules.recul_voirie_m, "m", "recul_voirie"),
        ("recul_limites", "Recul limites séparatives", rules.recul_limites_sep_m, "m", "recul_limites"),
        ("pleine_terre", "Pleine terre min", rules.pleine_terre_pct, "%", "pleine_terre"),
        ("stationnement", "Stationnement", rules.stat_logement, "", "stat"),
    ):
        txt, etat = _fmt_valeur(val, unite)
        ref = src.get(skey)
        out.append({"cle": cle, "libelle": libelle, "valeur": txt, "etat": etat,
                    "reference": ref, "url": _url(ref), "exceptions": _exc(cle)})
    return out


def resolve_reglement(commune: str | None, zone_code: str | None,
                      idurba: str | None = None) -> dict | None:
    """Référence règlement d'UNE zone. None si code de zone vide."""
    if not zone_code:
        return None
    if not est_outillee(commune):
        # Commune non outillée : repli propre (pas de deep link fiable).
        return {
            "zone": zone_code,
            "calibree": False,
            "document": None,
            "url": _GPU_CONSULT,
            "idurba": idurba,
            "articles": [],
            "annuaire": {"insee": (idurba or "")[:5] or None, "zone": zone_code},   # M51 — O13 deep-link
            "note": "Règlement PLU non outillé pour cette commune — consultez le "
                    "Géoportail de l'Urbanisme (recherche par commune)."
                    + (f" Réf. document : {idurba}." if idurba else ""),
        }

    src = reglement_source(commune) or {}
    base_url = src.get("url")
    offset = int(src.get("offset") or 0)      # regles portent page_pdf (page PDF réelle) → 0
    rules = resolve_zone(zone_code, commune)

    articles = []
    if rules and rules.calibree and rules.sources:
        from .api.export_commun import purger_marqueurs_internes
        for regle, reference in rules.sources.items():
            pi = _page_imprimee(reference)
            url_page = (f"{base_url}#page={pi + offset}" if base_url and pi else base_url)
            # EXPORTS-1 lot 6 : les marqueurs de curation interne des YAML (« (page corrigée) »,
            # « (doctrine a) »…) ne sortent pas dans un document client.
            articles.append({"regle": regle, "reference": purger_marqueurs_internes(reference),
                             "page_imprimee": pi, "url": url_page})
        articles.sort(key=lambda a: (a["page_imprimee"] is None, a["page_imprimee"] or 0))

    # Lien « primaire » = première page citée (sinon document nu).
    deep = articles[0]["url"] if articles else base_url
    calibree = bool(rules and rules.calibree and articles)
    # RETOURS-11F3 F4 — le TABLEAU des règles de la zone AVEC leurs VALEURS (hauteur, emprise, reculs,
    # pleine terre, stationnement), pas seulement des références d'articles. Servi quand la zone est
    # calibrée (valeurs lues du YAML PLU, jamais inventées).
    regles_valeurs = _regles_valeurs(rules, base_url, offset) if (rules and rules.calibree) else []
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
        "regles_valeurs": regles_valeurs,   # F4 — les valeurs chiffrées de la zone
        # M51 — lien contextuel vers l'annuaire PLU (O13) : le verbatim de la zone servie.
        "annuaire": {"insee": (idurba or "")[:5] or None, "zone": zone_code},
        # M57-P1 (Q3) : le repli est LÉGITIME (calibration par TYPE de zone ; A/N n'ont pas
        # d'articles indexés dans le corpus M51). Condition INCHANGÉE ; seul le libellé est
        # reformulé — il ne doit pas laisser croire à un manque de couverture de la commune.
        "note": None if calibree else
                "Le règlement des zones agricoles et naturelles n'est pas indexé article "
                "par article dans LABUSE. Consultez le document complet.",
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
            # COUCHES-1 lot 3 (item 12 / B4) — propager la PART de surface (aire intersection / aire
            # parcelle) à la fiche : elle sert l'affichage « à cheval » (plusieurs zones + leur surface
            # respective). `zones` est trié part DESC → le premier code vu porte sa part réelle.
            if z.get("part") is not None:
                ref["part"] = z.get("part")
            seen[code] = ref
    if not seen:
        return None
    return {
        "zones": list(seen.values()),
        "disclaimer": "Le règlement PLU fait foi ; les valeurs affichées sont une "
                      "aide à la lecture, non un certificat d'urbanisme.",
    }
