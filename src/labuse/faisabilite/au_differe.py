"""CHASSE-FIX-1 (C06) — RÈGLE UNIQUE du « potentiel différé » des zones AU non ouvertes.

Décision Vic : une zone AU fermée GARDE sa capacité calculée (doctrine « différée, pas
exclue », déjà appliquée par le Score ×0,5) mais AUCUN lecteur ne la présente comme
disponible. Tous les lecteurs (fiche §Potentiel, Faisabilité, Gabarit, PDF, Copilote)
passent par CETTE fonction — jamais une copie de la jointure ni du libellé.

Les classes « différées » sont exactement les classes BLOQUANTES du moteur d'ouverture AU
(parcel_au_statut) : fermée, phasage indéterminé, zone non calibrée. Les classes
conditionnelles (opération d'ensemble, plancher) restent du « constructible sous
condition », pas du différé.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

#: classes qui empêchent de construire TANT QUE la zone n'est pas ouverte — source unique
#: (app._AU_CLASSES_BLOQUANTES importe d'ici depuis CHASSE-FIX-1).
AU_CLASSES_DIFFEREES = frozenset({"declasse_au_fermee", "declasse_au_statut_inconnu", "générique"})

LIBELLE_COURT = "Potentiel différé — ouverture de la zone requise"


def libelle_differe(sdp_m2: float | None) -> str:
    """Le libellé client, UN SEUL endroit : « Potentiel différé — ouverture de la zone
    requise · ≈ N m² après ouverture » (sans la clause m² si la SDP est inconnue)."""
    if sdp_m2 is not None and sdp_m2 > 0:
        return f"{LIBELLE_COURT} · ≈ {round(sdp_m2):,} m² après ouverture".replace(",", " ")
    return LIBELLE_COURT


def statut_differe(session: Session, *, idu: str | None = None,
                   parcel_id: int | None = None) -> dict | None:
    """None si la parcelle n'est pas en zone AU à ouverture bloquée ; sinon
    {classe, zone_lib, motif} — la capacité servie est à présenter DIFFÉRÉE."""
    if idu is None and parcel_id is None:
        return None
    where, params = ("idu = :v", {"v": idu}) if idu is not None else ("parcel_id = :v", {"v": parcel_id})
    try:
        r = session.execute(text(
            f"SELECT classe, zone_lib, motif FROM parcel_au_statut WHERE {where}"),
            params).mappings().first()
    except Exception:  # noqa: BLE001 — table absente (base de test minimale) : pas de différé
        return None
    if not r or r["classe"] not in AU_CLASSES_DIFFEREES:
        return None
    return {"classe": r["classe"], "zone_lib": r["zone_lib"], "motif": r["motif"]}
