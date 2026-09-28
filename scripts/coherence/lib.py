"""COHERENCE-1 — l'infrastructure du banc : accès aux lecteurs, comparaison, écarts.

Le banc interroge chaque lecteur d'une notion par son VRAI canal (endpoint HTTP, table,
tuile MVT décodée, PDF extrait) et compare les valeurs à la tolérance près. Aucune
écriture en base (statement_timeout posé), aucun navigateur.

Vocabulaire des valeurs :
  · une valeur Python (nombre, str, bool, liste) = la notion est servie ;
  · None       = le lecteur dit explicitement « pas de donnée » ;
  · ABSENT     = le lecteur ne porte pas cette notion pour cette parcelle (pas comparé) ;
  · ERREUR(msg)= le lecteur a échoué (HTTP 500, décodage…) — compté, jamais ignoré.

La comparaison rend une CAUSE probable automatique quand l'ordre de grandeur trahit le
bug (ratio ≈ 100 → fraction/pourcentage ; ≈ 10 000 → ha/m² ; petit → arrondi), et surtout
le cas fondateur : ZÉRO d'un côté / ABSENCE de l'autre = FAUX-CLIENT.
"""
from __future__ import annotations

import csv
import json
import math
import pathlib
import subprocess
import urllib.parse
import urllib.request

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-09" / "COHERENCE-1"
DSN = "postgresql://openclaw@localhost:5432/labuse"
API = "http://127.0.0.1:8605"
RUN = "q_v11_m137"


class Absent:
    """Le lecteur ne porte pas la notion ici (≠ None = « pas de donnée » affiché)."""
    def __repr__(self):
        return "ABSENT"


ABSENT = Absent()


class Erreur:
    def __init__(self, msg: str):
        self.msg = str(msg)[:200]

    def __repr__(self):
        return f"ERREUR({self.msg})"


class Contexte:
    """Caches par parcelle/commune : la fiche est UN appel, la tuile UN décodage."""

    def __init__(self):
        self.conn = psycopg.connect(DSN, options="-c statement_timeout=120000")
        self.conn.autocommit = True     # lecture seule ; une requête qui casse ne doit pas
        # avorter la suite (psycopg ouvrirait sinon une transaction par curseur)
        self._fiches: dict[str, dict] = {}
        self._tuiles: dict[str, dict] = {}
        self._communes: dict[str, dict] = {}
        self._http: dict[str, object] = {}

    def http_json(self, path: str):
        if path not in self._http:
            try:
                with urllib.request.urlopen(API + path, timeout=120) as r:
                    self._http[path] = json.loads(r.read())
            except Exception as e:  # noqa: BLE001 — l'échec est une donnée du banc
                self._http[path] = Erreur(e)
        return self._http[path]

    def fiche(self, idu: str):
        if idu not in self._fiches:
            self._fiches[idu] = self.http_json(f"/parcels/{idu}")
        return self._fiches[idu]

    def commune_ctx(self, commune: str):
        if commune not in self._communes:
            self._communes[commune] = self.http_json(
                f"/communes/{urllib.parse.quote(commune)}/contexte")
        return self._communes[commune]

    def sql1(self, query: str, **params):
        """Une valeur scalaire ; ABSENT si 0 ligne (= la source n'a pas de ligne)."""
        try:
            with self.conn.cursor() as cur:
                cur.execute(query, params)
                row = cur.fetchone()
        except Exception as e:  # noqa: BLE001 — l'échec est une donnée du banc
            self.conn.rollback()
            return Erreur(e)
        return row[0] if row else ABSENT

    def sql_row(self, query: str, **params):
        with self.conn.cursor() as cur:
            cur.execute(query, params)
            row = cur.fetchone()
            cols = [d.name for d in cur.description]
        return dict(zip(cols, row)) if row else None

    # ── tuiles MVT ──
    def _centroide(self, idu: str) -> tuple[float, float]:
        with self.conn.cursor() as cur:
            cur.execute("SELECT ST_X(ST_Transform(centroid,4326)), "
                        "ST_Y(ST_Transform(centroid,4326)) FROM parcels WHERE idu=%s", (idu,))
            return cur.fetchone()

    def tuile_props(self, idu: str, z: int = 14):
        """Les attributs de la parcelle dans la tuile MVT servie qui la contient."""
        cle = f"{idu}@{z}"
        if cle in self._tuiles:
            return self._tuiles[cle]
        try:
            lon, lat = self._centroide(idu)
            n = 2 ** z
            x = int((lon + 180) / 360 * n)
            y = int((1 - math.log(math.tan(math.radians(lat))
                                  + 1 / math.cos(math.radians(lat))) / math.pi) / 2 * n)
            pbf = pathlib.Path(f"/tmp/coherence_tile_{z}_{x}_{y}.pbf")
            if not pbf.exists():
                with urllib.request.urlopen(f"{API}/map/tiles/{z}/{x}/{y}.pbf", timeout=120) as r:
                    pbf.write_bytes(r.read())
            out = subprocess.run(
                ["node", str(RACINE / "scripts/coherence/decode_tile.mjs"), str(pbf)],
                capture_output=True, text=True, timeout=60)
            couches = json.loads(out.stdout)
            feat = None
            for feats in couches.values():
                for f in feats:
                    if f.get("idu") == idu:
                        feat = f
                        break
            self._tuiles[cle] = feat if feat is not None else ABSENT
        except Exception as e:  # noqa: BLE001
            self._tuiles[cle] = Erreur(e)
        return self._tuiles[cle]


