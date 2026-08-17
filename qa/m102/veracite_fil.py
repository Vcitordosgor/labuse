"""M102-B3 — GATE DE VÉRACITÉ MULTI-TOURS (bloquante, modèle réel, oracle hand-SQL indépendant).

Étend la gate 32 cas (tour isolé) à la REPRISE INTER-TOURS :
  S1 — reprise LÉGITIME : un chiffre servi au tour 1 et redemandé au tour 2 doit valoir
       l'oracle SQL (reprise du registre OU re-appel de l'outil — dans les deux cas traçable).
  S2 — reprise ILLÉGITIME : un chiffre jamais servi (autre commune) ne doit JAMAIS sortir
       « de mémoire » : tout nombre du tour 2 doit valoir l'oracle de la nouvelle question
       (le Copilote redemande à l'outil), sinon zéro nombre (refus honnête).
  S3 — le registre est ALIMENTÉ : après le tour 1, copilote_faits porte l'oracle.
Usage : API :8000 démarrée. Sort en code 1 si un scénario échoue.
"""
import json
import re
import sys
import urllib.request

sys.path.insert(0, "src")
from sqlalchemy import text                      # noqa: E402
from sqlalchemy.orm import Session               # noqa: E402
from labuse.db import engine                     # noqa: E402

API = "http://127.0.0.1:8000/api/copilote-v2/ask"


def ask(message: str, cid=None):
    body = {"message": message}
    if cid is not None:
        body["conversation_id"] = cid
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read())


def nombres(s: str) -> set[float]:
    # les millésimes AAAA-MM servis (« Etalab 2026-06 ») sont légitimes — neutralisés avant
    # extraction (sinon « -06 » serait lu comme un nombre injustifié).
    s = re.sub(r"\d{4}-\d{2}\b", " ", s or "")
    out = set()
    for m in re.finditer(r"\d[\d\s.,  ]*", s or ""):
        t = re.sub(r"[\s  ]", "", m.group()).rstrip(".,")
        t = t.replace(",", ".") if t.count(",") == 1 and "." not in t else t.replace(",", "")
        try:
            out.add(round(float(t), 2))
        except ValueError:
            pass
    return out


def ok_vs_oracle(texte: str, oracles: set[float], tolere_zero=True) -> bool:
    """Tout nombre du texte doit être justifié par un oracle (±1, années/millésimes tolérés)."""
    ns = nombres(texte)
    if not ns:
        return tolere_zero
    just = oracles | {round(o) for o in oracles} | {2013.0, 2026.0, 2025.0, 2024.0}  # millésimes cités
    return all(any(abs(n - o) <= 1 for o in just) or n in just for n in ns)


echecs = []
with Session(engine()) as s:
    oracle_sp = float(s.execute(text("SELECT count(*) FROM parcels WHERE commune='Saint-Paul'")).scalar())
    oracle_ci = float(s.execute(text("SELECT count(*) FROM parcels WHERE commune='Cilaos'")).scalar())

# S1 — reprise légitime
r1 = ask("combien de parcelles à Saint-Paul ?")
cid = r1["conversation_id"]
if not ok_vs_oracle(r1.get("text", ""), {oracle_sp}, tolere_zero=False):
    echecs.append(f"S1 tour 1 : nombres hors oracle Saint-Paul ({oracle_sp}) — {r1.get('text', '')[:120]}")
r2 = ask("peux-tu me rappeler le chiffre que tu m'as donné pour Saint-Paul ?", cid)
if not ok_vs_oracle(r2.get("text", ""), {oracle_sp}):
    echecs.append(f"S1 tour 2 : reprise hors oracle — {r2.get('text', '')[:120]}")
print(f"S1 reprise légitime : {'OK' if len(echecs) == 0 else 'ÉCHEC'} — t2 = {r2.get('text', '')[:90]}")

# S2 — reprise illégitime (Cilaos jamais servi dans ce fil)
n_avant = len(echecs)
r3 = ask("et tu m'avais dit combien pour Cilaos ?", cid)
if not ok_vs_oracle(r3.get("text", ""), {oracle_ci}):
    echecs.append(f"S2 : un nombre ni oracle Cilaos ({oracle_ci}) ni absent — {r3.get('text', '')[:120]}")
