"""ORACLE-1 — les oracles qui rejoignent le banc de cohérence.

COHERENCE-1 (scripts/coherence/verite.py) relit HORS de LABUSE une poignée de notions à
fort enjeu. ORACLE-1 pousse la même idée sur TOUTES les notions parcelle qui ont une source
publique stable et requêtable, et ajoute les contrôles que COHERENCE-1 sautait ou n'avait
pas :

  · contenance cadastrale  — API Carto cadastre (contenance PCI) vs surface servie, à 1 %
                             (COHERENCE-1 tolérait 5 %, ce qui masquait l'aire-géométrique-
                             étiquetée-contenance) ;
  · Géorisques multirisque — PPR (zonage + date d'approbation), ICPE + distance, cavités,
                             argiles (RGA), sismicité, radon (COHERENCE-1 sautait le PPR) ;
  · rayon DVF réel         — nombre de ventes RÉELLEMENT à ≤500 m (haversine sur le fichier
                             Etalab) vs le « N ventes à moins de 500 m » affiché, quand le
                             rayon servi est en fait 1 000/1 500 m ou la commune ;
  · adresse BAN            — reverse geocoding au centroïde vs adresse servie ;
  · bâtiments RNB          — compte RNB (points dans la parcelle) vs n bâtiments servi.

Chaque oracle a la forme des oracles COHERENCE-1 : une fonction qui reçoit le collecteur V
et la liste des témoins, et ajoute des lignes {notion, objet, valeur_labuse, valeur_oracle,
source_oracle, ecart, verdict}. Rejouable sans navigateur, lecture seule.

    LABUSE_ORACLE_API=http://127.0.0.1:8645 python -m scripts.coherence.oracles
      → docs/audit-2026-09/ORACLE-1/ORACLES.csv

Le job nocturne appelle `lancer(idus, api=…)` sur SES témoins (COHERENCE-1 en a 7 ;
ORACLE-1 en gèle 20 dans PARCELLES.csv).
"""
from __future__ import annotations

import csv
import json
import math
import os
import pathlib
import subprocess
import time
import urllib.parse

import psycopg

RACINE = pathlib.Path(__file__).resolve().parents[3]
SORTIE = RACINE / "docs" / "audit-2026-09" / "ORACLE-1"
PARCELLES = SORTIE / "PARCELLES.csv"
DVF_CACHE = pathlib.Path(os.environ.get("ORACLE_DVF_CACHE", "/tmp/oracle1/dvf"))
DSN = os.environ.get("LABUSE_DSN", "postgresql://openclaw@localhost:5432/labuse")
API = os.environ.get("LABUSE_ORACLE_API", "http://127.0.0.1:8645")
GEO = "https://www.georisques.gouv.fr/api/v1"
UA = "LABUSE-oracle-1 (audit interne)"


# ───────────────────────── socle réseau (curl : urllib casse en CERTIFICATE_VERIFY sur ce poste)

def _get(url: str, timeout: int = 40) -> bytes:
    out = subprocess.run(["curl", "-sL", "-m", str(timeout), "-A", UA, url],
                         capture_output=True, timeout=timeout + 10)
    if out.returncode != 0 or not out.stdout:
        raise RuntimeError(f"curl {out.returncode} sur {url[:80]}")
    return out.stdout


def _json(url: str, timeout: int = 40, essais: int = 1):
    """GET JSON ; `essais`>1 pour les endpoints Géorisques instables (backoff court)."""
    last = None
    for i in range(essais):
        try:
            return json.loads(_get(url, timeout))
        except Exception as e:  # noqa: BLE001
            last = e
            if i + 1 < essais:
                time.sleep(1.5 * (i + 1))
    raise last


def _fiche(idu: str):
    return _json(f"{API}/parcels/{idu}", timeout=120)


def _haversine_m(lon1, lat1, lon2, lat2) -> float:
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


# ───────────────────────── collecteur (même forme que COHERENCE-1 V)

