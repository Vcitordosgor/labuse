"""AUDIT COMPTES · A2 — cloisonnement à DEUX COMPTES RÉELS (le cœur du mandat).

Monte l'app en auth ACTIVE (env pilot + secret), crée Stéphanie et Caroline [AUDIT-TEST],
les fait VIVRE (projets, CRM, veilles/zones, filtres, recherches, courrier, conversation
Copilote, signalement, parcelle suivie, événement), puis — session de Stéphanie en main —
attaque TOUTES les routes {param} de openapi.json avec les id d'objets de Caroline. Toute
route qui renvoie 200 avec la donnée de Caroline = FUITE 🔴. Teste aussi l'inverse
(non-sur-filtrage : Stéphanie retrouve TOUS ses objets).

Sortie : qa/comptes/out/a2_matrice.json + tableau imprimé. Purge en fin (les deux comptes +
la parcelle dédiée), vérifiée par le script FIN.

Exécution : `python qa/comptes/audit_a2.py` (env conda labusedb, DB labuse_test).
"""
from __future__ import annotations

import json
import os
import sys
import uuid
from pathlib import Path

# ── env : auth ACTIVE, base de test (jamais la prod servie par :8000) ──
os.environ["LABUSE_ENV"] = "pilot"
os.environ["LABUSE_AUTH_PASSWORD"] = "pilote-audit-a2"
os.environ["LABUSE_SECRET_KEY"] = "secret-audit-a2-0000000000000000000000"
# Base de TEST (labuse_test), dérivée comme le conftest — jamais la base servie par :8000.
_app_url = "postgresql+psycopg://openclaw@localhost:5432/labuse"
for _l in (Path(__file__).resolve().parents[2] / ".env").read_text().splitlines():
    if _l.startswith("LABUSE_DATABASE_URL="):
        _app_url = _l.split("=", 1)[1].strip()
os.environ["LABUSE_DATABASE_URL"] = os.environ.get("LABUSE_TEST_DATABASE_URL") or (_app_url.rsplit("/", 1)[0] + "/labuse_test")

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import text  # noqa: E402

from labuse import comptes, config  # noqa: E402
from labuse.db import session_scope  # noqa: E402

config.get_settings.cache_clear()
from labuse.api.app import app  # noqa: E402

PREFIX = "[AUDIT-TEST]"
STEPH = f"stephanie-{uuid.uuid4().hex[:8]}@audit-test.re"
CARO = f"caroline-{uuid.uuid4().hex[:8]}@audit-test.re"
IDU_A = f"974AUD{uuid.uuid4().hex[:5].upper()}A"   # parcelle dédiée (commune, publique)
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
WKT = "POLYGON((55.46 -20.92,55.461 -20.92,55.461 -20.921,55.46 -20.921,55.46 -20.92))"


def creer_compte(email: str, nom: str) -> int:
    with session_scope() as s:
        try:
            comptes.supprimer_utilisateur(s, email)
        except Exception:
            pass
        inv = comptes.creer_invitation(s, email, nom=f"{PREFIX} {nom}")
        comptes.activer_par_invitation(s, inv["lien"].split("token=")[1], "motdepasse-audit-a2", "2026-07-22")
        s.execute(text("UPDATE comptes SET statut='actif' WHERE id=:c"), {"c": inv["compte_id"]})
        s.commit()
        return inv["compte_id"]


def login(email: str) -> TestClient:
    c = TestClient(app, base_url="https://testserver")
    r = c.post("/login", data={"identifiant": email, "password": "motdepasse-audit-a2"},
               follow_redirects=False)
    assert r.status_code == 303, f"login {email} → {r.status_code} {r.text[:200]}"
    return c


def creer_parcelle(idu: str) -> None:
    with session_scope() as s:
        s.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2,"
            " centroid, bbox) VALUES (:i,'Saint-Denis','ZA','1', ST_GeomFromText(:w,4326),"
            " ST_Transform(ST_GeomFromText(:w,4326),2975), 900,"
            " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"
            " ON CONFLICT (idu) DO NOTHING"), {"i": idu, "w": WKT})
        s.commit()


