"""Blocs fonciers (OUTILS-MUSCLER-3) — les assiettes d'un même propriétaire personne morale,
faites de parcelles cadastrales CONTIGUËS, sur toute l'île.

Balaie l'île, calcule les composantes connexes par SIREN et écrit `parcel_blocs` (+ membres).
Lecture seule côté sources : le batch n'écrit QUE ses deux tables. Idempotent : DELETE + rebuild
atomique — rejouer produit le même contenu (bloc_key déterministe).

Règles de regroupement (B3), explicites :
  - CONTIGUÏTÉ : `ST_DWithin(geom_2975, 0,5 m)` — même contact cadastral que l'Assemblage
    (`assemblage.ADJ_BUFFER_M`, source unique de la constante).
  - PROPRIÉTAIRE : MÊME SIREN (`parcelle_personne_morale.siren`). Les particuliers, sans identité
    stable d'une parcelle à l'autre, sont HORS périmètre — aucun regroupement par nom approché.
  - CADASTRAL SEULEMENT : `parcels` EST la couche cadastrale (IDU 14 caractères) ; le domaine
    public non cadastré n'y figure pas → la règle est satisfaite par construction.
  - TAILLE : un bloc = composante connexe d'AU MOINS 2 parcelles (`MIN_PARCELLES`).

Résiduel SDP : agrégé (SOMME des résiduels par parcelle) depuis la vue SERVIE `parcel_residuel`
— statut Estimé. On épingle le `run_seq` résiduel servi au moment du build.
"""
from __future__ import annotations

from collections import defaultdict

from sqlalchemy import insert, text
from sqlalchemy.orm import Session

from . import models
from .assemblage import ADJ_BUFFER_M  # 0,5 m — contact cadastral, constante unique
from .faisabilite import residuel_runs

MIN_PARCELLES = 2


def ensure_schema(session: Session) -> None:
    """Crée `parcel_blocs` + `parcel_bloc_membres` si absentes (idempotent). N'affecte rien d'autre."""
    bind = session.get_bind()
    models.ParcelBloc.__table__.create(bind, checkfirst=True)
    models.ParcelBlocMembre.__table__.create(bind, checkfirst=True)


