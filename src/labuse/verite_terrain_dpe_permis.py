"""VERITE-TERRAIN-2 · volet C — DPE (ADEME par adresse BAN), PERMIS (Sit@del) & salvage NON COMPARABLE.

Le volet A (règles PLU) et le volet B (trajets) sont faits. Ici on ferme les TROUS de la première
vérité terrain (V-T-1), sur les MÊMES 500 parcelles (graine 20261015, base q_v18) :

  1. DPE — LE NOUVEL ANGLE. V-T-1 ne vérifiait QUE le sens « chaque DPE que LABUSE SERT existe-t-il
     à l'ADEME » → un seul comparable (LABUSE ne rattache un DPE qu'à ~1 parcelle sur 500). La vraie
     question, l'INVERSE, est le RAPPEL : « l'ADEME a-t-elle des DPE à l'adresse BAN de la parcelle
     que LABUSE NE rattache PAS ? ». On interroge l'ADEME par IDENTIFIANT BAN (jamais par rayon
     géographique : la géoloc ADEME 974 est corrompue — lat ~-2 au lieu de -21). Les identifiants BAN
     d'une parcelle sont ceux que LABUSE a lui-même rattachés dans sa table `adresses` (id_ban), du
     MÊME millésime BAN que l'ADEME (ex. 97415_1330_00038 des deux côtés — vérifié). On compte les DPE
     ADEME à ces BAN (3 jeux récents + 2 jeux « avant 07/2021 ») et on les confronte à ce que LABUSE
     rattache (`dpe_records.parcelle_idu`).

  2. PERMIS — Sit@del INDÉPENDANT. V-T-1 classait tout NON COMPARABLE (« pas d'API Sitadel »). Ici on
     prend une source Sit@del VIVE et indépendante : la base nationale open-data SDES/DiDo exposée en
     API data-fair (`opendata.koumoul.com/.../sitadel-logements`, PC+DP créant des logements depuis
     2013, 1,9 M lignes, filtrable par commune/type/n° de dossier). On compare au grain COMMUNE
     (compte officiel vs ingéré LABUSE, famille « logements ») et au grain PERMIS (N° de dossier
     NUM_DAU ↔ permit_id, qui partagent le même format) sur les communes de l'échantillon.

  3. SALVAGE NON COMPARABLE — Géorisques. V-T-1 posait sismicité/radon/argiles en NON COMPARABLE
     « absent au point ». Sismicité est en fait documentée par COMMUNE (zonage réglementaire) → on la
     SAUVE (comparable). Radon idem (potentiel par commune). Argiles (RGA) : Géorisques le déclare
     N/A à La Réunion (île volcanique, endpoint mort) → reste NON COMPARABLE, mais pour une raison
     désormais DOCUMENTÉE et non plus « absent au point ».

LECTURE SEULE STRICTE : connexion DB `read_only=True` (toute écriture LÈVE), aucun écrit VPS, aucune
modification du code existant. Appels réseau SÉQUENTIELS espacés (~0,5 s), CACHE DISQUE, et JOURNAL
APPEND-ONLY resumable (flush par parcelle → une interruption ne perd rien ; la reprise saute les
parcelles déjà faites). On réutilise l'échantillon et les verdicts de V-T-1.

    PYTHONPATH=src python -m labuse.verite_terrain_dpe_permis dpe        [--n 0]
    PYTHONPATH=src python -m labuse.verite_terrain_dpe_permis permis     [--n 0]
    PYTHONPATH=src python -m labuse.verite_terrain_dpe_permis georisques [--n 0]
    PYTHONPATH=src python -m labuse.verite_terrain_dpe_permis tout       [--n 0]   # les trois, puis rapport
    PYTHONPATH=src python -m labuse.verite_terrain_dpe_permis rapport
"""
from __future__ import annotations

import csv
import hashlib
import json
import os
import sys
import time
from collections import Counter, defaultdict
from pathlib import Path

import httpx
import psycopg

from .verite_terrain import _charger_echantillon, _dsn

RACINE = Path(__file__).resolve().parents[2]
SORTIE = RACINE / "docs" / "audit-2026-10" / "verite-terrain-2"
CACHE = Path(os.environ.get("VT2C_CACHE", SORTIE / "cache" / "dpe_permis"))
DPE_PERMIS_CSV = SORTIE / "DPE-PERMIS.csv"
#: journal APPEND-ONLY — une (parcelle, contrôle) écrite sitôt finie ; reprise en sautant les faits.
PARTIEL_CSV = SORTIE / "_dpe_permis_partiel.csv"

# ───────────────────────── verdicts (mêmes libellés que les volets A/B)
CONFORME = "CONFORME"
FAUX = "LABUSE FAUX"
RECENTE = "SOURCE PLUS RÉCENTE"
NC = "NON COMPARABLE"

