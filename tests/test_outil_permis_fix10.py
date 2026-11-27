"""OUTIL-PERMIS-FIX-10 — LOT 0 : le FILET, écrit AVANT les correctifs (il doit échouer maintenant).

Contre-audit 02-PERMIS-ASTRA-5, liste « C'est faux » (3 points) :
  1. le bloc « Activité de dépôt de permis » (`depots_recents`) compte et date sur la colonne BRUTE
     `date_depot` → pour 97401000AD0701, il compte 9744012520010 (DR_DEPOT 09/03/2026, AN_DEPOT 2025)
     comme un dépôt de 2026 et affiche « dernier = 2026-03-09 » ;
  2. l'alerte de zone garde un TITRE « Permis déposé dans… » même quand le dépôt est écarté (le détail
     ne connaît que l'autorisation) ;
  3. (traité hors test db, par la migration + preuve de non-écriture) le trigger résiduel.

+ un test STRUCTUREL : AUCUN fichier (hors `permis_classe.py`) ne doit lire la colonne Sitadel
  `date_depot` / `DR_DEPOT` pour l'afficher, la compter, la trier ou la comparer — sauf exception
  légitime inscrite NOMMÉMENT ci-dessous avec sa raison.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

import pytest
from sqlalchemy import text

_SRC = Path(__file__).resolve().parents[1] / "src" / "labuse"


# ───────────────────────────── test structurel (non-db, dans le hook) ─────────────────────────────
# OUTIL-PERMIS-FIX-12 (LOT 4) — contre-audit ASTRA-6 : le test ne dispense plus un FICHIER entier. Chaque
# exception vise un USAGE PRÉCIS — la FONCTION (ou la requête) qui touche `date_depot`/`DR_DEPOT`, avec sa
# raison. Les mentions en COMMENTAIRE et en DOCSTRING ne comptent pas (pas un usage) ; les requêtes SQL en
# chaîne, si (elles touchent la colonne), comptent. Un usage dans une fonction NON listée fait échouer le
# test (même dans un fichier déjà « connu ») ; une exception SANS usage réel (périmée) le fait échouer aussi.
import ast as _ast  # noqa: E402
import io as _io  # noqa: E402
import tokenize as _tokenize  # noqa: E402

#: USAGES AUTORISÉS de la date de dépôt Sitadel : clé (chemin relatif à src/labuse, FONCTION) → RAISON.
#: `<module>` = au niveau module (constante/template/schéma). Tout usage hors de cette table échoue.
USAGES_AUTORISES: dict[tuple[str, str], str] = {
    # ── permis_classe.py — LA maison de la règle unique ──
    ("permis_classe.py", "<module>"): "gabarit SQL _DEPOT_COND_TMPL de la condition « dépôt affichable ».",
    ("permis_classe.py", "depot_affichable_sql"): "fonction UNIQUE — CASE SQL du dépôt affichable (::date ou NULL).",
    ("permis_classe.py", "depot_affichable"): "fonction UNIQUE — version Python de la règle (tests/lecteurs Python).",
    ("permis_classe.py", "depot_date_sql"): "fonction UNIQUE (FIX-13) — date de DÉPÔT réelle (dépôt affichable "
        "sinon 1er janvier de AN_DEPOT) pour FILTRER/GROUPER « ce qui est déposé » (Scan patrimoine).",
    ("permis_classe.py", "depot_depuis_cond_sql"): "fonction UNIQUE (FIX-16) — filtre « déposées depuis » "
        "SANS jour inventé (jour-contre-jour si affichable, année-contre-année sinon ; via depot_affichable_sql).",
    # ── SÉLECTION / AFFICHAGE via la fonction unique (clé de SORTIE date_depot = valeur gatée) ──
    ("alertes.py", "compute_alertes"): "alerte de zone — « déposé le <date_depot> » SEULEMENT si le dépôt "
        "est affichable ; la SÉLECTION passe par evenement_date_sql (jamais la date brute).",
    ("alertes_migration.py", "_exprs"): "migration FIX-12 — recompose label/détail (dépôt affichable) "
        "EXACTEMENT comme compute_alertes.",
    ("api/modules.py", "permis_fiche"): "fiche — dépôt AFFICHÉ via depot_affichable_sql (clé de sortie date_depot, gatée).",
    ("api/moteurs.py", "histoire_parcelle"): "frise — dépôt via depot_affichable_sql (clé de sortie date_depot, gatée).",
    ("api/site_voisinage.py", "historique_permis"): "historique — dépôt via depot_affichable_sql ; tri/fenêtre sur l'autorisation.",
    ("api/pdf_premium.py", "render_fiche_pdf"): "PDF premium — consomme la valeur GATÉE du payload (clé date_depot).",
    ("exports/miroir.py", "_r_permis_liste"): "Dossier — consomme la valeur GATÉE du payload historique_site (pas la colonne brute).",
    # ── INGESTION Sitadel — ÉCRIT la colonne brute + millésime (usages NOMMÉS, pas un affichage) ──
    ("ingestion/permits_sdes.py", "<module>"): "ingestion — SQL d'upsert de la colonne brute date_depot (stockage).",
    ("ingestion/permits_sdes.py", "_date_depot"): "ingestion — parse DR_DEPOT → date_depot (+ raw.date_depot_brute).",
    ("ingestion/permits_sdes.py", "ingest_sdes"): "ingestion — stocke l'année de dépôt officielle AN_DEPOT "
        "dans raw (la SEULE date de dépôt fiable du flux SDES).",
    ("ingestion/permits_sdes.py", "run"): "ingestion — millésime de SOURCE = max(dépôt, autorisation) : horizon des "
        "données ingérées (ASTRA-6 : usage distinct du stockage, nommé), jamais un affichage.",
    # ── SCHÉMA ──
    ("models.py", "<module>"): "schéma ORM — déclaration de la colonne date_depot.",
    ("models.py", "ensure_sitadel_depot"): "schéma — migration idempotente ADD COLUMN date_depot.",
    # ── MÉTA de fraîcheur de source ──
    ("filtres/sources.py", "<module>"): "méta de fraîcheur SITADEL (date_cols=('date_depot',)) — pas un affichage/compte.",
    # ── CALIBRATION interne NON servie — autorisation, repli date_depot si nulle ──
    ("verite_terrain_capacite.py", "_permis_post_plu"): "vérité-terrain (calibration, NON servie) — COALESCE(date, date_depot).",
    ("verite_terrain_capacite.py", "_ecrire_notes"): "vérité-terrain — texte de note de méthode (repli date_depot).",
    ("verite_terrain_dpe_permis.py", "_labuse_commune"): "vérité-terrain DPE (calibration, NON servie) — filtre d'historique.",
    # ── MODULE DORMANT m10 (décommissionné, trigger retiré FIX-10) ──
    ("ingestion/permit_delais_m10.py", "<module>"): "module DORMANT — couche m10 décommissionnée (non câblée, non lue).",
    ("ingestion/permit_delais_m10.py", "build_delais"): "module DORMANT — m10 décommissionnée (AN_DEPOT→1er janvier, non câblée).",
    ("regles/velocite_delai_median_mois.py", "<module>"): "fiche de RÈGLE décommissionnée — texte : le dépôt "
        "n'est connu qu'à l'année (AN_DEPOT→1er janvier), délai d'instruction ni calculé ni servi.",
    # ── AUTRE table pige_depots (annonces Pige), sans rapport avec sitadel_permits ──
    ("circuit_garanties.py", "radar_sans_depot"): "AUTRE table pige_depots (max date_depot des annonces Pige).",
    ("pige/api.py", "radar_check"): "AUTRE table pige_depots (dernier dépôt d'annonces).",
    ("pige/tables.py", "<module>"): "AUTRE table pige_depots (schéma).",
    # ── REGISTRE — texte de déclaration des lectures servies ──
    ("registre/lectures.py", "<module>"): "registre — texte descriptif des lectures servies (documentation).",
}

# OUTIL-PERMIS-FIX-13 (LOT 3) — la date de DÉPÔT Sitadel a DEUX colonnes sources : `date_depot`/`DR_DEPOT`
# (date brute, souvent corrompue) ET `an_depot`/`AN_DEPOT` (millésime de dépôt fiable). Les DEUX sont des
# lectures de dépôt à médiatiser par `permis_classe` : le test les traque ensemble. Scan patrimoine
# (veille_promoteurs) lit désormais la date de dépôt via `permis_classe.depot_date_sql` (aucun littéral ici
# → consommateur vérifié, pas un intrus).
_TOKEN = re.compile(r"\bdate_depot\b|\bDR_DEPOT\b|\ban_depot\b|\bAN_DEPOT\b")


def _lignes_a_ignorer(txt: str, tree: _ast.Module) -> set[int]:
    """Lignes de COMMENTAIRE et de DOCSTRING (module/fonction/classe) — pas un usage de la colonne."""
    ignore: set[int] = set()
    try:
        for tok in _tokenize.generate_tokens(_io.StringIO(txt).readline):
            if tok.type == _tokenize.COMMENT:
                ignore.add(tok.start[0])
    except _tokenize.TokenError:
        pass
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.Module, _ast.FunctionDef, _ast.AsyncFunctionDef, _ast.ClassDef)):
            if node.body and isinstance(node.body[0], _ast.Expr) and \
                    isinstance(getattr(node.body[0], "value", None), _ast.Constant) and \
                    _ast.get_docstring(node, clean=False) is not None:
                v = node.body[0].value
                for ln in range(v.lineno, (v.end_lineno or v.lineno) + 1):
                    ignore.add(ln)
    return ignore


def _fonction_englobante(tree: _ast.Module, lineno: int) -> str:
    best = None
    for node in _ast.walk(tree):
        if isinstance(node, (_ast.FunctionDef, _ast.AsyncFunctionDef)) and \
                node.lineno <= lineno <= (node.end_lineno or node.lineno):
            if best is None or node.lineno > best.lineno:
                best = node
    return best.name if best else "<module>"


def _usages_code() -> set[tuple[str, str]]:
    """Tous les (fichier, fonction) où `date_depot`/`DR_DEPOT` apparaît dans du CODE (hors commentaire
    et hors docstring ; les requêtes SQL en chaîne comptent)."""
    trouves: set[tuple[str, str]] = set()
    for f in sorted(_SRC.rglob("*.py")):
        txt = f.read_text(encoding="utf-8")
        if not _TOKEN.search(txt):
            continue
        tree = _ast.parse(txt)
        ignore = _lignes_a_ignorer(txt, tree)
        rel = f.relative_to(_SRC).as_posix()
        for i, line in enumerate(txt.splitlines(), 1):
            if i not in ignore and _TOKEN.search(line):
                trouves.add((rel, _fonction_englobante(tree, i)))
    return trouves


def test_lot4_structurel_usage_par_usage_du_depot():
    """Chaque usage CODE de la date de dépôt Sitadel vise une FONCTION autorisée nommément (plus de
    dispense de fichier entier, ASTRA-6). Deux garde-fous : (1) aucun usage hors `USAGES_AUTORISES`
    (intrus = nouveau lecteur direct) ; (2) aucune exception PÉRIMÉE (listée sans usage réel)."""
    usages = _usages_code()
    intrus = sorted(u for u in usages if u not in USAGES_AUTORISES)
    perimes = sorted(u for u in USAGES_AUTORISES if u not in usages)
    assert not intrus, (
        "Usage direct de la date de dépôt Sitadel hors USAGES_AUTORISES : "
        + "; ".join(f"{r}::{fn}" for r, fn in intrus)
        + " — passer par permis_classe (fonction unique) / la date d'autorisation, ou inscrire "
        "l'usage NOMMÉMENT (fichier, fonction) dans USAGES_AUTORISES avec sa raison.")
    assert not perimes, (
        "Exception(s) PÉRIMÉE(s) dans USAGES_AUTORISES (plus aucun usage) : "
        + "; ".join(f"{r}::{fn}" for r, fn in perimes) + " — retirer l'entrée.")


# ───────────────────────────── témoins sur base (labuse_test) ─────────────────────────────

def _seed_parcelle(db, idu):
    wkt = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"
    return db.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) "
        "VALUES (:i,'Dépôtville','AD','0701', ST_GeomFromText(:w,4326), "
        " ST_Transform(ST_GeomFromText(:w,4326),2975), 500, ST_Centroid(ST_GeomFromText(:w,4326)), "
        " ST_Envelope(ST_GeomFromText(:w,4326))) RETURNING id"), {"i": idu, "w": wkt}).scalar()


def _seed_permit(db, pid, *, aut, dep, an_depot, idus):
    db.execute(text("DELETE FROM sitadel_permits WHERE permit_id = :p"), {"p": pid})
    db.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, date_depot, idu_codes, commune, raw) "
        "VALUES (:p,'DP',:aut,:dep,CAST(:i AS jsonb),'Dépôtville',CAST(:r AS jsonb))"),
        {"p": pid, "aut": aut, "dep": dep, "i": json.dumps(idus), "r": json.dumps({"an_depot": an_depot})})


@pytest.mark.db
def test_lot0_bloc_depots_ne_compte_pas_la_date_contradictoire(db_session):
    """Témoin 1 — 9744012520010 (DR_DEPOT 09/03/2026, AN_DEPOT 2025) ne doit PAS être compté comme un
    dépôt de 2026 ni dater le bloc « dernier = 2026-03-09 ». Un dépôt VALIDE de contrôle (09/05/2024,
    AN_DEPOT 2024) reste compté. ÉCHOUE maintenant (count=2, dernier=2026-03-09)."""
    from labuse.ingestion.permits import depots_recents
    s = db_session
    idu = "97401000AD0701"
    s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    pid = _seed_parcelle(s, idu)
    _seed_permit(s, "9744012520010", aut="2025-10-24", dep="2026-03-09", an_depot="2025", idus=[idu])  # écarté
    _seed_permit(s, "DEPOT-VALIDE-10", aut="2024-09-01", dep="2024-05-10", an_depot="2024", idus=[idu])  # valide
    dep = depots_recents(s, pid)
    assert dep is not None and dep.get("parcelle") is not None
    assert "2026-03-09" not in json.dumps(dep, default=str)          # la date écartée n'apparaît nulle part
    assert dep["parcelle"]["count"] == 1                             # seul le dépôt valide compte
    assert dep["parcelle"]["dernier"] == "2024-05-10"               # dernier = le dépôt valide


@pytest.mark.db
def test_lot0_alerte_de_zone_titre_annonce_l_evenement_date(db_session):
    """Témoin 2 — pour 97441626E0304 (dépôt écarté, autorisé 03/08/2026), le TITRE de l'alerte de zone
    doit annoncer l'événement réellement daté (« Permis autorisé dans… »), pas « déposé ». ÉCHOUE
    maintenant (titre toujours « Permis déposé dans… »)."""
    from labuse import alertes
    s = db_session
    commune = "Zonetitre10"
    lon, lat = 55.333, -20.999
    zone = {"type": "Polygon", "coordinates": [[
        [lon - 0.002, lat - 0.002], [lon + 0.002, lat - 0.002], [lon + 0.002, lat + 0.002],
        [lon - 0.002, lat + 0.002], [lon - 0.002, lat - 0.002]]]}
    s.execute(text("DELETE FROM alertes WHERE source_ref = '97441626E0304'"))
    s.execute(text("DELETE FROM sitadel_permits WHERE permit_id = '97441626E0304'"))
    alertes.create_watch_zone(s, "Titre FIX-10", commune, zone, None)
    alertes.compute_alertes(s, commune, None)
    s.execute(text(
        "INSERT INTO sitadel_permits (permit_id, type, date, date_depot, commune, geom, raw, idu_codes) "
        "VALUES ('97441626E0304','DP','2026-08-03','2020-06-01', :c, "
        "ST_SetSRID(ST_MakePoint(:lon,:lat),4326), CAST('{\"an_depot\":\"2026\"}' AS jsonb), '[]'::jsonb)"),
        {"c": commune, "lon": lon, "lat": lat})
    alertes.compute_alertes(s, commune, None)
    label = s.execute(text("SELECT label FROM alertes WHERE source_ref = '97441626E0304'")).scalar()
    assert "autorisé" in label.lower() and "déposé" not in label.lower()


def _watch_zone(s, name, commune, lon, lat):
    from labuse import alertes
    zone = {"type": "Polygon", "coordinates": [[
        [lon - 0.002, lat - 0.002], [lon + 0.002, lat - 0.002], [lon + 0.002, lat + 0.002],
        [lon - 0.002, lat + 0.002], [lon - 0.002, lat - 0.002]]]}
    alertes.create_watch_zone(s, name, commune, zone, None)
    alertes.compute_alertes(s, commune, None)


@pytest.mark.db
def test_fix10_lot2_titre_et_tri_alignes_sur_le_texte(db_session):
    """LOT 2 — le TITRE, le détail et `fait_date` (le tri) annoncent le MÊME événement. Dépôt AFFICHABLE
    → « Permis déposé » + fait_date = date de dépôt ; dépôt écarté → « Permis autorisé » + fait_date =
    date d'autorisation."""
    from labuse import alertes
    s = db_session
    commune = "Zonetri10"
    lon, lat = 55.21, -21.21
    _watch_zone(s, "Tri FIX-10", commune, lon, lat)
    # (a) dépôt AFFICHABLE : DR 10/05/2024 (AN_DEPOT 2024) < autorisation 01/09/2024
    s.execute(text("DELETE FROM alertes WHERE source_ref IN ('AFF-DEP','ECARTE')"))
    for pid in ("AFF-DEP", "ECARTE"):
        s.execute(text("DELETE FROM sitadel_permits WHERE permit_id = :p"), {"p": pid})
    s.execute(text(
        "INSERT INTO sitadel_permits (permit_id,type,date,date_depot,commune,geom,raw,idu_codes) "
        "VALUES ('AFF-DEP','PC','2024-09-01','2024-05-10',:c,ST_SetSRID(ST_MakePoint(:lo,:la),4326),"
        "CAST('{\"an_depot\":\"2024\"}' AS jsonb),'[]'::jsonb)"), {"c": commune, "lo": lon, "la": lat})
    # (b) dépôt ÉCARTÉ : DR 09/03/2026 mais AN_DEPOT 2025 → autorisation 24/10/2025
    s.execute(text(
        "INSERT INTO sitadel_permits (permit_id,type,date,date_depot,commune,geom,raw,idu_codes) "
        "VALUES ('ECARTE','PC','2025-10-24','2026-03-09',:c,ST_SetSRID(ST_MakePoint(:lo,:la),4326),"
        "CAST('{\"an_depot\":\"2025\"}' AS jsonb),'[]'::jsonb)"), {"c": commune, "lo": lon, "la": lat})
    alertes.compute_alertes(s, commune, None)
    aff = s.execute(text("SELECT label, payload->>'fait_date' AS fd, payload->>'detail' AS det "
                         "FROM alertes WHERE source_ref='AFF-DEP'")).mappings().first()
    assert "déposé" in aff["label"].lower() and aff["fd"] == "2024-05-10" and "déposé le 2024-05-10" in aff["det"]
    eca = s.execute(text("SELECT label, payload->>'fait_date' AS fd, payload->>'detail' AS det "
                         "FROM alertes WHERE source_ref='ECARTE'")).mappings().first()
    assert "autorisé" in eca["label"].lower() and eca["fd"] == "2025-10-24"
    assert "autorisé le 2025-10-24" in eca["det"] and "2026-03-09" not in eca["det"]   # jamais la date écartée


