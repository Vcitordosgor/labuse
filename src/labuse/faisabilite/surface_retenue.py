"""CAPACITE-1 LOT C — LA règle unique « surface à retenir », lue par TOUS les documents.

Deux grandeurs, deux noms, jamais confondus (décision Vic 14/11) :
  · **estimation rapide** — moteur analytique (`faisabilite/engine`), disponible pour TOUTE parcelle,
    base de la fiche, du Dossier, du Comparatif et du classement ;
  · **scénario d'implantation** — l'Étude de faisabilité (`implantation/moteur`), qui DESSINE des
    bâtiments et déduit le stationnement quand son barème est connu.

La « surface à retenir » vaut le scénario SEULEMENT si une Étude existe ET que tous ses contrôles durs
ont été appliqués, **stationnement compris** ; sinon l'estimation rapide. Le plus grand chiffre n'est
jamais « la » capacité par défaut (règle LABUSE : jamais de faux positif). Fonction PURE, testable,
appelée à l'identique par chaque document → un seul « surface à retenir » par parcelle (garde-fou).
"""
from __future__ import annotations

GRANDEUR_ESTIMATION = "estimation rapide"
GRANDEUR_SCENARIO = "scénario d'implantation"


def _m2(v) -> str:
    return f"{round(float(v)):,}".replace(",", " ") + " m²"


def estimation_rapide_m2(db, idu: str):
    """L'ESTIMATION RAPIDE (table rase, moteur analytique) d'une parcelle, lue EN DIRECT via
    `parcel_faisabilite` — comparable au scénario d'implantation (lui aussi « terrain libéré »), et
    robuste même quand la colonne `sdp_max_m2` du run servi n'est pas peuplée (cas d'une parcelle bâtie
    dans une base dont le run résiduel est partiel). None si non constructible / non calculable."""
    try:
        from sqlalchemy import text
        from .db import parcel_faisabilite
        pid = db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()
        if not pid:
            return None
        res = parcel_faisabilite(db, pid)   # (ParcelContext, Faisabilite) | None
        if not res:
            return None
        f = res[1]
        if f is None or not getattr(f, "constructible", False):
            return None
        return (f.fourchette or {}).get("surface_plancher_m2")
    except Exception:  # noqa: BLE001 — lecture annexe, jamais bloquante
        return None


def surface_a_retenir(estimation_rapide_m2, scenario: dict | None = None) -> dict:
    """`scenario` = None (aucune Étude) ou {"sdp_m2": float, "stationnement_applique": bool}.

    Retourne {"valeur_m2", "source" (GRANDEUR_*), "phrase", "estimation_rapide_m2", "scenario_m2"}.
    `stationnement_applique=False` ⇒ le scénario est un MAJORANT (règle de stationnement non appliquée) :
    on retient l'estimation rapide et on le dit."""
    est = round(float(estimation_rapide_m2)) if estimation_rapide_m2 not in (None, "") else None
    scn = None
    if scenario and scenario.get("sdp_m2") not in (None, ""):
        scn = round(float(scenario["sdp_m2"]))
    stat_ok = bool(scenario and scenario.get("stationnement_applique"))

    if scn is not None and stat_ok:
        phrase = f"Surface à retenir : {_m2(scn)} ({GRANDEUR_SCENARIO}, stationnement déduit)."
        if est is not None:
            phrase += f" L'estimation rapide donnait {_m2(est)}, hors stationnement."
        return {"valeur_m2": scn, "source": GRANDEUR_SCENARIO, "phrase": phrase,
                "estimation_rapide_m2": est, "scenario_m2": scn}

    # estimation rapide retenue (pas d'Étude, ou contrôles durs incomplets — stationnement non vérifié)
    if est is None:
        return {"valeur_m2": None, "source": GRANDEUR_ESTIMATION,
                "phrase": "Surface à retenir : non calculée (capacité nulle ou non constructible).",
                "estimation_rapide_m2": None, "scenario_m2": scn}
    phrase = f"Surface à retenir : {_m2(est)} ({GRANDEUR_ESTIMATION})."
    if scn is not None:
        phrase += (f" Le scénario dessiné atteint {_m2(scn)}, non retenu tant que le stationnement "
                   "n'est pas vérifié.")
    return {"valeur_m2": est, "source": GRANDEUR_ESTIMATION, "phrase": phrase,
            "estimation_rapide_m2": est, "scenario_m2": scn}