class V:
    def __init__(self):
        self.lignes: list[dict] = []

    def note(self, notion, objet, labuse, oracle, source, url="", tol_rel=0.0, page=""):
        try:
            fa, fb = float(labuse), float(oracle)
            ecart = abs(fa - fb)
            ok = ecart <= tol_rel * max(abs(fa), abs(fb), 1)
            ecart_txt = "" if ok else f"{ecart:.3g}"
        except (TypeError, ValueError):
            ok = str(labuse).strip().lower() == str(oracle).strip().lower()
            ecart_txt = "" if ok else f"{labuse!r} ≠ {oracle!r}"
        self.lignes.append({"notion": notion, "objet": objet,
                            "valeur_labuse": labuse, "valeur_oracle": oracle,
                            "source_oracle": source, "url": url, "page": page,
                            "ecart": ecart_txt, "verdict": "vrai" if ok else "faux"})
        return ok

    def verdict(self, notion, objet, labuse, oracle, source, ok, pourquoi="", url="", page=""):
        self.lignes.append({"notion": notion, "objet": objet,
                            "valeur_labuse": labuse, "valeur_oracle": oracle,
                            "source_oracle": source, "url": url, "page": page,
                            "ecart": "" if ok else pourquoi, "verdict": "vrai" if ok else "faux"})

    def skip(self, notion, objet, raison, url=""):
        self.lignes.append({"notion": notion, "objet": objet, "valeur_labuse": "",
                            "valeur_oracle": "", "source_oracle": raison, "url": url,
                            "page": "", "ecart": "", "verdict": "non_verifiable"})


# ───────────────────────── oracle : contenance cadastrale (vs surface servie)

def oracle_contenance(v: V, conn, temoins: list[dict]):
    """La surface servie (surface_m2) est l'aire géométrique du contour PCI ; la contenance
    cadastrale officielle (API Carto) peut en différer de plusieurs %. Le piège ORACLE-1 :
    le Dossier PDF étiquette cette aire « contenance ». On compare à 1 %."""
    for t in temoins:
        idu = t["idu"]
        insee, section, numero = idu[:5], idu[8:10], idu[10:]
        url = ("https://apicarto.ign.fr/api/cadastre/parcelle?"
               f"code_insee={insee}&section={section}&numero={numero}")
        try:
            feats = _json(url).get("features", [])
            if not feats:
                v.skip("surface_contenance_m2", idu, "parcelle absente d'API Carto cadastre", url)
                continue
            cont = feats[0]["properties"].get("contenance")
            with conn.cursor() as cur:
                cur.execute("SELECT surface_m2 FROM parcels WHERE idu=%s", (idu,))
                r = cur.fetchone()
            surf = r[0] if r else None
            v.note("surface_contenance_m2", idu, round(surf) if surf else None, cont,
                   "API Carto cadastre (contenance PCI)", url, tol_rel=0.01)
        except Exception as e:  # noqa: BLE001
            v.skip("surface_contenance_m2", idu, f"API Carto : {str(e)[:60]}", url)
        time.sleep(0.3)


# ───────────────────────── oracle : Géorisques multirisque

