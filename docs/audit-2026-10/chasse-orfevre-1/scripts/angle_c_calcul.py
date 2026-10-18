#!/usr/bin/env python
"""CHASSE-ORFEVRE-1 — Angle C « les coins du calcul » : script REJOUABLE, lecture seule.

Rejoue tous les contrôles du brouillon ANGLE-C.md :
  · SQL (psycopg via SQLAlchemy) — cas extrêmes en base ;
  · appels de fonctions projet EN MÉMOIRE (resolve_zone, parts_zonage_surface) ;
  · sondes API via fastapi.testclient.TestClient SANS `with` → le lifespan (ensure_schema,
    DDL) n'est PAS exécuté : AUCUNE écriture, aucun serveur lancé.

Usage :
  cd ~/Desktop/labuse-orfevre && set -a && source .env && set +a && \
  PYTHONPATH=$PWD/src ~/Desktop/labuse/.venv/bin/python \
    docs/audit-2026-10/chasse-orfevre-1/scripts/angle_c_calcul.py
"""
from __future__ import annotations

import re
import warnings

warnings.filterwarnings("ignore")

from sqlalchemy import text  # noqa: E402

from labuse.db import session_factory  # noqa: E402

RUN_RESIDUEL_SERVI = 16   # parcel_residuel_runs.run_seq du run servi (vue parcel_residuel)
RUN_SCORE_SERVI = "q_v19"  # config/served_run.txt (le mandat disait q_v18 : PÉRIMÉ)


def titre(t: str) -> None:
    print(f"\n{'─' * 80}\n■ {t}\n{'─' * 80}")


def q(db, sql: str, **p):
    return db.execute(text(sql), p).mappings().all()


