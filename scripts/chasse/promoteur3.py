"""CHASSE-3 angle 2 (promoteur) — 8 scénarios réalistes joués DE BOUT EN BOUT contre /filtre
(build de prod), puis RECALCULÉS indépendamment en SQL depuis les tables de base.

    python -m scripts.chasse.promoteur3   # → docs/audit-2026-10/CHASSE-3/PROMOTEUR.csv

Méthode (une parcelle oubliée ou en trop côté app = FAUX) :
  1. GET /filtre?source=<run servi>&…&idus=1&limit=0 → compteur + liste COMPLÈTE d'IDU
     (aucun scénario ne dépasse le plafond _FILTRE_IDUS_CAP — vérifié, sinon le harnais échoue) ;
  2. recalcul SQL indépendant depuis les tables de base (parcels, parcel_zone_plu,
     parcel_residuel_runs du run servi, parcel_flags q_v16, parcelle_personne_morale,
     pm_dirigeants/pm_dirigeant_gigogne, p_model_permits+sitadel_permits+m10_permit_delais…),
     sur le MÊME périmètre client : parcelles de la commune, slivers < MIN_DISPLAY_SURFACE_M2
     (2 m²) exclus, univers = cascade du run servi (q_v16 emprunte l'étage 0 q_v13_sources1) ;
  3. diff symétrique (manquantes = vues par le SQL, pas par l'app ; en_trop = l'inverse) ;
  4. contrôles de cohérence interne : compte == len(idus) (fix F2/D05) ;
  5. contrôles de NOTION secondaires (S3 : table pc_caducs vs recalcul Sitadel ; S4 : instantané
     veille vs recalcul dirigeants ; S5 : règle « ≥3 parcelles même SIREN » + mesure de contiguïté).

Lecture seule (API + base) ; n'écrit QUE le CSV de sortie.
"""
from __future__ import annotations

import csv
import json
import os
import pathlib
import urllib.parse
import urllib.request

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "CHASSE-3" / "PROMOTEUR.csv"
API = os.environ.get("CHASSE3_API", "http://127.0.0.1:6015")
DSN = os.environ.get("CHASSE3_DSN", "dbname=labuse")
RUN = json.loads((RACINE / "config" / "served_manifest.json").read_text())["scoring_run"]

# ── constantes MIROIR (relues du code, jamais importées : recalcul indépendant) ──
MIN_DISPLAY_SURFACE_M2 = 2.0          # app.py:69 — slivers masqués du compteur ET de la liste
SDP_PAR_LOGEMENT_M2 = 70              # app.py:1417 — capacite_min N ⇒ SDP ≥ N×70
PC_REF_YEAR = 2026                    # ingestion/pc_caducs.py — caduc si Y ≤ ref_year-4
PUBLIC_GROUPES = (1, 2, 3, 4, 9)      # proprietaire_type.PUBLIC_DGFIP_GROUPES (C35)
VEILLE_FORMES = ("SCI", "SC", "SCEA", "EARL", "GFA", "SCM", "SARL", "SNC")  # score_v_constants
ASSEMBLAGE_MIN = 3                    # signaux_vie.ASSEMBLAGE_MIN_PARCELLES


def fetch(path: str) -> dict:
    with urllib.request.urlopen(API + path, timeout=600) as r:
        return json.loads(r.read())


def app_filtre(params: dict) -> tuple[int, set[str]]:
    """Compteur + liste d'IDU COMPLÈTE de /filtre (échoue si tronquée : resserrer le scénario)."""
    qs = urllib.parse.urlencode({"source": RUN, "limit": 0, "idus": 1, **params})
    d = fetch("/filtre?" + qs)
    if d.get("idus_tronque"):
        raise SystemExit(f"liste idus tronquée pour {params} — resserrer le périmètre")
    idus = set(d.get("idus") or [])
    compte = int(d["compte"])
    # pièges connus F2/D05 : le compteur et la liste (carte) doivent être le MÊME ensemble
    if compte != len(idus):
        raise AssertionError(f"compte {compte} ≠ len(idus) {len(idus)} pour {params}")
    return compte, idus


