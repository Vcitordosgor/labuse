"""FRAICHEUR-FIX-1 (point 1) — le format Etalab ACTUEL de géo-DVF, lu depuis l'API data.gouv.

En octobre 2026, Etalab a changé la distribution de géo-DVF :
  · AVANT  — un fichier par DÉPARTEMENT et par ANNÉE sous `files.data.gouv.fr/geo-dvf/latest/csv/
             {année}/departements/{dep}.csv.gz`. Cette arborescence LEGACY est FIGÉE depuis mai 2026
             (Last-Modified « Mon, 18 May 2026 ») et ANNONCÉE À LA SUPPRESSION au 31/11/2026.
  · APRÈS  — un fichier par PÉRIODE pour TOUTE la France, publié comme RESSOURCE du jeu data.gouv
             `demandes-de-valeurs-foncieres-geolocalisees` : `full-2021-s2`, `full-2022` … `full-2025`,
             `full-2026-s1` (fenêtre glissante 5 ans). Chaque ressource est servie sur
             `static.data.gouv.fr/resources/<slug>/<AAAAMMJJ-HHMMSS>/<nom>.csv.gz`.

L'ancien détecteur (`fraicheur.check_dvf_livraison`) faisait un HEAD sur l'arborescence legacy : elle
ne bouge plus → chaque passage était un no-op et le nouveau `full-2026-s1` n'était JAMAIS vu
(FRAICHEUR-1 §4.1). Ici, on lit la LISTE DES RESSOURCES du jeu (API data.gouv) et on déduit la
couverture du fichier le plus récent — exactement le signal que la source publie réellement.

Ce module est la SOURCE UNIQUE du format : `fraicheur.refresh_dvf` (table servie `dvf_mutations`),
`dvf_detail.build_dvf_detail` (table latérale) et la sentinelle (`sonder_dvf`) en dérivent tous.
Les fonctions réseau acceptent un `charger`/`http_get` injectable → testables sans réseau.
"""
from __future__ import annotations

import csv
import gzip
import io
import json
import re
from dataclasses import dataclass
from datetime import date

#: le jeu data.gouv officiel de géo-DVF (DGFiP / Etalab).
DATASET_SLUG = "demandes-de-valeurs-foncieres-geolocalisees"
DATASET_API = f"https://www.data.gouv.fr/api/1/datasets/{DATASET_SLUG}/"

#: une ressource utile = un fichier PÉRIODE `full-AAAA[-sN].csv.gz` (on IGNORE le fichier unique
#: `dvf.csv.gz` — 600 Mo, redondant — et l'entrée ARCHIVE qui pointe l'arborescence legacy).
_RES_RE = re.compile(r"/full-(\d{4})(?:-s([12]))?\.csv\.gz\b")
#: le segment horodaté du chemin static.data.gouv change à CHAQUE republication d'une ressource :
#: c'est notre signal de changement (plus robuste qu'un Last-Modified, qui restait figé côté legacy).
_VERSION_RE = re.compile(r"/resources/[^/]+/(\d{8}-\d{6})/")

DEP_974 = "974"


def periode_token(year: int, sem: int | None) -> str:
    """Millésime normé et COMPARABLE lexicalement : « 2024 » (année pleine) ou « 2026-S1 »/« 2021-S2 »."""
    return f"{year}-S{sem}" if sem else str(year)


def periode_bornes(year: int, sem: int | None) -> tuple[date, date]:
    """Bornes de dates couvertes par une ressource période (pour un rechargement SANS doublon :
    on supprime exactement cette fenêtre avant de réinsérer)."""
    if sem == 1:
        return date(year, 1, 1), date(year, 6, 30)
    if sem == 2:
        return date(year, 7, 1), date(year, 12, 31)
    return date(year, 1, 1), date(year, 12, 31)


@dataclass(frozen=True)
class Ressource:
    token: str          # « 2026-S1 » / « 2024 »
    year: int
    sem: int | None
    url: str
    version: str        # segment horodaté (« 20261020-114825 ») = signal de changement
    filesize: int | None

    @property
    def bornes(self) -> tuple[date, date]:
        return periode_bornes(self.year, self.sem)


def _http_get(url: str) -> bytes:
    """GET réel (httpx, UA LABUSE). Isolé pour l'injection en test."""
    from .layers_ingest import _client
    with _client() as c:
        r = c.get(url, timeout=300.0)
        r.raise_for_status()
        return r.content


def lister_ressources(http_get=None) -> tuple[list[Ressource], str | None]:
    """Lit les ressources `full-AAAA[-sN].csv.gz` du jeu data.gouv (triées par période croissante)
    et le `last_update` du jeu. `http_get(url) -> bytes` injectable. Une période en double (rare) =
    on garde la ressource au segment horodaté le plus récent."""
    get = http_get or _http_get
    meta = json.loads(get(DATASET_API).decode("utf-8", "replace"))
    par_token: dict[str, Ressource] = {}
    for r in meta.get("resources", []):
        url = r.get("url") or ""
        m = _RES_RE.search(url)
        if not m:
            continue
        year, sem = int(m.group(1)), (int(m.group(2)) if m.group(2) else None)
        vm = _VERSION_RE.search(url)
        res = Ressource(token=periode_token(year, sem), year=year, sem=sem, url=url,
                        version=(vm.group(1) if vm else ""), filesize=r.get("filesize"))
        ancien = par_token.get(res.token)
        if ancien is None or res.version > ancien.version:
            par_token[res.token] = res
    ressources = sorted(par_token.values(), key=lambda x: x.token)
    return ressources, meta.get("last_update")


def dernier_millesime(ressources: list[Ressource]) -> str | None:
    """Le millésime le plus récent PUBLIÉ (token de la dernière ressource). None si aucune."""
    return ressources[-1].token if ressources else None


def lignes_974(res: Ressource, http_get=None) -> list[dict]:
    """Télécharge la ressource (full-France, .csv.gz) et rend les LIGNES brutes du département 974.
    Streamé et filtré en mémoire : seules les ~quelques milliers de lignes 974 sont conservées
    (le fichier national fait des dizaines de Mo), jamais toute la France."""
    get = http_get or _http_get
    brut = gzip.decompress(get(res.url))
    out: list[dict] = []
    reader = csv.DictReader(io.TextIOWrapper(io.BytesIO(brut), encoding="utf-8", errors="replace"))
    for row in reader:
        if (row.get("code_departement") or "").strip() == DEP_974:
            out.append(row)
    return out