@pytest.mark.db
def test_fix10_lot2_aucune_alerte_double_ni_perdue(db_session):
    """LOT 2 — la clé d'arrivée est inchangée : réévaluer n'émet pas de doublon (ON CONFLICT) et ne perd
    pas l'alerte du panneau (une ligne, stable)."""
    from labuse import alertes
    s = db_session
    commune = "Zonedup10"
    lon, lat = 55.19, -21.19
    _watch_zone(s, "Dup FIX-10", commune, lon, lat)
    s.execute(text("DELETE FROM alertes WHERE source_ref = 'DUP-10'"))
    s.execute(text("DELETE FROM sitadel_permits WHERE permit_id = 'DUP-10'"))
    s.execute(text(
        "INSERT INTO sitadel_permits (permit_id,type,date,date_depot,commune,geom,raw,idu_codes) "
        "VALUES ('DUP-10','PC','2026-02-01','2026-01-05',:c,ST_SetSRID(ST_MakePoint(:lo,:la),4326),"
        "CAST('{\"an_depot\":\"2026\"}' AS jsonb),'[]'::jsonb)"), {"c": commune, "lo": lon, "la": lat})
    r1 = alertes.compute_alertes(s, commune, None)
    r2 = alertes.compute_alertes(s, commune, None)   # réévaluation
    assert r1["permis_in_zone"] == 1 and r2["permis_in_zone"] == 0   # arrivée détectée une fois
    n = s.execute(text("SELECT count(*) FROM alertes WHERE source_ref = 'DUP-10'")).scalar()
    assert n == 1                                                    # une seule ligne : ni double ni perdue
