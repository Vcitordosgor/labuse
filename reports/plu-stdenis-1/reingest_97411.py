"""PLU-STDENIS-1 — ré-ingestion CIBLÉE du règlement-texte de Saint-Denis (97411) au millésime
20260805, par le chemin d'ingestion EXISTANT (plu_corpus.fetch_reglement + plu_ingest.ingest_reglement).
Garde-fou 974 respecté (insee='97411' seulement). Aucun autre INSEE touché.
Le nom de document change (20260423 -> 20260805) => on SUPPRIME d'abord les extraits 97411 existants
pour que l'ancien millésime ne soit plus servi."""
import sys
sys.path.insert(0, "src")
from sqlalchemy import text                       # noqa: E402
from labuse.db import session_factory             # noqa: E402
from labuse.ingestion import plu_corpus, plu_ingest  # noqa: E402

INSEE = "97411"
COMMUNE = "Saint-Denis"
IDURBA = "97411_PLU_20260805"
MILLESIME = "2026-08-05"
DEST = "data/plu_reglements"

assert INSEE.startswith("974"), "garde-fou 974"

s = session_factory()()
plu_ingest.ensure_ddl(s)

# état AVANT
before = s.execute(text("SELECT min(idurba), count(*), string_agg(DISTINCT document, ',') "
                        "FROM plu_reglement_extrait WHERE insee=:i"), {"i": INSEE}).first()
print(f"AVANT 97411 : idurba={before[0]} extraits={before[1]} docs={before[2]}")

# 1) FETCH du règlement 20260805 (garde d'identité idurba)
r = plu_corpus.fetch_reglement(INSEE, IDURBA, DEST, log=print)
print(f"FETCH ok : idurba_gpu={r.idurba_gpu} garde_ok={r.garde_ok} entries={[e['name'] for e in r.entries]}")
assert r.garde_ok and r.idurba_gpu.lower() == IDURBA.lower(), "garde idurba KO"

# 2) SUPPRESSION des extraits 97411 existants (ancien millésime, nom de doc différent)
n_del = s.execute(text("DELETE FROM plu_reglement_extrait WHERE insee=:i"), {"i": INSEE}).rowcount
s.commit()
print(f"SUPPRIME {n_del} extraits 97411 (ancien 20260423)")

# 3) INGESTION du nouveau règlement
total = 0
for e in r.entries:
    res = plu_ingest.ingest_reglement(
        s, insee=INSEE, commune=COMMUNE, idurba=r.idurba_gpu, millesime=MILLESIME,
        document=e["name"], pdf_path=e["path"], source_url=r.url_archive,
        fetched_at=r.fetched_at, commit=True, log=print)
    total += res["extraits"]
print(f"INGERE {total} extraits pour {r.idurba_gpu}")

# état APRÈS
after = s.execute(text("SELECT min(idurba), max(to_char(millesime,'YYYY-MM-DD')), count(*), "
                       "min(source_url), string_agg(DISTINCT document, ',') "
                       "FROM plu_reglement_extrait WHERE insee=:i"), {"i": INSEE}).first()
print(f"APRÈS 97411 : idurba={after[0]} millesime={after[1]} extraits={after[2]}")
print(f"            source_url={after[3]}")
print(f"            docs={after[4]}")

# garde-fou : aucune autre commune touchée (compte global inchangé hors 97411)
n_comm = s.execute(text("SELECT count(DISTINCT insee) FROM plu_reglement_extrait")).scalar()
print(f"communes distinctes dans le corpus : {n_comm}")
s.close()
print("REINGEST_DONE")
