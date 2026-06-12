"""Audit pull (Lot A) — auditer un terrain À LA DEMANDE, par 3 chemins :

  1. référence cadastrale (commune + section + numéro),
  2. adresse (géocodage BAN → point → parcelle),
  3. polygone dessiné sur la carte.

Tous convergent vers UN SEUL code path : résolution de la (des) parcelle(s) via l'API Carto
IGN (cadastre PCI, déjà branchée), insertion au référentiel avec `origine='audit'`, puis
LA MÊME cascade/scoring que la découverte (`evaluate_parcels`). Aucune logique d'évaluation
dupliquée — la parcelle auditée devient une parcelle comme les autres.

Garde-fou commune : seule la commune pilote (Saint-Paul) a ses couches ingérées ; auditer
ailleurs ne produirait que des UNKNOWN. Hors pilote → message propre, jamais de crash ni
d'évaluation trompeuse. Le contrôle se fait AVANT tout appel réseau quand l'INSEE est connu.
"""
from __future__ import annotations

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

from . import config, models
from .connectors.cadastre import CadastreConnector, ingest_parcels, parse_parcelles

BAN_URL = "https://api-adresse.data.gouv.fr/search/"


class AuditResult(dict):
    """Résultat d'un audit (sérialisable tel quel par l'API). `ok=False` porte `error`+`message`."""


def _pilot() -> tuple[str, str]:
    s = config.get_settings()
    return s.pilot_commune_insee, s.pilot_commune_name


def _hors_commune(insee: str | None, ville: str | None = None) -> AuditResult:
    _, name = _pilot()
    lieu = ville or (f"commune {insee}" if insee else "cette commune")
    return AuditResult(
        ok=False, error="commune_non_couverte", insee=insee,
        message=f"{lieu} non couverte — LA BUSE est en phase pilote sur {name} uniquement.",
    )


def _evaluate(session: Session, parcels: list[dict]) -> AuditResult:
    """Ingestion (origine='audit') + évaluation des parcelles résolues. Renvoie le résultat
    orienté fiche (idu principal = la plus grande emprise)."""
    _, name = _pilot()
    run = models.IngestionRun(commune=name, status="ok", parcels_count=len(parcels))
    session.add(run)
    session.flush()
    ingest_parcels(session, parcels, name, run.id, origine="audit")

    idus = [p["idu"] for p in parcels]
    ids = [r[0] for r in session.execute(
        text("SELECT id FROM parcels WHERE idu = ANY(:idus)"), {"idus": idus}).all()]

    from .cascade import evaluate_parcels
    outs = {o.idu: o for o in evaluate_parcels(ids, session, persist=True)}
    # Potentiel résiduel (Lot B) : caché aussi pour la parcelle auditée → visible au filtre.
    try:
        from .faisabilite.residuel import compute_residuel_batch
        compute_residuel_batch(session, ids)
    except Exception:  # noqa: BLE001 - n'empêche jamais l'audit
        pass

    primary = max(parcels, key=lambda p: _surface(session, p["idu"]))["idu"]
    o = outs.get(primary)
    return AuditResult(
        ok=True, idu=primary, idus=idus, n=len(idus), origine="audit", cached=False,
        status=o.status if o else None,
        opportunity_score=o.opportunity.score if o else None,
        completeness_score=o.completeness.score if o else None,
    )


def _surface(session: Session, idu: str) -> float:
    return float(session.execute(
        text("SELECT coalesce(surface_m2, 0) FROM parcels WHERE idu = :i"), {"i": idu}).scalar() or 0.0)


def _cached(session: Session, idu: str) -> AuditResult | None:
    """Réponse immédiate (< 5 s, sans réseau) si la parcelle est déjà évaluée."""
    row = session.execute(text(
        """SELECT p.idu, p.origine, e.status, e.opportunity_score, e.completeness_score
           FROM parcels p JOIN parcel_evaluations e ON e.parcel_id = p.id
           WHERE p.idu = :i ORDER BY e.evaluated_at DESC LIMIT 1"""), {"i": idu}).mappings().first()
    if not row:
        return None
    return AuditResult(
        ok=True, idu=row["idu"], idus=[row["idu"]], n=1, cached=True,
        origine=row["origine"] or "referentiel", status=row["status"],
        opportunity_score=row["opportunity_score"], completeness_score=row["completeness_score"])


# ───────────────────────────── 1. par référence cadastrale ─────────────────────────────