# ── univers client : commune + hors slivers + cascade du run servi ──
UNIVERS = """
SELECT p.idu FROM parcels p
WHERE p.commune = %(commune)s
  AND (p.surface_m2 IS NULL OR p.surface_m2 >= %(minsurf)s)
  AND EXISTS (SELECT 1 FROM dryrun_parcel_evaluations d
              WHERE d.parcel_id = p.id AND d.run_label = %(cascade)s)
"""

# S3 — recalcul INDÉPENDANT des permis caducs depuis Sitadel (règle du code SERVI,
# ingestion/pc_caducs.py : octroyé = etat ∈ {2,5,6}, réalisé = DAACT ou etat ∈ {5,6}, Y ≤ ref-4).
SQL_PC_CADUCS_RECALCUL = """
WITH pc AS (
  SELECT pmp.idu, EXTRACT(YEAR FROM pmp.date_autorisation)::int AS y,
         (sp.raw->>'etat') AS etat, (md.date_achevement IS NOT NULL) AS daact
  FROM p_model_permits pmp
  JOIN sitadel_permits sp ON sp.permit_id = pmp.permit_id
  JOIN m10_permit_delais md ON md.permit_id = pmp.permit_id
  WHERE pmp.type = 'PC' AND pmp.date_autorisation IS NOT NULL),
parc AS (
  SELECT idu,
         min(y) FILTER (WHERE etat IN ('2','5','6')) AS y_octroye,
         bool_or(daact OR etat IN ('5','6')) AS realized,
         bool_or(etat IN ('2','5','6'))      AS granted
  FROM pc GROUP BY idu)
SELECT parc.idu FROM parc JOIN parcels p ON p.idu = parc.idu
WHERE parc.granted AND NOT parc.realized AND parc.y_octroye <= %(ycut)s
"""

# S4 — recalcul de la notion « succession à venir » : dirigeant ≥ 70 ans (vue rejouée depuis
# pm_dirigeants + pm_dirigeant_gigogne) × forme patrimoniale. La branche « SCI dormante » n'est
# PAS recalculable depuis la base (payload RNE owner_enrichment) : reprise de l'instantané, dit.
SQL_SUCCESSION_AGE70 = """
WITH ages AS (
  SELECT d.siren,
         max(EXTRACT(YEAR FROM age(to_date(d.date_naissance, 'YYYY-MM')))::int)
             FILTER (WHERE d.type_personne = 'INDIVIDU' AND d.date_naissance IS NOT NULL) AS age_direct
  FROM pm_dirigeants d GROUP BY d.siren),
gig AS (
  SELECT g.siren, max(EXTRACT(YEAR FROM age(to_date(g.date_naissance, 'YYYY-MM')))::int) AS age_gigogne
  FROM pm_dirigeant_gigogne g WHERE g.date_naissance IS NOT NULL GROUP BY g.siren)
SELECT DISTINCT pm.idu
FROM parcelle_personne_morale pm
JOIN ages a ON a.siren = pm.siren
LEFT JOIN gig ON gig.siren = pm.siren
WHERE COALESCE(a.age_direct, gig.age_gigogne) >= 70
  AND upper(trim(pm.forme_juridique)) = ANY(%(formes)s)
"""
SQL_SUCCESSION_SCI_SNAPSHOT = "SELECT parcelle_id FROM parcel_veille_succession WHERE sci_dormante"

# S5 — recalcul de la règle documentée (signaux_vie.py) : société PRIVÉE (groupe MAJIC 0)
# détenant ≥ 3 parcelles sur l'ÎLE (pas de contiguïté dans la règle — mesurée à part).
SQL_ASSEMBLAGE_RECALCUL = """
SELECT DISTINCT pm.idu
FROM parcelle_personne_morale pm
JOIN (SELECT siren FROM parcelle_personne_morale
      WHERE groupe = 0 AND siren IS NOT NULL
      GROUP BY siren HAVING count(DISTINCT idu) >= %(seuil)s) own ON own.siren = pm.siren
WHERE pm.groupe = 0
"""

