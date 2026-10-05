"""CHASSE-3 angle 1 — usage simultané : 10 clients virtuels × 10 min sur le BUILD.

Protocole (leçon AD0554 : un écart qui n'apparaît que sous charge = DISCORDANT) :
  A. baseline SOLO : chaque requête canonique jouée seule, corps normalisé + hash ;
  B. CHARGE : 10 workers bouclent 10 min sur le mix réel (fiches, filtres, PDF,
     Copilote, tuiles) ; chaque réponse → statut, durée, et pour les requêtes
     canoniques le corps re-hashé et comparé à la baseline EN DIRECT ;
  C. re-mesure SOLO post-charge (l'état n'a pas dérivé).

Verdicts écrits dans docs/audit-2026-10/CHASSE-3/CHARGE.csv (une ligne par anomalie)
+ CHARGE_P95.csv (temps de réponse par famille). 0 écriture hors CHASSE-3/.

Rejouable :  LABUSE_CHASSE3_API=http://127.0.0.1:6015 python -m scripts.chasse.charge3
  (durée réglable : LABUSE_CHASSE3_DUREE_S, défaut 600 ; clients : LABUSE_CHASSE3_CLIENTS=10)
"""
from __future__ import annotations

import concurrent.futures as cf
import csv
import hashlib
import json
import os
import random
import re
import time
import urllib.request
import urllib.error
from pathlib import Path

BASE = os.environ.get("LABUSE_CHASSE3_API", "http://127.0.0.1:6015")
DUREE_S = int(os.environ.get("LABUSE_CHASSE3_DUREE_S", "600"))
N_CLIENTS = int(os.environ.get("LABUSE_CHASSE3_CLIENTS", "10"))
OUT = Path(__file__).resolve().parents[2] / "docs" / "audit-2026-10" / "CHASSE-3"
OUT.mkdir(parents=True, exist_ok=True)

# ── requêtes canoniques (corps comparé solo vs charge vs post-charge) ──────────
# Parcelles réelles stables (témoins des audits précédents + tirage AD StDenis).
IDUS = ["97401000AD0069", "97401000AD0077", "97401000AD0091",
        "97411000BZ1065", "97415000ES0266", "97402000AB1117"]
CANON = (
    [("fiche", f"/parcels/{i}") for i in IDUS]
    + [("enrichment", f"/parcels/{i}/enrichment") for i in IDUS]
    + [("filtre", "/filtre?source=q_v16&commune=Saint-Paul"),
       ("filtre", "/filtre?source=q_v16&commune=Saint-Denis&limit=50"),
       ("filtre", "/filtre?source=q_v16"),
       ("marche", "/moteurs/marche/Saint-Paul"),
       ("marche", "/moteurs/marche/Bras-Panon"),
       ("tuile", "/map/tiles/12/2678/2292.pbf"),
       ("tuile", "/map/tiles/13/5357/4585.pbf"),
       ("tuile", "/map/tiles/14/10714/9170.pbf")]
)
PDF = [("pdf", f"/dossier/{IDUS[0]}.pdf"), ("pdf", f"/gabarit/{IDUS[3]}.pdf"),
       ("pdf", f"/apporteur/{IDUS[1]}.pdf")]
COPILOTE_Q = ["terrain nu de plus de 1000 m² en zone U à Saint-Paul",
              "que puis-je construire sur la parcelle 97411000BZ1065 ?",
              "prix du neuf à Saint-Denis"]

# clés volatiles retirées avant hachage (horodatages, ids de session, TTL de cache)
_VOLATILE = re.compile(r"(_at$|^at_|date|heure|timestamp|conversation_id|ttl|duree|"
                       r"elapsed|cache|request_id|trace)", re.I)


def _normalise(obj):
    if isinstance(obj, dict):
        return {k: _normalise(v) for k, v in sorted(obj.items()) if not _VOLATILE.search(k)}
    if isinstance(obj, list):
        return [_normalise(v) for v in obj]
    return obj


def _hash_body(fam: str, body: bytes) -> str:
    if fam == "pdf":
        # le contenu binaire varie (date de création incluse) : on vérifie l'intégrité
        # (en-tête + trailer) et l'ordre de grandeur ; l'égalité des CHIFFRES est
        # l'affaire de l'angle 5 (texte extrait).
        ok = body.startswith(b"%PDF") and b"%%EOF" in body[-2048:]
        return f"pdf:{'ok' if ok else 'INCOMPLET'}:{len(body) // 4096}"  # taille à 4 Ko près
    if fam == "tuile":
        return f"tuile:{hashlib.sha256(body).hexdigest()[:16]}"
    try:
        data = json.loads(body)
    except Exception:
        return "brut:" + hashlib.sha256(body).hexdigest()[:16]
    canon = json.dumps(_normalise(data), ensure_ascii=False, sort_keys=True)
    return "json:" + hashlib.sha256(canon.encode()).hexdigest()[:16]


