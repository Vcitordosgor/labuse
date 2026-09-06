"""CIRCUIT-1 lot 4 — LA SONDE DE COHÉRENCE « Vérifier que tout coule ».

  · 4.1 `verifier_robinets` : pour chaque chiffre servi par ≥ 2 robinets, compare les chemins
    réels sur les TÉMOINS (24 communes — méthode héritée de scripts/inventaire/mesure_fuites.py).
    Écarts → `circuit_ecarts` (dédupliqués par (chiffre, clé, robinets) ; un écart disparu
    passe `statut='solde'` et GARDE sa ligne — 4.4, l'historique que Vic veut voir).
  · 4.2 `verifier_eau_ancienne` : par TAMPON — run ≠ manifeste, millésime servi plus vieux que
    le réservoir. Les six familles de CIRCUIT-0 sont le jeu de contrôle ; après les lots 2-3 il
    doit en rester zéro hors « solaire gelé, étiqueté ».
  · 4.3 `controle` : une ligne de verdict par passage (`circuit_controles`) — la page lit la
    dernière. Lancé par le job wrapper `coherence-robinets`, APRÈS chaque bascule, et au bouton.

0-bis (CIRCUIT-2) — la V1 « fonctions seulement » est DÉPASSÉE : `verifier_chemins_reels`
appelle l'endpoint HTTP de la fiche (TestClient in-process) et l'outil Copilote sur les
témoins EXPORTS-1 (TEMOINS_PARCELLES) ; la famille PDF est portée par le cas
`verifier_exports` (scripts/recette_exports1.py — 24 PDF des 4 témoins, nocturne seulement) ;
`verifier_scission_neuf` verrouille l'arbitrage Q3 (scoring = VEFA à l'acte, bilan = observé) ;
le contrôle « mots interdits » (config/mots_interdits.yaml, versionnée) est un verdict DISTINCT.
"""
from __future__ import annotations

import json
import logging
import time

from sqlalchemy import text

log = logging.getLogger("labuse.sonde_circuit")

DDL = """
CREATE TABLE IF NOT EXISTS circuit_ecarts (
  id bigserial PRIMARY KEY,
  chiffre_id varchar(120) NOT NULL,
  cle text NOT NULL,
  robinet_a varchar(120) NOT NULL,
  valeur_a text,
  robinet_b varchar(120) NOT NULL,
  valeur_b text,
  cause varchar(24),            -- denominateur · perimetre · run · table · millesime · fenetre_temporelle · arrondi · autre
  depuis timestamptz NOT NULL DEFAULT now(),
  statut varchar(12) NOT NULL DEFAULT 'ouvert',   -- ouvert | solde
  solde_le timestamptz,
  commit_solde varchar(64),
  UNIQUE (chiffre_id, cle, robinet_a, robinet_b)
);
CREATE TABLE IF NOT EXISTS circuit_eau_ancienne (
  id bigserial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  chiffre_id varchar(120) NOT NULL,
  robinet varchar(120) NOT NULL,
  tampon text,
  attendu text,
  mecanisme text,
  statut varchar(12) NOT NULL DEFAULT 'ouvert'    -- ouvert | etiquete (assumé) | solde
);
CREATE TABLE IF NOT EXISTS circuit_controles (
  id bigserial PRIMARY KEY,
  ts timestamptz NOT NULL DEFAULT now(),
  fuites_ouvertes int NOT NULL,
  eau_ancienne int NOT NULL,
  robinets_couverts int NOT NULL,
  robinets_non_couverts int NOT NULL,
  duree_s numeric,
  details jsonb
)
"""


def ensure(db) -> None:
    for stmt in DDL.split(";"):
        if stmt.strip():
            db.execute(text(stmt))
    # CIRCUIT-2 lot 4 — la sonde devient CATÉGORIELLE : chaque écart porte le TYPE de la donnée
    # (nombre · classe · geometrie · couche · texte · liste) ; la page et les pastilles comptent
    # les types classe/geometrie comme les autres (5.3).
    db.execute(text("ALTER TABLE circuit_ecarts ADD COLUMN IF NOT EXISTS "
                    "type varchar(12) NOT NULL DEFAULT 'nombre'"))
    db.execute(text("ALTER TABLE circuit_ecarts ALTER COLUMN chiffre_id TYPE varchar(120)"))
    # CIRCUIT-5 lot 3.3 — la sonde écrit des IDS, plus seulement des libellés (dette P3) :
    # `robinet_*_id` = id du registre quand le côté EST un robinet (NULL sinon : moteur, SQL,
    # règle — le libellé reste). Backfill des lignes d'avant la migration.
    db.execute(text("ALTER TABLE circuit_ecarts ADD COLUMN IF NOT EXISTS robinet_a_id varchar(120)"))
    db.execute(text("ALTER TABLE circuit_ecarts ADD COLUMN IF NOT EXISTS robinet_b_id varchar(120)"))
    db.execute(text("ALTER TABLE circuit_eau_ancienne ADD COLUMN IF NOT EXISTS robinet_id varchar(120)"))
    _backfill_ids(db)


#: lot 3.3 — libellés descriptifs de la sonde → id de robinet du registre (quand le côté est
#: bien un robinet servi ; un côté moteur/SQL/règle n'a PAS d'id et garde son libellé seul).
CORRESPONDANCES_ROBINETS: dict[str, str] = {
    "http:/parcels": "fiche_parcelle_entete",
    "copilote:fiche_parcelle": "copilote_fiche_parcelle",
    "attrs.niveau (servi)": "couche_alea_inondation",
    "sitadel_permits (points servis)": "couche_permis",
    "payload fiche (bloc dpe_connu, non affiché)": "",   # servi par AUCUN robinet (Fiche.tsx:1492)
    "fiche parcelle / filtres": "",                       # ancien libellé DPE (backfill)
}