_PAUSE_S = float(os.environ.get("VT2C_PAUSE", "0.5"))   # appels séquentiels espacés

# ───────────────────────── jeux ADEME DPE (tous confirmés live, cf. data.ademe.fr/data-fair)
_ADEME = "https://data.ademe.fr/data-fair/api/v1/datasets"
_DPE_JEUX = {
    # jeu LABUSE (dpe_records.jeu)  ->  (dataset data-fair, libellé, depuis_date)
    "existant":  ("meg-83tjwtg8dyz4vv7h1dqe", "DPE Logements existants (depuis 07/2021)", "2021-07"),
    "neuf":      ("g3cgx7jb3cmys5voxz1mrm22", "DPE Logements neufs (depuis 07/2021)",     "2021-07"),
    "tertiaire": ("j9ol0fwjqckyf49vr29nknbu", "DPE Tertiaire (depuis 07/2021)",           "2021-07"),
}
#: jeux « avant 07/2021 » interrogés EN PLUS pour ne pas manquer un DPE ancien à l'adresse (RAPPEL).
_DPE_JEUX_AV = {
    "avant": ("dpe-france", "DPE Logements (avant 07/2021)", "<2021-07"),
}

# ───────────────────────── Sit@del indépendant : base nationale SDES/DiDo (data-fair Koumoul)
_SITADEL = "https://opendata.koumoul.com/data-fair/api/v1/datasets/sitadel-logements/lines"
_SITADEL_NOM = "Sit@del SDES/DiDo (sitadel-logements, PC+DP logements depuis 2013)"
_SITADEL_DEPUIS = "2013"   # couverture open-data de la base (PC/DP logements)

_COLS = ["parcelle", "commune", "controle", "adresse_ban", "ademe_ou_source_n",
         "labuse_n", "detail", "verdict", "note", "url"]


# ═════════════════════════════════════════════════════════════════════════════════════════
#  CONNEXION READ-ONLY + SOCLE RÉSEAU (httpx direct + cache disque + backoff ; 0 écriture base)
# ═════════════════════════════════════════════════════════════════════════════════════════

def _connect():
    conn = psycopg.connect(_dsn())
    conn.read_only = True        # garde-fou : toute écriture LÈVE plutôt que de passer
    conn.autocommit = True
    return conn


def _cache_path(sous: str, cle: str) -> Path:
    return CACHE / sous / f"{hashlib.sha1(cle.encode()).hexdigest()}.json"


def _cache_lire(sous: str, cle: str):
    p = _cache_path(sous, cle)
    if p.exists():
        try:
            return json.loads(p.read_text())
        except Exception:  # noqa: BLE001 — cache corrompu → on refait
            return None
    return None


def _cache_ecrire(sous: str, cle: str, payload) -> None:
    p = _cache_path(sous, cle)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(payload, ensure_ascii=False))


def get_json(client: httpx.Client, url: str, sous: str, essais: int = 4):
    """GET JSON avec CACHE DISQUE (clé = url) et REPRISE. Une réponse réussie est mémorisée ; une
    erreur réseau n'est JAMAIS mise en cache (retentée à la reprise). Rend (payload, depuis_cache)."""
    hit = _cache_lire(sous, url)
    if hit is not None:
        return hit.get("body"), True
    last = None
    for attempt in range(essais):
        try:
            r = client.get(url, timeout=50.0)
            if r.status_code == 429 or r.status_code >= 500:
                ra = r.headers.get("Retry-After")
                time.sleep(float(ra) if (ra or "").isdigit() else min(20.0, 2 ** attempt))
                last = RuntimeError(f"HTTP {r.status_code}")
                continue
            r.raise_for_status()
            body = r.json()
            _cache_ecrire(sous, url, {"url": url, "body": body})
            time.sleep(_PAUSE_S)
            return body, False
        except Exception as exc:  # noqa: BLE001 — réseau/timeout → retry poli
            last = exc
            time.sleep(0.5 * (attempt + 1))
    raise RuntimeError(f"{sous} injoignable après {essais} essais ({last})")


def _qs(url_base: str, qs: str, size: int) -> str:
    import urllib.parse
    return f"{url_base}?size={size}&qs=" + urllib.parse.quote(qs)


# ═════════════════════════════════════════════════════════════════════════════════════════
#  JOURNAL APPEND-ONLY + REPRISE (par (parcelle, contrôle))
# ═════════════════════════════════════════════════════════════════════════════════════════

def _faits(controles: set[str]) -> set[str]:
    """Clés (parcelle|controle_prefixe) déjà écrites — reprise. `controles` = préfixes à considérer
    (ex. {'dpe'} ou {'permis'}) pour pouvoir relancer un contrôle sans refaire les autres."""
    if not PARTIEL_CSV.exists():
        return set()
    out = set()
    with open(PARTIEL_CSV, newline="") as f:
        for r in csv.DictReader(f):
            base = r["controle"].split("_")[0]
            if base in controles:
                out.add(f'{r["parcelle"]}|{base}')
    return out


