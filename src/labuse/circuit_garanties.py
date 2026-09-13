"""CIRCUIT-6 — les sept garanties. Une phrase en français, un verrou qui casse la CI,
un endroit sur la page Circuit (le bloc « garanties » du Résumé, lot 8).

Doctrine : ces verrous lisent le CODE du registre (donnees/robinets/tables, la vérité) et les
tables d'exploitation (data_sources, source_veille…) — jamais le miroir registre_* (qui peut
être en retard d'une branche sur la base partagée). Même dataclass ResultatVerrou que
circuit_verrous (CIRCUIT-5) : verdict ok | casse | a_decider, preuve en une ligne.
"""
from __future__ import annotations

from sqlalchemy import text
from sqlalchemy.orm import Session

from .circuit_verrous import ResultatVerrou

# ── G1 — toutes les sources, une seule fois ────────────────────────────────────────────

#: statuts admis pour une ligne data_sources (liste FERMÉE — un statut inventé casse G1).
STATUTS_ADMIS = frozenset({"connecte", "manuel", "a_faire", "retiree", "alias", "hub"})

#: paires de sources qui portent le MÊME concept sans partager table/endpoint (détection
#: par recouvrement impossible) — déclarées ici, l'arbitrage reste exigé comme pour les autres.
CONCEPTS_PARTAGES: dict[str, tuple[str, ...]] = {
    "DVF (mutations foncières)": ("DVF / valeurs foncières", "DVF Réunion (Région, data.regionreunion.com)"),
    "SIRENE (entreprises)": ("SIRENE", "Recherche d'entreprises (DINUM)", "SIRENE établissements géolocalisés"),
}

#: jetons qui valent ARBITRAGE ÉCRIT dans une note (technical_notes de la base, ou note du
#: réservoir dans registre/tables.py) : le doublon est connu, tranché, la raison est lisible.
_JETONS_ARBITRAGE = ("DOUBLON", "ARBITRAGE", "LOGIQUE", "canonique", "échantillon", "témoin",
                     "subtype", "canal")

#: passerelles MUTUALISÉES : un même endpoint y sert N jeux distincts par paramètre
#: (typename WFS, requête Overpass, couche Carmen, catégorie GPU). Partager cette URL n'est
#: PAS un doublon — la détection par endpoint les ignore (les règles table/kind/concept restent).
PASSERELLES_MUTUALISEES = (
    "data.geopf.fr/wfs", "data.geopf.fr/wms", "overpass-api.de",
    "ws.carmen.developpement-durable.gouv.fr", "apicarto.ign.fr/api/gpu",
    "georisques.gouv.fr/api",
)


def _a_arbitrage(txt_: str | None) -> bool:
    t = txt_ or ""
    return any(j in t for j in _JETONS_ARBITRAGE)


def catalogue_compteurs(db: Session) -> dict:
    """G1 — les nombres CALCULÉS : total, vitrine, par statut. Jamais gravés."""
    from .sources_catalog import WHERE_AFFICHEES, masquees_param
    par_statut = {s: n for s, n in db.execute(text(
        "SELECT status, count(*) FROM data_sources GROUP BY status"))}
    total = sum(par_statut.values())
    vitrine = db.execute(text(
        f"SELECT count(*) FROM data_sources WHERE {WHERE_AFFICHEES}"),
        {"masquees": masquees_param()}).scalar() or 0
    return {"total": total, "vitrine": vitrine, "par_statut": par_statut,
            "hors_vitrine": total - vitrine}


def detecter_doublons(db: Session) -> list[dict]:
    """G1 — deux sources qui alimentent le même concept, partagent une table (hors
    spatial_layers), une couche (kind) ou un endpoint : signalées, avec leur arbitrage s'il
    est écrit (alias_de, note DOUBLON/ARBITRAGE en base, note LOGIQUE/… dans tables.py)."""
    rows = db.execute(text(
        "SELECT id, name, status, endpoint_url, technical_notes, alias_de"
        " FROM data_sources ORDER BY id")).mappings().all()
    return analyse_doublons([dict(r) for r in rows])