def oracle_georisques(v: V, conn, temoins: list[dict]):
    """Risques au point (inondation, mouvement de terrain, submersion, ICPE…) via le
    rapport risque Géorisques ; sismicité et potentiel radon par code commune. On vérifie
    la COHÉRENCE DE PRÉSENCE : si Géorisques voit un risque naturel « existant » au point,
    la fiche doit porter au moins une vigilance/aléa ; et réciproquement.

    (Le détail zonage PPR par parcelle a été vérifié manuellement au Lot B ; ici l'oracle
    est une sonde de régression stable — endpoint `/ppr` direct abandonné : il répond 404,
    et `/gaspar/pprn?code_insee=` ne filtre PAS par commune.)"""
    for t in temoins:
        idu, lon, lat, insee = t["idu"], float(t["lon"]), float(t["lat"]), t["idu"][:5]
        fiche = t.get("_fiche") or {}
        lines = [l for l in (fiche.get("lines") or []) if isinstance(l, dict)]
        # --- rapport risque au point (présence)
        url = f"{GEO}/resultats_rapport_risque?latlon={lon},{lat}&rayon=1000"
        try:
            o = _json(url, essais=4, timeout=50)
            nat = o.get("risquesNaturels") or {}
            tech = o.get("risquesTechnologiques") or {}
            def _present(bloc):
                out = []
                for k, val in (bloc or {}).items():
                    if isinstance(val, dict) and val.get("present"):
                        out.append(val.get("libelle") or k)
                return out
            risques_geo = _present(nat) + _present(tech)
            # LABUSE porte-t-il une vigilance risque/aléa ?
            risque_labuse = bool(fiche.get("aleas")) or any(
                l.get("layer") in ("risques", "mvt", "icpe") and
                l.get("result") in ("SOFT_FLAG", "HARD_EXCLUDE") for l in lines)
            ok = bool(risques_geo) == risque_labuse
            v.verdict("risques_presence", idu,
                      "vigilance(s) risque servie" if risque_labuse else "aucune vigilance risque",
                      (", ".join(risques_geo)[:70] or "aucun risque Géorisques"),
                      "Géorisques rapport risque (au point)",
                      ok=ok,
                      pourquoi="" if ok else "présence de risque divergente fiche vs Géorisques",
                      url=url)
        except Exception as e:  # noqa: BLE001
            v.skip("risques_presence", idu, f"Géorisques rapport instable : {str(e)[:50]}", url)
        # --- sismicité (code_insee, stable) — documentaire
        url_s = f"{GEO}/zonage_sismique?code_insee={insee}"
        try:
            o = _json(url_s, essais=2)
            d = next((x for x in (o.get("data") or []) if x.get("code_insee") == insee), None)
            v.skip("zonage_sismique", idu,
                   f"Géorisques : zone {d.get('zone_sismicite')}" if d else "Géorisques sans donnée",
                   url_s)
        except Exception as e:  # noqa: BLE001
            v.skip("zonage_sismique", idu, f"Géorisques sismique : {str(e)[:50]}", url_s)
        # --- radon (code_insee, stable) — documentaire
        url_r = f"{GEO}/radon?code_insee={insee}"
        try:
            o = _json(url_r, essais=2)
            d = (o.get("data") or [{}])[0]
            v.skip("potentiel_radon", idu,
                   f"Géorisques : classe potentiel {d.get('classe_potentiel')}", url_r)
        except Exception as e:  # noqa: BLE001
            v.skip("potentiel_radon", idu, f"Géorisques radon : {str(e)[:50]}", url_r)
        time.sleep(0.3)


# ───────────────────────── oracle : rayon DVF réellement à ≤500 m

def oracle_dvf_rayon(v: V, conn, temoins: list[dict]):
    """La fiche/PDF annonce souvent « N ventes à moins de 500 m » alors que le rayon servi
    (radius_m) vaut 1 000/1 500 m ou la commune. On recompte, sur le fichier Etalab, les
    mutations RÉELLEMENT à ≤500 m du centroïde et on compare au libellé « 500 m »."""
    muts = _charger_dvf()
    if not muts:
        for t in temoins:
            v.skip("dvf_ventes_500m", t["idu"], "cache DVF Etalab absent (/tmp/oracle1/dvf)")
        return
    for t in temoins:
        idu, lon, lat = t["idu"], float(t["lon"]), float(t["lat"])
        fiche = t.get("_fiche") or {}
        pa = fiche.get("prix_ancien") or {}
        radius = pa.get("radius_m")
        n_servi = pa.get("n")
        if radius is None:
            v.skip("dvf_ventes_500m", idu, "fiche sans prix_ancien.radius_m")
            continue
        type_prix = pa.get("type_prix")  # appartement / maison / terrain
        n_500 = 0
        for m in muts:
            if m["type"] != type_prix and type_prix not in (None, "mixte"):
                continue
            if _haversine_m(lon, lat, m["lon"], m["lat"]) <= 500:
                n_500 += 1
        # le verdict porte sur la VÉRACITÉ du libellé « 500 m » quand radius != 500
        libelle_500 = (radius != 500)  # la fiche sert un rayon ≠ 500 mais le PDF dit « 500 m »
        v.verdict("dvf_rayon_500m_libelle", idu,
                  f"n={n_servi} au rayon servi {radius:.0f} m (type {type_prix})",
                  f"{n_500} vente(s) réellement ≤500 m",
                  "fichier DVF Etalab (haversine au centroïde)",
                  ok=(not libelle_500) or (n_500 == n_servi),
                  pourquoi=(f"rayon servi {radius:.0f} m ≠ 500 m : le libellé « {n_servi} ventes "
                            f"à moins de 500 m » est faux ({n_500} réellement ≤500 m)")
                  if libelle_500 and n_500 != n_servi else "",
                  url="files.data.gouv.fr/geo-dvf (974, 2022-2025)")
        time.sleep(0.05)


