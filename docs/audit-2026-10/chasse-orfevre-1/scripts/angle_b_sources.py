#!/usr/bin/env python3
"""CHASSE-ORFEVRE-1 — Angle B : chaque source de bout en bout (LECTURE SEULE).

Quatre contrôles par source servie :
  B1  volume chargé vs annoncé (producteur et/ou millésime déclaré dans data_sources)
  B2  couverture commune par commune (24 INSEE 97401-97424)
  B3  fantômes (lignes plus récentes que le dernier chargement / millésime retiré)
  B4  poids mort (colonnes 100 % NULL ; colonnes jamais lues par le code — grep)

Usage :
  LABUSE_DATABASE_URL=... python angle_b_sources.py            # base seule
  LABUSE_DATABASE_URL=... python angle_b_sources.py --en-ligne # + GET producteurs (doux)

Aucune écriture : rôle read-only, requêtes SELECT uniquement, statement_timeout 60 s.
"""
from __future__ import annotations

import json
import os
import re
import subprocess
import sys
import urllib.request

try:
    import psycopg
except ImportError:  # venv du repo principal
    sys.exit("psycopg manquant — utiliser ~/Desktop/labuse/.venv/bin/python")

EN_LIGNE = "--en-ligne" in sys.argv
REPO = os.path.expanduser("~/Desktop/labuse-orfevre")
DSN = os.environ.get("LABUSE_DATABASE_URL", "").replace("postgresql+psycopg://", "postgresql://")
if not DSN:
    # repli : lire le .env du worktree
    envp = os.path.join(REPO, ".env")
    if os.path.exists(envp):
        for line in open(envp):
            if line.startswith("LABUSE_DATABASE_URL="):
                DSN = line.split("=", 1)[1].strip().replace("postgresql+psycopg://", "postgresql://")
if not DSN:
    sys.exit("LABUSE_DATABASE_URL absent")

CONN = psycopg.connect(DSN)
CONN.execute("SET statement_timeout = '60s'")
CONN.execute("SET default_transaction_read_only = on")

INSEE_24 = [f"974{i:02d}" for i in range(1, 25)]


def q(sql, params=None):
    with CONN.cursor() as cur:
        cur.execute(sql, params or ())
        return cur.fetchall()


def one(sql, params=None):
    return q(sql, params)[0][0]


def _ssl_ctx():
    import ssl
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except Exception:
        # dernier recours (open data public, lecture seule) : pas de vérification
        c = ssl.create_default_context()
        c.check_hostname = False
        c.verify_mode = ssl.CERT_NONE
        return c


SSL_CTX = None


def get_bytes(url, timeout=60):
    global SSL_CTX
    if SSL_CTX is None:
        SSL_CTX = _ssl_ctx()
    req = urllib.request.Request(url, headers={"User-Agent": "labuse-audit-orfevre/1 (lecture seule)"})
    with urllib.request.urlopen(req, timeout=timeout, context=SSL_CTX) as r:
        return r.read()


def get_json(url, timeout=30):
    return json.loads(get_bytes(url, timeout).decode("utf-8"))