def _get(path: str, timeout: float = 180.0, post_json: dict | None = None):
    t0 = time.monotonic()
    req = urllib.request.Request(BASE + path)
    if post_json is not None:
        req.data = json.dumps(post_json).encode()
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            body = r.read()
            return r.status, time.monotonic() - t0, body
    except urllib.error.HTTPError as e:
        return e.code, time.monotonic() - t0, e.read()
    except Exception as e:  # réseau/timeout : statut 0, le motif dans le corps
        return 0, time.monotonic() - t0, str(e).encode()


def jouer_canon(tag: str) -> dict[str, str]:
    """Joue toutes les requêtes canoniques en SÉQUENTIEL, retourne {path: hash}."""
    hashes: dict[str, str] = {}
    for fam, path in CANON + PDF:
        code, dt, body = _get(path)
        hashes[path] = f"{code}|{_hash_body(fam, body)}"
        print(f"  [{tag}] {code} {dt:6.2f}s {fam:<11} {path}")
    return hashes


def client(worker_id: int, fin: float, baseline: dict[str, str], sink: list):
    rng = random.Random(1000 + worker_id)
    mix = (CANON * 3) + PDF + [("copilote", q) for q in COPILOTE_Q]
    while time.monotonic() < fin:
        fam, path = rng.choice(mix)
        if fam == "copilote":
            code, dt, body = _get("/api/copilote-v2/ask", post_json={"message": path})
            sink.append((fam, "/api/copilote-v2/ask", code, dt, ""))
            continue
        code, dt, body = _get(path)
        anomalie = ""
        if code >= 500 or code == 0:
            anomalie = f"statut {code}: {body[:120]!r}"
        elif path in baseline:
            h = f"{code}|{_hash_body(fam, body)}"
            if h != baseline[path]:
                anomalie = f"corps différent sous charge: {h} vs baseline {baseline[path]}"
        if fam == "pdf" and b"INCOMPLET" in str(_hash_body(fam, body)).encode():
            anomalie = (anomalie + " | " if anomalie else "") + "PDF incomplet servi"
        sink.append((fam, path, code, dt, anomalie))


def main() -> None:
    print(f"CHASSE-3 charge — {N_CLIENTS} clients × {DUREE_S}s sur {BASE}")
    print("— baseline solo (A) :")
    baseline = jouer_canon("solo-avant")

    print(f"— charge (B) : {N_CLIENTS} clients, {DUREE_S}s…")
    fin = time.monotonic() + DUREE_S
    sinks: list[list] = [[] for _ in range(N_CLIENTS)]
    with cf.ThreadPoolExecutor(max_workers=N_CLIENTS) as ex:
        futs = [ex.submit(client, i, fin, baseline, sinks[i]) for i in range(N_CLIENTS)]
        for f in futs:
            f.result()

    print("— re-mesure solo (C) :")
    apres = jouer_canon("solo-après")

    # ── dépouillement ──────────────────────────────────────────────────────────
    lignes = [l for s in sinks for l in s]
    anomalies = [l for l in lignes if l[4]]
    derives = [(p, baseline[p], apres[p]) for p in baseline if apres.get(p) != baseline[p]]

    with (OUT / "CHARGE.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["phase", "famille", "chemin", "statut", "duree_s", "anomalie"])
        for fam, path, code, dt, ano in anomalies:
            w.writerow(["charge", fam, path, code, f"{dt:.2f}", ano])
        for p, h0, h1 in derives:
            w.writerow(["post-charge", "", p, "", "", f"corps a DÉRIVÉ après charge: {h0} → {h1}"])

    with (OUT / "CHARGE_P95.csv").open("w", newline="") as f:
        w = csv.writer(f)
        w.writerow(["famille", "n", "p50_s", "p95_s", "max_s", "n_5xx", "n_timeout"])
        familles = sorted({l[0] for l in lignes})
        for fam in familles:
            ds = sorted(l[3] for l in lignes if l[0] == fam)
            n5 = sum(1 for l in lignes if l[0] == fam and l[2] >= 500)
            n0 = sum(1 for l in lignes if l[0] == fam and l[2] == 0)
            w.writerow([fam, len(ds), f"{ds[len(ds)//2]:.2f}",
                        f"{ds[int(len(ds)*0.95)]:.2f}", f"{ds[-1]:.2f}", n5, n0])

    print(f"\n{len(lignes)} requêtes jouées · {len(anomalies)} anomalie(s) sous charge · "
          f"{len(derives)} dérive(s) post-charge → {OUT}/CHARGE.csv + CHARGE_P95.csv")


if __name__ == "__main__":
    main()
