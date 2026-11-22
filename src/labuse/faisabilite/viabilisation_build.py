"""M-VIA lot 2 — construction batch de `parcel_viabilisation`.

Calcule, par parcelle, les signaux du faisceau (permis < 100/200 m, façade voie
urbanisée, adjacence bâti, zone PLU, poste source S3REnR, zonage assainissement) et
le score 0-100. Le score est calculé en SQL avec EXACTEMENT les mêmes poids/seuils
que faisabilite.viabilisation.compute_score (parité vérifiée par test).

Aucun tracé de réseau : uniquement des signaux déjà en base + géométries publiques.
"""
from __future__ import annotations

import time

from sqlalchemy import text
from sqlalchemy.orm import Session

from . import viabilisation as V

_DDL = """
CREATE TABLE IF NOT EXISTS parcel_viabilisation (
    idu           VARCHAR(14) PRIMARY KEY,
    commune       VARCHAR(64),
    score         INTEGER,
    band          VARCHAR(16),
    zone_fam      VARCHAR(4),
    c100          INTEGER,
    c200          INTEGER,
    c100_recent   INTEGER,
    c100_acheve   INTEGER,
    voie10        BOOLEAN,
    voie75        BOOLEAN,
    bati10        BOOLEAN,
    bati30        BOOLEAN,
    bati75        BOOLEAN,
    assainissement_zonage VARCHAR(12),
    computed_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX IF NOT EXISTS ix_parcel_viab_commune ON parcel_viabilisation (commune);
CREATE INDEX IF NOT EXISTS ix_parcel_viab_band ON parcel_viabilisation (band);
"""

# Permis Sitadel AUTORISÉS et géolocalisés, projetés en 2975 (couche de voisinage lue par le mode
# parcelle de l'outil Permis, la fiche parcelle et le score de viabilisation). Un permis n'a de
# DATE_REELLE_AUTORISATION que s'il a été accordé.
#
# OUTIL-PERMIS-FIX-1 (LOT 3) — la couche était un SNAPSHOT refait seulement au run M-VIA (DROP+CREATE) :
# elle prenait un mois de retard sur `sitadel_permits` et lui manquait 3 004 permis déjà géolocalisés
# (BZ1065 comptait 11 au lieu de 13). Désormais elle est MAINTENUE PAR TRIGGER : chaque INSERT/UPDATE/
# DELETE sur `sitadel_permits` met à jour la ligne correspondante → elle suit d'elle-même l'ingestion,
# sans dépendre du run M-VIA. `ensure_via_permits_geo()` est idempotent (table + index + trigger), et
# `resync=True` refait le plein une fois (réconciliation initiale / après un backfill sans trigger).
# Migration : l'ancienne couche était un snapshot SANS clé primaire. On la refait (cache dérivé,
# reconstruit par le resync) pour poser la PK permit_id. Transactionnel → les lecteurs ne voient
# jamais la table absente.
_VIA_MIGRATE = """
DO $mig$
BEGIN
    IF to_regclass('via_permits_geo') IS NOT NULL
       AND NOT EXISTS (SELECT 1 FROM pg_constraint
                       WHERE conrelid = 'via_permits_geo'::regclass AND contype = 'p') THEN
        DROP TABLE via_permits_geo;
    END IF;
END
$mig$;
"""

_VIA_CREATE_TABLE = """
CREATE TABLE IF NOT EXISTS via_permits_geo (
    permit_id VARCHAR(40) PRIMARY KEY,
    d         DATE,
    etat      TEXT,
    g         geometry(Point, 2975)
)
"""
_VIA_CREATE_INDEX = (
    "CREATE INDEX IF NOT EXISTS ix_via_permits_geo_g ON via_permits_geo USING gist (g)")