# S5 (notion) — part des parcelles du résultat dont le SIREN possède AU MOINS UNE autre parcelle
# CONTIGUË (≤ 1 m, geom_2975) n'importe où sur l'île — mesure le « contiguës » du scénario client.
SQL_ASSEMBLAGE_CONTIGUITE = """
WITH res AS (
  SELECT pm.idu, pm.siren, p.geom_2975
  FROM parcelle_personne_morale pm JOIN parcels p ON p.idu = pm.idu
  WHERE pm.groupe = 0 AND pm.idu = ANY(%(idus)s))
SELECT count(DISTINCT r.idu) FILTER (WHERE EXISTS (
         SELECT 1 FROM parcelle_personne_morale pm2 JOIN parcels p2 ON p2.idu = pm2.idu
         WHERE pm2.siren = r.siren AND pm2.idu <> r.idu
           AND p2.geom_2975 && ST_Expand(r.geom_2975, 1.0)
           AND ST_DWithin(p2.geom_2975, r.geom_2975, 1.0))),
       count(DISTINCT r.idu)
FROM res r
"""

# S6 — même vue rejouée que S4, SANS restriction de forme (filtre pm_age=70plus de l'app)
SQL_PM_AGE70 = """
WITH ages AS (
  SELECT d.siren,
         max(EXTRACT(YEAR FROM age(to_date(d.date_naissance, 'YYYY-MM')))::int)
             FILTER (WHERE d.type_personne = 'INDIVIDU' AND d.date_naissance IS NOT NULL) AS age_direct
  FROM pm_dirigeants d GROUP BY d.siren),
gig AS (
  SELECT g.siren, max(EXTRACT(YEAR FROM age(to_date(g.date_naissance, 'YYYY-MM')))::int) AS age_gigogne
  FROM pm_dirigeant_gigogne g WHERE g.date_naissance IS NOT NULL GROUP BY g.siren)
SELECT DISTINCT pm.idu
FROM parcelle_personne_morale pm
JOIN ages a ON a.siren = pm.siren
LEFT JOIN gig ON gig.siren = pm.siren
WHERE COALESCE(a.age_direct, gig.age_gigogne) >= 70
"""


def cascade_de(cur) -> str:
    """Résolution INDÉPENDANTE de la cascade du run servi (bascule_flux rejoué sur les tables)."""
    cur.execute("SELECT 1 FROM dryrun_parcel_evaluations WHERE run_label = %s LIMIT 1", (RUN,))
    if cur.fetchone():
        return RUN
    cur.execute("SELECT params FROM p_score_v2_runs WHERE run_id = %s", (RUN,))
    row = cur.fetchone()
    p = row[0] if row else None
    if isinstance(p, str):
        p = json.loads(p)
    emprunte = (p or {}).get("etage0_run") or (p or {}).get("prev_run")
    if not emprunte:
        raise SystemExit(f"run {RUN} sans cascade propre ni étage 0 emprunté")
    return emprunte


