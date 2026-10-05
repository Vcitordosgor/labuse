"""CHASSE-3 angle 4 — causes certaines / causes d'ignorance (post CHASSE-FIX-2)
+ badge « Propriétaire public ».

Invariant île (run SERVI, vue parcel_residuel) :
  cause CERTAINE  (zone_non_constructible, terrain_exigu, habitat_interdit,
                   redhibitoire, capacite_nulle)             ⇒ SDP = 0 (jamais NULL)
  cause d'IGNORANCE (toutes les autres)                      ⇒ SDP = NULL (jamais un chiffre)
  pas de cause                                               ⇒ SDP calculée (dont 0 légitime ? NON :
                                                               un 0 sans cause est un écart — le 0
                                                               doit être NOMMÉ)
Libellés : la fiche (API) d'un échantillon par cause dit « Non retenue — … » /
« Analyse incomplète — … » selon la classe — jamais l'inverse.

Badge public : 50 parcelles tirées au sort parmi celles que la LISTE (API) sert avec
proprietaire_public=true → chacune doit avoir, dans la source DGFiP
(parcelle_personne_morale), un groupe ∈ PUBLIC_DGFIP_GROUPES. Un faux positif = FAUX.

Sorties : docs/audit-2026-10/CHASSE-3/CAUSES.csv (anomalies, vide = sain).
Rejouable : LABUSE_CHASSE3_API=http://127.0.0.1:6015 python -m scripts.chasse.causes3
"""
from __future__ import annotations

import csv
import json
import os
import urllib.parse
import urllib.request
from pathlib import Path

import psycopg

BASE = os.environ.get("LABUSE_CHASSE3_API", "http://127.0.0.1:6015")
DSN = os.environ.get("LABUSE_DSN", "dbname=labuse")
OUT = Path(__file__).resolve().parents[2] / "docs" / "audit-2026-10" / "CHASSE-3"
OUT.mkdir(parents=True, exist_ok=True)

# la classe vient du CODE (engine._CAUSES_CERTAINES) — importée, pas recopiée, pour
# que le harnais casse si la taxonomie bouge sans que l'invariant soit rejoué.
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src"))
from labuse.faisabilite.engine import _CAUSES_CERTAINES  # noqa: E402
from labuse.proprietaire_type import PUBLIC_DGFIP_GROUPES  # noqa: E402


def _api(path: str):
    url = BASE + urllib.parse.quote(path, safe="/?&=")
    with urllib.request.urlopen(url, timeout=120) as r:
        return json.loads(r.read())


