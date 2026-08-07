"""M51-P1a — Récupère le règlement écrit opposable de CHAQUE commune non-RNU depuis le GPU, avec
garde d'identité (idurba téléchargé == idurba M40). Écrit un manifeste de provenance (URL, date,
sha256, idurba). STOP au moindre écart d'idurba : les communes non réconciliées sont LISTÉES et
NON servies (le batch collecte tout, puis on décide de l'ingestion).

    PYTHONPATH=src /Users/openclaw/Desktop/labuse/.venv/bin/python scripts/m51_fetch_corpus.py
"""
import glob
import json
import os
import sys
import time

import requests
import yaml
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

sys.path.insert(0, "src")
from labuse.ingestion import plu_corpus  # noqa: E402

DEST = "data/plu_reglements"
MANIFEST = "qa/m51/corpus_manifest.json"
DELAY = 6           # politesse anti-429 entre communes (data.geopf.fr rate-limite)

mil = yaml.safe_load(open("config/plu_millesimes.yaml"))["communes"]
session = requests.Session()
# retry avec backoff sur 429/5xx (respecte Retry-After) — la lecture ZIP fait plusieurs requêtes Range
_retry = Retry(total=6, backoff_factor=3, status_forcelist=[429, 500, 502, 503, 504],
               allowed_methods=["GET", "HEAD"], respect_retry_after_header=True)
session.mount("https://", HTTPAdapter(max_retries=_retry))

ok, mismatch, err = [], [], []
for insee in sorted(mil):
    c = mil[insee]
    if c["statut"] == "rnu" or not c.get("idurba"):
        print(f"— {insee} {c['commune']} : RNU / pas d'idurba → hors corpus (dit dans l'outil)")
        continue
    try:
        time.sleep(DELAY)
        r = plu_corpus.fetch_reglement(insee, c["idurba"], DEST, session=session, log=print)
        ok.append({
            "insee": insee, "commune": c["commune"], "statut": c["statut"],
            "idurba_attendu": r.idurba_attendu, "idurba_gpu": r.idurba_gpu, "garde_ok": r.garde_ok,
            "doc_id": r.doc_id, "url_api": r.url_api, "url_archive": r.url_archive,
            "fetched_at": r.fetched_at, "entries": r.entries,
        })
    except plu_corpus.IdurbaMismatch as e:
        print(f"⚠ STOP-écart {insee} {c['commune']} : {e}")
        mismatch.append({"insee": insee, "commune": c["commune"], "idurba_attendu": c["idurba"],
                         "erreur": str(e)})
    except Exception as e:   # noqa: BLE001
        print(f"✗ ERREUR {insee} {c['commune']} : {type(e).__name__}: {str(e)[:200]}")
        err.append({"insee": insee, "commune": c["commune"], "erreur": f"{type(e).__name__}: {str(e)[:200]}"})

os.makedirs(os.path.dirname(MANIFEST), exist_ok=True)
json.dump({"ok": ok, "ecart_idurba": mismatch, "erreurs": err}, open(MANIFEST, "w"),
          ensure_ascii=False, indent=2)
print(f"\n=== BILAN FETCH : {len(ok)} servables · {len(mismatch)} écart idurba (NON servis) · "
      f"{len(err)} erreurs · manifeste {MANIFEST}")
if mismatch:
    print("ÉCARTS IDURBA (à réconcilier, arbitrage Vic) :", [m["insee"] for m in mismatch])
print("FETCH_DONE")
