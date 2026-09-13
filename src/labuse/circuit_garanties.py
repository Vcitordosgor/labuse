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


# ── l'assembleur (rempli garantie par garantie, lots 1→7) ─────────────────────────────

def jouer_garanties(db: Session) -> list[ResultatVerrou]:
    """Joue les garanties implémentées, dans l'ordre. Le Résumé de la page Circuit et la CLI
    `labuse circuit verrous` les affichent avec les 16 verrous de CIRCUIT-5 (lot 8)."""
    jouees = [verrou_g1(db), verrou_g2(db)]
    return jouees