class _UnionFind:
    def __init__(self, items):
        self.p = {i: i for i in items}

    def find(self, x):
        r = x
        while self.p[r] != r:
            r = self.p[r]
        while self.p[x] != r:
            self.p[x], x = r, self.p[x]
        return r

    def union(self, a, b):
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def compute_blocs(session: Session) -> list[dict]:
    """Calcule les blocs (≥ 2 parcelles contiguës, même SIREN) sur toute l'île. Aucune écriture.

    Renvoie une liste de dicts prêts à insérer (header + membres), triée par résiduel décroissant.
    """
    # 1 — parcelles des PM, dans une table temporaire indexée (le self-join spatial passe par le
    #     GIST geom_2975 ; jointure bornée au même SIREN → un SIREN à la fois, jamais le produit île).
    session.execute(text("DROP TABLE IF EXISTS _blocs_pm"))
    session.execute(text(
        """CREATE TEMP TABLE _blocs_pm AS
           SELECT pa.id AS pid, pa.idu, p.siren, pa.geom_2975,
                  round(pa.surface_m2)::int AS surface, pa.commune
           FROM parcelle_personne_morale p
           JOIN parcels pa ON pa.idu = p.idu
           WHERE p.siren IS NOT NULL AND p.siren <> ''"""))
    session.execute(text("CREATE INDEX ON _blocs_pm USING gist(geom_2975)"))
    session.execute(text("CREATE INDEX ON _blocs_pm(siren)"))

    nodes = session.execute(text(
        "SELECT pid, idu, siren, surface, commune FROM _blocs_pm")).mappings().all()
    edges = session.execute(text(
        """SELECT a.pid AS a, b.pid AS b FROM _blocs_pm a JOIN _blocs_pm b
             ON a.siren = b.siren AND a.pid < b.pid
            AND ST_DWithin(a.geom_2975, b.geom_2975, :buf)"""),
        {"buf": ADJ_BUFFER_M}).all()

    by_pid = {n["pid"]: n for n in nodes}
    uf = _UnionFind(by_pid.keys())
    for a, b in edges:
        uf.union(a, b)

    comps: dict[int, list[int]] = defaultdict(list)
    for pid in by_pid:
        comps[uf.find(pid)].append(pid)
    blocs_pids = [m for m in comps.values() if len(m) >= MIN_PARCELLES]

    # 2 — enrichissements en lot (résiduel servi + zone + dénomination).
    member_pids = [pid for m in blocs_pids for pid in m]
    member_idus = [by_pid[pid]["idu"] for pid in member_pids]

    resid_run = residuel_runs.served_run_seq(session.connection())
    resid = dict(session.execute(text(
        "SELECT parcel_id, sdp_residuelle_m2 FROM parcel_residuel WHERE parcel_id = ANY(:ids)"),
        {"ids": member_pids}).all()) if member_pids else {}
    zone = dict(session.execute(text(
        "SELECT idu, COALESCE(zone_lib, zone_fam) FROM parcel_zone_plu WHERE idu = ANY(:idus)"),
        {"idus": member_idus}).all()) if member_idus else {}
    sirens = list({by_pid[m[0]]["siren"] for m in blocs_pids})
    denom = dict(session.execute(text(
        "SELECT siren, max(denomination) FROM parcelle_personne_morale "
        "WHERE siren = ANY(:s) GROUP BY siren"), {"s": sirens}).all()) if sirens else {}

    # 3 — agrégation par bloc.
    out: list[dict] = []
    for pids in blocs_pids:
        members = [by_pid[pid] for pid in pids]
        siren = members[0]["siren"]
        min_idu = min(m["idu"] for m in members)
        communes = sorted({m["commune"] for m in members if m["commune"]})
        zonages = sorted({zone.get(m["idu"]) for m in members if zone.get(m["idu"])})
        sdp_par = {pid: resid.get(pid) for pid in pids}
        sdp_total = sum(v for v in sdp_par.values() if v is not None)
        couverture = sum(1 for v in sdp_par.values() if v is not None)
        out.append({
            "bloc_key": f"{siren}:{min_idu}",
            "siren": siren,
            "denomination": denom.get(siren),
            "n_parcelles": len(members),
            "surface_totale_m2": sum(m["surface"] or 0 for m in members),
            "communes": communes,
            "sdp_residuelle_m2": int(sdp_total),
            "sdp_couverture": couverture,
            "zonages": zonages,
            "residuel_run_seq": resid_run,
            "membres": [{
                "idu": m["idu"], "parcel_id": m["pid"], "surface_m2": m["surface"],
                "commune": m["commune"], "zone": zone.get(m["idu"]),
                "sdp_residuelle_m2": resid.get(m["pid"]),
            } for m in members],
        })
    out.sort(key=lambda b: b["sdp_residuelle_m2"], reverse=True)
    return out


def build_blocs(session: Session, *, progress_cb=None) -> dict:
    """Reconstruit `parcel_blocs` + `parcel_bloc_membres` en bloc (idempotent). Renvoie des stats.

    `progress_cb(phase, done, total)` — optionnel — pour la barre de progression du run.
    """
    ensure_schema(session)
    if progress_cb:
        progress_cb("contiguïté", 0, 3)
    blocs = compute_blocs(session)
    if progress_cb:
        progress_cb("écriture", 2, 3)

    # DELETE + rebuild atomique (la transaction est commitée par l'appelant).
    session.execute(text("DELETE FROM parcel_bloc_membres"))
    session.execute(text("DELETE FROM parcel_blocs"))

    n_membres = 0
    for b in blocs:
        membres = b.pop("membres")
        bloc_id = session.execute(
            insert(models.ParcelBloc).returning(models.ParcelBloc.id), b).scalar_one()
        for m in membres:
            m["bloc_id"] = bloc_id
        if membres:
            session.execute(insert(models.ParcelBlocMembre), membres)
            n_membres += len(membres)

    if progress_cb:
        progress_cb("terminé", 3, 3)
    return {"n_blocs": len(blocs), "n_membres": n_membres,
            "residuel_run_seq": blocs[0]["residuel_run_seq"] if blocs else None}