def analyse_doublons(rows: list[dict]) -> list[dict]:
    """Le cœur PUR de la détection (testable sur des lignes construites)."""
    from .circuit_etats import NOM_VERS_SLUG
    from .registre.tables import RESERVOIR_TABLES
    par_nom = {r["name"]: r for r in rows}

    def note_reservoir(name: str) -> str:
        slug = NOM_VERS_SLUG.get(name)
        rt = RESERVOIR_TABLES.get(slug) if slug else None
        return (rt.note or "") if rt else ""

    def arbitrage(a: dict, b: dict) -> str | None:
        for r in (a, b):
            if r["alias_de"]:
                return f"alias (alias_de={r['alias_de']})"
            if _a_arbitrage(r["technical_notes"]):
                return "note en base"
            if _a_arbitrage(note_reservoir(r["name"])):
                return "note du réservoir (tables.py)"
        return None

    paires: dict[tuple[int, int], dict] = {}

    def signale(a: dict, b: dict, raison: str):
        cle = tuple(sorted((a["id"], b["id"])))
        if cle in paires:
            paires[cle]["raisons"].append(raison)
            return
        paires[cle] = {"ids": list(cle), "noms": [par_nom_id[cle[0]], par_nom_id[cle[1]]],
                       "raisons": [raison], "arbitrage": arbitrage(a, b)}

    par_nom_id = {r["id"]: r["name"] for r in rows}
    # (a) même endpoint — hors passerelles mutualisées (un endpoint, N jeux par paramètre)
    par_endpoint: dict[str, list[dict]] = {}
    for r in rows:
        ep = (r["endpoint_url"] or "").strip().rstrip("/")
        if ep and not any(p in ep for p in PASSERELLES_MUTUALISEES):
            par_endpoint.setdefault(ep, []).append(r)
    for ep, grp in par_endpoint.items():
        for i in range(len(grp)):
            for j in range(i + 1, len(grp)):
                signale(grp[i], grp[j], f"même endpoint ({ep.split('//')[-1][:60]})")
    # (b) même table hors spatial_layers · (c) même couche (kind)
    par_table: dict[str, list[dict]] = {}
    par_kind: dict[str, list[dict]] = {}
    for r in rows:
        slug = NOM_VERS_SLUG.get(r["name"])
        rt = RESERVOIR_TABLES.get(slug) if slug else None
        if not rt:
            continue
        for t in rt.tables:
            if t != "spatial_layers":
                par_table.setdefault(t, []).append(r)
        for k in rt.couches:
            par_kind.setdefault(k, []).append(r)
    for t, grp in par_table.items():
        for i in range(len(grp)):
            for j in range(i + 1, len(grp)):
                signale(grp[i], grp[j], f"même table ({t})")
    for k, grp in par_kind.items():
        for i in range(len(grp)):
            for j in range(i + 1, len(grp)):
                signale(grp[i], grp[j], f"même couche (kind {k})")
    # (d) même concept déclaré
    for concept, noms in CONCEPTS_PARTAGES.items():
        present = [par_nom[n] for n in noms if n in par_nom]
        for i in range(len(present)):
            for j in range(i + 1, len(present)):
                signale(present[i], present[j], f"même concept ({concept})")
    return sorted(paires.values(), key=lambda p: p["ids"])


def verrou_g1(db: Session) -> ResultatVerrou:
    phrase = ("La page Circuit montre les 116 sources de la base, chacune avec son état "
              "(liste fermée), et signale tout doublon — aucun doublon sans arbitrage écrit.")
    pbs: list[str] = []
    cpt = catalogue_compteurs(db)
    inconnus = sorted(set(cpt["par_statut"]) - STATUTS_ADMIS)
    for s in inconnus:
        pbs.append(f"statut hors liste fermée : {s} ({cpt['par_statut'][s]} ligne(s))")
    doublons = detecter_doublons(db)
    sans_arb = [d for d in doublons if not d["arbitrage"]]
    for d in sans_arb:
        pbs.append("doublon sans arbitrage : " + " ↔ ".join(d["noms"])
                   + " — " + "; ".join(d["raisons"][:2]))
    preuve = (f"{cpt['total']} en base = {cpt['vitrine']} en vitrine + {cpt['hors_vitrine']} "
              f"hors vitrine ; {len(doublons)} recouvrement(s) signalé(s), "
              f"{len(sans_arb)} sans arbitrage")
    return ResultatVerrou("G1", phrase, "casse" if pbs else "ok", preuve, pbs[:10])


# ── G2 — visible ou pas, je le sais ────────────────────────────────────────────────────