def robinet_id_de(libelle: str | None) -> str | None:
    """L'id de robinet du registre pour un libellé de la sonde — le libellé lui-même s'il EST
    un id, la correspondance déclarée sinon, None quand le côté n'est pas un robinet."""
    if not libelle:
        return None
    from .registre import ROBINETS
    if libelle in ROBINETS:
        return libelle
    return CORRESPONDANCES_ROBINETS.get(libelle) or None


def _backfill_ids(db) -> None:
    """lot 3.3 — pose les ids sur les lignes écrites avant la migration (idempotent)."""
    # l'eau DPE historique : chiffre HORS registre « (chiffres DPE) » → `dpe_connu` (donnée du
    # registre, attribuable), et SOLDÉE — le contrôle a été corrigé (last_sync_at, plus le max
    # des dates de contenu) et la source ré-ingérée --force le 06/09/2026 : l'eau a été bue.
    db.execute(text(
        "UPDATE circuit_eau_ancienne SET chiffre_id = 'dpe_connu', statut = 'solde' "
        "WHERE chiffre_id = '(chiffres DPE)'"))
    for table, cols in (("circuit_ecarts", ("robinet_a", "robinet_b")),
                        ("circuit_eau_ancienne", ("robinet",))):
        suffixe = "_id" if table == "circuit_eau_ancienne" else None
        for col in cols:
            cible = f"{col}{suffixe}" if suffixe else f"{col}_id"
            rows = db.execute(text(
                f"SELECT DISTINCT {col} FROM {table} WHERE {cible} IS NULL")).scalars().all()  # noqa: S608
            for lib in rows:
                rid = robinet_id_de(lib)
                if rid:
                    db.execute(text(
                        f"UPDATE {table} SET {cible} = :rid WHERE {col} = :lib AND {cible} IS NULL"),  # noqa: S608
                        {"rid": rid, "lib": lib})


def _upsert_ecart(db, chiffre_id: str, cle: str, ra: str, va, rb: str, vb, cause: str,
                  type_donnee: str = "nombre") -> None:
    db.execute(text(
        "INSERT INTO circuit_ecarts (chiffre_id, cle, robinet_a, valeur_a, robinet_b, valeur_b,"
        " cause, type, robinet_a_id, robinet_b_id) "
        "VALUES (:c, :k, :ra, :va, :rb, :vb, :ca, :t, :ra_id, :rb_id) "
        "ON CONFLICT (chiffre_id, cle, robinet_a, robinet_b) DO UPDATE SET "
        " valeur_a = EXCLUDED.valeur_a, valeur_b = EXCLUDED.valeur_b, cause = EXCLUDED.cause, "
        " type = EXCLUDED.type, robinet_a_id = EXCLUDED.robinet_a_id, "
        " robinet_b_id = EXCLUDED.robinet_b_id, statut = 'ouvert', solde_le = NULL"),
        {"c": chiffre_id, "k": cle, "ra": ra, "va": str(va), "rb": rb, "vb": str(vb),
         "ca": cause, "t": type_donnee, "ra_id": robinet_id_de(ra), "rb_id": robinet_id_de(rb)})


def verifier_robinets(db) -> dict:
    """4.1 — les chiffres à ≥ 2 robinets, mesurés par leurs chemins réels sur les témoins.
    Rend {ecarts_trouves, mesures, couverts, non_couverts}."""
    from .registre import CHIFFRES, ROBINETS
    from .registre.moteurs.zonage import parts_zonage_surface

    mesures = 0
    trouves: list[tuple] = []
    verifies: set[tuple[str, str, str, str]] = set()

    # ── témoin 1 : les parts de zonage (LA fuite de CIRCUIT-0) sur les 24 communes ──
    communes = [c for (c,) in db.execute(text(
        "SELECT DISTINCT commune FROM parcels ORDER BY commune")).all()]
    for com in communes:
        parts = parts_zonage_surface(db, com)
        if not parts:
            continue
        # la fiche commune sert le MÊME objet (rebranchée lot 2.1) : re-mesure par le chemin fiche
        from .api.app import _foncier_commune
        try:
            fiche = _foncier_commune(db, com).get("repartition_zonage")
        except Exception:  # noqa: BLE001 — commune sans données de run : la sonde continue
            db.rollback()
            continue
        mesures += 1
        for fam in ("U", "AU", "A", "N"):
            cle = (f"part_zone_{fam}_pct", com, "moteur:zonage", "fiche_commune_zonage")
            verifies.add(cle)
            va = parts["familles"][fam]["pct"]
            vb = (fiche or {}).get("familles", {}).get(fam, {}).get("pct")
            if vb is not None and abs(float(va) - float(vb)) > 0.05:
                trouves.append((f"part_zone_{fam}_pct", com, "moteur:zonage", va,
                                "fiche_commune_zonage", vb, "denominateur"))

    # ── témoin 2 : le compte de sources (3 écrans, unifiés au lot 0.2) ──
    try:
        from . import etats_sources, flux
        n_flux = flux.construire_flux(db)["comptes"]["total"]
        n_arbitre = len(etats_sources.lister_etats(db))
        mesures += 1
        verifies.add(("n_sources", "global", "admin_flux_circuit", "page_sources_client"))
        if n_flux != n_arbitre:
            trouves.append(("n_sources", "global", "admin_flux_circuit", n_flux,
                            "page_sources_client", n_arbitre, "perimetre"))
    except Exception:  # noqa: BLE001
        db.rollback()

    for t in trouves:
        _upsert_ecart(db, *t)
    # 4.4 — solder les écarts re-mesurés ce passage et absents des trouvés
    cles_trouves = {(t[0], t[1], t[2], t[4]) for t in trouves}
    solde = 0
    for v in verifies - cles_trouves:
        n = db.execute(text(
            "UPDATE circuit_ecarts SET statut = 'solde', solde_le = now() "
            "WHERE chiffre_id = :c AND cle = :k AND robinet_a = :ra AND robinet_b = :rb "
            "AND statut = 'ouvert'"),
            {"c": v[0], "k": v[1], "ra": v[2], "rb": v[3]}).rowcount
        solde += n

    multi = {cid for cid, c in CHIFFRES.items()
             if sum(1 for r in ROBINETS.values() if cid in r.chiffres) >= 2}
    couverts = {"part_zone_U_pct", "part_zone_AU_pct", "part_zone_A_pct", "part_zone_N_pct", "n_sources"}
    return {"ecarts_trouves": len(trouves), "mesures": mesures, "soldes": solde,
            "chiffres_multi_robinets": len(multi),
            "couverts": len(couverts & multi) + len(couverts - multi),
            "non_couverts": len(multi - couverts)}