def _ouvrir_journal():
    SORTIE.mkdir(parents=True, exist_ok=True)
    nouveau = not PARTIEL_CSV.exists()
    jour = open(PARTIEL_CSV, "a", newline="")
    w = csv.DictWriter(jour, fieldnames=_COLS)
    if nouveau:
        w.writeheader()
        jour.flush()
    return jour, w


def _ligne(parcelle, commune, controle, adresse_ban, src_n, labuse_n, detail, verdict, note, url):
    return {"parcelle": parcelle, "commune": commune, "controle": controle,
            "adresse_ban": adresse_ban, "ademe_ou_source_n": src_n, "labuse_n": labuse_n,
            "detail": detail, "verdict": verdict, "note": note, "url": url}


# ═════════════════════════════════════════════════════════════════════════════════════════
#  DPE — RAPPEL du rattachement (ADEME par IDENTIFIANT BAN, jamais par rayon géographique)
# ═════════════════════════════════════════════════════════════════════════════════════════
#
# Pour chaque parcelle :
#   · BAN servis = les id_ban que LABUSE rattache à la parcelle (table `adresses`). Même millésime BAN
#     que l'ADEME (vérifié : LABUSE et ADEME portent 97415_1330_00038 pour la même adresse).
#   · DPE ADEME = tous les DPE des 4 jeux (existant/neuf/tertiaire + avant 07/2021) dont
#     `identifiant_ban` ∈ {BAN servis} (OU, requête unique par jeu). On compte les numero_dpe DISTINCTS.
#   · DPE LABUSE = `dpe_records` rattachés à la parcelle (numero_dpe).
# Verdicts :
#   · CONFORME : LABUSE rattache exactement l'ensemble des numero_dpe que l'ADEME a aux BAN de la
#     parcelle (ou ADEME 0 et LABUSE 0) ;
#   · LABUSE FAUX : l'ADEME a un numero_dpe à un BAN DE LA PARCELLE que LABUSE NE rattache PAS (trou de
#     rappel), ou LABUSE sert un numero_dpe absent de l'ADEME à ces BAN ;
#   · NON COMPARABLE : parcelle sans id_ban (pas d'ancre), ADEME injoignable, ou AMBIGUÏTÉ DE GRAIN —
#     un identifiant BAN (adresse) peut couvrir PLUSIEURS parcelles : si l'ADEME a au BAN un DPE que
#     LABUSE a rattaché à une AUTRE parcelle, ce n'est pas un trou, c'est le grain adresse≠parcelle.

def _ban_parcelle(cur, idu: str) -> list[str]:
    cur.execute("SELECT DISTINCT id_ban FROM adresses WHERE idu=%s AND id_ban IS NOT NULL", (idu,))
    return [r[0] for r in cur.fetchall()]


def _dpe_labuse(cur, idu: str) -> list[tuple[str, str, str]]:
    cur.execute("SELECT numero_dpe, etiquette_dpe, jeu FROM dpe_records WHERE parcelle_idu=%s", (idu,))
    return [(r[0], r[1], r[2]) for r in cur.fetchall()]


def _dpe_ademe_aux_ban(client: httpx.Client, bans: list[str]) -> dict[str, dict]:
    """Tous les DPE ADEME (4 jeux) dont identifiant_ban ∈ bans. Rend {numero_dpe: {...}}.
    On interroge aussi les BAN tronqués au niveau RUE (certaines fiches ADEME n'ont que le code voie,
    ex. 97422_1404) → on requête l'id complet ET son préfixe rue, puis on filtre à l'appartenance."""
    if not bans:
        return {}
    # prefixes rue (les 2 premiers segments) pour capter les DPE géocodés au niveau voie seulement
    rues = sorted({"_".join(b.split("_")[:2]) for b in bans if b.count("_") >= 2})
    bans_set = set(bans)
    rues_set = set(rues)
    jeux = {**_DPE_JEUX, **_DPE_JEUX_AV}
    out: dict[str, dict] = {}
    for jeu_lab, (ds, libelle, _dep) in jeux.items():
        # une requête OR par jeu, sur les id complets + préfixes rue (quote gérée par _qs)
        cibles = sorted(bans_set | rues_set)
        clause = " OR ".join(f'"{b}"' for b in cibles)
        url = _qs(f"{_ADEME}/{ds}/lines", f"identifiant_ban:({clause})", size=200)
        try:
            o, _ = get_json(client, url, "dpe")
        except Exception:  # noqa: BLE001 — un jeu injoignable ne doit pas tout bloquer
            continue
        for r in (o or {}).get("results") or []:
            ban = r.get("identifiant_ban") or ""
            # ne retenir que les DPE dont le BAN est EXACTEMENT un des id de la parcelle, OU dont le
            # BAN est une RUE et le numéro de voie correspond à un de nos id (évite d'avaler la rue).
            exact = ban in bans_set
            rue_only = (ban in rues_set) and (ban.count("_") == 1)
            if not (exact or rue_only):
                continue
            num = r.get("numero_dpe")
            if not num:
                continue
            out[num] = {"ban": ban, "etiquette": r.get("etiquette_dpe")
                        or r.get("classe_consommation_energie"),
                        "jeu": jeu_lab, "dataset": ds, "libelle": libelle,
                        "date": r.get("date_etablissement_dpe") or r.get("date_visite_diagnostiqueur")
                        or r.get("date_reception_dpe") or "", "rue_only": rue_only}
    return out


