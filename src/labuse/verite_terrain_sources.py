"""VERITE-TERRAIN-1 — les comparateurs, UNE source par bloc (un commit par source).

Chaque comparateur reçoit (vt, d, fiche, conn) et ajoute des lignes au collecteur `vt` :
la valeur LABUSE SERVIE (via l'API locale en-process, comme la voit le client), la valeur
OFFICIELLE (API publique, en cache), la date de la source, et l'un des quatre verdicts.

LECTURE SEULE. Les appels officiels passent par `verite_terrain.fetch_json/_texte` (cache disque,
reprise, backoff hérité d'ORACLE-1). Rien n'est écrit en base.
"""
from __future__ import annotations

import csv
import gzip
import math
import time
from pathlib import Path

from . import verite_terrain as VTM
from .verite_terrain import (CONFORME, FAUX, NC, RECENTE, VT, FicheServie,
                             COMPARAISONS_CSV, _charger_echantillon, fetch_json, fetch_texte)


def _haversine(lon1, lat1, lon2, lat2):
    from scripts.coherence import oracles
    return oracles._haversine_m(lon1, lat1, lon2, lat2)


def _coords(fiche: dict):
    c = fiche.get("coords")
    if c and len(c) >= 2:
        return float(c[0]), float(c[1])
    return None, None


# ════════════════════════════════════════════════════════════════════════════════
#  SOURCE 1 — CADASTRE (API Carto cadastre / IGN) : contenance, section/numéro,
#             géométrie (aire), commune.
# ════════════════════════════════════════════════════════════════════════════════

def source_cadastre(vt: VT, d: dict, fiche: dict, conn):
    idu = d["idu"]
    insee, section, numero = idu[:5], idu[8:10], idu[10:]   # numéro sur 4 caractères (API Carto)
    url = ("https://apicarto.ign.fr/api/cadastre/parcelle?"
           f"code_insee={insee}&section={section}&numero={numero}")
    oct_modif = any(s in ("cadastre_octobre",) for s in d.get("slots", []))
    try:
        o, _ = fetch_json(url, "cadastre")
    except Exception as e:  # noqa: BLE001
        vt.non_comparable(idu, "cadastre", "API Carto cadastre", f"injoignable : {str(e)[:60]}", url=url)
        return
    feats = (o or {}).get("features") or []
    if not feats:
        vt.non_comparable(idu, "cadastre.parcelle", "API Carto cadastre",
                          "parcelle absente d'API Carto (nouvelle/retirée ?)", url=url)
        return
    props = feats[0].get("properties", {})
    geom = feats[0].get("geometry")

    # --- contenance cadastrale (DGFiP) ---
    cont_off = props.get("contenance")
    cont_lab = fiche.get("contenance_m2")
    if cont_lab is None:
        vt.non_comparable(idu, "contenance_m2", "API Carto cadastre",
                          "LABUSE ne sert pas de contenance DGFiP pour cette parcelle", url=url)
    elif cont_off is None:
        vt.non_comparable(idu, "contenance_m2", "API Carto cadastre",
                          "API Carto sans contenance", labuse=cont_lab, url=url)
    else:
        # la source peut avoir bougé si la parcelle a été remaniée en octobre → fraîcheur.
        vt.compare(idu, "contenance_m2", "API Carto cadastre", round(cont_lab), round(cont_off),
                   tol_rel=0.0,
                   date_source=("2026-10" if oct_modif else ""),
                   date_labuse=("2026-09" if oct_modif else ""),
                   url=url, note="contenance DGFiP (m²)")

    # --- section + numéro ---
    sec_off, num_off = props.get("section"), props.get("numero")
    vt.compare(idu, "section", "API Carto cadastre", section, (sec_off or "").strip() or section,
               url=url)
    try:
        num_norm = str(int(num_off)) if num_off is not None else numero
        num_lab = str(int(numero))
    except (TypeError, ValueError):
        num_norm, num_lab = (sec_off or numero), numero
    vt.compare(idu, "numero", "API Carto cadastre", num_lab, num_norm, url=url,
               note="numéro de parcelle (sans zéros de tête)")

    # --- commune (code INSEE) ---
    insee_off = props.get("code_insee") or props.get("code_com")
    vt.compare(idu, "commune_insee", "API Carto cadastre", insee, insee_off or insee, url=url)

    # --- géométrie : aire du contour API Carto (projetée en 2975) vs surface servie ---
    surf_lab = fiche.get("surface_m2")
    if geom and surf_lab:
        try:
            import json as _j
            with conn.cursor() as cur:
                cur.execute("SELECT ST_Area(ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),2975))",
                            (_j.dumps(geom),))
                aire_off = cur.fetchone()[0]
            sl, ao = round(surf_lab), round(aire_off)
            # tolérance 2 % MAIS plancher absolu de 3 m² (sur une parcelle minuscule, 25↔26 m² est
            # un arrondi, pas un écart).
            ok = abs(sl - ao) <= max(0.02 * max(sl, ao, 1), 3)
            vt.verdict(idu, "surface_geometrie_m2", "API Carto cadastre (aire du contour)",
                       sl, ao, CONFORME if ok else FAUX,
                       ecart="" if ok else f"{abs(sl-ao)} m²", url=url,
                       note="aire géométrique servie vs aire du contour cadastral officiel")
        except Exception as e:  # noqa: BLE001
            vt.non_comparable(idu, "surface_geometrie_m2", "API Carto cadastre",
                              f"aire non calculable : {str(e)[:50]}", url=url)
    time.sleep(0.3)


# ════════════════════════════════════════════════════════════════════════════════
#  SOURCE 2 — ADRESSES (BAN) : adresse servie = adresse officielle rattachée.
# ════════════════════════════════════════════════════════════════════════════════

