"""CHASSE-1 angle 3 — matrice de couverture source × commune (lecture seule).

    python -m scripts.chasse.couverture   # → docs/audit-2026-10/CHASSE-1/COUVERTURE.csv

Pour chaque source servie, le nombre d'objets par commune. Une cellule à 0 est une
ABSENCE : l'angle 3 vérifie alors ce que disent les lecteurs (« aucun » = TROMPEUR si la
source n'est simplement pas ingérée là). Format long : source;commune;n — plus un
récapitulatif des communes à 0 par source en fin de fichier console.
"""
from __future__ import annotations

import csv
import pathlib

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-1" / "COUVERTURE.csv"
DSN = "postgresql://openclaw@localhost:5432/labuse"

# sources table → (expression commune/insee, libellé)
TABLES = [
    ("dvf_mutations_parcelle", "code_commune", "DVF (mutations rattachées)"),
    ("dvf_mutations", "commune", "DVF (mutations brutes)"),
    ("batiment_hauteur_lidar", "left(idu,5)", "LiDAR hauteurs bâtiment"),
    ("adresse_parcelles", "left(idu,5)", "BAN adresses↔parcelles"),
    ("pc_caducs", "left(idu,5)", "Permis caducs"),
    ("sitadel_permits", "commune", "Sitadel permis"),
    ("catnat_arretes", "insee", "CatNat arrêtés"),
    ("dpe_records", "code_insee", "DPE"),
    ("rnb_batiments", "insee", "RNB bâtiments"),
    ("sirene_etablissements", "insee", "SIRENE établissements"),
    ("rnic_coproprietes", "insee", "RNIC copropriétés"),
    ("parcelle_personne_morale", "left(idu,5)", "Propriétaires PM (DGFiP)"),
    ("commune_rei", "insee", "REI fiscalité"),
    ("population_legale", "insee", "Population légale"),
    ("parcel_terrain", "left(idu,5)", "Pentes (RGE Alti)"),
    ("parcel_zone_plu", "left(idu,5)", "Zonage PLU rattaché"),
    ("filosofi_carreaux_200m", None, "Filosofi (carreaux, pas de commune)"),
]

SQL_KINDS = """
SELECT kind, coalesce(cr.insee, sl.commune, '??') AS insee, count(*)
FROM spatial_layers sl
LEFT JOIN communes_referentiel cr ON cr.nom = sl.commune OR cr.insee = sl.commune
GROUP BY 1, 2
"""


def main() -> None:
    conn = psycopg.connect(DSN, options="-c statement_timeout=300000")
    cur = conn.cursor()
    cur.execute("SELECT insee, nom FROM communes_referentiel ORDER BY insee")
    communes = dict(cur.fetchall())  # insee → nom (24)
    lignes = []

    def emettre(source, par_insee: dict):
        for insee, nom in communes.items():
            lignes.append({"source": source, "insee": insee, "commune": nom,
                           "n": par_insee.get(insee, 0)})
        hors = {k: v for k, v in par_insee.items() if k not in communes and k}
        if hors:
            lignes.append({"source": source, "insee": "HORS_REF", "commune": "",
                           "n": sum(hors.values())})

    for table, expr, lib in TABLES:
        if expr is None:
            cur.execute(f"SELECT count(*) FROM {table}")
            lignes.append({"source": lib, "insee": "ILE", "commune": "(non communal)",
                           "n": cur.fetchone()[0]})
            continue
        cur.execute(f"SELECT {expr}, count(*) FROM {table} GROUP BY 1")
        emettre(lib, {str(k or ""): v for k, v in cur.fetchall()})

    # couches spatiales : un bloc par kind (commune de la couche quand posée)
    cur.execute(SQL_KINDS)
    par_kind: dict[str, dict] = {}
    for kind, insee, n in cur.fetchall():
        par_kind.setdefault(kind, {})[str(insee)] = \
            par_kind.setdefault(kind, {}).get(str(insee), 0) + n
    for kind in sorted(par_kind):
        d = par_kind[kind]
        sans = d.pop("??", 0)
        emettre(f"couche:{kind}", d)
        if sans:
            lignes.append({"source": f"couche:{kind}", "insee": "SANS_COMMUNE",
                           "commune": "(couche non communale)", "n": sans})

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["source", "insee", "commune", "n"])
        w.writeheader()
        w.writerows(lignes)

    # récapitulatif : les trous (communes à 0) par source — la matière de l'angle 3
    print(f"{len(lignes)} lignes → {SORTIE}\n— trous (communes à 0) —")
    from collections import defaultdict
    trous = defaultdict(list)
    for l in lignes:
        if l["n"] == 0 and l["insee"] in communes:
            trous[l["source"]].append(l["commune"])
    for src in sorted(trous):
        cs = trous[src]
        print(f"  {src}: {len(cs)} communes à 0 → {', '.join(cs[:6])}{'…' if len(cs) > 6 else ''}")
    conn.close()


if __name__ == "__main__":
    main()
