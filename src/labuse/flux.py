"""FLUX-1 — le circuit de la donnée, RENDU EXÉCUTABLE (mandat FLUX-1, F1/F2).

La page « Flux » du dashboard dessine la fourmilière — Sources → Moteurs → Surfaces — coiffée du
run courant. Elle n'est JAMAIS un dessin statique qui dériverait du code : les NŒUDS et leurs ÉTATS
sont calculés depuis les métadonnées VIVANTES (`data_sources`, `source_veille`, `p_score_v2_runs`,
le registre des outils), et les LIENS depuis la matrice source→consommateurs de CONNEXIONS-1 M1,
ici rendue EXÉCUTABLE : `MATRICE` est un vrai dict interrogé au requête, plus une prose d'audit.

Doctrine (rappel FLUX-1) : trois étages (sources → run → surfaces) et un interrupteur (la bascule).
Chaque source porte son millésime ; chaque surface lit « le run courant » par le pointeur unique
`Q_A_RUN_LABEL` (`config/served_run.txt`). Entre l'injection d'un nouveau millésime et la bascule,
l'app est dans un état intermédiaire ASSUMÉ — la page le rend visible (source orange « plus récente
que le run »), elle ne le cache pas.

Lecture seule : ce module CONSTRUIT la vue, il n'écrit rien (la bascule vit dans `bascule_flux.py`).
"""
from __future__ import annotations

from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import sentinelle
from .scoring.score_v_constants import Q_A_RUN_LABEL, RUN_PRECEDENT
from .sources_catalog import WHERE_AFFICHEES, masquees_param

# ─────────────────────────── LA MATRICE (M1 rendue exécutable) ───────────────────────────
# Colonne du MILIEU : les moteurs/tables qui prennent les sources et produisent le run. Chaque
# moteur déclare (1) les MOTIFS de sources qu'il consomme (sous-chaîne insensible à la casse,
# confrontée au nom réel de `data_sources`) et (2) s'il lit LE RUN figé ou une donnée VIVANTE
# (rattachement adresse→IDU n'est pas run-scopé : BAN + cadastre, à la volée). `detail` = le
# résumé « ← … » affiché sous le nœud. Grounded sur CONNEXIONS-RAPPORT §A1 (inventaire des moteurs).
MOTEURS: list[dict] = [
    {"key": "sector_price", "label": "sector_price (valorisation €/m²)", "run": "run",
     "sources": ["dvf", "radar", "pige", "cadastre"], "detail": "← DVF · Radar · cadastre"},
    {"key": "scoring", "label": "scoring · tiers", "run": "run",
     "sources": ["dvf", "sitadel", "permis", "bodacc", "rne", "inpi", "plu", "gpu", "bd topo", "bdtopo"],
     "detail": "← DVF · permis · succession · PLU · BD TOPO"},
    {"key": "cascade", "label": "cascade · risques", "run": "run",
     "sources": ["ppr", "géorisque", "georisque", "sup", "abf", "servitude", "risque", "bruit",
                 "cinquante", "argile", "cavit", "znieff", "zonage"],
     "detail": "← PPR · SUP · ABF · Géorisques"},
    {"key": "capacite", "label": "capacité · SDP", "run": "run",
     "sources": ["plu", "gpu", "cadastre", "bd topo", "bdtopo", "bâti", "bati"],
     "detail": "← PLU · cadastre · BD TOPO"},
    {"key": "rattachement", "label": "rattachement adresse → IDU", "run": "vivant",
     "sources": ["ban", "adresse", "cadastre"], "detail": "← BAN · cadastre (vivant, hors run)"},
    {"key": "signaux", "label": "signaux (permis/vie)", "run": "run",
     "sources": ["sitadel", "permis", "dvf", "bodacc", "dpe"],
     "detail": "← permis · DVF · BODACC"},
]

