"""COHERENCE-1 lot C — LA VÉRITÉ : relire chaque notion HORS de LABUSE, à la source.

Pour les notions à fort enjeu, la valeur servie est comparée au service ou au fichier
D'ORIGINE, relu indépendamment (aucun code LABUSE importé) :

  · zone PLU            — API Carto GPU (zone-urba au centroïde) ;
  · surface cadastrale  — API Carto cadastre (contenance PCI) ;
  · population commune  — geo.api.gouv.fr (population municipale légale) ;
  · arrêtés CatNat      — Géorisques GASPAR (api/v1/gaspar/catnat) ;
  · ventes DVF          — fichier Etalab brut (files.data.gouv.fr/geo-dvf), id de mutation ;
  · altitude            — service alti IGN (data.geopf.fr) vs profil altimétrique servi ;
  · SIRENE              — recherche-entreprises.api.gouv.fr (dénomination du SIREN) ;
  · taux SRU            — fichier DHUP brut (l'URL que la fiche cite elle-même) ;
  · taxe d'aménagement  — délibérations documentées (St-Denis 3 %, St-Paul 5 % — vérifiées
                          en recette RETOURS-15 D7 sur les délibérations) ;
  · règles PLU calibrées — 30 règles tirées au sort (md5), le PDF du règlement est ouvert à
                          la page citée et la valeur doit s'y lire (pdftotext).

Skips honnêtes (dits, jamais silencieux) : PPR/aléas (pas de GetFeatureInfo DEAL public
stable — la couche est comparée à sa table au lot B), CoSIA raster (téléchargement lourd),
Sitadel brut (fichier national lourd — le compte est croisé au lot E), Filosofi revenu
(publication INSEE sans API), PDF Kelfoncier CK0678 (fichier absent du poste).

    python -m scripts.coherence.verite          → VERITE.csv (~10 min, réseau requis)
"""
from __future__ import annotations

import csv
import hashlib
import json
import re
import subprocess
import time
import urllib.parse
import urllib.request

import psycopg

from .lib import API, DSN, SORTIE

ECH = SORTIE / "ECHANTILLON.csv"
UA = {"User-Agent": "LABUSE-coherence-1 (audit interne)"}


def _get(url, timeout=30):
    if url.startswith(API):
        req = urllib.request.Request(url, headers=UA)
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.read()
    # externe : curl (urllib de ce poste échoue en CERTIFICATE_VERIFY_FAILED — certifi absent)
    out = subprocess.run(["curl", "-sL", "-m", str(timeout), "-A", UA["User-Agent"], url],
                         capture_output=True, timeout=timeout + 10)
    if out.returncode != 0 or not out.stdout:
        raise RuntimeError(f"curl {out.returncode} sur {url[:80]}")
    return out.stdout


def _json(url, timeout=30):
    return json.loads(_get(url, timeout))


def _fiche(idu):
    return _json(f"{API}/parcels/{idu}", timeout=120)


class V:
    def __init__(self):
        self.lignes = []

    def note(self, notion, objet, labuse, oracle, source, tol_rel=0.0):
        try:
            fa, fb = float(labuse), float(oracle)
            ecart = abs(fa - fb)
            ok = ecart <= tol_rel * max(abs(fa), abs(fb), 1)
        except (TypeError, ValueError):
            ecart = "" if str(labuse) == str(oracle) else f"{labuse!r} ≠ {oracle!r}"
            ok = str(labuse) == str(oracle)
        self.lignes.append({"notion": notion, "objet": objet, "valeur_labuse": labuse,
                            "valeur_oracle": oracle, "source_oracle": source,
                            "ecart": ecart if not ok else "",
                            "verdict": "VRAI" if ok else "FAUX"})

    def skip(self, notion, raison):
        self.lignes.append({"notion": notion, "objet": "—", "valeur_labuse": "",
                            "valeur_oracle": "", "source_oracle": raison,
                            "ecart": "", "verdict": "NON VÉRIFIÉ (dit)"})


def charge_echantillon():
    with open(ECH, newline="") as f:
        return list(csv.DictReader(f))