def mesures_remplissage(db: Session, *, rapide: bool = True) -> dict[str, dict]:
    """Le remplissage des sources en vitrine sur les 12 témoins du jour (moteur lot 2).
    rapide=True : types parcelle/commune seulement (les couches carte ne peuvent pas être
    « invisibles » et leur mesure par kind×commune coûte ~1-2 s pièce — la nuit s'en charge)."""
    from .registre import remplissage as R
    temoins = R.temoins_du_jour(db)
    mesures = R.mesurer_vitrine(db, temoins, rapide=rapide)
    return mesures


def invisibles_mesures(db: Session) -> list[dict]:
    """Les sources BRANCHÉES MAIS VIDES (signature DPE : type parcelle, 0/12 témoins,
    table quasi vide) — le verdict INVISIBLE que la page doit afficher."""
    return sorted(
        ({"slug": slug, **m} for slug, m in mesures_remplissage(db).items() if m["quasi_vide"]),
        key=lambda m: m["slug"])


_CACHE_VIDES: dict = {"t": 0.0, "v": None}


def noms_vides_caches(db: Session, ttl: int = 300) -> set[str]:
    """Les NOMS de sources vides, avec un cache court (la page /sources et le catalogue les
    consultent à chaque rendu — la mesure vaut ~2 s, le cache 5 min l'amortit)."""
    import time
    now = time.monotonic()
    if _CACHE_VIDES["v"] is None or now - _CACHE_VIDES["t"] > ttl:
        _CACHE_VIDES["v"] = {m["nom"] for m in invisibles_mesures(db)}
        _CACHE_VIDES["t"] = now
    return _CACHE_VIDES["v"]


def verrou_g2(db: Session) -> ResultatVerrou:
    phrase = ("Pour chaque source, la page dit sur quelle surface elle arrive et si sa fiche "
              "est réellement remplie — aucune source connectée de type parcelle vide sur "
              "l'ensemble des témoins sans un état INVISIBLE affiché.")
    from .circuit_etats import etat_reservoir
    vides = invisibles_mesures(db)
    pbs: list[str] = []
    for m in vides:
        # l'état que la PAGE affichera pour ce réservoir (le drapeau `invisible` est posé par
        # l'assembleur du dashboard depuis la MÊME mesure) — s'il ne sort pas rouge-INVISIBLE,
        # le circuit dit « à jour » sur une source vide : le mensonge DPE.
        couleur, libelle = etat_reservoir({"invisible": True, "mode": "cron_mensuel",
                                           "veille": {"statut": "ok"}, "filtre": {}})
        if not (couleur == "rouge" and "INVISIBLE" in libelle):
            pbs.append(f"{m['nom']} : vide mesurée ({m['remplis']}/{m['n_temoins']} témoins, "
                       f"table quasi vide) mais l'état affiché est « {libelle} » ({couleur})")
    preuve = (f"{len(vides)} source(s) vide(s) mesurée(s) sur les 12 témoins"
              + (f" ({', '.join(v['slug'] for v in vides)})" if vides else "")
              + f" ; {len(pbs)} sans état INVISIBLE")
    return ResultatVerrou("G2", phrase, "casse" if pbs else "ok", preuve, pbs[:10])


# ── G3 — je sais ce qui nourrit le score ───────────────────────────────────────────────

#: variable du modèle P servi → réservoir(s) qui la nourrissent. Liste FERMÉE : une feature
#: absente de cette carte casse G3 (on ne devine jamais). Curée depuis features.py (champ
#: source, texte libre) — la vérité lisible par variable.
FEATURE_RESERVOIRS: dict[str, tuple[str, ...]] = {
    "rot_nu": ("dvf",), "rot_bati": ("dvf",),
    "med_pm2_terrain_36m": ("dvf",), "med_pm2_bati_36m": ("dvf",),
    "tendance_pm2_bati": ("dvf",), "window_coverage": ("dvf",), "tenure_bin": ("dvf",),
    "permis_24m_norm": ("sitadel",), "permis_bin": ("sitadel",),
    "dens_bati_secteur": ("bd_topo",), "pct_bati_secteur": ("bd_topo",),
    "nu_constructible": ("bd_topo", "gpu_plu_api_carto"),
    "filo_snv_pp": ("filosofi_carreaux",), "filo_pct_pauv": ("filosofi_carreaux",),
    "filo_pct_prop": ("filosofi_carreaux",), "filo_dens_pop": ("filosofi_carreaux",),
    "qpv": ("qpv_2024",),
    "pente_moy_deg": ("rge_alti",),
    "acces_equipements": ("osm_overpass",),
    "zone_plu": ("gpu_plu_api_carto",),
    "surface_m2": ("cadastre_api_carto",),
    "dormance_droits": ("cosia", "gpu_plu_api_carto"),
    "sous_densite": ("cosia", "gpu_plu_api_carto"),
    "sdp_residuelle_m2": ("cosia", "gpu_plu_api_carto"),
    "canopee_pct": ("bd_ortho_irc",), "ndvi_moyen": ("bd_ortho_irc",),
    "friche": ("cartofriches",),
    "piscine": ("bd_ortho",), "pv_candidat": ("bd_ortho",),
}