# Colonne de DROITE : le registre des SURFACES (les 15 outils + écrans + exports + IA). Chaque
# surface déclare les MOTEURS qu'elle lit ; toutes lisent « le run courant » (`run`), sauf celles
# qui ne servent aucune grandeur run-scopée. Les 15 outils miroir du registre front
# (`frontend/src/components/outils/registry.ts`) — même clés, ordre du registre.
_OUTILS = [
    ("scoreur-adresse", "Étudier un bien", ["sector_price", "scoring", "cascade", "capacite", "rattachement"]),
    ("programme", "Faisabilité", ["sector_price", "capacite", "cascade"]),
    ("taxe-amenagement", "Taxe d'aménagement", ["capacite"]),
    ("risques", "Pièges et risques", ["cascade"]),
    ("plu", "PLU", ["cascade", "capacite"]),
    ("comparer", "Comparer des parcelles", ["scoring", "sector_price"]),
    ("assemblage", "Assemblage", ["capacite", "sector_price"]),
    ("patrimoine", "Scan patrimoine", ["scoring", "signaux"]),
    ("courriers", "Courrier propriétaire", ["scoring"]),
    ("prospection-solaire", "Prospection solaire", ["capacite"]),
    ("communes", "Communes", ["sector_price", "scoring"]),
    ("permis", "Permis", ["signaux"]),
    ("renouvellement", "Densifier l'existant", ["scoring", "capacite"]),
    ("etude-zone", "Étude de zone", ["cascade", "capacite"]),
    ("temps", "Remonter le temps", []),
]
SURFACES: list[dict] = (
    [{"key": k, "label": lbl, "groupe": "Outils", "run": "run" if mots else "vivant", "moteurs": mots}
     for (k, lbl, mots) in _OUTILS]
    + [
        {"key": "fiche", "label": "Fiche parcelle", "groupe": "Écrans", "run": "run",
         "moteurs": ["sector_price", "scoring", "cascade", "capacite"]},
        {"key": "radar", "label": "Radar", "groupe": "Écrans", "run": "run", "moteurs": ["sector_price"]},
        {"key": "projets", "label": "Projets", "groupe": "Écrans", "run": "run", "moteurs": ["scoring"]},
        {"key": "carte", "label": "Carte · couches", "groupe": "Écrans", "run": "run",
         "moteurs": ["scoring", "cascade"]},
        {"key": "exports", "label": "Exports experts (5)", "groupe": "Exports · IA", "run": "run",
         "moteurs": ["sector_price", "scoring", "cascade", "capacite"]},
        {"key": "copilote", "label": "Copilote", "groupe": "Exports · IA", "run": "run",
         "moteurs": ["scoring", "sector_price", "cascade"]},
    ]
)

#: méthodes de veille qui constituent une SURVEILLANCE réelle (sonde amont), par opposition au
#: rappel manuel et au non-surveillé. Aligné sur `sentinelle.nature()`.
_METHODES_SONDEES = frozenset({"api", "page", "entete", "temoin"})


def _moteurs_pour_source(nom: str) -> list[str]:
    """Les moteurs (clés) qu'une source alimente, par confrontation de son NOM aux motifs de `MOTEURS`.
    Une source qui ne matche aucun moteur reste affichée mais non câblée (arête absente — honnête)."""
    bas = (nom or "").lower()
    return [m["key"] for m in MOTEURS if any(p in bas for p in m["sources"])]


def _couleur_source(veille: dict | None, plus_recente_que_run: bool) -> tuple[str, str]:
    """État (dot) d'un nœud source + libellé court. vert=à jour · orange=version amont / plus récente
    que le run · rouge=sonde en échec répété · gris=non surveillée ou manuelle."""
    if veille is None or (veille.get("methode") not in _METHODES_SONDEES) or not veille.get("actif", True):
        return "off", "non surveillée"
    statut = veille.get("dernier_statut")
    if statut in ("injoignable", "illisible") and (veille.get("echecs_consecutifs") or 0) >= 3:
        return "err", f"sonde en échec ({statut})"
    if statut == "nouvelle_version":
        return "warn", "nouvelle version dispo"
    if plus_recente_que_run:
        return "warn", "plus récente que le run"
    return "ok", "à jour"