# ──────────────────────────────────────────────────────────────────────────────
# Inventaire : table → (clé commune SQL, libellé source)
# ──────────────────────────────────────────────────────────────────────────────
TABLES = {
    # table                  (expression INSEE, source)
    "parcels":                ("substr(idu,1,5)", "Cadastre PCI/Etalab", "cadastre_disparue_le IS NULL"),
    "dvf_mutations_parcelle": ("code_commune", "DVF géo Etalab 2021-2025", None),
    "dvf_mutations_histo":    ("code_commune", "DVF archives DGFiP 2014-2020", None),
    "sirene_etablissements":  ("insee", "SIRENE géolocalisé INSEE", None),
    "sitadel_permits":        (None, "Sitadel (DIDO/SDES)", None),  # commune = nom → mappée via referentiel
    "rnb_batiments":          ("insee", "RNB", None),
    "adresses":               ("insee", "BAN", None),
    "dpe_records":            ("code_insee", "DPE ADEME", None),
    "piscines":               (None, "Piscines (détection ortho/CoSIA)", None),  # commune = nom
    "batiment_hauteur_lidar": ("substr(idu,1,5)", "LiDAR HD MNH (IGN)", None),
    "parcel_zone_plu":        ("substr(idu,1,5)", "GPU/PLU (API Carto)", None),
    "plu_reglement_extrait":  ("insee", "Règlements PLU (verbatims)", None),
    "catnat_arretes":         ("insee", "GASPAR CatNat (Géorisques)", None),
    "parcelle_personne_morale": ("substr(idu,1,5)", "DGFiP parcelles PM", None),
    "dfi_filiation":          ("insee", "DFI DGFiP", None),
    "arcep_immeubles":        ("insee", "Fibre Arcep", None),
    "ban_plus_liens":         ("substr(idu,1,5)", "BAN PLUS (IGN)", None),
    "adresse_parcelles":      (None, "BAN ↔ parcelle (croisement)", None),
    "rpls_commune":           ("insee", "RPLS (SDES)", None),
    "bodacc_depots":          (None, "BODACC (DILA)", None),
    "rnic_coproprietes":      (None, "RNIC (Anah)", None),
}


def b0_inventaire():
    print("\n════ B0 · INVENTAIRE data_sources ════")
    for st, n in q("SELECT status, count(*) FROM data_sources GROUP BY 1 ORDER BY 2 DESC"):
        print(f"  {st:<20} {n}")
    print("  millésimes auto-déclarés portant un compte :")
    for name, mil in q("SELECT name, source_millesime FROM data_sources WHERE source_millesime ~ '[0-9]{3,} '"):
        print(f"    - {name}: {mil}")


def b1_volumes():
    print("\n════ B1 · VOLUMES chargés ════")
    for t in TABLES:
        n = one(f"SELECT count(*) FROM {t}")
        print(f"  {t:<26} {n:>9}")
    # cas particuliers
    print("  parcels vivantes          ",
          one("SELECT count(*) FROM parcels WHERE cadastre_disparue_le IS NULL"))
    print("  spatial_layers znieff/ppr/qpv/bruit :",
          q("SELECT kind, count(*) FROM spatial_layers WHERE kind IN ('znieff','ppr','qpv','bruit_route','bruit_carte','trait_de_cote','peb') GROUP BY 1 ORDER BY 1"))
    # auto-déclarés chiffrés dans data_sources vs base
    paires = [
        ("arcep_immeubles", r"(\d[\d\s]{4,})\s*immeubles", "Fibre Arcep"),
        ("dfi_filiation", r"(\d[\d\s]{4,})\s*liens", "DFI"),
        ("rnic_coproprietes", r"\((\d[\d\s]{2,})\s*copros", "RNIC"),
    ]
    for t, rx, lib in paires:
        mil = one("SELECT source_millesime FROM data_sources WHERE source_millesime ~ %s LIMIT 1", (rx,))
        m = re.search(rx, mil or "")
        annonce = int(re.sub(r"\s", "", m.group(1))) if m else None
        base = one(f"SELECT count(*) FROM {t}")
        print(f"  {lib}: base={base} annoncé(data_sources)={annonce} "
              f"{'OK' if annonce and abs(base-annonce)/annonce < 0.02 else 'ÉCART' if annonce else '?'}")