#: kinds LOGIQUES de la cascade (config/cascade_rules.yaml) → kind physique / réservoir.
CASCADE_KIND_ALIASES = {
    "eau": "water", "risques": "georisque_alea", "zonage_plu_gpu": "plu_gpu_zone",
    "prescription_plu": "plu_gpu_prescription", "bati": "batiment", "acces": "voirie",
}
#: couches cascade SANS réservoir (calcul pur : surface de la parcelle, faux positifs curés).
CASCADE_SANS_RESERVOIR = frozenset({"surface", "osm_faux_positif"})


def sources_du_score() -> dict[str, dict]:
    """La liste fermée : slug réservoir → {variables score, couches cascade}. Calculée depuis
    features.py (via FEATURE_RESERVOIRS) et cascade_rules.yaml (kinds → réservoirs par la
    carte tables.py). C'est ce que la fiche d'une source affiche (« nourrit le score via… »)."""
    from .config import load_yaml_config
    from .registre.tables import RESERVOIR_TABLES
    out: dict[str, dict] = {}
    for feat, slugs in FEATURE_RESERVOIRS.items():
        for slug in slugs:
            out.setdefault(slug, {"variables": [], "cascade": []})["variables"].append(feat)
    kind_vers_slugs: dict[str, list[str]] = {}
    for slug, rt in RESERVOIR_TABLES.items():
        for k in rt.couches:
            kind_vers_slugs.setdefault(k, []).append(slug)
    regles = load_yaml_config("cascade_rules")
    for layer in regles.get("layers", []):
        kind = layer.get("kind") or layer.get("name") or ""
        if kind in CASCADE_SANS_RESERVOIR:
            continue
        k = CASCADE_KIND_ALIASES.get(kind, kind)
        for slug in kind_vers_slugs.get(k, []):
            entry = out.setdefault(slug, {"variables": [], "cascade": []})
            if kind not in entry["cascade"]:
                entry["cascade"].append(kind)
    return out


def repere_score(db: Session) -> dict:
    """Le repère de la page : N sources peuvent déclencher un run · dernière maj de l'une
    d'elles le … · run servi calculé le … (ce qui dit à Vic s'il doit recalculer)."""
    from .circuit_etats import NOM_VERS_SLUG
    slugs = set(sources_du_score())
    noms = [n for n, s in NOM_VERS_SLUG.items() if s in slugs]
    row = db.execute(text(
        "SELECT max(last_sync_at) FROM data_sources WHERE name = ANY(:n)"), {"n": noms}).scalar()
    from . import runs
    servi = None
    try:
        servi = runs.current()
    except Exception:  # noqa: BLE001
        pass
    return {"n_sources": len(slugs), "derniere_maj": row.isoformat() if row else None,
            "run_servi": servi}


