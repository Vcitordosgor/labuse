"""SECTEUR-1 (S3) + SECTEUR-2 (T2) — outil « Veille promoteurs » : ce que les promoteurs / bailleurs /
SEM CONSTRUISENT (leurs OPÉRATIONS), pas leur patrimoine.

DIAGNOSTIC (rendu au compte-rendu) : l'ingestion Sitadel porte le demandeur (`permits_sdes.py` :
DENOM_DEM / SIREN_DEM → `raw.petitioner_*`), mais l'OPEN SDES ne le peuple que ~0,5 % (PM anonymisées).
Le linkage FIABLE = le PROPRIÉTAIRE FONCIER personne morale de la parcelle du permis
(`parcelle_personne_morale` via idu) : dénomination + SIREN + groupe MAJIC — MÊME SIREN que les
acquisitions de Scan patrimoine (les deux outils se RENVOIENT, ne se dupliquent pas).

SECTEUR-2 (T2) — une OPÉRATION = un groupe de permis Sitadel sur des parcelles CONTIGUËS, du MÊME
propriétaire moral, déposés sur une MÊME PÉRIODE (règle de regroupement en constantes ci-dessous). On
montre l'opération (un point sur la carte, promoteur, commune, logements, dates, état), pas le permis nu.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

router = APIRouter(prefix="/outils/veille-promoteurs", tags=["veille-promoteurs"])

# groupe MAJIC → catégorie « promoteur / bailleur / SEM » (diagnostic S3 : les labels de la base).
CATEGORIES = {
    "promoteur": {"groupes": [0], "label": "Promoteur / société privée"},
    "bailleur": {"groupes": [5], "label": "Bailleur social (Office HLM)"},
    "sem": {"groupes": [6], "label": "Société d'économie mixte (SEM)"},
}
_GROUPE_CAT = {0: "promoteur", 5: "bailleur", 6: "sem"}
_TOUS_GROUPES = [0, 5, 6]

# ── SECTEUR-2 (T2) — RÈGLE DE REGROUPEMENT EN OPÉRATIONS (en constantes, documentée) ──────────────
# Deux permis appartiennent à la MÊME opération s'ils partagent le MÊME propriétaire moral (SIREN) ET
# que leurs parcelles sont CONTIGUËS ET qu'ils sont déposés sur une MÊME PÉRIODE.
OP_CONTIG_M = 250       # « contiguës » : centroïdes des permis à ≤ 250 m (proxy d'un même îlot d'opération)
OP_PERIODE_MOIS = 24    # « même période » : dépôts dans une fenêtre glissante de 24 mois
PLAFOND = 200


def get_db():
    from .app import get_db as _g
    yield from _g()


class _UF:
    """Union-find minimal pour agréger les permis d'un même SIREN en opérations (composantes)."""
    def __init__(self, n: int):
        self.p = list(range(n))

    def find(self, a: int) -> int:
        while self.p[a] != a:
            self.p[a] = self.p[self.p[a]]
            a = self.p[a]
        return a

    def union(self, a: int, b: int) -> None:
        ra, rb = self.find(a), self.find(b)
        if ra != rb:
            self.p[ra] = rb


def _mois(d1, d2) -> float:
    return abs((d1.year - d2.year) * 12 + (d1.month - d2.month)) if d1 and d2 else 1e9


