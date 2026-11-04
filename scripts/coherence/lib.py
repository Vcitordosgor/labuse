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
import struct
import time
import urllib.error
import urllib.parse
import urllib.request

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-09" / "COHERENCE-1"


def _dsn_defaut() -> str:
    """COHERENCE-FIX-1 (lot G) — le DSN suit l'environnement : LABUSE_COHERENCE_DSN d'abord,
    sinon LABUSE_DATABASE_URL (débarrassé du dialecte SQLAlchemy), sinon le poste de dev."""
    import os
    explicite = os.environ.get("LABUSE_COHERENCE_DSN")
    if explicite:
        return explicite
    url = os.environ.get("LABUSE_DATABASE_URL", "")
    if url:
        return url.replace("postgresql+psycopg://", "postgresql://")
    return "postgresql://openclaw@localhost:5432/labuse"


def _run_defaut() -> str:
    """Le run servi VIVANT (config/served_manifest.json via labuse.runs) — plus jamais un label
    figé qui survivrait à une bascule. Repli sur l'ancien littéral si le paquet est introuvable."""
    import sys
    try:
        sys.path.insert(0, str(RACINE / "src"))
        from labuse import runs as _runs
        return _runs.current()
    except Exception:  # noqa: BLE001 — hors repo installé : dernier recours
        return "q_v11_m137"


import os as _os                                     # noqa: E402
DSN = _dsn_defaut()
API = _os.environ.get("LABUSE_COHERENCE_API") or "http://127.0.0.1:8605"
RUN = _run_defaut()


def client_en_process():
    """PRE-DEPLOY-1 (lot A) — un lecteur EN-PROCESS : TestClient FastAPI, JAMAIS l'API publique.

    Rend `(client, fetch)` où `fetch(path)` renvoie le JSON de la route, exactement comme un
    client HTTP le verrait — mais sans serveur, sans socket, sans réseau. Trois conséquences,
    voulues par le mandat :
      · pas de HTTP vers l'API publique (le banc nocturne ne consomme plus le port servi) ;
      · pas de quota anti-scraping (l'hôte réservé `HOTE_INTERNE` est exempté du rate-limit —
        inatteignable depuis le réseau, cf. protection.HOTE_INTERNE) ;
      · pas de `LABUSE_DEV_MODE` : l'auth reste ACTIVE (comme en prod), et le banc s'authentifie
        proprement par une session pilote MINTÉE en interne (`auth.make_token()`, signée par la
        vraie clé de l'app) — jamais un contournement d'auth.
    """
    import sys as _sys
    _sys.path.insert(0, str(RACINE / "src"))
    from fastapi.testclient import TestClient

    from labuse.api import auth
    from labuse.api.app import app
    from labuse.api.protection import HOTE_INTERNE
    client = TestClient(app, client=(HOTE_INTERNE, 0))
    client.cookies.set(auth.COOKIE, auth.make_token())   # session pilote (auth active hors 'local')

    def _fetch(path: str):
        r = client.get(path)
        r.raise_for_status()
        return json.loads(r.content)

    return client, _fetch


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


# ─────────────────────────── décodeur MVT des PROPRIÉTÉS (sans dépendance) ───────────────────────────
# AUTONOMIE-2 — le lecteur « tuile: » du banc lisait la tuile via un sous-processus node
# (`decode_tile.mjs` → @mapbox/vector-tile), qui exige les node_modules du front. En prod (et sur
# tout poste où le front n'est pas installé) node renvoyait un corps VIDE → `json.loads('')` →
# « Expecting value: line 1 column 1 » sur CHAQUE parcelle (1198 erreurs_lecteur au DEPLOY-AUTONOMIE),
# ce qui bloque le contrôle de cohérence (il exige erreurs_lecteur=0). Depuis la vague couches_tuyau
# la carte sert du protobuf MVT (`/map/tiles/z/x/y.pbf`) : on le décode ICI, en Python pur, sur les
# octets RÉELLEMENT servis — même philosophie « décodeur sans dépendance » que `circuit_tuiles.py`
# (qui décode la GÉOMÉTRIE). Celui-ci décode les PROPRIÉTÉS (clés/valeurs MVT) d'où le banc tire
# `idu`/`surface_m2`/`zone_lib`/`zone_fam`. La carte n'est PAS touchée.
def _mvt_varint(buf: bytes, pos: int) -> tuple[int, int]:
    shift = result = 0
    while True:
        b = buf[pos]
        pos += 1
        result |= (b & 0x7F) << shift
        if not (b & 0x80):
            return result, pos
        shift += 7


def _mvt_skip(buf: bytes, wire: int, pos: int) -> int:
    if wire == 0:
        _, pos = _mvt_varint(buf, pos)
    elif wire == 2:
        ln, pos = _mvt_varint(buf, pos)
        pos += ln
    elif wire == 5:
        pos += 4
    elif wire == 1:
        pos += 8
    else:
        raise ValueError(f"wire type {wire} non géré")
    return pos