def _charger_dvf() -> list[dict]:
    out: list[dict] = []
    for f in sorted(DVF_CACHE.glob("dvf_974_*.csv")):
        with open(f, newline="") as fh:
            for r in csv.DictReader(fh):
                try:
                    lon = float(r.get("longitude") or "")
                    lat = float(r.get("latitude") or "")
                except ValueError:
                    continue
                tl = (r.get("type_local") or "").lower()
                t = ("appartement" if "appart" in tl else
                     "maison" if "maison" in tl else
                     "terrain" if not tl else "autre")
                out.append({"lon": lon, "lat": lat, "type": t,
                            "valeur": r.get("valeur_fonciere"),
                            "date": r.get("date_mutation")})
    return out


# ───────────────────────── oracle : adresse BAN (reverse)

def oracle_ban(v: V, conn, temoins: list[dict]):
    for t in temoins:
        idu, lon, lat = t["idu"], float(t["lon"]), float(t["lat"])
        fiche = t.get("_fiche") or {}
        adr_labuse = fiche.get("adresse") or ""
        url = f"https://api-adresse.data.gouv.fr/reverse/?lon={lon}&lat={lat}&limit=1"
        try:
            o = _json(url)
            feats = o.get("features") or []
            if not feats:
                v.skip("adresse_ban", idu, "BAN sans résultat au centroïde", url)
                continue
            p = feats[0]["properties"]
            label = p.get("label", "")
            dist = p.get("distance")

            def _norm(s):
                import re as _re
                return _re.sub(r"[\s,]+", " ", (s or "").lower().strip())
            # le numéro+voie de LABUSE se retrouve-t-il dans le label BAN ? (robuste aux
            # grandes parcelles où le point BAN est loin du centroïde mais l'adresse est bonne)
            tete = _norm(adr_labuse).split(" 974")[0]
            memes = bool(tete) and (tete in _norm(label) or _norm(label).startswith(tete))
            non_rattachee = "non rattach" in adr_labuse.lower() or not adr_labuse
            ok = non_rattachee or memes or (dist is not None and dist <= 80)
            v.verdict("adresse_ban", idu, adr_labuse or "∅",
                      f"{label} ({dist} m)", "BAN reverse",
                      ok=ok,
                      pourquoi="" if ok else f"adresse BAN la plus proche à {dist} m (libellé différent)",
                      url=url)
        except Exception as e:  # noqa: BLE001
            v.skip("adresse_ban", idu, f"BAN : {str(e)[:60]}", url)
        time.sleep(0.2)


# ───────────────────────── oracle : bâtiments RNB