# Fonction + trigger : via_permits_geo suit sitadel_permits ligne à ligne (autorisé & géolocalisé).
_VIA_TRIGGER_FN = """
CREATE OR REPLACE FUNCTION via_permits_geo_sync() RETURNS trigger AS $fn$
BEGIN
    -- DÉFENSIF (base partagée) : si la couche n'existe pas (une autre session l'a droppée), on ne casse
    -- JAMAIS l'écriture sur sitadel_permits. DELETE+INSERT (sans ON CONFLICT) : indépendant de la PK,
    -- donc robuste même si la table a été recréée sans contrainte unique par du code hérité.
    IF to_regclass('via_permits_geo') IS NULL THEN
        RETURN COALESCE(NEW, OLD);
    END IF;
    IF (TG_OP = 'DELETE') THEN
        DELETE FROM via_permits_geo WHERE permit_id = OLD.permit_id;
        RETURN OLD;
    END IF;
    DELETE FROM via_permits_geo WHERE permit_id = NEW.permit_id;
    IF NEW.geom IS NOT NULL AND NEW.date IS NOT NULL THEN
        INSERT INTO via_permits_geo (permit_id, d, etat, g)
        VALUES (NEW.permit_id, NEW.date::date, NEW.raw->>'etat', ST_Transform(NEW.geom, 2975));
    END IF;
    RETURN NEW;
END;
$fn$ LANGUAGE plpgsql
"""
_VIA_TRIGGER_DROP = "DROP TRIGGER IF EXISTS trg_via_permits_geo_sync ON sitadel_permits"
_VIA_TRIGGER_CREATE = """
CREATE TRIGGER trg_via_permits_geo_sync
    AFTER INSERT OR UPDATE OR DELETE ON sitadel_permits
    FOR EACH ROW EXECUTE FUNCTION via_permits_geo_sync()
"""

# Réconciliation plein : (ré)aligne la couche sur TOUT sitadel_permits (autorisés & géolocalisés).
_VIA_RESYNC_INSERT = """
INSERT INTO via_permits_geo (permit_id, d, etat, g)
SELECT permit_id, date::date, raw->>'etat', ST_Transform(geom, 2975)
FROM sitadel_permits WHERE geom IS NOT NULL AND date IS NOT NULL
ON CONFLICT (permit_id) DO UPDATE SET d = EXCLUDED.d, etat = EXCLUDED.etat, g = EXCLUDED.g
"""
_VIA_RESYNC_PRUNE = """
DELETE FROM via_permits_geo w
WHERE NOT EXISTS (SELECT 1 FROM sitadel_permits s
                 WHERE s.permit_id = w.permit_id AND s.geom IS NOT NULL AND s.date IS NOT NULL)
"""


def ensure_via_permits_geo(session: Session, resync: bool = True) -> dict:
    """OUTIL-PERMIS-FIX-1 (LOT 3) — garantit la couche de voisinage `via_permits_geo` et son TRIGGER de
    synchronisation (idempotent). Migre l'ancien snapshot sans PK, puis (resync=True) réaligne la couche
    sur tout `sitadel_permits` une fois. À exécuter UNE fois en prod (cf. COMMANDE DE RECONSTRUCTION du
    compte-rendu) ; ensuite le trigger entretient la couche tout seul à chaque mise à jour des permis."""
    for stmt in (_VIA_MIGRATE, _VIA_CREATE_TABLE, _VIA_CREATE_INDEX,
                 _VIA_TRIGGER_FN, _VIA_TRIGGER_DROP, _VIA_TRIGGER_CREATE):
        session.execute(text(stmt))
    session.commit()
    if resync:
        session.execute(text(_VIA_RESYNC_INSERT))
        session.execute(text(_VIA_RESYNC_PRUNE))
        session.commit()
    n = session.execute(text("SELECT count(*) FROM via_permits_geo")).scalar()
    return {"via_permits_geo": int(n or 0)}


# OUTIL-PERMIS-FIX-1 (LOT 2) — EMPRISE DE BÂTI MESURÉE par parcelle de permis PC (idu → m² de bâti
# réellement intersecté avec les empreintes BD TOPO `spatial_layers.kind='batiment'`). C'est LA mesure
# du dormant (« aucun bâtiment détecté » = emprise < 10 m²), vérifiée identique au contre-audit du
# relecteur (97441516A0419 → 253 m², 97441122A0103 → 133 m², 97442320A0048 → 188 m²). Seuls les PC
# peuvent être dormants → on ne mesure que leurs parcelles (borne le calcul).
_BATI_CREATE = """
CREATE TABLE IF NOT EXISTS parcel_bati_emprise (
    idu     VARCHAR(14) PRIMARY KEY,
    bati_m2 DOUBLE PRECISION NOT NULL
)
"""
_BATI_FILL = """
INSERT INTO parcel_bati_emprise (idu, bati_m2)
SELECT p.idu, coalesce(sum(ST_Area(ST_Intersection(p.geom_2975, bl.geom_2975))), 0)
FROM (SELECT DISTINCT c.idu FROM sitadel_permits s,
             jsonb_array_elements_text(s.idu_codes) c(idu) WHERE s.type = 'PC') pp
JOIN parcels p ON p.idu = pp.idu
LEFT JOIN spatial_layers bl ON bl.kind = 'batiment' AND ST_Intersects(p.geom_2975, bl.geom_2975)
GROUP BY p.idu
ON CONFLICT (idu) DO UPDATE SET bati_m2 = EXCLUDED.bati_m2
"""


