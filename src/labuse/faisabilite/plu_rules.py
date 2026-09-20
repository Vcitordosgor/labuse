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
# M94 — norme PRÉSENTE au règlement mais pas exprimée en places/logement (ex. « 1 place / 75 m² SDP »,
# ou par chambre, ou % SHON) : non modélisable dans le scénario au sol (≠ absente, ≠ à vérifier).
NON_MODELISABLE = "non_modelisable"


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
    habitat: str | None = None               # "interdit" = vocation non résidentielle au
                                             # règlement (zones éco — M6 2b, A-03) ; None = admis
    calibree: bool = True                    # True = règles d'un YAML PLU communal ; False = estimation générique
    hauteur_mode: str | None = None          # 'prospect' = hf_m calculé PAR PARCELLE (L≥H, largeur voirie)
    niveaux_max: int | None = None           # PLU-CALIBRAGE-2 : R+n LU au règlement (validé) → niveaux imposés
    notes: list[str] = field(default_factory=list)
    sources: dict[str, str] = field(default_factory=dict)
    raw: dict = field(default_factory=dict)

    def places_par_logement(self) -> float | str | None:
        """Ratio places/logement. M94 — quatre issues DISTINCTES, jamais une valeur inventée :
          · nombre           — norme chiffrable en places/logement (Sourcé, bornée) ;
          · None             — ABSENTE : aucune norme extraite pour cette zone (`stat_logement` vide) ;
          · A_VERIFIER       — présente mais ambiguë (tableau non extrait) : à signaler ;
          · EXEMPT           — explicitement non réglementé ;
          · NON_MODELISABLE  — PRÉSENTE mais pas exprimée par logement (par m² SDP / chambre / %SHON) :
                               le scénario au sol ne sait pas la traduire (dit, jamais comblé)."""
        s = self.stat_logement
        if not s:
            return None
        if s == A_VERIFIER:
            return A_VERIFIER
        if re.search(r"exempt|aucune place|sauf en zone", s, re.I):
            return EXEMPT
        # M94 — sur un barème de surface (« 1,5 place/logt (>30 m²) ; 1 place (<30) »), on retient le
        # nombre COLLÉ au premier « place/logement », qui est la tranche écrite en tête (le MAJORANT,
        # prudent : plus de stationnement = capacité au sol plus basse). Départage tracé, jamais muet.
        m = re.search(r"(\d+(?:[.,]\d+)?)\s*places?\s*/?\s*(?:par\s*)?logement", s, re.I)
        if m:
            return float(m.group(1).replace(",", "."))
        return NON_MODELISABLE          # texte présent mais aucune forme « X place/logement » lisible


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


def _hypotheses_faisabilite(commune: str | None = None) -> dict:
    """Section `hypotheses_faisabilite` du YAML PLU de la commune (M-N P1-13).

    Contrairement à `_doc()` — qui retombe TOUJOURS sur Saint-Paul quand la commune n'a pas de
    YAML —, ce point de lecture RESPECTE l'absence : commune non outillée → {} (l'appelant
    `Hypotheses.charger` retombe alors sur les défauts du dataclass, jamais sur Saint-Paul).
      - `commune=None` → Saint-Paul (back-compat pilote & tests) ;
      - commune outillée → sa section ; commune sans YAML → {}."""
    if commune is None:
        return _doc().get("hypotheses_faisabilite") or {}
    path = _calibrated_yaml(commune)
    if path is None:
        return {}
    return _doc_for(str(path)).get("hypotheses_faisabilite") or {}


def _hypotheses_ile() -> dict:
    """M-PLU-REF — les hypothèses ÎLE-GÉNÉRIQUES (source NEUTRE `config/hypotheses_ile.yaml`), base de
    résolution AVANT tout override commune. Valeurs identiques aux anciens défauts → golden = baseline ;
    elles ne s'appellent plus « Saint-Paul par défaut »."""
    from .. import config
    try:
        return (config.load_yaml_config("hypotheses_ile") or {}).get("hypotheses_ile") or {}
    except Exception:  # noqa: BLE001 — fichier absent = repli défauts dataclass, jamais un crash
        return {}


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
        hauteur_mode=v.get("hauteur_mode"),
        habitat=v.get("habitat"),
        # M131 : lit un gel EXPLICITE du YAML (défaut True). Permet une entrée `zones:` propre qui
        # porte une hauteur PAR ZONE (renvoi) tout en gardant `constructible_neuf=False` (zone AU*st
        # gelée : Us, 2AU). NE FABRIQUE aucune valeur numérique — honore une clé explicite. Piège
        # consigné en dette : sur une zone gelée, OMETTRE cette clé la rend constructible en silence.
        constructible_neuf=v.get("constructible_neuf", True),
        notes=[n for n in notes if n], sources=srcs, raw=v,
    )


# ── PLU-CALIBRAGE-2 lot 1 — branchement du calcul sur les règles CHIFFRÉES VALIDÉES ──────────
# Le calcul lit `resolve_zone`. On l'ENRICHIT ici, en UN point, des règles chiffrées calibrées et
# VALIDÉES lues par `destinations.regles_zone` (mandat PLU-CALIBRAGE-1) : une feuille `valide`
# impose sa valeur ET sa source (article + page → l'étape passe SOURCÉ) ; une feuille `absent`
# (silence prouvé) fait dire à l'étape « pas de règle dans le PLU » ; `propose` ou non calibrée =
# on ne touche à rien (l'étape reste ESTIMÉE, comme avant). Seules les communes dotées de règles
# validées (aujourd'hui : Saint-Denis) sont concernées — ailleurs, IDENTITÉ stricte.
from functools import lru_cache as _lru_cache

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