def oracle_zone_et_surface(v, conn, parcelles, n=40):
    """API Carto : GPU zone-urba (typezone au centroïde) + cadastre (contenance)."""
    sel = parcelles[:n]
    for row in sel:
        idu = row["idu"]
        with conn.cursor() as cur:
            cur.execute("SELECT ST_X(ST_Transform(centroid,4326)), ST_Y(ST_Transform(centroid,4326)),"
                        " surface_m2 FROM parcels WHERE idu=%s", (idu,))
            lon, lat, surf = cur.fetchone()
            cur.execute("SELECT zone_fam, zone_lib FROM parcel_zone_plu WHERE idu=%s", (idu,))
            z = cur.fetchone()
        # zone PLU (GPU)
        try:
            geom = urllib.parse.quote(json.dumps({"type": "Point", "coordinates": [lon, lat]}))
            feats = _json(f"https://apicarto.ign.fr/api/gpu/zone-urba?geom={geom}").get("features", [])
            types = sorted({f["properties"].get("typezone") for f in feats})
            if z and types:
                fam = z[0]
                # GPU « AUc/AUs » ↔ famille AU ; « Ah/Nd… » portent la famille en tête
                ok_fam = any(t and (t == fam or t.startswith(fam)) for t in types)
                v.note("zone_plu_famille", idu, fam, "/".join(t or "∅" for t in types),
                       "API Carto GPU zone-urba (centroïde)", 0 if not ok_fam else 1)
            elif z and not types:
                v.note("zone_plu_famille", idu, z[0], "∅ (GPU sans zonage au point)",
                       "API Carto GPU zone-urba (centroïde)")
        except Exception as e:  # noqa: BLE001
            v.skip(f"zone_plu_famille[{idu}]", f"API Carto GPU injoignable : {str(e)[:60]}")
        # surface (contenance PCI)
        try:
            insee, section, numero = idu[:5], idu[8:10], idu[10:]
            fc = _json("https://apicarto.ign.fr/api/cadastre/parcelle?"
                       f"code_insee={insee}&section={section}&numero={numero}")
            feats = fc.get("features", [])
            if feats:
                cont = feats[0]["properties"].get("contenance")
                v.note("surface_parcelle_m2", idu, round(surf), cont,
                       "API Carto cadastre (contenance PCI)", 0.05)
        except Exception as e:  # noqa: BLE001
            v.skip(f"surface_parcelle_m2[{idu}]", f"API Carto cadastre : {str(e)[:60]}")
        time.sleep(0.3)


def oracle_communes(v, communes):
    """Population légale (geo.api.gouv) + arrêtés CatNat (Géorisques GASPAR)."""
    for com in communes:
        try:
            ctx = _json(f"{API}/communes/{urllib.parse.quote(com)}/contexte", timeout=120)
        except Exception as e:  # noqa: BLE001
            v.skip(f"contexte[{com}]", str(e)[:80])
            continue
        insee = ctx.get("insee")
        hab = (ctx.get("population") or {}).get("habitants")
        try:
            g = _json(f"https://geo.api.gouv.fr/communes/{insee}?fields=population")
            v.note("habitants_n", com, hab, g.get("population"),
                   "geo.api.gouv.fr (population municipale légale)", 0.03)
        except Exception as e:  # noqa: BLE001
            v.skip(f"habitants_n[{com}]", str(e)[:80])
        try:
            cat = _json("https://www.georisques.gouv.fr/api/v1/gaspar/catnat?"
                        f"code_insee={insee}&page=1&page_size=1")
            v.note("catnat_n", com, (ctx.get("risques") or {}).get("catnat_arretes"),
                   cat.get("results"), "Géorisques GASPAR catnat")
        except Exception as e:  # noqa: BLE001
            v.skip(f"catnat_n[{com}]", str(e)[:80])
        time.sleep(0.3)


