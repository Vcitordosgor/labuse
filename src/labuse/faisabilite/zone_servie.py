"""ZONE-1 — LA résolution de zone PLU d'une parcelle, et la garde de lecture du résiduel.

Deux moteurs divergeaient (audit EXPORTS, docs/audit-2026-09/EXPORTS/DONNEES-RAPPORT.md,
chapitre A3/transverse) : l'écran lit la zone DOMINANTE PAR SURFACE (`parcel_zone_plu`,
bâtie par api/tiles.build_parcel_zone_plu) quand la faisabilité prenait la zone CONTENANT
LE CENTROÏDE (`_CTX` de faisabilite/db.py) — verdicts en miroir sur toute parcelle à
cheval (97416000DY0106 servie « 27-31 logements » en zone N ; 97411000AV0110 « rien à
construire » en dominante Uh).

Ici : UNE fonction, `zone_dominante`, la dominante par surface — la même que l'écran
(lecture de `parcel_zone_plu` quand la table existe, calcul identique sinon) — avec le
drapeau `a_cheval` (aucune zone n'atteint 90 % de la surface) et la liste des parts.
Point d'appel : `faisabilite.db.parcel_context` ; tout autre lecteur de zone passe par
`parcel_zone_plu` (même source) ou par cette fonction.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from sqlalchemy import text
from sqlalchemy.orm import Session

#: en deçà de cette part, la zone dominante ne « résume » plus la parcelle → drapeau.
SEUIL_A_CHEVAL_PCT = 90.0
FAMILLES_CONSTRUCTIBLES = ("U", "AU")


@dataclass(frozen=True)
class ZoneServie:
    zone: str | None                 # code court dominant (« U1a », « Uh », « N ») — celui de l'écran
    zone_fam: str | None             # U / AU / A / N / autre
    a_cheval: bool                   # aucune zone ≥ SEUIL_A_CHEVAL_PCT
    parts: list = field(default_factory=list)   # [{zone, fam, pct}] tri pct DESC (vide si non calculé)
    pct_constructible: float | None = None      # somme des parts U/AU (None si parts non calculées)
    source: str = "aucune"           # 'parcel_zone_plu' | 'calcul' | 'aucune'


# Même extraction de code court et même dérivation de famille que build_parcel_zone_plu
# (api/tiles.py, z0/z CTE) : 1er token de attrs->>'libelle' (source fiable), repli name.
_TOK = ("COALESCE(NULLIF(rtrim(split_part(btrim(z.attrs->>'libelle'), ' ', 1), ':'), ''), "
        "rtrim(split_part(btrim(z.name), ' ', 1), ':'))")
_FAM = ("CASE WHEN z.subtype ILIKE 'AU%' THEN 'AU' WHEN z.subtype ILIKE 'U%' THEN 'U' "
        "WHEN z.subtype = 'A' THEN 'A' WHEN z.subtype = 'N' THEN 'N' ELSE 'autre' END")

# Sonde bon marché (index gist, pas d'aire) : combien de codes de zone distincts touchent
# la parcelle ? 1 seul → pas d'aire à calculer, la dominante est entière.
_N_ZONES = text(f"""
SELECT count(DISTINCT {_TOK}) AS n, min({_TOK}) AS zone, min({_FAM}) AS fam
FROM spatial_layers z, (SELECT geom_2975 AS g FROM parcels WHERE id = :pid) p
WHERE z.kind = 'plu_gpu_zone' AND ST_Intersects(z.geom_2975, p.g)
""")

# Parts par surface d'intersection — uniquement quand la sonde voit > 1 zone.
_PARTS = text(f"""
WITH p AS (SELECT geom_2975 AS g, ST_Area(geom_2975) AS a FROM parcels WHERE id = :pid)
SELECT {_TOK} AS zone, {_FAM} AS fam,
       round((100 * sum(ST_Area(ST_Intersection(ST_MakeValid(z.geom_2975), p.g)))
              / NULLIF((SELECT a FROM p), 0))::numeric, 1) AS pct
