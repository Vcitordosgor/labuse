"""LE ZONAGE — résolution de la zone d'une parcelle en règles chiffrées (nouveau système, unique).

Depuis PLU-CALIBRAGE-4, ce module est la SOURCE UNIQUE des règles de zone. Il remplace l'ancien
moteur de constructibilité (supprimé) et ne lit plus aucun `config/plu_<slug>.yaml` :

  · les VALEURS chiffrées viennent des `regles` servies par le module `plu.destinations`
    (PLU-CALIBRAGE-1/2/3, qui les ont extraites, sourcées article/page, puis préservées — 0-diff) ;
  · la MÉTADONNÉE de zonage (mode strict/progressif, zones AU*st, renvois AU→U, habitat, prospect,
    hypothèses moteur, notes de provenance) vient de `config/plu_zonage.yaml` (migrée en lot 4).

Le contrôle de flux reproduit à l'identique l'ancien `_resolve_zone_base` : correspondance directe,
zones AU*st non constructibles, renvoi AU→U, repli générique, modes strict/progressif. La
superposition des feuilles VALIDÉES (`_calibrage_overlay`) impose valeur + source ; un `propose`
ne branche jamais le calcul (l'étape reste ESTIMÉE). `resolve_zone` = base + overlay.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field, replace as _replace
from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG = Path(__file__).resolve().parents[3] / "config"
_ZONAGE = _CONFIG / "plu_zonage.yaml"

# ── marqueurs de valeur (mêmes sémantiques que l'ancien moteur de constructibilité) ─────────────
A_VERIFIER = "a_verifier"          # présent au règlement mais ambigu : à signaler, ne pas combler
EXEMPT = "exempt"                  # stationnement explicitement non réglementé
NON_MODELISABLE = "non_modelisable"  # norme présente mais pas exprimée en places/logement


@dataclass
class ZoneRules:
    """Règles chiffrées d'une (sous-)zone, avec leurs sources. Un champ peut valoir
    None (non réglementé) ou A_VERIFIER (ambigu : à signaler, ne pas combler)."""

    code: str
    bassin: str | None = None
    he_m: float | str | None = None          # hauteur égout/acrotère (niveaux habitables)
    hf_m: float | str | None = None          # hauteur faîtage
    emprise_sol_pct: float | str | None = None
    recul_voirie_m: float | str | None = None
    recul_limites_sep_m: float | str | None = None
    stat_logement: str | None = None         # ex. "1,5 place / logement"
    pleine_terre_pct: float | str | None = None
    # provenance / contexte
    via_renvoi: str | None = None            # ex. "AU1a → règles U1a"
    constructible_neuf: bool = True          # False pour les zones AU*st
    habitat: str | None = None               # "interdit" = vocation non résidentielle au règlement
    calibree: bool = True                    # True = règles d'une commune ; False = estimation générique
    hauteur_mode: str | None = None          # 'prospect' = hf_m calculé PAR PARCELLE (L≥H, largeur voirie)
    niveaux_max: int | None = None           # R+n LU au règlement (validé) → niveaux imposés
    hauteur_plage: dict | None = None         # hauteur variant par secteur (base) → plage
    emprise_plage: dict | None = None         # idem emprise au sol
    notes: list[str] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    def places_par_logement(self) -> float | str | None:
        """Ratio places/logement. Quatre issues DISTINCTES, jamais une valeur inventée :
          · nombre · None (absente) · A_VERIFIER (ambiguë) · EXEMPT · NON_MODELISABLE."""
        s = self.stat_logement
        if not s:
            return None
        if s == A_VERIFIER:
            return A_VERIFIER
        if re.search(r"exempt|aucune place|sauf en zone", s, re.I):
            return EXEMPT
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*places?\s*/?\s*(?:par\s*)?logement", s, re.I)
        if m:
            return float(m.group(1).replace(",", "."))
        return NON_MODELISABLE          # texte présent mais aucune forme « X place/logement » lisible


# ── métadonnée de zonage (config/plu_zonage.yaml, migrée hors des plu_<slug>.yaml) ──────────────
@lru_cache(maxsize=None)
def _zonage_doc() -> dict:
    return yaml.safe_load(_ZONAGE.read_text(encoding="utf-8")) if _ZONAGE.is_file() else {}


def _insee(commune: str | None) -> str | None:
    """Commune → INSEE. `commune=None` ⇒ Saint-Paul (back-compat, comme l'ancien _YAML)."""
    from ..plu.destinations import _fichier_commune, _slug
    if commune is None:
        return "97415"                    # Saint-Paul (gold, défaut historique)
    if re.fullmatch(r"974\d\d", str(commune).strip()):
        return commune.strip()
    p = _fichier_commune(commune)          # 974xx_slug.yaml
    if p is not None:
        return p.name[:5]
    slug = _slug(commune)
    for ins, e in _zonage_doc().items():   # repli : slug → insee via plu_zonage
        if e.get("slug") == slug:
            return ins
    return None


def _zonage_commune(commune: str | None) -> dict | None:
    ins = _insee(commune)
    return _zonage_doc().get(ins) if ins else None


# ── valeurs chiffrées reconstruites depuis les regles (TOUTES les feuilles, quel que soit le
#    statut : la conversion PLU-CALIBRAGE-3 a préservé les valeurs de l'ancien système) ──────────
def _val(reg: dict, rub: str, feuille: str, cle: str):
    """Valeur d'une feuille (valide OU propose) ; None → 'a_verifier' (l'ancien système écrivait
    'a_verifier' quand la valeur n'était pas exploitable — même effet non-numérique au moteur)."""
    leaf = (reg.get(rub) or {}).get(feuille) if rub in reg else None
    if not isinstance(leaf, dict) or leaf.get("absent") or leaf.get("plage"):
        return None
    v = leaf.get(cle)
    if v is None:
        return A_VERIFIER if leaf.get("statut") == "propose" else None
    return float(v) if isinstance(v, (int, float)) else v


def _stat_from_regles(reg: dict):
    leaf = (reg.get("stationnement") or {}).get("par_logement")
    if not isinstance(leaf, dict) or leaf.get("absent"):
        return None
    p = leaf.get("places")
    if isinstance(p, (int, float)):
        p = int(p) if float(p).is_integer() else p
        return f"{p} place / logement" if p == 1 else f"{p} places / logement"
    # exemption explicite (ex. Saint-Paul U1pru, Art. 12 « sauf en zone… ») : la RAISON de la
    # feuille la porte (« exempté : aucune place imposée ») — on la préserve pour que
    # places_par_logement() la reconnaisse EXEMPT (l'ancien YAML portait la même mention). On lit
    # la raison (curée par zone), pas la citation (qui cite la règle générale « sauf en zone U1pru »
    # pour BEAUCOUP de zones → aurait faussement exempté les autres).
    if re.search(r"exempt|aucune place", leaf.get("raison") or "", re.I):
        return "exempté : aucune place imposée"
    return A_VERIFIER if leaf.get("statut") == "propose" else None


def _zone_rules_from_regles(commune: str | None, code: str, zmeta: dict) -> ZoneRules:
    """ZoneRules d'une zone CALIBRÉE : valeurs des regles + métadonnée de zone (plu_zonage)."""
    from ..plu import destinations as D
    reg = D.regles_zone(_insee(commune) or "", code)
    zm = (zmeta.get("zones") or {}).get(code, {})
    return ZoneRules(
        code=code, bassin=zm.get("bassin"),
        he_m=_val(reg, "hauteur", "egout", "m"),
        hf_m=_val(reg, "hauteur", "faitage", "m"),
        emprise_sol_pct=_val(reg, "emprise_sol", "ces", "pct"),
        recul_voirie_m=_val(reg, "retraits", "voie", "min_m"),
        recul_limites_sep_m=_val(reg, "retraits", "limites_separatives", "min_m"),
        stat_logement=_stat_from_regles(reg),
        pleine_terre_pct=_val(reg, "pleine_terre", "pct", "pct"),
        hauteur_mode=zm.get("hauteur_mode"),
        habitat=zm.get("habitat"),
        constructible_neuf=zm.get("constructible_neuf", True),
        notes=list(zm.get("notes") or []),   # provenance/ouverture — lues par classify_au_statut
        calibree=True, sources={}, raw={"_regles": True, "notes": zm.get("notes") or []},
    )


def _resolve_zone_base(code: str, commune: str | None = None) -> ZoneRules | None:
    """Résout le code de zone en ZoneRules (depuis regles + plu_zonage), AVANT l'overlay validé.

    Deux modes (`mode:` de plu_zonage, défaut « progressif ») :
      - `strict` (Saint-Paul, « gold ou rien ») : code hors calibrage → None ;
      - `progressif` (défaut) : code hors calibrage, ou zone sans hauteur exploitable, → estimation
        générique (`calibree=False`). `commune=None` ⇒ Saint-Paul (back-compat) ; None si code vide.
    """
    from .zone_norm import normalize_key
    from ..plu import destinations as D
    if not code:
        return None
    code = code.strip()
    zc = _zonage_commune(commune)
    ins = _insee(commune)
    # « commune outillée » = elle a une métadonnée de zonage OU des regles (les communes extraites
    # par l'agent interne n'ont pas d'entrée plu_zonage mais ont des regles).
    reg_zones = {r["zone"] for r in D.regles_commune(ins)} if ins else set()
    outillee = (zc is not None) or bool(reg_zones)
    if outillee:
        zc = zc or {}
        strict = (zc.get("mode") == "strict")
        zones = set(reg_zones) | set((zc.get("zones") or {}).keys())
        norm = {normalize_key(c): c for c in zones}

        # 1) correspondance directe (normalisée)
        hit = norm.get(normalize_key(code))
        if hit is not None:
            r = _zone_rules_from_regles(commune, hit, zc)
            r.code = code
            if strict or _has_usable_height(r):
                return r
            return _zone_generique(code)

        # 2) zones AU*st — pas de construction neuve
        st = zc.get("zones_au_st") or {}
        st_norm = {normalize_key(x) for x in (st.get("liste") or [])}
        if normalize_key(code) in st_norm or re.fullmatch(r"AU\w*st", code, re.I):
            _hmax = st.get("hauteur_max_m")
            return ZoneRules(
                code=code, constructible_neuf=False,
                hf_m=float(_hmax) if _hmax is not None else None,
                notes=[st.get("portee", "Travaux mineurs uniquement")],
                sources=({"hauteur": st["source"]} if (_hmax is not None and st.get("source")) else {}))

        # 3) renvoi AU<n><indice> → U<n><indice>
        m = re.fullmatch(r"AU(\d[a-zA-Z0-9]*)", code, re.I)
        if m:
            u_code = "U" + m.group(1)
            hit_u = norm.get(normalize_key(u_code))
            if hit_u is not None:
                r = _zone_rules_from_regles(commune, hit_u, zc)
                r.code = code
                r.via_renvoi = (f"{code} → règles de {hit_u} (renvoi du règlement, "
                                f"{(zc.get('zones_au_renvoi') or {}).get('AU' + m.group(1)[0], 'caractère de zone')})")
                return r

        # 4) code hors zonage : strict → None ; progressif → estimation
        return None if strict else _zone_generique(code)

    return _zone_generique(code)                    # commune SANS calibrage → capacité ESTIMÉE générique


def resolve_zone(code: str, commune: str | None = None) -> ZoneRules | None:
    """Résout le code de zone, PUIS superpose les règles chiffrées validées (PLU-CALIBRAGE-2)."""
    return _appliquer_calibrage(_resolve_zone_base(code, commune), code, commune)


# rétro-compat : le harnais d'équivalence et d'anciens scripts nomment resolve_zone_v2.
resolve_zone_v2 = resolve_zone


def load_rules(commune: str | None = None) -> dict[str, ZoneRules]:
    """(Sous-)zones d'une commune → ZoneRules (regles + overlay validé), sans repli générique
    (chaque zone garde ses valeurs calibrées, ex. l'emprise, même sans hauteur exploitable)."""
    from ..plu import destinations as D
    zc = _zonage_commune(commune) or {}
    ins = _insee(commune)
    codes = set((zc.get("zones") or {}).keys())
    if ins:
        codes |= {r["zone"] for r in D.regles_commune(ins)}
    out: dict[str, ZoneRules] = {}
    for code in codes:
        out[code] = _appliquer_calibrage(_zone_rules_from_regles(commune, code, zc), code, commune)
    return out


def est_outillee(commune: str | None) -> bool:
    """La commune a-t-elle un calibrage (métadonnée de zonage OU regles) ? Remplace l'ancien
    `_calibrated_yaml(commune) is not None`."""
    from ..plu import destinations as D
    if _zonage_commune(commune) is not None:
        return True
    ins = _insee(commune)
    return bool(ins and D.regles_commune(ins))


def reglement_source(commune: str | None) -> dict | None:
    """Métadonnée du document règlement de la commune (URL, document, édition, millésime), lue de
    module `plu.destinations` (meta). Remplace l'ancien `_doc(commune)['source']`. `offset` = 0 : regles
    portent `page_pdf` (page PDF réelle), plus de conversion page imprimée → page PDF."""
    from ..plu import destinations as D
    meta = D.reglement_meta(commune) if commune else D.reglement_meta(_insee(commune) or "")
    if meta is None:
        return None
    return {"url": meta.get("url"), "document": meta.get("document"),
            "edition": meta.get("edition"), "approbation": meta.get("edition"),
            "millesime": meta.get("millesime"), "offset": 0}


# ── superposition des feuilles VALIDÉES (branchement PLU-CALIBRAGE-2, lu de destinations) ────────
_ABSENT_SENTINELLE = "pas de règle dans le PLU"


def _art(leaf: dict) -> str:
    """« Article Ud.7 » ou « Ud 10 » → « Art. Ud.7 » (jamais « Art. Article … »)."""
    a = str(leaf.get("article") or "").strip()
    a = re.sub(r"^\s*articles?\s+", "", a, flags=re.I)
    return f"Art. {a}"


def _src_validee(leaf: dict) -> str:
    return f"{_art(leaf)} · p.{leaf.get('page_pdf')} (PLU, calibrage validé)"


def _src_absente(leaf: dict) -> str:
    return f"{_ABSENT_SENTINELLE} (silence prouvé — {_art(leaf)} · p.{leaf.get('page_pdf')})"


@lru_cache(maxsize=4096)
def _calibrage_overlay(code: str, commune: str | None):
    """Overrides (valeurs + sources) tirés des règles chiffrées VALIDÉES de la (commune, zone),
    ou None si rien à appliquer. Ne considère QUE les feuilles `valide` / `absent` — jamais
    `propose`. Mis en cache (les regles ne changent pas en cours de process)."""
    from ..plu import destinations as _D
    ins = _insee(commune)
    if not ins:
        return None
    reg = _D.regles_zone(ins, code)
    if not reg:
        return None
    champs: dict = {}
    src: dict[str, str] = {}

    def _feuille(*chemin):
        """La feuille (valeur OU silence prouvé) SEULEMENT si son statut est `valide` ; sinon
        None (un `propose` ne branche jamais le calcul)."""
        n = reg
        for k in chemin:
            n = n.get(k) if isinstance(n, dict) else None
            if n is None:
                return None
        return n if (isinstance(n, dict) and n.get("statut") == "valide") else None

    # hauteur : faîtage (hf), égout (he), niveaux (R+n imposé)
    fait = _feuille("hauteur", "faitage")
    ego = _feuille("hauteur", "egout")
    niv = _feuille("hauteur", "niveaux")
    if fait and fait.get("plage"):
        champs["hauteur_plage"] = {**fait, "source": _src_validee(fait)}
        src["hauteur"] = _src_validee(fait)
    elif fait and not fait.get("absent") and isinstance(fait.get("m"), (int, float)):
        champs["hf_m"] = float(fait["m"]); src["hauteur"] = _src_validee(fait)
        champs["hauteur_mode"] = None      # une hauteur ABSOLUE validée prime sur le mode prospect
    if ego and not ego.get("absent") and isinstance(ego.get("m"), (int, float)):
        champs["he_m"] = float(ego["m"]); src.setdefault("hauteur", _src_validee(ego))
    if niv and not niv.get("absent") and isinstance(niv.get("r_plus"), int):
        champs["niveaux_max"] = int(niv["r_plus"]); src.setdefault("hauteur", _src_validee(niv))
    for leaf in (fait, ego, niv):
        if leaf and leaf.get("absent"):
            src.setdefault("hauteur", _src_absente(leaf))

    # emprise au sol (CES)
    ces = _feuille("emprise_sol", "ces")
    if ces and ces.get("plage"):
        champs["emprise_plage"] = {**ces, "source": _src_validee(ces)}
        src["emprise"] = _src_validee(ces)
    elif ces and not ces.get("absent") and isinstance(ces.get("pct"), (int, float)):
        champs["emprise_sol_pct"] = float(ces["pct"]); src["emprise"] = _src_validee(ces)
    elif ces and ces.get("absent"):
        src["emprise"] = _src_absente(ces)         # l'étape « % réglementé » le dira

    # retraits : voie, limites séparatives (min_m — la formule est évaluée telle quelle par le moteur)
    voie = _feuille("retraits", "voie")
    lim = _feuille("retraits", "limites_separatives")
    if voie and not voie.get("absent") and isinstance(voie.get("min_m"), (int, float)):
        champs["recul_voirie_m"] = float(voie["min_m"]); src["recul_voirie"] = _src_validee(voie)
    elif voie and voie.get("absent"):
        src["recul_voirie"] = _src_absente(voie)
    if lim and not lim.get("absent") and isinstance(lim.get("min_m"), (int, float)):
        champs["recul_limites_sep_m"] = float(lim["min_m"]); src["recul_limites"] = _src_validee(lim)
    elif lim and lim.get("absent"):
        src["recul_limites"] = _src_absente(lim)

    # stationnement (par logement)
    st = _feuille("stationnement", "par_logement")
    if st and not st.get("absent") and isinstance(st.get("places"), (int, float)):
        p = st["places"]; p = int(p) if float(p).is_integer() else p
        champs["stat_logement"] = f"{p} place / logement" if p == 1 else f"{p} places / logement"
        src["stationnement"] = _src_validee(st)
    elif st and st.get("absent"):
        src["stationnement"] = _src_absente(st)

    if not champs and not src:
        return None
    return champs, src


def _appliquer_calibrage(rules: ZoneRules | None, code: str, commune: str | None) -> ZoneRules | None:
    """Superpose les règles chiffrées validées à un ZoneRules (identité si rien à appliquer)."""
    if rules is None:
        return None
    ov = _calibrage_overlay(code, commune)
    if ov is None:
        return rules
    champs, src = ov
    return _replace(rules, sources={**(rules.sources or {}), **src}, **champs)


# ── repli générique + hypothèses moteur ─────────────────────────────────────────────────────────
def _has_usable_height(r: ZoneRules) -> bool:
    """Le moteur ne calcule des niveaux que si he_m OU hf_m est chiffré (sinon « non constructible »).
    EXCEPTION : zone 'prospect' → hf_m calculé PAR PARCELLE, donc considérée exploitable."""
    return r.hauteur_mode == 'prospect' or isinstance(r.he_m, (int, float)) or isinstance(r.hf_m, (int, float))


def _positive_prefixes() -> tuple[str, ...]:
    """Préfixes constructibles — SOURCE UNIQUE : cascade_rules.yaml › zonage_plu_gpu."""
    from .. import config
    for lc in config.cascade_rules().get("layers", []):
        if lc.get("name") == "zonage_plu_gpu":
            return tuple(lc.get("params", {}).get("positive_prefixes", ["U", "AU"]))
    return ("U", "AU")


def _zone_generique(code: str) -> ZoneRules:
    """Règles ESTIMÉES pour une zone hors calibrage (calibree=False) : préfixe U/AU →
    constructible (hé générique prudent) ; N/A → non constructible."""
    from .zone_norm import est_famille
    constructible = est_famille(code, _positive_prefixes())
    note = ("Capacité ESTIMÉE — PLU de la commune non calibré. Valeurs génériques prudentes ; "
            "calibrage = extraction des regles de la commune.")
    if not constructible:
        return ZoneRules(code=code, calibree=False, constructible_neuf=False,
                         notes=[note], sources={"zone": "estimation générique"})
    from .engine import HE_DEFAUT_GENERIQUE_M
    he = float(HE_DEFAUT_GENERIQUE_M)
    # le libellé de SOURCE reste mot pour mot celui de l'ancien système (comparé par le
    # traducteur) — seule la note, non comparée, dit la nouvelle voie de calibrage.
    return ZoneRules(code=code, calibree=False, he_m=he, notes=[note],
                     sources={"hauteur": "estimation générique (PLU non outillé)",
                              "zone": "estimation générique"})


def hypotheses_faisabilite(commune: str | None = None) -> dict:
    """Section `hypotheses_faisabilite` migrée dans plu_zonage.yaml (remplace l'ancien point de
    lecture des plu_<slug>.yaml). Commune non outillée → {} (l'appelant retombe sur les défauts)."""
    zc = _zonage_commune(commune)
    return (zc or {}).get("hypotheses_faisabilite") or {}


# rétro-compat de nom pour le harnais d'équivalence.
hypotheses_faisabilite_v2 = hypotheses_faisabilite


def _hypotheses_ile() -> dict:
    """Hypothèses ÎLE-GÉNÉRIQUES (source NEUTRE `config/hypotheses_ile.yaml`), base AVANT tout
    override commune. Valeurs identiques aux anciens défauts → golden = baseline."""
    from .. import config
    try:
        return (config.load_yaml_config("hypotheses_ile") or {}).get("hypotheses_ile") or {}
    except Exception:  # noqa: BLE001 — fichier absent = repli défauts dataclass, jamais un crash
        return {}