#: 0-bis — les quatre témoins d'EXPORTS-1 ENTRENT dans les parcelles golden de la sonde (mandat
#: CIRCUIT-2, lot 0-bis point 5). Même jeu que scripts/recette_exports1.py (jamais deux listes).
TEMOINS_PARCELLES: tuple[str, ...] = (
    "97415000BO0852", "97401000AD0554", "97416000DY0106", "97411000AV0110")


def _parcel_id(db, idu: str) -> int | None:
    return db.execute(text("SELECT id FROM parcels WHERE idu = :i"), {"i": idu}).scalar()


def verifier_chemins_reels(db) -> dict:
    """0-bis (dû du 4.1) — la sonde appelle les VRAIS chemins, plus seulement les fonctions :
    endpoint HTTP de la fiche (TestClient in-process), outil Copilote, et la famille PDF (portée
    par le cas recette_exports1, nocturne — jamais « non_couverts » pour ces trois familles).
    Compare sur les témoins EXPORTS-1 : surface (HTTP vs SQL), SDP au sol (HTTP vs moteur
    potentiel), Copilote fiche_parcelle (surface outil vs HTTP), et « Neuf VEFA » ABSENT de la
    fiche (scission 0-bis / arbitrage Q3)."""
    trouves: list[tuple] = []
    mesures = 0
    familles = {"http": 0, "copilote": 0, "pdf": "cas recette_exports1 (nocturne)"}
    try:
        from fastapi.testclient import TestClient

        from .api.app import app
        client = TestClient(app)
    except Exception as exc:  # noqa: BLE001 — app inimportable : la sonde le DIT, jamais muette
        return {"ecarts_trouves": 0, "mesures": 0, "familles": familles,
                "erreur": f"TestClient indisponible : {exc}"}
    for idu in TEMOINS_PARCELLES:
        pid = _parcel_id(db, idu)
        if pid is None:
            continue
        try:
            fiche = client.get(f"/parcels/{idu}").json()
        except Exception:  # noqa: BLE001
            db.rollback()
            continue
        mesures += 1
        familles["http"] += 1
        # surface : HTTP = SQL (passe-plat honnête)
        surf_sql = db.execute(text("SELECT surface_m2 FROM parcels WHERE idu = :i"),
                              {"i": idu}).scalar()
        surf_http = fiche.get("surface_m2")
        if surf_sql is not None and surf_http is not None and \
                abs(float(surf_sql) - float(surf_http)) > 0.5:
            trouves.append(("surface_parcelle_m2", idu, "http:/parcels", surf_http,
                            "sql:parcels.surface_m2", surf_sql, "table"))
        # SDP au sol : HTTP (potentiel_transformation) = moteur potentiel (EXPORTS-1 lot 3)
        try:
            from .faisabilite.potentiel import bloc_potentiel
            bloc = bloc_potentiel(db, pid)
            sdp_moteur = (bloc or {}).get("au_sol", {}).get("sdp_residuelle_m2")
            sdp_http = ((fiche.get("potentiel_transformation") or {})
                        .get("au_sol") or {}).get("sdp_residuelle_m2")
            if sdp_moteur is not None and sdp_http is not None and \
                    abs(float(sdp_moteur) - float(sdp_http)) > 0.5:
                trouves.append(("sdp_residuelle_m2", idu, "http:/parcels", sdp_http,
                                "moteur:potentiel", sdp_moteur, "run"))
        except Exception:  # noqa: BLE001
            db.rollback()
        # scission du neuf (robinet) : le VEFA à l'acte ne se sert plus sous la fiche (Q3)
        if "Neuf VEFA" in json.dumps(fiche, ensure_ascii=False, default=str):
            trouves.append(("prix_neuf_observe_eur_m2", idu, "http:/parcels",
                            "« Neuf VEFA » servi", "scission 0-bis", "id acte réservé au scoring",
                            "perimetre"))
        # outil Copilote : fiche_parcelle (surface outil = surface HTTP)
        try:
            from .copilote_v2 import outils
            res = outils.fiche_parcelle(db, idu=idu)
            familles["copilote"] += 1
            if res.valeur is not None and surf_http is not None and \
                    abs(float(res.valeur) - float(surf_http)) > 0.5:
                trouves.append(("surface_parcelle_m2", idu, "copilote:fiche_parcelle",
                                res.valeur, "http:/parcels", surf_http, "table"))
        except Exception:  # noqa: BLE001
            db.rollback()
    ensure(db)   # idem : le DDL a pu être annulé par un rollback interne
    for t in trouves:
        _upsert_ecart(db, *t)
    return {"ecarts_trouves": len(trouves), "mesures": mesures, "familles": familles}