FROM spatial_layers z, p
WHERE z.kind = 'plu_gpu_zone' AND ST_Intersects(z.geom_2975, p.g)
GROUP BY 1, 2 HAVING sum(ST_Area(ST_Intersection(ST_MakeValid(z.geom_2975), p.g))) > 0
ORDER BY pct DESC
""")

_TABLE_ECRAN = text("""
SELECT zp.zone_lib, zp.zone_fam FROM parcel_zone_plu zp
JOIN parcels p ON p.idu = zp.idu WHERE p.id = :pid
""")


def _table_ecran_existe(session: Session) -> bool:
    return bool(session.execute(text(
        "SELECT to_regclass('parcel_zone_plu') IS NOT NULL")).scalar())


def zone_dominante(session: Session, parcel_id: int) -> ZoneServie:
    """LA zone PLU de la parcelle — dominante par surface, LA MÊME que l'écran.

    Lit `parcel_zone_plu` (source de l'écran/tuiles/filtres) quand la table existe ;
    sinon calcule la dominante avec la même règle. Le drapeau `a_cheval` est posé quand
    aucune zone n'atteint SEUIL_A_CHEVAL_PCT de la surface (parts calculées seulement si
    plus d'une zone touche la parcelle — la sonde _N_ZONES évite l'aire dans le cas
    courant, y compris pendant les runs batch)."""
    ecran = (session.execute(_TABLE_ECRAN, {"pid": parcel_id}).one_or_none()
             if _table_ecran_existe(session) else None)

    probe = session.execute(_N_ZONES, {"pid": parcel_id}).one_or_none()
    n = int(probe.n or 0) if probe else 0
    if n <= 1:
        zone = (ecran.zone_lib if ecran else None) or (probe.zone if probe else None)
        fam = (ecran.zone_fam if ecran else None) or (probe.fam if probe else None)
        if zone is None:
            return ZoneServie(None, None, False, [], None, "aucune")
        return ZoneServie(zone, fam, False,
                          [{"zone": zone, "fam": fam, "pct": 100.0}],
                          100.0 if fam in FAMILLES_CONSTRUCTIBLES else 0.0,
                          "parcel_zone_plu" if ecran else "calcul")

    parts = [{"zone": r.zone, "fam": r.fam, "pct": float(r.pct)}
             for r in session.execute(_PARTS, {"pid": parcel_id})]
    if not parts:
        return ZoneServie(None, None, False, [], None, "aucune")
    # La dominante SERVIE reste celle de l'écran quand la table est là (jamais deux vérités) ;
    # le calcul ne prime que si la table est absente (test, parcelle née après la bascule).
    if ecran and ecran.zone_lib:
        zone, fam = ecran.zone_lib, ecran.zone_fam
        source = "parcel_zone_plu"
    else:
        zone, fam, source = parts[0]["zone"], parts[0]["fam"], "calcul"
    dominante_pct = next((p["pct"] for p in parts if p["zone"] == zone), parts[0]["pct"])
    pct_constructible = round(sum(p["pct"] for p in parts
                                  if p["fam"] in FAMILLES_CONSTRUCTIBLES), 1)
    return ZoneServie(zone, fam, dominante_pct < SEUIL_A_CHEVAL_PCT,
                      parts, pct_constructible, source)


def garde_sdp_residuelle(sdp: float | None, zone_fam: str | None,
                         zone: str | None = None) -> tuple[float | None, str | None]:
    """ZONE-1 pt2 — garde DE LECTURE : en zone dominante A ou N, la SDP résiduelle servie
    vaut 0 PAR RÈGLE, avec la cause `zone_non_constructible:<zone>`. Le run n'est pas
    recalculé (le chiffre stocké suivra à la prochaine bascule) ; la garde s'applique à
    l'écran comme aux exports. Renvoie (valeur_servie, cause | None)."""
    if sdp is None:
        return None, None
    if zone_fam in ("A", "N"):
        return 0.0, f"zone_non_constructible:{zone or zone_fam}"
    return float(sdp), None


def zone_fam_ecran(session: Session, idu: str) -> tuple[str | None, str | None]:
    """(zone_fam, zone_lib) de l'ÉCRAN (`parcel_zone_plu`) pour un IDU — lecture bon marché
    pour la garde pt2 aux points de service. (None, None) si table absente ou parcelle inconnue."""
    if not _table_ecran_existe(session):
        return None, None
    r = session.execute(text(
        "SELECT zone_fam, zone_lib FROM parcel_zone_plu WHERE idu = :idu"),
        {"idu": idu}).one_or_none()
    return (r.zone_fam, r.zone_lib) if r else (None, None)


def ligne_residuel_gardee(line: dict, zone_fam: str | None, zone: str | None) -> dict:
    """Réécriture DE LECTURE de la ligne servie `residuel_socle` quand la zone dominante est
    A/N : le chiffre du run (calculé sous l'ancienne zone du centroïde) ne doit plus sortir.
    Copie modifiée ; la ligne d'origine (dryrun) n'est pas touchée."""
    _, cause = garde_sdp_residuelle(1.0, zone_fam, zone)   # 1.0 : sonde — seul `cause` compte
    if cause is None:
        return line
    out = dict(line)
    out["result"] = "SOFT_FLAG"
    out["severity"] = "INFO"
    out["weight_applied"] = 0.0
    out["detail"] = (f"SDP résiduelle servie : 0 m² — {cause} (zone dominante « {zone} » non "
                     "constructible ; le chiffre du run sera recalculé à la prochaine bascule).")
    return out


def libelle_a_cheval(parts: list) -> str:
    """Phrase servie (fiche, bilan, exports) quand la parcelle est à cheval."""
    detail = " + ".join(f"« {p['zone']} » {p['pct']:g} %" for p in parts)
    pct_c = round(sum(p["pct"] for p in parts if p["fam"] in FAMILLES_CONSTRUCTIBLES), 1)
    return (f"Parcelle à cheval sur plusieurs zones PLU ({detail}) — capacité calculée "
            f"sur la seule portion constructible (~{pct_c:g} % de la surface).")