def _operations(db: Session, groupes: list[int], commune: str | None, depuis: str | None) -> list[dict]:
    """Construit les OPÉRATIONS : permis PM (≥ 1 logement) groupés par SIREN, puis agrégés en composantes
    contiguïté (≤ OP_CONTIG_M) × période (≤ OP_PERIODE_MOIS). Un point (centroïde), promoteur, commune,
    logements (somme), dates (min→max), état (le plus récent). Nommée par une annonce neuve du Radar si
    l'une de ses parcelles en porte une, sinon libellé factuel."""
    where = ["(s.raw->>'nb_lgt') ~ '^[0-9]+$'", "(s.raw->>'nb_lgt')::int >= 1", "pm.groupe = ANY(:groupes)",
             "s.geom IS NOT NULL"]
    params: dict = {"groupes": groupes}
    if commune:
        where.append("s.commune = :commune"); params["commune"] = commune
    if depuis:
        where.append("s.date_depot >= :depuis"); params["depuis"] = depuis
    w = " AND ".join(where)
    # un rang par permis (le propriétaire moral majoritaire de ses parcelles), avec centroïde.
    rows = db.execute(text(
        f"SELECT DISTINCT ON (s.id) s.id, s.permit_id, s.commune, s.date_depot, "
        f"  (s.raw->>'nb_lgt')::int AS nb_lgt, s.raw->>'etat' AS etat, "
        f"  ST_X(ST_Centroid(s.geom)) AS lon, ST_Y(ST_Centroid(s.geom)) AS lat, "
        f"  j.idu, pm.denomination, pm.siren, pm.groupe "
        f"FROM sitadel_permits s "
        f"JOIN LATERAL jsonb_array_elements_text(s.idu_codes) j(idu) ON true "
        f"JOIN parcelle_personne_morale pm ON pm.idu = j.idu "
        f"WHERE {w} ORDER BY s.id, pm.groupe"), params).mappings().all()

    # regroupement par SIREN → union-find sur (contiguïté × période).
    par_siren: dict[str, list[dict]] = {}
    for r in rows:
        par_siren.setdefault(r["siren"], []).append(dict(r))

    operations: list[dict] = []
    for siren, permis in par_siren.items():
        uf = _UF(len(permis))
        for i in range(len(permis)):
            for jx in range(i + 1, len(permis)):
                a, b = permis[i], permis[jx]
                if a["lon"] is None or b["lon"] is None:
                    continue
                # distance métrique approchée (deg → m à la latitude de La Réunion, ~-21°)
                import math
                dlat = (a["lat"] - b["lat"]) * 111_320
                dlon = (a["lon"] - b["lon"]) * 111_320 * math.cos(math.radians(a["lat"]))
                dist = math.hypot(dlat, dlon)
                if dist <= OP_CONTIG_M and _mois(a["date_depot"], b["date_depot"]) <= OP_PERIODE_MOIS:
                    uf.union(i, jx)
        comps: dict[int, list[dict]] = {}
        for i, p in enumerate(permis):
            comps.setdefault(uf.find(i), []).append(p)
        for membres in comps.values():
            dates = [m["date_depot"] for m in membres if m["date_depot"]]
            recent = max(membres, key=lambda m: (m["date_depot"] is not None, m["date_depot"]))
            lons = [m["lon"] for m in membres if m["lon"] is not None]
            lats = [m["lat"] for m in membres if m["lat"] is not None]
            nb = sum(int(m["nb_lgt"] or 0) for m in membres)
            annee = max(dates).year if dates else None
            commune_op = recent["commune"]
            idus = sorted({m["idu"] for m in membres})
            operations.append({
                "siren": siren, "denomination": membres[0]["denomination"],
                "categorie": _GROUPE_CAT.get(membres[0]["groupe"], "promoteur"),
                "commune": commune_op, "nb_logements": nb, "n_permis": len(membres),
                "date_min": min(dates).isoformat() if dates else None,
                "date_max": max(dates).isoformat() if dates else None,
                "annee": annee, "etat": recent["etat"],
                "lon": round(sum(lons) / len(lons), 6) if lons else None,
                "lat": round(sum(lats) / len(lats), 6) if lats else None,
                "idus": idus,
                "libelle": f"{nb} logement{'s' if nb > 1 else ''} · {commune_op}" + (f" · {annee}" if annee else ""),
            })
    # nommage par une annonce NEUVE du Radar (copropriété rattachée à une parcelle de l'opération).
    tous_idus = {i for op in operations for i in op["idus"]}
    radar_par_idu: dict[str, int] = {}
    if tous_idus:
        for r in db.execute(text(
            "SELECT idu, bien_id FROM pige_biens WHERE est_copro = true AND a_qualifier = false "
            "AND statut IN ('active','en_vente_longue') AND idu = ANY(:idus)"),
            {"idus": list(tous_idus)}).mappings():
            radar_par_idu[r["idu"]] = r["bien_id"]
    for op in operations:
        cite = next((radar_par_idu[i] for i in op["idus"] if i in radar_par_idu), None)
        op["radar_bien_id"] = cite
        op["radar_cite"] = cite is not None
    # PROMO-1 (P4) — attache le PROGRAMME publié rattaché (par les coordonnées stables SIREN + commune +
    # année). On ne sert que des FAITS + le LIEN (nom du programme, URL) — jamais un texte/visuel.
    prog_par_op: dict[tuple, dict] = {}
    for r in db.execute(text(
        "SELECT nom, url, promoteur_nom, op_siren, op_commune, op_annee FROM programmes "
        "WHERE rattachement_mode IS NOT NULL")).mappings():
        prog_par_op[(r["op_siren"], r["op_commune"], r["op_annee"])] = dict(r)
    for op in operations:
        prog = prog_par_op.get((op["siren"], op["commune"], op["annee"]))
        op["programme"] = ({"nom": prog["nom"], "url": prog["url"], "promoteur_nom": prog["promoteur_nom"]}
                           if prog else None)
    return operations