def oracle_dvf(v, conn, insee="97411", annee="2024"):
    """Fichier Etalab brut : chaque mutation du fichier doit être en base (id + valeur)."""
    try:
        brut = _get(f"https://files.data.gouv.fr/geo-dvf/latest/csv/{annee}/communes/974/{insee}.csv",
                    timeout=60).decode()
    except Exception as e:  # noqa: BLE001
        v.skip("dvf_mutation", f"fichier Etalab injoignable : {str(e)[:60]}")
        return
    lignes = list(csv.DictReader(brut.splitlines()))
    muts = {}
    for l in lignes:
        muts.setdefault(l["id_mutation"], l)
    manquantes, valeurs_ko, verifiees = 0, 0, 0
    for mid, l in list(muts.items())[:200]:
        with conn.cursor() as cur:
            cur.execute("SELECT valeur_fonciere FROM dvf_mutations WHERE mutation_id=%s LIMIT 1",
                        (mid,))
            row = cur.fetchone()
        if not row:
            manquantes += 1
            continue
        verifiees += 1
        try:
            if abs(float(row[0]) - float(l["valeur_fonciere"] or 0)) > 1:
                valeurs_ko += 1
        except (TypeError, ValueError):
            valeurs_ko += 1
    v.note("dvf_mutation_presence", f"{insee}/{annee}",
           f"{verifiees}/{len(muts)} en base", f"{len(muts)} mutations Etalab",
           "files.data.gouv.fr geo-dvf (brut)", 1)
    v.note("dvf_valeur_fonciere", f"{insee}/{annee}",
           f"{valeurs_ko} valeurs ≠", "0 attendu", "files.data.gouv.fr geo-dvf (brut)")
    if manquantes:
        v.lignes[-2]["ecart"] = f"{manquantes} mutations du fichier absentes de la base"
        v.lignes[-2]["verdict"] = "FAUX" if manquantes > len(muts) * 0.05 else "VRAI (≤5 %)"


def oracle_alti(v, conn, temoins):
    """Altitude : le profil servi (RGE ALTI en base) encadré par le service IGN au
    centroïde — le centroïde est DANS la parcelle, son altitude IGN doit tomber dans
    [altitude_min ; altitude_max] du profil (à 5 m près, résolution du raster)."""
    for idu in temoins:
        try:
            prof = _json(f"{API}/parcels/{idu}/profil-altimetrique", timeout=120)
            amin, amax = prof.get("altitude_min_m"), prof.get("altitude_max_m")
            if amin is None or amax is None:
                v.skip(f"altitude[{idu}]", f"profil sans altitudes ({prof.get('motif')})")
                continue
            with conn.cursor() as cur:
                cur.execute("SELECT ST_X(ST_Transform(centroid,4326)), "
                            "ST_Y(ST_Transform(centroid,4326)) FROM parcels WHERE idu=%s", (idu,))
                lon, lat = cur.fetchone()
            o = _json("https://data.geopf.fr/altimetrie/1.0/calcul/alti/rest/elevation.json?"
                      f"lon={lon}&lat={lat}&resource=ign_rge_alti_wld")
            z_ign = o["elevations"][0]["z"]
            ok = (amin - 5) <= z_ign <= (amax + 5)
            v.lignes.append({"notion": "altitude_m", "objet": idu,
                             "valeur_labuse": f"[{amin};{amax}] (profil)",
                             "valeur_oracle": z_ign,
                             "source_oracle": "IGN service alti (RGE ALTI) au centroïde",
                             "ecart": "" if ok else "centroïde hors de la plage du profil ±5 m",
                             "verdict": "VRAI" if ok else "FAUX"})
        except Exception as e:  # noqa: BLE001
            v.skip(f"altitude[{idu}]", str(e)[:80])
        time.sleep(0.3)