def main() -> None:
    conn = psycopg.connect(DSN)
    conn.read_only = True
    cur = conn.cursor()
    cur.execute("SELECT count(*) FROM pg_stat_activity WHERE state='active'")
    print(f"sessions actives : {cur.fetchone()[0]} — run servi : {RUN}")
    cascade = cascade_de(cur)
    cur.execute("SELECT run_seq FROM residuel_runs WHERE is_served")
    rseq = cur.fetchone()[0]
    print(f"cascade résolue : {cascade} · résiduel servi : run_seq {rseq}")

    base = {"minsurf": MIN_DISPLAY_SURFACE_M2, "cascade": cascade, "rseq": rseq,
            "ycut": PC_REF_YEAR - 4, "formes": list(VEILLE_FORMES),
            "seuil": ASSEMBLAGE_MIN, "capa": 10 * SDP_PAR_LOGEMENT_M2,
            "publics": list(PUBLIC_GROUPES)}

    def univers(commune: str, conds: str = "") -> set[str]:
        cur.execute(UNIVERS + conds, {**base, "commune": commune})
        return {r[0] for r in cur.fetchall()}

    def requete(sql: str) -> set[str]:
        cur.execute(sql, base)
        return {r[0] for r in cur.fetchall()}

    # ── les 8 scénarios : (id, commune, params API, callable → set SQL indépendant, analyse) ──
    def s1() -> set[str]:
        return univers("Saint-Paul", """
  AND round(p.surface_m2::numeric) >= 1000
  AND EXISTS (SELECT 1 FROM parcel_zone_plu z WHERE z.idu = p.idu AND z.zone_fam = 'U')
  AND NOT EXISTS (SELECT 1 FROM parcel_residuel_runs r WHERE r.run_seq = %(rseq)s
                  AND r.parcel_id = p.id AND COALESCE(r.taux_emprise_pct, 0) >= 5)
  AND NOT EXISTS (SELECT 1 FROM parcel_flags f WHERE f.parcel_id = p.id
                  AND f.run_label = %(runflags)s AND f.layer_name = 'risques')""")

    def s2() -> set[str]:
        return univers("Saint-Denis", """
  AND EXISTS (SELECT 1 FROM parcel_zone_plu z WHERE z.idu = p.idu AND z.zone_fam = 'U')
  AND EXISTS (SELECT 1 FROM parcel_residuel_runs r WHERE r.run_seq = %(rseq)s
              AND r.parcel_id = p.id AND r.cause IS NULL AND r.sdp_residuelle_m2 >= %(capa)s)""")

    def s3() -> set[str]:
        return univers("Saint-Pierre") & requete(SQL_PC_CADUCS_RECALCUL)

    def s4() -> set[str]:
        return univers("Le Tampon") & (requete(SQL_SUCCESSION_AGE70)
                                       | requete(SQL_SUCCESSION_SCI_SNAPSHOT))

    def s5() -> set[str]:
        return univers("Saint-André") & requete(SQL_ASSEMBLAGE_RECALCUL)

    def s6() -> set[str]:
        return univers("Saint-Louis") & requete(SQL_PM_AGE70)

    def s7() -> set[str]:
        return univers("Le Port", """
  AND round(p.surface_m2::numeric) >= 5000
  AND EXISTS (SELECT 1 FROM parcelle_personne_morale pm WHERE pm.idu = p.idu
              AND pm.groupe = ANY(%(publics)s))""")

    def s8() -> set[str]:
        return univers("Saint-Benoît", """
  AND round(p.surface_m2::numeric) >= 800
  AND EXISTS (SELECT 1 FROM parcel_residuel_runs r WHERE r.run_seq = %(rseq)s
              AND r.parcel_id = p.id AND COALESCE(r.taux_emprise_pct, 0) >= 5)
  AND EXISTS (SELECT 1 FROM parcel_residuel_runs r2 WHERE r2.run_seq = %(rseq)s
              AND r2.parcel_id = p.id AND r2.sous_densite)""")

    base["runflags"] = RUN   # parcel_flags est scopée au run SERVI (q_v16), pas à la cascade

    SCENARIOS = [
        ("S1 nu ≥1000 m² zone U hors risques (Saint-Paul)",
         {"commune": "Saint-Paul", "etat_sol": "nu", "surface_min": 1000,
          "zonage": "U", "flags_exclus": "risques"}, s1, ""),
        ("S2 capacité ≥10 logements zone U (Saint-Denis)",
         {"commune": "Saint-Denis", "capacite_min": 10, "zonage": "U"}, s2,
         "capacité = SDP résiduelle ≥ 10×70 m², lignes calculées seules (cause IS NULL)"),
        ("S3 permis dormants/caducs (Saint-Pierre)",
         {"commune": "Saint-Pierre", "signaux": "permis_caduc"}, s3,
         "recalcul Sitadel (règle servie pc_caducs.py : octroyé {2,5,6}, Y ≤ 2022). ANALYSE "
         "(reproduite) : la table pc_caducs lue par /filtre date du 08/08, AVANT ORACLE-FIX-1 — "
         "manquantes = PC etat 2 « autorisé » jamais commencés, les VRAIS dormants (ex. CO0258, "
         "PC 2013, fiche liste le permis mais caducite=null) ; en_trop = parcelles dont le seul "
         "PC est ANNULÉ etat 4 (ex. CO0833 : la MÊME fiche dit permis « annulé » ET bloc "
         "caducité « PC autorisé 2019 · jamais commencé ») ou COMMENCÉ etat 5 (ex. CR0328, "
         "chantier 2025). Divergence née à l'ingestion : table jamais rebâtie après le fix"),
        ("S4 successions à venir (Le Tampon)",
         {"commune": "Le Tampon", "signaux": "succession"}, s4,
         "recalcul dirigeant 70+ (pm_dirigeants+gigogne × formes patrimoniales) ; branche SCI "
         "dormante reprise de l'instantané (RNE non recalculable). ANALYSE (reproduite) : "
         "l'instantané parcel_veille_succession date du 09/08 — en_trop : 12/48 sont des SA/SAS "
         "(ex. AK0603 SAS, AH0351 SA) que la règle SERVIE exclut depuis OUTILS-S2 (formes "
         "patrimoniales, décision Vic 25/09, POSTÉRIEURE à l'instantané) ; 36/48 ont un âge 09/08 "
         "introuvable dans pm_dirigeants du jour (fallback recherche-entreprises ou RNE changé — "
         "non tranché) ; manquantes : SIREN absents de l'instantané alors que la base du jour les "
         "qualifie (ex. 320878358, SCI, dirigeant 84 ans, 23 parcelles île, 0 ligne veille ; "
         "12/36 à 70-71 ans = franchissement du seuil depuis le 09/08)"),
        ("S5 assemblage même propriétaire (Saint-André)",
         {"commune": "Saint-André", "signaux": "assemblage"}, s5,
         "règle documentée : SIREN privé (groupe 0) ≥ 3 parcelles sur l'île — SANS contiguïté"),
        ("S6 PM dirigeant 70+ (Saint-Louis)",
         {"commune": "Saint-Louis", "personne_morale": "true", "pm_age": "70plus"}, s6,
         "âge max dirigeant rejoué depuis pm_dirigeants (INDIVIDU) + pm_dirigeant_gigogne"),
        ("S7 propriétaire public ≥5000 m² (Le Port)",
         {"commune": "Le Port", "proprietaire_type": "public", "surface_min": 5000}, s7,
         "groupes DGFiP publics (1,2,3,4,9) — règle C35"),
        ("S8 bâti sous-densité ≥800 m² (Saint-Benoît)",
         {"commune": "Saint-Benoît", "etat_sol": "bati", "sous_densite": "true",
          "surface_min": 800}, s8,
         "bâti = emprise ≥ 5 % (parcel_residuel) ∧ sous_densite"),
    ]

    lignes = []
    diffs: dict[str, dict] = {}
    for nom, params, sql_fn, note in SCENARIOS:
        compte, app = app_filtre(params)
        sql = sql_fn()
        manque, trop = sorted(sql - app), sorted(app - sql)
        # une parcelle oubliée ou en trop côté app = FAUX (les écarts de périmètre documentés —
        # slivers < 2 m², arrondi de surface — sont DANS le recalcul, donc jamais comptés ici)
        verdict = "JUSTE" if not manque and not trop else "FAUX"
        detail = note
        if manque or trop:
            detail += (f" · exemples manquantes={manque[:3]} en_trop={trop[:3]}")
        diffs[nom] = {"manque": manque, "trop": trop}
        lignes.append({"scenario": nom, "app_count": compte, "sql_count": len(sql),
                       "manquantes": len(manque), "en_trop": len(trop),
                       "verdict": verdict, "detail": detail})
        print(f"{nom}: app={compte} sql={len(sql)} manquantes={len(manque)} "
              f"en_trop={len(trop)} → {verdict}")

    # ── contrôles de notion secondaires (consignés en lignes NOTE) ──
    # S3 : la table servie pc_caducs correspond-elle ENCORE à la règle du code servi ?
    cur.execute("SELECT count(*), max(updated_at)::date FROM pc_caducs")
    n_table, d_table = cur.fetchone()
    n_recalc = len(requete(SQL_PC_CADUCS_RECALCUL))
    lignes.append({"scenario": "S3-NOTE table pc_caducs vs recalcul (île)",
                   "app_count": n_table, "sql_count": n_recalc,
                   "manquantes": "", "en_trop": "",
                   "verdict": "FAUX" if n_table != n_recalc else "JUSTE",
                   "detail": f"pc_caducs servie = {n_table} lignes (maj {d_table}) ; la règle du "
                             f"code servi (ORACLE-FIX-1, états 2/5/6) en produit {n_recalc} — "
                             "table jamais rebâtie après le fix (cache périmé)"})
    # S4 : fraîcheur de l'instantané veille (île) vs recalcul dirigeants du jour
    cur.execute("SELECT count(*), max(computed_at)::date FROM parcel_veille_succession")
    n_snap, d_snap = cur.fetchone()
    n_age = len(requete(SQL_SUCCESSION_AGE70))
    cur.execute("SELECT count(*) FROM parcel_veille_succession WHERE dirigeant_age IS NOT NULL")
    n_snap_age = cur.fetchone()[0]
    lignes.append({"scenario": "S4-NOTE instantané veille vs recalcul 70+ (île)",
                   "app_count": n_snap_age, "sql_count": n_age,
                   "manquantes": "", "en_trop": "",
                   "verdict": "NOTE",
                   "detail": f"instantané {n_snap} lignes (maj {d_snap}, dont {n_snap_age} "
                             f"« dirigeant 70+ ») ; recalcul du jour = {n_age} parcelles"})
    # S5 : mesure de contiguïté sur le résultat servi à Saint-André
    app_s5 = sorted(app_filtre({"commune": "Saint-André", "signaux": "assemblage"})[1])
    cur.execute(SQL_ASSEMBLAGE_CONTIGUITE, {"idus": app_s5})
    n_contig, n_tot = cur.fetchone()
    lignes.append({"scenario": "S5-NOTE contiguïté du résultat (Saint-André)",
                   "app_count": n_tot, "sql_count": n_contig,
                   "manquantes": "", "en_trop": "",
                   "verdict": "NOTE",
                   "detail": f"{n_contig}/{n_tot} parcelles du résultat ont ≥1 parcelle contiguë "
                             "(≤1 m) du même SIREN — le signal « assemblage » n'exige PAS la "
                             "contiguïté (règle documentée : ≥3 parcelles même SIREN sur l'île)"})

    SORTIE.parent.mkdir(parents=True, exist_ok=True)
    with SORTIE.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["scenario", "app_count", "sql_count",
                                          "manquantes", "en_trop", "verdict", "detail"],
                           delimiter=";")
        w.writeheader()
        w.writerows(lignes)
    print(f"→ {SORTIE}")

    # dump des diffs complets pour l'enquête (stdout seulement)
    for nom, d in diffs.items():
        if d["manque"] or d["trop"]:
            print(f"\n{nom}\n  manquantes ({len(d['manque'])}) : {d['manque'][:20]}"
                  f"\n  en_trop ({len(d['trop'])}) : {d['trop'][:20]}")


if __name__ == "__main__":
    main()
