"""Runner nommé (killable) pour V7a — COUCHES-TUYAU-1 lot 3."""
import time
from labuse.db import session_scope
from labuse import circuit_tuiles as ct

t0 = time.time()
with session_scope() as s:
    r = ct.verrou_tuiles(s)
print(f"\n=== V7a {r.verdict.upper()} in {time.time() - t0:.1f}s ===", flush=True)
print("preuve:", r.preuve, flush=True)
for d in r.details[:40]:
    print("  -", d, flush=True)
