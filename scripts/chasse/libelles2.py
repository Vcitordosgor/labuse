"""CHASSE-2 angle 2 (libellés) — les deux invariants de DISCOURS du mandat, joués sur fiches
servies (TestClient en-process, même chemin que l'écran) :

  · capacite_differee ⇒ libellé « différé » PARTOUT où la capacité apparaît
    (fiche §Potentiel : potentiel_transformation.capacite_differee + libellé unique C06) ;
  · terrain_exigu ⇒ un libellé qui nomme la VRAIE raison (la cause posée par le run —
    terrain exigu / PPR — doit être lisible quelque part dans la fiche, jamais un
    « Marge SDP non calculée » muet).

Population : échantillon CHASSE-2 (classes run13) + 40 parcelles au_differe tirées île
(graine SQL hashtext, rejouable). Sortie : docs/audit-2026-10/CHASSE-2/LIBELLES2.csv
(une ligne par violation) + synthèse imprimée.

Lecture seule.
"""
from __future__ import annotations

import csv
import json
import pathlib

RACINE = pathlib.Path(__file__).resolve().parents[2]
ECHANTILLON = RACINE / "docs" / "audit-2026-10" / "CHASSE-2" / "ECHANTILLON.csv"
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-2" / "LIBELLES2.csv"
DSN = "postgresql://openclaw@localhost:5432/labuse"


def main() -> None:
    import psycopg
    from fastapi.testclient import TestClient

    from labuse.api.app import app

    client = TestClient(app)
    conn = psycopg.connect(DSN, options="-c statement_timeout=120000")
    cur = conn.cursor()

    # population 1 — au_differe : 40 parcelles en classe bloquante, tirage rejouable.
    cur.execute("""
        SELECT a.idu FROM parcel_au_statut a
        WHERE a.classe IN ('declasse_au_fermee','declasse_au_statut_inconnu','générique')
        ORDER BY hashtext(a.idu || 'chasse2') LIMIT 40""")
    differes = [r[0] for r in cur.fetchall()]

    # population 2 — terrain_exigu : les classes run13 de l'échantillon (calculee_exigu)
    # + 20 terrain_exigu « anciens » (déjà exigu au run 10), pour voir si le discours diffère.
    with open(ECHANTILLON, newline="") as f:
        ech = [r for r in csv.DictReader(f) if r["idu"]]
    exigus = [r["idu"] for r in ech if r["classe"] == "calculee_exigu"]
    cur.execute("""
        SELECT p.idu FROM parcel_residuel_runs r13
        JOIN parcel_residuel_runs r10 ON r10.parcel_id = r13.parcel_id AND r10.run_seq = 10
        JOIN parcels p ON p.id = r13.parcel_id
        WHERE r13.run_seq = 13 AND r13.cause = 'terrain_exigu' AND r10.cause = 'terrain_exigu'
        ORDER BY hashtext(p.idu || 'chasse2') LIMIT 20""")
    exigus_anciens = [r[0] for r in cur.fetchall()]

    violations: list[dict] = []
    stats = {"differe_ok": 0, "differe_ko": 0, "exigu_nomme": 0, "exigu_muet": 0,
             "exigu_discordance_sdp": 0, "fiches_ko": 0}

    def fiche(idu: str) -> dict | None:
        r = client.get(f"/parcels/{idu}")
        if r.status_code != 200:
            stats["fiches_ko"] += 1
            violations.append({"invariant": "fiche_http", "idu": idu,
                               "constat": f"HTTP {r.status_code}", "detail": ""})
            return None
        return r.json()

    for idu in differes:
        f = fiche(idu)
        if f is None:
            continue
        pot = f.get("potentiel_transformation") or {}
        ana = f.get("analyse_labuse") or {}
        brut = json.dumps(f, ensure_ascii=False).lower()
        # « partout » se joue en deux temps : (a) la fiche dit « différé » QUELQUE PART ;
        # (b) là où une capacité est affichée (bloc potentiel présent), le libellé est différé.
        dit_qq_part = ("différé" in brut) or ("differe" in brut.replace("é", "e"))
        bloc_coherent = (not pot) or pot.get("capacite_differee")
        if dit_qq_part and bloc_coherent:
            stats["differe_ok"] += 1
        else:
            stats["differe_ko"] += 1
            violations.append({
                "invariant": "differe_libelle", "idu": idu,
                "constat": f"dit_differe={dit_qq_part} bloc_potentiel="
                           f"{'absent' if not pot else 'présent capacite_differee=' + str(pot.get('capacite_differee'))}"
                           f" bande={ana.get('bande')} sdp={ana.get('sdp_residuelle_m2')}",
                "detail": f"libelle={pot.get('libelle')!r}"})

    for grp, liste in (("calculee_exigu_run13", exigus), ("exigu_ancien", exigus_anciens)):
        for idu in liste:
            f = fiche(idu)
            if f is None:
                continue
            brut = json.dumps(f, ensure_ascii=False).lower()
            pot = f.get("potentiel_transformation") or {}
            ana = f.get("analyse_labuse") or {}
            nomme = ("exigu" in brut) or ("terrain trop" in brut)
            if nomme:
                stats["exigu_nomme"] += 1
            else:
                stats["exigu_muet"] += 1
                violations.append({
                    "invariant": "exigu_raison_nommee", "idu": idu,
                    "constat": "cause run=terrain_exigu, AUCUNE mention de la raison dans la fiche",
                    "detail": f"groupe={grp} pot.libelle={pot.get('libelle')!r} "
                              f"ana.cause={ana.get('cause')!r} ana.bande={ana.get('bande')!r}"})
            # discordance intra-fiche : analyse_labuse.sdp=0 vs potentiel.sdp=∅ « non calculée »
            if (ana.get("sdp_residuelle_m2") == 0 and pot
                    and pot.get("sdp_residuelle_m2") is None
                    and pot.get("libelle") == "Marge SDP non calculée"):
                stats["exigu_discordance_sdp"] += 1
                violations.append({
                    "invariant": "exigu_discordance_intra_fiche", "idu": idu,
                    "constat": "analyse_labuse.sdp=0 MAIS potentiel_transformation « Marge SDP "
                               "non calculée » (sdp ∅) — même fiche, deux discours",
                    "detail": f"groupe={grp}"})

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with open(SORTIE, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["invariant", "idu", "constat", "detail"])
        w.writeheader()
        w.writerows(violations)
    print(f"différé : {stats['differe_ok']} ok / {stats['differe_ko']} ko (sur {len(differes)})")
    print(f"exigu   : {stats['exigu_nomme']} nommé / {stats['exigu_muet']} muet "
          f"(sur {len(exigus)} run13 + {len(exigus_anciens)} anciens)")
    print(f"discordance intra-fiche sdp 0/∅ : {stats['exigu_discordance_sdp']}")
    print(f"fiches en erreur : {stats['fiches_ko']}")
    print(f"→ {SORTIE} ({len(violations)} lignes)")
    conn.close()


if __name__ == "__main__":
    main()