@router.get("")
def veille_promoteurs(commune: str | None = Query(None), categorie: str | None = Query(None),
                      depuis: str | None = Query(None, description="AAAA-MM-JJ — période de dépôt"),
                      siren: str | None = Query(None, description="ADMIN-1 AD3 — restreindre à UN propriétaire"),
                      limit: int = Query(100), db: Session = Depends(get_db)) -> dict:
    """Les OPÉRATIONS (groupes de permis) des promoteurs / bailleurs / SEM. Filtrable commune / catégorie
    / période. ADMIN-1 (AD3) : `siren` restreint à UN propriétaire — le Scan patrimoine (mode « ce qu'ils
    construisent » d'un propriétaire choisi) ne montre alors QUE ses opérations, jamais toute l'île. Même
    moteur (regroupement de permis), aucun recalcul. Chaque opération : un point, promoteur, commune,
    logements, dates, état. Comptes SQL."""
    groupes = CATEGORIES.get(categorie, {}).get("groupes", _TOUS_GROUPES) if categorie else _TOUS_GROUPES
    ops = _operations(db, groupes, commune, depuis)
    if siren:
        s9 = siren.strip()[:9]
        ops = [o for o in ops if (o.get("siren") or "")[:9] == s9]
    ops.sort(key=lambda o: (o["date_max"] is not None, o["date_max"] or ""), reverse=True)
    n_total = len(ops)
    lim = min(max(limit, 1), PLAFOND)
    tronquee = n_total > lim
    millesime = db.execute(text("SELECT max(date_depot) FROM sitadel_permits")).scalar()
    return {
        "n_total": n_total, "n_servi": min(n_total, lim), "tronquee": tronquee, "plafond": PLAFOND,
        "n_logements_total": sum(o["nb_logements"] for o in ops),
        "categories": [{"cle": k, "label": v["label"]} for k, v in CATEGORIES.items()],
        "millesime": millesime.isoformat() if millesime else None,
        "regle": {"contiguite_m": OP_CONTIG_M, "periode_mois": OP_PERIODE_MOIS,
                  "phrase": f"une opération = permis d'un même propriétaire moral, parcelles contiguës "
                            f"(≤ {OP_CONTIG_M} m) et déposés sur ≤ {OP_PERIODE_MOIS} mois"},
        "operations": ops[:lim],
        "note": "Le demandeur = propriétaire foncier personne morale de la parcelle (Scan patrimoine, même "
                "SIREN). L'open Sitadel n'identifie le pétitionnaire que ~0,5 % du temps.",
    }