def verifier_scission_neuf(db) -> dict:
    """0-bis point 3 — la sonde vérifie que le SCORING lit le VEFA à l'acte
    (prix_neuf_vefa_acte_eur_m2) et le BILAN le neuf observé (prix_neuf_observe_eur_m2).
    Mesuré sur les témoins : (a) la chaîne bilan résout par resolve_prix_neuf_marche ;
    (b) score_e servi ne porte plus le grain « secteur » (il n'existait que dans le précalcul
    divergent — CIRCUIT-1 2.2) ; jamais l'un sous le libellé de l'autre."""
    trouves: list[tuple] = []
    mesures = 0
    for idu in TEMOINS_PARCELLES:
        pid = _parcel_id(db, idu)
        if pid is None:
            continue
        try:
            from .faisabilite.bilan import resolve_prix_sortie_servi
            from .ingestion.dvf_prix_neuf import resolve_prix_neuf_marche
            servi = resolve_prix_sortie_servi(db, pid)
            brut = resolve_prix_neuf_marche(db, pid)
            mesures += 1
            p_servi = servi.get("prix")
            p_brut = (brut or {}).get("prix") if isinstance(brut, dict) else None
            # le bilan peut ajuster par bilan_params (override secteur) — mais s'il diverge du
            # moteur observé SANS niveau d'override déclaré, c'est une fuite.
            if p_servi is not None and p_brut is not None and \
                    abs(float(p_servi) - float(p_brut)) > 0.5 and \
                    servi.get("niveau") not in ("override_bassin",):
                trouves.append(("prix_neuf_observe_eur_m2", idu,
                                "bilan:resolve_prix_sortie_servi", p_servi,
                                "moteur:resolve_prix_neuf_marche", p_brut, "autre"))
        except Exception:  # noqa: BLE001
            db.rollback()
    # (b) scoring : score_e servi sans grain « secteur » (précalcul divergent mort)
    try:
        if db.execute(text("SELECT to_regclass('score_e')")).scalar():
            n_secteur = db.execute(text(
                "SELECT count(*) FROM score_e WHERE niveau_prix = 'secteur'")).scalar() or 0
            mesures += 1
            if n_secteur:
                trouves.append(("prix_neuf_vefa_acte_eur_m2", "global",
                                "score_e (niveau_prix)", f"{n_secteur} lignes 'secteur'",
                                "moteur:neuf_vefa_commune (live)",
                                "grain secteur = précalcul divergent mort", "table"))
    except Exception:  # noqa: BLE001
        db.rollback()
    ensure(db)   # idem : le DDL a pu être annulé par un rollback interne
    for t in trouves:
        _upsert_ecart(db, *t)
    return {"ecarts_trouves": len(trouves), "mesures": mesures}


def verifier_exports(db) -> dict:
    """0-bis point 5 — scripts/recette_exports1.py devient UN CAS DE LA SONDE : génération des
    24 PDF des 4 témoins par les vraies routes, extraction, comparaison à fiche.json — joué au
    passage NOCTURNE (declencheur cron), jamais au bouton (lourd : WeasyPrint + pdftotext).
    Le contrôle « mots interdits » (liste versionnée config/mots_interdits.yaml) est un verdict
    DISTINCT des divergences de grandeurs."""
    import os
    import subprocess
    import sys as _sys
    import tempfile
    from pathlib import Path
    script = Path(__file__).resolve().parents[2] / "scripts" / "recette_exports1.py"
    if not script.exists():
        return {"erreur": f"script absent : {script}"}
    with tempfile.TemporaryDirectory(prefix="sonde-exports-") as tmp:
        jpath = Path(tmp) / "verdict.json"
        env = dict(os.environ)
        env.setdefault("DYLD_FALLBACK_LIBRARY_PATH", "/opt/homebrew/lib")
        env["PYTHONPATH"] = str(script.parents[1] / "src")
        try:
            proc = subprocess.run(
                [_sys.executable, str(script), "--dir", tmp, "--json", str(jpath)],
                capture_output=True, text=True, timeout=1800, env=env)
        except Exception as exc:  # noqa: BLE001 — échec technique DIT, jamais déguisé en absence
            return {"erreur": f"recette injouable : {exc}"}
        if not jpath.exists():
            return {"erreur": f"recette sans verdict (rc={proc.returncode}) : "
                              f"{(proc.stderr or proc.stdout or '')[-400:]}"}
        verdict = json.loads(jpath.read_text())
    for e in verdict.get("erreurs", []):
        if "mot interdit" in e:
            continue           # contrôle distinct ci-dessous
        _upsert_ecart(db, "exports_recette", e[:200], "pdf:recette_exports1", "divergence",
                      "fiche.json / endpoint fiche", "référence écran", "autre")
    for m in verdict.get("mots_interdits", []):
        _upsert_ecart(db, "mots_interdits", m[:200], "pdf:recette_exports1", "présent",
                      "config/mots_interdits.yaml", "0 attendu", "autre")
    return {"n_erreurs_hors_mots": verdict.get("n_erreurs_hors_mots", 0),
            "n_mots_interdits": verdict.get("n_mots_interdits", 0)}


#: CIRCUIT-5 lot 5.2 — CE QUE LA SONDE COMPARE chaque nuit, couple par couple :
#: chiffre_id → les robinets du registre dont le chemin est mesuré. La vérité du code,
#: vérifiée par le verrou V5c contre les couples déclarés du registre.
SONDE_COUVRE: dict[str, tuple[str, ...]] = {
    "part_zone_U_pct": ("fiche_commune_zonage",),
    "part_zone_AU_pct": ("fiche_commune_zonage",),
    "part_zone_A_pct": ("fiche_commune_zonage",),
    "part_zone_N_pct": ("fiche_commune_zonage",),
    "n_sources": ("admin_flux_circuit", "page_sources_client"),
    "surface_parcelle_m2": ("copilote_fiche_parcelle",),
    "sdp_residuelle_m2": ("fiche_parcelle_constructibilite",),
    "prix_neuf_observe_eur_m2": ("fiche_parcelle_constructibilite",),
    "zone_plu_famille": ("fiche_parcelle_urbanisme",),
    "alea_inondation_couche": ("couche_alea_inondation",),
    "historique_permis_liste": ("fiche_parcelle_autour",),
    "divisible_classe": ("fiche_parcelle_division",),
    "prod_spec_kwh_kwc": ("outil_prospection_solaire",),
    "population_zone": ("outil_etude_zone",),
    "dpe_connu": (),          # en_attente : aucun robinet ne l'affiche (eau ancienne seule)
    "verdict_couche": ("couche_verdict",),
    "parcelle_geometrie": (),  # eau ancienne 4.5 (geom_simple) — pas une comparaison de robinets
}