def b2_couverture():
    print("\n════ B2 · COUVERTURE 24 communes ════")
    parc = dict(q("SELECT substr(idu,1,5), count(*) FROM parcels WHERE cadastre_disparue_le IS NULL GROUP BY 1"))
    pop = dict(q("SELECT insee, population FROM communes_referentiel")) if q(
        "SELECT 1 FROM information_schema.columns WHERE table_name='communes_referentiel' AND column_name='population'") else {}
    cibles = {t: v for t, v in TABLES.items() if v[0]}
    mats = {}
    for t, (expr, lib, extra) in cibles.items():
        where = f" WHERE {extra}" if extra else ""
        mats[t] = dict(q(f"SELECT {expr}, count(*) FROM {t}{where} GROUP BY 1"))
    # tables à commune en toutes lettres → mapping par nom
    noms = dict(q("SELECT nom, insee FROM communes_referentiel")) if q(
        "SELECT 1 FROM information_schema.columns WHERE table_name='communes_referentiel' AND column_name='nom'") else {}
    hdr = ["insee", "parcels"] + [t[:14] for t in cibles if t != "parcels"]
    print("  " + " | ".join(hdr))
    suspects = []
    for ins in INSEE_24:
        row = [ins, str(parc.get(ins, 0))]
        for t in cibles:
            if t == "parcels":
                continue
            n = mats[t].get(ins, 0)
            row.append(str(n))
            if n == 0:
                suspects.append((t, ins, 0))
        print("  " + " | ".join(row))
    # hors-24 ?
    for t, (expr, lib, extra) in cibles.items():
        hors = sum(n for k, n in mats[t].items() if k not in INSEE_24)
        if hors:
            print(f"  ⚠ {t}: {hors} lignes à code commune hors 24 ({[k for k in mats[t] if k not in INSEE_24][:5]})")
    if suspects:
        print("  Communes à ZÉRO :", suspects)


def b3_fantomes():
    print("\n════ B3 · FANTÔMES (dates / millésimes) ════")
    checks = [
        ("dvf_mutations_parcelle", "date_mutation > date '2025-12-31'", "mutations après le millésime 2021-2025"),
        ("dvf_mutations_histo", "date_mutation > date '2020-12-31' OR date_mutation < date '2014-01-01'",
         "archives hors fenêtre 2014-2020"),
        ("dvf_mutations", "date_mutation > current_date", "mutations futures"),
        ("sitadel_permits", "date > current_date OR date_depot > current_date", "permis futurs"),
        ("sirene_etablissements", "date_creation > current_date", "créations futures"),
        ("dpe_records", "date_etablissement > current_date", "DPE futurs"),
        ("catnat_arretes", "date_arrete > current_date", "arrêtés futurs"),
        ("rnb_batiments", "NOT is_active", "bâtiments RNB inactifs conservés"),
        ("sirene_etablissements", "NOT actif", "établissements fermés conservés"),
        ("parcelle_personne_morale", "millesime::int NOT BETWEEN 2019 AND 2025", "millésime PM hors panel"),
        ("pm_proprietaires_millesimes", "millesime::int NOT BETWEEN 2019 AND 2024", "millésime panel PM hors fenêtre"),
        ("dvf_mutations", "mutation_id IS NULL OR raw IS NULL", "mutations sans identifiant producteur (inventées)"),
        ("dvf_mutations_histo", "EXISTS (SELECT 1 FROM dvf_mutations_parcelle p WHERE p.id_mutation = dvf_mutations_histo.id_mutation)",
         "recouvrement histo/actuel (doublon de millésime)"),
        ("piscines", "statut='disparue'" , "piscines marquées disparues (fantômes volontaires ?)"),
    ]
    for t, cond, lib in checks:
        try:
            n = one(f"SELECT count(*) FROM {t} WHERE {cond}")
            print(f"  {t:<26} {lib:<55} {n}")
        except Exception as e:  # colonne absente etc.
            CONN.rollback()
            print(f"  {t:<26} {lib:<55} ERREUR {type(e).__name__}")
    # parcelles disparues encore référencées par des satellites servis
    for sat, col in [("dvf_mutations_parcelle", "id_parcelle"), ("adresses", "idu"),
                     ("dpe_records", "parcelle_idu")]:
        n = one(f"SELECT count(*) FROM {sat} s JOIN parcels p ON p.idu = s.{col} "
                "WHERE p.cadastre_disparue_le IS NOT NULL")
        print(f"  {sat:<26} lignes pointant une parcelle DISPARUE{'':<20} {n}")


