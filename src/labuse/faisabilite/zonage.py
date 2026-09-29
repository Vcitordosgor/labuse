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
    regle_non_validee: str | None = None      # PLU-CALIBRAGE-6 : liste des feuilles SDP `propose`
    #  (règle PLU non validée) qui BRANCHERAIENT la SDP → capacité non calculable, jamais un défaut
    recul_voirie_alignement: bool = False     # PLU-CALIBRAGE-7 forme 1 : recul 0 = « à l'alignement »
    recul_limites_alignement: bool = False    #  (idem « en limite séparative ») — 0 EXPLICITE, ≠ absent
    pleine_terre_compose: dict | None = None  # PLU-CALIBRAGE-7 forme 2 : {espaces_verts_pct, part_pct}
    #  pleine_terre_pct = espaces_verts_pct × part_pct / 100 (calculé, JAMAIS stocké — les 2 chiffres sourcés)
    # FICHE-FIX-2 P4 — clause de mixité sociale de la zone (LLS), lue des `regles` calibrées :
    #  {seuil_logements, quota_pct, portee, article, page_pdf, citation, statut}. None si la zone n'en
    #  porte pas. `statut` = 'valide' → branchée (11e étape sourcée) ; 'propose'/None → non modélisée.
    mixite: dict | None = None
    # PLU-EXCEPTIONS-1 — exceptions au règlement portées par les feuilles `regles` (verbatim + article +
    #  page + `porte`). Servies AVEC leur règle (id `<cle_regle>.exception`), jamais recomposées. Une
    #  liste par clé de règle ('hauteur','emprise','recul_voirie','recul_limites','pleine_terre',
    #  'stationnement','mixite') ; {} si la zone n'en porte aucune. AUCUNE n'entre dans un calcul.
    exceptions: dict[str, list[dict]] = field(default_factory=dict)
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
    """Valeur d'une feuille VALIDÉE seulement.

    PLU-CALIBRAGE-6 (garde) : la base est désormais VALIDÉES-ONLY, comme l'overlay
    (`_calibrage_overlay`). Avant, `_val` lisait la valeur numérique quel que soit le statut —
    c'est le trou de SCORING-5-RETOUR §2 : les 95 feuilles `propose` numériques branchaient la
    SDP (« un résiduel calculé sur du non-validé casse la règle "chaque chiffre est sourcé" »).
    Désormais un `propose` renvoie `a_verifier` (non numérique → n'entre PAS dans la SDP) ; la
    présence d'une telle feuille rend la zone non calculable (cf. `_regles_sdp_non_validees` /
    `_zone_regle_non_validee`), jamais une valeur par défaut."""
    leaf = (reg.get(rub) or {}).get(feuille) if rub in reg else None
    if not isinstance(leaf, dict) or leaf.get("absent") or leaf.get("plage"):
        return None
    if leaf.get("statut") != "valide":
        return A_VERIFIER if leaf.get("statut") == "propose" else None
    v = leaf.get(cle)
    if v is None:
        return None
    return float(v) if isinstance(v, (int, float)) else v


# ── garde PLU-CALIBRAGE-6 : les feuilles SDP-déterminantes NON validées rendent la capacité non
#    calculable (jamais une valeur par défaut). Le stationnement en est EXCLU : il ne détermine pas
#    la SDP (il borne le scénario « logements au sol », pas `surface_plancher_m2`). ────────────────
_FEUILLES_SDP_CAPACITE = (
    ("hauteur", "faitage", "m"), ("hauteur", "egout", "m"), ("hauteur", "niveaux", "r_plus"),
    ("emprise_sol", "ces", "pct"),
    ("retraits", "voie", "min_m"), ("retraits", "limites_separatives", "min_m"),
    ("pleine_terre", "pct", "pct"),
)


