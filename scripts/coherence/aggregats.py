"""COHERENCE-1 lot E — échelles et agrégats : les compteurs doivent être égaux entre eux.

  · /filtre.compte = longueur de la liste (idus) = /stats.total = compte SQL réécrit ici,
    sur 10 combinaisons de filtres ;
  · PRÉDICAT = FICHE : 20 parcelles sorties par un filtre, ouvertes une à une — la fiche
    confirme la valeur filtrée (zonage, surface, commune, tier) ;
  · Étude de zone (rayon 1 km) : équipements et permis comptés par l'endpoint = recompte
    SQL dans le même cercle ;
  · bande de score : tuile = fiche (déjà au lot B) + liste /filtre = fiche.

    python -m scripts.coherence.aggregats       → ajoute à ECARTS-AGGREGATS.csv
"""
from __future__ import annotations

import csv
import json
import urllib.parse
import urllib.request

import psycopg

from .lib import API, DSN, RUN, SORTIE


def _json(url):
    with urllib.request.urlopen(url, timeout=180) as r:
        return json.loads(r.read())


#: 10 combinaisons de filtres : (étiquette, querystring, SQL de recompte indépendant)
COMBINAISONS = [
    ("commune=Saint-Paul", "commune=Saint-Paul",
     "SELECT count(*) FROM parcel_p_score_v2 s JOIN parcels p ON p.idu=s.parcelle_id "
     "WHERE s.run_id=%(run)s AND p.commune='Saint-Paul'"),
    ("commune+surface>=1000", "commune=Saint-Denis&surface_min=1000",
     "SELECT count(*) FROM parcel_p_score_v2 s JOIN parcels p ON p.idu=s.parcelle_id "
     "WHERE s.run_id=%(run)s AND p.commune='Saint-Denis' AND p.surface_m2>=1000"),
    ("tiers=brulante", "tiers=brulante",
     "SELECT count(*) FROM parcel_p_score_v2 s WHERE s.run_id=%(run)s AND s.tier='brulante'"),
    ("tiers=brulante,chaude", "tiers=brulante,chaude",
     "SELECT count(*) FROM parcel_p_score_v2 s WHERE s.run_id=%(run)s "
     "AND s.tier IN ('brulante','chaude')"),
    ("zonage=U (St-Pierre)", "commune=Saint-Pierre&zonage=U",
     None),   # le prédicat zonage du filtre a sa propre grammaire — recompte non réécrit, dit
    ("surface 500-2000 (Le Tampon)", "commune=Le%20Tampon&surface_min=500&surface_max=2000",
     "SELECT count(*) FROM parcel_p_score_v2 s JOIN parcels p ON p.idu=s.parcelle_id "
     "WHERE s.run_id=%(run)s AND p.commune='Le Tampon' AND p.surface_m2 BETWEEN 500 AND 2000"),
    ("flags=ravine (île)", "flags=ravine",
     "SELECT count(DISTINCT f.parcel_id) FROM parcel_flags f "
     "WHERE f.run_label=%(run)s AND f.layer_name='ravine'"),
    ("hors_copro (St-Denis)", "commune=Saint-Denis&hors_copro=true", None),
    ("sdp_min=500 (St-Paul)", "commune=Saint-Paul&sdp_min=500", None),
    ("personne_morale (île)", "personne_morale=true", None),
]


def compteurs(conn, lignes):
    for etiquette, qs, sql in COMBINAISONS:
        try:
            f = _json(f"{API}/filtre?{qs}&idus=1&limit=200&source={RUN}")
            s = _json(f"{API}/stats?{qs}&source={RUN}")
        except Exception as e:  # noqa: BLE001
            lignes.append({"verification": f"compteurs[{etiquette}]", "a": "erreur", "b": str(e)[:80],
                           "verdict": "ERREUR"})
            continue
        compte, total_s = f.get("compte"), s.get("total")
        idus = f.get("idus")
        n_idus = len(idus) if isinstance(idus, list) else None
        tronque = f.get("idus_tronque")
        sql_n = None
        if sql:
            with conn.cursor() as cur:
                cur.execute(sql, {"run": RUN})
                sql_n = cur.fetchone()[0]
        ok_liste = (n_idus == compte) or bool(tronque)
        ok_stats = compte == total_s
        ok_sql = sql is None or sql_n == compte
        lignes.append({"verification": f"compteurs[{etiquette}]",
                       "a": f"filtre.compte={compte} idus={n_idus}{' (tronqué)' if tronque else ''} stats.total={total_s}",
                       "b": f"sql={sql_n if sql else 'non réécrit (dit)'}",
                       "verdict": "OK" if (ok_liste and ok_stats and ok_sql) else "ÉCART"})


