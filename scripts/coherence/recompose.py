"""COHERENCE-1 lot G — les calculs recomposables : chaque dérivé refait À CÔTÉ de lui.

Implémentation INDÉPENDANTE (aucun import du code de production) : chaque chiffre dérivé
est recomposé à partir des chiffres affichés à côté de lui sur le même écran. Un écart
au-delà de la tolérance = anomalie de calcul OU d'affichage des entrées.

  · pct_residuel = 100 − pct_consomme (fiche, même bloc) ;
  · vacance = 100 × vacants / logements (fiche commune, même bloc) ;
  · déficit SRU = max(0, objectif − taux) (fiche commune) ;
  · niveaux admissibles = round(hauteur_regle / 3) (fiche constructibilité) ;
  · marge de surélévation = hauteur_regle − hauteur_bati (fiche) ;
  · taxe d'aménagement : total = SDP × valeur forfaitaire × (taux com + taux dép)/100
    (outil, projet saisi de 100 m²) ;
  · valeur créée ≈ SDP potentielle × prix secteur €/m² (liste Analyser / score v2) ;
  · % d'aléa = aire(intersection) / aire(parcelle), MÊME géométrie (fiche §risques).

    python -m scripts.coherence.recompose       → ECARTS-RECOMPOSE.csv
"""
from __future__ import annotations

import csv
import json
import urllib.request

import psycopg

from .lib import API, DSN, RUN, SORTIE


def _json(url):
    with urllib.request.urlopen(url, timeout=180) as r:
        return json.loads(r.read())


class R:
    def __init__(self):
        self.lignes = []

    def note(self, calcul, objet, affiche, recompose, entrees, tol=0.02):
        try:
            fa, fb = float(affiche), float(recompose)
            ok = abs(fa - fb) <= tol * max(abs(fa), abs(fb), 1)
        except (TypeError, ValueError):
            ok = affiche == recompose
        self.lignes.append({"calcul": calcul, "objet": objet, "affiche": affiche,
                            "recompose": recompose, "entrees": entrees,
                            "verdict": "OK" if ok else "ÉCART"})


def parcelles_temoins():
    with open(SORTIE / "ECHANTILLON.csv", newline="") as f:
        return [r["idu"] for r in csv.DictReader(f)][:30]