def ensure_parcel_bati_emprise(session: Session) -> dict:
    """OUTIL-PERMIS-FIX-1 (LOT 2) — garantit et (re)remplit `parcel_bati_emprise` (emprise de bâti
    mesurée par parcelle de permis PC). À exécuter une fois en prod (cf. COMMANDE DE RECONSTRUCTION du
    compte-rendu), puis à chaque run M-VIA (le bâti et les parcelles de permis évoluent lentement)."""
    session.execute(text(_BATI_CREATE))
    session.execute(text(_BATI_FILL))
    session.commit()
    row = session.execute(text(
        "SELECT count(*) n, count(*) FILTER (WHERE bati_m2 >= 10) baties "
        "FROM parcel_bati_emprise")).mappings().first()
    return {"parcel_bati_emprise": int(row["n"] or 0), "baties": int(row["baties"] or 0)}

# Score SQL — miroir EXACT de viabilisation.compute_score (poids W_*).
_SCORE_SQL = f"""
  (CASE WHEN c100>=6 THEN {V.W_PERMIS} WHEN c100>=3 THEN 30 WHEN c100>=1 THEN 18
        WHEN c200>=3 THEN 8 ELSE 0 END)
+ (CASE WHEN voie10 AND bati30 THEN {V.W_FACADE} WHEN voie10 THEN 8 WHEN voie75 THEN 4 ELSE 0 END)
+ (CASE WHEN bati10 THEN {V.W_BATI} WHEN bati30 THEN 9 WHEN bati75 THEN 3 ELSE 0 END)
+ (CASE zone_fam WHEN 'U' THEN {V.W_ZONE} WHEN 'AU' THEN 13 WHEN 'A' THEN 4 ELSE 0 END)
"""

_BAND_SQL = (
    "CASE WHEN score>=70 THEN 'confirmee' WHEN score>=45 THEN 'probable' "
    "WHEN score>=25 THEN 'incertaine' ELSE 'lourde' END"
)

# Insertion par commune : signaux (sous-requêtes ST_DWithin index-friendly) → score → band.
_INSERT_COMMUNE = f"""
INSERT INTO parcel_viabilisation
  (idu, commune, zone_fam, c100, c200, c100_recent, c100_acheve,
   voie10, voie75, bati10, bati30, bati75, assainissement_zonage, score, band)
SELECT idu, commune, zone_fam, c100, c200, c100_recent, c100_acheve,
       voie10, voie75, bati10, bati30, bati75, assainissement_zonage,
       ({_SCORE_SQL}) AS score,
       ({_BAND_SQL.replace('score', '(' + _SCORE_SQL + ')')})
FROM (
  SELECT p.idu, p.commune, z.zone_fam,
    (SELECT count(*) FROM via_permits_geo w WHERE ST_DWithin(p.geom_2975,w.g,100)) c100,
    (SELECT count(*) FROM via_permits_geo w WHERE ST_DWithin(p.geom_2975,w.g,200)) c200,
    (SELECT count(*) FROM via_permits_geo w WHERE ST_DWithin(p.geom_2975,w.g,100) AND w.d>=make_date(:annee,1,1)) c100_recent,
    (SELECT count(*) FROM via_permits_geo w WHERE ST_DWithin(p.geom_2975,w.g,100) AND w.etat='6') c100_acheve,
    EXISTS(SELECT 1 FROM spatial_layers v WHERE v.kind='voirie' AND v.commune=p.commune AND ST_DWithin(p.geom_2975,v.geom_2975,10)) voie10,
    EXISTS(SELECT 1 FROM spatial_layers v WHERE v.kind='voirie' AND v.commune=p.commune AND ST_DWithin(p.geom_2975,v.geom_2975,75)) voie75,
    EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND b.commune=p.commune AND ST_DWithin(p.geom_2975,b.geom_2975,10)) bati10,
    EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND b.commune=p.commune AND ST_DWithin(p.geom_2975,b.geom_2975,30)) bati30,
    EXISTS(SELECT 1 FROM spatial_layers b WHERE b.kind='batiment' AND b.commune=p.commune AND ST_DWithin(p.geom_2975,b.geom_2975,75)) bati75,
    (SELECT za.subtype FROM spatial_layers za WHERE za.kind='zonage_assainissement'
       AND za.commune=p.commune AND ST_Intersects(p.geom_2975, za.geom_2975)
       ORDER BY CASE za.subtype WHEN 'collectif' THEN 0 ELSE 1 END LIMIT 1) assainissement_zonage
  FROM parcels p
  LEFT JOIN parcel_zone_plu z ON z.idu = p.idu
  WHERE p.commune = :commune AND p.geom_2975 IS NOT NULL
) s
ON CONFLICT (idu) DO UPDATE SET
  commune=EXCLUDED.commune, zone_fam=EXCLUDED.zone_fam, c100=EXCLUDED.c100, c200=EXCLUDED.c200,
  c100_recent=EXCLUDED.c100_recent, c100_acheve=EXCLUDED.c100_acheve, voie10=EXCLUDED.voie10,
  voie75=EXCLUDED.voie75, bati10=EXCLUDED.bati10, bati30=EXCLUDED.bati30, bati75=EXCLUDED.bati75,
  assainissement_zonage=EXCLUDED.assainissement_zonage,
  score=EXCLUDED.score, band=EXCLUDED.band, computed_at=now();
"""