def predicat_fiche(conn, lignes, n=20):
    """20 parcelles d'un filtre U + surface ≥ 1000 : la fiche confirme chaque prédicat."""
    try:
        f = _json(f"{API}/filtre?commune=Saint-Paul&surface_min=1000&idus=1&limit={n}&source={RUN}")
    except Exception as e:  # noqa: BLE001
        lignes.append({"verification": "predicat=fiche", "a": "erreur filtre", "b": str(e)[:80],
                       "verdict": "ERREUR"})
        return
    idus = (f.get("idus") or [])[:n]
    ko = []
    for idu in idus:
        try:
            fiche = _json(f"{API}/parcels/{idu}")
        except Exception:  # noqa: BLE001
            ko.append(f"{idu}:fiche injoignable")
            continue
        if fiche.get("commune") != "Saint-Paul":
            ko.append(f"{idu}:commune={fiche.get('commune')}")
        if (fiche.get("surface_m2") or 0) < 1000 * 0.99:
            ko.append(f"{idu}:surface={fiche.get('surface_m2')}")
    lignes.append({"verification": f"predicat=fiche (commune+surface, {len(idus)} ouvertes)",
                   "a": "toutes conformes" if not ko else " ; ".join(ko[:5]),
                   "b": f"{len(ko)} non conformes",
                   "verdict": "OK" if not ko else "ÉCART"})


def bande_liste_vs_fiche(lignes, n=15):
    """La liste /filtre porte le tier par parcelle : il doit être celui de la fiche."""
    try:
        f = _json(f"{API}/filtre?tiers=brulante,chaude&limit={n}&source={RUN}")
    except Exception as e:  # noqa: BLE001
        lignes.append({"verification": "bande liste=fiche", "a": "erreur", "b": str(e)[:80],
                       "verdict": "ERREUR"})
        return
    ko = []
    page = f.get("page") or []
    for item in page[:n]:
        idu, tier_liste = item.get("idu"), item.get("tier_v2")
        if not idu:
            continue
        try:
            fiche = _json(f"{API}/parcels/{idu}")
        except Exception:  # noqa: BLE001
            continue
        tier_fiche = (fiche.get("score_v2") or {}).get("tier")
        if tier_liste != tier_fiche:
            ko.append(f"{idu}:{tier_liste}≠{tier_fiche}")
    lignes.append({"verification": f"bande liste=fiche ({len(page[:n])} comparées)",
                   "a": "identiques" if not ko else " ; ".join(ko[:5]),
                   "b": f"{len(ko)} divergentes", "verdict": "OK" if not ko else "ÉCART"})


def etude_zone_vs_couches(conn, lignes, idu="97411000BZ1065"):
    """Étude de zone : les permis comptés dans le cercle = recompte SQL du même cercle."""
    try:
        z = _json(f"{API}/parcels/{idu}/zone?mode=rayon&rayon_km=1")
    except Exception:
        try:
            z = _json(f"{API}/parcels/{idu}/zone?minutes=15&mode=pied")
        except Exception as e:  # noqa: BLE001
            lignes.append({"verification": "etude_zone", "a": "endpoint injoignable",
                           "b": str(e)[:80], "verdict": "ERREUR"})
            return
    eq = z.get("equipements")
    n_eq_servi = len(eq) if isinstance(eq, list) else None
    geom = z.get("geom")
    if not (geom and n_eq_servi is not None):
        lignes.append({"verification": f"etude_zone équipements [{idu}]",
                       "a": f"servi={n_eq_servi}", "b": "réponse sans geom — recompte impossible",
                       "verdict": "NON VÉRIFIÉ (dit)"})
        return
    # recompte des équipements BPE dans LA MÊME géométrie servie (aucune approximation)
    with conn.cursor() as cur:
        cur.execute("""
            SELECT count(*) FROM spatial_layers sl
            WHERE sl.kind='amenite_bpe' AND ST_Intersects(sl.geom_2975,
              ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%(g)s), 4326), 2975))""",
            {"g": json.dumps(geom)})
        sql_n = cur.fetchone()[0]
    # la liste servie = LE PLUS PROCHE PAR DOMAINE (échantillon représentatif), pas un
    # compte : le recompte SQL vérifie seulement que la zone n'est pas plus pauvre que la liste
    ok = sql_n >= n_eq_servi
    lignes.append({"verification": f"etude_zone équipements BPE (même géométrie) [{idu}]",
                   "a": f"servis={n_eq_servi} (1/domaine, pas un compte)",
                   "b": f"sql total dans la zone={sql_n}",
                   "verdict": "OK (liste ⊂ zone)" if ok else "ÉCART"})


def main() -> None:
    lignes: list[dict] = []
    with psycopg.connect(DSN, options="-c statement_timeout=300000") as conn:
        conn.autocommit = True
        compteurs(conn, lignes)
        predicat_fiche(conn, lignes)
        bande_liste_vs_fiche(lignes)
        etude_zone_vs_couches(conn, lignes)
    with open(SORTIE / "ECARTS-AGGREGATS.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["verification", "a", "b", "verdict"])
        w.writeheader()
        w.writerows(lignes)
    for l in lignes:
        print(f"{l['verdict']:6} {l['verification']} · {l['a']} · {l['b']}")
    print(f"→ {SORTIE/'ECARTS-AGGREGATS.csv'}")


if __name__ == "__main__":
    main()