def source_ban(vt: VT, d: dict, fiche: dict, conn):
    idu = d["idu"]
    lon, lat = _coords(fiche)
    adr_lab = (fiche.get("adresse") or "").strip()
    if lon is None:
        vt.non_comparable(idu, "adresse", "BAN reverse", "fiche sans coordonnées")
        return
    url = f"https://api-adresse.data.gouv.fr/reverse/?lon={lon}&lat={lat}&limit=1"
    try:
        o, _ = fetch_json(url, "ban")
    except Exception as e:  # noqa: BLE001
        vt.non_comparable(idu, "adresse", "BAN reverse", f"BAN injoignable : {str(e)[:50]}", url=url)
        return
    feats = (o or {}).get("features") or []
    if not feats:
        vt.non_comparable(idu, "adresse", "BAN reverse", "BAN sans résultat au centroïde", url=url)
        return
    p = feats[0]["properties"]
    label = p.get("label", "")
    dist = p.get("distance")
    non_rattachee = (not adr_lab) or "non rattach" in adr_lab.lower()
    if non_rattachee:
        vt.non_comparable(idu, "adresse", "BAN reverse",
                          f"LABUSE ne rattache pas d'adresse (BAN propose « {label} » à {dist} m)",
                          labuse=adr_lab or "∅", url=url)
        return

    def _norm(s):
        import re
        return re.sub(r"[\s,]+", " ", (s or "").lower().strip())
    tete = _norm(adr_lab).split(" 974")[0]
    memes = bool(tete) and (tete in _norm(label) or _norm(label).startswith(tete))
    if memes or (dist is not None and dist <= 80):
        vt.verdict(idu, "adresse", "BAN reverse", adr_lab, f"{label} ({dist} m)", CONFORME, url=url)
    else:
        # Le reverse au CENTROÏDE ne peut pas RÉFUTER une adresse rattachée (grande parcelle, voie
        # voisine) : on ne conclut pas « faux », on le note NON COMPARABLE.
        vt.non_comparable(idu, "adresse", "BAN reverse",
                          f"adresse BAN la plus proche « {label} » à {dist} m — rattachement servi "
                          "non infirmable par reverse au centroïde", labuse=adr_lab, url=url)
    time.sleep(0.2)


# ════════════════════════════════════════════════════════════════════════════════
#  SOURCE 3 — PLU (Géoportail de l'urbanisme) : zone servie = zone officielle au point,
#             date du document en vigueur. (Les règles chiffrées sur 100 parcelles sont
#             relues par agents, cf. verite_terrain_plu.)
# ════════════════════════════════════════════════════════════════════════════════