def _mvt_value(buf: bytes, pos: int, end: int):
    """Un message Value MVT → valeur Python (string/float/double/int/uint/sint/bool)."""
    val = None
    while pos < end:
        key, pos = _mvt_varint(buf, pos)
        field, wire = key >> 3, key & 0x7
        if field == 1 and wire == 2:                         # string_value
            ln, pos = _mvt_varint(buf, pos)
            val = buf[pos:pos + ln].decode("utf-8"); pos += ln
        elif field == 2 and wire == 5:                       # float_value
            val = struct.unpack("<f", buf[pos:pos + 4])[0]; pos += 4
        elif field == 3 and wire == 1:                       # double_value
            val = struct.unpack("<d", buf[pos:pos + 8])[0]; pos += 8
        elif field == 4 and wire == 0:                       # int_value
            val, pos = _mvt_varint(buf, pos)
        elif field == 5 and wire == 0:                       # uint_value
            val, pos = _mvt_varint(buf, pos)
        elif field == 6 and wire == 0:                       # sint_value (zigzag)
            v, pos = _mvt_varint(buf, pos); val = (v >> 1) ^ -(v & 1)
        elif field == 7 and wire == 0:                       # bool_value
            v, pos = _mvt_varint(buf, pos); val = bool(v)
        else:
            pos = _mvt_skip(buf, wire, pos)
    return val


def _mvt_layer(buf: bytes, pos: int, end: int) -> tuple[str | None, list[dict]]:
    """Décode une couche MVT : (nom, [propriétés par feature]). Les clés (field 3) et valeurs
    (field 4) sont collectées, puis chaque feature résout ses tags (paires index-clé/index-valeur)."""
    name: str | None = None
    keys: list[str] = []
    values: list = []
    feats_tags: list[list[int]] = []
    while pos < end:
        key, pos = _mvt_varint(buf, pos)
        field, wire = key >> 3, key & 0x7
        if field == 1 and wire == 2:                         # name
            ln, pos = _mvt_varint(buf, pos)
            name = buf[pos:pos + ln].decode("utf-8"); pos += ln
        elif field == 3 and wire == 2:                       # key (string)
            ln, pos = _mvt_varint(buf, pos)
            keys.append(buf[pos:pos + ln].decode("utf-8")); pos += ln
        elif field == 4 and wire == 2:                       # value (message)
            ln, pos = _mvt_varint(buf, pos)
            values.append(_mvt_value(buf, pos, pos + ln)); pos += ln
        elif field == 2 and wire == 2:                       # feature
            ln, pos = _mvt_varint(buf, pos)
            fend = pos + ln
            tags: list[int] = []
            q = pos
            while q < fend:
                k2, q = _mvt_varint(buf, q)
                f2, w2 = k2 >> 3, k2 & 0x7
                if f2 == 2 and w2 == 2:                      # tags (packed varint)
                    tl, q = _mvt_varint(buf, q)
                    tend = q + tl
                    while q < tend:
                        v, q = _mvt_varint(buf, q)
                        tags.append(v)
                else:
                    q = _mvt_skip(buf, w2, q)
            feats_tags.append(tags)
            pos = fend
        else:
            pos = _mvt_skip(buf, wire, pos)
    props: list[dict] = []
    for tags in feats_tags:
        d: dict = {}
        for i in range(0, len(tags) - 1, 2):
            ki, vi = tags[i], tags[i + 1]
            if ki < len(keys) and vi < len(values):
                d[keys[ki]] = values[vi]
        props.append(d)
    return name, props


def decode_tile_props(data: bytes) -> dict[str, list[dict]]:
    """{nom_couche: [propriétés par feature]} — l'équivalent Python pur de l'ancien
    `decode_tile.mjs` (feature.properties), sur les octets MVT réellement servis. Un corps vide
    (parcelle hors tuile) rend {} → le lecteur conclut ABSENT, jamais une fausse erreur."""
    out: dict[str, list[dict]] = {}
    pos, n = 0, len(data)
    while pos < n:
        key, pos = _mvt_varint(data, pos)
        field, wire = key >> 3, key & 0x7
        if field == 3 and wire == 2:                         # layer
            ln, pos = _mvt_varint(data, pos)
            end = pos + ln
            name, props = _mvt_layer(data, pos, end)
            if name is not None:
                out[name] = props
            pos = end
        else:
            pos = _mvt_skip(data, wire, pos)
    return out


