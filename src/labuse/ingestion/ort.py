"""SOURCES-1 lot 5 — ACV / PVD / ORT (DGALN/ANCT, table grist vivante via data.gouv).

Source vérifiée live 07/09/2026 : la table COMPLÈTE s'exporte par
`grist.numerique.gouv.fr/o/dgaln/api/docs/<doc>/download/csv?tableId=BDD` (2 440 communes ;
l'export « viewSection » du jeu data.gouv est FILTRÉ à 78 lignes — piège documenté). 19
communes 974, 13 conventions ORT SIGNÉES.

⚠ ÉCART MESURÉ vs attendu (fiche 10 du rapport) : ACV 974 = Saint-Pierre, Le Port,
Saint-André, Saint-Joseph — **Saint-Louis, attendu ACV, est ABSENT de la table** (contrôle
au filtre, avertissant). Périmètres infra-communaux NON publiés (conventions EPCI — demande
lot 7). Éligibilité Denormandie : commune en ORT signée = condition COMMUNALE remplie ; le
logement doit être dans le périmètre conventionné (non publié) — l'état le dit.
"""
from __future__ import annotations

import csv
import io

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings

SOURCE_NAME = "ACV / PVD / ORT (DGALN — liste des communes)"
URL_CSV = ("https://grist.numerique.gouv.fr/o/dgaln/api/docs/j4i9oKD3jzFtgEUuM9sXnL/"
           "download/csv?tableId=BDD")
MILLESIME = "table DGALN vivante (grist) — lecture 07/09/2026"
#: attendu du rapport (fiche 10) — contrôlé CONTRE le CSV réel, jamais imposé
ACV_ATTENDUES = {"97407": "Le Port", "97409": "Saint-André", "97412": "Saint-Joseph",
                 "97414": "Saint-Louis", "97416": "Saint-Pierre"}

DDL = """
CREATE TABLE IF NOT EXISTS commune_ort (
    insee          varchar(5) PRIMARY KEY,
    commune        varchar(64) NOT NULL,
    statut         varchar(16) NOT NULL,          -- acv | pvd | autre
    ort_signee     boolean NOT NULL,
    date_signature date,
    duree_annees   numeric(4,1),
    millesime      varchar(64) NOT NULL,
    maj_at         timestamptz NOT NULL DEFAULT now()
)
"""


def ensure_tables(engine) -> None:
    with engine.begin() as cx:
        cx.execute(text(DDL))


def ingest_ort(session: Session, *, url: str = URL_CSV, csv_text: str | None = None,
               client: httpx.Client | None = None, log=print) -> dict:
    """Télécharge la table BDD complète, garde le 974, upsert. Rend
    {"n", "signees", "acv", "pvd", "ecart_attendu"}."""
    if csv_text is None:
        own = client is None
        c = client or httpx.Client(timeout=max(get_settings().http_timeout_s, 120.0),
                                   headers={"User-Agent": constants.USER_AGENT},
                                   follow_redirects=True)
        try:
            r = c.get(url)
            r.raise_for_status()
            csv_text = r.content.decode("utf8", errors="replace")
        finally:
            if own:
                c.close()
    session.execute(text("DELETE FROM commune_ort"))
    n = signees = 0
    acv: list[str] = []
    pvd: list[str] = []
    vus: set[str] = set()
    for row in csv.DictReader(io.StringIO(csv_text)):
        insee = str(row.get("Code commune") or "").strip()
        if not insee.startswith("974"):
            continue
        est_acv = (row.get("ACV") or "").strip().lower() == "true"
        est_pvd = (row.get("PVD") or "").strip().lower() == "true"
        statut = "acv" if est_acv else ("pvd" if est_pvd else "autre")
        signee = (row.get("Signée ?") or "").strip().lower() == "signée"
        date_sig = (row.get("Si signée, date de signature") or "").strip() or None
        duree = (row.get("Durée (en années)") or "").strip()
        nom = (row.get("Commune") or "").split("-", 1)[-1].strip() or insee
        session.execute(text(
            "INSERT INTO commune_ort (insee, commune, statut, ort_signee, date_signature, "
            " duree_annees, millesime, maj_at) "
            "VALUES (:i, :c, :s, :sig, :d, :du, :m, now()) "
            "ON CONFLICT (insee) DO UPDATE SET commune = :c, statut = :s, ort_signee = :sig, "
            " date_signature = :d, duree_annees = :du, millesime = :m, maj_at = now()"),
            {"i": insee, "c": nom, "s": statut, "sig": signee, "d": date_sig,
             "du": float(duree) if duree.replace(".", "", 1).isdigit() else None,
             "m": MILLESIME})
        vus.add(insee)
        n += 1
        signees += int(signee)
        (acv if est_acv else pvd if est_pvd else []).append(nom)
    session.flush()
    ecart = sorted(f"{nom} ({insee}) attendue ACV, absente ou non-ACV dans la table"
                   for insee, nom in ACV_ATTENDUES.items()
                   if insee not in vus or insee not in {
                       i for (i,) in session.execute(text(
                           "SELECT insee FROM commune_ort WHERE statut = 'acv'")).all()})
    if ecart:
        log(f"  ⚠ ORT : écart vs attendu fiche 10 : {ecart}")
    return {"n": n, "signees": signees, "acv": sorted(acv), "pvd": sorted(pvd),
            "ecart_attendu": ecart}


def ort_commune(session: Session, insee: str) -> dict | None:
    """Statut ACV/PVD/ORT d'une commune + éligibilité Denormandie (condition communale),
    sourcé + daté. None si non ingéré.
    KELFONCIER-FIX-1 — garde d'existence de la table AVANT toute requête : sur une base sans
    `commune_ort` (schéma de test), interroger la table poisonnait la transaction de l'appelant
    (fiche §7, Étude de zone). `to_regclass` renvoie NULL pour une table absente, sans échec SQL."""
    if session.execute(text("SELECT to_regclass('commune_ort')")).scalar() is None:
        return None
    row = session.execute(text(
        "SELECT insee, commune, statut, ort_signee, date_signature, millesime "
        "FROM commune_ort WHERE insee = :i"), {"i": insee}).mappings().first()
    if row is None:
        # table peuplée mais commune absente = hors dispositif (l'état le dit)
        if session.execute(text("SELECT 1 FROM commune_ort LIMIT 1")).scalar():
            return {"statut": "hors", "ort_signee": False,
                    "denormandie": "non éligible (commune hors ACV/PVD/ORT)"}
        return None
    d = dict(row)
    d["date_signature"] = d["date_signature"].isoformat() if d["date_signature"] else None
    d["denormandie"] = (
        "éligible sous conditions — commune en ORT signée (logement DANS le périmètre "
        "conventionné requis, périmètre non publié ; travaux ≥ 25 % du coût total ; "
        "jusqu'au 31/12/2027)" if d["ort_signee"] else
        "non éligible en l'état (convention ORT non signée)")
    return d