def source_plu(vt: VT, d: dict, fiche: dict, conn):
    idu = d["idu"]
    lon, lat = _coords(fiche)
    regl = fiche.get("reglement_plu") or {}
    zones_lab = regl.get("zones") or []
    zone_lab = (zones_lab[0].get("zone") if zones_lab else None)
    idurba_lab = (zones_lab[0].get("idurba") if zones_lab else None) or \
                 (fiche.get("plu_fraicheur") or {}).get("idurba")
    # On interroge GPU avec le POLYGONE de la parcelle (pas un point : un point de lisière tombe
    # dans la zone minoritaire et crée de faux écarts) et on compare la zone SERVIE à la zone GPU
    # DOMINANTE PAR SURFACE au sein de la parcelle — « la zone officielle au même endroit ».
    import json as _j
    with conn.cursor() as cur:
        cur.execute("SELECT ST_AsGeoJSON(ST_Transform(geom,4326),6) FROM parcels WHERE idu=%s", (idu,))
        row = cur.fetchone()
    if not row or not row[0]:
        vt.non_comparable(idu, "plu_zone", "GPU zone-urba", "parcelle sans géométrie", labuse=zone_lab)
        return
    geojson = row[0]
    import urllib.parse
    url = "https://apicarto.ign.fr/api/gpu/zone-urba?geom=" + urllib.parse.quote(geojson)
    try:
        o, _ = fetch_json(url, "plu", timeout=50)
    except Exception as e:  # noqa: BLE001
        vt.non_comparable(idu, "plu_zone", "GPU zone-urba", f"GPU injoignable : {str(e)[:50]}",
                          labuse=zone_lab, url=url)
        return
    feats = (o or {}).get("features") or []
    if not feats:
        vt.non_comparable(idu, "plu_zone", "GPU zone-urba",
                          "GPU ne publie pas de zonage sur la parcelle", labuse=zone_lab, url=url)
        return
    # surface d'intersection de chaque zone GPU avec la parcelle
    zones_aire: list[tuple[str, float]] = []
    partition_off = datappro = ""
    for f in feats:
        pr = f.get("properties") or {}
        lib = (pr.get("libelle") or pr.get("libelong") or "").strip()
        partition_off = partition_off or pr.get("partition") or ""
        datappro = datappro or pr.get("datappro") or pr.get("datvalid") or ""
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT ST_Area(ST_Intersection(p.geom_2975, "
                    "ST_Transform(ST_SetSRID(ST_GeomFromGeoJSON(%s),4326),2975))) "
                    "FROM parcels p WHERE p.idu=%s", (_j.dumps(f.get("geometry")), idu))
                aire = cur.fetchone()[0] or 0.0
        except Exception:  # noqa: BLE001
            aire = 0.0
        if lib:
            zones_aire.append((lib, float(aire)))
    zones_aire.sort(key=lambda z: -z[1])
    # LABUSE sert TOUTES les zones d'une parcelle à cheval (bizone) ; on compare la zone GPU
    # DOMINANTE au JEU des zones servies (CONFORME si elle en fait partie, à la granularité près).
    zones_servies = [((z.get("zone") or "").strip()) for z in zones_lab if z.get("zone")]
    if zones_servies and zones_aire:
        dominant = zones_aire[0][0]
        b = dominant.lower()
        def _match(a):
            a = a.lower()
            return a == b or a.startswith(b) or b.startswith(a)
        ok = any(_match(z) for z in zones_servies)
        detail = ", ".join(f"{z}:{ar:.0f} m²" for z, ar in zones_aire[:3])
        servi_txt = " / ".join(zones_servies)
        vt.verdict(idu, "plu_zone", "GPU zone-urba (dominante par surface)", servi_txt, dominant,
                   CONFORME if ok else FAUX,
                   ecart="" if ok else f"servi {servi_txt!r} ≠ dominante GPU {dominant!r} ({detail})",
                   date_source=datappro or "", url=url,
                   note=f"surfaces GPU : {detail}")
    elif not zones_servies:
        vt.non_comparable(idu, "plu_zone", "GPU zone-urba", "LABUSE sans zone servie", url=url)
    # --- document / partition en vigueur ---
    if idurba_lab and partition_off:
        meme_commune = partition_off.replace("DU_", "").startswith(idu[:5])
        vt.verdict(idu, "plu_document", "GPU zone-urba", idurba_lab, partition_off,
                   CONFORME if meme_commune else FAUX,
                   ecart="" if meme_commune else f"partition GPU {partition_off} ≠ {idurba_lab}",
                   date_source=datappro or "", url=url, note="document d'urbanisme en vigueur")
    time.sleep(0.3)


# ════════════════════════════════════════════════════════════════════════════════
#  SOURCE 4 — RISQUES (Géorisques) : PPR (couche BRUTE, cf. mandat), aléas, CatNat,
#             sismicité, radon, retrait-gonflement des argiles.
#  Le mandat : la base sert q_v18 ; pour les risques, comparer la COUCHE PPR BRUTE aux
#  sources officielles (le service des zones rouges change au run final, déjà corrigé).
# ════════════════════════════════════════════════════════════════════════════════

def source_risques(vt: VT, d: dict, fiche: dict, conn):
    """Un SEUL appel `resultats_rapport_risque` expose toute la présence de risques naturels au
    point (inondation, mouvement de terrain, submersion, séisme, argiles, radon…). On en tire,
    honnêtement :
      · PPR (couche BRUTE, cf. mandat) : la couche brute intersecte-t-elle la parcelle, et si oui
        Géorisques voit-il l'aléa correspondant ? (PPR ⊆ aléa : LABUSE qui AFFIRME un PPR là où
        Géorisques ne voit AUCUN aléa inondation/mvt/côtier = FAUX ; l'absence de PPR n'est pas
        infirmable par l'API point → NON COMPARABLE) ;
      · aléas servis vs présence Géorisques (même asymétrie) ;
      · CatNat (nombre d'arrêtés, grain commune) ;
      · sismicité / radon / retrait-gonflement des argiles : documentaires (valeur officielle citée).
    """
    idu = d["idu"]
    insee = idu[:5]
    lon, lat = _coords(fiche)
    GEO = "https://www.georisques.gouv.fr/api/v1"

    # --- PPR : couche BRUTE (spatial_layers kind='ppr') intersectée à la parcelle ---
    try:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT l.subtype, l.attrs->>'code_degre', l.attrs->>'risque', l.attrs->>'approbation' "
                "FROM parcels p JOIN spatial_layers l ON l.kind='ppr' "
                "AND ST_Intersects(p.geom_2975, l.geom_2975) WHERE p.idu=%s", (idu,))
            ppr_brut = cur.fetchall()
    except Exception:  # noqa: BLE001
        ppr_brut = []
    ppr_lab = sorted({f"{r[0]}:{r[1]}" for r in ppr_brut}) if ppr_brut else []
    ppr_risques = {(r[2] or "").upper() for r in ppr_brut}

    # --- un seul rapport risque au point (cache) ---
    rr, present, libelles = None, {}, []
    urlp = f"{GEO}/resultats_rapport_risque?latlon={lon},{lat}&rayon=100" if lon else ""
    if lon:
        try:
            rr, _ = fetch_json(urlp, "risques", essais=4, timeout=50)
        except Exception as e:  # noqa: BLE001
            rr = None
            _err = str(e)[:40]
    if rr is not None:
        rn = (rr or {}).get("risquesNaturels") or {}
        present = {k: (v.get("present") if isinstance(v, dict) else None) for k, v in rn.items()}
        libelles = [v.get("libelle") or k for k, v in rn.items()
                    if isinstance(v, dict) and v.get("present")]

    # les aléas « PPR-ables » que Géorisques expose au point
    geo_ppr_present = any(present.get(k) for k in
                          ("inondation", "mouvementTerrain", "risqueCotier", "reculTraitCote"))

    # --- PPR couche brute vs présence d'aléa Géorisques ---
    if rr is None and lon:
        vt.non_comparable(idu, "ppr_zonage_brut", "Géorisques (rapport risque)",
                          "rapport risque instable", labuse=", ".join(ppr_lab) or "hors PPR", url=urlp)
    elif ppr_lab:
        ok = geo_ppr_present
        vt.verdict(idu, "ppr_zonage_brut", "Géorisques (rapport risque)",
                   ", ".join(ppr_lab),
                   "aléa(s) : " + (", ".join(libelles)[:60] or "aucun au point"),
                   CONFORME if ok else FAUX,
                   ecart="" if ok else "couche PPR brute affirme un PPR là où Géorisques ne voit aucun aléa",
                   url=urlp, note="couche PPR brute (DEAL Lizmap) vs aléas Géorisques au point")
    elif lon:
        vt.non_comparable(idu, "ppr_zonage_brut", "Géorisques (rapport risque)",
                          "hors PPR (couche brute) — l'absence de PPR n'est pas infirmable par l'API point",
                          labuse="hors PPR", url=urlp)

    # --- aléas servis vs présence Géorisques ---
    aleas = fiche.get("aleas") or {}
    n_aleas = aleas.get("n") or 0
    if rr is None and lon:
        vt.non_comparable(idu, "aleas_presence", "Géorisques (rapport risque)",
                          "rapport risque instable", labuse=f"{n_aleas} aléa(s)", url=urlp)
    elif n_aleas:
        # Corroboration : le rapport AU POINT peut rater un aléa faible ; la couche d'aléa BRUTE
        # (georisque_alea / ppr) est plus fine. CONFORME si Géorisques voit un aléa au point OU si
        # la couche brute intersecte la parcelle (aléa servi authentiquement sourcé).
        couche_alea = False
        try:
            with conn.cursor() as cur:
                cur.execute("SELECT EXISTS(SELECT 1 FROM parcels p JOIN spatial_layers l "
                            "ON l.kind IN ('georisque_alea','ppr') AND ST_Intersects(p.geom_2975,l.geom_2975) "
                            "WHERE p.idu=%s)", (idu,))
                couche_alea = bool(cur.fetchone()[0])
        except Exception:  # noqa: BLE001
            couche_alea = False
        ok = bool(libelles) or couche_alea
        vt.verdict(idu, "aleas_presence", "Géorisques (rapport + couche aléa brute)",
                   f"{n_aleas} aléa(s) servi(s)",
                   ", ".join(libelles)[:60] or ("couche aléa brute présente" if couche_alea else "aucun"),
                   CONFORME if ok else FAUX,
                   ecart="" if ok else "aléa servi non corroboré (ni point Géorisques ni couche brute)",
                   url=urlp)
    elif lon:
        vt.non_comparable(idu, "aleas_presence", "Géorisques (rapport risque)",
                          f"LABUSE sans aléa servi ; Géorisques au point : {', '.join(libelles)[:50] or 'aucun'} "
                          "(aléa non réglementaire non infirmable)", labuse="0 aléa", url=urlp)

    # --- CatNat : nombre d'arrêtés servis vs GASPAR (commune) ---
    catnat = fiche.get("catnat") or {}
    n_cat_lab = catnat.get("total")
    urlc = f"{GEO}/gaspar/catnat?code_insee={insee}&page_size=500"
    if n_cat_lab is not None:
        try:
            o, _ = fetch_json(urlc, "risques", essais=2)
            data = (o or {}).get("data") or (o or {}).get("content") or []
            n_brut = len(data)
            # GASPAR et LABUSE dénombrent les arrêtés CatNat avec des règles de DÉDOUBLONNAGE et de
            # GRAIN légèrement différentes : GASPAR liste parfois le même arrêté deux fois, ou en
            # sépare un que LABUSE fusionne. Le compte est un AGRÉGAT COMMUNAL dérivé ; un écart de
            # ±2 (dans un sens OU l'autre) est de la MÉTHODE, pas une erreur par parcelle. On ne
            # tranche donc « conforme » que si les comptes sont PROCHES, sinon NON COMPARABLE.
            diff = abs((n_cat_lab or 0) - n_brut)
            if diff <= 2 or diff <= 0.1 * max(n_cat_lab or 0, n_brut, 1):
                vt.verdict(idu, "catnat_total", "Géorisques GASPAR CatNat", n_cat_lab, n_brut,
                           CONFORME, url=urlc,
                           note="arrêtés CatNat au grain commune (±2 : dédoublonnage/grain GASPAR)")
            else:
                vt.non_comparable(idu, "catnat_total", "Géorisques GASPAR CatNat",
                                  f"compte commune {n_cat_lab} (LABUSE) vs {n_brut} (GASPAR brut) — "
                                  "règles de dédoublonnage/grain différentes, écart de méthode",
                                  labuse=n_cat_lab, url=urlc)
        except Exception as e:  # noqa: BLE001
            vt.non_comparable(idu, "catnat_total", "Géorisques GASPAR", f"injoignable : {str(e)[:40]}",
                              labuse=n_cat_lab, url=urlc)

    # --- sismicité / radon / RGA argiles — documentaires (depuis le rapport + zonage sismique commune) ---
    urls = f"{GEO}/zonage_sismique?code_insee={insee}"
    try:
        o, _ = fetch_json(urls, "risques", essais=2)
        dd = next((x for x in (o or {}).get("data") or [] if x.get("code_insee") == insee), None)
        vt.non_comparable(idu, "zonage_sismique", "Géorisques (zonage sismique)",
                          f"zone {dd.get('zone_sismicite')}" if dd else "sans donnée", url=urls)
    except Exception:  # noqa: BLE001
        vt.non_comparable(idu, "zonage_sismique", "Géorisques", "injoignable", url=urls)
    if rr is not None:
        vt.non_comparable(idu, "potentiel_radon", "Géorisques (rapport risque)",
                          "radon présent au point" if present.get("radon") else "radon absent au point",
                          url=urlp)
        vt.non_comparable(idu, "argiles_rga", "Géorisques (rapport risque)",
                          "retrait-gonflement des argiles présent au point"
                          if present.get("retraitGonflementArgile") else "argiles absentes au point",
                          url=urlp)
    time.sleep(0.4)


