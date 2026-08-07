"""M51 — Récupération du RÈGLEMENT ÉCRIT PLU depuis le Géoportail de l'Urbanisme (GPU), la source
qui fait foi. Garde d'identité : l'idurba du document téléchargé DOIT égaler l'idurba attendu
(ancré M40, config/plu_millesimes.yaml) — sinon STOP, on ne sert pas un règlement non réconcilié.

Le pack GPU est un ZIP énorme (~300 Mo : cartes graphiques 40-50 Mo pièce). On n'extrait que le
règlement ÉCRIT (~1 Mo) par **extraction ZIP en HTTP Range** (on ne télécharge que l'entrée voulue),
via un lecteur seek/read adossé aux requêtes Range que `zipfile` sait piloter.

Provenance CONSIGNÉE par document (URL API, URL archive, date de fetch, sha256, idurba GPU).
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import re
import zipfile
from dataclasses import dataclass, field

import requests

_GPU = "https://www.geoportail-urbanisme.gouv.fr"
_UA = {"User-Agent": "labuse-m51-plu-annuaire/1.0 (verbatim sourcé, fetch règlement opposable)"}


class IdurbaMismatch(RuntimeError):
    """Garde d'identité : aucun document GPU ne porte l'idurba attendu → STOP (non réconcilié)."""


class _RangeReader:
    """Fichier virtuel seek/read adossé à des requêtes HTTP Range — `zipfile` lit ainsi l'EOCD
    (fin de fichier), le répertoire central, puis SEULE l'entrée demandée, sans tirer les 300 Mo."""

    def __init__(self, url: str, session: requests.Session, total: int):
        self.url, self.s, self.total, self.pos = url, session, total, 0

    def seek(self, off: int, whence: int = 0) -> int:
        self.pos = off if whence == 0 else (self.pos + off if whence == 1 else self.total + off)
        return self.pos

    def tell(self) -> int:
        return self.pos

    def seekable(self) -> bool:
        return True

    def read(self, n: int = -1) -> bytes:
        if n is None or n < 0:
            n = self.total - self.pos
        end = min(self.pos + n, self.total) - 1
        if end < self.pos:
            return b""
        r = self.s.get(self.url, headers={**_UA, "Range": f"bytes={self.pos}-{end}"}, timeout=90)
        r.raise_for_status()
        data = r.content
        self.pos += len(data)
        return data


@dataclass
class FetchResult:
    insee: str
    idurba_attendu: str
    idurba_gpu: str
    garde_ok: bool
    doc_id: str
    url_api: str
    url_archive: str
    fetched_at: str
    entries: list[dict] = field(default_factory=list)   # [{name, path, bytes, sha256}]


def gpu_documents(insee: str, session: requests.Session | None = None) -> list[dict]:
    """La liste des documents d'urbanisme GPU pour cette commune (grid = INSEE)."""
    s = session or requests.Session()
    r = s.get(f"{_GPU}/api/document", params={"grid": insee}, headers=_UA, timeout=60)
    r.raise_for_status()
    return r.json()


def _norm(idurba: str | None) -> str:
    return (idurba or "").strip().lower()


def _resolve_archive(doc_id: str, name: str, session: requests.Session) -> tuple[str, int]:
    """Suit la redirection vers data.geopf.fr et renvoie (url_réelle, taille totale)."""
    dl = f"{_GPU}/api/document/{doc_id}/download/{name}.zip"
    h = session.head(dl, headers=_UA, allow_redirects=True, timeout=60)
    h.raise_for_status()
    total = int(h.headers.get("content-length") or 0)
    if h.headers.get("accept-ranges") != "bytes" or not total:
        raise RuntimeError(f"archive non rangeable ({name}) : accept-ranges="
                           f"{h.headers.get('accept-ranges')} len={total}")
    return h.url, total


