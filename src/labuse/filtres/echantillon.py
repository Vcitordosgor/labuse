"""CIRCUIT-3 lot 3 — L'ÉCHANTILLON VÉRIFIÉ CONTRE LE PRODUCTEUR.

Pour une source, un échantillon FIXE d'enregistrements dont la valeur attendue est **lue chez le
producteur** (fichier brut, API du producteur, page officielle) — JAMAIS dans nos tables. Stocké
dans `filtres/echantillons/<source>.json` avec l'origine de chaque attendu (URL, champ, date).

Le contrôle `echantillon` rejoue l'échantillon à chaque version : tout écart entre notre table et
l'attendu producteur = KO AVERTISSANT, avec les DEUX valeurs (la nôtre et celle du producteur).

Format du fichier :
    {
      "source": "cadastre_etalab",
      "producteur": "IGN — API Carto Cadastre",
      "table": "parcels", "cle_colonne": "idu", "lu_le": "2026-09-06",
      "lignes": [
        {"cle": "97415000BO0852", "colonne": "surface_m2", "attendu": 745,
         "tolerance_pct": 2.0,
         "origine": {"url": "https://apicarto.ign.fr/api/cadastre/parcelle?...",
                     "champ": "features[0].properties.contenance"}}
      ]
    }
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text

from .cadre import Controle, Filtre, Resultat, ko, ok, skip

_DIR = Path(__file__).resolve().parent / "echantillons"


def chemin(source: str) -> Path:
    return _DIR / f"{source}.json"


def charger(source: str) -> dict | None:
    p = chemin(source)
    if not p.exists():
        return None
    return json.loads(p.read_text())


def _compare(nous, attendu, tol_pct: float | None, tol_abs: float | None) -> bool:
    """VRAI si notre valeur == l'attendu producteur (numérique à tolérance près, sinon texte)."""
    if nous is None:
        return False
    # numérique ?
    try:
        a, b = float(nous), float(attendu)
        if tol_abs is not None and abs(a - b) <= tol_abs:
            return True
        if tol_pct is not None:
            return abs(a - b) <= abs(b) * tol_pct / 100.0
        return a == b
    except (TypeError, ValueError):
        return str(nous).strip().casefold() == str(attendu).strip().casefold()


def mesurer(db, f: Filtre, version: str) -> Resultat:
    doc = charger(f.source)
    if not doc or not doc.get("lignes"):
        return skip("aucun échantillon producteur pour cette source")
    table = doc.get("table") or f.table
    cle_col = doc.get("cle_colonne")
    if not (table and cle_col):
        return skip("échantillon sans table/clé")
    ecarts = []
    verifies = 0
    for ligne in doc["lignes"]:
        col = ligne["colonne"]
        try:
            nous = db.execute(text(
                f"SELECT {col} FROM {table} WHERE {cle_col} = :k LIMIT 1"),
                {"k": ligne["cle"]}).scalar()
        except Exception as exc:  # noqa: BLE001
            ecarts.append({"cle": ligne["cle"], "colonne": col, "erreur": str(exc)[:120]})
            continue
        verifies += 1
        if not _compare(nous, ligne["attendu"], ligne.get("tolerance_pct"),
                        ligne.get("tolerance_abs")):
            ecarts.append({"cle": ligne["cle"], "colonne": col,
                           "notre_valeur": None if nous is None else str(nous),
                           "attendu_producteur": ligne["attendu"],
                           "origine": ligne.get("origine")})
    d = {"producteur": doc.get("producteur"), "verifies": verifies,
         "ecarts": ecarts, "n_ecarts": len(ecarts), "lu_le": doc.get("lu_le")}
    return ok(f"{verifies - len(ecarts)}/{verifies} conformes", d) if not ecarts \
        else ko(f"{len(ecarts)} écart(s) / {verifies}", d)


def controle() -> Controle:
    """Le contrôle `echantillon` — un seul par filtre, chargé depuis le JSON de la source."""
    return Controle("d_echantillon", "echantillon", "avertissant",
                    "Échantillon vérifié contre le producteur",
                    "0 écart entre notre table et l'attendu producteur (lu chez le producteur)",
                    mesurer)
