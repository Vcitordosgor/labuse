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
from .. import permis_classe

OP_CONTIG_M = 250       # « contiguës » : centroïdes des permis à ≤ 250 m (proxy d'un même îlot d'opération)
OP_PERIODE_MOIS = 24    # « même période » : dépôts dans une fenêtre glissante de 24 mois
# SCAN-FIX-2 (M1) — la fenêtre se compte EN JOURS, pas en mois entiers (le contre-audit relevait que le
# test ignorait le jour du mois : deux dépôts à 1 j d'écart de part et d'autre d'un changement de mois
# étaient traités à tort comme 1 mois). 24 mois = 730 jours (365,25/12 × 24).
OP_PERIODE_JOURS = round(OP_PERIODE_MOIS * 365.25 / 12)   # 730
PLAFOND = 200
NOTE_SOURCE = (
    "Attribution par le PROPRIÉTAIRE FONCIER de la parcelle (Scan patrimoine, même SIREN), pas "
                "par le pétitionnaire — l'open Sitadel n'identifie le pétitionnaire que sur une part des "
                "permis. Voir la frise d'un propriétaire pour « permis qu'elle a déposés » vs « sur son foncier »."
)


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


def _jours(d1, d2) -> float:
    """SCAN-FIX-2 (M1) — écart EN JOURS entre deux dépôts (compte le jour du mois, pas des mois entiers)."""
    return abs((d1 - d2).days) if d1 and d2 else 1e9


def _haversine_m(lat1, lon1, lat2, lon2) -> float:
    """Distance GÉODÉSIQUE (m) entre deux points — haversine, vraie distance (SCAN-FIX-1 bloquant 4 :
    remplace la conversion deg→m approchée qui faisait basculer des paires de part et d'autre du seuil)."""
    import math
    r = 6_371_000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(a))


def _permis_proprietaire(db: Session, commune: str | None, depuis: str | None) -> list[dict]:
    """SCAN-FIX-1 (bloquants 2-4) — UN rang par permis (≥ 1 logement, géolocalisé) avec son PROPRIÉTAIRE
    FONCIER DÉTERMINISTE : le SIREN qui détient le PLUS de parcelles du permis, départage `groupe` croissant
    puis `siren` croissant (deux exécutions → même résultat). L'owner est choisi INDÉPENDAMMENT de toute
    catégorie (→ les catégories forment une partition, un filtre ne change pas l'attribution). `ambigu` =
    plusieurs SIREN ex æquo au nombre de parcelles (cas à signaler). Porte aussi le pétitionnaire déclaré
    (`petitioner_siren`), le type (PC/DP…), l'état et la DAACT — pour distinguer déposé/foncier, PC/DP,
    annulé, achevé."""

    where = ["(s.raw->>'nb_lgt') ~ '^[0-9]+$'", "(s.raw->>'nb_lgt')::int >= 1", "s.geom IS NOT NULL"]
    params: dict = {}
    if commune:
        where.append("s.commune = :commune"); params["commune"] = commune
    if depuis:
        where.append(permis_classe.depot_depuis_cond_sql("s.")); params["depuis"] = depuis
    w = " AND ".join(where)
    rows = db.execute(text(f"""
        WITH perm AS (
          SELECT s.id, s.permit_id, s.commune, {permis_classe.depot_date_sql("s.")} AS date_regroupement, s.type,
                 {permis_classe.depot_jour_connu_sql("s.")} AS depot_jour_connu,
                 s.raw->>'petitioner_name' AS petitioner_name,
                 (s.raw->>'nb_lgt')::int AS nb_lgt, s.raw->>'etat' AS etat, s.raw->>'daact' AS daact,
                 NULLIF(s.raw->>'petitioner_siren', '') AS petitioner_siren,
                 ST_X(ST_Centroid(s.geom)) AS lon, ST_Y(ST_Centroid(s.geom)) AS lat, s.idu_codes
          FROM sitadel_permits s WHERE {w}
        ),
        own AS (
          SELECT p.id, pm.siren, max(pm.denomination) AS denomination, min(pm.groupe) AS groupe,
                 count(*) AS n_parc
          FROM perm p JOIN LATERAL jsonb_array_elements_text(p.idu_codes) j(idu) ON true
          JOIN parcelle_personne_morale pm ON pm.idu = j.idu AND pm.siren IS NOT NULL
          GROUP BY p.id, pm.siren
        ),
        ranked AS (
          SELECT *, row_number() OVER w AS rk, count(*) OVER (PARTITION BY id) AS n_cand,
                 max(n_parc) OVER (PARTITION BY id) AS max_parc
          FROM own WINDOW w AS (PARTITION BY id ORDER BY n_parc DESC, groupe ASC NULLS LAST, siren ASC)
        ),
        ties AS (SELECT id, count(*) FILTER (WHERE n_parc = max_parc) AS n_top FROM ranked GROUP BY id)
        SELECT perm.id, perm.permit_id, perm.commune, perm.date_regroupement, perm.type, perm.nb_lgt,
               perm.etat, perm.daact, perm.depot_jour_connu, perm.petitioner_name, perm.petitioner_siren, perm.lon, perm.lat, perm.idu_codes,
               r.siren, r.denomination, r.groupe, r.n_parc, r.n_cand, (t.n_top > 1) AS ambigu
        FROM perm JOIN ranked r ON r.id = perm.id AND r.rk = 1
        JOIN ties t ON t.id = perm.id
        ORDER BY perm.id"""), params).mappings().all()   # SCAN-FIX-2 (M2) — ordre STABLE (pas d'ex æquo d'ordre de ligne)
    return [dict(r) for r in rows]