def chemin(obj, path: str):
    """fiche('a.b.0.c') — ABSENT si un maillon manque, None si la feuille est null."""
    if isinstance(obj, Erreur):
        return obj
    cur = obj
    for part in path.split("."):
        if isinstance(cur, Erreur):
            return cur
        if isinstance(cur, dict):
            if part not in cur:
                return ABSENT
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return ABSENT
        elif cur is None:
            return ABSENT      # un parent null = la section entière est « pas de donnée »
        else:
            return ABSENT
    return cur


# ── comparaison ──

def _num(v):
    try:
        if isinstance(v, bool):
            return None
        return float(v)
    except (TypeError, ValueError):
        return None


def comparer(va, vb, tol: str):
    """→ (ok, ecart, cause_probable). tol : '0', '0,5 point', '1 %', 'n %'."""
    if isinstance(va, Erreur) or isinstance(vb, Erreur):
        return False, "erreur lecteur", "erreur"
    if va is ABSENT or vb is ABSENT:
        return True, "", ""                      # pas les deux lecteurs → pas un écart
    if va is None and vb is None:
        return True, "", ""
    na, nb = _num(va), _num(vb)
    # le cas fondateur : zéro affiché d'un côté, absence de l'autre
    if (va is None) != (vb is None):
        autre = nb if va is None else na
        if autre == 0:
            return False, "0 contre absence", "zero_pour_absence"
        return False, "valeur contre absence", "absence"
    if na is not None and nb is not None:
        if na == nb:
            return True, "0", ""
        ecart = abs(na - nb)
        rel = ecart / max(abs(na), abs(nb))
        if tol.startswith("0,5 point"):
            ok = ecart <= 0.5
        elif tol.strip().startswith("0"):
            ok = na == nb
        else:                                     # 'n %'
            pct = float(tol.replace("%", "").replace(",", ".").strip() or 1) / 100
            ok = rel <= pct
        cause = ""
        if not ok:
            ratio = (max(abs(na), abs(nb)) / min(abs(na), abs(nb))
                     if min(abs(na), abs(nb)) > 0 else 0)
            if 90 <= ratio <= 110:
                cause = "fraction_vs_pourcentage"
            elif 9000 <= ratio <= 11000:
                cause = "ha_vs_m2"
            elif rel <= 0.05:
                cause = "arrondi"
            else:
                cause = "calcul_ou_source"
        return ok, f"{ecart:g}", cause
    ok = str(va) == str(vb)
    return ok, "" if ok else f"{va!r} ≠ {vb!r}", "" if ok else "label"


class Ecarts:
    """Le collecteur ECARTS.csv — chaque comparaison est journalisée, écart ou pas."""

    COLS = ["notion", "objet", "lecteur_a", "valeur_a", "lecteur_b", "valeur_b",
            "ecart", "cause", "gravite"]

    def __init__(self):
        self.lignes: list[dict] = []
        self.n_comparaisons = 0

    def noter(self, notion, objet, la, va, lb, vb, tol, cause_declaree="", gravite_si_ecart="INCOHERENT"):
        self.n_comparaisons += 1
        ok, ecart, cause_auto = comparer(va, vb, tol)
        if ok:
            return True
        cause = cause_auto or cause_declaree or "à instruire"
        gravite = gravite_si_ecart
        if cause == "zero_pour_absence":
            gravite = "FAUX-CLIENT"
        elif cause == "arrondi":
            gravite = "TOLERABLE"
        self.lignes.append({"notion": notion, "objet": objet,
                            "lecteur_a": la, "valeur_a": _bref(va),
                            "lecteur_b": lb, "valeur_b": _bref(vb),
                            "ecart": ecart, "cause": cause, "gravite": gravite})
        return False

    def ecrire(self, fichier="ECARTS.csv"):
        SORTIE.mkdir(parents=True, exist_ok=True)
        with open(SORTIE / fichier, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.COLS)
            w.writeheader()
            w.writerows(self.lignes)
        return SORTIE / fichier


def _bref(v):
    if v is None:
        return "∅ (pas de donnée)"
    if isinstance(v, (Absent, Erreur)):
        return repr(v)
    s = json.dumps(v, ensure_ascii=False, default=str) if isinstance(v, (dict, list)) else str(v)
    return s[:120]
