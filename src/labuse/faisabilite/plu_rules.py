"""Chargement des règles PLU Saint-Paul et résolution de la zone d'une parcelle.

Source : config/plu_saint_paul.yaml (extraction ÉTAPE A, sourcée article/page).
Aucune valeur n'est inventée ici : on relaie le YAML tel quel, en propageant les
marqueurs `null` (non réglementé) et `"a_verifier"` (ambigu).
"""
from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

import yaml

_CONFIG_DIR = Path(__file__).resolve().parents[3] / "config"
_YAML = _CONFIG_DIR / "plu_saint_paul.yaml"   # PLU « gold » de référence (défaut + back-compat)

# Valeur "à vérifier" telle qu'écrite dans le YAML.
A_VERIFIER = "a_verifier"
# Stationnement explicitement non réglementé (ex. U1pru exemptée par l'Art. 12).
EXEMPT = "exempt"


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
    calibree: bool = True                    # True = règles d'un YAML PLU communal ; False = estimation générique
    notes: list[str] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    def places_par_logement(self) -> float | str | None:
        """Ratio places/logement : nombre, None, A_VERIFIER, ou EXEMPT (non réglementé)."""
        s = self.stat_logement
        if not s:
            return None
        if s == A_VERIFIER:
            return A_VERIFIER
        if re.search(r"exempt|aucune place|sauf en zone", s, re.I):
            return EXEMPT
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*places?\s*/?\s*(?:par\s*)?logement", s, re.I)
        return float(m.group(1).replace(",", ".")) if m else None


def _commune_slug(commune: str) -> str:
    """« Saint-Denis » → « saint_denis » (même convention que l'import gold standard)."""
    s = unicodedata.normalize("NFKD", commune).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^A-Za-z0-9]+", "_", s).strip("_").lower()


def _calibrated_yaml(commune: str | None) -> Path | None:
    """YAML PLU CALIBRÉ de la commune, ou None si non outillée (→ estimation générique).
    `commune=None` ⇒ Saint-Paul (back-compat tests + fiche pilote). Brancher une commune
    calibrée = déposer `config/plu_<slug>.yaml` — AUCUNE modification de code requise."""
    if commune is None:
        return _YAML
    p = _CONFIG_DIR / f"plu_{_commune_slug(commune)}.yaml"
    return p if p.is_file() else None


@lru_cache(maxsize=None)
def _doc_for(path_str: str) -> dict:
    return yaml.safe_load(Path(path_str).read_text(encoding="utf-8"))


def _doc(commune: str | None = None) -> dict:
    """Doc PLU (défaut = Saint-Paul). Hypotheses.charger() s'appuie dessus, inchangé."""
    return _doc_for(str(_calibrated_yaml(commune) or _YAML))


def load_rules(commune: str | None = None) -> dict[str, ZoneRules]:
    """(Sous-)zones détaillées du YAML PLU de la commune → ZoneRules (défaut = Saint-Paul)."""
    path = _calibrated_yaml(commune)
    doc = _doc_for(str(path)) if path is not None else {}
    return {code: _to_rules(code, v) for code, v in doc.get("zones", {}).items()}


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


def resolve_zone(code: str, commune: str | None = None) -> ZoneRules | None:
    """Résout le code de zone en ZoneRules applicables.

    Priorité : (1) YAML PLU CALIBRÉ de la commune ; (2) fallback GÉNÉRIQUE estimé.

    Deux modes (clé `mode:` du YAML, défaut « progressif ») :
      - `strict`  (Saint-Paul, « gold ou rien ») : un code hors YAML, ou une zone
        sans hauteur exploitable, renvoie tel quel (→ None / non constructible).
        JAMAIS d'estimation : la commune de référence ne doit voir que du calibré.
      - `progressif` (défaut, communes en cours de calibration) : un code hors YAML,
        ou une zone calibrée mais sans hauteur exploitable (he_m ET hf_m non chiffrés),
        retombe sur l'ESTIMATION générique (calibree=False) — la couverture ne RECULE
        jamais quand on ajoute un YAML partiel ; on gagne la précision zone par zone.
    `commune=None` ⇒ Saint-Paul (back-compat). None aussi si code vide.
    """
    if not code:
        return None
    code = code.strip()
    yaml_path = _calibrated_yaml(commune)
    if yaml_path is not None:                       # commune OUTILLÉE (YAML PLU présent)
        doc = _doc_for(str(yaml_path))
        strict = (doc.get("mode") == "strict")      # défaut absent = progressif
        rules = {c: _to_rules(c, v) for c, v in doc.get("zones", {}).items()}

        # 1) correspondance directe (U…, Usdu, AU5e…)
        if code in rules:
            r = rules[code]
            # PROGRESSIF : zone calibrée mais SANS hauteur exploitable (prospect/AVAP →
            # he_m et hf_m non chiffrés) → estimation générique plutôt que non constructible.
            if strict or _has_usable_height(r):
                return r
            return _zone_generique(code)

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

        # 4) code hors YAML : strict → None (gold ou rien) ; progressif → estimation.
        return None if strict else _zone_generique(code)

    return _zone_generique(code)                    # commune SANS YAML → capacité ESTIMÉE générique


def _has_usable_height(r: ZoneRules) -> bool:
    """Le moteur ne calcule des niveaux que si he_m OU hf_m est chiffré (sinon
    estimate_capacity renvoie « non constructible »). « a_verifier »/None → non exploitable."""
    return isinstance(r.he_m, (int, float)) or isinstance(r.hf_m, (int, float))


def _positive_prefixes() -> tuple[str, ...]:
    """Préfixes constructibles — SOURCE UNIQUE : cascade_rules.yaml › zonage_plu_gpu (alignement
    avec la cascade qui classe déjà U/AU vs A/N sur les 24 communes)."""
    from .. import config
    for lc in config.cascade_rules().get("layers", []):
        if lc.get("name") == "zonage_plu_gpu":
            return tuple(lc.get("params", {}).get("positive_prefixes", ["U", "AU"]))
    return ("U", "AU")


def _zone_generique(code: str) -> ZoneRules:
    """Règles ESTIMÉES pour une zone hors PLU outillé (calibree=False) : préfixe U/AU →
    constructible, emprise bornée par les reculs (défauts Hypotheses) + hé générique prudent ;
    N/A → non constructible. À calibrer en ajoutant un config/plu_<commune>.yaml."""
    noyau = re.sub(r"^\d+", "", code).strip().upper()          # « 1AUc » → « AUC »
    constructible = any(noyau.startswith(p.upper()) for p in _positive_prefixes())
    note = ("Capacité ESTIMÉE — PLU de la commune non outillé (aucun config/plu_<commune>.yaml). "
            "Valeurs génériques prudentes ; calibrage = ajout du YAML PLU communal.")
    if not constructible:
        return ZoneRules(code=code, calibree=False, constructible_neuf=False,
                         notes=[note], sources={"zone": "estimation générique"})
    he = float((_doc().get("hypotheses_faisabilite") or {}).get("he_defaut_generique_m", 9.0))
    return ZoneRules(code=code, calibree=False, he_m=he, notes=[note],
                     sources={"hauteur": "estimation générique (PLU non outillé)",
                              "zone": "estimation générique"})