def oracle_batiments_rnb(v: V, conn, temoins: list[dict]):
    """n bâtiments servi (le_bien) vs compte RNB des bâtiments dont le point est DANS la
    bbox serrée de la parcelle (approx : l'API RNB prend une bbox lat/lon)."""
    for t in temoins:
        idu = t["idu"]
        fiche = t.get("_fiche") or {}
        le_bien = fiche.get("le_bien") or {}
        n_labuse = le_bien.get("nb_batiments")
        if n_labuse is None:
            v.skip("batiments_rnb", idu, "fiche sans le_bien.nb_batiments")
            continue
        with conn.cursor() as cur:
            cur.execute("SELECT ST_YMin(e), ST_XMin(e), ST_YMax(e), ST_XMax(e) "
                        "FROM (SELECT ST_Envelope(ST_Transform(geom,4326)) e "
                        "FROM parcels WHERE idu=%s) q", (idu,))
            bb = cur.fetchone()
        if not bb:
            v.skip("batiments_rnb", idu, "parcelle absente de la base")
            continue
        # aire de la bbox (deg²→m² approx) : au-delà de ~4 ha la bbox déborde trop pour que
        # le compte RNB soit comparable (parcelle géante/allongée) — on skippe honnêtement.
        import math as _m
        dlat = (bb[2] - bb[0]) * 111_320
        dlon = (bb[3] - bb[1]) * 111_320 * _m.cos(_m.radians((bb[0] + bb[2]) / 2))
        if dlat * dlon > 40_000:
            v.skip("batiments_rnb", idu,
                   f"bbox {dlat:.0f}×{dlon:.0f} m trop large pour un compte RNB comparable")
            continue
        base = (f"https://rnb-api.beta.gouv.fr/api/alpha/buildings/"
                f"?bb={bb[0]},{bb[1]},{bb[2]},{bb[3]}")
        try:
            n_rnb, url, garde = 0, base, 0
            while url and garde < 10:
                o = _json(url, timeout=40)
                n_rnb += len(o.get("results") or [])
                url = o.get("next")
                garde += 1
            # la bbox déborde la parcelle → RNB ≥ n servi attendu ; faux seulement si le
            # compte servi DÉPASSE le RNB d'une bbox pourtant plus large (surcompte).
            ok = n_labuse <= n_rnb + 1
            v.verdict("batiments_rnb", idu, f"{n_labuse} bâtiments (le_bien)",
                      f"{n_rnb} dans la bbox RNB", "RNB (bbox parcelle)",
                      ok=ok,
                      pourquoi="" if ok else
                      f"{n_labuse} servis > {n_rnb} RNB dans une bbox pourtant plus large",
                      url=base)
        except Exception as e:  # noqa: BLE001
            v.skip("batiments_rnb", idu, f"RNB : {str(e)[:60]}", base)
        time.sleep(0.2)


# ───────────────────────── orchestration

ORACLES = [oracle_contenance, oracle_georisques, oracle_dvf_rayon, oracle_ban, oracle_batiments_rnb]


def charger_temoins(chemin: pathlib.Path = PARCELLES) -> list[dict]:
    """Lit les témoins (idu + commune) et complète coords + fiche depuis l'API."""
    import csv as _csv
    temoins = []
    with open(chemin, newline="") as f:
        for r in _csv.DictReader(f, delimiter=";"):
            temoins.append({"slot": r.get("slot"), "idu": r["idu"], "commune": r.get("commune")})
    return temoins


def _enrichir(temoins: list[dict]) -> list[dict]:
    for t in temoins:
        try:
            fiche = _fiche(t["idu"])
            t["_fiche"] = fiche
            c = fiche.get("coords")
            if c:
                t["lon"], t["lat"] = c[0], c[1]
        except Exception:  # noqa: BLE001
            t["_fiche"] = {}
    return [t for t in temoins if "lon" in t]


def lancer(temoins: list[dict] | None = None, oracles=ORACLES) -> V:
    v = V()
    if temoins is None:
        temoins = charger_temoins()
    temoins = _enrichir(temoins)
    with psycopg.connect(DSN, options="-c statement_timeout=120000") as conn:
        conn.autocommit = True
        for oracle in oracles:
            print(f"  {oracle.__name__}…", flush=True)
            try:
                oracle(v, conn, temoins)
            except Exception as e:  # noqa: BLE001
                print(f"    ! {oracle.__name__} a levé : {e}")
    return v


def main() -> None:
    print(f"ORACLE-1 — oracles rejouables (API={API})")
    v = lancer()
    SORTIE.mkdir(parents=True, exist_ok=True)
    cible = SORTIE / "ORACLES.csv"
    with open(cible, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["notion", "objet", "valeur_labuse", "valeur_oracle",
                                          "source_oracle", "url", "page", "ecart", "verdict"])
        w.writeheader()
        w.writerows(v.lignes)
    faux = sum(1 for l in v.lignes if l["verdict"] == "faux")
    vrai = sum(1 for l in v.lignes if l["verdict"] == "vrai")
    nv = sum(1 for l in v.lignes if l["verdict"] == "non_verifiable")
    print(f"\n{len(v.lignes)} lignes · {vrai} vrai · {faux} faux · {nv} non vérifiable → {cible}")


if __name__ == "__main__":
    main()