class Contexte:
    """Caches par parcelle/commune : la fiche est UN appel, la tuile UN décodage.

    COHERENCE-FIX-1 (lot G) — `fetch` injectable : le verrou V6b joue les MÊMES lecteurs
    en-process (TestClient FastAPI) sans serveur HTTP ; `dsn` injectable pour la base de test."""

    def __init__(self, dsn: str | None = None, fetch=None, client=None):
        self.conn = psycopg.connect(dsn or DSN, options="-c statement_timeout=120000")
        self.conn.autocommit = True     # lecture seule ; une requête qui casse ne doit pas
        # avorter la suite (psycopg ouvrirait sinon une transaction par curseur)
        self._fetch = fetch             # fetch(path) -> objet JSON (None = HTTP urllib)
        self._client = client           # TestClient en-process (octets bruts : tuiles PBF)
        self._fiches: dict[str, dict] = {}
        self._tuiles: dict[str, dict] = {}
        self._communes: dict[str, dict] = {}
        self._http: dict[str, object] = {}

    def http_json(self, path: str):
        if self._fetch is not None and path not in self._http:
            try:
                self._http[path] = self._fetch(path)
            except Exception as e:  # noqa: BLE001 — l'échec est une donnée du banc
                self._http[path] = Erreur(e)
        if path not in self._http:
            derniere = None
            for attente in (0, 2, 5, 15):     # l'API limite le débit (429) — on ré-essaie
                if attente:
                    time.sleep(attente)
                try:
                    with urllib.request.urlopen(API + path, timeout=120) as r:
                        self._http[path] = json.loads(r.read())
                    break
                except urllib.error.HTTPError as e:
                    derniere = e
                    if e.code != 429:
                        break
                except Exception as e:  # noqa: BLE001 — l'échec est une donnée du banc
                    derniere = e
                    break
            else:
                pass
            if path not in self._http:
                self._http[path] = Erreur(derniere)
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
            # COHERENCE-FIX-1 — le fichier tuile est CLÉ PAR PROCESSUS (un run = des tuiles
            # fraîches) : l'ancien cache disque nu (/tmp/coherence_tile_z_x_y.pbf) survivait à un
            # rebuild des MVT et faisait mesurer au banc des tuiles PÉRIMÉES (constaté : AB1117
            # tuile 0 vs table 27 après rebuild — la table était juste, le fichier datait du matin).
            import os as _os
            pbf = pathlib.Path(f"/tmp/coherence_tile_{_os.getpid()}_{z}_{x}_{y}.pbf")
            if not pbf.exists():
                if self._client is not None:     # EN-PROCESS : octets bruts via TestClient (pas de réseau)
                    resp = self._client.get(f"/map/tiles/{z}/{x}/{y}.pbf")
                    resp.raise_for_status()
                    pbf.write_bytes(resp.content)
                else:
                    with urllib.request.urlopen(f"{API}/map/tiles/{z}/{x}/{y}.pbf", timeout=120) as r:
                        pbf.write_bytes(r.read())
            # AUTONOMIE-2 — décodage MVT EN PYTHON PUR sur les octets servis (plus de sous-processus
            # node ni de node_modules du front : c'est ce qui faisait 1198 erreurs_lecteur en prod).
            couches = decode_tile_props(pbf.read_bytes())
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
    """→ (ok, ecart, cause_probable).

    ECARTS-ZERO-1 (décision Vic) — PLUS DE MARGE FLOUE. `tol` ne dit plus « combien on tolère »,
    il dit la PRÉCISION D'AFFICHAGE du fait = le nombre de décimales de son arrondi UNIQUE :
      · "0" / "0 (entier)" → le fait s'affiche à l'entier (m², €, compte) ;
      · "1"                → le fait s'affiche à une décimale (hauteur en m, pourcentage, pente).
    On arrondit LES DEUX lecteurs à cette précision puis on exige l'ÉGALITÉ STRICTE : une différence
    d'un m² / d'un euro / d'un dixième EST un écart rouge ; le bruit flottant SOUS l'unité affichée
    (float32 d'une tuile vs float64 d'une colonne, ST_Area recalculé) n'est jamais montré à l'écran,
    donc n'est pas un écart entre deux écrans. L'arrondi se fait UNE fois, au point de calcul/au bord ;
    le banc ne fait que lire chaque écran à sa précision servie.
    """
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
        ndec = 1 if tol.strip().startswith("1") else 0     # précision d'affichage du fait
        ra, rb = round(na, ndec), round(nb, ndec)
        if ra == rb:
            return True, "0", ""
        ecart = abs(ra - rb)
        # l'écart est RÉEL à la précision affichée → cause (jamais « arrondi toléré » : il n'existe plus)
        mn = min(abs(na), abs(nb))
        ratio = (max(abs(na), abs(nb)) / mn) if mn > 0 else 0
        if 90 <= ratio <= 110:
            cause = "fraction_vs_pourcentage"
        elif 9000 <= ratio <= 11000:
            cause = "ha_vs_m2"
        else:
            cause = "calcul_ou_source"
        return False, f"{ecart:g}", cause
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
        # ECARTS-ZERO-1 (décision Vic) — la gravité « TOLERABLE » n'existe plus : un fait a une
        # seule fonction de lecture, un seul arrondi, un seul format, partout. Le moindre écart
        # (même un euro, même un arrondi) est ROUGE. L'arrondi reste une CAUSE lisible dans la
        # colonne `cause`, mais ne dégrade plus la gravité. Le correctif se fait à la SOURCE
        # (arrondi unique au point de calcul ; format au bord via lib/format + registre_fmt).
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