@_lru_cache(maxsize=4096)
def _calibrage_overlay(code: str, commune: str | None):
    """Overrides (valeurs + sources) tirés des règles chiffrées VALIDÉES de la (commune, zone),
    ou None si rien à appliquer. Ne considère QUE les feuilles `valide` / `absent` — jamais
    `propose`. Mis en cache (le YAML ne change pas en cours de process)."""
    if not commune:
        return None
    from ..plu import destinations as _D
    reg = _D.regles_zone(commune, code)
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
    if fait and not fait.get("absent") and isinstance(fait.get("m"), (int, float)):
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
    if ces and not ces.get("absent") and isinstance(ces.get("pct"), (int, float)):
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
        # format LISIBLE par ZoneRules.places_par_logement() (« N place[s] / logement »)
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
    from dataclasses import replace as _replace
    return _replace(rules, sources={**(rules.sources or {}), **src}, **champs)


def resolve_zone(code: str, commune: str | None = None) -> ZoneRules | None:
    """Résout le code de zone, PUIS superpose les règles chiffrées validées (PLU-CALIBRAGE-2)."""
    return _appliquer_calibrage(_resolve_zone_base(code, commune), code, commune)


def _resolve_zone_base(code: str, commune: str | None = None) -> ZoneRules | None:
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

        # 1) correspondance directe, NORMALISÉE (pt2.2 : casse/accents/séparateurs, phasage conservé —
        #    1AUb ≠ 2AUb). POINT DE CALCUL UNIQUE via zone_norm.normalize_key.
        from .zone_norm import normalize_key, est_famille
        norm_rules = {normalize_key(c): c for c in rules}
        hit = norm_rules.get(normalize_key(code))
        if hit is not None:
            r = rules[hit]
            # PROGRESSIF : zone calibrée mais SANS hauteur exploitable (prospect/AVAP →
            # he_m et hf_m non chiffrés) → estimation générique plutôt que non constructible.
            if strict or _has_usable_height(r):
                return r
            return _zone_generique(code)

        # 2) zones AU*st (secteurs de transition) — pas de construction neuve. Match normalisé.
        # M130-12 (rattrapage) : NE PAS FABRIQUER de hauteur. Le « H max 4 m » codé en dur était un
        # repli que le schéma déclare lui-même INEXACTE (cf. commentaires YAML Saint-Pierre) — 4 m est
        # la valeur-signature du mécanisme, pas une règle lue au règlement (aucune commune ne définit
        # `hauteur_max_m`). Absence de `hauteur_max_m` au YAML = absence de règle de hauteur → he/hf None
        # (remontés « non renseignée » à l'affichage), jamais un 4 m étranger. La CAPACITÉ (zéro
        # construction neuve) reste EXACTE : constructible_neuf=False + note de portée. Une hauteur n'est
        # servie QUE si la commune a LU et gravé `hauteur_max_m` au règlement (avec sa source).
        st = doc.get("zones_au_st", {})
        st_norm = {normalize_key(x) for x in st.get("liste", [])}
        if normalize_key(code) in st_norm or re.fullmatch(r"AU\w*st", code, re.I):
            _hmax = st.get("hauteur_max_m")
            return ZoneRules(
                code=code, constructible_neuf=False,
                hf_m=float(_hmax) if _hmax is not None else None,
                notes=[st.get("portee", "Travaux mineurs uniquement")],
                sources=({"hauteur": st["source"]} if (_hmax is not None and st.get("source")) else {}),
            )

        # 3) renvoi AU<n><indice> → U<n><indice> (insensible à la casse)
        m = re.fullmatch(r"AU(\d[a-zA-Z0-9]*)", code, re.I)
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
    estimate_capacity renvoie « non constructible »). « a_verifier »/None → non exploitable.
    EXCEPTION : zone 'prospect' → hf_m sera calculé PAR PARCELLE (faisabilite/db.py) ; on la
    considère exploitable, sinon le mode progressif la ferait tomber en estimation générique."""
    return r.hauteur_mode == 'prospect' or isinstance(r.he_m, (int, float)) or isinstance(r.hf_m, (int, float))


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
    from .zone_norm import est_famille                         # « 1AUc » → famille AU (phasage retiré)
    constructible = est_famille(code, _positive_prefixes())
    note = ("Capacité ESTIMÉE — PLU de la commune non outillé (aucun config/plu_<commune>.yaml). "
            "Valeurs génériques prudentes ; calibrage = ajout du YAML PLU communal.")
    if not constructible:
        return ZoneRules(code=code, calibree=False, constructible_neuf=False,
                         notes=[note], sources={"zone": "estimation générique"})
    # M-N P1-13 : hé générique = constante SOURCE UNIQUE (défaut du dataclass), plus d'emprunt au
    # YAML Saint-Paul pour estimer une zone d'une commune non outillée. Import différé (engine
    # dépend de plu_rules) pour éviter le cycle.
    from .engine import HE_DEFAUT_GENERIQUE_M
    he = float(HE_DEFAUT_GENERIQUE_M)
    return ZoneRules(code=code, calibree=False, he_m=he, notes=[note],
                     sources={"hauteur": "estimation générique (PLU non outillé)",
                              "zone": "estimation générique"})