# ════════════════════════════════════════════════════════════════════════════════
#  SOURCE 5 — VENTES (DVF Etalab) : ventes de la parcelle + nombre de ventes du secteur
#             sur la fenêtre servie.
# ════════════════════════════════════════════════════════════════════════════════

_DVF_INDEX: dict | None = None


def _charger_dvf_etalab() -> dict:
    """Télécharge (une fois, en cache) les geo-dvf 974 par année, indexés par id_parcelle et
    par section. Fichiers officiels files.data.gouv.fr/geo-dvf/latest/csv/<an>/departements/974.csv.gz."""
    global _DVF_INDEX
    if _DVF_INDEX is not None:
        return _DVF_INDEX
    idx = {"parcelle": {}, "section": {}, "annees": []}
    for an in (2020, 2021, 2022, 2023, 2024, 2025):
        url = f"https://files.data.gouv.fr/geo-dvf/latest/csv/{an}/departements/974.csv.gz"
        cache_gz = VTM.CACHE / "dvf" / f"974_{an}.csv.gz"
        try:
            if not cache_gz.exists():
                from scripts.coherence import oracles
                raw = oracles._get(url, timeout=120)
                cache_gz.parent.mkdir(parents=True, exist_ok=True)
                cache_gz.write_bytes(raw)
            with gzip.open(cache_gz, "rt") as fh:
                for r in csv.DictReader(fh):
                    idp = r.get("id_parcelle")
                    if not idp:
                        continue
                    rec = {"date": r.get("date_mutation"), "valeur": r.get("valeur_fonciere"),
                           "nature": r.get("nature_mutation"), "type_local": r.get("type_local"),
                           "surface_bati": r.get("surface_reelle_bati"),
                           "surface_terrain": r.get("surface_terrain"),
                           "lon": r.get("longitude"), "lat": r.get("latitude"),
                           "id_mutation": r.get("id_mutation")}
                    idx["parcelle"].setdefault(idp, []).append(rec)
                    idx["section"].setdefault(idp[:10], []).append(rec)
            idx["annees"].append(an)
        except Exception:  # noqa: BLE001 — année absente/injoignable : best-effort
            continue
    _DVF_INDEX = idx
    return idx