def ilot_s3renr_note(session: Session) -> dict | None:
    """Note PV S3REnR au niveau ÎLE (les 24 postes sources ne sont pas géolocalisés en
    base : pas d'attribution par parcelle → message honnête d'îlot). Volet PV, hors 0-100."""
    row = session.execute(text(
        "SELECT count(*) n, count(*) FILTER (WHERE capa_dispo_mw<=0) sat, "
        "count(*) FILTER (WHERE capa_dispo_mw>0) dispo, count(geom) with_geom, "
        "max(source) src FROM grid_capacity")).mappings().first()
    if not row or not row["n"]:
        return None
    n, sat = row["n"], row["sat"]
    # M70 décision 2 — grid_capacity est actuellement un STUB (24 postes, capa_dispo_mw=0 fabriqué,
    # geom NULL). Affirmer « capacité NULLE » sur un 0 non mesuré est un FAUX POSITIF. Tant qu'aucune
    # vraie donnée n'existe (aucune capa positive ET aucune géométrie), on ne dit RIEN sur le PV.
    if row["dispo"] == 0 and row["with_geom"] == 0:
        return None
    if sat >= n:
        note = (f"Capacité d'accueil PV NULLE sur les {n} postes sources de La Réunion "
                "(S3REnR) → toute injection photovoltaïque est en file d'attente réseau.")
        statut = "saturee"
    else:
        note = (f"{n - sat}/{n} postes sources avec capacité d'accueil PV disponible (S3REnR).")
        statut = "partielle"
    return {"portee": "ile", "n_postes": n, "n_satures": sat, "statut": statut,
            "note": note, "source": row["src"],
            "disclaimer": "Volet PV — capacité réseau au niveau poste source (non géolocalisé "
                          "par parcelle). À confirmer auprès d'EDF SEI."}


def solaire_note(session: Session, idu: str) -> dict | None:
    """M75 — gisement solaire PVGIS d'une parcelle, en INFORMATION (jamais un signal de scoring).

    POINT DE CALCUL UNIQUE du libellé client (`note`) : la fiche ET les exports affichent CE texte,
    au mot près (exigence Vic — une donnée, un libellé). Le productible (kWh/kWc/an) est SOURCÉ PVGIS
    (modèle SARAH3, Commission européenne) donc affiché en Estimé avec sa réserve ; le `score_solaire`
    /100 (score LABUSE opaque) N'EST JAMAIS exposé. None si pas de donnée.
    """
    r = session.execute(text(
        "SELECT prod_spec_kwh_kwc, flag_topo_ombrage, flag_ombrage_vegetal "
        "FROM parcel_solar WHERE idu = :idu"), {"idu": idu}).mappings().first()
    if not r or r["prod_spec_kwh_kwc"] is None:
        return None
    prod = round(float(r["prod_spec_kwh_kwc"]))
    prod_approx = round(prod / 10) * 10           # « ~1 430 » : ordre de grandeur, pas une garantie
    # bornes qualitatives mesurées sur le parc (q25 1 329 · médiane 1 399 · q75 1 501 kWh/kWc/an) :
    # l'île entière est un bon gisement → 2 mots seulement, jamais de jauge ni de note sur 100.
    qualite = "très favorable" if prod >= 1500 else "favorable"
    ombrage = bool(r["flag_topo_ombrage"] or r["flag_ombrage_vegetal"])
    note = (f"Ensoleillement {qualite} à une installation solaire — productible estimé "
            f"~{prod_approx:,} kWh/kWc/an".replace(",", " ")
            + (" ; ombrage local à vérifier sur place" if ombrage else "")
            + " (modèle SARAH3, hors gradient côtier local).")
    return {"prod_kwh_kwc": prod, "qualite": qualite, "ombrage": ombrage,
            "note": note, "etat": "Estimé"}