def _is_reglement_ecrit(path: str, insee: str) -> bool:
    """L'entrée ZIP est-elle le RÈGLEMENT ÉCRIT (le texte) ? On EXIGE le préfixe INSEE + « reglement »
    (`97415_reglement_20251217.pdf`) et on écarte les plans SECTORIELS graphiques qui contiennent aussi
    « reglement » mais SANS préfixe INSEE (`REGLEMENTAIRE_P4_5000_A0_BOUCAN_…`), les cartes, zonages,
    prescriptions surfaciques. On ne veut QUE la pièce écrite."""
    name = path.lower().rsplit("/", 1)[-1]
    if not name.endswith(".pdf"):
        return False
    if not re.match(rf"^{re.escape(insee)}_r[eè]glement", name):
        return False
    return not any(x in name for x in ("graphique", "zonage", "plan", "prescription",
                                        "surf", "_sup", "_a0_", "_a1_"))


def fetch_reglement(insee: str, idurba_attendu: str, dest_dir: str,
                    session: requests.Session | None = None, log=print) -> FetchResult:
    """Récupère le(s) PDF de règlement ÉCRIT opposable de la commune, GARDE D'IDENTITÉ en tête.
    Lève IdurbaMismatch si aucun document GPU ne porte l'idurba attendu (→ STOP appelant)."""
    import os
    s = session or requests.Session()
    docs = gpu_documents(insee, s)
    # garde d'identité : un document dont originalName == idurba attendu (M40)
    match = next((d for d in docs if _norm(d.get("originalName")) == _norm(idurba_attendu)), None)
    if match is None:
        got = ", ".join(f"{d.get('originalName')}({d.get('effectiveStatus')})" for d in docs) or "aucun"
        raise IdurbaMismatch(
            f"{insee} : idurba attendu « {idurba_attendu} » ABSENT du GPU. Documents servis : {got}. "
            f"STOP — règlement non réconcilié, on ne sert pas.")
    idurba_gpu = match["originalName"]
    doc_id = match["id"]
    fetched_at = _dt.datetime.now(_dt.timezone.utc).isoformat(timespec="seconds")
    real_url, total = _resolve_archive(doc_id, idurba_gpu, s)

    os.makedirs(dest_dir, exist_ok=True)
    entries: list[dict] = []
    with zipfile.ZipFile(_RangeReader(real_url, s, total)) as zf:
        cands = [n for n in zf.namelist() if _is_reglement_ecrit(n, insee)]
        if len(cands) > 1:
            # plusieurs règlements écrits (ex. Petite-Île : 2017 + 2023) → garder l'OPPOSABLE,
            # celui daté comme l'idurba (les 8 chiffres de fin) ; sinon on garde tout (et on le dit).
            m = re.search(r"(\d{8})(?!.*\d{8})", idurba_gpu)
            # match sur le NOM DE FICHIER seul — le dossier racine de l'archive porte l'idurba daté
            # (97405_PLU_20230609/…), sinon un règlement 2017 « contient » aussi la date via son chemin.
            dated = [n for n in cands if m and m.group(1) in n.rsplit("/", 1)[-1]]
            if dated:
                cands = dated
        if not cands:
            raise RuntimeError(f"{insee} : aucune pièce « règlement écrit » dans l'archive "
                               f"(entrées 3_Reglement : {[n for n in zf.namelist() if '3_Reglement' in n]})")
        for n in cands:
            data = zf.read(n)                      # Range : ne tire que cette entrée
            base = n.rsplit("/", 1)[-1]
            out = os.path.join(dest_dir, base)
            with open(out, "wb") as f:
                f.write(data)
            sha = hashlib.sha256(data).hexdigest()
            entries.append({"name": base, "path": out, "bytes": len(data), "sha256": sha})
            log(f"  ✓ {insee} {base} — {len(data)//1024} Ko — sha {sha[:12]}")
    return FetchResult(insee=insee, idurba_attendu=idurba_attendu, idurba_gpu=idurba_gpu,
                       garde_ok=True, doc_id=doc_id, url_api=f"{_GPU}/api/document?grid={insee}",
                       url_archive=real_url, fetched_at=fetched_at, entries=entries)