def verrou_g3(db: Session, features=None) -> ResultatVerrou:
    phrase = ("Chaque source dit si elle nourrit le score ou la cascade, par quelle variable — "
              "et aucune variable du modèle servi n'est nourrie par une source hors registre, "
              "retirée, ou vide.")
    from .circuit_etats import NOM_VERS_SLUG
    if features is None:
        from .scoring.p_model.features import FEATURES
        features = [f.name for f in FEATURES]
    slugs_registre = set(NOM_VERS_SLUG.values())
    pbs: list[str] = []
    for feat in features:
        if feat not in FEATURE_RESERVOIRS:
            pbs.append(f"variable {feat} : aucune source déclarée (FEATURE_RESERVOIRS)")
    statuts = {s: st for s, st in db.execute(text(
        "SELECT name, status FROM data_sources"))}
    slug_vers_nom = {v: k for k, v in NOM_VERS_SLUG.items()}
    vides = {m["slug"] for m in invisibles_mesures(db)}
    for slug in sorted(sources_du_score()):
        if slug not in slugs_registre:
            pbs.append(f"réservoir {slug} : hors registre (pont NOM_VERS_SLUG)")
            continue
        st = statuts.get(slug_vers_nom.get(slug, ""))
        if st == "retiree":
            pbs.append(f"réservoir {slug} : source RETIRÉE nourrit encore le score")
        if slug in vides:
            pbs.append(f"réservoir {slug} : source VIDE (mesure témoins) nourrit le score")
    rep = repere_score(db)
    preuve = (f"{rep['n_sources']} sources nourrissent score/cascade · dernière maj "
              f"{(rep['derniere_maj'] or 'inconnue')[:10]} · run servi {rep['run_servi']}"
              f" ; {len(pbs)} problème(s)")
    return ResultatVerrou("G3", phrase, "casse" if pbs else "ok", preuve, pbs[:10])


# ── G4 — dernière version ou pas ───────────────────────────────────────────────────────

def verrou_g4(db: Session) -> ResultatVerrou:
    phrase = ("Chaque source connectée porte soit un état de version calculé (sonde), soit une "
              "raison de non-vérifiabilité écrite — jamais rien ; et « à jour » n'est jamais "
              "vrai sur une source vide (version ET remplissage).")
    from .etats_sources import lister_etats
    from .sentinelle import RAISONS_NON_SURVEILLEES
    from .sources_catalog import WHERE_AFFICHEES, masquees_param
    pbs: list[str] = []
    rows = db.execute(text(
        "SELECT d.name, v.methode FROM data_sources d"
        " LEFT JOIN source_veille v ON v.source_id = d.id"
        f" WHERE {WHERE_AFFICHEES}"), {"masquees": masquees_param()}).all()
    nus = sorted(n for n, m in rows if not m and n not in RAISONS_NON_SURVEILLEES)
    for n in nus:
        pbs.append(f"{n} : ni sonde ni raison de non-vérifiabilité")
    vides = noms_vides_caches(db)
    etats = {e["name"]: e for e in lister_etats(db)}
    for n in sorted(vides):
        e = etats.get(n)
        if e and e.get("etat_client") == "a_jour":
            pbs.append(f"{n} : VIDE mesurée mais l'état client dit « à jour »")
    n_sondees = sum(1 for _, m in rows if m)
    preuve = (f"{len(rows)} en vitrine : {n_sondees} sondées + "
              f"{len(rows) - n_sondees - len(nus)} avec raison écrite + {len(nus)} NUES ; "
              f"{len(vides)} vide(s) → état « pas à jour »")
    return ResultatVerrou("G4", phrase, "casse" if pbs else "ok", preuve, pbs[:10])


# ── G5 — date du dernier contrôle ──────────────────────────────────────────────────────

def verrou_g5(db: Session) -> ResultatVerrou:
    phrase = ("Pour chaque source, la date du dernier contrôle est affichée — et une source "
              "jamais contrôlée le dit, en rouge, jamais en silence.")
    from .circuit_etats import etat_reservoir
    from .sources_catalog import WHERE_AFFICHEES, masquees_param
    rows = db.execute(text(
        "SELECT d.name, d.last_sync_at, d.mode_remplissage,"
        "       v.methode, v.dernier_passage_at, v.dernier_statut"
        " FROM data_sources d LEFT JOIN source_veille v ON v.source_id = d.id"
        f" WHERE {WHERE_AFFICHEES}"), {"masquees": masquees_param()}).mappings().all()
    pbs: list[str] = []
    jamais = 0
    for r in rows:
        derniers = [d for d in (r["dernier_passage_at"], r["last_sync_at"]) if d is not None]
        dernier_controle = max(derniers) if derniers else None
        veille = ({"statut": r["dernier_statut"],
                   "passage": r["dernier_passage_at"]} if r["methode"] else None)
        couleur, libelle = etat_reservoir({"veille": veille, "dernier_controle": dernier_controle,
                                           "mode": r["mode_remplissage"] or "one_shot",
                                           "filtre": {}})
        if libelle == "jamais vérifié":
            jamais += 1
            if couleur != "rouge":
                pbs.append(f"{r['name']} : jamais vérifié affiché en {couleur}, pas en rouge")
        elif dernier_controle is None and "jamais" not in libelle and libelle != "vide":
            # un état PARLANT (« vide », « … jamais alimenté ») couvre l'absence de date ;
            # tout le reste sans date est un blanc — la garantie casse.
            pbs.append(f"{r['name']} : aucune date de contrôle ET aucune mention "
                       f"« jamais » (état « {libelle} »)")
    preuve = (f"{len(rows)} en vitrine : {len(rows) - jamais} avec date de dernier contrôle "
              f"ou état parlant, {jamais} « jamais vérifié » (affichés ROUGE)")
    return ResultatVerrou("G5", phrase, "casse" if pbs else "ok", preuve, pbs[:10])