@router.get("/{siren}/frise")
def promoteur_frise(siren: str, db: Session = Depends(get_db)) -> dict:
    """La FRISE par année d'un promoteur : ses opérations et leurs logements, année par année. Renvoie aussi
    le lien vers son Scan patrimoine (les deux outils se renvoient, ne se dupliquent pas)."""
    ops = [o for o in _operations(db, _TOUS_GROUPES, None, None) if o["siren"] == siren]
    denom = db.execute(text(
        "SELECT denomination FROM parcelle_personne_morale WHERE siren = :s AND denomination IS NOT NULL LIMIT 1"),
        {"s": siren}).scalar()
    par_annee: dict[int, dict] = {}
    for o in ops:
        if o["annee"] is None:
            continue
        a = par_annee.setdefault(o["annee"], {"annee": o["annee"], "n_operations": 0, "n_logements": 0})
        a["n_operations"] += 1
        a["n_logements"] += o["nb_logements"]
    frise = sorted(par_annee.values(), key=lambda a: a["annee"])
    n_patrimoine = db.execute(text("SELECT count(*) FROM parcelle_personne_morale WHERE siren = :s"),
                              {"s": siren}).scalar() or 0
    # PROMO-1 (P4) — les opérations avec le NOM de programme rattaché (la frise porte les noms) + les
    # programmes NON rattachés (« publiés sur leur site »). Faits + lien seulement, jamais un visuel.
    ops_nommees = [{"annee": o["annee"], "commune": o["commune"], "nb_logements": o["nb_logements"],
                    "libelle": o["libelle"], "programme": o.get("programme")}
                   for o in sorted(ops, key=lambda o: (o["annee"] or 0), reverse=True)]
    non_rattaches = [dict(r) for r in db.execute(text(
        "SELECT id, nom, commune, url, annee FROM programmes "
        "WHERE (promoteur_siren = :s OR (:s IS NULL AND promoteur_nom = :n)) AND rattachement_mode IS NULL "
        "ORDER BY commune NULLS LAST, nom"), {"s": siren, "n": denom}).mappings()]
    return {
        "siren": siren, "denomination": denom,
        "n_operations": len(ops), "n_logements": sum(o["nb_logements"] for o in ops),
        "frise": frise, "operations": ops_nommees,
        "programmes_publies": non_rattaches,   # « publiés sur leur site » (non rattachés à une opération)
        # renvoi vers Scan patrimoine (pas de duplication : le détail parcellaire vit là-bas).
        "scan_patrimoine": {"n_parcelles": int(n_patrimoine),
                            "endpoint": f"/outils/veille-promoteurs/{siren}/acquisitions"},
        "note": "Ce que ce promoteur CONSTRUIT (permis groupés en opérations). Son patrimoine foncier détenu "
                "est dans Scan patrimoine (même SIREN) — les deux se renvoient, ne se dupliquent pas.",
    }


@router.get("/{siren}/acquisitions")
def promoteur_acquisitions(siren: str, db: Session = Depends(get_db)) -> dict:
    """Le patrimoine foncier détenu par le promoteur (Scan patrimoine, MÊME SIREN) : parcelles par commune.
    Comptes SQL — jamais une estimation. Renvoyé par la frise (les deux outils se renvoient)."""
    denom = db.execute(text(
        "SELECT denomination FROM parcelle_personne_morale WHERE siren = :s AND denomination IS NOT NULL LIMIT 1"),
        {"s": siren}).scalar()
    par_commune = db.execute(text(
        "SELECT p.commune, count(*) AS n FROM parcelle_personne_morale pm JOIN parcels p ON p.idu = pm.idu "
        "WHERE pm.siren = :s GROUP BY p.commune ORDER BY 2 DESC LIMIT 20"), {"s": siren}).mappings().all()
    n_total = db.execute(text("SELECT count(*) FROM parcelle_personne_morale WHERE siren = :s"), {"s": siren}).scalar() or 0
    return {
        "siren": siren, "denomination": denom, "n_parcelles": int(n_total),
        "par_commune": [{"commune": r["commune"], "n": int(r["n"])} for r in par_commune],
        "note": "Patrimoine parcellaire détenu par ce SIREN (Scan patrimoine, DGFiP PM). Constat, hors scoring.",
    }
