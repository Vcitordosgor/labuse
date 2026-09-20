#!/usr/bin/env python3
"""Harness d'audit COPILOTE-AUDIT-1 — pose une liste de questions au Copilote v2 et enregistre
la réponse brute + un extrait lisible. Lecture seule côté audit (le Copilote écrit son ia_log/historique
comme en prod, inhérent au test)."""
import json, sys, time, urllib.request

BASE = "http://127.0.0.1:8085"

def ask(message, contexte=None, conversation_id=None):
    body = {"message": message}
    if contexte: body["contexte"] = contexte
    if conversation_id: body["conversation_id"] = conversation_id
    data = json.dumps(body).encode()
    req = urllib.request.Request(BASE + "/api/copilote-v2/ask", data=data,
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=120) as r:
        out = json.load(r)
    out["_ms"] = int((time.time()-t0)*1000)
    return out

def run(tag, questions):
    results = []
    for i, q in enumerate(questions, 1):
        msg = q["m"]; ctx = q.get("ctx")
        try:
            r = ask(msg, contexte=ctx)
        except Exception as e:
            r = {"error": str(e)}
        rec = {"n": i, "q": msg, "ctx": ctx,
               "intent": r.get("intent"), "text": r.get("text"),
               "voie": r.get("voie"), "ms": r.get("_ms"),
               "full": r}
        results.append(rec)
        print(f"\n[{tag} {i}] Q: {msg}")
        print(f"    intent={r.get('intent')} voie={r.get('voie')} ms={r.get('_ms')}")
        txt = (r.get("text") or r.get("error") or "")[:700]
        print(f"    A: {txt}")
        sys.stdout.flush()
        time.sleep(0.5)
    json.dump(results, open(f"captures/copilote-audit1/{tag}.json","w"),
              ensure_ascii=False, indent=2)
    return results

if __name__ == "__main__":
    import importlib.util
    spec = sys.argv[1]
    QS = json.load(open(spec))
    run(QS["tag"], QS["questions"])