def _run_courant(db: Session) -> dict:
    """Le run courant : label servi (pointeur unique), date de calcul, n parcelles, et la liste des
    sources+millésimes qu'il a ENREGISTRÉE à son lancement (F2.2 — clé `source_millesimes` de params).
    `enregistre_sources=False` si le run est antérieur à FLUX-1 (aucune reconstruction inventée)."""
    row = db.execute(text(
        "SELECT run_id, computed_at, n_parcelles, params FROM p_score_v2_runs WHERE run_id = :r"),
        {"r": Q_A_RUN_LABEL}).mappings().first()
    params = (row["params"] if row else None) or {}
    millesimes = params.get("source_millesimes")
    return {
        "label": Q_A_RUN_LABEL,
        "precedent": RUN_PRECEDENT,
        "calcule_le": row["computed_at"].isoformat() if row and row["computed_at"] else None,
        "n_parcelles": (row["n_parcelles"] if row else None),
        "enregistre_sources": millesimes is not None,
        "source_millesimes": millesimes or [],
    }


def construire_flux(db: Session) -> dict:
    """Construit TOUTE la page Flux (fourmilière + bandeau + run) depuis les métadonnées vivantes.
    Lecture seule. Le bloc Radar (F3) et la garde de cohérence (F4) sont ajoutés par leurs modules."""
    run = _run_courant(db)
    # ── run.source_millesimes → mapping {source_id: millésime enregistré} pour l'état intermédiaire ──
    run_millesimes = {int(m["source_id"]): m.get("millesime")
                      for m in run["source_millesimes"] if m.get("source_id") is not None}

    # ── SOURCES : le catalogue affiché (même filtre que la vitrine) + la veille de chacune ──
    src_rows = db.execute(text(
        f"SELECT d.id, d.name, d.provider, d.category, d.source_millesime, d.last_sync_at, "
        f"       v.methode, v.dernier_statut, v.dernier_vu, v.dernier_message, v.echecs_consecutifs, "
        f"       v.actif, v.injection_lancee_at "
        f"FROM data_sources d LEFT JOIN source_veille v ON v.source_id = d.id "
        f"WHERE {WHERE_AFFICHEES} ORDER BY COALESCE(d.provider, 'zzz'), d.name"),
        {"masquees": masquees_param()}).mappings().all()

    sources: list[dict] = []
    edges_source: dict[int, list[str]] = {}
    n_nouvelle, n_plus_recente, plus_recentes = 0, 0, []
    for r in src_rows:
        veille = {"methode": r["methode"], "dernier_statut": r["dernier_statut"],
                  "echecs_consecutifs": r["echecs_consecutifs"], "actif": r["actif"]} if r["methode"] else None
        # « plus récente que le run » : la veille voit un millésime amont postérieur à celui que le
        # run a ENREGISTRÉ pour cette source (état intermédiaire assumé). Sans enregistrement (run
        # ancien) on retombe sur le seul signal veille (nouvelle_version) — jamais un faux positif.
        run_mille = run_millesimes.get(r["id"])
        plus_recente = bool(run_mille and r["source_millesime"] and r["source_millesime"] != run_mille)
        dot, etat = _couleur_source(veille, plus_recente)
        if r["dernier_statut"] == "nouvelle_version":
            n_nouvelle += 1
        if dot == "warn":
            n_plus_recente += 1
            plus_recentes.append({"id": r["id"], "name": r["name"], "millesime": r["source_millesime"],
                                  "amont": r["dernier_vu"]})
        moteurs = _moteurs_pour_source(r["name"])
        edges_source[r["id"]] = moteurs
        sources.append({
            "id": r["id"], "name": r["name"], "fournisseur": r["provider"], "categorie": r["category"],
            "millesime": r["source_millesime"], "amont_vu": r["dernier_vu"],
            "ingere_le": r["last_sync_at"].isoformat() if r["last_sync_at"] else None,
            "dot": dot, "etat": etat, "nature": sentinelle.nature(r["methode"]),
            "moteurs": moteurs, "message": r["dernier_message"],
            "injectable": bool(_injectable(r["name"])),
            "injection_lancee_at": r["injection_lancee_at"].isoformat() if r["injection_lancee_at"] else None,
        })

    # ── comptages surveillance (64 · N surveillées) ──
    total_sources = db.execute(text("SELECT count(*) FROM data_sources")).scalar() or 0
    surveillees = db.execute(text(
        "SELECT count(*) FROM source_veille WHERE methode = ANY(:m) AND COALESCE(actif, true)"),
        {"m": list(_METHODES_SONDEES)}).scalar() or 0

    # ── MOTEURS : état = orange si une source amont est plus récente que le run, sinon vert ──
    src_par_moteur: dict[str, list[int]] = {m["key"]: [] for m in MOTEURS}
    for sid, mots in edges_source.items():
        for mk in mots:
            src_par_moteur[mk].append(sid)
    warn_sids = {s["id"] for s in sources if s["dot"] == "warn"}
    moteurs_out = []
    for m in MOTEURS:
        alimentee_warn = any(sid in warn_sids for sid in src_par_moteur[m["key"]])
        moteurs_out.append({
            "key": m["key"], "label": m["label"], "detail": m["detail"],
            "run": (run["label"] if m["run"] == "run" else "vivant"),
            "dot": "warn" if (m["run"] == "run" and alimentee_warn) else "ok",
            "sources": src_par_moteur[m["key"]],
        })

    surfaces_out = [{"key": s["key"], "label": s["label"], "groupe": s["groupe"],
                     "run": (run["label"] if s["run"] == "run" else "vivant"),
                     "moteurs": s["moteurs"], "dot": "ok"} for s in SURFACES]

    return {
        "run": run,
        "sources": sources,
        "moteurs": moteurs_out,
        "surfaces": surfaces_out,
        "comptes": {"total": total_sources, "surveillees": surveillees,
                    "nouvelle_version": n_nouvelle, "plus_recentes_que_run": n_plus_recente,
                    "n_surfaces": len(surfaces_out)},
        "plus_recentes": plus_recentes,
        "genere_le": datetime.now(timezone.utc).isoformat(),
    }


