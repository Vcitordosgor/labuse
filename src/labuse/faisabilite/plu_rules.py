"""Chargement des règles PLU Saint-Paul et résolution de la zone d'une parcelle.

Source : config/plu_saint_paul.yaml (extraction ÉTAPE A, sourcée article/page).
Aucune valeur n'est inventée ici : on relaie le YAML tel quel, en propageant les
marqueurs `null` (non réglementé) et `"a_verifier"` (ambigu).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

_YAML = Path(__file__).resolve().parents[3] / "config" / "plu_saint_paul.yaml"

# Valeur "à vérifier" telle qu'écrite dans le YAML.
A_VERIFIER = "a_verifier"


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
    notes: list[str] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    def places_par_logement(self) -> float | str | None:
        """Extrait le ratio places/logement du texte stationnement (best-effort)."""
        s = self.stat_logement
        if not s or s == A_VERIFIER:
            return A_VERIFIER if s == A_VERIFIER else None
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*places?\s*/?\s*(?:par\s*)?logement", s, re.I)
        return float(m.group(1).replace(",", ".")) if m else None


@lru_cache(maxsize=1)
def _doc() -> dict:
    return yaml.safe_load(_YAML.read_text(encoding="utf-8"))


def load_rules() -> dict[str, ZoneRules]:
    """Toutes les (sous-)zones détaillées du YAML → ZoneRules."""
    doc = _doc()
    out: dict[str, ZoneRules] = {}
    for code, v in doc.get("zones", {}).items():
        out[code] = _to_rules(code, v)
    return out


def _num(x):
    """Convertit en float si numérique, sinon relaie None / 'a_verifier' tel quel."""
    if isinstance(x, (int, float)):
        return float(x)
    return x  # None ou "a_verifier"


def _to_rules(code: str, v: dict) -> ZoneRules:
    srcs = {k.replace("_src", ""): val for k, val in v.items() if k.endswith("_src")}
    notes = [val for k, val in v.items() if k.endswith("_note") or k == "note"]
    return ZoneRules(
        code=code, bassin=v.get("bassin"),
        he_m=_num(v.get("he_m")), hf_m=_num(v.get("hf_m")),
        emprise_sol_pct=_num(v.get("emprise_sol_pct")),
        recul_voirie_m=_num(v.get("recul_voirie_m")),
        recul_limites_sep_m=_num(v.get("recul_limites_sep_m")),
        stat_logement=v.get("stat_logement"),
        pleine_terre_pct=_num(v.get("pleine_terre_pct")),
        notes=[n for n in notes if n], sources=srcs, raw=v,
    )


def resolve_zone(code: str) -> ZoneRules | None:
    """Résout le code de zone d'une parcelle en ZoneRules applicables.

    - zone détaillée dans le YAML : telle quelle ;
    - zone AU*st : non constructible en neuf (H max 4 m, travaux mineurs) ;
    - zone AU<n><indice> : RENVOI aux règles de U<n><indice> (cf. règlement) ;
    - sinon : None (zone inconnue / hors périmètre Saint-Paul).
    """
    if not code:
        return None
    code = code.strip()
    rules = load_rules()
    doc = _doc()

    # 1) correspondance directe (U…, Usdu, AU5e…)
    if code in rules:
        return rules[code]

    # 2) zones AU*st (secteurs de transition) — pas de construction neuve
    st = doc.get("zones_au_st", {})
    if code in st.get("liste", []) or re.fullmatch(r"AU\w*st", code):
        return ZoneRules(
            code=code, constructible_neuf=False, hf_m=float(st.get("hauteur_max_m", 4)),
            notes=[st.get("portee", "Travaux mineurs uniquement")],
            sources={"hauteur": st.get("source", "Art. 10 AU*st")},
        )

    # 3) renvoi AU<n><indice> → U<n><indice>
    m = re.fullmatch(r"AU(\d[a-zA-Z0-9]*)", code)
    if m:
        u_code = "U" + m.group(1)
        if u_code in rules:
            base = rules[u_code]
            r = _to_rules(u_code, base.raw)
            r.code = code
            r.via_renvoi = f"{code} → règles de {u_code} (renvoi du règlement, " \
                           f"{doc.get('zones_au_renvoi', {}).get('AU' + m.group(1)[0], 'caractère de zone')})"
            return r

    return None
