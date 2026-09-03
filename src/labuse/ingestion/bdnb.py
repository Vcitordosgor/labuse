"""BDNB — Base nationale des bâtiments (CSTB, Licence Ouverte) — SCORING-3 · L3.

Par bâtiment : année de construction, classe DPE, surfaces, usage — le dernier
proxy accessible de l'âge du propriétaire et de l'état du bien (plan v2 §2.4).

Distribution amont (constatée le 03/09/2026, sondée pour de vrai) : depuis le
millésime 2026-02-a, le CSTB ne publie QUE des exports France entiers
(csv.tar.gz ~39 Go) — plus d'extrait départemental. L'ingestion STREAME donc
l'archive nationale et ne garde que le département (974) des tables utiles,
sans jamais poser les 39 Go sur le disque :

  réseau (S3, ~55 Mo/s) → gunzip → tar (flux) → filtre lignes dep=974
  → data/bdnb/<millesime>/*.csv (quelques dizaines de Mo)

Tables retenues :
  - rel_batiment_groupe_parcelle : la jointure bâtiment → parcelle PAR L'EMPRISE
    (croisement cadastre fait par le CSTB — la même jointure que le mandat
    demande, déjà calculée à la source) ;
  - batiment_groupe_ffo_bat : année de construction, usage, surfaces (FF) ;
  - batiment_groupe_dpe_representatif_logement : classe DPE représentative ;
  - batiment_groupe_bdtopo_bat : surface BD TOPO vue par la BDNB (écart) ;
  - batiment_groupe : socle (commune, département).

Doctrine : la sentinelle SURVEILLE (api data.gouv, `last_update`), le CRON
trimestriel CALCULE (cette ingestion → tables bdnb_*), rien de servi ne change
sans geste de Vic — les variables candidates passent au banc K0 avant toute
inscription au modèle (L3.2).
"""
from __future__ import annotations

import csv
import io
import json
import sys
import tarfile
import time
import urllib.request
from pathlib import Path

# géométries WKT en colonne : bien au-delà de la limite csv par défaut (128 Ko)
csv.field_size_limit(sys.maxsize)

from sqlalchemy import text
from sqlalchemy.orm import Session

DATASET_API = ("https://www.data.gouv.fr/api/1/datasets/"
               "base-de-donnees-nationale-des-batiments/")
DEP = "974"

#: tables gardées du flux national (basename → filtre)
TABLES_CIBLES = {
    "batiment_groupe.csv",
    "rel_batiment_groupe_parcelle.csv",
    "batiment_groupe_ffo_bat.csv",
    "batiment_groupe_dpe_representatif_logement.csv",
    "batiment_groupe_bdtopo_bat.csv",
}

#: colonnes candidates pour filtrer le département, par ordre de préférence.
COLS_DEP = ("code_departement_insee", "parcelle_id", "code_commune_insee")


def resoudre_export(timeout: float = 30.0) -> dict:
    """Lit l'API data.gouv (la MÊME que la sentinelle) et renvoie l'URL de
    l'export France csv.tar.gz + le millésime + last_update. Jamais une URL
    inventée : celle du catalogue amont, lue à chaque ingestion."""
    with urllib.request.urlopen(DATASET_API, timeout=timeout) as r:
        d = json.load(r)
    res = [x for x in d.get("resources", [])
           if (x.get("url") or "").endswith("_france_csv.tar.gz")]
    if not res:
        raise RuntimeError("BDNB : export France csv.tar.gz introuvable au "
                           "catalogue data.gouv — distribution amont changée ?")
    url = res[0]["url"]
    # .../bdnb_millesime_2026-02-a/... → « 2026-02-a »
    millesime = next((seg.replace("bdnb_millesime_", "")
                      for seg in url.split("/") if seg.startswith("bdnb_millesime_")),
                     "inconnu")
    return {"url": url, "millesime": millesime,
            "last_update": d.get("last_update"),
            "filesize": res[0].get("filesize")}


