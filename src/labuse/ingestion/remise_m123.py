"""M123 · Phase 2 — remise en état du CATALOGUE (arbitrage Vic). Idempotent, versionné, reproductible.

Ne touche PAS l'ingestion des données ni le scoring/cascade : range la vitrine `data_sources` selon les
décisions rendues (retraits, canal qui juge des doublons, dormance PV). À rejouer sans effet de bord :
chaque écriture est conditionnée à l'état courant (préfixe/segment absent).
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

#: RETRAITS — sortis de la vitrine (préfixe technical_notes 'RETIRÉ — …'), jamais supprimés (histoire
#: conservée). Le filtre WHERE_AFFICHEES exclut 'RETIRÉ%'. Raison écrite, reprise possible.
RETRAITS: dict[str, str] = {
    "EDF SEI Réunion — open data":
        "RETIRÉ — amont 410 Gone (jeu retiré par EDF SEI ~24/12/2025), aucun usage identifié. "
        "À reprendre si republié.",
    "Registre national des installations (ODRÉ)":
        "RETIRÉ — jamais branché, aucun usage identifié (a_faire dormant).",
    "Fichiers fonciers (Cerema)":
        "RETIRÉ — convention Cerema requise (démarchage commercial interdit) → table vide "
        "(parcel_source_results = 0). À reprendre si convention signée.",
}

#: DOUBLONS — sur la ligne CANONIQUE affichée, on NOMME le canal qui JUGE (le jumeau masqué qui
#: alimente réellement le moteur). Le client doit savoir quel cadastre / quel MNT sert.
CANAL_QUI_JUGE: dict[str, str] = {
    "Cadastre (API Carto PCI)": "CANAL SERVI : Cadastre Etalab bulk (alimente le socle `parcels`).",
    "RGE ALTI (altimétrie)": "CANAL SERVI : MNT 5 m (`rgealti_pente_5m`, alimente la pente scorée).",
}

#: DORMANTES ASSUMÉES — restent en vitrine, dites dormantes (pas un faux « servi »).
DORMANTES: dict[str, str] = {
    "PVGIS (Commission européenne)":
        "DORMANT — signal PV candidat mort (0 validé / 23 529, feature retirée M71 B2) ; conservé "
        "au catalogue, non servi.",
}


def _prefixer(db: Session, name: str, note: str) -> int:
    """Remplace technical_notes par `note` si le préfixe n'y est pas déjà (idempotent)."""
    cur = db.execute(text("SELECT technical_notes FROM data_sources WHERE name = :n"), {"n": name}).scalar()
    if cur is None:
        return 0
    if cur.startswith(note[:12]):
        return 0
    db.execute(text("UPDATE data_sources SET technical_notes = :t, updated_at = now() WHERE name = :n"),
               {"t": note, "n": name})
    return 1


def _appendre(db: Session, name: str, segment: str) -> int:
    """Ajoute ` · <segment>` à technical_notes s'il n'y est pas (idempotent)."""
    cur = db.execute(text("SELECT technical_notes FROM data_sources WHERE name = :n"), {"n": name}).scalar()
    if cur is None or segment in (cur or ""):
        return 0
    db.execute(text("UPDATE data_sources SET technical_notes = COALESCE(technical_notes,'') || :s, "
                    "updated_at = now() WHERE name = :n"), {"s": f" · {segment}", "n": name})
    return 1


def appliquer(db: Session) -> dict:
    """Applique les décisions de Phase 2 au catalogue. Renvoie le compte des lignes touchées."""
    n_retraits = sum(_prefixer(db, name, note) for name, note in RETRAITS.items())
    n_canal = sum(_appendre(db, name, seg) for name, seg in CANAL_QUI_JUGE.items())
    n_dormant = sum(_prefixer(db, name, note) for name, note in DORMANTES.items())
    db.flush()
    return {"retraits": n_retraits, "canal_nomme": n_canal, "dormantes": n_dormant}