# ── G6 — quelle donnée alimente quoi (le graphe, dans les DEUX sens) ───────────────────

#: répertoires de src/labuse dont les fichiers ÉCRIVENT ou outillent les réservoirs — pas des
#: lecteurs d'affichage (l'ingestion remplit, la machinerie contrôle) : exemptés du sens inverse.
_REPERTOIRES_EXEMPTS_G6 = ("ingestion/", "connectors/", "registre/", "filtres/", "scoring/",
                           "migrations/")
_FICHIERS_EXEMPTS_G6 = ("circuit_verrous.py", "circuit_garanties.py", "circuit_etats.py",
                        "sonde_circuit.py", "sentinelle.py", "sources_catalog.py",
                        "etats_sources.py", "flux.py", "cli.py", "jobs_impl.py", "jobs.py",
                        "models.py", "db.py", "referentiel_communes.py", "bascule_flux.py",
                        "bascule_gardes.py", "manifeste.py", "runs.py")

#: lecteurs CONNUS et ASSUMÉS hors du champ `fonction` du registre — chaque entrée dit
#: pourquoi (déclaration lisible, même doctrine que ACTIONS_PROPOSEES pour les orphelines).
#: Vide au départ : le verrou G6 dit ce qui manque, et chaque ajout ici est un arbitrage écrit.
LECTEURS_ASSUMES_G6: dict[str, str] = {}


from functools import lru_cache


@lru_cache(maxsize=1)
def _lecteurs_du_code_cache() -> dict[str, frozenset[str]]:
    return {t: frozenset(f) for t, f in _lecteurs_du_code_scan().items()}


def lecteurs_du_code() -> dict[str, set[str]]:
    """table de réservoir → fichiers qui la citent (scan statique, mis en cache : le code ne
    change pas pendant la vie du processus)."""
    return {t: set(f) for t, f in _lecteurs_du_code_cache().items()}


def lecteurs_par_slug() -> dict[str, list[str]]:
    """slug de réservoir → fichiers de src/labuse qui lisent une de ses tables (la page de
    détail d'une source affiche SES lecteurs — le sens source → app, calculé)."""
    from .registre.tables import reservoirs_de
    out: dict[str, set[str]] = {}
    for table, fichiers in lecteurs_du_code().items():
        for s in reservoirs_de(table):
            out.setdefault(s, set()).update(fichiers)
    return {s: sorted(f) for s, f in out.items()}


def _lecteurs_du_code_scan() -> dict[str, set[str]]:
    """table de réservoir → fichiers de src/labuse qui la citent (FROM/JOIN/UPDATE…)."""
    from pathlib import Path

    from .circuit_verrous import tables_citees
    from .registre.tables import RESERVOIR_TABLES
    racine = Path(__file__).parent
    cibles = {t for rt in RESERVOIR_TABLES.values() for t in rt.tables if t != "spatial_layers"}
    out: dict[str, set[str]] = {t: set() for t in cibles}
    for f in racine.rglob("*.py"):
        rel = f.relative_to(racine).as_posix()
        for t in tables_citees(f.read_text(encoding="utf-8")) & cibles:
            out[t].add(rel)
    return out


def _fichiers_declares_par_slug() -> dict[str, set[str]]:
    """slug → fichiers nommés par le champ `fonction` des chiffres qui le lisent."""
    import re as _re

    from .registre.donnees import DONNEES
    out: dict[str, set[str]] = {}
    for d in DONNEES.values():
        fichiers = set(_re.findall(r"src/labuse/([\w/]+\.py)", d.fonction or ""))
        for slug in d.reservoirs:
            out.setdefault(slug, set()).update(fichiers)
    return out