def main() -> None:
    anomalies: list[list] = []
    conn = psycopg.connect(DSN)
    cur = conn.cursor()

    # ── 1. invariant île : classe(cause) ↔ forme de la SDP ────────────────────
    certaines = tuple(sorted(_CAUSES_CERTAINES))
    cur.execute(
        """
        SELECT CASE
                 WHEN cause IS NULL THEN 'sans_cause'
                 WHEN split_part(cause, ':', 1) = ANY(%s) THEN 'certaine'
                 ELSE 'ignorance'
               END AS classe,
               CASE WHEN sdp_residuelle_m2 IS NULL THEN 'sdp_null'
                    WHEN sdp_residuelle_m2 = 0 THEN 'sdp_0'
                    ELSE 'sdp_chiffree' END AS forme,
               count(*)
        FROM parcel_residuel
        GROUP BY 1, 2 ORDER BY 1, 2
        """, (list(certaines),))
    repartition = cur.fetchall()
    print("répartition île (classe × forme SDP) :")
    for classe, forme, n in repartition:
        print(f"  {classe:<10} {forme:<13} {n:>8}")
        interdit = (
            (classe == "certaine" and forme != "sdp_0")
            or (classe == "ignorance" and forme != "sdp_null")
        )
        if interdit:
            cur.execute(
                """
                SELECT p.idu FROM parcel_residuel r JOIN parcels p ON p.id = r.parcel_id
                WHERE (CASE WHEN r.cause IS NULL THEN 'sans_cause'
                            WHEN split_part(r.cause, ':', 1) = ANY(%s) THEN 'certaine'
                            ELSE 'ignorance' END) = %s
                  AND (CASE WHEN r.sdp_residuelle_m2 IS NULL THEN 'sdp_null'
                            WHEN r.sdp_residuelle_m2 = 0 THEN 'sdp_0'
                            ELSE 'sdp_chiffree' END) = %s
                LIMIT 5
                """, (list(certaines), classe, forme))
            temoins = ",".join(r[0] for r in cur.fetchall())
            anomalies.append(["invariant_ile", f"{classe}×{forme}", n,
                              f"combinaison interdite — témoins {temoins}"])

    # ── 1-bis. un 0 SANS cause doit être NOMMÉ à la fiche (échantillon 12) ─────
    # (la cause stockée n'est pas le seul canal : « Densité autorisée atteinte ou
    #  dépassée » vient d'un autre champ — on vérifie le LIBELLÉ CLIENT, pas la colonne)
    cur.execute("""
        SELECT p.idu FROM parcel_residuel r JOIN parcels p ON p.id = r.parcel_id
        WHERE r.cause IS NULL AND r.sdp_residuelle_m2 = 0
        ORDER BY md5('chasse3' || p.idu) LIMIT 12""")
    for (idu,) in cur.fetchall():
        try:
            fiche = _api(f"/parcels/{idu}")
        except Exception as e:
            anomalies.append(["zero_nomme", idu, "", f"fiche injouable: {e}"])
            continue
        pt = fiche.get("potentiel_transformation") or {}
        if not (pt.get("libelle") or "").strip():
            anomalies.append(["zero_nomme", idu, "", "SDP 0 servie SANS libellé à la fiche"])

    # ── 1-ter. cohérence fiche ↔ bande servie : une parcelle « Analyse incomplète »
    #           à la fiche ne doit pas être classée bande '0' (Non retenue) au Score ──
    cur.execute("""
        SELECT sl.idu, r.cause FROM score_labuse sl
        JOIN parcel_residuel r ON r.parcel_id = sl.parcel_id
        WHERE sl.run_label = (SELECT split_part(label, ' ', 1)
                              FROM residuel_runs WHERE is_served)
          AND sl.bande = '0' AND r.cause IS NOT NULL
          AND split_part(r.cause, ':', 1) <> ALL(%s)""", (list(certaines),))
    for idu, cause in cur.fetchall():
        anomalies.append(["fiche_vs_bande", idu, cause,
                          "cause d'ignorance (fiche « Analyse incomplète ») mais bande '0' au classement"])

    # ── 2. libellés servis (fiche API) : 3 témoins par cause distincte ────────
    cur.execute("""
        SELECT DISTINCT ON (split_part(cause,':',1), n) p.idu, r.cause
        FROM (SELECT parcel_id, cause, row_number() OVER
                     (PARTITION BY split_part(cause,':',1) ORDER BY parcel_id) AS n
              FROM parcel_residuel WHERE cause IS NOT NULL) r
        JOIN parcels p ON p.id = r.parcel_id
        WHERE r.n <= 3""")
    for idu, cause in cur.fetchall():
        racine = cause.split(":")[0]
        attendu = "Non retenue" if racine in _CAUSES_CERTAINES else "Analyse incomplète"
        inverse = "Analyse incomplète" if attendu == "Non retenue" else "Non retenue"
        try:
            fiche = _api(f"/parcels/{idu}")
        except Exception as e:
            anomalies.append(["fiche_libelle", idu, cause, f"fiche injouable: {e}"])
            continue
        pv = (fiche.get("potentiel_transformation") or {})
        lib = pv.get("libelle") or ""
        if attendu not in lib or inverse in lib:
            anomalies.append(["fiche_libelle", idu, cause,
                              f"attendu « {attendu} — … », servi « {lib[:90]} »"])

    # ── 3. badge « Propriétaire public » : 50 tirés au sort (LISTE servie), 0 faux ──
    # Le badge est servi par la LISTE (/parcels, champ proprietaire_public, app.py:3650) :
    # on tire 50 lignes badgées « public » (tirage déterministe md5) sur plusieurs communes
    # et on confronte chacune à la SOURCE DGFiP (groupe ∈ PUBLIC_DGFIP_GROUPES).
    # Bonus faux NÉGATIFS : les lignes NON badgées dont la source dit « public ».
    import random
    communes = ["Saint-Denis", "Saint-Paul", "Saint-Pierre", "Le Tampon", "Saint-Louis",
                "Bras-Panon", "Saint-André", "Le Port", "Saint-Joseph", "Sainte-Marie"]
    lignes: list[dict] = []
    for c in communes:
        try:
            lignes += _api(f"/parcels?source=q_v16&commune={c}&limit=400")
        except Exception as e:
            anomalies.append(["badge_public", c, "liste injouable", str(e)])
    rng = random.Random("chasse3")
    badges = [r for r in lignes if r.get("proprietaire_public")]
    rng.shuffle(badges)
    faux = 0
    for r in badges[:50]:
        cur.execute("SELECT groupe FROM parcelle_personne_morale WHERE idu=%s", (r["idu"],))
        groupes = [g[0] for g in cur.fetchall()]
        if not any(g in PUBLIC_DGFIP_GROUPES for g in groupes):
            faux += 1
            anomalies.append(["badge_public", r["idu"], "faux positif",
                              f"badge public servi en liste, groupes DGFiP={groupes}"])
    sans_badge = [r for r in lignes if not r.get("proprietaire_public")]
    rng.shuffle(sans_badge)
    faux_neg = 0
    for r in sans_badge[:200]:
        cur.execute("SELECT groupe FROM parcelle_personne_morale WHERE idu=%s", (r["idu"],))
        groupes = [g[0] for g in cur.fetchall()]
        if groupes and all(g in PUBLIC_DGFIP_GROUPES for g in groupes):
            faux_neg += 1
            anomalies.append(["badge_public", r["idu"], "faux négatif",
                              f"source DGFiP groupes={groupes} (public) mais badge absent en liste"])
    print(f"badge public : {min(50, len(badges))} badgées vérifiées ({faux} faux positif), "
          f"{min(200, len(sans_badge))} non badgées ({faux_neg} faux négatif)")

    with (OUT / "CAUSES.csv").open("w", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["volet", "cle", "valeur", "detail"])
        w.writerows(anomalies)
    print(f"{len(anomalies)} anomalie(s) → {OUT}/CAUSES.csv")
    conn.close()


if __name__ == "__main__":
    main()
