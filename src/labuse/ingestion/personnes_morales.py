"""Propriétaires personnes morales (1.A) — fichier DGFiP « parcelles des personnes morales ».

Donnée PUBLIQUE (Licence Ouverte v2), millésime annuel. Une parcelle présente dans le fichier
appartient à une personne morale (commune, État, SEM, bailleur, SCI…) → owner_type + owner_name.
Une parcelle ABSENTE appartient à un particulier → aucune donnée perso (légal), bouton SPF.

Le fichier national est livré en ZIP par tranches de départements, un CSV `;` par département
(`PM_25_NB_974.csv` pour la Réunion). Le loader filtre la commune pilote (INSEE 97415), construit
l'IDU 14 caractères et classe via `proprietaire_type.classify_dgfip`. Idempotent (upsert par idu).
"""
from __future__ import annotations

import csv
import io
import zipfile
from pathlib import Path

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from .. import constants
from ..config import get_settings

SOURCE = "DGFiP — parcelles des personnes morales"
URL_ZIP_2025 = ("https://data.economie.gouv.fr/api/v2/catalog/datasets/"
                "fichiers-des-locaux-et-des-parcelles-des-personnes-morales/attachments/"
                "fichier_des_parcelles_situation_2025_dpts_57_a_976_zip")

# Positions (1-indexées) dans le CSV DGFiP (24 colonnes, délimiteur ';', avec entête).
_COL = {"dep": 0, "commune": 2, "prefixe": 4, "section": 5, "nplan": 6,
        "siren": 19, "groupe": 20, "forme": 22, "denomination": 23}


def _build_idu(insee: str, prefixe: str, section: str, nplan: str) -> str | None:
    section = (section or "").strip()
    nplan = (nplan or "").strip()
    if not section or not nplan:
        return None
    pref = (prefixe or "").strip() or "000"
    return f"{insee}{pref.zfill(3)}{section.zfill(2)}{nplan.zfill(4)}"


def _rows_from_csv(path: Path, code_commune: str):
    """Itère les lignes de la commune (dé-doublonnées par parcelle). Encodage tolérant."""
    raw = path.read_bytes()
    for enc in ("utf-8-sig", "latin-1"):
        try:
            txt = raw.decode(enc)
            break
        except UnicodeDecodeError:
            continue
    else:
        txt = raw.decode("latin-1", errors="replace")
    seen: set[str] = set()
    reader = csv.reader(io.StringIO(txt), delimiter=";")
    next(reader, None)  # entête
    for r in reader:
        if len(r) <= _COL["denomination"] or r[_COL["commune"]].strip() != code_commune:
            continue
        idu = _build_idu("97" + code_commune, r[_COL["prefixe"]], r[_COL["section"]], r[_COL["nplan"]])
        if not idu or idu in seen:
            continue
        seen.add(idu)
        groupe_raw = (r[_COL["groupe"]] or "").strip()
        groupe = int(groupe_raw[0]) if groupe_raw[:1].isdigit() else None
        groupe_label = groupe_raw.split(" - ", 1)[-1].strip() if " - " in groupe_raw else groupe_raw
        yield {"idu": idu, "groupe": groupe, "groupe_label": groupe_label[:80],
               "forme": (r[_COL["forme"]] or "").strip()[:20],
               "denomination": (r[_COL["denomination"]] or "").strip()[:200],
               "siren": (r[_COL["siren"]] or "").strip()[:20]}


def ingest_personnes_morales(session: Session, csv_path: str | Path,
                             insee: str | None = None, millesime: str = "2025",
                             url_source: str = URL_ZIP_2025) -> int:
    """Charge le fichier DGFiP (CSV départemental déjà extrait) pour la commune pilote. Upsert
    par idu ; remplace le millésime précédent de chaque parcelle. Retourne le nombre de parcelles."""
    insee = insee or get_settings().pilot_commune_insee
    code_commune = insee[2:]  # 97415 -> 415
    n = 0
    for row in _rows_from_csv(Path(csv_path), code_commune):
        session.execute(text(
            """INSERT INTO parcelle_personne_morale
                 (idu, groupe, groupe_label, forme_juridique, denomination, siren,
                  millesime, source, url_source, date_import)
               VALUES (:idu,:g,:gl,:f,:d,:s,:m,:src,:url, now())
               ON CONFLICT (idu) DO UPDATE SET
                 groupe=EXCLUDED.groupe, groupe_label=EXCLUDED.groupe_label,
                 forme_juridique=EXCLUDED.forme_juridique, denomination=EXCLUDED.denomination,
                 siren=EXCLUDED.siren, millesime=EXCLUDED.millesime, date_import=now()"""),
            {"idu": row["idu"], "g": row["groupe"], "gl": row["groupe_label"],
             "f": row["forme"], "d": row["denomination"], "s": row["siren"],
             "m": millesime, "src": SOURCE, "url": url_source})
        n += 1
    session.flush()
    return n


def fetch_974_csv(dest_dir: str | Path = "/tmp/dgfip_pm") -> Path:
    """Télécharge le ZIP DGFiP (retry) et extrait le CSV départemental 974 (cache si déjà là)."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    csv_path = dest / "PM_25_NB_974.csv"
    if csv_path.exists() and csv_path.stat().st_size > 0:
        return csv_path
    last = None
    for attempt in range(4):
        try:
            with httpx.Client(timeout=600.0, follow_redirects=True,
                              headers={"User-Agent": constants.USER_AGENT}) as c:
                r = c.get(URL_ZIP_2025)
                r.raise_for_status()
                zf = zipfile.ZipFile(io.BytesIO(r.content))
                name = next(n for n in zf.namelist() if n.endswith("PM_25_NB_974.csv"))
                csv_path.write_bytes(zf.read(name))
            return csv_path
        except Exception as exc:  # noqa: BLE001
            last = exc
    raise RuntimeError(f"Téléchargement DGFiP échoué : {last}")
