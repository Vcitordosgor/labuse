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
    "VRD / assainissement (SPANC)":
        "DORMANT — manuel EPCI, aucune table ni chemin servi (le 'VRD' du bilan est un poste de coût, "
        "pas cette source) ; conservé au catalogue, hors vitrine tant qu'il ne sert pas.",
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


#: CASSÉES — doublons d'INGESTION dans spatial_layers (même géométrie ré-ingérée par bbox commune).
#: Dedup EXACT (geom, name, subtype) : la cascade intersecte la géométrie (booléen) → une géométrie
#: dupliquée est REDONDANTE, le dedup NE CHANGE AUCUN résultat servi (prouvé golden avant/après).
DEDUP_KINDS: tuple[str, ...] = ("foret_publique", "ocs_ge")


def dedup_kind(db: Session, kind: str) -> dict:
    """Supprime les doublons EXACTS (même geom+name+subtype) d'une couche, garde le plus ancien id.
    Idempotent (relancé = 0 supprimé). Renvoie avant/après pour la preuve."""
    avant = db.execute(text("SELECT count(*) FROM spatial_layers WHERE kind = :k"), {"k": kind}).scalar()
    db.execute(text("""
        DELETE FROM spatial_layers a USING spatial_layers b
        WHERE a.kind = :k AND b.kind = :k AND a.id > b.id
          AND a.geom IS NOT DISTINCT FROM b.geom
          AND a.name IS NOT DISTINCT FROM b.name
          AND a.subtype IS NOT DISTINCT FROM b.subtype"""), {"k": kind})
    apres = db.execute(text("SELECT count(*) FROM spatial_layers WHERE kind = :k"), {"k": kind}).scalar()
    return {"kind": kind, "avant": avant, "apres": apres, "supprimes": avant - apres}


#: CASSÉE — sonde Géorisques PPR sur endpoint v1 (404) : la sonde radar/le catalogue doit pointer
#: la v2 DEAL Réunion Lizmap (la couche `ppr` en base VIENT déjà de là ; seule l'URL de sonde était morte).
PPR_ENDPOINT_V2 = ("https://lizmap.geoportail-reunion.fr/lizmap/index.php/lizmap/service?repository="
                   "deal&project=risques&SERVICE=WFS&VERSION=1.1.0&REQUEST=GetCapabilities")


def appliquer(db: Session) -> dict:
    """Applique les décisions de Phase 2 au catalogue. Renvoie le compte des lignes touchées."""
    n_retraits = sum(_prefixer(db, name, note) for name, note in RETRAITS.items())
    n_canal = sum(_appendre(db, name, seg) for name, seg in CANAL_QUI_JUGE.items())
    n_dormant = sum(_prefixer(db, name, note) for name, note in DORMANTES.items())
    # CASSÉE PPR : corriger l'endpoint de sonde mort (v1 404 → v2 Lizmap) — la donnée servie ne bouge pas.
    ppr = db.execute(text("UPDATE data_sources SET endpoint_url = :u, updated_at = now() "
                          "WHERE name = 'DEAL Réunion — PPR / aléas' AND endpoint_url IS DISTINCT FROM :u"),
                     {"u": PPR_ENDPOINT_V2}).rowcount
    dedups = [dedup_kind(db, k) for k in DEDUP_KINDS]
    db.flush()
    return {"retraits": n_retraits, "canal_nomme": n_canal, "dormantes": n_dormant,
            "ppr_endpoint": ppr, "dedups": dedups}
