"""CAPACITE-1 LOT C/D — LA règle unique « surface à retenir », lue par TOUS les documents.

Deux grandeurs, deux noms, jamais confondus :
  · **estimation rapide** — moteur analytique (`faisabilite/engine`), disponible pour TOUTE parcelle,
    base de la fiche, du Dossier, du Comparatif et du classement ;
  · **esquisse d'implantation** — l'Étude de faisabilité (`implantation/moteur`), qui DESSINE des
    bâtiments ; toujours « à vérifier », jamais « exploitable » (ses contrôles — stationnement compris —
    peuvent appliquer une règle inexacte, cf. LOT D : un contrôle faux ne « retient » pas un scénario).

LOT D (décision Vic 15/11) — la « surface à retenir » est la PLUS PRUDENTE des deux : la PLUS PETITE
entre l'estimation rapide et l'esquisse quand une esquisse existe ; sinon l'estimation rapide. Jamais le
plus grand chiffre par défaut. Fonction PURE, testable, appelée à l'identique par chaque document → un
seul « surface à retenir » par parcelle (garde-fou).
"""
from __future__ import annotations

GRANDEUR_ESTIMATION = "estimation rapide"
GRANDEUR_ESQUISSE = "esquisse d'implantation"
#: compat : d'anciens appels importent GRANDEUR_SCENARIO — c'est l'esquisse d'implantation.
GRANDEUR_SCENARIO = GRANDEUR_ESQUISSE


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


def surface_a_retenir(estimation_rapide_m2, esquisse=None) -> dict:
    """`esquisse` = la SDP de l'esquisse d'implantation (float), ou un dict {"sdp_m2": …} (compat), ou
    None quand aucune Étude n'a été dessinée.

    Retourne {"valeur_m2", "source" (GRANDEUR_*), "phrase", "estimation_rapide_m2", "esquisse_m2"}.

    LOT D — la surface à retenir est la PLUS PETITE des deux (prudente), jamais la plus grande :
      · pas d'esquisse → estimation rapide ;
      · esquisse < estimation → on retient l'esquisse (« à vérifier : la surface réelle peut être
        inférieure » — ses contrôles, dont le stationnement, ne sont pas garantis) ;
      · estimation ≤ esquisse → on retient l'estimation (l'esquisse est un majorant, stationnement non
        déduit). L'esquisse est TOUJOURS « à vérifier », jamais « exploitable »."""
    est = round(float(estimation_rapide_m2)) if estimation_rapide_m2 not in (None, "") else None
    esq = None
    if isinstance(esquisse, dict):
        esquisse = esquisse.get("sdp_m2")
    if esquisse not in (None, ""):
        esq = round(float(esquisse))

    def _out(valeur, source, phrase):
        return {"valeur_m2": valeur, "source": source, "phrase": phrase,
                "estimation_rapide_m2": est, "esquisse_m2": esq}

    if est is None and esq is None:
        return _out(None, GRANDEUR_ESTIMATION,
                    "Surface à retenir : non calculée (capacité nulle ou non constructible).")
    if esq is None:                                   # aucune esquisse → estimation rapide
        return _out(est, GRANDEUR_ESTIMATION, f"Surface à retenir : {_m2(est)} ({GRANDEUR_ESTIMATION}).")
    if est is None or esq < est:                      # esquisse retenue (la plus petite / prudente)
        phrase = (f"Surface à retenir : {_m2(esq)} ({GRANDEUR_ESQUISSE}, stationnement à vérifier : "
                  "la surface réelle peut être inférieure).")
        if est is not None:
            phrase += f" L'estimation rapide donnait {_m2(est)}, hors stationnement."
        return _out(esq, GRANDEUR_ESQUISSE, phrase)
    # estimation ≤ esquisse → estimation retenue (l'esquisse est un majorant)
    return _out(est, GRANDEUR_ESTIMATION,
                f"Surface à retenir : {_m2(est)} ({GRANDEUR_ESTIMATION}). L'esquisse d'implantation "
                f"atteint {_m2(esq)}, à vérifier : stationnement non déduit.")