def oracle_sirene(v, conn, n=8):
    """Dénomination du propriétaire PM servie = celle du SIREN à l'API recherche-entreprises."""
    with conn.cursor() as cur:
        cur.execute("""SELECT DISTINCT ON (siren) siren, denomination, idu
                       FROM pm_proprietaires_millesimes
                       WHERE millesime=(SELECT max(millesime) FROM pm_proprietaires_millesimes)
                         AND siren ~ '^[0-9]{9}$'
                       ORDER BY siren, idu LIMIT %s""", (n,))
        rows = cur.fetchall()
    for siren, denom, idu in rows:
        try:
            o = _json(f"https://recherche-entreprises.api.gouv.fr/search?q={siren}&page=1&per_page=1")
            res = (o.get("results") or [{}])[0]
            nom = (res.get("nom_raison_sociale") or res.get("nom_complet") or "").upper()
            ok = bool(nom) and (denom or "").upper()[:20] in nom or nom[:20] in (denom or "").upper()
            v.lignes.append({"notion": "proprietaire_moral_denomination", "objet": f"{idu} ({siren})",
                             "valeur_labuse": denom, "valeur_oracle": nom or "∅",
                             "source_oracle": "recherche-entreprises.api.gouv.fr",
                             "ecart": "" if ok else "dénominations divergentes",
                             "verdict": "VRAI" if ok else "FAUX"})
        except Exception as e:  # noqa: BLE001
            v.skip(f"proprietaire_moral[{siren}]", str(e)[:80])
        time.sleep(0.5)


def oracle_sru(v):
    """Le taux LLS servi = le fichier DHUP que la fiche cite elle-même (source_url)."""
    try:
        with psycopg.connect(DSN) as conn, conn.cursor() as cur:
            cur.execute("SELECT insee, commune, taux_lls, source_url FROM commune_contexte_sru "
                        "ORDER BY insee")
            rows = cur.fetchall()
        url = rows[0][3]
        brut = _get(url, timeout=60).decode("utf-8", errors="replace")
        # fichier DHUP : csv ; on cherche la colonne du taux par insee
        lignes = list(csv.DictReader(brut.splitlines(), delimiter=";"))
        if len(lignes) < 5:
            lignes = list(csv.DictReader(brut.splitlines(), delimiter=","))
        col_insee = next((c for c in lignes[0] if "insee" in c.lower() or c.lower() == "code"), None)
        col_taux = next((c for c in lignes[0] if "taux" in c.lower() and "lls" in c.lower()), None)
        if not (col_insee and col_taux):
            v.skip("taux_lls_pct", f"colonnes DHUP non reconnues : {list(lignes[0])[:8]}")
            return
        par_insee = {l[col_insee].strip(): l[col_taux] for l in lignes}
        for insee, com, taux, _ in rows:
            o = par_insee.get(insee)
            if o is None:
                continue
            v.note("taux_lls_pct", com, taux, float(str(o).replace(",", ".").rstrip("% ")),
                   "DHUP inventaire SRU (source citée par la fiche)", 0.01)
    except Exception as e:  # noqa: BLE001
        v.skip("taux_lls_pct", f"fichier DHUP : {str(e)[:80]}")


#: taux vérifiés sur les délibérations en recette RETOURS-15 (D7, 27-28/09/2026).
TAXE_DELIB = {"Saint-Denis": 3.0, "Saint-Paul": 5.0}


def oracle_taxe(v):
    for com, taux_delib in TAXE_DELIB.items():
        try:
            ctx = _json(f"{API}/communes/{urllib.parse.quote(com)}/contexte", timeout=120)
            servi = (ctx.get("taxe_amenagement") or {}).get("part_communale_pct")
            v.note("taxe_amenagement_taux_communal_pct", com, servi, taux_delib,
                   "délibération communale (vérifiée RETOURS-15 D7)")
        except Exception as e:  # noqa: BLE001
            v.skip(f"taxe_amenagement[{com}]", str(e)[:80])