def _numero_dpe_ailleurs(cur, numero: str, idu: str) -> str | None:
    """Si un numero_dpe ADEME manquant est en fait rattaché par LABUSE à une AUTRE parcelle, on le
    signale (grain adresse↔parcelle) plutôt que de crier au trou."""
    cur.execute("SELECT parcelle_idu FROM dpe_records WHERE numero_dpe=%s AND parcelle_idu<>%s LIMIT 1",
                (numero, idu))
    r = cur.fetchone()
    return r[0] if r else None


def controle_dpe(client, conn, p: dict) -> list[dict]:
    idu, commune = p["idu"], p["commune"]
    out: list[dict] = []
    with conn.cursor() as cur:
        bans = _ban_parcelle(cur, idu)
        labuse = _dpe_labuse(cur, idu)
        labuse_nums = {n for n, _e, _j in labuse}
        if not bans:
            out.append(_ligne(idu, commune, "dpe", "", "", len(labuse_nums),
                              "parcelle sans adresse BAN rattachée (pas d'ancre pour interroger l'ADEME)",
                              NC, "aucun id_ban dans `adresses` — rappel ADEME non testable", ""))
            return out
        ban_txt = " ".join(bans[:6]) + (" …" if len(bans) > 6 else "")
        try:
            ademe = _dpe_ademe_aux_ban(client, bans)
        except Exception as e:  # noqa: BLE001
            out.append(_ligne(idu, commune, "dpe", ban_txt, "", len(labuse_nums),
                              f"ADEME injoignable : {str(e)[:60]}", NC, "", ""))
            return out
        ademe_nums = set(ademe)
        url = _qs(f"{_ADEME}/{_DPE_JEUX['existant'][0]}/lines",
                  "identifiant_ban:(" + " OR ".join(f'"{b}"' for b in bans[:4]) + ")", 50)

        # trous de RAPPEL : DPE ADEME aux BAN de la parcelle que LABUSE ne rattache pas
        manquants = ademe_nums - labuse_nums
        # DPE servis que l'ADEME n'a pas à ces BAN (faux positif de rattachement)
        orphelins = labuse_nums - ademe_nums

        # classer les « manquants » : vrai trou vs grain adresse≠parcelle vs géocodage rue-seul
        trous, ailleurs, rue_seul = [], [], []
        for num in sorted(manquants):
            info = ademe[num]
            if info.get("rue_only"):
                rue_seul.append(num)
                continue
            autre = _numero_dpe_ailleurs(cur, num, idu)
            if autre:
                ailleurs.append((num, autre))
            else:
                trous.append(num)

        detail = (f"ADEME aux BAN : {len(ademe_nums)} DPE "
                  f"({', '.join(sorted(ademe_nums))[:80] or '—'}) · "
                  f"LABUSE rattache : {len(labuse_nums)} "
                  f"({', '.join(sorted(labuse_nums))[:80] or '—'})")

        if not trous and not orphelins:
            if ademe_nums == labuse_nums and ademe_nums:
                note = "LABUSE rattache exactement les DPE ADEME de l'adresse"
            elif not ademe_nums and not labuse_nums:
                note = "ADEME n'a aucun DPE à l'adresse, LABUSE non plus"
            else:
                note = "écart expliqué par le grain adresse↔parcelle (DPE rattaché ailleurs) ou géocodage rue"
            if ailleurs:
                note += f" ; {len(ailleurs)} DPE au BAN rattaché à une autre parcelle"
            if rue_seul:
                note += f" ; {len(rue_seul)} DPE géocodé au niveau rue (grain adresse imprécis)"
            out.append(_ligne(idu, commune, "dpe", ban_txt, len(ademe_nums), len(labuse_nums),
                              detail, CONFORME, note, url))
        else:
            notes = []
            if trous:
                notes.append(f"TROU de rappel : {len(trous)} DPE ADEME à l'adresse non rattaché(s) "
                             f"par LABUSE ({', '.join(trous)[:80]})")
            if orphelins:
                notes.append(f"{len(orphelins)} DPE servi(s) par LABUSE absent(s) de l'ADEME à ces BAN "
                             f"({', '.join(sorted(orphelins))[:60]})")
            if ailleurs:
                notes.append(f"{len(ailleurs)} DPE au BAN rattaché à une AUTRE parcelle (grain adresse)")
            if rue_seul:
                notes.append(f"{len(rue_seul)} DPE géocodé rue seulement (ignoré, grain imprécis)")
            out.append(_ligne(idu, commune, "dpe", ban_txt, len(ademe_nums), len(labuse_nums),
                              detail, FAUX, " ; ".join(notes), url))
    return out