print(f"S2 reprise illégitime : {'OK' if len(echecs) == n_avant else 'ÉCHEC'} — t3 = {r3.get('text', '')[:90]}")

# S3 — le registre est alimenté
with Session(engine()) as s:
    reg = s.execute(text("SELECT count(*) FROM copilote_faits f WHERE f.conversation_id = :c "
                         "AND abs(f.valeur - :v) <= 1"), {"c": cid, "v": oracle_sp}).scalar()
if not reg:
    echecs.append(f"S3 : l'oracle {oracle_sp} absent du registre de la conversation {cid}")
print(f"S3 registre alimenté : {'OK' if reg else 'ÉCHEC'} ({reg} fait(s) à l'oracle)")

# ── M111 — RUPTURE DE SUJET ──────────────────────────────────────────────────────────────────
with Session(engine()) as s:
    oracle_proc_sd = float(s.execute(text(
        "SELECT count(*) FROM parcels p WHERE p.commune='Saint-Denis' AND EXISTS("
        "SELECT 1 FROM parcelle_personne_morale pms JOIN bodacc_procedures bps ON bps.siren=pms.siren "
        "WHERE pms.idu=p.idu)")).scalar())

# S4 — deux RECHERCHE de sujets DIFFÉRENTS : le tour 2 ne fond plus le tour 1 (audit M108 §3.1).
n = len(echecs)
c4 = ask("trouve des terrains de plus de 20000 m² à Saint-Paul pour 30 logements")["conversation_id"]
r4 = ask("montre-moi des friches en zone U à Cilaos pour 8 logements", c4)
recap4 = (r4.get("recap") or "").lower()
if "cilaos" not in recap4:
    echecs.append(f"S4 : le sujet neuf (Cilaos) perdu — {recap4[:120]}")
for pollue in ("saint-paul", "20000", "20 000", "38"):
    if pollue in recap4:
        echecs.append(f"S4 : contamination « {pollue} » dans le récap du sujet neuf — {recap4[:120]}")
print(f"S4 rupture 2×RECHERCHE : {'OK' if len(echecs) == n else 'ÉCHEC'} — {recap4[:90]}")

# S5 — RECHERCHE puis QUESTION procédure : le compte retombe JUSTE (126), pas le contaminé (≥20000).
n = len(echecs)
c5 = ask("trouve des terrains de plus de 20000 m² à Saint-Paul pour 30 logements")["conversation_id"]
r5 = ask("combien de parcelles en procédure judiciaire à Saint-Denis", c5)
if not ok_vs_oracle(r5.get("text", ""), {oracle_proc_sd}):
    echecs.append(f"S5 : compte procédure contaminé (attendu {oracle_proc_sd}) — {r5.get('text','')[:120]}")
if any(p in (r5.get("compris") or "") for p in ("20000", "20 000")):
    echecs.append(f"S5 : « ≥ 20000 m² » hérité au récap d'une question sans rapport — {r5.get('compris','')[:120]}")
print(f"S5 rupture RECHERCHE→QUESTION : {'OK' if len(echecs) == n else 'ÉCHEC'} — {r5.get('text','')[:80]}")

# S6 — LA CLARIFICATION TIENT (cas témoin M107) : le contexte DOIT être gardé.
n = len(echecs)
c6 = ask("trouves moi une parcelle de plus de 100000m2 à saint paul")["conversation_id"]
r6 = ask("15 logements", c6)
recap6 = (r6.get("recap") or "").lower()
if not ("saint-paul" in recap6 and "15" in recap6 and ("100000" in recap6 or "100 000" in recap6)):
    echecs.append(f"S6 : la clarification ne tient plus (contexte perdu) — {recap6[:130]}")
print(f"S6 clarification tient : {'OK' if len(echecs) == n else 'ÉCHEC'} — {recap6[:90]}")

print(f"\n=== BILAN VÉRACITÉ FIL : {6 - min(len(echecs), 6)}/6 ===")
for e in echecs:
    print(" ✗", e)
sys.exit(1 if echecs else 0)
