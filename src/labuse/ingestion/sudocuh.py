"""SOURCES-5 #14 — Sudocuh : le FICHIER OFFICIEL complet (DGALN), plus le petit extrait curaté.

L'ancien `scripts/m41_ingest_sudocuh.py` chargeait un CSV local de 6 colonnes (24 communes). Ce
module reprend le FLUX OFFICIEL : le classeur XLSX national « État des documents d'urbanisme par
commune » (data.gouv, DGALN, Licence Ouverte 2.0), feuille `ListeCommunes`, **23 colonnes**, filtré
au 974 (garde 974 par code INSEE). Tout champ publié conservé (colonnes promues + `raw` jsonb).

Table de PROVENANCE `sudocuh_procedures` (hors scoring direct sauf `approbation_opp`, lu par qv14
comme date as-of du DU) ; la CHAIR SERVIE reste `config/veille_plu.yaml` (registre curaté). Idempotent.
"""
from __future__ import annotations

import datetime as _dt
import io
import json
import logging

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

log = logging.getLogger("labuse.sudocuh")

# classeur XLSX « État des documents d'urbanisme par commune » (dernier état 31/12/2024).
URL = "https://www.data.gouv.fr/api/1/datasets/r/61541a0f-e9b0-43dc-bace-6c3905714400"
SHEET = "ListeCommunes "
MILLESIME_DATE = "2024-12-31"
SOURCE_NAME = "Sudocuh (procédures d'urbanisme)"

# ── colonnes promues (au-delà des 6 de l'extrait M41) : tout champ publié du fichier officiel ──
_ALTERS = (
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS region text",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS dept text",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS collectivite_porteuse text",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS siren_epci text",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS code_etat text",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS id_du_opp text",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS id_en_cours text",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS code_bcsi text",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS etat_commune text",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS prescription_du_vigueur date",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS executoire_du_vigueur date",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS pop_mun integer",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS pop_tot integer",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS superficie_km2 numeric",
    "ALTER TABLE sudocuh_procedures ADD COLUMN IF NOT EXISTS raw jsonb",
)


def ensure_tables(session: Session) -> None:
    session.execute(text("""
        CREATE TABLE IF NOT EXISTS sudocuh_procedures (
          insee varchar(5) PRIMARY KEY, commune text, du_opposable text, du_en_cours text,
          etat_detaille text, prescription_proc date, approbation_opp date,
          millesime_date date, ingested_at timestamptz DEFAULT now())"""))
    for stmt in _ALTERS:
        session.execute(text(stmt))


def _d(v):
    """Date XLSX → date python (ou None)."""
    if isinstance(v, _dt.datetime):
        return v.date()
    if isinstance(v, _dt.date):
        return v
    return None


def _i(v):
    try:
        return int(v)
    except (TypeError, ValueError):
        return None


def _j(v):
    """Valeur sérialisable JSON pour le raw (datetime → iso)."""
    if isinstance(v, (_dt.datetime, _dt.date)):
        return v.isoformat()
    return v


def ingest_sudocuh(session: Session, log=print, content: bytes | None = None) -> dict:
    """Télécharge le classeur XLSX officiel, filtre le 974 (garde INSEE), upsert les 23 colonnes."""
    import openpyxl

    ensure_tables(session)
    if content is None:
        r = httpx.get(URL, timeout=180, follow_redirects=True)
        r.raise_for_status()
        content = r.content
    wb = openpyxl.load_workbook(io.BytesIO(content), read_only=True, data_only=True)
    ws = wb[SHEET]
    it = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(it)]
    idx = {h: i for i, h in enumerate(header)}

    def g(row, col):
        i = idx.get(col)
        return row[i] if i is not None and i < len(row) else None

    n = 0
    for row in it:
        insee = str(g(row, "Code INSEE") or "").strip()
        if not insee.startswith("974"):           # GARDE 974 par code INSEE
            continue
        raw = {h: _j(v) for h, v in zip(header, row)}
        session.execute(text("""
            INSERT INTO sudocuh_procedures
              (insee, commune, du_opposable, du_en_cours, etat_detaille, prescription_proc,
               approbation_opp, region, dept, collectivite_porteuse, siren_epci, code_etat,
               id_du_opp, id_en_cours, code_bcsi, etat_commune, prescription_du_vigueur,
               executoire_du_vigueur, pop_mun, pop_tot, superficie_km2, raw, millesime_date, ingested_at)
            VALUES (:insee,:commune,:duo,:duc,:etd,:pproc,:appr,:region,:dept,:cp,:siren,:cetat,
               :idopp,:iden,:bcsi,:etcom,:presc_vig,:exec_vig,:popm,:popt,:superf,CAST(:raw AS jsonb),:mil,now())
            ON CONFLICT (insee) DO UPDATE SET
               commune=EXCLUDED.commune, du_opposable=EXCLUDED.du_opposable, du_en_cours=EXCLUDED.du_en_cours,
               etat_detaille=EXCLUDED.etat_detaille, prescription_proc=EXCLUDED.prescription_proc,
               approbation_opp=EXCLUDED.approbation_opp, region=EXCLUDED.region, dept=EXCLUDED.dept,
               collectivite_porteuse=EXCLUDED.collectivite_porteuse, siren_epci=EXCLUDED.siren_epci,
               code_etat=EXCLUDED.code_etat, id_du_opp=EXCLUDED.id_du_opp, id_en_cours=EXCLUDED.id_en_cours,
               code_bcsi=EXCLUDED.code_bcsi, etat_commune=EXCLUDED.etat_commune,
               prescription_du_vigueur=EXCLUDED.prescription_du_vigueur,
               executoire_du_vigueur=EXCLUDED.executoire_du_vigueur, pop_mun=EXCLUDED.pop_mun,
               pop_tot=EXCLUDED.pop_tot, superficie_km2=EXCLUDED.superficie_km2, raw=EXCLUDED.raw,
               millesime_date=EXCLUDED.millesime_date, ingested_at=now()"""),
            {"insee": insee, "commune": g(row, "Nom commune"), "duo": g(row, "DU_Opposable"),
             "duc": g(row, "DU_en_cours"), "etd": g(row, "Etat détaillé"),
             "pproc": _d(g(row, "Prescription proc en cours")),
             "appr": _d(g(row, "Approbation DU en vigueur")),
             "region": g(row, "Région"), "dept": g(row, "Dépt"),
             "cp": g(row, "Collectivite porteuse"), "siren": g(row, "SIREN EPCI"),
             "cetat": g(row, "Code Etat"), "idopp": g(row, "id DU opp"),
             "iden": g(row, "Id en cours"), "bcsi": g(row, "Code BCSI"),
             "etcom": g(row, "Etat Commune"),
             "presc_vig": _d(g(row, "Prescription DU en vigueur")),
             "exec_vig": _d(g(row, "Executoire DU en vigueur")),
             "popm": _i(g(row, "POP Mun")), "popt": _i(g(row, "POP Tot")),
             "superf": g(row, "Superficie INSEE (km²)"),
             "raw": json.dumps(raw, ensure_ascii=False), "mil": MILLESIME_DATE})
        n += 1
    session.flush()
    log(f"  Sudocuh : {n} communes 974 chargées ({len(header)} colonnes, millésime {MILLESIME_DATE})")
    return {"communes": n, "colonnes": len(header)}