def _injectable(nom: str) -> bool:
    """Une source a-t-elle une commande d'ingestion mappée (bouton « Injecter » de X6) ?"""
    from .api.dashboard import _relance_pour
    try:
        return bool(_relance_pour(nom))
    except Exception:  # noqa: BLE001 — l'absence de mapping n'est jamais une erreur
        return False


def snapshot_source_millesimes(db: Session) -> list[dict]:
    """F2.2 — la PHOTO des sources + millésimes au moment où un run est lancé, à ENREGISTRER dans
    `p_score_v2_runs.params['source_millesimes']`. Sans ça, on ne peut pas savoir sur quoi un run a
    été calculé (ni afficher « plus récente que le run »). Lecture seule ; ne renvoie que les sources
    affichées porteuses d'un millésime amont."""
    rows = db.execute(text(
        f"SELECT id, name, provider, source_millesime, source_horizon_at FROM data_sources "
        f"WHERE {WHERE_AFFICHEES} AND source_millesime IS NOT NULL ORDER BY name"),
        {"masquees": masquees_param()}).mappings().all()
    return [{"source_id": r["id"], "name": r["name"], "fournisseur": r["provider"],
             "millesime": r["source_millesime"],
             "horizon": r["source_horizon_at"].isoformat() if r["source_horizon_at"] else None}
            for r in rows]