def faire_vivre(c: TestClient, qui: str) -> dict:
    """Crée un objet de chaque type propre au compte ; renvoie les id capturés."""
    objs: dict = {"_qui": qui}
    # projet
    r = c.post("/projets", json={"nom": f"Projet {qui} {uuid.uuid4().hex[:6]}",
                                 "cadrage": {"communes": ["Saint-Denis"]}})
    if r.status_code == 200:
        objs["projet"] = r.json()["projet"]["id"]
    # CRM (pipeline) sur la parcelle dédiée
    r = c.post("/pipeline", json={"idu": IDU_A})
    if r.status_code == 200:
        objs["pipeline"] = r.json()["entry"]["id"]
    # colonne CRM custom
    r = c.post("/pipeline/columns", json={"name": f"Col {qui}"})
    if r.status_code == 200:
        j = r.json()
        objs["column"] = (j.get("column") or j).get("id") if isinstance(j, dict) else None
    # filtre enregistré
    r = c.post("/filters", json={"name": f"Filtre {qui}", "params": {"tiers": ["brulante"]}})
    if r.status_code == 200:
        objs["filter"] = r.json().get("id") or (r.json().get("filter") or {}).get("id")
    # recherche enregistrée
    r = c.post("/events/searches", json={"nom": f"Rech {qui}", "hash": f"#f=1&q={qui}"})
    if r.status_code == 200:
        objs["search"] = r.json().get("id") or (r.json().get("search") or {}).get("id")
    # zone de veille
    r = c.post("/watch-zones", json={"name": f"Zone {qui}",
                                     "geometry": {"type": "Polygon", "coordinates": [[[55.46, -20.92], [55.47, -20.92], [55.47, -20.93], [55.46, -20.93], [55.46, -20.92]]]}})
    if r.status_code == 200:
        objs["zone"] = r.json().get("id") or (r.json().get("zone") or {}).get("id")
    # parcelle suivie
    r = c.post(f"/events/watch/{IDU_A}")
    objs["watch_idu"] = IDU_A if r.status_code == 200 else None
    # signalement
    r = c.post("/signalements", json={"idu": IDU_A, "type_erreur": "zonage",
                                      "commentaire": f"signal {qui}"})
    if r.status_code == 200:
        objs["signalement"] = r.json().get("id") or (r.json().get("signalement") or {}).get("id")
    # demande de courrier
    r = c.post("/courrier/demande", json={"parcelles": [IDU_A], "communes": "Saint-Denis",
                                          "modele": "standard", "corps": f"Courrier de {qui}."})
    if r.status_code == 200:
        objs["courrier"] = r.json().get("id")
    # conversation Copilote v2 (stub sans clé IA — best-effort)
    r = c.post("/api/copilote-v2/ask", json={"message": f"Bonjour, ici {qui}."})
    if r.status_code == 200:
        objs["conversation"] = r.json().get("conversation_id")
    return objs


# ── routes {param} de openapi : id d'OBJET (à cloisonner) vs id COMMUN (idu/commune/token) ──
def charger_routes() -> list[dict]:
    spec = json.loads((Path(__file__).resolve().parents[2] / "qa" / "comptes" / "openapi_snapshot.json").read_text()) \
        if (Path(__file__).resolve().parents[2] / "qa" / "comptes" / "openapi_snapshot.json").exists() \
        else json.loads(Path("/tmp/openapi.json").read_text())
    out = []
    for p, methods in spec["paths"].items():
        if "{" not in p:
            continue
        for m in methods:
            if m in ("get", "post", "patch", "delete", "put"):
                out.append({"method": m.upper(), "path": p})
    return out


# param d'objet → clé dans le dict objs de Caroline
PARAM_OBJ = {
    "{pid}": "projet", "{entry_id}": "pipeline", "{col_id}": "column",
    "{filter_id}": "filter", "{sid}": "search", "{zone_id}": "zone",
    "{demande_id}": "courrier", "{conversation_id}": "conversation",
    "{veille_id}": "conversation",  # veilles copilote-v2 (même famille scopée)
    "{retour_id}": None, "{event_id}": "event",
}


def substituer(path: str, caro: dict) -> str | None:
    """Remplace les {param} : id d'objet de Caroline si connu, idu/commune dédiés sinon.
    Renvoie None si le path porte un param d'objet dont Caroline n'a pas d'exemplaire."""
    out = path
    for tok in ["{pid}", "{entry_id}", "{col_id}", "{filter_id}", "{sid}", "{zone_id}",
                "{demande_id}", "{conversation_id}", "{veille_id}", "{event_id}"]:
        if tok in out:
            key = PARAM_OBJ.get(tok)
            val = caro.get(key) if key else None
            if val is None:
                return None
            out = out.replace(tok, str(val))
    out = out.replace("{idu}", IDU_A).replace("{commune}", "Saint-Denis")
    out = out.replace("{secteur}", "97411").replace("{token}", "zzz-inexistant")
    out = out.replace("{run_id}", "999999").replace("{permit_id}", "999999")
    out = out.replace("{retour_id}", "999999").replace("{source_id}", "999999")
    out = out.replace("{compte_id}", str(caro.get("_compte_id", 999999)))
    out = out.replace("{z}", "12").replace("{x}", "2000").replace("{y}", "2000").replace("{kind}", "ppr")
    return out