def _idx_dep(header: list[str]) -> tuple[int, str] | None:
    for c in COLS_DEP:
        if c in header:
            return header.index(c), c
    return None


class _FluxNonSeekable(io.RawIOBase):
    """Adaptateur lecture seule pour le membre d'un tar EN FLUX (le fileobj de
    tarfile mode 'r|gz' n'expose pas seekable(), TextIOWrapper le requiert)."""

    def __init__(self, f):
        self._f = f

    def readable(self) -> bool:
        return True

    def readinto(self, b) -> int:
        data = self._f.read(len(b))
        b[: len(data)] = data
        return len(data)


def sonde_couverture(url: str, dep: str = DEP, log=print) -> dict:
    """AVANT de filtrer 39 Go : la distribution amont couvre-t-elle le département ?

    Constat du 03/09/2026 (mesuré ligne à ligne) : l'export « France » 2026-02-a
    ne contient QUE la métropole — 96 départements, 0 ligne 974 sur 22,3 M dans
    batiment_groupe_ffo_bat. Cette sonde streame jusqu'à ffo_bat (~4 min) et
    compte les lignes du département : 0 → l'ingestion s'arrête là, HONNÊTEMENT
    (motif écrit au catalogue), sans dérouler les 39 Go pour rien."""
    req = urllib.request.Request(url, headers={"User-Agent": "labuse-bdnb/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        tf = tarfile.open(fileobj=resp, mode="r|gz")
        for membre in tf:
            if not membre.name.endswith("batiment_groupe_ffo_bat.csv"):
                continue
            src = io.TextIOWrapper(
                io.BufferedReader(_FluxNonSeekable(tf.extractfile(membre)),
                                  buffer_size=1 << 20),
                encoding="utf-8", newline="")
            lecteur = csv.reader(src, delimiter=";")
            header = next(lecteur)
            idx = header.index("code_departement_insee")
            n_dep = total = 0
            deps: set[str] = set()
            for ligne in lecteur:
                total += 1
                if idx < len(ligne):
                    deps.add(ligne[idx])
                    if ligne[idx] == dep:
                        n_dep += 1
            verdict = {"table_sondee": "batiment_groupe_ffo_bat",
                       "n_lignes": total, "n_departements": len(deps),
                       "n_lignes_dep": n_dep, "dep": dep,
                       "couvert": n_dep > 0}
            log(f"BDNB sonde : {total} lignes, {len(deps)} départements, "
                f"{n_dep} lignes {dep}")
            return verdict
    raise RuntimeError("BDNB : batiment_groupe_ffo_bat.csv absent de l'archive")


def telecharger_filtrer(dest: Path, *, url: str | None = None, dep: str = DEP,
                        log=print) -> dict:
    """Streame l'archive nationale et écrit data/bdnb/<dest>/ les tables cibles
    filtrées au département. Renvoie les compteurs par table."""
    info = {"url": url} if url else resoudre_export()
    url = info["url"]
    dest.mkdir(parents=True, exist_ok=True)
    compteurs: dict[str, dict] = {}
    t0 = time.time()
    req = urllib.request.Request(url, headers={"User-Agent": "labuse-bdnb/1.0"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        tf = tarfile.open(fileobj=resp, mode="r|gz")
        for membre in tf:
            nom = Path(membre.name).name
            if nom not in TABLES_CIBLES:
                continue
            log(f"[{time.strftime('%H:%M:%S')}] BDNB {nom} "
                f"({membre.size / 1e9:.1f} Go brut)…")
            src = io.TextIOWrapper(
                io.BufferedReader(_FluxNonSeekable(tf.extractfile(membre)),
                                  buffer_size=1 << 20),
                encoding="utf-8", newline="")
            lecteur = csv.reader(src, delimiter=";")   # export BDNB : point-virgule
            header = next(lecteur)
            pos = _idx_dep(header)
            if pos is None:
                log(f"  ⚠ {nom} : aucune colonne département connue "
                    f"({COLS_DEP}) — table ignorée, dit au rapport")
                compteurs[nom] = {"gardees": 0, "erreur": "colonne dep introuvable",
                                  "header": header[:12]}
                continue
            idx, col = pos
            gardees = total = 0
            with open(dest / nom, "w", encoding="utf-8", newline="") as out:
                w = csv.writer(out, delimiter=";")
                w.writerow(header)
                # préfiltre pas cher : une ligne sans « 974 » ne peut pas être
                # du département — le csv.reader ne parse que les candidates.
                for ligne in _lignes_candidates(src, dep):
                    total += 1
                    v = ligne[idx] if idx < len(ligne) else ""
                    if v.startswith(dep):
                        w.writerow(ligne)
                        gardees += 1
            compteurs[nom] = {"gardees": gardees, "candidates": total,
                              "colonne_filtre": col}
            log(f"  ✓ {nom} : {gardees} lignes {dep} gardées")
    duree = int(time.time() - t0)
    (dest / "_ingestion.json").write_text(json.dumps(
        {"info": info, "dep": dep, "duree_s": duree, "tables": compteurs},
        ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    return {"info": info, "duree_s": duree, "tables": compteurs}


def _lignes_candidates(src, dep: str):
    """Itère les lignes parsées, en ne parsant QUE celles qui contiennent la
    sous-chaîne du département (préfiltre conservateur : aucune ligne du
    département ne peut être écartée, les faux positifs sont re-vérifiés par
    colonne)."""
    # csv.reader consomme src ligne à ligne ; on préfiltre sur le tampon texte.
    tampon = []
    for brute in src:
        if dep not in brute:
            continue
        tampon.append(brute)
        if brute.count('"') % 2 == 0:      # ligne complète (guillemets fermés)
            for ligne in csv.reader(tampon, delimiter=";"):
                yield ligne
            tampon = []
    if tampon:
        for ligne in csv.reader(tampon, delimiter=";"):
            yield ligne


# ─────────────────────────── chargement en base ───────────────────────────

def charger_en_base(session: Session, src: Path, *, millesime: str) -> dict:
    """Charge les CSV filtrés dans les tables bdnb_* (remplacement atomique par
    millésime : DROP + CREATE — la BDNB est un référentiel, pas un flux) et
    mesure la couverture parcelle. Écrit la fraîcheur au catalogue."""
    import pandas as pd

    compteurs: dict[str, int] = {}

    def _table(nom_csv: str, nom_table: str, colonnes: dict[str, str]) -> int:
        p = src / nom_csv
        if not p.exists():
            compteurs[nom_table] = 0
            return 0
        df = pd.read_csv(p, dtype=str, sep=";", usecols=lambda c: c in colonnes)
        df = df.rename(columns=colonnes)
        session.execute(text(f"DROP TABLE IF EXISTS {nom_table}"))
        df.to_sql(nom_table, session.connection(), index=False,
                  method="multi", chunksize=5000)
        compteurs[nom_table] = len(df)
        return len(df)

    # la jointure bâtiment → parcelle (croisement d'emprise cadastre, fait CSTB)
    _table("rel_batiment_groupe_parcelle.csv", "bdnb_rel_parcelle",
           {"batiment_groupe_id": "batiment_groupe_id",
            "parcelle_id": "parcelle_idu",
            "parcelle_principale": "parcelle_principale"})
    _table("batiment_groupe_ffo_bat.csv", "bdnb_ffo",
           {"batiment_groupe_id": "batiment_groupe_id",
            "annee_construction": "annee_construction",
            "usage_niveau_1_txt": "usage_txt",
            "nb_log": "nb_log", "nb_niveau": "nb_niveau",
            "mat_mur_txt": "mat_mur_txt"})
    _table("batiment_groupe_dpe_representatif_logement.csv", "bdnb_dpe",
           {"batiment_groupe_id": "batiment_groupe_id",
            "classe_bilan_dpe": "classe_dpe",
            "surface_habitable_logement": "surface_habitable_m2",
            "annee_construction_dpe": "annee_construction_dpe",
            "periode_construction_dpe": "periode_construction_dpe"})
    # le socle : surface d'emprise du groupe (s_geom_groupe) — l'« écart de surface
    # bâtie BDNB vs BD TOPO » se mesure contre notre p_model_bati.emprise_bati_m2
    _table("batiment_groupe.csv", "bdnb_groupe",
           {"batiment_groupe_id": "batiment_groupe_id",
            "code_commune_insee": "code_commune_insee",
            "s_geom_groupe": "s_geom_groupe_m2"})

    for t, cols in (("bdnb_rel_parcelle", "parcelle_idu"),
                    ("bdnb_rel_parcelle", "batiment_groupe_id"),
                    ("bdnb_ffo", "batiment_groupe_id"),
                    ("bdnb_dpe", "batiment_groupe_id"),
                    ("bdnb_groupe", "batiment_groupe_id")):
        if compteurs.get(t):
            session.execute(text(
                f"CREATE INDEX IF NOT EXISTS ix_{t}_{cols} ON {t} ({cols})"))

    # couverture : parcelles du parc avec ≥ 1 bâtiment BDNB rattaché
    couverture = session.execute(text("""
        SELECT count(DISTINCT p.idu) FROM parcels p
        JOIN bdnb_rel_parcelle r ON r.parcelle_idu = p.idu
    """)).scalar() if compteurs.get("bdnb_rel_parcelle") else 0
    parc = session.execute(text("SELECT count(*) FROM parcels")).scalar() or 1

    session.execute(text(
        "UPDATE data_sources SET last_sync_at = now(), source_millesime = :m "
        "WHERE name = 'BDNB'"), {"m": millesime})
    return {"tables": compteurs, "parcelles_couvertes": int(couverture or 0),
            "parc": int(parc), "couverture_pct": round(100 * (couverture or 0) / parc, 1),
            "millesime": millesime}


def build_bdnb(session: Session, *, dep: str = DEP, force: bool = False,
               log=print) -> dict:
    """L'ingestion complète (CRON trimestriel `ingest-bdnb` / CLI).
    Idempotente par millésime ; SONDE d'abord la couverture du département —
    l'export amont 2026-02-a ne couvre QUE la métropole (constat 03/09/2026,
    0 ligne 974 sur 22,3 M) : tant que c'est le cas, l'ingestion s'arrête
    honnêtement (motif au catalogue), et le trimestre suivant re-sonde."""
    info = resoudre_export()
    dest = Path("data/bdnb") / info["millesime"]
    deja = session.execute(text(
        "SELECT source_millesime FROM data_sources WHERE name = 'BDNB'")).scalar()
    if deja == info["millesime"] and not force:
        return {"skip": True, "millesime": info["millesime"],
                "motif": "millésime déjà ingéré (force pour rejouer)"}
    sonde = sonde_couverture(info["url"], dep=dep, log=log)
    if not sonde["couvert"]:
        motif = (f"export amont {info['millesime']} SANS le département {dep} "
                 f"({sonde['n_departements']} départements, métropole seule) — "
                 "ingestion sans objet, re-sondé au prochain trimestre")
        session.execute(text(
            "UPDATE data_sources SET fraicheur_erreur_at = now(), "
            "fraicheur_erreur_message = :m WHERE name = 'BDNB'"), {"m": motif})
        log(f"BDNB : {motif}")
        return {"skip": True, "millesime": info["millesime"], "motif": motif,
                "sonde": sonde}
    if not (dest / "_ingestion.json").exists() or force:
        telecharger_filtrer(dest, url=info["url"], dep=dep, log=log)
    r = charger_en_base(session, dest, millesime=info["millesime"])
    log(f"BDNB {info['millesime']} : {r['parcelles_couvertes']} parcelles couvertes "
        f"({r['couverture_pct']} % du parc)")
    return r
