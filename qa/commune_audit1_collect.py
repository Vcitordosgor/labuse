"""COMMUNE-AUDIT-1 — collecte lecture seule : le payload servi de /communes/{c}/contexte pour les 24
communes, via TestClient (exacte logique d'endpoint : cache + rafraîchissement live). Écrit un JSON."""
import json, sys
from fastapi.testclient import TestClient
from labuse import communes
from labuse.api.app import app

client = TestClient(app)
out = {}
for nom in sorted(communes.load_communes().keys()):
    r = client.get(f"/communes/{nom}/contexte")
    out[nom] = {"status": r.status_code, "payload": r.json() if r.status_code == 200 else None}
    print(nom, r.status_code, file=sys.stderr)
with open("qa/commune_audit1_payloads.json", "w") as f:
    json.dump(out, f, ensure_ascii=False, indent=1)
print("WROTE qa/commune_audit1_payloads.json", file=sys.stderr)
