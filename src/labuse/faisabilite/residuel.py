"""Potentiel résiduel (Lot B) — « cette parcelle est bâtie à N % de son potentiel ».

Croise deux choses qui existaient séparément :
  - le BÂTI EXISTANT (BD TOPO, via bati.py) : emprise au sol réellement construite ;
  - la CAPACITÉ MAX (faisabilité) : emprise constructible et SDP maximales.

Métriques :
  - `taux_emprise` = emprise bâtie / emprise constructible max  → RÉEL (aucune hypothèse
    de hauteur) ; sert au filtre « sous-densité ».
  - `sdp_existante` = emprise bâtie × niveaux du bâti existant. Les niveaux viennent de BD
    TOPO (`nombre_d_etages`/`hauteur`) QUAND ils sont ingérés ; sinon hypothèse PLACEHOLDER
    `niveaux_bati_existant_defaut` (prudente) → la SDP résiduelle est alors une ESTIMATION,
    signalée comme telle.
  - `sdp_residuelle` = max(0, SDP max − SDP existante) ; `pct_potentiel` = part déjà bâtie.

Lecture seule, isolée : ne touche ni la cascade ni le scoring.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import bati as bati_mod
from .db import parcel_faisabilite
from .engine import Hypotheses


def _niveaux_existants(session: Session, parcel_id: int, defaut: float) -> tuple[float, bool]:
    """Niveaux du bâti existant. Renvoie (niveaux, reel) — `reel=False` = hypothèse PLACEHOLDER
    (hauteur/étages BD TOPO non ingérés sur ce lot)."""
    row = session.execute(text(
        """SELECT max((b.attrs->>'nombre_d_etages')::int)            AS etages,
                  max(NULLIF(b.attrs->>'hauteur','')::float)         AS hauteur
           FROM spatial_layers b JOIN parcels p ON p.id = :pid
           WHERE b.kind='batiment' AND ST_Intersects(b.geom_2975, p.geom_2975)"""),
        {"pid": parcel_id}).first()
    if row and row.etages:
        return float(row.etages), True
    if row and row.hauteur:
        return max(1.0, round(float(row.hauteur) / 3.0)), True
    return float(defaut), False


def compute_residuel(session: Session, parcel_id: int,
                     faisa: tuple | None = None) -> dict:
    """Bloc « potentiel résiduel » d'une parcelle. `faisa` = (ctx, Faisabilite) déjà calculé
    (réutilisé par la fiche pour ne pas relancer le moteur). `disponible=False` quand la
    parcelle n'est pas constructible ou que le bâti n'est pas mesurable."""
    if not bati_mod.layer_available(session):
        return {"disponible": False, "raison": "Couche bâtiments (BD TOPO) non ingérée."}
    res = faisa or parcel_faisabilite(session, parcel_id)
    if res is None:
        return {"disponible": False, "raison": "Zone hors PLU outillé — capacité non calculable."}
    ctx, f = res
    if not f.constructible:
        return {"disponible": False, "raison": "Parcelle non constructible — pas de potentiel résiduel."}

    fr = f.fourchette
    emprise_max = float(fr.get("emprise_constructible_m2") or 0.0)
    sdp_max = float(fr.get("surface_plancher_m2") or 0.0)
    if emprise_max <= 0 or sdp_max <= 0:
        return {"disponible": False, "raison": "Capacité max nulle — résiduel non défini."}

    hyp = Hypotheses.charger()
    st = bati_mod.stats_batch(session, [parcel_id]).get(parcel_id, {})
    surface = float(ctx.surface_m2 or 0.0)
    emprise_batie = float(st.get("bati_ratio", 0.0)) * surface           # emprise au sol bâtie (réelle)

    niveaux_exist, niveaux_reels = _niveaux_existants(session, parcel_id, hyp.niveaux_bati_existant_defaut)
    sdp_existante = emprise_batie * niveaux_exist
    sdp_residuelle = max(0.0, sdp_max - sdp_existante)

    taux_emprise = min(999.0, 100.0 * emprise_batie / emprise_max) if emprise_max else 0.0
    pct_potentiel = min(999.0, 100.0 * sdp_existante / sdp_max) if sdp_max else 0.0
    seuil = float(hyp.sous_densite_seuil_pct)
    sous_densite = taux_emprise < seuil

    return {
        "disponible": True,
        "taux_emprise_pct": round(taux_emprise),
        "pct_potentiel": round(pct_potentiel),
        "sous_densite": sous_densite,
        "sous_densite_seuil_pct": round(seuil),
        "emprise_batie_m2": round(emprise_batie),
        "emprise_constructible_m2": round(emprise_max),
        "sdp_max_m2": round(sdp_max),
        "sdp_existante_m2": round(sdp_existante),
        "sdp_residuelle_m2": round(sdp_residuelle),
        "niveaux_max": fr.get("niveaux_max"),
        "niveaux_existants": round(niveaux_exist, 1),
        "niveaux_reels": niveaux_reels,
        # Résumé prudent (le taux d'emprise est réel ; la SDP résiduelle est estimée si la
        # hauteur du bâti n'est pas connue → on le dit).
        "libelle": _libelle(taux_emprise, sdp_residuelle, niveaux_reels),
        "estimation_sdp": not niveaux_reels,
        # Traçabilité capacité : calibré (YAML PLU communal) vs estimation générique.
        "calibree": f.calibree,
        "capacite_estimee": not f.calibree,
    }


def compute_residuel_batch(session: Session, parcel_ids: list[int]) -> int:
    """Calcule et CACHE le résiduel (table parcel_residuel) pour alimenter le filtre carte.
    Ne stocke que les parcelles où le résiduel est défini (constructibles)."""
    n = 0
    for pid in parcel_ids:
        try:
            r = compute_residuel(session, pid)
        except Exception:  # noqa: BLE001 - une parcelle ne casse pas le lot
            continue
        if not r.get("disponible"):
            session.execute(text("DELETE FROM parcel_residuel WHERE parcel_id = :p"), {"p": pid})
            continue
        session.execute(text(
            """INSERT INTO parcel_residuel
                 (parcel_id, taux_emprise_pct, pct_potentiel, sous_densite, sdp_residuelle_m2,
                  capacite_estimee, computed_at)
               VALUES (:p, :t, :pp, :sd, :sr, :ce, now())
               ON CONFLICT (parcel_id) DO UPDATE SET
                 taux_emprise_pct=EXCLUDED.taux_emprise_pct, pct_potentiel=EXCLUDED.pct_potentiel,
                 sous_densite=EXCLUDED.sous_densite, sdp_residuelle_m2=EXCLUDED.sdp_residuelle_m2,
                 capacite_estimee=EXCLUDED.capacite_estimee, computed_at=now()"""),
            {"p": pid, "t": r["taux_emprise_pct"], "pp": r["pct_potentiel"],
             "sd": r["sous_densite"], "sr": r["sdp_residuelle_m2"], "ce": r["capacite_estimee"]})
        n += 1
    session.flush()
    return n


def _libelle(taux: float, sdp_res: float, niveaux_reels: bool) -> str:
    etat = ("terrain nu — potentiel quasi intégral" if taux < 2
            else f"bâtie à ~{round(taux)} % de l'emprise constructible")
    suffix = "" if niveaux_reels else " (SDP résiduelle estimée — hauteur du bâti non ingérée)"
    return f"{etat} · SDP résiduelle ~{round(sdp_res)} m²{suffix}"