def oracle_regles_plu(v, conn, n=30):
    """30 règles calibrées tirées au sort (md5) : le PDF du règlement, ouvert à la page
    citée, contient le verbatim déclaré (première phrase ≥ 12 caractères)."""
    with conn.cursor() as cur:
        cur.execute("""SELECT commune, zone, article_ref, page_pdf, texte_verbatim, source_url
                       FROM plu_reglement_extrait
                       WHERE source_url IS NOT NULL AND page_pdf IS NOT NULL
                         AND length(coalesce(texte_verbatim,'')) > 20
                       ORDER BY md5('coherence1'||commune||zone||article_ref) LIMIT %s""", (n,))
        regles = cur.fetchall()
    cache: dict[str, str] = {}
    for com, zone, art, page, verbatim, url in regles:
        pdf_url = url.split("#")[0]
        cle = f"{pdf_url}#p{page}"
        try:
            if cle not in cache:
                pdf = _get(pdf_url, timeout=90)
                tmp = f"/tmp/coherence_plu_{hashlib.md5(pdf_url.encode()).hexdigest()[:10]}.pdf"
                with open(tmp, "wb") as f:
                    f.write(pdf)
                out = subprocess.run(["pdftotext", "-f", str(max(1, int(page) - 1)),
                                      "-l", str(int(page) + 1), tmp, "-"],
                                     capture_output=True, text=True, timeout=60)
                cache[cle] = out.stdout
            texte = cache[cle]
            morceau = re.sub(r"\s+", " ", verbatim).strip()[:60]
            present = re.sub(r"\s+", " ", texte).find(morceau[:40]) >= 0
            v.lignes.append({"notion": "regle_plu_calibree", "objet": f"{com} {zone} {art} p.{page}",
                             "valeur_labuse": morceau, "valeur_oracle": "présent" if present else "ABSENT de la page",
                             "source_oracle": pdf_url[:90],
                             "ecart": "" if present else "verbatim introuvable à la page citée (±1)",
                             "verdict": "VRAI" if present else "FAUX"})
        except Exception as e:  # noqa: BLE001
            v.skip(f"regle_plu[{com} {zone} {art}]", str(e)[:80])
        time.sleep(0.2)


def main() -> None:
    v = V()
    parcelles = charge_echantillon()
    communes = sorted({r["commune"] for r in parcelles if r["commune"] not in ("", "?")})
    with psycopg.connect(DSN, options="-c statement_timeout=120000") as conn:
        conn.autocommit = True
        print("oracle zone PLU + surface (API Carto, 40 parcelles)…")
        oracle_zone_et_surface(v, conn, parcelles, n=40)
        print("oracle communes (population, CatNat)…")
        oracle_communes(v, communes)
        print("oracle DVF (fichier Etalab brut)…")
        oracle_dvf(v, conn)
        print("oracle altitude (7 témoins)…")
        oracle_alti(v, conn, [r["idu"] for r in parcelles if r["strate"] == "temoin"])
        print("oracle SIRENE (8 PM)…")
        oracle_sirene(v, conn)
        print("oracle SRU (fichier DHUP)…")
        oracle_sru(v)
        print("oracle taxe d'aménagement (délibérations)…")
        oracle_taxe(v)
        print("oracle règles PLU (30 tirées au sort)…")
        oracle_regles_plu(v, conn)
    # skips de périmètre, dits une fois
    v.skip("ppr_alea", "pas d'oracle public requêtable stable (GetFeatureInfo DEAL) — couche comparée à sa table au lot B")
    v.skip("cosia_couverture", "raster brut CoSIA = téléchargement lourd, hors budget du banc v1")
    v.skip("permis_sitadel", "fichier national Sit@del lourd — compte croisé en interne (lot E)")
    v.skip("filosofi_revenu", "publication INSEE sans API — à verser en oracle manuel")
    v.skip("kelfoncier_ck0678", "PDF Saint-Paul_000_CK_0678 introuvable sur le poste (cherché ~/Desktop)")
    with open(SORTIE / "VERITE.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["notion", "objet", "valeur_labuse", "valeur_oracle",
                                          "source_oracle", "ecart", "verdict"])
        w.writeheader()
        w.writerows(v.lignes)
    faux = sum(1 for l in v.lignes if l["verdict"] == "FAUX")
    vrais = sum(1 for l in v.lignes if l["verdict"].startswith("VRAI"))
    print(f"\n{len(v.lignes)} lignes · {vrais} VRAI · {faux} FAUX → {SORTIE/'VERITE.csv'}")


if __name__ == "__main__":
    main()