def _feuille_sdp_porte_valeur(rub: str, cle: str, leaf: dict) -> bool:
    """La feuille porterait-elle une valeur dans la SDP ? (numérique standard, ou PLU-CALIBRAGE-7 :
    recul « forme: alignement » = 0 explicite, ou pleine terre composée `espaces_verts_pct`)."""
    if isinstance(leaf.get(cle), (int, float)):
        return True
    if rub == "retraits" and leaf.get("forme") == "alignement":
        return True                                      # forme 1 : recul 0 explicite
    if rub == "pleine_terre" and isinstance(leaf.get("espaces_verts_pct"), (int, float)):
        return True                                      # forme 2 : composée
    return False


def _regles_sdp_non_validees(reg: dict) -> list[str]:
    """Feuilles SDP-déterminantes en statut `propose` PORTANT une valeur (elles brancheraient la
    SDP). Leur présence = capacité non calculable (« règle PLU non validée »). Vide = la zone se
    calcule sur ses seules feuilles validées."""
    out: list[str] = []
    for rub, feuille, cle in _FEUILLES_SDP_CAPACITE:
        sous = reg.get(rub)
        leaf = sous.get(feuille) if isinstance(sous, dict) else None
        if not isinstance(leaf, dict):
            continue
        if (leaf.get("statut") == "propose" and not leaf.get("absent") and not leaf.get("plage")
                and _feuille_sdp_porte_valeur(rub, cle, leaf)):
            out.append(f"{rub}.{feuille}")
    return out


# ── PLU-CALIBRAGE-7 — lecture des deux formes de règle ajoutées au schéma ─────────────────────────
def _recul_alignement(reg: dict, feuille: str) -> bool:
    """Forme 1 : la feuille recul (`retraits.<feuille>`) est-elle VALIDÉE en « forme: alignement »
    (recul 0 explicite — « à l'alignement » / « en limite séparative ») ? ≠ absent."""
    leaf = (reg.get("retraits") or {}).get(feuille)
    return (isinstance(leaf, dict) and leaf.get("statut") == "valide"
            and leaf.get("forme") == "alignement")


def _pleine_terre_val(reg: dict):
    """Valeur de pleine terre d'une feuille VALIDÉE — directe (`pct`) ou COMPOSÉE (forme 2 :
    `espaces_verts_pct` × `pleine_terre_part` / 100). `propose` → a_verifier (ne branche pas)."""
    leaf = (reg.get("pleine_terre") or {}).get("pct")
    if not isinstance(leaf, dict) or leaf.get("absent") or leaf.get("plage"):
        return None
    if leaf.get("statut") != "valide":
        return A_VERIFIER if leaf.get("statut") == "propose" else None
    if isinstance(leaf.get("pct"), (int, float)):
        return float(leaf["pct"])
    ev, part = leaf.get("espaces_verts_pct"), leaf.get("pleine_terre_part")
    if isinstance(ev, (int, float)) and isinstance(part, (int, float)):
        return round(float(ev) * float(part) / 100.0, 2)      # forme 2 : le moteur calcule
    return None


def _pleine_terre_compose(reg: dict) -> dict | None:
    """Forme 2 : les deux chiffres sourcés {espaces_verts_pct, part_pct} d'une feuille pleine terre
    composée VALIDÉE (pour l'affichage de l'étape). None si feuille directe / non validée."""
    leaf = (reg.get("pleine_terre") or {}).get("pct")
    if (isinstance(leaf, dict) and leaf.get("statut") == "valide"
            and isinstance(leaf.get("espaces_verts_pct"), (int, float))
            and isinstance(leaf.get("pleine_terre_part"), (int, float))):
        return {"espaces_verts_pct": float(leaf["espaces_verts_pct"]),
                "part_pct": float(leaf["pleine_terre_part"])}
    return None


