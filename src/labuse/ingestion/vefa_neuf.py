"""SECTEUR-2 (T4) + SECTEUR-2b (U1) — couche « Prix du logement neuf (VEFA acté) », aplat par COMMUNE.

DIAGNOSTIC (rendu au compte-rendu, préalable au code) — ce que DVF porte réellement sur le VEFA au 974 :
  · fenêtre 36 mois glissants : ~993 mutations VEFA, quasi 100 % APPARTEMENTS (VEFA neuf = collectif) ;
  · champs présents : `type_local` (appartement/maison) et `surface_reelle_bati` (souvent, pas toujours) ;
  · champ ABSENT : le NOMBRE DE PIÈCES — il n'existe dans AUCUNE table DVF au 974 (ni colonne, ni `raw`)
    → la « médiane par taille T2/T3/T4 » est IMPOSSIBLE (absence honnête, jamais extrapolée) ;
  · ECLN (SDES) = métropole seule, N/A DOM → aucun STOCK/écoulement servi (jamais extrapolé) ;
  · en FACE, Sitadel donne l'OFFRE ENGAGÉE (logements collectifs autorisés) = ce qui arrive.
  · 7 communes atteignent 10 ventes VEFA AVEC un prix calculable (peintes) ; les 17 autres = HACHURE.
  · RETOURS-11 C3 (mesuré 09/2026) : 988 mutations VEFA sur 36 mois, mais SEULES 315 (32 %) portent
    `surface_reelle_bati` — à l'acte VEFA le bâti n'est pas construit, la surface réelle est vide. Le
    filtre `bati > 0` élimine donc 68 % des ventes. DVF au 974 (dvf_mutations_parcelle) NE porte PAS la
    surface Carrez des lots → aucun moyen de récupérer le prix des 673 restantes (jamais inventé). La
    correction porte sur l'HONNÊTETÉ de la hachure (dire le volume réel, pas « moins de 10 ventes »),
    pas sur un déblocage impossible faute de donnée amont.

La couche réutilise le plombing des aplats commune (spatial_layers `kind='vefa_neuf'`, servie par
`/map/layers.geojson`). La TRANCHE DE PRIX (ou 'sous_seuil') voyage dans `subtype` ; le détail dans `attrs`.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .dvf_marche import NEUF_VEFA_FENETRE_ANS, neuf_vefa_commune

# Fenêtre glissante de la couche VEFA, en MOIS (affichée dans le « i »). RETOURS-11F M2 : 60 mois = 5 ans,
# alignée sur `neuf_vefa_commune` (NEUF_VEFA_FENETRE_ANS=5) — un seul moteur, une seule fenêtre.
FENETRE_MOIS = NEUF_VEFA_FENETRE_ANS * 12
# RETOURS-11F M1 — le SEUIL vient du profil `neuf_vefa` (source unique, comme la fiche et le comparateur) :
# la carte ne peut pas hachurer à 10 pendant que la fiche sert une médiane dès 8. Un seuil, un endroit.
from ..marche_service import neuf_vefa_seuil as _neuf_vefa_seuil  # noqa: E402
SEUIL_VEFA_AFFICHAGE = _neuf_vefa_seuil()
OFFRE_SITADEL_MOIS = 24          # offre engagée = logements collectifs autorisés sur 24 mois
_VEFA = "nature_mutation = 'Vente en l''état futur d''achèvement'"

# Tranches de prix €/m² bâti neuf (calées sur la plage VEFA réunionnaise ~4 000–6 000 €/m²) → subtype.
TRANCHES = [(4000, "moins_4000"), (4500, "4000_4500"), (5000, "4500_5000"),
            (5500, "5000_5500"), (float("inf"), "5500_plus")]
TRANCHE_LIBELLE = {
    "moins_4000": "< 4 000 €/m²", "4000_4500": "4 000–4 500 €/m²", "4500_5000": "4 500–5 000 €/m²",
    "5000_5500": "5 000–5 500 €/m²", "5500_plus": "≥ 5 500 €/m²",
    "sous_seuil": f"moins de {SEUIL_VEFA_AFFICHAGE} ventes",
}


def _tranche(prix: float) -> str:
    for borne, cle in TRANCHES:
        if prix < borne:
            return cle
    return "5500_plus"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def _offre_sitadel(session: Session, commune: str | None) -> dict:
    """OFFRE ENGAGÉE — logements COLLECTIFS (nb_lgt ≥ 2) autorisés sur 24 mois (Sitadel = autorisations
    d'urbanisme par définition). « Ce qui arrive en face » du marché VEFA acté. Comptes SQL."""
    if not commune:
        return {"logements": None, "permis": None}
    r = session.execute(text(
        f"SELECT coalesce(sum((s.raw->>'nb_lgt')::int), 0) lgt, count(*) n FROM sitadel_permits s "
        f"WHERE s.commune = :c AND s.date >= (now() - interval '{OFFRE_SITADEL_MOIS} months') "
        f"  AND (s.raw->>'nb_lgt') ~ '^[0-9]+$' AND (s.raw->>'nb_lgt')::int >= 2"),
        {"c": commune}).mappings().first()
    return {"logements": int(r["lgt"] or 0), "permis": int(r["n"] or 0)}


def build_vefa_neuf(session: Session, *, commit: bool = True, log=lambda *_: None) -> dict:
    """Reconstruit l'aplat `vefa_neuf` — UN item par commune (les 24), peinte (tranche de prix) OU
    HACHURÉE (subtype 'sous_seuil', « moins de 10 ventes »). Jamais une commune absente. Idempotent."""
    geo = json.loads((_repo_root() / "frontend" / "public" / "communes974.geojson").read_text("utf-8"))
    dmax = session.execute(text(
        f"SELECT to_char(max(date_mutation), 'YYYY-MM-DD') FROM dvf_mutations_parcelle "
        f"WHERE {_VEFA} AND date_mutation >= (now() - interval '{FENETRE_MOIS} months')::date")).scalar()
    millesime = (f"VEFA DVF — {FENETRE_MOIS} mois glissants (dernière vente {dmax})" if dmax
                 else f"VEFA DVF — {FENETRE_MOIS} mois glissants")
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'vefa_neuf'"))
    n_peintes = hachurees = 0
    for feat in geo["features"]:
        insee = feat["properties"].get("code")
        commune = feat["properties"].get("nom") or feat["properties"].get("name")
        if not insee:
            continue
        v = neuf_vefa_commune(session, insee)
        prix, n = v.get("mediane_prix_m2_bati"), v.get("n") or 0
        n_total = v.get("n_total") or n     # RETOURS-11 C3 — volume RÉEL de VEFA (avant filtre surface)
        offre = _offre_sitadel(session, commune)
        peinte = bool(prix) and n >= SEUIL_VEFA_AFFICHAGE
        if peinte:
            cle = _tranche(float(prix))
            name = f"{commune} · {int(prix)} €/m² · {int(n)} ventes VEFA"
            n_peintes += 1
        else:
            cle = "sous_seuil"
            # RETOURS-11 C3 — hachure HONNÊTE : « peu de ventes » seulement si le volume est vraiment faible.
            # Si le marché VEFA existe (≥ seuil) mais que peu de ventes portent une surface bâtie (à l'acte
            # VEFA le bâti n'est pas construit → surface souvent vide, non récupérable faute de Carrez au 974),
            # on le DIT au lieu de laisser croire « moins de 10 ventes ».
            if n_total >= SEUIL_VEFA_AFFICHAGE:
                name = (f"{commune} · {int(n_total)} ventes VEFA · prix calculable sur {int(n)} "
                        f"(surface bâtie souvent absente à l'acte)")
            else:
                name = f"{commune} · moins de {SEUIL_VEFA_AFFICHAGE} ventes VEFA ({int(n_total)})"
            hachurees += 1
        attrs = {"insee": insee, "prix_m2_neuf": int(prix) if peinte else None, "n_ventes": int(n),
                 "n_ventes_vefa_total": int(n_total),   # volume réel (avant filtre surface)
                 "maille": "commune", "fenetre_mois": FENETRE_MOIS, "peinte": peinte,
                 "tranche": TRANCHE_LIBELLE[cle], "seuil": SEUIL_VEFA_AFFICHAGE,
                 "offre_engagee_logements": offre["logements"], "offre_engagee_permis": offre["permis"],
                 "millesime": millesime, "stock": None,
                 "source": "geo-DVF (mutations VEFA, DGFiP) · Sitadel (offre engagée) — ECLN non couverte outre-mer"}
        session.execute(text(
            "INSERT INTO spatial_layers (kind, subtype, name, commune, geom, attrs) VALUES "
            "('vefa_neuf', :st, :nom, :c, ST_GeomFromGeoJSON(:g), CAST(:a AS jsonb))"),
            {"st": cle, "nom": name, "c": commune, "g": json.dumps(feat["geometry"]), "a": json.dumps(attrs)})
    if commit:
        session.commit()
    log(f"vefa_neuf : {n_peintes} communes peintes, {hachurees} hachurées (< {SEUIL_VEFA_AFFICHAGE} ventes)")
    return {"communes": n_peintes, "hachurees": hachurees, "millesime": dmax}


def detail_commune(session: Session, insee: str) -> dict:
    """SECTEUR-2b (U1) — le panneau de détail d'une commune, TOUT depuis les moteurs existants, CHAQUE
    chiffre avec son n. Sous le seuil par segment : le chiffre est ABSENT (jamais extrapolé)."""
    commune = session.execute(text(
        "SELECT commune FROM parcels WHERE substring(idu,1,5) = :i LIMIT 1"), {"i": insee}).scalar()
    v = neuf_vefa_commune(session, insee)           # médiane €/m² + n (36 mois, prix calculable)
    med, n = v.get("mediane_prix_m2_bati"), int(v.get("n") or 0)
    n_total = int(v.get("n_total") or n)            # RETOURS-11 C3 — volume VEFA réel (avant filtre surface)

    # TENDANCE 12 mois vs période : médiane des 12 derniers mois vs médiane des 36 mois (si n suffisant).
    # Le pivot « 12 derniers mois » est calé sur la DERNIÈRE VENTE observée (pas sur l'horloge système) —
    # robuste à un millésime DVF en retard, et honnête (« les 12 derniers mois de données »).
    tr = session.execute(text(f"""
        WITH bornes AS (
          SELECT max(date_mutation) dmax FROM dvf_mutations_parcelle
          WHERE code_commune = :i AND {_VEFA}
            AND date_mutation >= (now() - interval '{FENETRE_MOIS} months')::date),
        mut AS (
          SELECT id_mutation, max(valeur_fonciere) v, sum(coalesce(surface_reelle_bati,0)) b,
                 max(date_mutation) d
          FROM dvf_mutations_parcelle
          WHERE code_commune = :i AND {_VEFA}
            AND date_mutation >= (now() - interval '{FENETRE_MOIS} months')::date
          GROUP BY id_mutation)
        SELECT percentile_cont(0.5) WITHIN GROUP (ORDER BY v/b)
                 FILTER (WHERE b>0 AND v>1000 AND v/b BETWEEN 50 AND 20000
                         AND d >= ((SELECT dmax FROM bornes) - interval '12 months')) m12,
               count(*) FILTER (WHERE b>0 AND v>1000 AND v/b BETWEEN 50 AND 20000
                         AND d >= ((SELECT dmax FROM bornes) - interval '12 months')) n12
        FROM mut"""), {"i": insee}).mappings().first()
    med12, n12 = (round(float(tr["m12"])) if tr and tr["m12"] else None), int((tr or {}).get("n12") or 0)
    tendance = None
    if med and med12 and n12 >= 5:
        pct = round(100.0 * (med12 - med) / med)
        tendance = {"pct": pct, "n_12m": n12, "sens": "hausse" if pct >= 2 else "baisse" if pct <= -2 else "stable"}

    # RÉPARTITION appartements / maisons (type_local) — les deux comptés, jamais deviné.
    rep = session.execute(text(f"""
        SELECT count(*) FILTER (WHERE type_local ILIKE '%%appart%%') n_appt,
               count(*) FILTER (WHERE type_local ILIKE '%%maison%%') n_maison
        FROM dvf_mutations_parcelle
        WHERE code_commune = :i AND {_VEFA}
          AND date_mutation >= (now() - interval '{FENETRE_MOIS} months')::date"""),
        {"i": insee}).mappings().first()

    return {
        "insee": insee, "commune": commune,
        "peinte": bool(med) and n >= SEUIL_VEFA_AFFICHAGE,
        "mediane_eur_m2": med, "n_ventes": n, "n_ventes_vefa_total": n_total,
        "fenetre_mois": FENETRE_MOIS, "seuil": SEUIL_VEFA_AFFICHAGE,
        "tendance_12m": tendance,   # None si n insuffisant (jamais une tendance inventée)
        "repartition": {"appartements": int(rep["n_appt"] or 0), "maisons": int(rep["n_maison"] or 0)},
        # médiane par TAILLE (T2/T3/T4) : INDISPONIBLE — DVF au 974 ne porte pas le nombre de pièces.
        "par_taille": {"disponible": False,
                       "motif": "le nombre de pièces n'est pas porté par DVF au 974 — médiane par taille "
                                "(T2/T3/T4) non calculable, jamais extrapolée"},
        "offre_engagee": _offre_sitadel(session, commune) | {"mois": OFFRE_SITADEL_MOIS,
                          "libelle": "logements collectifs autorisés (Sitadel) — l'offre qui arrive"},
        "millesime": (f"VEFA DVF — {FENETRE_MOIS} mois glissants"),
        "source": "geo-DVF (mutations VEFA, DGFiP) · Sitadel (offre engagée). Chaque chiffre avec son n ; "
                  "sous le seuil, absent, jamais extrapolé.",
    }