#: lot 5.2 — les couples multi-robinets que la sonde ne compare PAS ENCORE, chacun avec sa
#: raison (un couple silencieux = verrou V5c cassé, jamais un « non couvert »). Raison par
#: chiffre (elle vaut pour tous ses couples non couverts).
NON_SONDES: dict[str, str] = {
    "tier_opportunite": "reconstruit à la bascule (portée run) — vérité tenue par le golden servi "
                        "(qa/golden_check, GOLDEN-REGEN) sur les 119 parcelles",
    "run_label_servi": "pointeur du manifeste — tenu par V3a (tuiles = run servi) et le golden",
    "prix_neuf_vefa_acte_eur_m2": "scission 0-bis mesurée par verifier_scission_neuf (grain "
                                  "score_e) — la comparaison robinet à robinet viendra avec "
                                  "l'extension sonde (chantier à décider Vic)",
    "annonces_actives_n": "Radar : compte recontrôlé par recomptage humain (échantillon 4.4 "
                          "carte annonces) — pas de second chemin machine",
    "azimut_bati_deg": "OUTILS-FIX-1 A2 : servi liste + carte du même moteur solaire — un seul "
                       "producteur, comparaison sans objet tant que le front ne recalcule pas",
    "capacite_logements": "fiche + PDF lisent le MÊME bloc potentiel (EXPORTS-1) — couverts par "
                          "le cas recette_exports1 (nocturne), pas par la sonde au bouton",
    "charge_fonciere_eur": "idem potentiel/bilan — cas recette_exports1 (nocturne)",
    "surface_vendable_m2": "idem potentiel/bilan — cas recette_exports1 (nocturne)",
    "potentiel_verdict": "idem potentiel — cas recette_exports1 (nocturne)",
    "comparateur_composite": "comparateur : composite d'affichage (moteur commune.composite) — "
                             "extension sonde à décider Vic",
    "deficit_sru_pts": "fiche commune + comparateur lisent commune_contexte_sru — couvert par "
                       "l'échantillon producteur SRU (4.4, à valider) puis extension sonde",
    "taux_lls_pct": "idem SRU — échantillon producteur 4.4 + identité du bloc (V4b)",
    "ecart_demande_acte_pct": "Radar marché : n<5 déjà gardé ; extension sonde à décider Vic",
    "mixite_clause": "règle L111 servie fiche+PDF du même moteur — cas recette_exports1",
    "mutations_12m_n": "fiche commune + comparateur (moteur commune.indicateurs) — échantillon "
                       "producteur DVF (4.4, à valider)",
    "n_bascules_7j": "compteur d'exploitation (page Circuit seule) — pas un chiffre client",
    "n_biens_du_jour": "digest Radar : recompté par le dedup event_log (RADAR-DIGESTS lot 4)",
    "n_communes_rnu": "corpus PLU : garde etat_corpus_plu (CIRCUIT-4) — un seul producteur",
    "n_densifiables": "fiche commune + couche lisent parcel_renouvellement du run servi — "
                      "tenu par V3a (une génération) et le golden",
    "n_parcelles_pm": "fiche propriétaire + contexte commune (proprietaire_historique, une "
                      "assiette) — KF-2 lot 1, extension sonde à décider Vic",
    "n_piscines": "détection ortho : QA humaine (piscine_corrections) fait foi — pas de second "
                  "chemin machine",
    "n_vigilances": "compteur d'affichage front (CIRCUIT-2 : portée front à rapatrier — dette "
                    "déjà écrite au registre)",
    "permis_12m_n": "fiche commune + comparateur (moteur commune) — échantillon producteur "
                    "Sitadel (4.4, à valider)",
    "permis_5a_n": "idem permis_12m_n",
    "point_mort_n": "idem permis (vélocité) — moteur commune.indicateurs",
    "pression_zan_ha": "passe-plat commune_conso_enaf (rattachement à décider, lot 1) — "
                       "échantillon producteur ZAN (4.4, à valider)",
    "prix_ancien_median_eur_m2": "fiche commune + comparateur (marche_service) — échantillon "
                                 "producteur DVF (4.4, à valider)",
    "prix_demande_median_eur_m2": "Radar (affiché vs acté) : n<5 gardé, recomptage humain",
    "prix_terrain_secteur_eur_m2": "parcelle-secteur (marche_service, témoins CONCEPTS 3.3 "
                                   "mesurés) — extension sonde à décider Vic",
    "projet_cadrage_n": "CRM projets : compteur interne (event_log) — pas un chiffre source",
    "stock_opportunites": "fiche commune + accueil lisent le run servi — golden + V3a",
    "velocite_delai_median_mois": "moteur commune.indicateurs — échantillon Sitadel (4.4)",
    "zonage_plu_couche": "couche calée cadastre vs zone_servie : comparés par la catégorielle "
                         "4.1 sur les témoins (couple couvert via zone_plu_famille)",
    "n_sources": "quatre lectures TENUES par V2a (68 = 68 partout, même WHERE_AFFICHEES) ; "
                 "la sonde en compare deux",
    "population_zone": "fiche « autour » et PDF Flash CONSOMMENT le moteur etude_de_zone "
                       "(FLASH-ZONE F2, aucune recopie) ; le cache isochrones est gardé par "
                       "l'eau 3 (TTL 30 j)",
    "prod_spec_kwh_kwc": "outil, fiche soleil et toits lisent le MÊME builder solaire (gel "
                         "étiqueté, eau 4) — pas de second calcul à comparer",
    "sdp_residuelle_m2": "outils densifier/faisa et PDF lisent le même bloc potentiel — "
                         "PDF couverts par recette_exports1 (nocturne)",
    "surface_parcelle_m2": "outil_etudier_bien lit le même passe-plat parcels.surface_m2 — "
                           "la sonde compare déjà HTTP/SQL/Copilote (chemins réels 0-bis)",
    "zone_plu_famille": "couche comparée par la catégorielle 4.1 ; PDF zonage par "
                        "recette_exports1 (nocturne)",
    "prix_neuf_observe_eur_m2": "PDF banquier couvert par recette_exports1 ; la scission du "
                                "neuf est mesurée par verifier_scission_neuf",
}


