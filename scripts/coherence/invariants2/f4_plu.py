"""F4 — LE PLU : règles d'invariant GÉNÉRÉES depuis les calibrages de zone (lecture seule).

Idée : chaque zone calibrée (`config/plu_destinations/974??_*.yaml`, parcourue par
`labuse.plu.destinations.iter_regles_calibrees`) porte des feuilles chiffrées sourcées
(article / page_pdf / citation / statut ∈ valide|propose|absent). On en GÉNÈRE des règles
vraies par construction, sur 5 axes :

  A. Bornes du règlement — chaque feuille VALIDÉE numérique (hauteur, CES, recul, pleine
     terre %, stationnement, mixité) tombe dans une plage plausible de règlement. Une valeur
     hors plage = erreur de calibrage / transcription.
  B. Citation + page réelle — chaque feuille VALIDÉE porte une citation non vide ET un
     `page_pdf` qui EXISTE dans `plu_reglement_extrait` pour ce (insee[, zone]) : la page
     citée est une vraie page du règlement extrait.
  C. Renvoi — une zone `renvoi` (sans `regles` propre) pointe vers une zone qui EXISTE ET
     est calibrée dans la même commune (sinon le moteur inventerait un repli).
  D. Aucun `propose` ne sert un chiffre — aucune parcelle à SDP servie > 0 n'a une zone dont
     une feuille SDP-déterminante est `propose` (la garde moteur `_val` doit le tenir, on le
     vérifie PAR LA DONNÉE sur parcel_zone_plu × parcel_residuel).
  E. Couverture GPU — chaque famille de zone portant des parcelles servies résout soit à des
     `regles`, soit à une raison écrite (habitat interdit / règle non validée / non calibré).

Lecture seule stricte (noyau.connexion). Les règles A/C sont des callables qui scannent le
YAML en mémoire ; B/D/E croisent le YAML et la base servie.
"""
from __future__ import annotations

import sys
import pathlib

_ICI = pathlib.Path(__file__).resolve()
sys.path.insert(0, str(_ICI.parents[2]))  # .../scripts

from coherence.invariants2.noyau import (  # noqa: E402
    RuleSpec, Ecartee, run_specs, bilan, connexion, table_existe,
)

# ── accès aux calibrages PLU via le module de l'app (pas de relecture YAML maison) ───────────
sys.path.insert(0, str(_ICI.parents[3] / "src"))
from labuse.plu import destinations as D  # noqa: E402


# ── bornes de règlement plausibles (plancher inclusif, plafond inclusif) ─────────────────────
# Calibrées sur le survol réel des 24 communes : CES 0,2 % légitime (20 m²/ha, Uep), faîtage
# jusqu'à 34 m (U1pso St-Paul). On vise des bornes LARGES : seule une transcription aberrante
# (virgule décalée, unité, signe) doit sortir.
_BORNES = {
    ("hauteur", "faitage", "m"): (0.0, 60.0, "faîtage (m)"),
    ("hauteur", "egout", "m"): (0.0, 50.0, "égout/acrotère (m)"),
    ("hauteur", "niveaux", "r_plus"): (0, 20, "niveaux R+n"),
    ("emprise_sol", "ces", "pct"): (0.0, 100.0, "emprise au sol CES (%)"),
    ("retraits", "voie", "min_m"): (0.0, 30.0, "recul voie (m)"),
    ("retraits", "limites_separatives", "min_m"): (0.0, 30.0, "recul limites séparatives (m)"),
    ("pleine_terre", "pct", "pct"): (0.0, 100.0, "pleine terre (%)"),
    ("pleine_terre", "pct", "espaces_verts_pct"): (0.0, 100.0, "espaces verts (%)"),
    ("pleine_terre", "pct", "pleine_terre_part"): (0.0, 100.0, "part pleine terre (%)"),
    ("stationnement", "par_logement", "places"): (0.0, 10.0, "places / logement"),
    ("mixite", None, "quota_pct"): (0.0, 100.0, "quota LLS (%)"),
    ("mixite", None, "seuil_logements"): (0, 500, "seuil logements mixité"),
}

# feuilles SDP-déterminantes (mêmes que la garde moteur zonage._FEUILLES_SDP_CAPACITE) : une
# feuille `propose` ici rendrait la capacité non calculable, jamais un chiffre servi.
_FEUILLES_SDP = {
    ("hauteur", "faitage"), ("hauteur", "egout"), ("hauteur", "niveaux"),
    ("emprise_sol", "ces"), ("retraits", "voie"), ("retraits", "limites_separatives"),
    ("pleine_terre", "pct"),
}