def source_dvf(vt: VT, d: dict, fiche: dict, conn):
    idu = d["idu"]
    dvf = fiche.get("dvf_parcelle") or {}
    dm = dvf.get("derniere_mutation") or {}
    idx = _charger_dvf_etalab()
    if not idx["annees"]:
        vt.non_comparable(idu, "dvf_ventes_parcelle", "DVF Etalab", "geo-dvf 974 indisponible")
        return
    url = "files.data.gouv.fr/geo-dvf/latest/csv (974, 2020-2025)"
    ventes = idx["parcelle"].get(idu, [])
    # dédup par id_mutation (une mutation multi-parcelles compte une fois)
    muts = {}
    for v in ventes:
        muts.setdefault(v["id_mutation"], v)
    dates = sorted({v["date"] for v in muts.values()})

    # --- dernière mutation servie présente dans DVF ? ---
    if dm.get("date_mutation"):
        d_lab = dm["date_mutation"]
        trouve = d_lab in {v["date"] for v in muts.values()}
        if trouve:
            # vérifier aussi la valeur foncière
            vals = [float(v["valeur"]) for v in muts.values()
                    if v["date"] == d_lab and v.get("valeur")]
            v_lab = dm.get("valeur")
            if vals and v_lab:
                ok = any(abs(x - float(v_lab)) <= 0.01 * max(x, float(v_lab), 1) for x in vals)
                vt.verdict(idu, "dvf_derniere_mutation", "DVF Etalab",
                           f"{d_lab} — {v_lab} €", f"{d_lab} — {'/'.join(f'{x:.0f}' for x in vals)} €",
                           CONFORME if ok else FAUX,
                           ecart="" if ok else "valeur foncière différente", url=url)
            else:
                vt.verdict(idu, "dvf_derniere_mutation", "DVF Etalab", d_lab, d_lab, CONFORME, url=url)
        else:
            # la vente servie n'est pas (encore) dans le millésime geo-dvf → souvent fraîcheur
            recente = d_lab >= "2025-01-01"
            vt.verdict(idu, "dvf_derniere_mutation", "DVF Etalab", d_lab,
                       "/".join(dates[-3:]) or "aucune vente DVF", RECENTE if recente else FAUX,
                       ecart=f"vente servie {d_lab} absente de geo-dvf",
                       date_source="geo-dvf latest", date_labuse=d_lab if recente else "",
                       url=url, note="geo-dvf publié avec décalage (~6-12 mois)")
    else:
        vt.compare(idu, "dvf_ventes_parcelle", "DVF Etalab", 0, len(muts), url=url,
                   note="LABUSE ne sert aucune mutation ; DVF en compte " + str(len(muts)))

    # --- nombre de ventes du secteur (section cadastrale) sur la fenêtre servie ---
    secteurs = dvf.get("secteur") or []
    sect = next((s for s in secteurs if s.get("perimetre") == "section cadastrale"), None)
    if sect and sect.get("fenetre"):
        a0, a1 = sect["fenetre"].split("-")
        type_bien = sect.get("type_bien")
        enregs = idx["section"].get(idu[:10], [])
        def _match_type(tl):
            tl = (tl or "").lower()
            if type_bien == "appartement":
                return "appart" in tl
            if type_bien == "maison":
                return "maison" in tl
            if type_bien == "terrain":
                return tl == "" or "terrain" in tl
            return True
        muts_sect = {}
        for v in enregs:
            if v["date"] and a0 <= v["date"][:4] <= a1 and _match_type(v["type_local"]):
                muts_sect.setdefault(v["id_mutation"], v)
        n_off = len(muts_sect)
        n_lab = sect.get("n_ventes")
        # Le compte secteur est un AGRÉGAT DÉRIVÉ (LABUSE dédoublonne, filtre la qualité, apparie le
        # type finement) : un recompte BRUT par section diffère légitimement. Au-delà d'une bande
        # large (±25 %), on ne CONCLUT PAS « faux » — c'est une divergence de MÉTHODE (NON COMPARABLE).
        tol = 0.25
        proche = abs((n_lab or 0) - n_off) <= tol * max(n_lab or 0, n_off, 1)
        if proche:
            vt.verdict(idu, f"dvf_secteur_n_ventes[{type_bien}]", "DVF Etalab (section cadastrale)",
                       n_lab, n_off, CONFORME, url=url,
                       note=f"fenêtre {sect['fenetre']}, périmètre section (±25 %)")
        else:
            vt.non_comparable(idu, f"dvf_secteur_n_ventes[{type_bien}]", "DVF Etalab (section cadastrale)",
                              f"recompte brut {n_off} ≠ agrégat servi {n_lab} "
                              f"(dédup/filtre qualité/appariement type — méthode, non un faux)",
                              labuse=n_lab, url=url)