def aper_note(session: Session, idu: str) -> dict | None:
    """M75 — obligation APER (ombrières PV, grand parking > 1 500 m²) sur la parcelle. INFORMATION.

    POINT DE CALCUL UNIQUE du libellé client (`note`) : la fiche ET les exports affichent CE texte,
    au mot près. Loi 2023-175 art. 40 + décret 2024-1023 ; donnée refiltrée au seuil légal 1 500 m²
    (scripts/m75_refiltre_parkings_aper_1500.sql). On dit « POTENTIELLEMENT concerné », JAMAIS
    « soumis à » (exemptions possibles) ; `equipe` OSM incomplet → jamais « à équiper ». None sinon.
    """
    # M90 — garde défensive au POINT UNIQUE : sur une base sans la couche `parkings_aper` (gisement
    # M75 optionnel, OSM/ODbL « sur demande » ; data-gap, base de test), on ne plante pas une fiche en
    # 500 (panne d'environnement déguisée en régression). Table absente → None (aucune obligation
    # affichée), cohérent avec le « None sinon » de cette fonction. L'absence d'une COLONNE resterait
    # levée (régression de schéma non masquée).
    if session.execute(text("SELECT to_regclass('parkings_aper')")).scalar() is None:
        return None
    r = session.execute(text(
        "SELECT max(surface_m2) surf, min(echeance) ech, bool_or(equipe) eq "
        "FROM parkings_aper WHERE idus @> to_jsonb(CAST(:idu AS text)) AND tranche IS NOT NULL"),
        {"idu": idu}).mappings().first()
    if not r or r["surf"] is None:
        return None
    surf = int(round(float(r["surf"]) / 100) * 100)
    ech = r["ech"].strftime("%d/%m/%Y") if r["ech"] else None
    note = (f"Grand parking (~{surf:,} m²) sur cette parcelle".replace(",", " ")
            + " — potentiellement concerné par l'obligation d'ombrières photovoltaïques (loi APER, "
            + "décret 2024-1023 ; obligation au-delà de 1 500 m²)"
            + (f", échéance {ech}" if ech else "")
            + ". Surface mesurée (OpenStreetMap)."
            + (" Une installation d'ombrières est déjà cartographiée (OSM)." if r["eq"] else ""))
    return {"surface_m2": surf, "echeance": ech, "equipe": bool(r["eq"]),
            "note": note, "etat": "Sourcé"}


def build_viabilisation(session: Session, communes: list[str] | None = None) -> dict:
    """Construit/rafraîchit parcel_viabilisation. `communes=None` → les 24."""
    t0 = time.time()
    for stmt in _DDL.strip().split(";\n"):
        if stmt.strip():
            session.execute(text(stmt))
    # OUTIL-PERMIS-FIX-1 (LOT 3) — via_permits_geo est désormais une couche MAINTENUE PAR TRIGGER (plus
    # un snapshot DROP+CREATE qui prenait du retard). On garantit table+trigger et on réaligne le plein.
    ensure_via_permits_geo(session, resync=True)
    # OUTIL-PERMIS-FIX-1 (LOT 2) — emprise de bâti mesurée (définition unique du dormant) rafraîchie.
    ensure_parcel_bati_emprise(session)
    session.commit()

    if communes is None:
        communes = [r[0] for r in session.execute(text(
            "SELECT DISTINCT commune FROM parcels WHERE geom_2975 IS NOT NULL ORDER BY 1")).all()]

    # M-C (F5) : les compteurs mesurent CE RUN, pas toute la table. Avant : per_commune faisait un
    # count(*) de la tranche commune (rows d'anciens runs inclus), `total += 0` était mort, et total
    # était un count(*) GLOBAL (toutes communes, même hors de ce run). On lit le rowcount de l'INSERT
    # ... ON CONFLICT DO UPDATE = lignes réellement insérées/mises à jour par ce run pour la commune.
    total = 0
    per_commune = {}
    for c in communes:
        res = session.execute(text(_INSERT_COMMUNE), {"commune": c, "annee": V.ANNEE_RECENTE})
        n = res.rowcount if res.rowcount is not None and res.rowcount >= 0 else 0
        session.commit()
        per_commune[c] = n
        total += n
    return {"n": total, "communes": len(communes), "per_commune": per_commune,
            "duree_s": round(time.time() - t0, 1)}