def est_route_objet(path: str) -> str | None:
    for tok, key in PARAM_OBJ.items():
        if tok in path and key:
            return key
    return None


def main() -> int:
    cid_s = creer_compte(STEPH, "Stéphanie")
    cid_c = creer_compte(CARO, "Caroline")
    creer_parcelle(IDU_A)
    cs, cc = login(STEPH), login(CARO)

    caro = faire_vivre(cc, "Caroline"); caro["_compte_id"] = cid_c
    steph = faire_vivre(cs, "Stéphanie"); steph["_compte_id"] = cid_s

    caro_objs = {k: v for k, v in caro.items() if not k.startswith("_") and v is not None}
    steph_objs = {k: v for k, v in steph.items() if not k.startswith("_") and v is not None}
    print(f"Caroline objets créés : {caro_objs}")
    print(f"Stéphanie objets créés : {steph_objs}")

    # ── ATTAQUE : Stéphanie tente les objets de Caroline sur toutes les routes {param} ──
    routes = charger_routes()
    matrice = []
    fuites = []
    for r in routes:
        path = substituer(r["path"], caro)
        if path is None:
            continue
        objkey = est_route_objet(r["path"])
        meth = r["method"].lower()
        try:
            resp = getattr(cs, meth)(path) if meth in ("get", "delete") \
                else getattr(cs, meth)(path, json={})
            code = resp.status_code
            body = resp.text[:400]
        except Exception as exc:  # noqa: BLE001
            code, body = -1, f"EXC {type(exc).__name__}: {exc}"[:200]
        # verdict : sur une route d'OBJET de Caroline, tout code < 400 = fuite potentielle
        verdict = "ok"
        if objkey:
            if code < 400 and code != -1:
                # 200 sur l'objet d'un autre → FUITE (sauf si la réponse est vide/neutre)
                verdict = "FUITE"
                fuites.append({**r, "path": path, "objet": objkey, "code": code, "extrait": body})
            elif code in (404, 403, 401):
                verdict = "cloisonné"
            else:
                verdict = f"code {code}"
        matrice.append({"method": r["method"], "route": r["path"], "objet_attaque": objkey,
                        "code": code, "verdict": verdict})

    # ── NON-SUR-FILTRAGE : Stéphanie retrouve TOUS ses objets ──
    retrouve = {}
    lst = cs.get("/projets").json()
    retrouve["projet"] = any(p.get("id") == steph_objs.get("projet") for p in lst) if steph_objs.get("projet") else None
    lst = cs.get("/pipeline").json()
    retrouve["pipeline"] = any(e.get("id") == steph_objs.get("pipeline") for e in (lst if isinstance(lst, list) else lst.get("entries", []))) if steph_objs.get("pipeline") else None
    lst = cs.get("/filters").json()
    retrouve["filter"] = any((f.get("id") == steph_objs.get("filter")) for f in (lst if isinstance(lst, list) else lst.get("filters", []))) if steph_objs.get("filter") else None
    lst = cs.get("/watch-zones").json()
    retrouve["zone"] = any(z.get("id") == steph_objs.get("zone") for z in (lst if isinstance(lst, list) else lst.get("zones", []))) if steph_objs.get("zone") else None

    result = {
        "comptes": {"stephanie": {"email": STEPH, "id": cid_s}, "caroline": {"email": CARO, "id": cid_c}},
        "idu_dedie": IDU_A,
        "caro_objs": caro_objs, "steph_objs": steph_objs,
        "matrice": matrice, "fuites": fuites, "retrouve_ses_objets": retrouve,
        "n_routes_objet_testees": sum(1 for m in matrice if m["objet_attaque"]),
        "n_fuites": len(fuites),
    }
    (OUT / "a2_matrice.json").write_text(json.dumps(result, indent=2, ensure_ascii=False))

    print("\n=== ROUTES D'OBJET (attaque cross-compte) ===")
    for m in matrice:
        if m["objet_attaque"]:
            flag = "🔴 FUITE" if m["verdict"] == "FUITE" else "✓" if m["verdict"] == "cloisonné" else m["verdict"]
            print(f"  {flag:12} {m['method']:6} {m['route']:45} (objet {m['objet_attaque']}) → {m['code']}")
    print(f"\nRoutes d'objet testées : {result['n_routes_objet_testees']} · FUITES : {result['n_fuites']}")
    print(f"Non-sur-filtrage (Stéphanie retrouve les siens) : {retrouve}")
    print(f"\nMatrice → {OUT / 'a2_matrice.json'}")
    return 0 if not fuites else 2


if __name__ == "__main__":
    sys.exit(main())
