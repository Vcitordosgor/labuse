"""CHASSE-DONNEES-FIX-1 (Lot 2) — LA garde unique « parcelle disparue du cadastre ».

Une parcelle marquée `parcels.cadastre_disparue_le` est sortie de la trame cadastrale à un
millésime récent (SOURCES-MAJ-1) : elle n'est plus servie par la carte / la recherche / les
filtres / les listes. La FICHE écran rend une fiche de courtoisie (message + remplaçantes), mais
les DOCUMENTS (export md/html/pdf, Dossier, Flash, gabarit, Comparatif, Courrier, KMZ) la
composaient comme vivante (« Surface : 2 853 m², zone UB », filiation « parcelle stable »…).

Un seul point de vérité : `info_disparue(db, idu)` rend le dict (ou None), `phrase_disparue(info)`
rend la phrase prête à imprimer. Tout document REFUSE de composer une disparue et sert ce message
à la place — jamais une donnée servie, jamais une parcelle de remplacement présentée comme la
parcelle demandée.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session


def colonne_presente(db: Session) -> bool:
    """`parcels.cadastre_disparue_le` est posée HORS ORM à l'ingestion différentielle (SOURCES-MAJ-1)
    — absente des schémas de test minimaux. Même garde que scoring/p_model/sql.py : on vérifie le
    catalogue avant toute requête, sinon « aucune disparue » (filtre vide)."""
    return bool(db.execute(text(
        "SELECT 1 FROM information_schema.columns "
        "WHERE table_name = 'parcels' AND column_name = 'cadastre_disparue_le'")).scalar())


def filtre_vivant_sql(db: Session, alias: str = "p") -> str:
    """Fragment SQL « AND {alias}.cadastre_disparue_le IS NULL » si la colonne existe, sinon ''.
    À concaténer dans un WHERE pour ne compter/servir que le parc vivant (résilient base de test)."""
    return f" AND {alias}.cadastre_disparue_le IS NULL" if colonne_presente(db) else ""


def info_disparue(db: Session, idu: str) -> dict | None:
    """Rend {idu, commune, disparue_le, message, remplacee_par[]} si la parcelle est sortie du
    cadastre, sinon None. Lookup PK indexé filtré sur le marqueur (≈0 ligne hors disparues)."""
    if not colonne_presente(db):
        return None
    row = db.execute(text(
        "SELECT commune, cadastre_disparue_le FROM parcels "
        "WHERE idu = :i AND cadastre_disparue_le IS NOT NULL"), {"i": idu}).mappings().first()
    if not row:
        return None
    dt = row["cadastre_disparue_le"]
    ds = dt.isoformat() if dt else None
    remp = db.execute(text(
        "SELECT r.nouvelle_idu AS idu, p.commune, r.taux_couv_ancienne AS recouvrement "
        "FROM parcel_cadastre_remplacement r JOIN parcels p ON p.idu = r.nouvelle_idu "
        "WHERE r.ancienne_idu = :i AND p.cadastre_disparue_le IS NULL "
        "ORDER BY r.taux_couv_ancienne DESC NULLS LAST"), {"i": idu}).mappings().all()
    return {
        "idu": idu, "commune": row["commune"], "disparue_le": ds,
        "message": (f"Parcelle disparue du cadastre (version du {ds})."
                    if ds else "Parcelle disparue du cadastre."),
        "remplacee_par": [dict(x) for x in remp],
    }


def phrase_disparue(info: dict) -> str:
    """Phrase prête à imprimer dans un document (une ligne) : message + remplaçantes éventuelles."""
    txt = info.get("message") or "Parcelle disparue du cadastre."
    remp = info.get("remplacee_par") or []
    if remp:
        txt += " Remplacée par : " + ", ".join(r["idu"] for r in remp if r.get("idu")) + "."
    txt += (" Aucune donnée n'est servie pour cette parcelle ; "
            "les documents ne peuvent pas être composés.")
    return txt