def temoins_tournants(db, n: int = 50) -> list[str]:
    """CIRCUIT-5 lot 5.3 — l'échantillon TOURNANT : n parcelles tirées parmi celles
    CONSULTÉES la veille (journal d'usage `consultation_log.idu`), tirage DÉTERMINISTE du
    jour (md5(idu || date du jour)) — rejouable dans la nuit, différent chaque jour, pour
    qu'un écart hors témoins fixes finisse par être vu."""
    try:
        return [r for (r,) in db.execute(text(
            "SELECT idu FROM (SELECT DISTINCT idu FROM consultation_log "
            " WHERE idu IS NOT NULL AND ts >= (CURRENT_DATE - INTERVAL '1 day')) t "
            "ORDER BY md5(idu || CURRENT_DATE::text) LIMIT :n"), {"n": n}).all()]
    except Exception:  # noqa: BLE001 — pas de journal d'usage : échantillon vide, dit au verdict
        db.rollback()
        return []


def _temoins_golden(db) -> list[str]:
    """Les parcelles témoins de la sonde catégorielle : les 4 EXPORTS-1 + les GOLDEN_IDUS de
    qa/golden_check.py (même jeu, jamais deux listes — parsé du fichier ; repli : sélection
    STABLE par idu si le fichier manque, le compte est dit dans le verdict)."""
    import re
    from pathlib import Path
    idus = list(TEMOINS_PARCELLES)
    golden = Path(__file__).resolve().parents[2] / "qa" / "golden_check.py"
    if golden.exists():
        m = re.search(r"GOLDEN_IDUS = \[(.*?)\]", golden.read_text(), re.S)
        if m:
            idus += re.findall(r'"(\d{5}0{3}[A-Z]{2}\d{4})"', m.group(1))
    if len(idus) < 10:      # repli honnête : jeu stable, jamais un échantillon aléatoire
        idus += [r for (r,) in db.execute(text(
            "SELECT idu FROM parcels ORDER BY idu LIMIT 46")).all()]
    return list(dict.fromkeys(idus))