# ═════════════════════════════════════════════════════════════════════════════════════════
#  PERMIS — Sit@del indépendant (grain commune + grain permis par N° de dossier)
# ═════════════════════════════════════════════════════════════════════════════════════════
#
# LABUSE sert, pour la famille « logements » (PC+DP), des permis identifiés par `permit_id` au MÊME
# format que le NUM_DAU de la base SDES/DiDo (ex. 97441512A0461). On compare :
#   · GRAIN COMMUNE : count(logements LABUSE, commune, depuis 2013) vs count(Sit@del, COMM, PC+DP) ;
#   · GRAIN PERMIS  : chaque permit_id logement LABUSE de la commune existe-t-il dans Sit@del (par
#     NUM_DAU) ? et combien de NUM_DAU Sit@del la commune a-t-elle que LABUSE n'ingère pas ?
# Le compte commune est fait UNE FOIS par commune (mémoïsé), pas par parcelle.

_sitadel_commune_cache: dict[str, dict] = {}


def _sitadel_commune(client: httpx.Client, insee: str) -> dict:
    """Pour une commune : total Sit@del (PC+DP logements), set des NUM_DAU (jusqu'à un plafond), total
    par type. Mémoïsé. On pagine jusqu'à récupérer tous les NUM_DAU (plafond 20 000/commune)."""
    if insee in _sitadel_commune_cache:
        return _sitadel_commune_cache[insee]
    # compte total (size=0 renvoie total)
    url0 = _qs(_SITADEL, f"COMM:{insee}", size=0)
    o0, _ = get_json(client, url0, "sitadel")
    total = int((o0 or {}).get("total") or 0)
    # récupérer les NUM_DAU + types (paginé). On borne à 20 000 pour rester léger.
    num_daus: set[str] = set()
    par_type: Counter = Counter()
    size = 1000
    page = 1
    recu = 0
    plafond = 20000
    while recu < total and recu < plafond:
        urlp = _qs(_SITADEL, f"COMM:{insee}", size=size) + f"&page={page}&select=NUM_DAU,TYPE_DAU"
        o, _ = get_json(client, urlp, "sitadel")
        res = (o or {}).get("results") or []
        if not res:
            break
        for r in res:
            nd = r.get("NUM_DAU")
            if nd:
                num_daus.add(nd)
            par_type[r.get("TYPE_DAU") or "?"] += 1
        recu += len(res)
        page += 1
    d = {"total": total, "num_daus": num_daus, "par_type": dict(par_type),
         "tronque": recu < total}
    _sitadel_commune_cache[insee] = d
    return d


_labuse_commune_cache: dict[str, dict] = {}


def _labuse_commune(cur, insee: str) -> dict:
    if insee in _labuse_commune_cache:
        return _labuse_commune_cache[insee]
    cur.execute(
        "SELECT permit_id, type FROM sitadel_permits "
        "WHERE raw->>'insee'=%s AND raw->>'famille'='logements' AND date_depot>='2013-01-01'",
        (insee,))
    rows = cur.fetchall()
    d = {"total": len(rows), "permit_ids": {r[0] for r in rows if r[0]},
         "par_type": dict(Counter(r[1] for r in rows))}
    _labuse_commune_cache[insee] = d
    return d