def lecteurs_non_declares() -> list[str]:
    """L'INDEX de la dette fine : fichiers qui lisent une table de réservoir sans être le
    `fonction` d'un chiffre de ce réservoir (ni écrivain/machinerie/assumé). AFFICHÉ sur la
    page de détail de chaque source (les deux sens, calculés) — le raccord fichier par
    fichier est un mandat à part (206 lignes mesurées le 13/09/2026), PAS ce verrou."""
    from .registre.tables import reservoirs_de
    declares = _fichiers_declares_par_slug()
    pbs: list[str] = []
    for table, fichiers in sorted(lecteurs_du_code().items()):
        slugs = reservoirs_de(table)
        ok = set().union(*(declares.get(s, set()) for s in slugs)) if slugs else set()
        for f in sorted(fichiers):
            if f.startswith(_REPERTOIRES_EXEMPTS_G6) or f in _FICHIERS_EXEMPTS_G6:
                continue
            if f in ok or f in LECTEURS_ASSUMES_G6:
                continue
            pbs.append(f"{table} ({'/'.join(slugs) or '?'}) lue par {f}")
    return pbs


def analyse_g6() -> list[str]:
    """Le verrou EXACT : (a) aucune table de réservoir lue par l'app alors que son réservoir
    est MUET (zéro chiffre → provenance impossible — le trou CatNat/Taxe/RTAA d'avant lot 0) ;
    (b) aucune table lue d'un réservoir dont la source est hors du pont NOM_VERS_SLUG."""
    from .circuit_etats import NOM_VERS_SLUG
    from .registre.donnees import DONNEES
    from .registre.tables import reservoirs_de
    slugs_avec_chiffre = {s for d in DONNEES.values() for s in d.reservoirs}
    slugs_pont = set(NOM_VERS_SLUG.values())
    pbs: list[str] = []
    for table, fichiers in sorted(lecteurs_du_code().items()):
        slugs = reservoirs_de(table)
        lecteurs_app = [f for f in sorted(fichiers)
                        if not f.startswith(_REPERTOIRES_EXEMPTS_G6)
                        and f not in _FICHIERS_EXEMPTS_G6]
        if not lecteurs_app:
            continue
        if not slugs:
            pbs.append(f"{table} lue par {lecteurs_app[0]} — table de réservoir sans slug")
            continue
        if not any(s in slugs_avec_chiffre for s in slugs):
            pbs.append(f"{table} ({'/'.join(slugs)}) lue par {', '.join(lecteurs_app[:3])} — "
                       f"réservoir MUET (aucun chiffre au registre : provenance impossible)")
        for s in slugs:
            if s not in slugs_pont:
                pbs.append(f"{table} : slug {s} hors du pont NOM_VERS_SLUG")
    return pbs


def verrou_g6(db: Session | None = None) -> ResultatVerrou:
    phrase = ("Depuis une source je vois tout ce qu'elle alimente, depuis un endroit de l'app "
              "toutes les sources qu'il lit — et aucune table de réservoir n'est lue par l'app "
              "avec un réservoir MUET (zéro chiffre : provenance impossible).")
    pbs = analyse_g6()
    n_tables = len(lecteurs_du_code())
    dette = len(lecteurs_non_declares())
    preuve = (f"{n_tables} tables de réservoirs au crible ; {len(pbs)} lecture(s) de réservoir "
              f"muet ; dette fine (lecteurs non déclarés, affichée par source) : {dette}")
    return ResultatVerrou("G6", phrase, "casse" if pbs else "ok", preuve, pbs[:10])


# ── l'assembleur (rempli garantie par garantie, lots 1→7) ─────────────────────────────

def jouer_garanties(db: Session) -> list[ResultatVerrou]:
    """Joue les garanties implémentées, dans l'ordre. Le Résumé de la page Circuit et la CLI
    `labuse circuit verrous` les affichent avec les 16 verrous de CIRCUIT-5 (lot 8)."""
    jouees = [verrou_g1(db), verrou_g2(db), verrou_g3(db), verrou_g4(db), verrou_g5(db),
              verrou_g6(db)]
    return jouees