def verifier_categorielle(db) -> dict:
    """CIRCUIT-2 lot 4 — LA SONDE CATÉGORIELLE : la sonde sait désormais dire « la fiche dit
    zone A, la couche peint U ».

    · 4.1 ZONAGE : famille servie (zone_dominante — la fiche) vs dominante CALCULÉE des parts
      GPU vs table écran/couche `parcel_zone_plu`, sur les témoins golden. 0 écart attendu.
    · 4.2 ALÉAS : contrôle de DISTRIBUTION du domaine — un degré DEAL ELEVE/TRES_ELEVE ne peut
      pas être servi `niveau='moyen'` (la régression RETOURS-13 ne peut plus passer inaperçue).
    · 4.3 PERMIS : un permis à géométrie APPROXIMATIVE (sitadel_permits.geom_approx) n'est
      jamais un point sur une parcelle (RETOURS-14).
    · 4.5 GÉOMÉTRIES : fiche/carte/PDF lisent la MÊME table cadastre ; si une table matérialisée
      `…geom_simple…` existe, elle n'est jamais plus vieille que la source (sinon eau ancienne).
    · 4.6 COUCHES : tuiles MVT fabriquées pour un AUTRE run que le servi ⇒ eau ancienne
      (mécanisme build-mvt).
    Les PDF de zonage (pré-dossier, lettre) sont confrontés par le cas recette_exports1
    (nocturne) — jamais « non couverts »."""
    trouves: list[tuple] = []
    mesures = 0
    # ── 4.1 zonage sur les témoins : les FIXES (golden) + le TOURNANT du jour (lot 5.3 :
    #    50 parcelles consultées la veille, tirage déterministe) ──
    tournants = temoins_tournants(db)
    temoins = list(dict.fromkeys(_temoins_golden(db) + tournants))
    for idu in temoins:
        pid = _parcel_id(db, idu)
        if pid is None:
            continue
        try:
            from .faisabilite.zone_servie import zone_dominante
            zs = zone_dominante(db, pid)
        except Exception:  # noqa: BLE001
            db.rollback()
            continue
        mesures += 1
        if zs.source == "parcel_zone_plu" and zs.parts and len(zs.parts) > 1:
            fam_calc = zs.parts[0].get("fam")
            if fam_calc and zs.zone_fam and fam_calc != zs.zone_fam:
                trouves.append(("zone_plu_famille", idu, "couche:parcel_zone_plu", zs.zone_fam,
                                "moteur:zone_servie (dominante calculée)", fam_calc,
                                "table", "classe"))
    # ── 4.2 aléas : distribution du domaine ──
    try:
        n_mal = db.execute(text(
            "SELECT count(*) FROM spatial_layers WHERE kind = 'georisque_alea' "
            "AND upper(COALESCE(attrs->>'degre','')) LIKE '%ELEVE%' "
            "AND COALESCE(attrs->>'niveau','') <> 'fort'")).scalar() or 0
        mesures += 1
        if n_mal:
            trouves.append(("alea_inondation_couche", "distribution",
                            "attrs.degre (DEAL brut)", f"{n_mal} zones ELEVE/TRES_ELEVE",
                            "attrs.niveau (servi)", "≠ fort — normalisées à tort",
                            "table", "classe"))
    except Exception:  # noqa: BLE001
        db.rollback()
    # ── 4.3 permis approximatifs ──
    try:
        if db.execute(text("SELECT to_regclass('sitadel_permits')")).scalar():
            cols = {r[0] for r in db.execute(text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_name = 'sitadel_permits'")).all()}
            mesures += 1
            if "geom_approx" in cols:
                n_pts = db.execute(text(
                    "SELECT count(*) FROM sitadel_permits "
                    "WHERE geom_approx IS TRUE AND geom IS NOT NULL")).scalar() or 0
                if n_pts:
                    trouves.append(("historique_permis_liste", "geom_approx",
                                    "sitadel_permits (points servis)", f"{n_pts} permis approximatifs à géométrie",
                                    "règle RETOURS-14", "jamais un point sur une parcelle",
                                    "perimetre", "geometrie"))
    except Exception:  # noqa: BLE001
        db.rollback()
    # ── 4.5 géométries : table matérialisée jamais plus vieille que la source ──
    try:
        simple = db.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_name LIKE '%geom_simple%' LIMIT 1")).scalar()
        if simple:
            n_src = db.execute(text("SELECT count(*) FROM parcels")).scalar() or 0
            n_mat = db.execute(text(f"SELECT count(*) FROM {simple}")).scalar() or 0  # noqa: S608
            mesures += 1
            if n_mat and abs(n_src - n_mat) > 0:
                db.execute(text(
                    "INSERT INTO circuit_eau_ancienne (chiffre_id, robinet, tampon, attendu,"
                    " mecanisme, statut) VALUES (:c, :r, :t, :a, :m, 'ouvert')"),
                    {"c": "parcelle_geometrie", "r": "carte (tuiles)",
                     "t": f"{simple} : {n_mat} lignes", "a": f"parcels : {n_src}",
                     "m": "geom_simple (table matérialisée en retard sur le cadastre)"})
    except Exception:  # noqa: BLE001
        db.rollback()
    # ── 4.6 couches : tuiles d'un autre run que le servi ──
    try:
        if db.execute(text("SELECT to_regclass('mvt_meta')")).scalar():
            from . import runs
            run_mvt = db.execute(text(
                "SELECT value FROM mvt_meta WHERE key = 'run_label'")).scalar()
            run_servi = runs.current()
            mesures += 1
            if run_mvt and run_servi and run_mvt != run_servi:
                db.execute(text(
                    "INSERT INTO circuit_eau_ancienne (chiffre_id, robinet, tampon, attendu,"
                    " mecanisme, statut) VALUES (:c, :r, :t, :a, :m, 'ouvert')"),
                    {"c": "verdict_couche", "r": "couche_verdict",
                     "t": f"tuiles fabriquées pour {run_mvt}", "a": f"run servi {run_servi}",
                     "m": "build-mvt (reconstruction détachée pas encore passée)"})
    except Exception:  # noqa: BLE001
        db.rollback()
    ensure(db)   # un rollback interne peut avoir annulé le DDL posé dans la même transaction
    for t in trouves:
        _upsert_ecart(db, *t[:7], type_donnee=t[7])
    return {"ecarts_trouves": len(trouves), "mesures": mesures, "temoins": len(temoins),
            "temoins_tournants": len(tournants),
            "pdf_zonage": "cas recette_exports1 (nocturne)"}


def eau_lignes(db) -> list[tuple[str, str, str, str, str, str]]:
    """4.2 (extrait CIRCUIT-5 lot 3) — les lignes d'eau ancienne MESURÉES maintenant, sans
    écrire : (chiffre_id, robinet, tampon, attendu, mecanisme, statut). Utilisé par
    `verifier_eau_ancienne` (qui les journalise) ET par le verrou V3b (état, sans doublon)."""
    from . import manifeste

    lignes: list[tuple[str, str, str, str, str, str]] = []
    # 1) division : des lignes hors du run du manifeste encore présentes ? (servies : plus jamais — lot 2.3)
    run_div = manifeste.division_run()
    autres = db.execute(text(
        "SELECT DISTINCT run_label FROM division_or_candidates WHERE run_label <> :r"),
        {"r": run_div}).scalars().all() if db.execute(text(
            "SELECT to_regclass('division_or_candidates')")).scalar() else []
    if autres:
        lignes.append(("divisible_classe", "fiche_parcelle_division",
                       f"runs en base : {sorted(autres)}", f"run servi : {run_div}",
                       "lignes d'anciens runs en base (non servies — scope lot 2.3) ; purge au geste",
                       "etiquete"))
    # 2) DPE : l'amont a-t-il publié une version APRÈS notre dernière ingestion ?
    # CIRCUIT-5 lot 3.3 — le comparant est `last_sync_at` (notre geste), plus le max des dates
    # de contenu : l'ancien contrôle (`dernier_vu > max(date_etablissement)`) restait « ouvert »
    # même base à jour, car le dernier DPE authentique 974 date du 21/07 quand l'amont republie
    # le JEU chaque semaine — un faux signal permanent, constaté au rafraîchissement --force du
    # 06/09 (16 DPE, max inchangé). Et la ligne devient ATTRIBUABLE : chiffre_id = `dpe_connu`
    # (donnée du registre, en_attente — le bloc payload existe, plus aucun robinet ne l'affiche).
    try:
        vu, sync = db.execute(text(
            "SELECT v.dernier_vu, d.last_sync_at FROM source_veille v "
            "JOIN data_sources d ON d.id = v.source_id "
            "WHERE d.name ILIKE 'DPE ADEME%'")).first() or (None, None)
        if vu and (sync is None or str(vu)[:10] > str(sync)[:10]):
            lignes.append(("dpe_connu", "payload fiche (bloc dpe_connu, non affiché)",
                           f"dernière ingestion {str(sync)[:10] if sync else 'jamais'}",
                           f"amont vu {str(vu)[:10]}",
                           "cron DPE : ré-ingérer (--force) pour boire la nouvelle version", "ouvert"))
    except Exception:  # noqa: BLE001
        db.rollback()
    # 3) isochrones : entrées au-delà du TTL 30 j (plus jamais SERVIES — lot 2.7 — mais à purger)
    try:
        n_vieilles = db.execute(text(
            "SELECT count(*) FROM zone_isochrone_cache "
            "WHERE created_at <= now() - interval '30 days'")).scalar() or 0
        if n_vieilles:
            lignes.append(("population_zone", "outil_etude_zone",
                           f"{n_vieilles} entrées de cache > 30 j", "TTL 30 j (lot 2.7)",
                           "entrées ignorées à la lecture ; purge à la prochaine bascule", "etiquete"))
    except Exception:  # noqa: BLE001
        db.rollback()
    # 4) solaire : gel assumé, étiqueté (jamais « ouvert »)
    lignes.append(("prod_spec_kwh_kwc", "outil_prospection_solaire",
                   "millésime gelé porté en base (bandeau)", "recalcul au geste solaire-build",
                   "gel ASSUMÉ et étiqueté (CIRCUIT-0, famille 3)", "etiquete"))
    return lignes


def verifier_eau_ancienne(db) -> dict:
    """4.2 — par tampon : run ≠ manifeste, millésime servi < réservoir. Les six familles de
    CIRCUIT-0 sont contrôlées ; « solaire gelé » sort `etiquete` (assumé), jamais `ouvert`.
    lot 3.3 : chaque ligne porte aussi `robinet_id` (id du registre, NULL si aucun robinet)."""
    lignes = eau_lignes(db)
    for (cid, rob, tampon, attendu, meca, statut) in lignes:
        db.execute(text(
            "INSERT INTO circuit_eau_ancienne (chiffre_id, robinet, robinet_id, tampon, attendu,"
            " mecanisme, statut) VALUES (:c, :r, :rid, :t, :a, :m, :s)"),
            {"c": cid, "r": rob, "rid": robinet_id_de(rob), "t": tampon, "a": attendu,
             "m": meca, "s": statut})
    ouvertes = sum(1 for x in lignes if x[5] == "ouvert")
    return {"lignes": len(lignes), "ouvertes": ouvertes,
            "etiquetees": sum(1 for x in lignes if x[5] == "etiquete")}


def controle(db, *, declencheur: str = "bouton", exports: bool | None = None,
             progres=None) -> dict:
    """4.3 — LE passage complet : robinets + eau ancienne + chemins réels (0-bis) + scission du
    neuf (0-bis) + verdict (une ligne circuit_controles). La page Circuit lit la dernière ligne.
    `exports` (0-bis) : le cas recette_exports1 (24 PDF des 4 témoins + mots interdits) est joué
    au passage NOCTURNE seulement (déclencheur cron), jamais au bouton — sauf override explicite.
    CIRCUIT-P2 (lot 3.2) : `progres(fait, total, label)` est appelé avant chaque phase pour la ligne
    de progression sous les onglets (jamais bloquant si None)."""
    t0 = time.monotonic()
    ensure(db)
    jouer_exports = (declencheur == "cron") if exports is None else exports
    phases = ["Robinets (témoins)", "Chemins réels sur parcelles", "Scission du neuf",
              "Cohérence catégorielle", "Eau ancienne"]
    if jouer_exports:
        phases.append("Exports (24 PDF)")
    total = len(phases)

    def _p(i):
        if progres:
            try:
                progres(i, total, phases[i])
            except Exception:  # noqa: BLE001 — la progression ne doit jamais casser le contrôle
                pass

    _p(0); rob = verifier_robinets(db)
    _p(1); chemins = verifier_chemins_reels(db)
    _p(2); neuf = verifier_scission_neuf(db)
    _p(3); cat = verifier_categorielle(db)
    _p(4); eau = verifier_eau_ancienne(db)
    if jouer_exports:
        _p(5)
    exp = verifier_exports(db) if jouer_exports else {"saute": "hors passage nocturne"}
    fuites_ouvertes = db.execute(text(
        "SELECT count(*) FROM circuit_ecarts WHERE statut = 'ouvert'")).scalar() or 0
    # lot 5.3 — les pastilles comptent AUSSI par type (classe/geometrie comme les nombres)
    par_type = dict(db.execute(text(
        "SELECT type, count(*) FROM circuit_ecarts WHERE statut = 'ouvert' GROUP BY type")).all())
    duree = round(time.monotonic() - t0, 2)
    details = {"declencheur": declencheur, "robinets": rob, "eau": eau,
               "chemins_reels": chemins, "scission_neuf": neuf, "categorielle": cat,
               "ecarts_par_type": par_type, "exports": exp}
    db.execute(text(
        "INSERT INTO circuit_controles (fuites_ouvertes, eau_ancienne, robinets_couverts,"
        " robinets_non_couverts, duree_s, details) VALUES (:f, :e, :c, :n, :d, :j)"),
        {"f": fuites_ouvertes, "e": eau["ouvertes"], "c": rob["couverts"],
         "n": rob["non_couverts"], "d": duree, "j": json.dumps(details, ensure_ascii=False, default=str)})
    return {"fuites_ouvertes": fuites_ouvertes, "eau_ancienne_ouverte": eau["ouvertes"],
            "eau_etiquetee": eau["etiquetees"], "ecarts_par_type": par_type,
            "duree_s": duree, **rob}