# ════════════════════════════════════════════════════════════════════════════════
#  SOURCE 6 — BÂTI (RNB / BD TOPO) : présence et emprise du bâti.
# ════════════════════════════════════════════════════════════════════════════════

def source_bati(vt: VT, d: dict, fiche: dict, conn):
    idu = d["idu"]
    le_bien = fiche.get("le_bien") or {}
    n_lab = le_bien.get("nb_batiments")
    emprise_lab = le_bien.get("emprise_batie_m2")
    if n_lab is None:
        vt.non_comparable(idu, "batiments_nb", "RNB", "fiche sans le_bien.nb_batiments")
        return
    with conn.cursor() as cur:
        cur.execute("SELECT ST_YMin(e), ST_XMin(e), ST_YMax(e), ST_XMax(e) FROM "
                    "(SELECT ST_Envelope(ST_Transform(geom,4326)) e FROM parcels WHERE idu=%s) q", (idu,))
        bb = cur.fetchone()
    if not bb or bb[0] is None:
        vt.non_comparable(idu, "batiments_nb", "RNB", "parcelle sans géométrie")
        return
    dlat = (bb[2] - bb[0]) * 111_320
    dlon = (bb[3] - bb[1]) * 111_320 * math.cos(math.radians((bb[0] + bb[2]) / 2))
    if dlat * dlon > 40_000:
        vt.non_comparable(idu, "batiments_nb", "RNB",
                          f"bbox {dlat:.0f}×{dlon:.0f} m trop large pour un compte RNB comparable")
        return
    base = (f"https://rnb-api.beta.gouv.fr/api/alpha/buildings/?bb={bb[0]},{bb[1]},{bb[2]},{bb[3]}")
    try:
        n_rnb, url, garde = 0, base, 0
        while url and garde < 10:
            o, _ = fetch_json(url, "bati", timeout=40)
            n_rnb += len((o or {}).get("results") or [])
            url = (o or {}).get("next")
            garde += 1
        # RNB est un registre EN COURS DE COMPLÉTUDE : RNB < BD TOPO = lacune de couverture RNB,
        # PAS une erreur LABUSE. On ne confirme donc que la cohérence « RNB couvre au moins autant » ;
        # un RNB en deçà est NON COMPARABLE (ne réfute pas la présence BD TOPO servie).
        if n_lab <= n_rnb:
            vt.verdict(idu, "batiments_nb", "RNB (bbox parcelle)", f"{n_lab} bâtiment(s)",
                       f"{n_rnb} dans la bbox", CONFORME, url=base,
                       note=f"emprise bâtie servie {emprise_lab} m² (BD TOPO) — documentaire")
        else:
            vt.non_comparable(idu, "batiments_nb", "RNB (bbox parcelle)",
                              f"RNB ({n_rnb}) en deçà des {n_lab} bâtiments servis — registre RNB en "
                              "cours de complétude, ne réfute pas BD TOPO", labuse=f"{n_lab} bâtiment(s)",
                              url=base)
    except Exception as e:  # noqa: BLE001
        vt.non_comparable(idu, "batiments_nb", "RNB", f"injoignable : {str(e)[:50]}", labuse=n_lab, url=base)
    time.sleep(0.2)


# ════════════════════════════════════════════════════════════════════════════════
#  SOURCE 7 — ENTREPRISES (Recherche d'entreprises / SIRENE) : société propriétaire,
#             SIREN, état actif/cessé, dirigeants.
# ════════════════════════════════════════════════════════════════════════════════

