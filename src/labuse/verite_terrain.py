"""VERITE-TERRAIN-1 — LABUSE face aux sources officielles, sur 500 parcelles.

Les chasses aux invariants vérifient que LABUSE est COHÉRENT AVEC LUI-MÊME. Elles ne voient
pas un chiffre FAUX mais identique partout (une contenance mal ingérée, une zone PLU décalée,
une hauteur mal recopiée). Seule la comparaison avec la source officielle, interrogée en direct,
l'attrape. Le contrôle mensuel (SOLIDITE-1, `verite_sources.py`) le fait sur 20 parcelles ; ici on
le fait une fois sur 500, pour MESURER le taux d'erreur réel de chaque donnée.

Ce module ÉTEND l'oracle ORACLE-1 (`scripts.coherence.oracles`) — il réutilise son socle réseau
(curl, backoff, respect des cadences) et son haversine — mais apporte ce que la sonde mensuelle
n'avait pas :

  · un échantillon STRATIFIÉ et REPRODUCTIBLE de 500 parcelles (graine fixée) : les 24 communes
    au prorata, avec un minimum pour chaque cas difficile ;
  · les QUATRE verdicts du mandat — CONFORME · LABUSE FAUX · SOURCE PLUS RÉCENTE · NON COMPARABLE —
    là où la sonde n'en avait que trois (la fraîcheur était confondue avec le faux) ;
  · une MISE EN CACHE LOCALE des réponses officielles (dans le dossier de la chasse, jamais en base)
    avec REPRISE : une chasse interrompue repart sans refaire les appels déjà faits ;
  · huit sources (cadastre, BAN, PLU/GPU, Géorisques, DVF, bâti RNB, entreprises SIRENE, ADEME/Sitadel)
    au lieu de cinq.

LECTURE SEULE : aucune écriture en base, rien sur le VPS. La fiche SERVIE est lue EN-PROCESS
(TestClient + session pilote) — comme le banc — pour que l'auth de prod ne bloque pas la sonde ;
les appels aux sources officielles partent en direct (curl), séquentiels et espacés.

    python -m labuse.verite_terrain echantillon            # (re)tire les 500 → ECHANTILLON.md
    python -m labuse.verite_terrain comparer --source cadastre [--n 50]
    python -m labuse.verite_terrain comparer --source toutes  # tout (long)
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import random
import sys
import time
from pathlib import Path

import psycopg

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "verite-terrain-1"
CACHE = Path(os.environ.get("VT_CACHE", SORTIE / "cache"))
ECHANTILLON_CSV = SORTIE / "echantillon.csv"
COMPARAISONS_CSV = SORTIE / "COMPARAISONS.csv"
GRAINE = int(os.environ.get("VT_GRAINE", "20261015"))

# ───────────────────────── les quatre verdicts du mandat
CONFORME = "CONFORME"
FAUX = "LABUSE FAUX"
RECENTE = "SOURCE PLUS RÉCENTE"
NC = "NON COMPARABLE"
VERDICTS = (CONFORME, FAUX, RECENTE, NC)

# Communes « des Hauts » (cirques + plaines d'altitude) — INSEE.
HAUTS = {"97424": "Cilaos", "97421": "Salazie", "97403": "Entre-Deux",
         "97406": "La Plaine-des-Palmistes"}


def _dsn() -> str:
    from .config import get_settings
    raw = os.environ.get("LABUSE_VT_DSN") or get_settings().database_url
    return (raw.replace("postgresql+psycopg://", "postgresql://")
               .replace("postgresql+psycopg2://", "postgresql://"))


# ═════════════════════════════════════════════════════════════════════════════════════════
#  CACHE LOCAL + SOCLE RÉSEAU (réutilise le curl/backoff d'ORACLE-1, enrobé d'un cache disque)
# ═════════════════════════════════════════════════════════════════════════════════════════

def _cle(source: str, url: str) -> Path:
    h = hashlib.sha1(f"{source}|{url}".encode()).hexdigest()
    return CACHE / source / f"{h}.json"


def fetch_json(url: str, source: str, timeout: int = 40, essais: int = 3,
               rafraichir: bool = False):
    """GET JSON avec CACHE DISQUE et REPRISE. Une réponse réussie (y compris un 'vide'
    explicite) est mémorisée sous `cache/<source>/<sha1>.json` ; une chasse relancée la relit
    sans rappeler le service. Les erreurs réseau NE sont PAS mises en cache (retentées à la
    reprise). `rafraichir=True` force un nouvel appel. Rend (payload, depuis_cache: bool)."""
    cle = _cle(source, url)
    if cle.exists() and not rafraichir:
        try:
            d = json.loads(cle.read_text())
            return d.get("body"), True
        except Exception:  # noqa: BLE001 — cache corrompu → on refait l'appel
            pass
    from scripts.coherence import oracles
    body = oracles._json(url, timeout=timeout, essais=essais)   # curl + backoff d'ORACLE-1
    cle.parent.mkdir(parents=True, exist_ok=True)
    cle.write_text(json.dumps({"url": url, "fetched_at": _horodatage(), "body": body},
                              ensure_ascii=False))
    return body, False


def fetch_texte(url: str, source: str, timeout: int = 40) -> tuple[str, bool]:
    """Idem mais pour du texte brut (CSV DVF, PDF déjà en cache local, etc.)."""
    cle = _cle(source, url).with_suffix(".txt")
    if cle.exists():
        return cle.read_text(), True
    from scripts.coherence import oracles
    raw = oracles._get(url, timeout=timeout).decode("utf-8", "replace")
    cle.parent.mkdir(parents=True, exist_ok=True)
    cle.write_text(raw)
    return raw, False


def _horodatage() -> str:
    # Date du système, en ISO ; utilisée pour tracer QUAND la réponse officielle a été lue.
    import datetime
    return datetime.datetime.now().astimezone().isoformat(timespec="seconds")


# ═════════════════════════════════════════════════════════════════════════════════════════
#  COLLECTEUR À QUATRE VERDICTS
# ═════════════════════════════════════════════════════════════════════════════════════════

class VT:
    """Collecteur de comparaisons. Chaque ligne : parcelle, champ, source, valeur_labuse,
    valeur_officielle, date_source, verdict (parmi VERDICTS), ecart, url, note.

    `compare` tranche CONFORME / LABUSE FAUX / SOURCE PLUS RÉCENTE :
      · égal (à la tolérance près)                      → CONFORME ;
      · différent, et la source est datée APRÈS notre
        version (date_source > date_labuse)             → SOURCE PLUS RÉCENTE (fraîcheur, pas bug) ;
      · différent sinon                                 → LABUSE FAUX (candidat ; revérifié à la main).
    `non_comparable` pose un NON COMPARABLE avec sa raison."""

    def __init__(self):
        self.lignes: list[dict] = []

    def _ligne(self, parcelle, champ, source, labuse, officiel, verdict,
               date_source="", ecart="", url="", note=""):
        self.lignes.append({
            "parcelle": parcelle, "champ": champ, "source": source,
            "valeur_labuse": labuse, "valeur_officielle": officiel,
            "date_source": date_source or "", "verdict": verdict,
            "ecart": ecart, "url": url, "note": note})

    @staticmethod
    def _egal(labuse, officiel, tol_rel: float) -> tuple[bool, str]:
        try:
            fa, fb = float(labuse), float(officiel)
            e = abs(fa - fb)
            ok = e <= tol_rel * max(abs(fa), abs(fb), 1)
            return ok, ("" if ok else f"{e:.4g}")
        except (TypeError, ValueError):
            a = str(labuse).strip().lower()
            b = str(officiel).strip().lower()
            ok = a == b
            return ok, ("" if ok else f"{labuse!r} ≠ {officiel!r}")

    def compare(self, parcelle, champ, source, labuse, officiel, *, tol_rel=0.0,
                date_source="", date_labuse="", url="", note="") -> str:
        ok, ecart = self._egal(labuse, officiel, tol_rel)
        if ok:
            verdict = CONFORME
        elif date_source and date_labuse and str(date_source) > str(date_labuse):
            verdict = RECENTE
        else:
            verdict = FAUX
        self._ligne(parcelle, champ, source, labuse, officiel, verdict,
                    date_source=date_source, ecart=ecart, url=url, note=note)
        return verdict

    def verdict(self, parcelle, champ, source, labuse, officiel, verdict, *,
                date_source="", ecart="", url="", note=""):
        """Pose un verdict déjà tranché par l'appelant (quand la logique dépasse l'égalité)."""
        assert verdict in VERDICTS, verdict
        self._ligne(parcelle, champ, source, labuse, officiel, verdict,
                    date_source=date_source, ecart=ecart, url=url, note=note)
        return verdict

    def non_comparable(self, parcelle, champ, source, raison, *, labuse="", url=""):
        self._ligne(parcelle, champ, source, labuse, "", NC, note=raison, url=url)
        return NC

    def bilan(self) -> dict:
        return {v: sum(1 for l in self.lignes if l["verdict"] == v) for v in VERDICTS}


# ═════════════════════════════════════════════════════════════════════════════════════════
#  LECTEUR DE FICHE SERVIE (en-process, comme le banc — pas d'HTTP public ni de quota)
# ═════════════════════════════════════════════════════════════════════════════════════════

class FicheServie:
    def __init__(self):
        from fastapi.testclient import TestClient
        from .api import auth
        from .api.app import app
        from .api.protection import HOTE_INTERNE
        self._client = TestClient(app, client=(HOTE_INTERNE, 0))
        self._client.cookies.set(auth.COOKIE, auth.make_token())

    def __call__(self, idu: str) -> dict:
        r = self._client.get(f"/parcels/{idu}")
        r.raise_for_status()
        return json.loads(r.content)


# ═════════════════════════════════════════════════════════════════════════════════════════
#  ÉCHANTILLON STRATIFIÉ REPRODUCTIBLE — 500 parcelles
# ═════════════════════════════════════════════════════════════════════════════════════════
#
# 24 communes AU PRORATA (backbone), avec un MINIMUM pour chaque cas difficile du mandat.
# Reproductible : une graine fixe + un contenu de base figé (q_v18) donnent le même tirage.
# Les strates NON spatiales tirent au hasard dans PostgreSQL (setseed + ORDER BY random(),
# reproductible) ; les strates SPATIALES (lentes en full-scan) tirent dans un VIVIER ordonné
# par l'index (idu asc ∪ desc, pour couvrir les deux bouts de l'INSEE), puis échantillonné en
# Python avec la même graine. Chaque strate est best-effort : une strate vide est documentée,
# jamais bloquante.

_MIN_STRATE = 20            # minimum garanti par cas difficile
_N_DEFAUT = 500

# Strates NON spatiales : (label, sql prenant %(k)s, remplace-t-il la graine ?)
_STRATES_SQL = [
    ("contenance_vs_dessin",
     "SELECT idu, commune FROM parcels WHERE contenance_m2 IS NOT NULL AND surface_m2>0 "
     "AND abs(contenance_m2-surface_m2)>0.05*surface_m2 AND cadastre_disparue_le IS NULL "
     "ORDER BY random() LIMIT %(k)s"),
    ("surface_incertaine",
     "SELECT idu, commune FROM parcels WHERE contenance_m2 IS NULL AND cadastre_disparue_le IS NULL "
     "ORDER BY random() LIMIT %(k)s"),
    ("cadastre_octobre",
     "SELECT idu, commune FROM parcels WHERE (created_at>='2026-10-01' OR updated_at>='2026-10-01') "
     "AND cadastre_disparue_le IS NULL ORDER BY random() LIMIT %(k)s"),
    ("bande_A",
     "SELECT s.idu, s.commune FROM score_labuse s WHERE s.run_label='q_v18' AND s.bande='A' "
     "ORDER BY random() LIMIT %(k)s"),
    ("proprietaire_societe",
     "SELECT idu, commune FROM (SELECT DISTINCT p.idu, p.commune FROM parcelle_personne_morale m "
     "JOIN parcels p ON p.idu=m.idu WHERE m.siren IS NOT NULL AND p.cadastre_disparue_le IS NULL) q "
     "ORDER BY random() LIMIT %(k)s"),
    ("ventes_recentes",
     "SELECT idu, commune FROM (SELECT DISTINCT p.idu, p.commune FROM dvf_mutations_parcelle d "
     "JOIN parcels p ON p.idu=d.id_parcelle WHERE d.date_mutation>='2024-01-01' "
     "AND p.cadastre_disparue_le IS NULL) q ORDER BY random() LIMIT %(k)s"),
    ("permis",
     "SELECT p.idu, p.commune FROM parcels p WHERE p.cadastre_disparue_le IS NULL AND EXISTS "
     "(SELECT 1 FROM sitadel_permits s WHERE jsonb_exists(s.idu_codes, p.idu)) "
     "ORDER BY random() LIMIT %(k)s"),
    ("zones_calibrees_plu8",
     "SELECT idu, commune FROM (SELECT DISTINCT p.idu, p.commune FROM parcel_zone_plu z "
     "JOIN parcels p ON p.idu=z.idu JOIN plu_reglement_extrait e "
     "ON e.insee=substring(p.idu,1,5) AND e.zone=z.zone_lib WHERE p.cadastre_disparue_le IS NULL) q "
     "ORDER BY random() LIMIT %(k)s"),
    ("les_Hauts",
     "SELECT idu, commune FROM parcels WHERE substring(idu,1,5) IN "
     "('97424','97421','97403','97406') AND cadastre_disparue_le IS NULL ORDER BY random() LIMIT %(k)s"),
]

# Strates SPATIALES : (label, sql index-ordonné prenant %(k)s et un suffixe ASC/DESC via {ordre})
_STRATES_SPATIALES = [
    ("bizone",
     "SELECT p.idu, p.commune FROM parcels p WHERE p.cadastre_disparue_le IS NULL AND "
     "(SELECT count(*) FROM spatial_layers l WHERE l.kind='plu_gpu_zone' "
     " AND ST_Intersects(p.geom_2975,l.geom_2975))>1 ORDER BY p.idu {ordre} LIMIT %(k)s"),
    ("ppr_rouge_partiel",
     "SELECT p.idu, p.commune FROM parcels p WHERE p.cadastre_disparue_le IS NULL AND EXISTS "
     "(SELECT 1 FROM spatial_layers l WHERE l.kind='ppr' AND l.subtype='INTERDICTION' "
     " AND ST_Intersects(p.geom_2975,l.geom_2975) "
     " AND NOT ST_Within(p.geom_2975,l.geom_2975)) ORDER BY p.idu {ordre} LIMIT %(k)s"),
    ("littoral",
     "SELECT p.idu, p.commune FROM parcels p WHERE p.cadastre_disparue_le IS NULL AND EXISTS "
     "(SELECT 1 FROM spatial_layers l WHERE l.kind='cinquante_pas' "
     " AND ST_Intersects(p.geom_2975,l.geom_2975)) ORDER BY p.idu {ordre} LIMIT %(k)s"),
]


def _seed_frac(label: str) -> float:
    """Graine déterministe dans [-1, 1] dérivée de (GRAINE, label) pour setseed()."""
    h = hashlib.sha1(f"{GRAINE}:{label}".encode()).hexdigest()
    return (int(h[:12], 16) / 0xFFFFFFFFFFFF) * 2 - 1


def _rng(label: str) -> random.Random:
    return random.Random(f"{GRAINE}:{label}")


def _fetch_strate_sql(conn, label: str, sql: str, k: int) -> list[tuple[str, str]]:
    with conn.cursor() as cur:
        cur.execute("SELECT setseed(%s)", (_seed_frac(label),))
        cur.execute(sql, {"k": k})
        return [(r[0], r[1]) for r in cur.fetchall()]


def _fetch_strate_spatiale(conn, label: str, sql: str, vivier: int) -> list[tuple[str, str]]:
    """Vivier index-ordonné : moitié idu ASC, moitié DESC (couvre bas et haut de l'INSEE)."""
    out: list[tuple[str, str]] = []
    vus: set[str] = set()
    for ordre in ("ASC", "DESC"):
        with conn.cursor() as cur:
            cur.execute(sql.format(ordre=ordre), {"k": vivier // 2})
            for idu, commune in cur.fetchall():
                if idu not in vus:
                    vus.add(idu)
                    out.append((idu, commune))
    return out


def tirer_echantillon(conn, n: int = _N_DEFAUT, min_strate: int = _MIN_STRATE) -> list[dict]:
    """Rend n dicts {idu, commune, insee, slots:[...]} : d'abord les minimums par cas difficile
    (sans doublon), puis le complément par prorata communal. Reproductible à graine fixe."""
    choisis: dict[str, dict] = {}          # idu -> {idu, commune, insee, slots:set}

    def _ajoute(idu, commune, slot):
        d = choisis.setdefault(idu, {"idu": idu, "commune": commune,
                                     "insee": idu[:5], "slots": []})
        if slot not in d["slots"]:
            d["slots"].append(slot)

    strates_vides: list[str] = []

    # 1) strates NON spatiales — on sur-tire (3×min) puis échantillonne pour la diversité.
    for label, sql in _STRATES_SQL:
        try:
            pool = _fetch_strate_sql(conn, label, sql, min_strate * 3)
        except Exception as exc:  # noqa: BLE001
            strates_vides.append(f"{label} (SQL: {str(exc)[:60]})")
            continue
        if not pool:
            strates_vides.append(f"{label} (0 candidat)")
            continue
        rng = _rng(label)
        rng.shuffle(pool)
        pris = 0
        for idu, commune in pool:
            if pris >= min_strate:
                break
            _ajoute(idu, commune, label)
            pris += 1
        if pris < min_strate:
            strates_vides.append(f"{label} ({pris}/{min_strate} seulement)")

    # 2) strates SPATIALES — vivier index-ordonné, échantillonné.
    for label, sql in _STRATES_SPATIALES:
        try:
            pool = _fetch_strate_spatiale(conn, label, sql, min_strate * 6)
        except Exception as exc:  # noqa: BLE001
            strates_vides.append(f"{label} (SQL: {str(exc)[:60]})")
            continue
        if not pool:
            strates_vides.append(f"{label} (0 candidat)")
            continue
        rng = _rng(label)
        rng.shuffle(pool)
        pris = 0
        for idu, commune in pool:
            if pris >= min_strate:
                break
            _ajoute(idu, commune, label)
            pris += 1
        if pris < min_strate:
            strates_vides.append(f"{label} ({pris}/{min_strate} seulement)")

    # 3) complément PRORATA communal jusqu'à n.
    with conn.cursor() as cur:
        cur.execute("SELECT commune, count(*) FROM parcels WHERE cadastre_disparue_le IS NULL "
                    "GROUP BY commune")
        pop = dict(cur.fetchall())
    total = sum(pop.values())
    reste = n - len(choisis)
    if reste > 0:
        # Cible par commune AU PRORATA, en déduisant ce que les strates ont déjà apporté. Le total
        # des « besoins » (cible − déjà) dépasse souvent `reste` (certaines communes sont déjà
        # sur-représentées par les strates) ; on RÉPARTIT donc `reste` AU PRORATA DES BESOINS
        # (plus de gloutonnerie « plus grande commune d'abord » qui affamait les petites).
        deja = {}
        for d in choisis.values():
            deja[d["commune"]] = deja.get(d["commune"], 0) + 1
        besoins = {c: max(0.0, n * nb / total - deja.get(c, 0)) for c, nb in pop.items()}
        somme_besoins = sum(besoins.values()) or 1.0
        reste0 = reste
        for commune, _b in sorted(besoins.items(), key=lambda kv: -kv[1]):
            if reste <= 0:
                break
            alloc = min(round(reste0 * besoins[commune] / somme_besoins), reste)
            if alloc <= 0:
                continue
            besoin = alloc
            k = besoin + deja.get(commune, 0) + 40   # sur-tire pour sauter les déjà pris (dédup)
            try:
                with conn.cursor() as cur:
                    cur.execute("SELECT setseed(%s)", (_seed_frac(f"prorata:{commune}"),))
                    cur.execute("SELECT idu, commune FROM parcels WHERE commune=%s "
                                "AND cadastre_disparue_le IS NULL ORDER BY random() LIMIT %s",
                                (commune, k))
                    rows = cur.fetchall()
            except Exception:  # noqa: BLE001
                continue
            pris_commune = 0
            for idu, c in rows:
                if reste <= 0 or pris_commune >= besoin:   # CAP PAR COMMUNE (sinon on draine reste)
                    break
                if idu not in choisis:
                    _ajoute(idu, c, "prorata")
                    reste -= 1
                    pris_commune += 1

    # 4) dernier filet : s'il manque encore (communes saturées), compléter n'importe où.
    if len(choisis) < n:
        with conn.cursor() as cur:
            cur.execute("SELECT setseed(%s)", (_seed_frac("filet"),))
            cur.execute("SELECT idu, commune FROM parcels WHERE cadastre_disparue_le IS NULL "
                        "ORDER BY random() LIMIT %s", (n * 2,))
            for idu, commune in cur.fetchall():
                if len(choisis) >= n:
                    break
                if idu not in choisis:
                    _ajoute(idu, commune, "prorata")

    echantillon = sorted(choisis.values(), key=lambda d: d["idu"])[:n]
    tirer_echantillon.strates_vides = strates_vides  # exposé pour le rapport
    return echantillon


# ═════════════════════════════════════════════════════════════════════════════════════════
#  CLI
# ═════════════════════════════════════════════════════════════════════════════════════════

def _charger_echantillon() -> list[dict]:
    if not ECHANTILLON_CSV.exists():
        raise SystemExit("échantillon absent — lancer d'abord : python -m labuse.verite_terrain echantillon")
    out = []
    with open(ECHANTILLON_CSV, newline="") as f:
        for r in csv.DictReader(f):
            out.append({"idu": r["idu"], "commune": r["commune"], "insee": r["insee"],
                        "slots": r["slots"].split("|") if r["slots"] else []})
    return out


def cmd_echantillon(n: int = _N_DEFAUT) -> None:
    SORTIE.mkdir(parents=True, exist_ok=True)
    conn = psycopg.connect(_dsn())
    conn.read_only = True
    conn.autocommit = True   # lectures indépendantes : une strate qui casse n'avorte pas les suivantes
    try:
        ech = tirer_echantillon(conn, n)
    finally:
        conn.close()
    with open(ECHANTILLON_CSV, "w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["idu", "commune", "insee", "slots"])
        for d in ech:
            w.writerow([d["idu"], d["commune"], d["insee"], "|".join(d["slots"])])
    vides = getattr(tirer_echantillon, "strates_vides", [])
    print(f"échantillon : {len(ech)} parcelles → {ECHANTILLON_CSV}")
    if vides:
        print("strates best-effort incomplètes :")
        for v in vides:
            print("  -", v)
    _ecrire_echantillon_md(ech, vides)


def _ecrire_echantillon_md(ech: list[dict], vides: list[str]) -> None:
    from collections import Counter
    par_commune = Counter(d["commune"] for d in ech)
    par_slot = Counter(s for d in ech for s in d["slots"])
    lignes = [
        "# VERITE-TERRAIN-1 — ÉCHANTILLON",
        "",
        f"**{len(ech)} parcelles**, tirées au hasard mais stratifiées et reproductibles "
        f"(graine `{GRAINE}`, base figée q_v18).",
        "",
        "Reproduire : `python -m labuse.verite_terrain echantillon`. Le tirage est déterministe "
        "(même graine + même contenu de base = même échantillon).",
        "",
        "## Répartition par commune (prorata)",
        "",
        "| Commune | Parcelles |",
        "|---|---|",
    ]
    for commune, nb in sorted(par_commune.items(), key=lambda kv: -kv[1]):
        lignes.append(f"| {commune} | {nb} |")
    lignes += ["", "## Minimum garanti par cas difficile", "",
               "| Cas difficile | Parcelles |", "|---|---|"]
    for slot, nb in sorted(par_slot.items(), key=lambda kv: -kv[1]):
        lignes.append(f"| {slot} | {nb} |")
    if vides:
        lignes += ["", "## Strates best-effort incomplètes (documentées, non bloquantes)", ""]
        lignes += [f"- {v}" for v in vides]
    lignes += ["", "## Les 500 parcelles", "",
               "| # | IDU | Commune | Cas |", "|---|---|---|---|"]
    for i, d in enumerate(ech, 1):
        lignes.append(f"| {i} | {d['idu']} | {d['commune']} | {', '.join(d['slots'])} |")
    (SORTIE / "ECHANTILLON.md").write_text("\n".join(lignes) + "\n")
    print(f"→ {SORTIE / 'ECHANTILLON.md'}")


def main(argv: list[str] | None = None) -> None:
    import argparse
    p = argparse.ArgumentParser(prog="labuse.verite_terrain")
    sub = p.add_subparsers(dest="cmd", required=True)
    pe = sub.add_parser("echantillon", help="(re)tire les 500 parcelles")
    pe.add_argument("--n", type=int, default=_N_DEFAUT)
    pc = sub.add_parser("comparer", help="compare une source (ou toutes)")
    pc.add_argument("--source", required=True)
    pc.add_argument("--n", type=int, default=0, help="0 = tout l'échantillon")
    pc.add_argument("--rafraichir", action="store_true")
    a = p.parse_args(argv)
    if str(RACINE) not in sys.path:
        sys.path.insert(0, str(RACINE))
    if a.cmd == "echantillon":
        cmd_echantillon(a.n)
    elif a.cmd == "comparer":
        from .verite_terrain_sources import cmd_comparer
        cmd_comparer(a.source, a.n, a.rafraichir)


if __name__ == "__main__":
    main()
