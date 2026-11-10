"""PLU-VEILLE-FIX-1 — la VEILLE PLU/GPU : voir un nouveau document, l'appliquer en entier, prévenir.

Thème du mandat (audit `docs/audit-2026-11/plu-veille-1/RAPPORT.md`) : la sonde quotidienne lisait
`totalFeatures` — un COMPTE de documents — donc AVEUGLE au remplacement 1→1 (le cas d'une révision
sur une commune déjà dotée d'un PLU). Et quand le document bougeait, les couches ne suivaient pas
ensemble (Saint-Denis : zonage 05/08 servi, prescriptions restées au 23/04, aucun signal client).

Ici on tranche par PREUVE, couche par couche :
  · le DOCUMENT PUBLIÉ au Géoportail — l'IDENTIFIANT (idurba), lu sur `/document?partition=DU_<insee>`
    (champ `name`, ex. `97411_PLU_20260805`), ou à défaut l'idurba ancré au catalogue
    `config/plu_millesimes.yaml` (confronté aux pièces en M40) ;
  · le DOCUMENT RÉELLEMENT INGÉRÉ par couche :
      - zonage        → `spatial_layers kind='plu_gpu_zone'`      (attrs->>'idurba') ;
      - prescriptions → `spatial_layers kind='plu_gpu_prescription'` ;
      - informations  → `spatial_layers kind='dpu'` (droit de préemption urbain, le cas servi) ;
      - règles        → le calibrage chiffré servi (`plu.destinations.etat_commune`).
Verdict par commune :
  · `a_jour`      — toutes les couches présentes portent le MÊME document que le Géoportail, et les
                    règles chiffrées sont calibrées sur ce document ;
  · `desync`      — au moins une couche porte un document plus ANCIEN que la référence (remplacement
                    non suivi), ou les règles sont « à relire » (nouveau document servi, calibrage pas
                    encore refait) ⇒ « PLU modifié — règles en cours de mise à jour » côté client ;
  · `rnu`         — commune au RNU (aucun PLU) ;
  · `inconnu`     — ni Géoportail ni catalogue ni ingéré lisibles.

Le remplacement 1→1 est détecté le jour même : on compare l'identifiant, pas le compte.
Module PUR côté comparaison ; les I/O (Géoportail, base, ré-ingestion) sont injectables pour les tests.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date

from sqlalchemy import text

GPU_BASE = "https://apicarto.ign.fr/api/gpu"

# Les couches spatiales qui DOIVENT porter le document communal, dans l'ordre d'affichage.
# (clé interne, kind spatial_layers, libellé client)
COUCHES_SPATIALES: list[tuple[str, str, str]] = [
    ("zonage", "plu_gpu_zone", "zonage"),
    ("prescriptions", "plu_gpu_prescription", "prescriptions (ER, EBC, mixité…)"),
    ("informations", "dpu", "informations (droit de préemption urbain)"),
]
LIBELLE_COUCHE = {c[0]: c[2] for c in COUCHES_SPATIALES}
LIBELLE_COUCHE["regles"] = "règles chiffrées (destinations)"


def _date8(idurba: str | None) -> date | None:
    """`97411_PLU_20260805` → date(2026, 8, 5). None si pas de date AAAAMMJJ lisible."""
    if not idurba:
        return None
    m = re.search(r"(\d{8})", str(idurba))
    if not m:
        return None
    s = m.group(1)
    try:
        return date(int(s[:4]), int(s[4:6]), int(s[6:8]))
    except ValueError:
        return None


def _fr(d: date | None) -> str | None:
    return d.strftime("%d/%m/%Y") if d else None


# ─────────────────────────── le catalogue des 24 communes ───────────────────────────

def _catalogue() -> dict[str, dict]:
    """Le catalogue `config/plu_millesimes.yaml` (insee → {commune, idurba, date_mairie, statut})."""
    from .plu import destinations
    return destinations._millesimes()


def communes() -> list[tuple[str, str]]:
    """Les (insee, nom) des communes du catalogue, triés par code."""
    return [(i, c.get("commune") or i) for i, c in sorted(_catalogue().items())]


# ─────────────────────────── lecture de l'ingéré (base) ───────────────────────────

def idurba_ingere(db, insee: str, commune: str) -> dict:
    """Pour chaque couche spatiale, le document RÉELLEMENT ingéré de la commune (idurba propre à
    l'insee, pour écarter les débordements de bbox d'un document voisin). Retourne
    {couche: {idurba, date, ingere_le, n} | None}. Plusieurs idurba propres = incohérence interne :
    on garde le plus RÉCENT (et le signale via `n_idurba`)."""
    out: dict[str, dict | None] = {}
    for cle, kind, _lib in COUCHES_SPATIALES:
        rows = db.execute(text(
            "SELECT attrs->>'idurba' AS idurba, count(*) AS n, min(created_at)::date AS ingere_le "
            "FROM spatial_layers WHERE kind = :k AND commune = :c "
            "AND left(attrs->>'idurba', 5) = :insee AND attrs->>'idurba' IS NOT NULL "
            "GROUP BY 1 ORDER BY 1 DESC"),
            {"k": kind, "c": commune, "insee": insee}).mappings().all()
        if not rows:
            out[cle] = None
            continue
        # plus récent d'abord (idurba trié desc = date desc car suffixe AAAAMMJJ)
        best = max(rows, key=lambda r: (_date8(r["idurba"]) or date.min))
        out[cle] = {"idurba": best["idurba"], "date": _date8(best["idurba"]),
                    "ingere_le": best["ingere_le"],
                    "n": sum(r["n"] for r in rows), "n_idurba": len(rows)}
    return out


def idurba_regles(insee: str) -> dict:
    """Document gravé au calibrage chiffré servi + son état (`plu.destinations.etat_commune`)."""
    from .plu import destinations
    e = destinations.etat_commune(insee)
    doc = e.get("document_gpu")
    return {"idurba": doc, "date": _date8(doc), "etat": e.get("etat"),
            "document_gpu_servi": e.get("document_gpu_servi")}


# ─────────────────────────── lecture du publié (Géoportail) ───────────────────────────

def fetch_gpu_idurba(insee: str, *, client=None) -> dict | None:
    """Interroge `/document?partition=DU_<insee>` et rend {idurba, du_type, timestamp} du document
    d'urbanisme servi (PLU préféré au POS/CC). None si injoignable, illisible ou aucun document.
    `client` httpx injectable (tests/politesse réseau)."""
    own = client is None
    if own:
        import httpx

        from . import constants
        from .config import get_settings
        client = httpx.Client(timeout=max(get_settings().http_timeout_s, 30.0),
                              headers={"User-Agent": constants.USER_AGENT}, follow_redirects=True)
    try:
        r = client.get(f"{GPU_BASE}/document", params={"partition": f"DU_{insee}"})
        r.raise_for_status()
        feats = r.json().get("features") or []
    except Exception:  # noqa: BLE001 — injoignable/illisible → publié inconnu (jamais une exception)
        return None
    finally:
        if own:
            client.close()
    if not feats:
        return None
    docs = [f.get("properties") or {} for f in feats]
    plu = [p for p in docs if (p.get("du_type") or "").upper() == "PLU"]
    p = (plu or docs)[0]
    name = p.get("name") or p.get("idurba")
    if not name:
        return None
    return {"idurba": name, "du_type": p.get("du_type"), "timestamp": p.get("gpu_timestamp")}


def fetch_gpu_ile(communes_insee: list[str] | None = None, *, fetch=None) -> dict[str, dict | None]:
    """Le document GPU de chaque commune (politesse : une requête par commune). `fetch` injectable."""
    import time
    fetch = fetch or fetch_gpu_idurba
    out: dict[str, dict | None] = {}
    insees = communes_insee or [i for i, _ in communes()]
    for k, insee in enumerate(insees):
        out[insee] = fetch(insee)
        if fetch is fetch_gpu_idurba and k + 1 < len(insees):
            time.sleep(1.5)
    return out


# ─────────────────────────── le verdict par commune ───────────────────────────

@dataclass
class EtatPlu:
    insee: str
    commune: str
    etat: str                                   # a_jour | desync | rnu | inconnu
    publie: str | None = None                   # idurba servi par le Géoportail (ou catalogue)
    publie_source: str | None = None            # 'geoportail' | 'catalogue'
    reference: str | None = None                # le document que tout devrait porter
    date_modif: date | None = None              # date du document de référence (le « PLU modifié le … »)
    couches: dict = field(default_factory=dict)  # couche → {idurba, date, en_retard, absente}
    couches_en_retard: list[str] = field(default_factory=list)
    recalibrage_pending: bool = False
    ancien: str | None = None
    nouveau: str | None = None
    gestes: list[str] = field(default_factory=list)

    def as_dict(self) -> dict:
        d = dict(self.__dict__)
        d["date_modif"] = self.date_modif.isoformat() if self.date_modif else None
        d["date_modif_fr"] = _fr(self.date_modif)
        for c in d["couches"].values():
            if isinstance(c, dict) and isinstance(c.get("date"), date):
                c["date"] = c["date"].isoformat()
        return d


def etat_commune(db, insee: str, *, gpu: dict | None = None, publie: str | None = None) -> EtatPlu:
    """Le verdict d'une commune. `gpu` = résultat de `fetch_gpu_idurba` (ou None → catalogue) ;
    `publie` force l'idurba publié (tests). RÈGLE : `a_jour` SEULEMENT si toutes les couches
    présentes portent la référence ET les règles sont calibrées dessus."""
    cat = _catalogue().get(insee) or {}
    commune = cat.get("commune") or insee
    if cat.get("statut") == "rnu":
        return EtatPlu(insee=insee, commune=commune, etat="rnu",
                       publie=None, publie_source="catalogue")

    # publié : Géoportail en priorité (le signal qui détecte le 1→1), repli catalogue.
    pub, pub_src = None, None
    if publie:
        pub, pub_src = publie, "test"
    elif gpu and gpu.get("idurba"):
        pub, pub_src = gpu["idurba"], "geoportail"
    elif cat.get("idurba"):
        pub, pub_src = cat["idurba"], "catalogue"

    ing = idurba_ingere(db, insee, commune)
    reg = idurba_regles(insee)
    return verdict_pur(insee, commune, pub, pub_src, ing, reg,
                       demande_fn=lambda ref: recalibrage_pending(db, insee, ref))


def verdict_pur(insee: str, commune: str, pub: str | None, pub_src: str | None,
                ing: dict, reg: dict, *, demande_fn=lambda ref: False) -> EtatPlu:
    """Le VERDICT, pur (sans base) : à partir du publié, de l'ingéré par couche (`ing`), des règles
    (`reg`) et d'un prédicat `demande_fn(reference)` (drapeau « à recalibrer »). Testable seul.

    RÈGLE : `a_jour` SEULEMENT si toutes les couches présentes portent la référence ET les règles
    sont calibrées dessus (et aucun drapeau de recalibrage en cours)."""
    # référence = le document le plus récent entre le publié et tout ce qui est déjà en base.
    candidats = [c for c in ([pub, reg.get("idurba")] + [c["idurba"] for c in ing.values() if c]) if c]
    if not candidats:
        return EtatPlu(insee=insee, commune=commune, etat="inconnu",
                       publie=pub, publie_source=pub_src)
    reference = max(candidats, key=lambda c: (_date8(c) or date.min))
    ref_d = _date8(reference)

    couches: dict[str, dict] = {}
    en_retard: list[str] = []
    anciens: list[date] = []
    for cle, _kind, _lib in COUCHES_SPATIALES:
        c = ing.get(cle)
        if c is None:
            couches[cle] = {"idurba": None, "date": None, "absente": True, "en_retard": False}
            continue
        retard = bool(ref_d and c["date"] and c["date"] < ref_d)
        couches[cle] = {"idurba": c["idurba"], "date": c["date"], "ingere_le": c.get("ingere_le"),
                        "absente": False, "en_retard": retard}
        if retard:
            en_retard.append(cle)
            if c["date"]:
                anciens.append(c["date"])

    # règles chiffrées : « à relire » (document servi plus récent que le calibrage lu) OU calibrage
    # sur un document plus ancien que la référence OU drapeau « à recalibrer » posé par le geste
    # unique et pas encore validé (le client reste prévenu « règles en cours de mise à jour »).
    demande = bool(demande_fn(reference))
    reg_retard = demande or (reg.get("etat") == "a_relire") or bool(
        ref_d and reg.get("date") and reg["date"] < ref_d)
    couches["regles"] = {"idurba": reg.get("idurba"), "date": reg.get("date"),
                         "absente": reg.get("idurba") is None, "en_retard": reg_retard,
                         "etat_calibrage": reg.get("etat"), "demande_recalibrage": demande}
    if reg_retard:
        en_retard.append("regles")

    out = EtatPlu(insee=insee, commune=commune, etat="a_jour" if not en_retard else "desync",
                  publie=pub, publie_source=pub_src, reference=reference, date_modif=ref_d,
                  couches=couches, couches_en_retard=en_retard,
                  recalibrage_pending=bool(en_retard), nouveau=reference)
    out.ancien = (ing.get("prescriptions") or {}).get("idurba") if "prescriptions" in en_retard else \
        next((couches[c]["idurba"] for c in en_retard if couches[c].get("idurba")), None)
    out.gestes = _gestes(en_retard, couches, reference)
    return out


def _gestes(en_retard: list[str], couches: dict, reference: str | None) -> list[str]:
    """La liste des gestes à faire pour remettre la commune « à jour » — du concret, pas du jargon."""
    g: list[str] = []
    for c in en_retard:
        if c == "regles":
            g.append("Recalibrer les règles chiffrées (destinations) sur le nouveau document, "
                     "puis valider.")
        else:
            actuel = (couches.get(c) or {}).get("idurba") or "absent"
            g.append(f"Réingérer le {LIBELLE_COUCHE.get(c, c)} ({actuel} → {reference}).")
    if en_retard:
        g.append("Appliquer d'un seul geste : `labuse plu appliquer --insee <code>` "
                 "(zonage + prescriptions + informations + drapeau règles ensemble).")
    return g


def tableau_ile(db, *, gpu_par_insee: dict | None = None) -> list[dict]:
    """L'ÉTAT DES LIEUX des 24 communes : pour chacune, le document GPU face à l'ingéré par couche.
    `gpu_par_insee` = cache de `fetch_gpu_ile` (None → catalogue seul, hors réseau)."""
    gpu_par_insee = gpu_par_insee or {}
    out = []
    for insee, _nom in communes():
        e = etat_commune(db, insee, gpu=gpu_par_insee.get(insee))
        out.append(e.as_dict())
    return out


# ─────────────────────────── l'instantané de nuit (page Données) ───────────────────────────

_DDL = """
CREATE TABLE IF NOT EXISTS plu_veille_etat (
  insee           varchar(5) PRIMARY KEY,
  commune         text NOT NULL,
  etat            text NOT NULL,                 -- a_jour | desync | rnu | inconnu
  publie          text,                          -- idurba servi par le Géoportail (ou catalogue)
  publie_source   text,
  reference       text,
  date_modif      date,                          -- date du document de référence (le « PLU modifié le … »)
  couches_en_retard jsonb,
  recalibrage_pending boolean NOT NULL DEFAULT false,
  ancien          text,
  nouveau         text,
  gestes          jsonb,
  detecte_le      timestamptz NOT NULL DEFAULT now(),
  recalibre_le    timestamptz                    -- quand les règles ont été revalidées (NULL = en cours)
)
"""


def ensure_table(db) -> None:
    db.execute(text(_DDL))


def rejouer_nuit(db, *, gpu_par_insee: dict | None = None) -> dict:
    """Rejoue le tableau des 24 communes et écrit l'instantané `plu_veille_etat`. Préserve
    `recalibre_le` tant que le même document reste la référence (un recalibrage validé ne se
    « re-détecte » pas en boucle). Retourne les communes en `desync`."""
    import json
    ensure_table(db)
    ancien = {r["insee"]: dict(r) for r in db.execute(text(
        "SELECT insee, reference, recalibre_le FROM plu_veille_etat")).mappings().all()}
    etats = tableau_ile(db, gpu_par_insee=gpu_par_insee)
    for e in etats:
        prec = ancien.get(e["insee"])
        # on garde recalibre_le SSI la référence n'a pas changé depuis le dernier passage.
        recalibre = (prec.get("recalibre_le") if prec and prec.get("reference") == e.get("reference")
                     else None)
        db.execute(text(
            "INSERT INTO plu_veille_etat (insee, commune, etat, publie, publie_source, reference, "
            " date_modif, couches_en_retard, recalibrage_pending, ancien, nouveau, gestes, "
            " detecte_le, recalibre_le) "
            "VALUES (:insee, :commune, :etat, :publie, :psrc, :ref, :dmod, CAST(:cer AS jsonb), "
            " :recal, :anc, :nouv, CAST(:gestes AS jsonb), now(), :rl) "
            "ON CONFLICT (insee) DO UPDATE SET commune=EXCLUDED.commune, etat=EXCLUDED.etat, "
            " publie=EXCLUDED.publie, publie_source=EXCLUDED.publie_source, reference=EXCLUDED.reference, "
            " date_modif=EXCLUDED.date_modif, couches_en_retard=EXCLUDED.couches_en_retard, "
            " recalibrage_pending=EXCLUDED.recalibrage_pending, ancien=EXCLUDED.ancien, "
            " nouveau=EXCLUDED.nouveau, gestes=EXCLUDED.gestes, detecte_le=now(), "
            " recalibre_le=EXCLUDED.recalibre_le"),
            {"insee": e["insee"], "commune": e["commune"], "etat": e["etat"], "publie": e["publie"],
             "psrc": e["publie_source"], "ref": e["reference"], "dmod": e["date_modif"],
             "cer": json.dumps(e["couches_en_retard"]), "recal": e["recalibrage_pending"],
             "anc": e["ancien"], "nouv": e["nouveau"], "gestes": json.dumps(e["gestes"], ensure_ascii=False),
             "rl": recalibre})
    desync = [e for e in etats if e["etat"] == "desync"]
    return {"total": len(etats), "desync": desync,
            "a_jour": sum(1 for e in etats if e["etat"] == "a_jour")}


def lire_etat(db, insee: str) -> dict | None:
    """L'état servi d'une commune (fiche/documents/exploitation). None si non encore sondé."""
    ensure_table(db)
    r = db.execute(text(
        "SELECT insee, commune, etat, publie, reference, date_modif, couches_en_retard, "
        " recalibrage_pending, ancien, nouveau, gestes, detecte_le, recalibre_le "
        "FROM plu_veille_etat WHERE insee = :i"), {"i": insee}).mappings().first()
    if r is None:
        return None
    d = dict(r)
    d["date_modif"] = d["date_modif"].isoformat() if d["date_modif"] else None
    d["date_modif_fr"] = _fr(_date8(d["reference"]) or (
        date.fromisoformat(r["date_modif"].isoformat()) if r["date_modif"] else None))
    for k in ("detecte_le", "recalibre_le"):
        if d.get(k) is not None:
            d[k] = d[k].isoformat()
    return d


# ─────────────────────────── le drapeau « règles à recalibrer » ───────────────────────────
# Posé PAR LE GESTE UNIQUE (avec les couches), levé à la VALIDATION des règles recalibrées. Tant
# qu'il est posé, le client reste prévenu « règles en cours de mise à jour » et les parcelles sont
# « À vérifier » — même si zonage/prescriptions/informations portent déjà le nouveau document.

_DDL_RECAL = """
CREATE TABLE IF NOT EXISTS plu_recalibrage (
  insee       varchar(5) PRIMARY KEY,
  reference   text NOT NULL,              -- document pour lequel les règles sont à recalibrer
  demande_le  timestamptz NOT NULL DEFAULT now(),
  valide_le   timestamptz                 -- NULL = en cours ; horodaté = règles revalidées
)
"""


def _ensure_recal(db) -> None:
    db.execute(text(_DDL_RECAL))


def demander_recalibrage(db, insee: str, reference: str) -> None:
    """Pose le drapeau « règles à recalibrer » pour `reference` (remplace une demande antérieure)."""
    _ensure_recal(db)
    db.execute(text(
        "INSERT INTO plu_recalibrage (insee, reference, demande_le, valide_le) "
        "VALUES (:i, :r, now(), NULL) "
        "ON CONFLICT (insee) DO UPDATE SET reference = EXCLUDED.reference, "
        " demande_le = now(), valide_le = NULL"),
        {"i": insee, "r": reference})


def valider_recalibrage(db, insee: str) -> bool:
    """Lève le drapeau : les règles ont été recalibrées et validées. True si un drapeau était posé."""
    _ensure_recal(db)
    return bool(db.execute(text(
        "UPDATE plu_recalibrage SET valide_le = now() WHERE insee = :i AND valide_le IS NULL"),
        {"i": insee}).rowcount)


def recalibrage_pending(db, insee: str, reference: str | None) -> bool:
    """Un recalibrage est-il DÛ pour le document de référence (drapeau posé, pas encore validé) ?"""
    _ensure_recal(db)
    if not reference:
        return False
    return bool(db.execute(text(
        "SELECT 1 FROM plu_recalibrage WHERE insee = :i AND reference = :r AND valide_le IS NULL"),
        {"i": insee, "r": reference}).scalar())


# ─────────────────────────── le geste unique : appliquer un PLU EN ENTIER ───────────────────────────

def appliquer_plu(db, insee: str, *, commune: str | None = None, bbox=None, run_id=None,
                  log=print) -> dict:
    """LE GESTE UNIQUE. Applique un document d'urbanisme EN ENTIER, d'un seul tenant, dans UNE
    transaction : zonage + prescriptions + informations (DPU) ré-ingérés ensemble, PUIS le drapeau
    « règles à recalibrer » posé. Il n'existe AUCUN chemin qui mette à jour une couche sans les
    autres : le statut « à jour » d'une commune exige que toutes portent le même document, et le
    drapeau garde le client prévenu jusqu'à la validation des règles. Rend un bilan par couche.

    N.B. serving : après ce geste, la prod rebâtit `parcel_zone_plu` puis `build-mvt`/`promote`
    (couche servie) — documenté dans la procédure prod, hors de cette transaction de données."""
    from .ingestion import gpu_infos, layers_ingest, run_all, seed_sources
    cat = _catalogue().get(insee) or {}
    commune = commune or cat.get("commune")
    if not commune:
        raise ValueError(f"commune inconnue pour l'insee {insee}")
    if cat.get("statut") == "rnu":
        raise ValueError(f"{commune} est au RNU — aucun PLU à appliquer")
    seed_sources.seed(db)
    sids = layers_ingest._source_ids(db)
    bbox = bbox or run_all._commune_bbox(db, commune)
    if bbox is None:
        raise ValueError(f"aucune parcelle en base pour {commune} — ingère la commune d'abord")

    bilan: dict[str, object] = {}
    # 1) zonage — purge la commune puis ré-ingère
    db.execute(text("DELETE FROM spatial_layers WHERE kind='plu_gpu_zone' AND commune=:c"),
               {"c": commune})
    bilan["zonage"] = layers_ingest.ingest_gpu_zones(db, insee, bbox, commune, run_id, sids)
    # 2) prescriptions (ER, EBC, mixité…) — purge la commune puis ré-ingère
    db.execute(text("DELETE FROM spatial_layers WHERE kind='plu_gpu_prescription' AND commune=:c"),
               {"c": commune})
    bilan["prescriptions"] = layers_ingest.ingest_gpu_prescriptions(
        db, bbox, commune, run_id, sids, insee=insee)
    # 3) informations (DPU de la commune) — refresh ciblé
    sid_dpu = sids.get(gpu_infos.SOURCE_DPU)
    sid_peb = sids.get(gpu_infos.SOURCE_PEB)
    info = gpu_infos.ingest_gpu_infos(db, run_id=run_id, source_id_dpu=sid_dpu,
                                      source_id_peb=sid_peb, log=log, only_insee=insee)
    bilan["informations"] = info.get("dpu", 0)
    db.flush()

    # 4) le drapeau « règles à recalibrer » — posé AVEC les couches (jamais après coup, jamais seul).
    ing = idurba_ingere(db, insee, commune)
    candidats = [c["idurba"] for c in ing.values() if c]
    reference = max(candidats, key=lambda c: (_date8(c) or date.min)) if candidats else cat.get("idurba")
    if reference:
        demander_recalibrage(db, insee, reference)
    bilan["reference"] = reference
    bilan["commune"] = commune
    bilan["insee"] = insee
    log(f"geste unique {commune} ({insee}) : {bilan['zonage']} zones, {bilan['prescriptions']} "
        f"prescriptions, {bilan['informations']} informations → {reference} ; règles à recalibrer.")
    return bilan


def communes_desync(db) -> dict[str, dict]:
    """{nom_commune: état} des communes en cours de mise à jour (desync) — pour l'overlay scénarios
    et le bandeau fiche. Lu de l'instantané servi."""
    ensure_table(db)
    rows = db.execute(text(
        "SELECT insee, commune, reference, date_modif FROM plu_veille_etat WHERE etat = 'desync'")
    ).mappings().all()
    out = {}
    for r in rows:
        d = _date8(r["reference"]) or r["date_modif"]
        out[r["commune"]] = {"insee": r["insee"], "commune": r["commune"],
                             "date_modif_fr": _fr(d) if d else None, "reference": r["reference"]}
    return out