def _zone_regle_non_validee(code: str, feuilles: list[str]) -> ZoneRules:
    """ZoneRules « non calculable — règle PLU non validée » : la zone est calibrée mais une (ou
    plusieurs) de ses feuilles SDP restent `propose`. On NE retombe PAS sur l'estimation générique
    (ce serait une valeur par défaut) : la capacité est déclarée non calculable, motif porté."""
    liste = ", ".join(sorted(set(feuilles)))
    return ZoneRules(
        code=code, calibree=True, regle_non_validee=liste,
        notes=[f"Capacité non calculable — règle(s) PLU non validée(s) : {liste} "
               "(feuille `propose`, sans citation retenue). Aucune valeur par défaut appliquée."],
        sources={"zone": "règle PLU non validée (feuille propose)"})


def _stat_from_regles(reg: dict):
    leaf = (reg.get("stationnement") or {}).get("par_logement")
    if not isinstance(leaf, dict) or leaf.get("absent"):
        return None
    p = leaf.get("places")
    # PLU-CALIBRAGE-6 : la VALEUR numérique ne branche que si la feuille est validée (validées-only,
    # comme l'overlay). L'exemption (non numérique, cf. ci-dessous) reste reconnue quel que soit le
    # statut : c'est un silence de règle, pas un chiffre injecté dans le calcul.
    if isinstance(p, (int, float)) and leaf.get("statut") == "valide":
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


def _mixite_leaf(reg: dict) -> dict | None:
    """FICHE-FIX-2 P4 — clause de mixité sociale (LLS) de la zone, lue TELLE QUELLE des regles
    calibrées (seuil de logements, quota %, article/page/citation, statut). None si absente."""
    m = reg.get("mixite") if isinstance(reg, dict) else None
    if not isinstance(m, dict):
        return None
    return {"seuil_logements": m.get("seuil_logements"), "quota_pct": m.get("quota_pct"),
            "portee": m.get("portee"), "article": m.get("article"), "page_pdf": m.get("page_pdf"),
            "citation": m.get("citation"), "statut": m.get("statut")}


# PLU-EXCEPTIONS-1 — clé de règle servie (reglement_block / regles_valeurs) pour un chemin de feuille.
_CLE_REGLE = {"hauteur": "hauteur", "emprise_sol": "emprise", "pleine_terre": "pleine_terre",
              "stationnement": "stationnement", "mixite": "mixite"}


def _cle_regle(chemin: tuple) -> str:
    rub = chemin[0]
    if rub == "retraits":
        return "recul_voirie" if (len(chemin) > 1 and chemin[1] == "voie") else "recul_limites"
    return _CLE_REGLE.get(rub, rub)


def _exceptions_from_regles(commune: str | None, code: str) -> dict[str, list[dict]]:
    """Exceptions au règlement portées par les feuilles `regles` de la zone → {cle_regle: [exc…]}.
    Relaie le bloc `exception` TEL QUEL (texte verbatim, article, page, porte) ; dédoublonne par
    (cle, texte) : une même clause portée par faîtage ET égout n'apparaît qu'une fois. Ne fabrique
    rien, n'entre dans aucun calcul (PLU-EXCEPTIONS-1 Lot C)."""
    from ..plu import destinations as D
    reg = D.regles_zone(_insee(commune) or "", code)
    if not isinstance(reg, dict):
        return {}
    out: dict[str, list[dict]] = {}
    vus: set[tuple] = set()
    for chemin, feuille in D.iter_regles_feuilles(reg):
        if not isinstance(feuille, dict):
            continue
        excs = feuille.get("exceptions") or ([feuille["exception"]] if feuille.get("exception") else [])
        cle = _cle_regle(chemin)
        for exc in excs:
            if not isinstance(exc, dict) or not (exc.get("texte") or "").strip():
                continue
            clef = (cle, (exc.get("texte") or "").strip())
            if clef in vus:            # même clause portée par faîtage ET égout → une fois
                continue
            vus.add(clef)
            out.setdefault(cle, []).append({
                "texte": exc.get("texte"), "article": exc.get("article"),
                "page_pdf": exc.get("page_pdf"), "porte": exc.get("porte"),
                "modifie_calcul": bool(exc.get("modifie_calcul"))})
    return out


