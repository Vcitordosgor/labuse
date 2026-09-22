"""Cascade v2 — classification A/B/C/D des verdicts (SCORING-6 lot C).

Applique la classification du SCORING-5-RAPPORT §5 aux verdicts de la cascade existante, SANS
rejouer la cascade ni toucher le servi : le nouveau moteur (Score LABUSE + combinaison) lit les
verdicts de `dryrun_cascade_results` et les reclasse.

  · A — SEULE exclusion dure (assiette nulle certaine) ;
  · B — pénalité d'assiette/faisabilité (jamais une exclusion). PPR/ER/EBC/PEB + A/N sont
    VENTILÉES : A si recouvrement 100 %, B si partiel (une portion exploitable subsiste — c'est
    le lot A qui la valorise) ;
  · C — motif informatif, filtrable ;
  · D — supprimée / déplacée (proxy mort, ou signal parti au Signal de mutation / à l'info fiche).

Le proxy `ocs_ge` (BDCARTO, classe D) est remplacé par la VRAIE OCS GE (`parcel_ocsge`, 100 %),
lue comme information de contrôle (`ocsge_info`). Les motifs sont conservés (pour les filtres).
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from functools import lru_cache

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import load_yaml_config

_PCT_RE = re.compile(r"(\d+(?:[.,]\d+)?)\s*%")


@lru_cache(maxsize=1)
def charger_classification() -> dict:
    return load_yaml_config("cascade_v2").get("cascade_v2", {})


def pct_de_detail(detail: str | None) -> float | None:
    """% de recouvrement porté par le libellé du verdict (le dry-run l'imprime : « … 96 % … »).
    SCORING-5-RETOUR §5.3 : ventilation 100 %/partiel = parser le `detail`. None si absent."""
    if not detail:
        return None
    m = _PCT_RE.search(detail)
    return float(m.group(1).replace(",", ".")) if m else None


@dataclass
class VerdictV2:
    layer_name: str
    result: str                  # verdict d'origine (HARD_EXCLUDE / SOFT_FLAG / POSITIVE / …)
    classe: str                  # A / B / C / D
    detail: str | None = None
    recouvrement_pct: float | None = None
    exclusion: bool = False      # True SEULEMENT si classe A ET HARD_EXCLUDE (assiette nulle)


@dataclass
class ReclassementParcelle:
    exclue: bool = False                       # au moins une exclusion dure de classe A
    exclusions: list[VerdictV2] = field(default_factory=list)   # A
    penalites: list[VerdictV2] = field(default_factory=list)    # B
    infos: list[VerdictV2] = field(default_factory=list)        # C
    supprimes: list[VerdictV2] = field(default_factory=list)    # D (motif conservé mais inerte)

    def motifs(self) -> list[dict]:
        """Tous les motifs conservés en base pour les filtres (classe + libellé + recouvrement)."""
        out = []
        for grp in (self.exclusions, self.penalites, self.infos, self.supprimes):
            for v in grp:
                out.append({"layer": v.layer_name, "classe": v.classe,
                            "result": v.result, "recouvrement_pct": v.recouvrement_pct,
                            "detail": v.detail})
        return out


def classer_verdict(layer_name: str, result: str, detail: str | None = None,
                    recouvrement_pct: float | None = None, cfg: dict | None = None) -> VerdictV2:
    """Classe UN verdict. Ventilation A/B pour les familles ventilées (via le recouvrement).
    Un verdict de classe B ne produit JAMAIS d'exclusion (invariant vérifié par test)."""
    cfg = cfg or charger_classification()
    classes = cfg.get("classes", {})
    ventilees = set(cfg.get("ventilees", []))
    seuil = float(cfg.get("seuil_ventile_100_pct", 99))
    base = classes.get(layer_name, "C")        # couche inconnue → informative (défaut prudent)
    pct = recouvrement_pct if recouvrement_pct is not None else pct_de_detail(detail)

    classe = base
    if layer_name in ventilees and result == "HARD_EXCLUDE":
        # A si recouvrement 100 % (assiette nulle certaine) ; sinon B (portion exploitable).
        classe = "A" if (pct is not None and pct >= seuil) else "B"
    # une exclusion dure ne subsiste QUE pour une classe A sur un verdict HARD_EXCLUDE.
    exclusion = (classe == "A" and result == "HARD_EXCLUDE")
    return VerdictV2(layer_name, result, classe, detail, pct, exclusion)


def reclasser(verdicts: list[dict], cfg: dict | None = None) -> ReclassementParcelle:
    """Reclasse tous les verdicts d'une parcelle. `verdicts` = [{layer_name, result, detail,
    recouvrement_pct?}]. Renvoie l'exclusion v2 (classe A seule) et les motifs ventilés."""
    cfg = cfg or charger_classification()
    r = ReclassementParcelle()
    for v in verdicts:
        vv = classer_verdict(v.get("layer_name"), v.get("result"), v.get("detail"),
                             v.get("recouvrement_pct"), cfg)
        if vv.classe == "A":
            r.exclusions.append(vv)
            if vv.exclusion:
                r.exclue = True
        elif vv.classe == "B":
            r.penalites.append(vv)
        elif vv.classe == "D":
            r.supprimes.append(vv)
        else:
            r.infos.append(vv)
    return r


# ── verdicts d'origine (lecture du dry-run existant, aucune écriture) ─────────
_VERDICTS_SQL = text("""
SELECT parcel_id, layer_name, result, detail
FROM dryrun_cascade_results
WHERE run_label = :label AND parcel_id = ANY(:ids)
""")


def lire_verdicts(session: Session, parcel_ids: list[int], run_label: str) -> dict[int, list[dict]]:
    rows = session.execute(_VERDICTS_SQL, {"ids": list(parcel_ids), "label": run_label})
    out: dict[int, list[dict]] = {}
    for r in rows:
        out.setdefault(r.parcel_id, []).append(
            {"layer_name": r.layer_name, "result": r.result, "detail": r.detail})
    return out


# ── OCS GE réelle (remplace le proxy BDCARTO `ocs_ge`, classe D) ──────────────
_OCSGE_SQL = text("""
SELECT p.id AS parcel_id, o.part_artif_pct, o.us_dominant, o.millesime
FROM parcels p JOIN parcel_ocsge o ON o.idu = p.idu
WHERE p.id = ANY(:ids)
""")


def lire_ocsge(session: Session, parcel_ids: list[int]) -> dict[int, dict]:
    """OCS GE officielle par parcelle (contrôle qualité de l'artificialisation — information, pas
    un axe scoré). Remplace le proxy `ocs_ge` BDCARTO supprimé (classe D)."""
    rows = session.execute(_OCSGE_SQL, {"ids": list(parcel_ids)})
    return {r.parcel_id: {"part_artif_pct": (float(r.part_artif_pct)
                                             if r.part_artif_pct is not None else None),
                          "us_dominant": r.us_dominant, "millesime": r.millesime}
            for r in rows}


def reclasser_batch(session: Session, parcel_ids: list[int],
                    cascade_label: str) -> dict[int, ReclassementParcelle]:
    """Reclassement v2 d'un sous-ensemble, à partir des verdicts cascade de `cascade_label`."""
    cfg = charger_classification()
    verdicts = lire_verdicts(session, parcel_ids, cascade_label)
    return {pid: reclasser(verdicts.get(pid, []), cfg) for pid in parcel_ids}
