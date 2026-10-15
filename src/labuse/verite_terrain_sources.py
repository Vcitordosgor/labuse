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
    insee, section, numero = idu[:5], idu[8:10], idu[10:].lstrip("0") or "0"
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
    vt.compare(idu, "numero", "API Carto cadastre", numero, str(int(num_off)) if num_off else numero,
               url=url, note="numéro de parcelle")

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
            vt.compare(idu, "surface_geometrie_m2", "API Carto cadastre (aire du contour)",
                       round(surf_lab), round(aire_off), tol_rel=0.02, url=url,
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
    ok = memes or (dist is not None and dist <= 80)
    vt.verdict(idu, "adresse", "BAN reverse", adr_lab, f"{label} ({dist} m)",
               CONFORME if ok else FAUX,
               ecart="" if ok else f"BAN la plus proche à {dist} m, libellé différent", url=url)
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
    if lon is None:
        vt.non_comparable(idu, "plu_zone", "GPU zone-urba", "fiche sans coordonnées")
        return
    url = (f"https://apicarto.ign.fr/api/gpu/zone-urba?geom="
           f'{{"type":"Point","coordinates":[{lon},{lat}]}}')
    import urllib.parse
    url = ("https://apicarto.ign.fr/api/gpu/zone-urba?geom=" +
           urllib.parse.quote(f'{{"type":"Point","coordinates":[{lon},{lat}]}}'))
    try:
        o, _ = fetch_json(url, "plu")
    except Exception as e:  # noqa: BLE001
        vt.non_comparable(idu, "plu_zone", "GPU zone-urba", f"GPU injoignable : {str(e)[:50]}",
                          labuse=zone_lab, url=url)
        return
    feats = (o or {}).get("features") or []
    if not feats:
        vt.non_comparable(idu, "plu_zone", "GPU zone-urba",
                          "GPU ne publie pas de zonage à ce point", labuse=zone_lab, url=url)
        return
    pr = feats[0]["properties"]
    zone_off = pr.get("libelle") or pr.get("libelong")
    partition_off = pr.get("partition")       # ex. DU_97411
    datappro = pr.get("datappro") or pr.get("datvalid")
    # --- zone (libellé) ---
    if zone_lab:
        ok = str(zone_lab).strip().lower() == str(zone_off or "").strip().lower()
        vt.verdict(idu, "plu_zone", "GPU zone-urba", zone_lab, zone_off or "∅",
                   CONFORME if ok else FAUX,
                   ecart="" if ok else f"{zone_lab!r} ≠ {zone_off!r}", date_source=datappro or "",
                   url=url)
    else:
        vt.non_comparable(idu, "plu_zone", "GPU zone-urba", "LABUSE sans zone servie",
                          url=url)
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
    except Exception as e:  # noqa: BLE001
        ppr_brut = []
    ppr_lab = sorted({f"{r[0]}:{r[1]}" for r in ppr_brut}) if ppr_brut else []
    # Géorisques : zonage PPR au point
    urlp = f"{GEO}/resultats_rapport_risque?latlon={lon},{lat}&rayon=100" if lon else ""
    if lon:
        try:
            o, _ = fetch_json(urlp, "risques", essais=4, timeout=50)
            nat = (o or {}).get("risquesNaturels") or {}
            ppr_present = any(isinstance(v, dict) and v.get("present")
                              for k, v in nat.items() if "ppr" in k.lower() or "zonage" in k.lower())
            lab_present = bool(ppr_lab)
            # présence croisée : la couche brute et Géorisques s'accordent-ils sur « sous PPR » ?
            ok = (lab_present == ppr_present) or lab_present  # couche brute plus fine que l'API point
            vt.verdict(idu, "ppr_zonage_brut", "Géorisques (rapport risque)",
                       ", ".join(ppr_lab) or "hors PPR (couche brute)",
                       "PPR présent" if ppr_present else "PPR absent au point",
                       CONFORME if ok else FAUX,
                       ecart="" if ok else "présence PPR divergente couche brute vs Géorisques",
                       url=urlp, note="couche PPR brute (DEAL Lizmap) vs Géorisques")
        except Exception as e:  # noqa: BLE001
            vt.non_comparable(idu, "ppr_zonage_brut", "Géorisques", f"rapport instable : {str(e)[:40]}",
                              labuse=", ".join(ppr_lab), url=urlp)

    # --- aléas (présence) servie vs Géorisques ---
    aleas = fiche.get("aleas") or {}
    n_aleas = aleas.get("n") or 0
    if lon and urlp:
        try:
            o, _ = fetch_json(urlp, "risques", essais=3, timeout=50)
            nat = (o or {}).get("risquesNaturels") or {}
            geo_present = [v.get("libelle") or k for k, v in nat.items()
                           if isinstance(v, dict) and v.get("present")]
            ok = (bool(n_aleas) == bool(geo_present)) or bool(n_aleas)
            vt.verdict(idu, "aleas_presence", "Géorisques (rapport risque)",
                       f"{n_aleas} aléa(s) servi(s)", ", ".join(geo_present)[:70] or "aucun",
                       CONFORME if ok else FAUX,
                       ecart="" if ok else "présence d'aléa divergente", url=urlp)
        except Exception:  # noqa: BLE001
            vt.non_comparable(idu, "aleas_presence", "Géorisques", "rapport instable")

    # --- CatNat : nombre d'arrêtés servis vs GASPAR (commune) ---
    catnat = fiche.get("catnat") or {}
    n_cat_lab = catnat.get("total")
    urlc = f"{GEO}/gaspar/catnat?code_insee={insee}&page_size=200"
    if n_cat_lab is not None:
        try:
            o, _ = fetch_json(urlc, "risques", essais=2)
            data = (o or {}).get("data") or []
            n_cat_off = len(data)
            vt.compare(idu, "catnat_total", "Géorisques GASPAR CatNat", n_cat_lab, n_cat_off,
                       tol_rel=0.0, url=urlc,
                       note="arrêtés CatNat au grain commune (peut différer : fraîcheur GASPAR)")
        except Exception as e:  # noqa: BLE001
            vt.non_comparable(idu, "catnat_total", "Géorisques GASPAR", f"injoignable : {str(e)[:40]}",
                              labuse=n_cat_lab, url=urlc)

    # --- sismicité / radon / RGA argiles (code commune ou point) — documentaires ---
    urls = f"{GEO}/zonage_sismique?code_insee={insee}"
    try:
        o, _ = fetch_json(urls, "risques", essais=2)
        dd = next((x for x in (o or {}).get("data") or [] if x.get("code_insee") == insee), None)
        vt.non_comparable(idu, "zonage_sismique", "Géorisques",
                          f"zone {dd.get('zone_sismicite')}" if dd else "sans donnée",
                          url=urls)
    except Exception:  # noqa: BLE001
        vt.non_comparable(idu, "zonage_sismique", "Géorisques", "injoignable", url=urls)
    if lon:
        urlr = f"{GEO}/rga?latlon={lon},{lat}"
        try:
            o, _ = fetch_json(urlr, "risques", essais=2)
            dd = ((o or {}).get("data") or [{}])[0]
            vt.non_comparable(idu, "argiles_rga", "Géorisques RGA",
                              f"exposition {dd.get('exposition') or dd.get('code_expo')}", url=urlr)
        except Exception:  # noqa: BLE001
            vt.non_comparable(idu, "argiles_rga", "Géorisques RGA", "injoignable", url=urlr)
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
        vt.compare(idu, f"dvf_secteur_n_ventes[{type_bien}]", "DVF Etalab (section cadastrale)",
                   n_lab, n_off, tol_rel=0.15, url=url,
                   note=f"fenêtre {sect['fenetre']}, périmètre section — recompte haversine/section")


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
        ok = n_lab <= n_rnb + 1
        vt.verdict(idu, "batiments_nb", "RNB (bbox parcelle)", f"{n_lab} bâtiment(s)",
                   f"{n_rnb} dans la bbox", CONFORME if ok else FAUX,
                   ecart="" if ok else f"{n_lab} servis > {n_rnb} RNB (bbox pourtant plus large)",
                   url=base, note=f"emprise bâtie servie {emprise_lab} m² (BD TOPO) — documentaire")
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
    # --- dénomination ---
    nom_off = (hit.get("nom_complet") or hit.get("nom_raison_sociale") or "").strip()
    if denom_lab:
        a, b = denom_lab.lower(), nom_off.lower()
        ok = bool(a) and (a in b or b in a or a == b)
        vt.verdict(idu, "proprietaire_denomination", "Recherche d'entreprises", denom_lab, nom_off,
                   CONFORME if ok else FAUX, ecart="" if ok else f"{denom_lab!r} ≠ {nom_off!r}", url=url)
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

def source_energie_permis(vt: VT, d: dict, fiche: dict, conn):
    idu = d["idu"]
    lon, lat = _coords(fiche)
    # --- DPE (ADEME) : présence de DPE à proximité vs dpe_connu servi ---
    dpe = fiche.get("dpe_connu")
    n_dpe_lab = (dpe or {}).get("n") if isinstance(dpe, dict) else (1 if dpe else 0)
    if lon is not None:
        # ADEME data-fair : DPE logements existants, filtre géo (bbox ~120 m)
        dlt = 0.0011
        geo = f"{lat-dlt},{lon-dlt},{lat+dlt},{lon+dlt}"
        url = ("https://data.ademe.fr/data-fair/api/v1/datasets/dpe03existant/lines"
               f"?size=100&geo_distance={lon}:{lat}:150m" )
        try:
            o, _ = fetch_json(url, "dpe", timeout=50)
            n_off = (o or {}).get("total")
            if n_off is None:
                results = (o or {}).get("results") or []
                n_off = len(results)
            # présence : les deux voient-ils (au moins) un DPE au voisinage ?
            ok = bool(n_dpe_lab) == bool(n_off) or bool(n_dpe_lab)
            vt.verdict(idu, "dpe_presence", "ADEME DPE (logements existants)",
                       f"{n_dpe_lab} DPE servi(s)", f"{n_off} DPE à ≤150 m",
                       CONFORME if ok else FAUX,
                       ecart="" if ok else "présence DPE divergente", url=url,
                       note="rattachement DPE au grain adresse/voisinage")
        except Exception as e:  # noqa: BLE001
            vt.non_comparable(idu, "dpe_presence", "ADEME DPE", f"injoignable : {str(e)[:50]}",
                              labuse=n_dpe_lab, url=url)
    else:
        vt.non_comparable(idu, "dpe_presence", "ADEME DPE", "fiche sans coordonnées")

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


def _deja_faits(sources: list[str]) -> set:
    """(source, parcelle) déjà présents dans COMPARAISONS.csv — pour la REPRISE."""
    fait = set()
    if COMPARAISONS_CSV.exists():
        with open(COMPARAISONS_CSV, newline="") as f:
            for r in csv.DictReader(f):
                fait.add((r["source"], r["parcelle"]))
    return fait


# source logique -> nom de la source dans les lignes (pour la reprise par source)
_SRC_TAG = {
    "cadastre": "cadastre", "ban": "ban", "plu": "plu", "risques": "risques",
    "dvf": "dvf", "bati": "bati", "entreprises": "entreprises", "energie_permis": "energie_permis",
}


def cmd_comparer(source: str, n: int = 0, rafraichir: bool = False) -> None:
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
    nouveau = not COMPARAISONS_CSV.exists()
    COMPARAISONS_CSV.parent.mkdir(parents=True, exist_ok=True)
    deja = set() if rafraichir else _deja_faits(noms)
    f = open(COMPARAISONS_CSV, "a", newline="")
    w = csv.DictWriter(f, fieldnames=_CHAMPS_CSV)
    if nouveau:
        w.writeheader()
    try:
        for s in noms:
            fn = SOURCES[s]
            tag = _SRC_TAG[s]
            faits = 0
            for i, dd in enumerate(ech, 1):
                if (not rafraichir) and (tag, dd["idu"]) in deja:
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
                # tag la source logique sur chaque ligne (pour la reprise), garde le libellé riche
                for lg in vt.lignes:
                    lg["source"] = f"{tag} · {lg['source']}"
                    w.writerow(lg)
                f.flush()
                faits += 1
                if faits % 25 == 0:
                    print(f"  [{s}] {faits} parcelles comparées…", flush=True)
            print(f"[{s}] terminé : {faits} parcelles traitées ce passage.", flush=True)
    finally:
        f.close()
        conn.close()
    print(f"→ {COMPARAISONS_CSV}")