def _zone_rules_from_regles(commune: str | None, code: str, zmeta: dict) -> ZoneRules:
    """ZoneRules d'une zone CALIBRÉE : valeurs des regles + métadonnée de zone (plu_zonage)."""
    from ..plu import destinations as D
    reg = D.regles_zone(_insee(commune) or "", code)
    zm = (zmeta.get("zones") or {}).get(code, {})
    return ZoneRules(
        code=code, bassin=zm.get("bassin"), mixite=_mixite_leaf(reg),
        exceptions=_exceptions_from_regles(commune, code),
        he_m=_val(reg, "hauteur", "egout", "m"),
        hf_m=_val(reg, "hauteur", "faitage", "m"),
        emprise_sol_pct=_val(reg, "emprise_sol", "ces", "pct"),
        recul_voirie_m=_val(reg, "retraits", "voie", "min_m"),
        recul_limites_sep_m=_val(reg, "retraits", "limites_separatives", "min_m"),
        recul_voirie_alignement=_recul_alignement(reg, "voie"),
        recul_limites_alignement=_recul_alignement(reg, "limites_separatives"),
        stat_logement=_stat_from_regles(reg),
        pleine_terre_pct=_pleine_terre_val(reg),
        pleine_terre_compose=_pleine_terre_compose(reg),
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
            nv = _regles_sdp_non_validees(D.regles_zone(ins, hit)) if ins else []
            if nv:
                return _zone_regle_non_validee(code, nv)   # règle PLU non validée → non calculable
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
                nv = _regles_sdp_non_validees(D.regles_zone(ins, hit_u)) if ins else []
                if nv:
                    return _zone_regle_non_validee(code, nv)   # renvoi vers zone U à règle non validée
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


# ── DONNEES-FIX-1 point 4 — les exceptions PLU `modifie_calcul=true` entrent au moteur ────────────
# Constat : 81 exceptions (bandes depuis limite, sous-secteurs, majorations conditionnelles) étaient
# AFFICHÉES sous le « i » mais jamais déduites. Elles entrent maintenant par le MÊME système unique
# que le reste des règles (ce module). Calibrage figé, sourcé article/page, dans
# `config/plu_exceptions_effet.json` (index = ligne de PLU-EXCEPTIONS-1/A_CALIBRER.csv). Quatre
# décisions, une seule source :
#   · applique       — la valeur de l'exception entre dans ZoneRules SI sa condition est vérifiée
#                      (ex. majoration de hauteur si terrain ≥ seuil), jamais approximée ;
#   · deja_couvert   — le sous-secteur cité se résout DÉJÀ comme sa propre zone calibrée (resolve_zone
#                      lui sert la bonne valeur) → aucune action sur la zone parente ;
#   · hors_sdp       — n'affecte pas l'enveloppe SDP (stationnement) → aucune action ;
#   · non_modelisee  — on NE l'approxime PAS : la règle reste affichée et la parcelle la PORTE
#                      (« règle non modélisée », avec article/page), jamais une valeur inventée.
_EXC_EFFET = _CONFIG / "plu_exceptions_effet.json"


@lru_cache(maxsize=1)
def _exceptions_effet() -> dict[tuple[str, str], list[dict]]:
    """Calibrage des 81 exceptions `modifie_calcul=true`, indexé par (insee, zone). SOURCE UNIQUE."""
    import json
    try:
        raw = json.loads(_EXC_EFFET.read_text(encoding="utf-8"))
    except (FileNotFoundError, ValueError):
        return {}
    out: dict[tuple[str, str], list[dict]] = {}
    for e in (raw.get("entries") or {}).values():
        out.setdefault((e["insee"], e["zone"]), []).append(e)
    return out


def appliquer_exceptions_calcul(rules: "ZoneRules | None", commune: str | None,
                                zone_lib: str | None, surface_m2: float | None
                                ) -> tuple["ZoneRules | None", list[dict]]:
    """Applique au moteur les exceptions PLU `modifie_calcul=true` de (commune, zone_lib) et renvoie
    (rules ajustées, règles non modélisées). Copie la ZoneRules (dataclasses.replace) — la règle de
    zone partagée n'est JAMAIS mutée. Une majoration ne fait que RELÂCHER (valeur plus haute) : elle
    n'abaisse jamais une contrainte de zone (garde de sens)."""
    if rules is None or not zone_lib:
        return rules, []
    ins = _insee(commune)
    if not ins:
        return rules, []
    non_modelisees: list[dict] = []
    for e in _exceptions_effet().get((ins, zone_lib), []):
        dec = e.get("decision")
        if dec == "non_modelisee":
            # PLU-CALIBRAGE-5 — on PORTE aussi le verbatim (`texte`, source A_CALIBRER.csv) : la fiche
            # affiche sous la capacité « une exception du règlement n'est pas modélisée » AVEC son texte.
            non_modelisees.append({"regle": e.get("regle"), "porte": e.get("porte"),
                                   "article": e.get("article"), "page_pdf": e.get("page_pdf"),
                                   "texte": e.get("texte")})
        elif dec == "applique":
            eff = e.get("effet") or {}
            if eff.get("type") == "majoration_surface":
                seuil, champ, val = eff.get("seuil_m2"), eff.get("champ"), eff.get("valeur")
                if (surface_m2 is not None and seuil is not None and champ and val is not None
                        and float(surface_m2) >= float(seuil)):
                    cur = getattr(rules, champ, None)
                    if not isinstance(cur, (int, float)) or float(val) > float(cur):
                        rules = _replace(rules, **{champ: float(val)})
        # deja_couvert / hors_sdp : aucune action (documenté au calibrage)
    return rules, non_modelisees


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

    # retraits : voie, limites séparatives (min_m — la formule est évaluée telle quelle par le moteur ;
    # PLU-CALIBRAGE-7 forme 1 : « forme: alignement » = recul 0 EXPLICITE, ≠ absent)
    voie = _feuille("retraits", "voie")
    lim = _feuille("retraits", "limites_separatives")
    if voie and voie.get("forme") == "alignement":
        champs["recul_voirie_m"] = 0.0; champs["recul_voirie_alignement"] = True
        src["recul_voirie"] = _src_validee(voie)
    elif voie and not voie.get("absent") and isinstance(voie.get("min_m"), (int, float)):
        champs["recul_voirie_m"] = float(voie["min_m"]); src["recul_voirie"] = _src_validee(voie)
    elif voie and voie.get("absent"):
        src["recul_voirie"] = _src_absente(voie)
    if lim and lim.get("forme") == "alignement":
        champs["recul_limites_sep_m"] = 0.0; champs["recul_limites_alignement"] = True
        src["recul_limites"] = _src_validee(lim)
    elif lim and not lim.get("absent") and isinstance(lim.get("min_m"), (int, float)):
        champs["recul_limites_sep_m"] = float(lim["min_m"]); src["recul_limites"] = _src_validee(lim)
    elif lim and lim.get("absent"):
        src["recul_limites"] = _src_absente(lim)

    # pleine terre (PLU-CALIBRAGE-7 forme 2 : composée `espaces_verts_pct × pleine_terre_part`) —
    # sourcée ici (l'ancienne lecture base-only ne portait pas d'article) ; valeur = _pleine_terre_val.
    pt = _feuille("pleine_terre", "pct")
    if pt and not pt.get("absent"):
        _ptv = _pleine_terre_val(reg)
        if isinstance(_ptv, (int, float)):
            champs["pleine_terre_pct"] = float(_ptv); src["pleine_terre"] = _src_validee(pt)
            _cmp = _pleine_terre_compose(reg)
            if _cmp:
                champs["pleine_terre_compose"] = _cmp
    elif pt and pt.get("absent"):
        src["pleine_terre"] = _src_absente(pt)

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
