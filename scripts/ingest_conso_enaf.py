#!/usr/bin/env python3
"""Importe les séries communales Cerema de La Réunion du 1er janvier 2011 au 1er janvier 2025."""
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import tempfile
import urllib.request
from pathlib import Path

import psycopg
from psycopg import sql

URL = (
    "https://static.data.gouv.fr/resources/consommation-despaces-naturels-agricoles-et-"
    "forestiers-du-1er-janvier-2011-au-1er-janvier-2025/20260724-142953/conso-com-974.gpkg"
)
MILLESIME = "ENAF du 01/01/2011 au 01/01/2025 · Cerema 974, révision du 24/07/2026"
PRECEDENT = "consommation ENAF 2009-2024 · publié 12/05/2025 · Licence Ouverte 2.0"
SOURCE_NOM = ("Portail national de l'artificialisation / Cerema — Fichiers fonciers "
              "(CONSOENAF, indicateurs communaux)")
FENETRES = ((11,21), (21,24), (21,25), (24,25))


def lire_geopackage(path: Path) -> list[dict]:
    resultats = []
    with sqlite3.connect(path.resolve().as_uri() + "?mode=ro", uri=True) as source:
        source.row_factory = sqlite3.Row
        for ligne in source.execute("SELECT * FROM conso_com_974 ORDER BY idcom"):
            commune = {"insee": ligne["idcom"], "commune": ligne["idcomtxt"]}
            for type_flux, motif in (("conso", "naf{}art{}"), ("hab", "art{}hab{}")):
                annuel = {annee: ligne[motif.format(annee, annee + 1)] for annee in range(11,25)}
                if any(v is None or v < 0 or v != int(v) for v in annuel.values()):
                    raise ValueError(f"Flux annuel invalide pour {commune['insee']}")
                for debut, fin in FENETRES:
                    somme = sum(annuel[y] for y in range(debut,fin))
                    officiel = motif.format(debut, fin)
                    if officiel in ligne.keys() and ligne[officiel] != somme:
                        raise ValueError(f"Agrégat Cerema discordant pour {commune['insee']} et {officiel}")
                    commune[f"{type_flux}_20{debut}_20{fin}_m2"] = int(somme)
            commune.update(source_nom=SOURCE_NOM, source_url=URL, millesime=MILLESIME)
            resultats.append(commune)
    if [r["insee"] for r in resultats] != [f"974{i:02d}" for i in range(1,25)]:
        raise ValueError("Le fichier ne comporte pas exactement les 24 communes de La Réunion")
    return resultats


def charger(chemin: Path | None) -> list[dict]:
    if chemin is not None:
        return lire_geopackage(chemin)
    with tempfile.TemporaryDirectory() as temp:
        path = Path(temp) / "conso-com-974.gpkg"
        with urllib.request.urlopen(URL, timeout=90) as distant, path.open("wb") as fichier:
            shutil.copyfileobj(distant, fichier)
        return lire_geopackage(path)


def main() -> int:
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--fichier", type=Path, help="GeoPackage Cerema officiel déjà téléchargé")
    args.add_argument("--verifier", action="store_true", help="Vérifie les 24 communes et les fenêtres sans écriture")
    params = args.parse_args()
    lignes = charger(params.fichier)
    if params.verifier:
        print(f"{len(lignes)} communes, {sum(r['conso_2024_2025_m2'] for r in lignes)} m² en 2024–2025")
        return 0
    champs = list(lignes[0])
    chiffres = [c for c in champs if c.endswith("_m2")]
    ds = os.environ.get("DATABASE_URL") or os.environ.get("LABUSE_DATABASE_URL") or "postgresql://openclaw@127.0.0.1:5432/labuse"
    with psycopg.connect(ds.replace("postgresql+psycopg://","postgresql://",1)) as conn, conn.cursor() as cur:
        cur.execute("""CREATE TABLE IF NOT EXISTS commune_conso_enaf (
            insee varchar(5) PRIMARY KEY, commune varchar(80) NOT NULL,
            source_nom text, source_url text, millesime text, importe_le timestamptz DEFAULT now())""")
        for c in chiffres:
            cur.execute(sql.SQL("ALTER TABLE commune_conso_enaf ADD COLUMN IF NOT EXISTS {} double precision").format(sql.Identifier(c)))
        cur.execute("SELECT DISTINCT millesime FROM commune_conso_enaf WHERE insee LIKE '974%'")
        if any(v not in (None, PRECEDENT, MILLESIME) for (v,) in cur):
            raise ValueError("Une autre édition est déjà présente. Comparer ses dates à cette livraison Cerema.")
        valeurs = [c for c in champs if c not in ("insee","commune")]
        ins = sql.SQL(", ").join(map(sql.Identifier,champs))
        cols = sql.SQL(", ").join(map(sql.Identifier,valeurs))
        news = sql.SQL(", ").join(sql.Identifier("excluded",c) for c in valeurs)
        cur.executemany(sql.SQL("""INSERT INTO commune_conso_enaf AS t ({}) VALUES ({})
            ON CONFLICT(insee) DO UPDATE SET ({}) = ({}), importe_le=now()
            WHERE ({}) IS DISTINCT FROM ({})""").format(ins,sql.SQL(", ").join(map(sql.Placeholder,champs)),
            cols,news,sql.SQL(", ").join(sql.Identifier("t",c) for c in valeurs),news),lignes)
    print(f"{len(lignes)} communes vérifiées. {MILLESIME}.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