def main() -> None:  # noqa: PLR0915
    db = session_factory()()

    # ── C-0 — état réel de l'environnement (≠ hypothèses du mandat) ───────────────────────────
    titre("C-0 · fonctions SQL présentes + run servi")
    for r in q(db, "select proname from pg_proc where proname like 'labuse%' order by 1"):
        print("  fonction SQL en base :", r["proname"])
    print("  runs résiduel :", [r["run_seq"] for r in q(
        db, "select distinct run_seq from parcel_residuel_runs order by 1")])
    print("  runs score :", q(db, "select run_label, count(*) n from score_labuse group by 1 order by 1"))

    # ── C-07/C-08 — parcelles extrêmes ─────────────────────────────────────────────────────────
    titre("C-07/C-08 · surfaces extrêmes, géométries")
    print(q(db, """
        select count(*) filter (where surface_m2 <= 1) tiny,
               min(surface_m2) min_s,
               count(*) filter (where surface_m2 >= 2000000) ge200ha,
               max(surface_m2) max_s,
               count(*) filter (where surface_m2 is null or surface_m2 = 0) nul_ou_zero
        from parcels""")[0])
    print(q(db, "select GeometryType(geom) gt, count(*) n from parcels group by 1 order by 2 desc"))
    print("  minuscules → résiduel run servi :", q(db, """
        select r.cause, count(*) n from parcels p
        join parcel_residuel_runs r on r.parcel_id = p.id and r.run_seq = :rs
        where p.surface_m2 <= 1 group by 1 order by 2 desc limit 5""", rs=RUN_RESIDUEL_SERVI))
    print("  minuscules → bandes :", q(db, """
        select s.bande, count(*) n from parcels p
        join score_labuse s on s.parcel_id = p.id and s.run_label = :rl
        where p.surface_m2 <= 1 group by 1""", rl=RUN_SCORE_SERVI))
    print("  géantes ≥200 ha → bandes :", q(db, """
        select s.bande, count(*) n, max(s.score) from parcels p
        join score_labuse s on s.parcel_id = p.id and s.run_label = :rl
        where p.surface_m2 >= 2000000 group by 1""", rl=RUN_SCORE_SERVI))
    # GEOMETRYCOLLECTION : composition + aval
    print("  GEOMETRYCOLLECTION :", q(db, """
        select p.idu, (select string_agg(distinct GeometryType(g.geom), ',')
                       from st_dump(p.geom) g) parts,
               r.cause, s.bande
        from parcels p
        left join parcel_residuel_runs r on r.parcel_id = p.id and r.run_seq = :rs
        left join score_labuse s on s.parcel_id = p.id and s.run_label = :rl
        where GeometryType(p.geom) = 'GEOMETRYCOLLECTION'""",
        rs=RUN_RESIDUEL_SERVI, rl=RUN_SCORE_SERVI))
    # à cheval / incohérence idu↔commune
    print("  idu(insee)≠commune :", q(db, """
        select count(*) n from parcels p
        join communes_referentiel c on c.insee = substr(p.idu, 1, 5)
        where p.commune <> c.nom""")[0]["n"],
        "| idu hors référentiel :", q(db, """
        select count(*) n from parcels p where not exists
        (select 1 from communes_referentiel c where c.insee = substr(p.idu, 1, 5))""")[0]["n"])

    # ── C-10/C-11 — zones PLU tordues ─────────────────────────────────────────────────────────
    titre("C-10/C-11 · zones PLU : libellés tordus, familles")
    print(q(db, """
        select count(*) total,
               count(*) filter (where subtype is null or subtype = '') vide,
               count(*) filter (where subtype <> btrim(subtype)) espaces,
               count(*) filter (where subtype ~ '^[a-z]') minuscule
        from spatial_layers where kind = 'plu_gpu_zone'""")[0])
    print("  familles (fonction SQL) :", q(db, """
        select labuse_zone_famille(subtype) fam, count(*) n
        from spatial_layers where kind = 'plu_gpu_zone' group by 1 order by 2 desc"""))
    print(q(db, """
        select count(*) total,
               count(*) filter (where zone_lib is null or zone_lib = '') lib_vide,
               count(*) filter (where zone_lib <> btrim(zone_lib)) lib_espaces,
               count(*) filter (where zone_fam is null or zone_fam = '') fam_vide
        from parcel_zone_plu""")[0])
    # divergence des DEUX notions de famille (SQL subtype-only vs Python strip-phasage)
    print("  labuse_zone_famille(zone_lib) ≠ zone_fam (attendu — fonction faite pour subtype) :",
          q(db, """select count(*) n from parcel_zone_plu
                   where zone_fam <> labuse_zone_famille(zone_lib)""")[0]["n"])
    for code in ("1AUb", " U1", "u1", "Nco", "", None):
        row = q(db, "select labuse_zone_famille(:c) f", c=code)[0]
        print(f"  labuse_zone_famille({code!r}) = {row['f']!r}")
    # resolve_zone — torture en mémoire
    from labuse.faisabilite.zonage import resolve_zone
    for code, com in [("", "Saint-Denis"), ("   ", "Saint-Denis"), ("u1", "Saint-Denis"),
                      (" U1 ", "Saint-Denis"), ("ZZZZ", "Saint-Denis")]:
        r = resolve_zone(code, com)
        print(f"  resolve_zone({code!r}, {com}) ->",
              None if r is None else (r.code, r.constructible_neuf))

    # ── C-01 — phrase « bâti existant sur N % » non bornée (score servi) ──────────────────────
    titre("C-01 · contributions score q_v19 : « bâti existant sur N % » sans borne")
    print(q(db, r"""
        with c as (
          select (regexp_match(j->>'libelle', 'bâti existant sur (\d+) %'))[1]::int pct
          from score_labuse s, jsonb_array_elements(s.contributions) j
          where s.run_label = :rl and j->>'libelle' like 'bâti existant sur %')
        select count(*) total, count(*) filter (where pct > 100) sup100,
               count(*) filter (where pct > 300) sup300, max(pct) max
        from c""", rl=RUN_SCORE_SERVI)[0])

    # ── C-02 — parts CoSIA > 100 % (bati.py sans clamp) ───────────────────────────────────────
    titre("C-02 · parts CoSIA servies > 100 %")
    print(q(db, """
        with agg as (
          select c.idu,
            coalesce(sum(c.m2) filter (where c.classe in
              ('Bâtiment','Zone imperméable','Piscine','Serre')), 0)::numeric imper,
            coalesce(sum(c.m2) filter (where c.classe in
              ('Feuillu','Conifère','Broussaille','Pelouse','Culture','Vigne')), 0)::numeric veg,
            coalesce(sum(c.m2) filter (where c.classe in
              ('Sol nu','Terre labourée')), 0)::numeric nu,
            round(max(p.surface_m2))::numeric denom
          from parcel_cosia_couverture c join parcels p on p.idu = c.idu group by c.idu)
        select count(*) filter (where round(100*imper/denom,1) > 100
                                   or round(100*veg/denom,1) > 100
                                   or round(100*nu/denom,1) > 100) n_part_sup100,
               count(*) filter (where round(100*(imper+veg+nu)/denom,1) > 100.5) n_somme_sup100,
               max(greatest(round(100*imper/denom,1), round(100*veg/denom,1),
                            round(100*nu/denom,1))) max_part
        from agg where denom > 0""")[0])
    print("  pires cas :", q(db, """
        select c.idu, round(sum(c.m2)) cosia_m2, round(max(p.surface_m2)::numeric) surf
        from parcel_cosia_couverture c join parcels p on p.idu = c.idu
        group by c.idu having sum(c.m2) > max(p.surface_m2) * 1.05
        order by sum(c.m2)/max(p.surface_m2) desc limit 5"""))

    # ── C-06 — parcel_filtre_bati.ratio_pct : plafond 300 + poussière flottante ───────────────
    titre("C-06 · ratio_pct filtre bâti")
    print(q(db, """
        select count(*) filter (where ratio_pct > 100) sup100,
               count(*) filter (where ratio_pct = 300) exact300,
               count(*) filter (where ratio_pct > 300) sup300,
               max(ratio_pct) max from parcel_filtre_bati""")[0])

    # ── C-12 — dénominateurs zéro / quasi-zéro réels ──────────────────────────────────────────
    titre("C-12 · dénominateurs 0 ou quasi-0 en base (les gardes du code tiennent-elles ?)")
    print("  dvf surface_reelle_bati : ", q(db, """
        select count(*) filter (where surface_reelle_bati is null) nulls,
               min(surface_reelle_bati) min,
               count(*) filter (where surface_reelle_bati between 1 and 9
                                and valeur_fonciere > 100000) micro_chers
        from dvf_mutations_parcelle""")[0],
        " (marche_service.py:261 filtre surface >= 20 — garde OK)")
    print("  filosofi min(men)/min(ind) :", q(db,
        "select min(men) men, min(ind) ind from filosofi_carreaux_200m")[0],
        " (app.py:4467 garde `if carreau['men']`, NULLIF(ind,0))")
    print("  conso ENAF <= 0 :", q(db,
        "select count(*) n from commune_conso_enaf where conso_2021_2024_m2 <= 0")[0]["n"],
        " (app.py:2425 garde rythme <= 0 -> None)")

    # ── C-13 — NaN / Infinity dans les colonnes float servies ─────────────────────────────────
    titre("C-13 · NaN/Infinity (0 attendu partout)")
    checks = [
        ("batiment_hauteur_lidar", "faitage_m='NaN'::float8 or egout_m='NaN'::float8 "
         "or abs(coalesce(faitage_m,0))='Infinity'::float8"),
        ("dpe_records", "geocode_score='NaN'::float8 or surface_habitable='NaN'::float8"),
        ("dvf_mutations_parcelle", "valeur_fonciere='NaN'::float8"),
        ("filosofi_carreaux_200m", "ind_snv='NaN'::float8 or ind='NaN'::float8 or men='NaN'::float8"),
        ("parcel_p_score_v2", "p_raw='NaN'::float8 or p_24m='NaN'::float8 or percentile='NaN'::float8"),
        ("parcel_vegetation", "canopee_pct='NaN'::float8 or ndvi_moyen='NaN'::float8"),
        ("parcels", "surface_m2='NaN'::float8"),
        ("score_labuse", "signal_p='NaN'::float8 or abs(coalesce(signal_p,0))='Infinity'::float8"),
        ("parcel_filtre_bati", "ratio_pct='NaN'::float8 or emprise_max_m2='NaN'::float8"),
    ]
    for t, cond in checks:
        n = q(db, f"select count(*) n from {t} where {cond}")[0]["n"]  # noqa: S608 — littéraux internes
        print(f"  {t}: {n}")

    # ── C-14 — tri / accents ───────────────────────────────────────────────────────────────────
    titre("C-14 · collation C + chaînes à initiale accentuée")
    print("  datcollate :", q(db,
        "select datcollate from pg_database where datname = current_database()")[0]["datcollate"])
    for t, col in (("parcelle_personne_morale", "denomination"),
                   ("sirene_etablissements", "denomination"),
                   ("annuaire_services", "nom"), ("anru_quartiers", "nom")):
        n = q(db, f"select count(*) n from {t} where {col} ~ '^[ÀÂÄÉÈÊËÎÏÔÖÙÛÜÇ]'")[0]["n"]  # noqa: S608
        print(f"  {t}.{col} initiale accentuée : {n}")
    print("  communes triées :", [r["nom"] for r in q(
        db, "select nom from communes_referentiel order by nom limit 6")])

    # ── C-03 — parts de zonage commune : somme ≠ 100 ──────────────────────────────────────────
    titre("C-03 · parts zonage par commune (promesse docstring : somme = 100)")
    from labuse.registre.moteurs.zonage import parts_zonage_surface
    bad = []
    for (c,) in db.execute(text("select distinct commune from parcels order by 1")):
        z = parts_zonage_surface(db, c)
        if not z:
            continue
        s = round(sum(f["pct"] for f in z["familles"].values()), 1)
        if s != 100.0:
            bad.append((c, s))
    print("  communes != 100 :", bad, f"({len(bad)}/24)")
    db.rollback()
    db.close()

    # ── sondes API en mémoire (TestClient SANS with → lifespan/DDL non exécutés) ──────────────
    titre("Sondes API (TestClient, GET uniquement)")
    from fastapi.testclient import TestClient

    from labuse.api.app import app
    cl = TestClient(app, base_url="https://testserver", raise_server_exceptions=False)

    # C-01 : la phrase non bornée ATTEINT la fiche servie
    r = cl.get("/parcels/97411000AY0015")
    m = re.search(r"bâti existant sur (\d+) %", r.text)
    print("  fiche 97411000AY0015 :", r.status_code,
          "| phrase servie :", m.group(0) if m else "ABSENTE")

    # C-05 : /compare sert le taux brut (le front borne via fmtTauxEmprise)
    r = cl.get("/compare", params={"idus": "97411000AY0015", "source": RUN_SCORE_SERVI})
    print("  /compare taux_emprise_pct brut :",
          re.search(r'"taux_emprise_pct":\s*(-?\d+)', r.text).group(1)
          if r.status_code == 200 and "taux_emprise_pct" in r.text else f"({r.status_code})")

    # C-02 : parts CoSIA > 100 % servies sur la fiche
    for idu in ("97420000BH1222", "97411000AW0565"):
        d = cl.get(f"/parcels/{idu}").json()
        cc = ((d.get("le_bien") or {}).get("cosia_couverture")) or {}
        print(f"  fiche {idu} part_impermeabilisee_pct :", cc.get("part_impermeabilisee_pct"))

    # C-04 : division par zéro SQL via paramètre client (gracieusement 422, pas de borne ge=1)
    r = cl.get("/filtre", params={"source": RUN_SCORE_SERVI, "mode_b_rentable": "true",
                                  "modeb_rendement_pct": "0", "limit": 1})
    print("  /filtre modeb_rendement_pct=0 ->", r.status_code, r.json().get("detail"))

    # C-03 : parts servies par l'API commune (Saint-Denis = 100.1)
    d = cl.get("/communes/Saint-Denis/contexte").json()
    fam = ((d.get("foncier") or {}).get("repartition_zonage") or {}).get("familles") or {}
    print("  /communes/Saint-Denis/contexte parts :", {k: v["pct"] for k, v in fam.items()},
          "somme =", round(sum(v["pct"] for v in fam.values()), 1))

    # C-07 : fiche d'une parcelle de 0,027 m² (surface servie 0)
    d = cl.get("/parcels/97401000AR1644").json()
    print("  fiche 97401000AR1644 surface_m2 :", d.get("surface_m2"),
          "| surface_terrain_m2 :", d.get("surface_terrain_m2"))

    # C-15 : formats (longues décimales hors géo, notation scientifique, -0)
    for idu in ("97401000AR1644", "97404000AT0722"):
        t = cl.get(f"/parcels/{idu}").text
        longdec = [x for x in sorted(set(re.findall(r'"([a-z_0-9]+)":\s*-?\d+\.\d{5,}', t)))
                   if x not in ("lat", "lon", "latitude", "longitude")]
        sci = sorted(set(re.findall(r'"[a-z_0-9]+":\s*-?\d(?:\.\d+)?e-\d+', t)))
        print(f"  fiche {idu} — clés > 4 décimales : {longdec} | scientifique : {sci}")

    print("\nFini — aucun INSERT/UPDATE/DDL exécuté (lifespan non entré, session rollback).")


if __name__ == "__main__":
    main()