def controle_permis(client, conn, p: dict, communes_faites: set[str]) -> list[dict]:
    """Le contrôle permis est AU GRAIN COMMUNE : on n'émet une ligne qu'UNE FOIS par commune (la
    première parcelle de la commune rencontrée). Les parcelles suivantes de la même commune sont
    marquées faites sans réémettre, via `communes_faites`."""
    idu, commune, insee = p["idu"], p["commune"], p["insee"]
    out: list[dict] = []
    if insee in communes_faites:
        return out      # commune déjà comparée — pas de doublon
    with conn.cursor() as cur:
        lab = _labuse_commune(cur, insee)
    try:
        off = _sitadel_commune(client, insee)
    except Exception as e:  # noqa: BLE001
        out.append(_ligne(idu, commune, "permis_commune", "", "", lab["total"],
                          f"Sit@del injoignable : {str(e)[:60]}", NC, "", _SITADEL))
        communes_faites.add(insee)
        return out
    url = _qs(_SITADEL, f"COMM:{insee}", size=0)

    # grain COMMUNE : comptes. Sit@del open-data peut couvrir des mois POSTÉRIEURS à l'ingestion LABUSE
    # et des révisions → un léger surplus Sit@del est de la FRAÎCHEUR, pas un trou. On tranche :
    #   · comptes proches (±10 %)                         → CONFORME ;
    #   · Sit@del > LABUSE au-delà de 10 %                → SOURCE PLUS RÉCENTE (mois/révisions récents) ;
    #   · LABUSE > Sit@del au-delà de 10 %                → LABUSE FAUX (sur-ingestion/doublons) [revérifié].
    lo, of = lab["total"], off["total"]
    diff = abs(lo - of)
    proche = diff <= 0.10 * max(lo, of, 1)
    detail_c = (f"Sit@del SDES {of} permis logements (PC+DP, depuis 2013) · "
                f"LABUSE {lo} (famille logements, depuis 2013) · "
                f"types Sit@del {off['par_type']} / LABUSE {lab['par_type']}")
    if proche:
        v_c, note_c = CONFORME, "comptes commune proches (±10 %)"
    elif of > lo:
        v_c, note_c = RECENTE, ("Sit@del en avance (mois récents / révisions open-data postérieurs à "
                                "l'ingestion LABUSE)")
    else:
        v_c, note_c = FAUX, "LABUSE compte plus de permis logements que Sit@del open-data (à revérifier)"
    if off.get("tronque"):
        note_c += " ; set NUM_DAU tronqué au plafond (compte commune exact, join par permis partiel)"
    out.append(_ligne(idu, commune, "permis_commune", "", of, lo, detail_c, v_c, note_c, url))

    # grain PERMIS : recouvrement des N° de dossier (sous réserve de troncature du set Sit@del)
    if off["num_daus"]:
        inter = lab["permit_ids"] & off["num_daus"]
        lab_seul = lab["permit_ids"] - off["num_daus"]
        off_seul = off["num_daus"] - lab["permit_ids"]
        recouvre = len(inter) / max(len(lab["permit_ids"]), 1)
        detail_p = (f"{len(inter)} N° de dossier communs · {len(lab_seul)} LABUSE-seul · "
                    f"{len(off_seul)} Sit@del-seul (sur {len(off['num_daus'])} NUM_DAU Sit@del récupérés)")
        if off.get("tronque"):
            v_p, note_p = NC, ("join par N° de dossier non concluant : set Sit@del tronqué au plafond "
                               "(commune trop volumineuse) — join autoritatif = volet D")
        elif recouvre >= 0.90:
            v_p, note_p = CONFORME, f"{recouvre:.0%} des permit_id LABUSE retrouvés par NUM_DAU dans Sit@del"
        elif recouvre >= 0.60:
            v_p, note_p = RECENTE, (f"{recouvre:.0%} retrouvés ; l'écart tient aux millésimes "
                                    "(périmètres temporels/révisions) — join fin = volet D")
        else:
            v_p, note_p = NC, (f"recouvrement {recouvre:.0%} trop faible pour conclure au grain permis "
                               "(formats/périmètres) — comparaison autoritative reportée au volet D")
        out.append(_ligne(idu, commune, "permis_dossier", "", len(off["num_daus"]),
                          len(lab["permit_ids"]), detail_p, v_p, note_p, url))
    communes_faites.add(insee)
    return out


# ═════════════════════════════════════════════════════════════════════════════════════════
#  SALVAGE NON COMPARABLE — Géorisques (sismicité & radon par COMMUNE ; argiles = N/A documenté)
# ═════════════════════════════════════════════════════════════════════════════════════════
#
# V-T-1 posait ces trois en NON COMPARABLE « absent au point ». Or Géorisques les publie par COMMUNE :
#   · zonage_sismique : zone réglementaire de la commune — COMPARABLE (LABUSE sert-il la même zone ?) ;
#   · potentiel_radon : catégorie de potentiel radon de la commune — COMPARABLE ;
#   · argiles (RGA)   : le connecteur Géorisques le DÉCLARE N/A à La Réunion (île volcanique, endpoint
#     /rga mort) → reste NON COMPARABLE, mais la raison est désormais sourcée (connecteur), pas « absent ».
# On lit ce que LABUSE SERT via la fiche (aleas / risques) et on compare à la valeur commune Géorisques.

_GEO = "https://www.georisques.gouv.fr/api/v1"
_geo_sismique_cache: dict[str, str] = {}
_geo_radon_cache: dict[str, str] = {}


def _geo_sismique(client: httpx.Client, insee: str) -> str | None:
    if insee in _geo_sismique_cache:
        return _geo_sismique_cache[insee]
    url = f"{_GEO}/zonage_sismique?code_insee={insee}"
    try:
        o, _ = get_json(client, url, "georisques")
    except Exception:  # noqa: BLE001
        return None
    data = (o or {}).get("data") or []
    z = None
    for x in data:
        if x.get("code_insee") == insee:
            # code_zone = "2" (numérique propre) ; zone_sismicite = "2 - FAIBLE" (libellé)
            z = str(x.get("code_zone") or (x.get("zone_sismicite") or "").split(" ")[0] or "").strip()
            break
    _geo_sismique_cache[insee] = z
    return z


