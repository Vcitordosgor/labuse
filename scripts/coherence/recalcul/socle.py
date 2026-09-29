"""CALCULS-AUDIT-1 — le socle du recalcul indépendant.

Fournit : accès base LECTURE SEULE, chargement de l'échantillon gelé, le collecteur
ECARTS-CALCUL.csv (comparaison recalcul ↔ servi avec CAUSE), et le fournisseur de la
valeur SERVIE (fiche JSON via l'API en-process — jamais le code de calcul de production).

Aucune fonction de calcul de production n'est importée ici. La seule chose lue au back est
le RÉSULTAT servi (fiche JSON / table de résultat), pour le comparer au recalcul.
"""
from __future__ import annotations

import csv
import json
import math
import os
import pathlib

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[3]
SORTIE = RACINE / "docs" / "audit-2026-09" / "CALCULS-1"
ECHANTILLON = RACINE / "docs" / "audit-2026-09" / "COHERENCE-1" / "ECHANTILLON.csv"


def dsn() -> str:
    """DSN lecture seule — suit l'environnement (LABUSE_COHERENCE_DSN, LABUSE_DATABASE_URL),
    repli poste de dev. Identique à scripts.coherence.lib mais recopié pour rester
    self-contained (le mandat interdit d'importer le code de prod ; lib importe labuse.runs)."""
    explicite = os.environ.get("LABUSE_COHERENCE_DSN")
    if explicite:
        return explicite
    url = os.environ.get("LABUSE_DATABASE_URL", "")
    if url:
        return url.replace("postgresql+psycopg://", "postgresql://").replace(
            "postgresql+psycopg2://", "postgresql://")
    return "postgresql://openclaw@localhost:5432/labuse"


def connect():
    conn = psycopg.connect(dsn(), options="-c statement_timeout=180000")
    conn.autocommit = True
    return conn


def run_servi() -> str:
    """Label du run servi — lu dans config/served_run.txt (vue dérivée, pas un calcul)."""
    p = RACINE / "config" / "served_run.txt"
    if p.exists():
        for ligne in p.read_text().splitlines():
            ligne = ligne.strip()
            if ligne and not ligne.startswith("#"):
                return ligne
    return "q_v11_m137"


RUN = run_servi()


def charger_echantillon() -> list[dict]:
    with open(ECHANTILLON, newline="") as f:
        return list(csv.DictReader(f))


# ── fournisseur de la valeur SERVIE (fiche JSON en-process, sans calcul de prod exposé) ──

_CLIENT = None


def _client_en_process():
    """TestClient FastAPI en-process : la fiche servie telle que le client la voit, sans
    serveur HTTP ni quota. On ne lit QUE la sortie (JSON), jamais on n'appelle une fonction
    de calcul. (Chemin identique à scripts.coherence.lib.client_en_process.)"""
    global _CLIENT
    if _CLIENT is not None:
        return _CLIENT
    import sys
    sys.path.insert(0, str(RACINE / "src"))
    from fastapi.testclient import TestClient

    from labuse.api import auth
    from labuse.api.app import app
    from labuse.api.protection import HOTE_INTERNE
    client = TestClient(app, client=(HOTE_INTERNE, 0))
    client.cookies.set(auth.COOKIE, auth.make_token())
    _CLIENT = client
    return client


_FICHES: dict[str, object] = {}


def fiche(idu: str):
    """La fiche parcelle servie (dict) ou None. Cache par idu."""
    if idu in _FICHES:
        return _FICHES[idu]
    try:
        c = _client_en_process()
        r = c.get(f"/parcels/{idu}")
        r.raise_for_status()
        val = json.loads(r.content)
    except Exception as e:  # noqa: BLE001
        val = {"_erreur": str(e)[:200]}
    _FICHES[idu] = val
    return val


def chemin(obj, path: str, defaut=None):
    """Accès pointé tolérant : renvoie `defaut` si un maillon manque."""
    cur = obj
    for part in path.split("."):
        if isinstance(cur, dict):
            if part not in cur:
                return defaut
            cur = cur[part]
        elif isinstance(cur, list):
            try:
                cur = cur[int(part)]
            except (ValueError, IndexError):
                return defaut
        else:
            return defaut
    return cur


# ── collecteur ECARTS-CALCUL.csv ──

#: causes normalisées du mandat (lot B).
CAUSES = {
    "formule", "constante", "unite", "ordre_arrondi", "cas_limite",
    "division_zero", "negatif", "zero_pour_absence", "mauvais_id", "a_instruire",
}