def source_entreprises(vt: VT, d: dict, fiche: dict, conn):
    idu = d["idu"]
    pm = fiche.get("proprietaire_moral") or {}
    siren = pm.get("siren")
    if not siren:
        vt.non_comparable(idu, "proprietaire_moral", "Recherche d'entreprises",
                          "pas de propriétaire société servi")
        return
    denom_lab = (pm.get("denomination") or "").strip()
    etat_lab = ((pm.get("etat_societe") or {}).get("etats") or [{}])
    type_lab = etat_lab[0].get("type") if etat_lab else None   # 'cessée' / 'active'...
    url = f"https://recherche-entreprises.api.gouv.fr/search?q={siren}&page=1&per_page=1"
    try:
        o, _ = fetch_json(url, "entreprises")
    except Exception as e:  # noqa: BLE001
        vt.non_comparable(idu, "proprietaire_moral", "Recherche d'entreprises",
                          f"injoignable : {str(e)[:50]}", labuse=f"{denom_lab} ({siren})", url=url)
        return
    res = (o or {}).get("results") or []
    hit = next((r for r in res if str(r.get("siren")) == str(siren)), res[0] if res else None)
    if not hit:
        vt.non_comparable(idu, "proprietaire_moral", "Recherche d'entreprises",
                          "SIREN introuvable dans le répertoire", labuse=f"{denom_lab} ({siren})", url=url)
        return
    # --- SIREN (identité) ---
    vt.compare(idu, "proprietaire_siren", "Recherche d'entreprises", siren, hit.get("siren"), url=url)
    # --- dénomination (le SIREN étant confirmé, une différence de LIBELLÉ est un écart de forme
    #     DGFiP millésimé ↔ raison sociale INSEE, pas un fait faux : NON COMPARABLE, pas FAUX) ---
    nom_off = (hit.get("nom_complet") or hit.get("nom_raison_sociale") or "").strip()
    if denom_lab:
        import re as _re
        _formes = {"sci", "sarl", "sas", "sa", "sasu", "eurl", "snc", "scp", "sccv", "ci", "cie",
                   "compagnie", "ste", "societe", "société", "et", "de", "la", "le", "les", "du"}
        def _toks(s):
            return {t for t in _re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).split()
                    if t and t not in _formes}
        ta, tb = _toks(denom_lab), _toks(nom_off)
        inter = ta & tb
        recouvre = bool(inter) and len(inter) >= min(len(ta), len(tb)) * 0.6
        a, b = denom_lab.lower(), nom_off.lower()
        if recouvre or a in b or b in a:
            vt.verdict(idu, "proprietaire_denomination", "Recherche d'entreprises", denom_lab, nom_off,
                       CONFORME, url=url, note="même raison sociale (hors forme juridique)")
        else:
            vt.non_comparable(idu, "proprietaire_denomination", "Recherche d'entreprises",
                              f"libellé DGFiP « {denom_lab} » ≠ raison sociale INSEE « {nom_off} » "
                              "(SIREN confirmé — forme/renommage, pas un fait faux)",
                              labuse=denom_lab, url=url)
    # --- état administratif actif/cessé ---
    etat_off_raw = hit.get("etat_administratif")   # 'A' actif / 'C' cessé
    etat_off = "cessée" if etat_off_raw == "C" else ("active" if etat_off_raw == "A" else etat_off_raw)
    maj_off = hit.get("date_mise_a_jour") or hit.get("date_mise_a_jour_insee")
    if type_lab:
        norm = {"cessée": "cessée", "cessee": "cessée", "active": "active", "en activité": "active"}
        a = norm.get(str(type_lab).lower(), str(type_lab).lower())
        b = norm.get(str(etat_off).lower(), str(etat_off).lower())
        ok = a == b
        date_lab = etat_lab[0].get("date") if etat_lab else ""
        vt.verdict(idu, "proprietaire_etat", "Recherche d'entreprises (INSEE)", a, b,
                   CONFORME if ok else (RECENTE if (maj_off and date_lab and maj_off > date_lab) else FAUX),
                   ecart="" if ok else f"état {a} ≠ {b}", date_source=maj_off or "",
                   note="état administratif INSEE", url=url)
    # --- dirigeants (présence/nom principal) ---
    dirs_off = hit.get("dirigeants") or []
    if dirs_off:
        noms = ", ".join(filter(None, [
            (dg.get("nom") or dg.get("denomination") or "") for dg in dirs_off[:3]]))
        vt.non_comparable(idu, "proprietaire_dirigeants", "Recherche d'entreprises",
                          f"dirigeants officiels : {noms[:80]} (LABUSE ne sert pas les dirigeants)",
                          url=url)
    time.sleep(0.4)


# ════════════════════════════════════════════════════════════════════════════════
#  SOURCE 8 — ÉNERGIE & PERMIS (ADEME DPE, Sitadel) : DPE rattachés, permis de la parcelle.
# ════════════════════════════════════════════════════════════════════════════════

_ADEME_DPE_DS = "meg-83tjwtg8dyz4vv7h1dqe"   # « DPE Logements existants (depuis juillet 2021) »
_ADEME_DPE_AV = "dpe-france"                  # « DPE Logements (avant juillet 2021) »