def b4_poids_mort():
    """Deux poids morts : colonnes 100 % NULL ; colonnes jamais lues HORS écrivains
    (models.py, ingestion/, connectors/ = déclaration + chargement, pas une lecture)."""
    print("\n════ B4 · POIDS MORT ════")
    grep_dirs = [os.path.join(REPO, "src", "labuse"), os.path.join(REPO, "frontend", "src")]
    MENAGE = {"geom_2975", "ingested_at", "created_at", "updated_at", "refreshed_at",
              "ingere_le", "built_at", "maj_at", "date_import", "fetched_at", "computed_at"}

    def lu_hors_ecrivains(col):
        if len(col) <= 3 or col in MENAGE:  # trop générique / colonne de ménage
            return True
        for d in grep_dirs:
            r = subprocess.run(["grep", "-rlw", col, d], capture_output=True, text=True)
            hits = [p for p in r.stdout.splitlines()
                    if not (p.endswith("src/labuse/models.py")
                            or "/src/labuse/ingestion/" in p or "/src/labuse/connectors/" in p)]
            if hits:
                return True
        return False

    for t in TABLES:
        cols = [c for (c,) in q(
            "SELECT column_name FROM information_schema.columns WHERE table_schema='public' "
            "AND table_name=%s ORDER BY ordinal_position", (t,))]
        if not cols:
            continue
        counts = q(f"SELECT {', '.join(f'count({c})' for c in cols)} FROM {t}")[0]
        total = one(f"SELECT count(*) FROM {t}")
        vides = [c for c, n in zip(cols, counts) if total and n == 0]
        non_lues = [c for c in cols if not lu_hors_ecrivains(c)]
        if vides or non_lues:
            print(f"  {t}: 100%NULL={vides or '-'} | jamais lues hors écrivains={non_lues or '-'}")