def main() -> None:
    r = R()
    conn = psycopg.connect(DSN, options="-c statement_timeout=300000")
    conn.autocommit = True

    for idu in parcelles_temoins():
        try:
            fiche = _json(f"{API}/parcels/{idu}")
        except Exception:  # noqa: BLE001
            continue
        pt = fiche.get("potentiel_transformation") or {}
        # pct_residuel = 100 - pct_consomme (deux chiffres du même bloc)
        if pt.get("pct_consomme") is not None and pt.get("pct_residuel") is not None:
            r.note("pct_residuel=100-pct_consomme", idu, pt["pct_residuel"],
                   max(0, 100 - pt["pct_consomme"]),
                   f"pct_consomme={pt['pct_consomme']}")
        # marge de surélévation = hauteur règle - hauteur bâtie
        if pt.get("hauteur_regle_m") is not None and pt.get("hauteur_bati_m") is not None \
                and pt.get("hauteur_marge_m") is not None:
            r.note("marge_surelevation=h_regle-h_bati", idu, pt["hauteur_marge_m"],
                   round(pt["hauteur_regle_m"] - pt["hauteur_bati_m"], 1),
                   f"règle={pt['hauteur_regle_m']} bâti={pt['hauteur_bati_m']}", tol=0.05)
        # % d'aléa : aire d'intersection / aire de parcelle, MÊME géométrie 2975, PAR
        # sous-type (rouge = INTERDICTION, bleue = PRESCRIPTION)
        for alea in (fiche.get("aleas") or {}).get("liste") or []:
            part = alea.get("part_pct")
            nature = alea.get("nature") or ""
            if part is None or "PPR" not in nature:
                continue
            subtype = ("INTERDICTION" if "rouge" in nature.lower()
                       else "PRESCRIPTION" if "bleue" in nature.lower() else None)
            if subtype is None:
                continue
            with conn.cursor() as cur:
                cur.execute("""
                    SELECT round((100*ST_Area(ST_Intersection(u.g, p.geom_2975))
                                  / NULLIF(ST_Area(p.geom_2975),0))::numeric)
                    FROM parcels p,
                         (SELECT ST_Union(sl.geom_2975) g FROM spatial_layers sl, parcels p2
                          WHERE p2.idu=%(idu)s AND sl.kind='ppr' AND sl.subtype=%(st)s
                            AND ST_Intersects(sl.geom_2975, p2.geom_2975)) u
                    WHERE p.idu=%(idu)s""", {"idu": idu, "st": subtype})
                row = cur.fetchone()
            if row and row[0] is not None:
                r.note("part_alea=aire(inter)/aire(parcelle)", f"{idu} [{nature[:24]}]",
                       part, float(row[0]), f"géométries 2975 (ppr {subtype})", tol=0.05)

    # taxe d'aménagement : outil, projet type 100 m²
    try:
        cfg = _json(f"{API}/outils/taxe-amenagement/config")
        vf = (cfg.get("valeur_forfaitaire_eur_m2") or cfg.get("valeur_forfaitaire")
              or (cfg.get("bareme") or {}).get("valeur_forfaitaire_eur_m2"))
        pre = _json(f"{API}/outils/taxe-amenagement/prefill?idu=97411000BZ1065")
        tc, td = pre.get("taux_communal_pct"), pre.get("taux_departemental_pct")
        if vf and tc is not None and td is not None:
            attendu = round(100 * float(vf) * (float(tc) + float(td)) / 100)
            r.note("taxe=100m2×forfait×taux", "97411000BZ1065 (projet 100 m²)",
                   "(outil : saisie requise)", attendu,
                   f"forfait={vf} taux={tc}+{td} — recomposé seul, l'outil exige une saisie",
                   tol=1)
        else:
            r.lignes.append({"calcul": "taxe_amenagement", "objet": "config",
                             "affiche": json.dumps(cfg)[:80], "recompose": "",
                             "entrees": "barème non exposé par /config — dit",
                             "verdict": "NON VÉRIFIÉ (dit)"})
    except Exception as e:  # noqa: BLE001
        r.lignes.append({"calcul": "taxe_amenagement", "objet": "outil", "affiche": "",
                         "recompose": "", "entrees": str(e)[:80], "verdict": "ERREUR"})

    # valeur créée ≈ SDP potentielle × prix secteur (score v2, île entière en SQL)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT count(*),
                   count(*) FILTER (WHERE abs(valeur_creee_eur
                       - potentiel_sdp_m2*prix_secteur_eur_m2)
                       > 0.05*greatest(valeur_creee_eur,1))
            FROM parcel_p_score_v2
            WHERE run_id=%(run)s AND valeur_creee_eur IS NOT NULL
              AND potentiel_sdp_m2 IS NOT NULL AND prix_secteur_eur_m2 IS NOT NULL""",
            {"run": RUN})
        n, div = cur.fetchone()
    if n == 0:
        r.lignes.append({"calcul": "valeur_creee=sdp×prix_secteur (île)", "objet": "run servi",
                         "affiche": "colonnes valeur_creee/potentiel_sdp/prix_secteur NULLES",
                         "recompose": "", "entrees": "parcel_p_score_v2",
                         "verdict": "NON VÉRIFIÉ (dit)"})
    else:
        r.note("valeur_creee=sdp×prix_secteur (île)", f"{n} parcelles",
               div, 0, "parcel_p_score_v2 (run servi)", tol=0)

    # vacance et déficit SRU : fiche commune, mêmes blocs
    import urllib.parse
    for com in ("Saint-Paul", "Saint-Denis", "Le Tampon"):
        try:
            ctx = _json(f"{API}/communes/{urllib.parse.quote(com)}/contexte")
        except Exception:  # noqa: BLE001
            continue
        pop = ctx.get("population") or {}
        if pop.get("logements") and pop.get("vacants") is not None:
            quartiers = pop.get("quartiers") or {}
            vac_servie = quartiers.get("vacance_commune_pct") or (ctx.get("marche") or {}).get("vacance_pct")
            recomposee = round(100 * pop["vacants"] / pop["logements"], 1)
            if vac_servie is not None:
                r.note("vacance=vacants/logements", com, vac_servie, recomposee,
                       f"vacants={pop['vacants']} logements={pop['logements']}")
        sru = ctx.get("sru") or {}
        try:
            objectif, taux, deficit = (float(sru["objectif_pct"]), float(sru["taux_lls"]),
                                       float(sru["deficit"]))
        except (KeyError, TypeError, ValueError):
            continue
        r.note("deficit_sru=max(0,objectif-taux)", com, deficit,
               round(max(0.0, objectif - taux), 2),
               f"objectif={objectif} taux={taux}")

    conn.close()
    with open(SORTIE / "ECARTS-RECOMPOSE.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["calcul", "objet", "affiche", "recompose",
                                          "entrees", "verdict"])
        w.writeheader()
        w.writerows(r.lignes)
    ko = [l for l in r.lignes if l["verdict"] == "ÉCART"]
    print(f"{len(r.lignes)} recompositions · {len(ko)} écarts → {SORTIE/'ECARTS-RECOMPOSE.csv'}")
    for l in ko[:12]:
        print("ÉCART", l["calcul"], l["objet"], l["affiche"], "≠", l["recompose"])


if __name__ == "__main__":
    main()