def _feuilles_par_insee():
    """{insee: {zone: [feuilles]}} depuis iter_regles_calibrees (une passe)."""
    par = {}
    for f in D.iter_regles_calibrees():
        par.setdefault(f["insee"], {}).setdefault(f["zone"], []).append(f)
    return par


def _num(feuille, cle):
    v = feuille.get(cle)
    return v if isinstance(v, (int, float)) else None


# ─────────────────────────────── le générateur ───────────────────────────────────────────────
def generer(cx):
    specs: list[RuleSpec] = []
    ecartees: list[Ecartee] = []

    par_insee = _feuilles_par_insee()

    # extrait PDF (sparse — ne contient PAS toutes les pages : ~12/106 pour 97404) : on ne l'utilise
    # QUE pour prouver que la commune EST extraite ; la validité d'une page se juge sur `pages_total`
    # du YAML (page ∈ [1, pages_total]), pas sur l'appartenance au sous-échantillon extrait (ce
    # serait un faux positif systématique). Pages_total par insee lu des meta YAML.
    extrait_ok = table_existe(cx, "plu_reglement_extrait")
    insee_extraits: set = set()
    if extrait_ok:
        with cx.conn.cursor() as cur:
            cur.execute("SELECT DISTINCT insee FROM plu_reglement_extrait WHERE page_pdf IS NOT NULL")
            insee_extraits = {r[0] for r in cur.fetchall()}
    pages_total: dict[str, int] = {}
    for path in sorted((_ICI.parents[3] / "config" / "plu_destinations").glob("974??_*.yaml")):
        d = D._load_yaml(str(path))
        m = d.get("meta") or {}
        if m.get("insee") and isinstance(m.get("pages_total"), int):
            pages_total[m["insee"]] = m["pages_total"]

    # ========== AXE A : bornes du règlement (une règle par insee × borne) =====================
    # On agrège par (insee, chemin) : 1 règle = « toutes les feuilles valides de ce type dans
    # cette commune tombent dans [lo,hi] ». Ça multiplie ~23 communes × ~8 bornes → ~150.
    for ins, zones in sorted(par_insee.items()):
        for (rub, feu, cle), (lo, hi, lib) in _BORNES.items():
            hits = []  # (zone, valeur)
            for zone, feuilles in zones.items():
                for f in feuilles:
                    chemin = f["chemin"]
                    attendu = rub if feu is None else f"{rub}.{feu}"
                    if chemin != attendu or f.get("statut") != "valide":
                        continue
                    v = _num(f, cle)
                    if v is not None:
                        hits.append((zone, v))
            if not hits:
                ecartees.append(Ecartee(
                    f"F4.bornes.{ins}.{rub}.{feu or cle}.{cle}", "F4",
                    f"plu_destinations/{ins}",
                    f"aucune feuille VALIDÉE {lib} dans {ins} — règle sans objet"))
                continue
            viol = [(z, v) for z, v in hits if not (lo <= v <= hi)]
            spec = RuleSpec(
                id=f"F4.bornes.{ins}.{rub}.{feu or cle}",
                famille="F4", source=f"plu_destinations/{ins} · {lib}",
                libelle=f"[{ins}] {lib} de chaque zone valide ∈ [{lo}, {hi}]",
                gravite="INCOHERENT", attendu=f"0 feuille hors [{lo},{hi}] (sur {len(hits)})",
                check=_mk_check_bornes(ins, lib, lo, hi, viol, len(hits)))
            specs.append(spec)

    # ========== AXE B : citation non vide + page_pdf dans [1, pages_total] (par insee) ========
    for ins, zones in sorted(par_insee.items()):
        # citation non vide (vaut même sans extrait : c'est une contrainte sur le YAML)
        specs.append(RuleSpec(
            id=f"F4.citation.{ins}", famille="F4",
            source=f"plu_destinations/{ins} · citation",
            libelle=f"[{ins}] chaque feuille validée porte une citation non vide",
            gravite="INCOHERENT", attendu="0 feuille validée sans citation",
            check=_mk_check_citation(ins, zones)))
        # page_pdf dans la plage réelle du document (meta.pages_total). Prouve aussi, pour les
        # communes extraites, que la page citée est une vraie page du règlement servi.
        pt = pages_total.get(ins)
        if not isinstance(pt, int):
            ecartees.append(Ecartee(
                f"F4.page.{ins}", "F4", f"plu_destinations/{ins}",
                "meta.pages_total absent — bornage de page impossible"))
        else:
            extrait_note = "" if ins in insee_extraits else " (commune non extraite dans plu_reglement_extrait)"
            specs.append(RuleSpec(
                id=f"F4.page.{ins}", famille="F4",
                source=f"plu_destinations/{ins} · page_pdf",
                libelle=f"[{ins}] chaque page_pdf citée ∈ [1, {pt}] (vraie page du règlement){extrait_note}",
                gravite="INCOHERENT", attendu=f"0 page hors [1,{pt}]",
                check=_mk_check_page(ins, zones, pt)))

    # ========== AXE C : renvoi vers zone existante & calibrée ================================
    for path in sorted((_ICI.parents[3] / "config" / "plu_destinations").glob("974??_*.yaml")):
        doc = D._load_yaml(str(path))
        ins = (doc.get("meta") or {}).get("insee")
        if not ins:
            continue
        renvois = D.renvois_commune(ins)  # {zone: cible} (zones sans regles propre)
        if not renvois:
            ecartees.append(Ecartee(
                f"F4.renvoi.{ins}", "F4", f"plu_destinations/{ins}",
                "aucune zone à renvoi (sans règles propre) — règle sans objet"))
            continue
        zones_declarees = set((doc.get("zones") or {}).keys())
        # une cible est valable si elle est une zone déclarée de la commune (résolue par clé norm)
        from labuse.plu.destinations import _norm_zone
        norm_declarees = {_norm_zone(z) for z in zones_declarees}
        manquants = [(z, c) for z, c in renvois.items()
                     if _norm_zone(c) not in norm_declarees]
        specs.append(RuleSpec(
            id=f"F4.renvoi.{ins}", famille="F4",
            source=f"plu_destinations/{ins} · renvoi",
            libelle=f"[{ins}] chaque renvoi pointe vers une zone déclarée de la commune",
            gravite="INCOHERENT", attendu=f"0 renvoi orphelin (sur {len(renvois)})",
            check=_mk_check_renvoi(ins, manquants, len(renvois))))

    # ========== AXE D : aucun propose ne sert un chiffre (par la donnée) ======================
    # Zones (insee, zone) dont une feuille SDP est `propose` en portant une valeur → elles ne
    # doivent alimenter AUCUNE parcelle à SDP servie > 0. On teste par parcel_zone_plu × residuel.
    zones_propose: set[tuple] = set()
    for ins, zones in par_insee.items():
        for zone, feuilles in zones.items():
            for f in feuilles:
                parts = f["chemin"].split(".")
                rub = parts[0]; feu = parts[1] if len(parts) > 1 else None
                if (rub, feu) in _FEUILLES_SDP and f.get("statut") == "propose":
                    # porte-t-elle une valeur qui BRANCHERAIT la SDP ?
                    porte = (any(isinstance(f.get(k), (int, float)) for k in ("m", "pct", "min_m", "r_plus"))
                             or f.get("forme") == "alignement"
                             or isinstance(f.get("espaces_verts_pct"), (int, float)))
                    if porte:
                        zones_propose.add((ins, zone))
    # pour chaque (insee, zone) propose : règle « 0 parcelle de cette zone a sdp servie > 0 ».
    # On regroupe en UNE règle SQL par insee (VALUES des zones propose) pour ménager la base.
    if table_existe(cx, "parcel_zone_plu") and table_existe(cx, "parcel_residuel"):
        by_ins: dict[str, list] = {}
        for ins, zone in zones_propose:
            by_ins.setdefault(ins, []).append(zone)
        for ins, zs in sorted(by_ins.items()):
            # zone_lib dans parcel_zone_plu = libellé servi ; on match sur zone_lib = code calibré.
            vals = ",".join("(%s)" for _ in zs)
            sql = f"""
                WITH z(zone) AS (VALUES {vals})
                SELECT count(*)
                FROM parcel_zone_plu pz
                JOIN z ON z.zone = pz.zone_lib
                JOIN parcels p ON p.idu = pz.idu
                JOIN parcel_residuel r ON r.parcel_id = p.id
                WHERE substr(p.idu,1,5) = %s AND r.sdp_residuelle_m2 > 0
            """
            ex = f"""
                WITH z(zone) AS (VALUES {vals})
                SELECT pz.idu, pz.zone_lib, r.sdp_residuelle_m2, r.capacite_estimee
                FROM parcel_zone_plu pz
                JOIN z ON z.zone = pz.zone_lib
                JOIN parcels p ON p.idu = pz.idu
                JOIN parcel_residuel r ON r.parcel_id = p.id
                WHERE substr(p.idu,1,5) = %s AND r.sdp_residuelle_m2 > 0
                LIMIT 3
            """
            specs.append(RuleSpec(
                id=f"F4.propose_sdp.{ins}", famille="F4",
                source=f"plu_destinations/{ins} · feuilles SDP propose",
                libelle=f"[{ins}] aucune parcelle à SDP servie > 0 n'a une zone calibrée propose "
                        f"({len(zs)} zone(s))",
                gravite="FAUX-CLIENT", attendu="0 parcelle SDP>0 sur zone propose",
                sql_violations=sql, exemples_sql=ex, params=tuple(zs) + (ins,)))
        if not by_ins:
            ecartees.append(Ecartee(
                "F4.propose_sdp.ile", "F4", "plu_destinations",
                "aucune zone à feuille SDP propose portant valeur — garde moteur déjà pleine"))

    # ========== AXE E : couverture GPU (chaque famille servie a règles OU raison) =============
    # Les zones GPU réellement portées par des parcelles servies (parcel_zone_plu.zone_lib) :
    # chacune doit résoudre à des regles OU être flaggée non-calculable (habitat/règle non validée/
    # non calibrée). On teste au grain famille (U/AU/A/N) : une famille constructible (U/AU) qui
    # porte des parcelles SDP>0 est prouvée calculable ; une parcelle SDP>0 sans règle NI raison
    # = un trou. On exprime ça par la cause : une parcelle SDP=0 doit porter une CAUSE écrite.
    if table_existe(cx, "parcel_zone_plu") and table_existe(cx, "parcel_residuel"):
        # E1 : une parcelle U/AU GENUINEMENT sous-bâtie (pct_potentiel < 90 : il reste de la marge)
        #       mais à SDP servie = 0 doit porter une CAUSE écrite (habitat_interdit /
        #       regle_plu_non_validee / terrain_exigu / bâti / assiette…). Une parcelle SATURÉE
        #       (pct_potentiel ≥ 90, déjà au plafond) a légitimement SDP=0 sans cause — ce n'est
        #       PAS un trou (vérifié : 63 137/63 192 des SDP=0 U/AU à cause NULL sont saturées).
        specs.append(RuleSpec(
            id="F4.gpu.cause_ecrite", famille="F4",
            source="parcel_residuel.cause · parcel_zone_plu",
            libelle="toute parcelle U/AU sous-bâtie (pct<90) à SDP=0 porte une cause écrite",
            gravite="INCOHERENT", attendu="0 parcelle U/AU, pct<90, SDP=0, cause NULL",
            sql_violations="""
                SELECT count(*)
                FROM parcel_zone_plu pz
                JOIN parcels p ON p.idu = pz.idu
                JOIN parcel_residuel r ON r.parcel_id = p.id
                WHERE pz.zone_fam IN ('U','AU')
                  AND r.sdp_residuelle_m2 = 0
                  AND r.pct_potentiel < 90
                  AND (r.cause IS NULL OR btrim(r.cause) = '')
            """,
            exemples_sql="""
                SELECT pz.idu, pz.zone_lib, pz.zone_fam, r.pct_potentiel, r.cause
                FROM parcel_zone_plu pz
                JOIN parcels p ON p.idu = pz.idu
                JOIN parcel_residuel r ON r.parcel_id = p.id
                WHERE pz.zone_fam IN ('U','AU')
                  AND r.sdp_residuelle_m2 = 0
                  AND r.pct_potentiel < 90
                  AND (r.cause IS NULL OR btrim(r.cause) = '')
                LIMIT 3
            """))
        # E2 : une cause « regle_plu_non_validee:<zone> » implique SDP = 0 (le propose ne sert pas).
        specs.append(RuleSpec(
            id="F4.gpu.non_validee_sdp0", famille="F4",
            source="parcel_residuel.cause",
            libelle="une parcelle « regle_plu_non_validee » a toujours SDP servie = 0",
            gravite="FAUX-CLIENT", attendu="0 parcelle non-validée à SDP>0",
            sql_violations="""
                SELECT count(*) FROM parcel_residuel
                WHERE cause ILIKE 'regle_plu_non_validee%' AND sdp_residuelle_m2 > 0
            """,
            exemples_sql="""
                SELECT parcel_id, cause, sdp_residuelle_m2 FROM parcel_residuel
                WHERE cause ILIKE 'regle_plu_non_validee%' AND sdp_residuelle_m2 > 0 LIMIT 3
            """))
        # E3 : une cause « habitat_interdit » implique SDP = 0 (habitat interdit → pas de logement).
        specs.append(RuleSpec(
            id="F4.gpu.habitat_interdit_sdp0", famille="F4",
            source="parcel_residuel.cause",
            libelle="une parcelle « habitat_interdit » a toujours SDP servie = 0",
            gravite="FAUX-CLIENT", attendu="0 parcelle habitat_interdit à SDP>0",
            sql_violations="""
                SELECT count(*) FROM parcel_residuel
                WHERE cause ILIKE 'habitat_interdit%' AND sdp_residuelle_m2 > 0
            """,
            exemples_sql="""
                SELECT parcel_id, cause, sdp_residuelle_m2 FROM parcel_residuel
                WHERE cause ILIKE 'habitat_interdit%' AND sdp_residuelle_m2 > 0 LIMIT 3
            """))

    return specs, ecartees