def _operations(db: Session, groupes: list[int], commune: str | None, depuis: str | None) -> list[dict]:
    """Construit les OPÉRATIONS : permis PM (≥ 1 logement) rattachés à leur propriétaire foncier
    déterministe (`_permis_proprietaire`), gardés si le propriétaire est promoteur/bailleur/SEM (groupes
    0/5/6), groupés par SIREN puis agrégés en composantes contiguïté (≤ OP_CONTIG_M, distance GÉODÉSIQUE) ×
    période (≤ OP_PERIODE_MOIS). SCAN-FIX-1 : les logements ANNULÉS sortent du « construit ou en cours » ;
    PC et DP distingués ; un groupe n'est « achevé » que si TOUS ses permis non annulés le sont ; l'étendue
    réelle (distance/jours max du groupe) est servie ; `ambigu` remonté. La catégorie vient du propriétaire
    (partition) — `groupes` filtre APRÈS l'attribution, sans la changer."""
    from ..ingestion.permits import etat_libelle as _permis_etat_lib
    permis_tous = _permis_proprietaire(db, commune, depuis)
    # rattachement au propriétaire foncier ; ne gardent une OPÉRATION que les groupes servis (0/5/6),
    # mais l'attribution (ci-dessus) est faite AVANT ce filtre → catégories = partition, filtre neutre.
    par_siren: dict[str, list[dict]] = {}
    for r in permis_tous:
        if r["groupe"] in groupes:
            par_siren.setdefault(r["siren"], []).append(r)

    operations: list[dict] = []
    for siren, permis in par_siren.items():
        uf = _UF(len(permis))
        for i in range(len(permis)):
            for jx in range(i + 1, len(permis)):
                a, b = permis[i], permis[jx]
                if a["lon"] is None or b["lon"] is None:
                    continue
                if (_haversine_m(a["lat"], a["lon"], b["lat"], b["lon"]) <= OP_CONTIG_M
                        and _jours(a["date_regroupement"], b["date_regroupement"]) <= OP_PERIODE_JOURS):
                    uf.union(i, jx)
        comps: dict[int, list[dict]] = {}
        for i, p in enumerate(permis):
            comps.setdefault(uf.find(i), []).append(p)
        for membres in comps.values():
            # SCAN-FIX-2 (M2) — ordre TOTAL explicite des membres (plus de dépendance à l'ordre de ligne) :
            # tout « premier/plus récent » est départagé par permit_id puis id.
            membres = sorted(membres, key=lambda m: (str(m.get("permit_id") or ""), m["id"]))
            est_annule = lambda m: str(m.get("etat") or "") == "4"
            est_acheve = lambda m: bool((m.get("daact") or "").strip()) or str(m.get("etat") or "") == "6"
            est_dp = lambda m: (m.get("type") or "") == "DP"
            vivants = [m for m in membres if not est_annule(m)]          # non annulés
            annules = [m for m in membres if est_annule(m)]
            dates = [m["date_regroupement"] for m in vivants if m["date_regroupement"]] or \
                    [m["date_regroupement"] for m in membres if m["date_regroupement"]]
            # « plus récent » DÉTERMINISTE : date max, départagée par permit_id puis id (M2).
            recent = max(vivants or membres,
                         key=lambda m: (m["date_regroupement"] is not None, m["date_regroupement"],
                                        str(m.get("permit_id") or ""), m["id"]))
            lons = [m["lon"] for m in membres if m["lon"] is not None]
            lats = [m["lat"] for m in membres if m["lat"] is not None]
            # SCAN-FIX-2 (A1) — « construit ou en cours » = logements des permis NON annulés et HORS
            # déclaration préalable ; les logements de DP sont séparés (comme les annulés), plus fondus.
            vivants_hors_dp = [m for m in vivants if not est_dp(m)]
            vivants_dp = [m for m in vivants if est_dp(m)]
            nb = sum(int(m["nb_lgt"] or 0) for m in vivants_hors_dp)     # CONSTRUIT OU EN COURS (hors annulés, hors DP)
            nb_dp = sum(int(m["nb_lgt"] or 0) for m in vivants_dp)       # logements de DÉCLARATIONS PRÉALABLES
            nb_annule = sum(int(m["nb_lgt"] or 0) for m in annules)
            annee = max(dates).year if dates else None
            commune_op = recent["commune"]
            idus = sorted({i for m in membres for i in (m["idu_codes"] or [])})
            n_pc = sum(1 for m in membres if (m.get("type") or "") == "PC")
            n_dp = sum(1 for m in membres if est_dp(m))
            # ÉTAT DU GROUPE — « travaux achevés » UNIQUEMENT si TOUS les permis non annulés le sont
            # (SCAN-FIX-1 bloquant 3 : un seul achèvement ne qualifie plus tout le groupe). Sinon on dit le détail.
            n_ach = sum(1 for m in vivants if est_acheve(m))
            if not vivants:
                etat_op = "annulée"
            elif n_ach == len(vivants):
                etat_op = "travaux achevés"
            elif n_ach > 0:
                etat_op = f"{n_ach}/{len(vivants)} permis achevés — reste en cours"
            else:
                etat_op = _permis_etat_lib({"etat": recent["etat"]})
            # ÉTENDUE RÉELLE du groupe (SCAN-FIX-1 bloquant 4) : distance géodésique max entre membres,
            # durée entre dépôts extrêmes — servies pour que la définition affichée corresponde au groupe entier.
            span_m = 0.0
            pts = [(m["lat"], m["lon"]) for m in membres if m["lon"] is not None]
            for i in range(len(pts)):
                for jx in range(i + 1, len(pts)):
                    span_m = max(span_m, _haversine_m(pts[i][0], pts[i][1], pts[jx][0], pts[jx][1]))
            span_jours = (max(dates) - min(dates)).days if len(dates) >= 2 else 0
            petitionnaires = [{"nom": nom, "siren": identifiant} for nom, identifiant in dict.fromkeys(
                (m["petitioner_name"], m["petitioner_siren"]) for m in membres if m.get("petitioner_name"))]
            jour_connu = all(m.get("depot_jour_connu") for m in membres)
            operations.append({
                "petitionnaires": petitionnaires,
                "petitionnaire_nom": petitionnaires[0]["nom"] if len(petitionnaires) == 1 else None,
                "petitionnaire_siren": petitionnaires[0]["siren"] if len(petitionnaires) == 1 else None,
                "proprietaire_cadastral_nom": membres[0]["denomination"],
                "proprietaire_cadastral_siren": siren,
                "depot_jour_connu": jour_connu,
                "depot_a_confirmer": not jour_connu,
                "siren": siren, "denomination": membres[0]["denomination"],
                "categorie": _GROUPE_CAT.get(membres[0]["groupe"], "promoteur"),
                "commune": commune_op, "nb_logements": nb, "nb_logements_dp": nb_dp,
                "nb_logements_annules": nb_annule,
                "n_permis": len(membres), "n_permis_pc": n_pc, "n_permis_dp": n_dp,
                "n_permis_annules": len(annules),
                "n_sans_petitionnaire": sum(1 for m in membres if not m.get("petitioner_siren")),
                "date_min": min(dates).isoformat() if dates else None,
                "date_max": max(dates).isoformat() if dates else None,
                "annee": annee, "etat": recent["etat"],
                "annule": not vivants,                              # opération ENTIÈREMENT annulée
                "etat_libelle": etat_op,
                "span_m": round(span_m), "span_jours": span_jours,
                "ambigu": any(m.get("ambigu") for m in membres),
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
    # SCAN-FIX-1 (bloquant 6) — un nom de programme n'est attaché à une opération QUE si le rattachement
    # est SANS AMBIGUÏTÉ. La clé (société, commune, année) NE suffit PAS : plusieurs programmes peuvent la
    # partager (collision Zirondelles/Zoiseau Blanc) et plusieurs OPÉRATIONS aussi (double affectation). On
    # n'attache donc que si la clé mappe EXACTEMENT 1 programme ET EXACTEMENT 1 opération. Sinon : aucun
    # rattachement (le programme reste « publié sur leur site », listé par la frise). On garde l'id attaché
    # pour que la frise ne reliste pas un programme déjà posé sur une opération.
    from collections import defaultdict
    progs_par_cle: dict[tuple, list[dict]] = defaultdict(list)
    for r in db.execute(text(
        "SELECT id, nom, url, promoteur_nom, op_siren, op_commune, op_annee FROM programmes "
        "WHERE rattachement_mode IS NOT NULL")).mappings():
        progs_par_cle[(r["op_siren"], r["op_commune"], r["op_annee"])].append(dict(r))
    ops_par_cle: dict[tuple, list[dict]] = defaultdict(list)
    for op in operations:
        ops_par_cle[(op["siren"], op["commune"], op["annee"])].append(op)
        op["programme"] = None
    ids_attaches: set = set()
    for cle, progs in progs_par_cle.items():
        ops_cle = ops_par_cle.get(cle, [])
        if len(progs) == 1 and len(ops_cle) == 1:          # rattachement sans ambiguïté
            prog = progs[0]
            ops_cle[0]["programme"] = {"nom": prog["nom"], "url": prog["url"],
                                       "promoteur_nom": prog["promoteur_nom"]}
            ids_attaches.add(prog["id"])
        # sinon : collision (≥2 programmes) ou double affectation (≥2 opérations) → on n'attache rien
        # (le programme reste « publié sur leur site » ; la frise le reliste par son nom/URL non servi).
    # SCAN-FIX-1 (point 7) — la CATÉGORIE AFFICHÉE vient d'une SOURCE QUI LA JUSTIFIE. Les groupes DGFiP
    # 5/6 justifient « bailleur social » / « SEM ». Le groupe 0 (« personnes morales non remarquables »)
    # ne justifie PAS « promoteur » : on ne l'affiche promoteur QUE si l'activité SIRENE du SIREN est la
    # promotion immobilière (NAF 4110…) ; sinon « Société privée » (neutre), jamais « promoteur » par défaut.
    sirens = {op["siren"] for op in operations if op["siren"]}
    naf_par_siren: dict[str, str] = {}
    if sirens and db.execute(text("SELECT to_regclass('sirene_etablissements') IS NOT NULL")).scalar():
        for r in db.execute(text(
            "SELECT siren, min(naf) AS naf FROM sirene_etablissements "
            "WHERE siren = ANY(:s) AND naf IS NOT NULL GROUP BY siren"),
                {"s": list(sirens)}).mappings():
            naf_par_siren[r["siren"]] = r["naf"]
    for op in operations:
        if op["categorie"] == "bailleur":
            op["categorie_label"], op["categorie_justifiee"] = "Bailleur social (Office HLM)", True
            op["categorie_source"] = "DGFiP — groupe 5 (Office HLM)"
        elif op["categorie"] == "sem":
            op["categorie_label"], op["categorie_justifiee"] = "Société d'économie mixte (SEM)", True
            op["categorie_source"] = "DGFiP — groupe 6 (SEM)"
        else:   # groupe 0 — « promoteur » SEULEMENT si l'activité SIRENE le justifie
            naf = (naf_par_siren.get(op["siren"]) or "")
            if naf.startswith("4110"):
                op["categorie_label"], op["categorie_justifiee"] = "Promoteur", True
                op["categorie_source"] = f"SIRENE — NAF {naf} (promotion immobilière)"
            else:
                op["categorie_label"], op["categorie_justifiee"] = "Société privée", False
                op["categorie_source"] = ("groupe DGFiP 0 (personnes morales non remarquables) — "
                                          "activité ne justifiant pas « promoteur »")
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
    # SCAN-FIX-2 (M2) — tri à ordre TOTAL (date desc, puis siren/commune) : aucun ex æquo d'ordre de ligne.
    ops.sort(key=lambda o: (o["date_max"] is not None, o["date_max"] or "", o["siren"] or "", o["commune"] or ""),
             reverse=True)
    n_total = len(ops)
    lim = min(max(limit, 1), PLAFOND)
    tronquee = n_total > lim
    millesime = db.execute(text(f"SELECT max({permis_classe.depot_date_sql()}) FROM sitadel_permits s")).scalar()
    # SCAN-FIX-1 (bloquant 4, pt 7) — CARTES PAR PROMOTEUR calculées sur TOUTES les opérations (jamais sur
    # les seules 200 servies) : le front ne sous-compte plus. Agrégat déterministe trié.
    par_promoteur: dict[str, dict] = {}
    for o in ops:
        g = par_promoteur.setdefault(o["siren"] or "∅", {
            "siren": o["siren"], "denomination": o["denomination"], "categorie": o["categorie"],
            "categorie_label": o.get("categorie_label"), "categorie_justifiee": o.get("categorie_justifiee"),
            "n_operations": 0, "n_permis": 0, "nb_logements": 0, "nb_logements_dp": 0,
            "nb_logements_annules": 0, "ambigu": False})
        g["n_operations"] += 1
        g["n_permis"] += o["n_permis"]
        g["nb_logements"] += o["nb_logements"]
        g["nb_logements_dp"] += o["nb_logements_dp"]
        g["nb_logements_annules"] += o["nb_logements_annules"]
        g["ambigu"] = g["ambigu"] or o["ambigu"]
    cartes = sorted(par_promoteur.values(),
                    key=lambda c: (-c["n_operations"], -c["nb_logements"], c["siren"] or ""))
    return {
        "n_total": n_total, "n_servi": min(n_total, lim), "tronquee": tronquee, "plafond": PLAFOND,
        # SCAN-FIX-1 (bloquant 3) + SCAN-FIX-2 (A1) — « construit ou en cours » = HORS annulés ET HORS DP ;
        # les logements de DP et les annulés sont comptés À PART (plus fondus dans le total de tête).
        "n_logements_total": sum(o["nb_logements"] for o in ops),
        "n_logements_dp": sum(o["nb_logements_dp"] for o in ops),
        "n_logements_annules": sum(o["nb_logements_annules"] for o in ops),
        "n_operations_ambigues": sum(1 for o in ops if o["ambigu"]),
        "par_promoteur": cartes,     # cartes société calculées sur TOUT (pt 7), pas sur les 200 servies
        "categories": [{"cle": k, "label": v["label"]} for k, v in CATEGORIES.items()],
        "millesime": millesime.isoformat() if millesime else None,
        "regle": {"contiguite_m": OP_CONTIG_M, "periode_mois": OP_PERIODE_MOIS, "periode_jours": OP_PERIODE_JOURS,
                  "phrase": f"une opération = permis d'un même propriétaire foncier (SIREN), regroupés DE "
                            f"PROCHE EN PROCHE quand leurs parcelles sont à ≤ {OP_CONTIG_M} m (distance "
                            f"géodésique) et déposés à ≤ {OP_PERIODE_MOIS} mois ({OP_PERIODE_JOURS} jours) "
                            f"d'écart ; l'étendue réelle du groupe (distance et durée max) est affichée par opération"},
        "operations": ops[:lim],
        "note": NOTE_SOURCE,
    }


@router.get("/{siren}/frise")
def promoteur_frise(siren: str, db: Session = Depends(get_db)) -> dict:
    """La FRISE par année d'un promoteur : ses opérations et leurs logements, année par année. Renvoie aussi
    le lien vers son Scan patrimoine (les deux outils se renvoient, ne se dupliquent pas)."""
    ops = [o for o in _operations(db, _TOUS_GROUPES, None, None) if o["siren"] == siren]
    denom = db.execute(text(
        # CHASSE-FIX-3 (C3-08) — ORDER BY explicite (plusieurs parcelles par SIREN → nom déterministe).
        "SELECT denomination FROM parcelle_personne_morale WHERE siren = :s AND denomination IS NOT NULL "
        "ORDER BY denomination ASC LIMIT 1"),
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
    # SCAN-FIX-1 (bloquant 6) — « publiés sur leur site » = TOUS les programmes du promoteur qui ne sont
    # PAS effectivement attachés à une opération servie (donc aussi ceux dont le rattachement était ambigu
    # — collision de clé ou double affectation — et qu'on a refusé d'attacher ci-dessus). On reconnaît les
    # attachés par le (nom, url) réellement posé sur une opération.
    attaches_noms = {(o["programme"]["nom"], o["programme"]["url"]) for o in ops if o.get("programme")}
    non_rattaches = [dict(r) for r in db.execute(text(
        "SELECT id, nom, commune, url, annee FROM programmes "
        "WHERE (promoteur_siren = :s OR (:s IS NULL AND promoteur_nom = :n)) "
        "ORDER BY commune NULLS LAST, nom"), {"s": siren, "n": denom}).mappings()
        if (r["nom"], r["url"]) not in attaches_noms]
    # RETOURS-13 R29 — LE CHIFFRE DIT CE QU'IL COMPTE (doute Vic « CBO a que 20 opérations
    # depuis 2013 ?? ») : les « opérations » ci-dessus = permis ≥ 1 logement sur les parcelles
    # que la société POSSÈDE ENCORE (un promoteur revend après livraison → les opérations
    # livrées SORTENT de ce compte ; les SCI/SNC d'opération n'y sont pas). En COMPLÉMENT :
    # l'activité de PÉTITIONNAIRE (Sitadel 2013+, toutes destinations) au nom de la société,
    # et celle de ses filiales IDENTIFIÉES par le lien de gérance INPI (pm_dirigeants.
    # gerant_siren — jamais un rapprochement par adresse de siège : mesuré NON fiable,
    # « La Mare » = un quartier entier). Jamais un total gonflé sans méthode.
    petit = db.execute(text(
        "SELECT count(*) AS n, sum(NULLIF(raw->>'nb_lgt','')::int) AS lgt "
        "FROM sitadel_permits WHERE raw->>'petitioner_siren' = :s "
        f"  AND {permis_classe.evenement_date_sql('')} >= DATE '2013-01-01'"), {"s": siren}).mappings().first()   # CHASSE-FIX-1 (C40) : le « (2013+) » annoncé est appliqué
    filles = db.execute(text(
        "SELECT d.siren, count(s.id) AS n, sum(NULLIF(s.raw->>'nb_lgt','')::int) AS lgt, "
        "       max(s.raw->>'petitioner_name') AS nom "
        "FROM pm_dirigeants d "
        "JOIN sitadel_permits s ON s.raw->>'petitioner_siren' = d.siren "
        "WHERE d.gerant_siren = :s AND COALESCE(d.actif, true) "
        "GROUP BY d.siren HAVING count(s.id) > 0"), {"s": siren}).mappings().all()
    # SCAN-FIX-1 (bloquant 2) — DEUX listes SÉPARÉES et NOMMÉES : « permis qu'elle a déposés »
    # (pétitionnaire identifié) vs « permis sur son foncier » (propriétaire du terrain), avec la PART de
    # permis fonciers dont le pétitionnaire est inconnu.
    n_permis_foncier = sum(o["n_permis"] for o in ops)
    n_sans_pet = sum(o["n_sans_petitionnaire"] for o in ops)
    return {
        "siren": siren, "denomination": denom,
        "n_operations": len(ops), "n_logements": sum(o["nb_logements"] for o in ops),
        # R29 — périmètre du compte (source unique de la phrase affichée).
        "perimetre_note": ("permis ≥ 1 logement sur les parcelles que la société possède encore "
                           "(fichier DGFiP) — les opérations livrées puis revendues sortent de ce compte"),
        "sur_son_foncier": {
            "n_operations": len(ops), "n_permis": n_permis_foncier,
            "n_logements": sum(o["nb_logements"] for o in ops),
            "n_logements_dp": sum(o["nb_logements_dp"] for o in ops),   # SCAN-FIX-2 (A1) — DP à part
            "n_logements_annules": sum(o["nb_logements_annules"] for o in ops),
            "n_permis_sans_petitionnaire": n_sans_pet,
            "part_petitionnaire_inconnu": round(100 * n_sans_pet / n_permis_foncier) if n_permis_foncier else None,
            "note": "permis sur des parcelles dont la société est PROPRIÉTAIRE foncier (attribution par le "
                    "foncier, pas par le pétitionnaire)"},
        "deposes_petitionnaire": {
            "n_permis": int(petit["n"] or 0), "n_logements": int(petit["lgt"] or 0),
            "note": "permis DÉPOSÉS au nom de la société (pétitionnaire identifié ; Sitadel 2013+, toutes destinations)"},
        "petitionnaire": {"n_permis": int(petit["n"] or 0),
                          "n_logements": int(petit["lgt"] or 0),
                          "note": "permis Sitadel au nom de la société (2013+), toutes destinations"},
        "filiales_identifiees": [{"siren": f["siren"], "nom": f["nom"], "n_permis": int(f["n"]),
                                  "n_logements": int(f["lgt"] or 0)} for f in filles],
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
        # CHASSE-FIX-3 (C3-08) — ORDER BY explicite (plusieurs parcelles par SIREN → nom déterministe).
        "SELECT denomination FROM parcelle_personne_morale WHERE siren = :s AND denomination IS NOT NULL "
        "ORDER BY denomination ASC LIMIT 1"),
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
