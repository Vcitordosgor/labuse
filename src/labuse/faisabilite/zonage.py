"""PLU-CALIBRAGE-4 — LE ZONAGE, NOUVEAU SYSTÈME (règles chiffrées + métadonnée migrée).

Reconstruit un `ZoneRules` SANS lire les anciens `config/plu_<slug>.yaml` : les VALEURS viennent
des `regles` de `plu_destinations` (PLU-CALIBRAGE-3, qui les a préservées — équivalence 0-diff),
la MÉTADONNÉE de zonage vient de `config/plu_zonage.yaml` (PLU-CALIBRAGE-4, migrée des anciens
fichiers). Le contrôle de flux reproduit `plu_rules._resolve_zone_base` à l'identique :

  · repli générique (`_zone_generique`), modes strict/progressif, zones AU*st non constructibles,
    renvoi AU→U, drapeaux constructible_neuf / calibree / via_renvoi, mode prospect, habitat ;
  · la superposition des feuilles VALIDÉES (niveaux imposés, plage, source « calibrage validé »)
    reste `plu_rules._appliquer_calibrage` — le MÊME code déjà éprouvé.

Tant que `resolve_zone_v2` n'est pas branché (lot 3), il coexiste avec l'ancien pour PROUVER
l'équivalence (lot 2). `pleine_terre` est désormais LUE (rubrique du schéma).
"""
from __future__ import annotations

import re
from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG = Path(__file__).resolve().parents[3] / "config"
_ZONAGE = _CONFIG / "plu_zonage.yaml"


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
_A_VERIF = "a_verifier"


def _val(reg: dict, rub: str, feuille: str, cle: str):
    """Valeur d'une feuille (valide OU propose) ; None → 'a_verifier' (l'ancien système écrivait
    'a_verifier' quand la valeur n'était pas exploitable — même effet non-numérique au moteur)."""
    leaf = (reg.get(rub) or {}).get(feuille) if rub in reg else None
    if not isinstance(leaf, dict) or leaf.get("absent") or leaf.get("plage"):
        return None
    v = leaf.get(cle)
    if v is None:
        return _A_VERIF if leaf.get("statut") == "propose" else None
    return float(v) if isinstance(v, (int, float)) else v


def _stat_from_regles(reg: dict):
    leaf = (reg.get("stationnement") or {}).get("par_logement")
    if not isinstance(leaf, dict) or leaf.get("absent"):
        return None
    p = leaf.get("places")
    if isinstance(p, (int, float)):
        p = int(p) if float(p).is_integer() else p
        return f"{p} place / logement" if p == 1 else f"{p} places / logement"
    return _A_VERIF if leaf.get("statut") == "propose" else None


def _zone_rules_from_regles(commune: str, code: str, zmeta: dict):
    """ZoneRules d'une zone CALIBRÉE : valeurs des regles + métadonnée de zone (plu_zonage)."""
    from .plu_rules import ZoneRules
    from ..plu import destinations as D
    reg = D.regles_zone(commune, code)
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


def _has_usable_height(r) -> bool:
    from .plu_rules import _has_usable_height as _h
    return _h(r)


def _resolve_v2_base(code: str, commune: str | None):
    """Reproduit `plu_rules._resolve_zone_base`, mais depuis regles + plu_zonage."""
    from .plu_rules import _zone_generique, ZoneRules
    from .zone_norm import normalize_key
    from ..plu import destinations as D
    if not code:
        return None
    code = code.strip()
    zc = _zonage_commune(commune)
    ins = _insee(commune)
    # « commune outillée » = elle a une métadonnée de zonage OU des regles (les 3 extraites
    # n'ont pas d'entrée plu_zonage mais ont des regles).
    reg_zones = set()
    if ins:
        reg_zones = {r["zone"] for r in D.regles_commune(ins)}
    outillee = (zc is not None) or bool(reg_zones)
    if outillee:
        zc = zc or {}
        strict = (zc.get("mode") == "strict")
        # zones connues = clés des regles ∪ métadonnée de zone
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

    return _zone_generique(code)


def resolve_zone_v2(code: str, commune: str | None = None):
    """Résout la zone (nouveau système) PUIS superpose les feuilles validées (MÊME overlay que
    l'ancien `plu_rules.resolve_zone`)."""
    from .plu_rules import _appliquer_calibrage
    return _appliquer_calibrage(_resolve_v2_base(code, commune), code, commune)


# ── hypothèses moteur, migrées dans plu_zonage.yaml (remplace plu_rules._hypotheses_faisabilite) ──
def hypotheses_faisabilite_v2(commune: str | None = None) -> dict:
    zc = _zonage_commune(commune)
    return (zc or {}).get("hypotheses_faisabilite") or {}
