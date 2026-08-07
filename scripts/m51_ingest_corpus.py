"""M51-P1b — Ingestion du corpus fetché (manifeste) en extraits article FTS. Idempotent."""
import json
import sys

import yaml
from sqlalchemy import text

sys.path.insert(0, "src")
from labuse.db import session_factory          # noqa: E402
from labuse.ingestion import plu_ingest        # noqa: E402

mil = yaml.safe_load(open("config/plu_millesimes.yaml"))["communes"]
man = json.load(open("qa/m51/corpus_manifest.json"))
s = session_factory()()
plu_ingest.ensure_ddl(s)
s.commit()

total = 0
for o in man["ok"]:
    ins = o["insee"]
    for e in o["entries"]:
        r = plu_ingest.ingest_reglement(
            s, insee=ins, commune=o["commune"], idurba=o["idurba_gpu"],
            millesime=mil[ins].get("date_mairie"), document=e["name"], pdf_path=e["path"],
            source_url=o["url_archive"], fetched_at=o["fetched_at"], commit=True, log=print)
        total += r["extraits"]

n_comm = s.execute(text("SELECT count(DISTINCT insee) FROM plu_reglement_extrait")).scalar()
amb = s.execute(text("SELECT bool_or(pagination_ambigue) FROM plu_reglement_extrait WHERE insee='97410'")).scalar()
n_doute = s.execute(text("SELECT count(*) FROM plu_reglement_extrait WHERE doute")).scalar()
print(f"\n=== {total} extraits · {n_comm} communes · Saint-Benoît pagination_ambigue={amb} · {n_doute} douteux")
s.close()
print("INGEST_DONE")