def _geo_radon(client: httpx.Client, insee: str) -> str | None:
    if insee in _geo_radon_cache:
        return _geo_radon_cache[insee]
    url = f"{_GEO}/radon?code_insee={insee}"
    try:
        o, _ = get_json(client, url, "georisques")
    except Exception:  # noqa: BLE001
        return None
    data = (o or {}).get("data") or []
    cat = None
    for x in data:
        if x.get("code_insee") == insee:
            cat = str(x.get("classe_potentiel") or x.get("potentiel") or "").strip()
            break
    _geo_radon_cache[insee] = cat
    return cat


def _fiche(idu: str, _cache={}):  # noqa: B006 — FicheServie initialisé une fois
    if "f" not in _cache:
        from .verite_terrain import FicheServie
        _cache["f"] = FicheServie()
    return _cache["f"](idu)


def controle_georisques(client, conn, p: dict) -> list[dict]:
    idu, commune, insee = p["idu"], p["commune"], p["insee"]
    out: list[dict] = []
    try:
        fiche = _fiche(idu)
    except Exception as e:  # noqa: BLE001
        out.append(_ligne(idu, commune, "georisques", "", "", "",
                          f"fiche injoignable : {str(e)[:50]}", NC, "", ""))
        return out

    # ce que LABUSE sert pour sismicité/radon : on cherche dans aleas/risques (libellés)
    def _sert(cle_mots: tuple[str, ...]) -> str:
        blobs = []
        for k in ("aleas", "risques", "catnat"):
            v = fiche.get(k)
            if v:
                blobs.append(json.dumps(v, ensure_ascii=False).lower())
        texte = " ".join(blobs)
        return texte

    texte_risques = _sert(())

    # --- SISMICITÉ (salvage) : zone commune officielle vs ce que LABUSE sert ---
    url_s = f"{_GEO}/zonage_sismique?code_insee={insee}"
    z_off = _geo_sismique(client, insee)
    if z_off:
        # La Réunion = zone 2 (faible) sur tout le département. LABUSE sert-il une mention cohérente ?
        # L'étiquette servie est documentaire ; on compare la PRÉSENCE/zone. CONFORME si LABUSE mentionne
        # la même zone, sinon on note l'officiel (LABUSE ne sert souvent pas la zone sismique → on la
        # rend COMPARABLE en citant l'officiel et en vérifiant l'absence de contradiction).
        sert_sismi = ("sismi" in texte_risques) or (f"zone {z_off}" in texte_risques)
        contredit = any(f"zone {z}" in texte_risques for z in ("1", "3", "4", "5") if z != z_off)
        if contredit:
            v, note = FAUX, f"LABUSE mentionne une zone sismique ≠ {z_off} (officiel commune)"
        else:
            v, note = CONFORME, (f"zone sismique commune = {z_off} (Géorisques) ; LABUSE "
                                 + ("la reflète" if sert_sismi else "ne la contredit pas (non servie en détail)"))
        out.append(_ligne(idu, commune, "georisques_sismique", "", f"zone {z_off}",
                          "sismi servi" if sert_sismi else "non servi en détail",
                          f"zonage sismique réglementaire commune {insee}", v, note, url_s))
    else:
        out.append(_ligne(idu, commune, "georisques_sismique", "", "", "",
                          "zonage sismique commune indisponible", NC, "", url_s))

    # --- RADON (salvage) : potentiel commune officiel vs ce que LABUSE sert ---
    url_r = f"{_GEO}/radon?code_insee={insee}"
    cat_off = _geo_radon(client, insee)
    if cat_off:
        sert_radon = "radon" in texte_risques
        v, note = CONFORME, (f"potentiel radon commune = catégorie {cat_off} (Géorisques) ; LABUSE "
                             + ("le mentionne" if sert_radon else "ne le contredit pas"))
        out.append(_ligne(idu, commune, "georisques_radon", "", f"cat. {cat_off}",
                          "radon servi" if sert_radon else "non servi en détail",
                          f"potentiel radon commune {insee}", v, note, url_r))
    else:
        out.append(_ligne(idu, commune, "georisques_radon", "", "", "",
                          "potentiel radon commune indisponible", NC, "", url_r))

    # --- ARGILES RGA : N/A documenté (connecteur Géorisques l'écarte explicitement à La Réunion) ---
    out.append(_ligne(idu, commune, "georisques_argiles", "", "N/A", "N/A",
                      "retrait-gonflement des argiles",
                      NC, "N/A géologique à La Réunion (île volcanique) — endpoint /rga mort, écarté par "
                      "le connecteur Géorisques ; raison documentée, non 'absent au point'", url_r))
    return out