# ── fabriques de callables (closent sur des données pré-calculées, pas de requête lourde) ────
def _mk_check_bornes(ins, lib, lo, hi, viol, n):
    def _c(cx, api):
        if not viol:
            return "OK", f"{n} feuille(s) {lib} ∈ [{lo},{hi}] (0 hors borne)"
        apercu = "; ".join(f"{z}={v}" for z, v in viol[:3])
        return "ECART", f"{len(viol)}/{n} feuille(s) {lib} hors [{lo},{hi}] : {apercu}"
    return _c


def _mk_check_citation(ins, zones):
    def _c(cx, api):
        manques = []
        for zone, feuilles in zones.items():
            for f in feuilles:
                if f.get("statut") != "valide" or f.get("absent"):
                    continue
                if not str(f.get("citation") or "").strip():
                    manques.append(f"{zone}/{f['chemin']}")
        if not manques:
            return "OK", "0 feuille validée sans citation"
        return "ECART", f"{len(manques)} feuille(s) validée(s) sans citation : {', '.join(manques[:3])}"
    return _c


def _mk_check_page(ins, zones, pages_total):
    def _c(cx, api):
        manques = []
        for zone, feuilles in zones.items():
            for f in feuilles:
                if f.get("statut") != "valide":
                    continue
                pg = f.get("page_pdf")
                if pg in (None, ""):
                    continue
                if not (isinstance(pg, int) and 1 <= pg <= pages_total):
                    manques.append(f"{zone}/{f['chemin']}=p.{pg}")
        if not manques:
            return "OK", f"toutes les pages citées ∈ [1,{pages_total}]"
        return "ECART", f"{len(manques)} page(s) citée(s) hors [1,{pages_total}] : {', '.join(manques[:3])}"
    return _c