def audit_by_reference(session: Session, section: str, numero: str,
                       code_insee: str | None = None) -> AuditResult:
    insee, name = _pilot()
    code_insee = (code_insee or insee).strip()
    if code_insee != insee:
        return _hors_commune(code_insee)
    section = (section or "").strip().upper()
    numero = (numero or "").strip().lstrip("0") or "0"
    if not section or not numero.isdigit():
        return AuditResult(ok=False, error="entree_invalide",
                           message="Référence incomplète : indiquez une section (ex. BV) et un numéro.")

    # Cache : déjà au référentiel (numéro stocké zéro-padé OU brut) → pas de réseau.
    hit = session.execute(text(
        """SELECT idu FROM parcels WHERE commune = :c AND upper(section) = :s
           AND (numero = :n OR numero = lpad(:n, 4, '0')) LIMIT 1"""),
        {"c": name, "s": section, "n": numero}).scalar()
    if hit:
        c = _cached(session, hit)
        if c:
            return c

    try:
        # API Carto exige le numéro sur 4 chiffres (zéro-padé) ; on garde `numero` brut pour
        # le filtre/affichage.
        fc = CadastreConnector().fetch_by_section(code_insee, section, numero.zfill(4))
    except Exception as exc:  # noqa: BLE001 — réseau/API Carto
        return AuditResult(ok=False, error="source_indisponible",
                           message=f"Cadastre (API Carto IGN) injoignable : {type(exc).__name__}.")
    parcels = [p for p in parse_parcelles(fc)
               if str(p.get("numero") or "").lstrip("0") == numero]
    if not parcels:
        return AuditResult(ok=False, error="introuvable",
                           message=f"Parcelle {section} {numero} introuvable au cadastre de {name}.")
    return _evaluate(session, parcels)


# ───────────────────────────── 2. par adresse (BAN) ─────────────────────────────

def audit_by_address(session: Session, q: str) -> AuditResult:
    insee, name = _pilot()
    q = (q or "").strip()
    if len(q) < 3:
        return AuditResult(ok=False, error="entree_invalide", message="Adresse trop courte.")
    ban, last_exc = None, None
    for attempt in range(2):  # BAN rate-limite parfois : une 2e tentative suffit
        try:
            with httpx.Client(timeout=config.get_settings().http_timeout_s,
                              headers={"User-Agent": "LA-BUSE/0.1 (+audit)"}) as c:
                r = c.get(BAN_URL, params={"q": q, "limit": 1})
                r.raise_for_status()
                ban = r.json()
            break
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
    if ban is None:
        return AuditResult(ok=False, error="source_indisponible",
                           message=f"Géocodage (BAN) injoignable : {type(last_exc).__name__}.")
    feats = ban.get("features") or []
    if not feats:
        return AuditResult(ok=False, error="introuvable", message=f"Adresse « {q} » non trouvée.")
    props = feats[0].get("properties", {})
    lon, lat = feats[0]["geometry"]["coordinates"]
    if props.get("citycode") != insee:
        return _hors_commune(props.get("citycode"), props.get("city"))

    try:
        fc = CadastreConnector().fetch_by_geom({"type": "Point", "coordinates": [lon, lat]})
    except Exception as exc:  # noqa: BLE001
        return AuditResult(ok=False, error="source_indisponible",
                           message=f"Cadastre (API Carto IGN) injoignable : {type(exc).__name__}.")
    parcels = [p for p in parse_parcelles(fc) if (p.get("code_insee") or insee) == insee]
    if not parcels:
        return AuditResult(ok=False, error="introuvable",
                           message=f"Aucune parcelle cadastrale à l'adresse « {props.get('label', q)} ».")
    res = _evaluate(session, parcels)
    res["adresse"] = props.get("label")
    return res


# ───────────────────────────── 3. par polygone dessiné ─────────────────────────────

def audit_by_polygon(session: Session, geometry: dict, max_parcels: int = 25) -> AuditResult:
    insee, name = _pilot()
    if not isinstance(geometry, dict) or geometry.get("type") not in ("Polygon", "MultiPolygon"):
        return AuditResult(ok=False, error="entree_invalide", message="Polygone invalide.")
    try:
        fc = CadastreConnector().fetch_by_geom(geometry)
    except Exception as exc:  # noqa: BLE001
        return AuditResult(ok=False, error="source_indisponible",
                           message=f"Cadastre (API Carto IGN) injoignable : {type(exc).__name__}.")
    parsed = parse_parcelles(fc)
    in_pilot = [p for p in parsed if (p.get("code_insee") or insee) == insee]
    if not in_pilot:
        other = next((p.get("code_insee") for p in parsed if p.get("code_insee")), None)
        return _hors_commune(other) if parsed else AuditResult(
            ok=False, error="introuvable", message="Aucune parcelle cadastrale dans la zone dessinée.")
    if len(in_pilot) > max_parcels:
        return AuditResult(ok=False, error="zone_trop_large",
                           message=f"{len(in_pilot)} parcelles dans la zone — affinez le tracé "
                                   f"(maximum {max_parcels}).")
    return _evaluate(session, in_pilot)