class Recalc:
    """Collecte chaque comparaison recalcul ↔ servi. Écart hors tolérance → une ligne.

    tol : '0' (égalité stricte), 'n %' (relatif), 'k abs' (absolu k), '0,5 point'.
    Le pivot est TOUJOURS : valeur_recalc (l'indépendant) vs valeur_labuse (le servi)."""

    COLS = ["calcul", "notion", "objet", "valeur_labuse", "valeur_recalc",
            "ecart", "tol", "cause", "gravite"]

    def __init__(self):
        self.lignes: list[dict] = []
        self.n = 0

    @staticmethod
    def _num(v):
        try:
            if isinstance(v, bool):
                return None
            return float(v)
        except (TypeError, ValueError):
            return None

    def compare(self, calcul, notion, objet, servi, recalc, tol="1 %",
                cause="formule", gravite="ECART"):
        """Compare servi (labuse) et recalc (indépendant). Renvoie True si dans la tolérance."""
        self.n += 1
        # cas absence des deux côtés
        vide_s = servi is None or servi == ""
        vide_r = recalc is None or recalc == ""
        if vide_s and vide_r:
            return True
        # zéro d'un côté / absence de l'autre = FAUX-CLIENT
        if vide_s != vide_r:
            autre = recalc if vide_s else servi
            na = self._num(autre)
            if na == 0:
                self._noter(calcul, notion, objet, servi, recalc,
                            "0 contre absence", tol, "zero_pour_absence", "FAUX")
            else:
                self._noter(calcul, notion, objet, servi, recalc,
                            "valeur contre absence", tol, cause or "absence", "FAUX")
            return False
        ns, nr = self._num(servi), self._num(recalc)
        if ns is not None and nr is not None:
            if ns == nr:
                return True
            ecart = abs(ns - nr)
            base = max(abs(ns), abs(nr), 1e-9)
            rel = ecart / base
            ok = self._dans_tol(ns, nr, ecart, rel, tol)
            if ok:
                return True
            # cause auto par ordre de grandeur (aide l'instruction)
            cause_auto = self._cause_auto(ns, nr, rel)
            grav = gravite
            if cause_auto == "arrondi":
                grav = "TOLERABLE"
            self._noter(calcul, notion, objet, servi, recalc, f"{ecart:g}", tol,
                        cause_auto or cause, grav)
            return False
        # comparaison textuelle
        if str(servi) == str(recalc):
            return True
        self._noter(calcul, notion, objet, servi, recalc,
                    f"{servi!r} ≠ {recalc!r}", tol, cause or "label", gravite)
        return False

    @staticmethod
    def _dans_tol(ns, nr, ecart, rel, tol):
        t = tol.strip()
        if t.startswith("0,5 point") or t.startswith("0.5 point"):
            return ecart <= 0.5
        if t.endswith("abs"):
            k = float(t[:-3].replace(",", ".").strip() or 0)
            return ecart <= k
        if t == "0":
            return ns == nr
        if t.endswith("%"):
            pct = float(t[:-1].replace(",", ".").strip() or 1) / 100
            return rel <= pct
        return ns == nr

    @staticmethod
    def _cause_auto(ns, nr, rel):
        lo, hi = min(abs(ns), abs(nr)), max(abs(ns), abs(nr))
        ratio = hi / lo if lo > 1e-9 else 0
        if 90 <= ratio <= 110:
            return "unite"          # fraction ↔ pourcentage (×100)
        if 9000 <= ratio <= 11000:
            return "unite"          # ha ↔ m² (×10000)
        if 2.9 <= ratio <= 3.1:
            return "constante"      # facteur hauteur d'étage typique
        if rel <= 0.02:
            return "arrondi"
        return ""

    def _noter(self, calcul, notion, objet, servi, recalc, ecart, tol, cause, gravite):
        if cause not in CAUSES:
            cause = "a_instruire"
        self.lignes.append({
            "calcul": calcul, "notion": notion, "objet": str(objet),
            "valeur_labuse": _bref(servi), "valeur_recalc": _bref(recalc),
            "ecart": ecart, "tol": tol, "cause": cause, "gravite": gravite})

    def ecrire(self, fichier="ECARTS-CALCUL.csv"):
        SORTIE.mkdir(parents=True, exist_ok=True)
        chemin_csv = SORTIE / fichier
        with open(chemin_csv, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=self.COLS)
            w.writeheader()
            w.writerows(self.lignes)
        return chemin_csv

    def resume(self) -> dict:
        par_grav: dict[str, int] = {}
        par_cause: dict[str, int] = {}
        for l in self.lignes:
            par_grav[l["gravite"]] = par_grav.get(l["gravite"], 0) + 1
            par_cause[l["cause"]] = par_cause.get(l["cause"], 0) + 1
        return {"comparaisons": self.n, "ecarts": len(self.lignes),
                "par_gravite": par_grav, "par_cause": par_cause}


def _bref(v):
    if v is None:
        return "∅"
    if isinstance(v, float):
        return f"{v:g}"
    s = json.dumps(v, ensure_ascii=False, default=str) if isinstance(v, (dict, list)) else str(v)
    return s[:120]


# ── petits outils numériques réutilisés par plusieurs recalculs ──

def mediane(valeurs: list[float]):
    """Médiane INDÉPENDANTE (interpolation moyenne des deux centraux si n pair) — la
    référence contre laquelle on teste percentile_cont(0.5) de Postgres."""
    xs = sorted(v for v in valeurs if v is not None)
    n = len(xs)
    if n == 0:
        return None
    m = n // 2
    if n % 2 == 1:
        return float(xs[m])
    return (xs[m - 1] + xs[m]) / 2.0


def pente_deg_depuis_pct(pente_pct: float):
    """Pente en degrés à partir d'une pente en pourcentage : atan(pct/100)."""
    if pente_pct is None:
        return None
    return math.degrees(math.atan(pente_pct / 100.0))


if __name__ == "__main__":
    # fumée : connexion + échantillon + une fiche servie
    ech = charger_echantillon()
    print(f"échantillon : {len(ech)} parcelles, run servi {RUN}")
    with connect() as c, c.cursor() as cur:
        cur.execute("SELECT count(*) FROM parcels")
        print("parcels en base :", cur.fetchone()[0])
