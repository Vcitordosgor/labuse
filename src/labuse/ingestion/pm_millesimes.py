"""Panel POINT-IN-TIME des propriétaires personnes morales (mandat M2, 12/07/2026).

Millésimes annuels DGFiP « fichier des parcelles des personnes morales » (Licence Ouverte
v2, data.economie.gouv), chacun à la SITUATION DU 1ᵉʳ JANVIER de son année. Ce module
peuple `pm_proprietaires_millesimes` (clé millesime + idu) pour le département 974 ENTIER —
la table de prod `parcelle_personne_morale` (situation 2025) et le moteur V restent
strictement INTACTS : aucun flux existant modifié.

Usage v2 (bloc O) : features propriétaire datées à t — train ≤ 2023 / val 2024 (le test
2025 est déjà vendeur-certain par construction via la table courante).

Idempotent : DELETE du millésime puis ré-insertion (relançable à volonté).
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

SOURCE = "DGFiP — parcelles des personnes morales (millésimes)"
_BASE = ("https://data.economie.gouv.fr/api/v2/catalog/datasets/"
         "fichiers-des-locaux-et-des-parcelles-des-personnes-morales/attachments/")

#: attachment data.economie par millésime (reconnaissance M2 lot 1 — ids RÉELS du catalogue,
#: graphies irrégulières comprises : « dept_61 » en 2021, « fichiers_ » pluriel en 2024).
MILLESIME_ATTACHMENTS = {
    2021: "fichier_des_parcelles_situation_2021_dept_61_a_976_zip",
    2022: "fichier_des_parcelles_situation_2022_dept_62_a_976_zip",
    2023: "fichier_des_parcelles_situation_2023_dept_62_a_976_zip",
    2024: "fichiers_des_parcelles_situation_2024_dpts_61_a_976_zip",
}

#: positions attendues (mêmes 24 colonnes que la situation 2025 — vérifié par _sniff_header,
#: tout écart de schéma est LEVÉ, jamais deviné : « ne pas bricoler de substitut »).
#: Diffs CONSTATÉS entre millésimes (lot 1, documentés au rapport) — positions IDENTIQUES :
#:  · 2021-2023 : membre .txt, latin-1, entête QUOTÉE ; Département = '97' + Code Direction
#:    = '4' (le « 974 » est éclaté sur deux colonnes) ; groupe = code nu ('1', sans libellé).
#:  · 2024 (et 2025 prod) : membre .csv, Département = '974', groupe parfois libellé.
_COL = {"dep": 0, "direction": 1, "commune": 2, "prefixe": 4, "section": 5, "nplan": 6,
        "siren": 19, "groupe": 20, "forme": 22, "denomination": 23}
_NB_COLONNES_ATTENDU = 24


def _est_974(r: list[str]) -> bool:
    dep = (r[_COL["dep"]] or "").strip()
    return dep == "974" or (dep == "97" and (r[_COL["direction"]] or "").strip() == "4")


def url_millesime(annee: int) -> str:
    return _BASE + MILLESIME_ATTACHMENTS[annee]


def fetch_974_csv(annee: int, dest_dir: str | Path = "/tmp/dgfip_pm_millesimes") -> Path:
    """Télécharge le ZIP du millésime (cache disque) et extrait le CSV 974."""
    dest = Path(dest_dir)
    dest.mkdir(parents=True, exist_ok=True)
    zip_path = dest / f"{MILLESIME_ATTACHMENTS[annee]}.zip"
    csv_path = dest / f"PM_{annee}_974.csv"
    if csv_path.exists() and csv_path.stat().st_size > 0:
        return csv_path
    if not (zip_path.exists() and zip_path.stat().st_size > 0):
        with httpx.Client(timeout=1800.0, follow_redirects=True,
                          headers={"User-Agent": constants.USER_AGENT}) as c, \
             zip_path.open("wb") as f:
            with c.stream("GET", url_millesime(annee)) as r:
                r.raise_for_status()
                for chunk in r.iter_bytes():
                    f.write(chunk)
    zf = zipfile.ZipFile(zip_path)
    # graphies DGFiP irrégulières : PM_21_NB_974.txt (2021-2023) vs PM_24_NB_974.csv (2024)
    membre = next((n for n in zf.namelist()
                   if "974" in n and n.lower().endswith((".csv", ".txt"))), None)
    if membre is None:
        raise RuntimeError(f"millésime {annee} : aucun CSV 974 dans le ZIP "
                           f"({len(zf.namelist())} membres, ex. {zf.namelist()[:3]})")
    csv_path.write_bytes(zf.read(membre))
    return csv_path


def _decode(raw: bytes) -> str:
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("latin-1", errors="replace")


def _sniff_header(txt: str, annee: int) -> list[str]:
    """Entête du millésime — le nombre de colonnes DOIT correspondre au schéma 2025 connu.
    Un écart = erreur explicite documentée au rapport, jamais un mapping deviné."""
    header = next(csv.reader(io.StringIO(txt), delimiter=";"))
    if len(header) != _NB_COLONNES_ATTENDU:
        raise RuntimeError(
            f"millésime {annee} : {len(header)} colonnes (≠ {_NB_COLONNES_ATTENDU} attendues) — "
            f"schéma divergent, à documenter avant ingestion. Entête : {header}")
    return header


def _build_idu(insee: str, prefixe: str, section: str, nplan: str) -> str | None:
    section = (section or "").strip()
    nplan = (nplan or "").strip()
    if not section or not nplan:
        return None
    pref = (prefixe or "").strip() or "000"
    return f"{insee}{pref.zfill(3)}{section.zfill(2)}{nplan.zfill(4)}"


def ingest_millesime(session: Session, annee: int, csv_path: str | Path,
                     log=print) -> dict:
    """Ingestion 974 ENTIER d'un millésime → pm_proprietaires_millesimes (idempotent :
    le millésime est purgé puis réinséré). Dédup par idu (première ligne gagne — même
    convention que le loader 2025). Retourne {lignes_csv, parcelles, entete}."""
    txt = _decode(Path(csv_path).read_bytes())
    header = _sniff_header(txt, annee)
    session.execute(text("DELETE FROM pm_proprietaires_millesimes WHERE millesime = :m"),
                    {"m": annee})
    reader = csv.reader(io.StringIO(txt), delimiter=";")
    next(reader, None)
    seen: set[str] = set()
    batch: list[dict] = []
    n_lignes = 0

    def flush():
        if batch:
            session.execute(text(
                """INSERT INTO pm_proprietaires_millesimes
                     (millesime, idu, groupe, groupe_label, forme_juridique, denomination,
                      siren, url_source)
                   VALUES (:m, :idu, :g, :gl, :f, :d, :s, :url)"""), batch)
            batch.clear()

    for r in reader:
        if len(r) <= _COL["denomination"] or not _est_974(r):
            continue
        n_lignes += 1
        insee = "97" + (r[_COL["commune"]] or "").strip()
        idu = _build_idu(insee, r[_COL["prefixe"]], r[_COL["section"]], r[_COL["nplan"]])
        if not idu or idu in seen:
            continue
        seen.add(idu)
        groupe_raw = (r[_COL["groupe"]] or "").strip()
        groupe = int(groupe_raw[0]) if groupe_raw[:1].isdigit() else None
        groupe_label = groupe_raw.split(" - ", 1)[-1].strip() if " - " in groupe_raw else groupe_raw
        batch.append({"m": annee, "idu": idu, "g": groupe, "gl": groupe_label[:80],
                      "f": (r[_COL["forme"]] or "").strip()[:20],
                      "d": (r[_COL["denomination"]] or "").strip()[:200],
                      "s": (r[_COL["siren"]] or "").strip()[:20],
                      "url": url_millesime(annee)})
        if len(batch) >= 5000:
            flush()
    flush()
    session.commit()
    log(f"millésime {annee} : {n_lignes} lignes 974 → {len(seen)} parcelles distinctes")
    return {"annee": annee, "lignes_csv": n_lignes, "parcelles": len(seen), "entete": header}