def b5_en_ligne():
    if not EN_LIGNE:
        print("\n(producteurs en ligne non interrogés — relancer avec --en-ligne)")
        return
    import csv
    import gzip
    import io
    import time

    print("\n════ B5 · PRODUCTEURS EN LIGNE (GET légers, ~1 req/s) ════")
    # 1) Cadastre : API Carto totalFeatures par commune (24 GET)
    try:
        base = dict(q("SELECT substr(idu,1,5), count(*) FROM parcels WHERE cadastre_disparue_le IS NULL GROUP BY 1"))
        print("  Cadastre API Carto (totalFeatures) vs base (vivantes) :")
        tot_p = tot_b = 0
        for ins in INSEE_24:
            j = get_json(f"https://apicarto.ign.fr/api/cadastre/parcelle?code_insee={ins}&_limit=1")
            tf = j.get("totalFeatures")
            tot_p += tf or 0
            tot_b += base.get(ins, 0)
            print(f"    {ins}: producteur={tf} base={base.get(ins,0)} écart={None if tf is None else tf - base.get(ins,0)}")
            time.sleep(0.8)
        print(f"    TOTAL producteur={tot_p} base={tot_b} écart={tot_p - tot_b}")
    except Exception as e:
        print(f"  cadastre: ERREUR {e}")
    # 2) GASPAR CatNat par commune (24 GET)
    try:
        cat = dict(q("SELECT insee, count(*) FROM catnat_arretes GROUP BY 1"))
        print("  GASPAR CatNat (api georisques v1) vs base :")
        tot_p = 0
        for ins in INSEE_24:
            j = get_json(f"https://georisques.gouv.fr/api/v1/gaspar/catnat?code_insee={ins}&page=1&page_size=1")
            n = j.get("results")
            tot_p += n or 0
            ec = None if n is None else n - cat.get(ins, 0)
            print(f"    {ins}: producteur={n} base={cat.get(ins,0)} écart={ec}")
            time.sleep(0.8)
        print(f"    TOTAL producteur={tot_p} base={sum(cat.values())}")
    except Exception as e:
        print(f"  gaspar: ERREUR {e}")
    # 3) DPE ADEME : les trois jeux, filtre du connecteur (code_insee_ban:974*)
    try:
        for jeu, slug in [("existant", "dpe03existant"), ("neuf", "dpe02neuf"), ("tertiaire", "dpe01tertiaire")]:
            j = get_json(f"https://data.ademe.fr/data-fair/api/v1/datasets/{slug}/lines?qs=code_insee_ban%3A974*&size=0")
            n_base = one("SELECT count(*) FROM dpe_records WHERE jeu=%s", (jeu,))
            print(f"  DPE ADEME {jeu}: producteur(code_insee_ban:974*)={j.get('total')} base={n_base}")
            time.sleep(0.8)
    except Exception as e:
        print(f"  ademe: ERREUR {e}")
    # 4) BODACC : échantillon 3 sirens — dépôts des comptes (famille dpc) au producteur vs base
    try:
        sirens = [s for (s,) in q("SELECT siren FROM bodacc_depots GROUP BY 1 ORDER BY count(*) DESC LIMIT 3")]
        for s in sirens:
            j = get_json("https://bodacc-datadila.opendatasoft.com/api/explore/v2.1/catalog/datasets/"
                         f"annonces-commerciales/records?where=registre%20LIKE%20%22{s}%22%20AND%20familleavis%3D%22dpc%22&limit=0")
            nb = one("SELECT count(*) FROM bodacc_depots WHERE siren=%s", (s,))
            print(f"  BODACC dépôts siren {s}: producteur={j.get('total_count')} base={nb}")
            time.sleep(0.8)
    except Exception as e:
        print(f"  bodacc: ERREUR {e}")
    # 5) BAN : nbNumeros par commune (24 GET)
    try:
        adr = dict(q("SELECT insee, count(*) FROM adresses GROUP BY 1"))
        print("  BAN (plateforme.adresse.data.gouv /lookup) vs base :")
        tot = 0
        for ins in INSEE_24:
            j = get_json(f"https://plateforme.adresse.data.gouv.fr/lookup/{ins}")
            n = j.get("nbNumeros")
            tot += n or 0
            print(f"    {ins}: producteur(nbNumeros)={n} base={adr.get(ins,0)} écart={None if n is None else n - adr.get(ins,0)}")
            time.sleep(0.8)
        print(f"    TOTAL producteur={tot} base={sum(adr.values())}")
    except Exception as e:
        print(f"  ban: ERREUR {e}")
    # 6) DVF géo (Etalab) : 2 communes-années témoins, fichier commune officiel
    try:
        for ins, an in [("97403", 2024), ("97411", 2023)]:
            url = f"https://files.data.gouv.fr/geo-dvf/latest/csv/{an}/communes/974/{ins}.csv"
            data = get_bytes(url, timeout=60)
            if data[:2] == b"\x1f\x8b":
                data = gzip.decompress(data)
            rows = list(csv.DictReader(io.StringIO(data.decode("utf-8"))))
            muts = len({r["id_mutation"] for r in rows})
            b_rows, b_muts = q("SELECT count(*), count(DISTINCT id_mutation) FROM dvf_mutations_parcelle "
                               "WHERE code_commune=%s AND millesime=%s", (ins, an))[0]
            print(f"  DVF {ins}/{an}: producteur lignes={len(rows)} mutations={muts} | base lignes={b_rows} mutations={b_muts}")
            time.sleep(0.8)
    except Exception as e:
        print(f"  dvf: ERREUR {e}")
    print("  NON_VÉRIFIABLE en ligne (raison) : SIRENE géolocalisé (fichier national, API INSEE à jeton) ; "
          "Sitadel (CSV national DIDO sans compteur filtré) ; RNB (API alpha sans count) ; "
          "RPLS/DFI/Arcep/RNIC (fichiers nationaux ; compte producteur = millésime déclaré, contrôlé en B1) ; "
          "piscines/LiDAR/CoSIA (produits LABUSE dérivés, pas de compteur producteur).")


if __name__ == "__main__":
    b0_inventaire()
    b1_volumes()
    b2_couverture()
    b3_fantomes()
    b4_poids_mort()
    b5_en_ligne()
    print("\nFIN angle B.")