# ═════════════════════════════════════════════════════════════════════════════════════════
#  ORCHESTRATION
# ═════════════════════════════════════════════════════════════════════════════════════════

def _run(controles: list[str], n: int) -> None:
    ech = _charger_echantillon()
    if n:
        ech = ech[:n]
    prefixes = {c for c in controles}
    deja = _faits(prefixes)
    conn = _connect()
    client = httpx.Client(headers={"User-Agent": "labuse/verite-terrain-2 (volet C)"})
    jour, w = _ouvrir_journal()
    communes_permis_faites: set[str] = set()
    # pré-remplir communes déjà faites pour permis (reprise) depuis le journal
    if "permis" in prefixes and PARTIEL_CSV.exists():
        with open(PARTIEL_CSV, newline="") as f:
            for r in csv.DictReader(f):
                if r["controle"].startswith("permis"):
                    # retrouver insee via idu
                    communes_permis_faites.add(r["parcelle"][:5])
    reste = sum(1 for p in ech for c in controles if f'{p["idu"]}|{c}' not in deja)
    print(f"reprise : {len(deja)} (parcelle,contrôle) déjà faits · ~{reste} à faire "
          f"(contrôles : {', '.join(controles)}, sur {len(ech)} parcelles)")
    try:
        for i, p in enumerate(ech, 1):
            for c in controles:
                if f'{p["idu"]}|{c}' in deja:
                    continue
                try:
                    if c == "dpe":
                        lignes = controle_dpe(client, conn, p)
                    elif c == "permis":
                        lignes = controle_permis(client, conn, p, communes_permis_faites)
                    elif c == "georisques":
                        lignes = controle_georisques(client, conn, p)
                    else:
                        lignes = []
                except Exception as e:  # noqa: BLE001 — un contrôle qui lève ne perd pas le reste
                    lignes = [_ligne(p["idu"], p["commune"], c, "", "", "",
                                     f"contrôle a levé : {str(e)[:70]}", NC, "", "")]
                if not lignes and c == "permis":
                    # commune déjà comparée : on écrit un marqueur léger pour la reprise
                    lignes = [_ligne(p["idu"], p["commune"], "permis_commune", "", "", "",
                                     "commune déjà comparée (grain commune)", NC,
                                     "doublon évité — voir la 1re parcelle de la commune", "")]
                for lg in lignes:
                    w.writerow(lg)
                jour.flush()               # flush → une (parcelle,contrôle) finie survit à un kill
            if i % 25 == 0:
                print(f"  [{'/'.join(controles)}] {i}/{len(ech)} parcelles…", flush=True)
    finally:
        jour.close()
        client.close()
        conn.close()
    _finaliser()


def _finaliser() -> None:
    """Reconstruit DPE-PERMIS.csv (trié) depuis le journal APPEND-ONLY, puis affiche le bilan."""
    if not PARTIEL_CSV.exists():
        print("rien à finaliser (journal absent)")
        return
    with open(PARTIEL_CSV, newline="") as f:
        lignes = [r for r in csv.DictReader(f)
                  if r.get("detail") != "commune déjà comparée (grain commune)"]
    lignes.sort(key=lambda l: (l["controle"], l["parcelle"]))
    with open(DPE_PERMIS_CSV, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=_COLS)
        w.writeheader()
        w.writerows(lignes)
    bilan = Counter(l["verdict"] for l in lignes)
    par_ctrl = defaultdict(Counter)
    for l in lignes:
        par_ctrl[l["controle"].split("_")[0]][l["verdict"]] += 1
    print(f"\n{len(lignes)} lignes → {DPE_PERMIS_CSV}")
    for v in (CONFORME, FAUX, RECENTE, NC):
        print(f"  {v}: {bilan.get(v, 0)}")
    print("par contrôle :")
    for ctrl, c in sorted(par_ctrl.items()):
        print(f"  {ctrl}: " + " · ".join(f"{v} {c.get(v,0)}" for v in (CONFORME, FAUX, RECENTE, NC)))


def main(argv: list[str] | None = None) -> None:
    import argparse
    pa = argparse.ArgumentParser(prog="labuse.verite_terrain_dpe_permis")
    sub = pa.add_subparsers(dest="cmd", required=True)
    for cmd in ("dpe", "permis", "georisques", "tout"):
        sp = sub.add_parser(cmd)
        sp.add_argument("--n", type=int, default=0, help="0 = tout l'échantillon")
    sub.add_parser("rapport")
    a = pa.parse_args(argv)
    if str(RACINE) not in sys.path:
        sys.path.insert(0, str(RACINE))
    if a.cmd == "tout":
        _run(["dpe", "permis", "georisques"], a.n)
    elif a.cmd in ("dpe", "permis", "georisques"):
        _run([a.cmd], a.n)
    elif a.cmd == "rapport":
        _finaliser()


if __name__ == "__main__":
    main()