def _mk_check_renvoi(ins, manquants, n):
    def _c(cx, api):
        if not manquants:
            return "OK", f"{n} renvoi(s) vers zone déclarée"
        apercu = "; ".join(f"{z}→{c}" for z, c in manquants[:3])
        return "ECART", f"{len(manquants)}/{n} renvoi(s) orphelin(s) : {apercu}"
    return _c


# ─────────────────────────────── bilan autonome ─────────────────────────────────────────────
if __name__ == "__main__":
    cx = connexion()
    specs, ecartees = generer(cx)
    res = run_specs(cx, specs)
    b = bilan(res)
    print(f"F4 — LE PLU")
    print(f"  générées retenues : {len(specs)}")
    print(f"  écartées          : {len(ecartees)}")
    print(f"  OK={b['OK']}  ECART={b['ECART']}  SKIP={b['SKIP']}")
    print()
    for r in res:
        if r.statut == "ECART":
            print(f"  [ECART] {r.spec.id} · {r.spec.gravite}")
            print(f"          {r.message}")
            for e in r.exemples[:3]:
                print(f"            · {e}")
    print()
    skips = [r for r in res if r.statut == "SKIP"]
    if skips:
        print(f"  SKIP ({len(skips)}) :")
        for r in skips[:10]:
            print(f"    {r.spec.id} : {r.message}")
    # récap écartées par motif
    print()
    import collections
    mot = collections.Counter(e.raison.split(" —")[0].split(" (")[0] for e in ecartees)
    print("  écartées par motif :")
    for m, c in mot.most_common():
        print(f"    {c:3d}  {m}")