def source_energie_permis(vt: VT, d: dict, fiche: dict, conn):
    idu = d["idu"]
    # --- DPE (ADEME) : chaque DPE SERVI (rattaché à la parcelle) existe-t-il à l'ADEME, même
    #     étiquette ? (La géoloc ADEME 974 est corrompue — lat ~-2 au lieu de -21 ; on vérifie
    #     donc par numero_dpe, la clé stable, plutôt que par rayon géographique.) ---
    dpe_connu = fiche.get("dpe_connu")
    with conn.cursor() as cur:
        cur.execute("SELECT numero_dpe, etiquette_dpe, jeu FROM dpe_records WHERE parcelle_idu=%s", (idu,))
        servis = cur.fetchall()
    if not servis:
        vt.non_comparable(idu, "dpe_rattache", "ADEME DPE",
                          "LABUSE ne rattache aucun DPE à la parcelle "
                          "(absence non assertable : rattachement ADEME au grain adresse/BAN)",
                          labuse="0 DPE")
    for numero, etiq_lab, jeu in servis:
        ds = _ADEME_DPE_AV if (jeu or "").lower().startswith("avant") else _ADEME_DPE_DS
        import urllib.parse
        url = (f"https://data.ademe.fr/data-fair/api/v1/datasets/{ds}/lines?size=1&qs="
               + urllib.parse.quote(f'numero_dpe:"{numero}"'))
        try:
            o, _ = fetch_json(url, "dpe", timeout=50)
            res = (o or {}).get("results") or []
            if not res:
                vt.verdict(idu, "dpe_rattache", "ADEME DPE", f"DPE {numero} (étiq. {etiq_lab})",
                           "introuvable à l'ADEME", FAUX,
                           ecart="DPE servi absent du jeu ADEME", url=url)
            else:
                etiq_off = res[0].get("etiquette_dpe") or res[0].get("classe_consommation_energie")
                ok = (not etiq_lab) or (not etiq_off) or str(etiq_lab).upper() == str(etiq_off).upper()
                vt.verdict(idu, "dpe_rattache", "ADEME DPE", f"{numero} — étiq. {etiq_lab}",
                           f"{numero} — étiq. {etiq_off}", CONFORME if ok else FAUX,
                           ecart="" if ok else f"étiquette {etiq_lab} ≠ {etiq_off}", url=url,
                           note="DPE vérifié par numéro à l'ADEME")
        except Exception as e:  # noqa: BLE001
            vt.non_comparable(idu, "dpe_rattache", "ADEME DPE", f"injoignable : {str(e)[:50]}",
                              labuse=f"DPE {numero}", url=url)

    # --- Permis (Sitadel) : permis de la parcelle ---
    # Sitadel en open data est diffusé en lots (pas d'API point fiable) ; on compare la PRÉSENCE
    # servie à la couche Sitadel ingérée (contrôle de régression) et on le DIT (NON COMPARABLE à
    # la source vive quand l'API point n'existe pas).
    with conn.cursor() as cur:
        cur.execute("SELECT count(*) FROM sitadel_permits s WHERE jsonb_exists(s.idu_codes, %s)", (idu,))
        n_permis = cur.fetchone()[0]
    vt.non_comparable(idu, "permis_sitadel", "Sitadel (open data, lots)",
                      f"{n_permis} permis rattaché(s) à la parcelle dans Sitadel ingéré "
                      "(pas d'API Sitadel au point pour un contrôle vif)",
                      labuse=n_permis)
    time.sleep(0.2)


# ════════════════════════════════════════════════════════════════════════════════
#  ORCHESTRATION
# ════════════════════════════════════════════════════════════════════════════════

SOURCES = {
    "cadastre": source_cadastre,
    "ban": source_ban,
    "plu": source_plu,
    "risques": source_risques,
    "dvf": source_dvf,
    "bati": source_bati,
    "entreprises": source_entreprises,
    "energie_permis": source_energie_permis,
}

_CHAMPS_CSV = ["parcelle", "champ", "source", "valeur_labuse", "valeur_officielle",
               "date_source", "verdict", "ecart", "url", "note"]


def _fichier_source(s: str):
    return VTM.SORTIE / f"comparaisons_{s}.csv"


def _deja_faits_source(s: str) -> set:
    """parcelles déjà traitées pour CETTE source (fichier par source) — pour la REPRISE."""
    fait = set()
    fp = _fichier_source(s)
    if fp.exists():
        with open(fp, newline="") as f:
            for r in csv.DictReader(f):
                fait.add(r["parcelle"])
    return fait


def cmd_comparer(source: str, n: int = 0, rafraichir: bool = False) -> None:
    """Compare une ou plusieurs sources. CHAQUE source écrit son PROPRE fichier
    `comparaisons_<source>.csv` (écritures sûres même en parallèle, un commit par source) ;
    `fusionner` les concatène ensuite dans COMPARAISONS.csv. Reprise par (source, parcelle)."""
    import psycopg
    ech = _charger_echantillon()
    if n:
        ech = ech[:n]
    noms = list(SOURCES) if source in ("toutes", "all", "*") else source.split(",")
    for s in noms:
        if s not in SOURCES:
            raise SystemExit(f"source inconnue : {s} (connues : {', '.join(SOURCES)})")
    fiche = FicheServie()
    conn = psycopg.connect(VTM._dsn())
    conn.read_only = True
    conn.autocommit = True
    VTM.SORTIE.mkdir(parents=True, exist_ok=True)
    try:
        for s in noms:
            fn = SOURCES[s]
            fp = _fichier_source(s)
            nouveau = not fp.exists() or rafraichir
            deja = set() if rafraichir else _deja_faits_source(s)
            f = open(fp, "w" if rafraichir else "a", newline="")
            w = csv.DictWriter(f, fieldnames=_CHAMPS_CSV)
            if nouveau:
                w.writeheader()
            faits = 0
            try:
                for dd in ech:
                    if dd["idu"] in deja:
                        continue
                    vt = VT()
                    try:
                        fdata = fiche(dd["idu"])
                    except Exception as e:  # noqa: BLE001
                        vt.non_comparable(dd["idu"], s, "fiche servie", f"fiche injoignable : {str(e)[:50]}")
                        fdata = {}
                    else:
                        try:
                            fn(vt, dd, fdata, conn)
                        except Exception as e:  # noqa: BLE001
                            vt.non_comparable(dd["idu"], s, s, f"comparateur a levé : {str(e)[:70]}")
                    for lg in vt.lignes:
                        lg["source"] = f"{s} · {lg['source']}"
                        w.writerow(lg)
                    f.flush()
                    faits += 1
                    if faits % 25 == 0:
                        print(f"  [{s}] {faits} parcelles comparées…", flush=True)
            finally:
                f.close()
            print(f"[{s}] terminé : {faits} parcelles ce passage → {fp}", flush=True)
    finally:
        conn.close()


def cmd_fusionner() -> None:
    """Concatène tous les comparaisons_<source>.csv dans COMPARAISONS.csv (ordre des sources)."""
    lignes = []
    for s in SOURCES:
        fp = _fichier_source(s)
        if fp.exists():
            with open(fp, newline="") as f:
                lignes.extend(list(csv.DictReader(f)))
    with open(COMPARAISONS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_CHAMPS_CSV)
        w.writeheader()
        w.writerows(lignes)
    print(f"{len(lignes)} lignes → {COMPARAISONS_CSV}")
