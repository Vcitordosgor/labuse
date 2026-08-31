"""SECTEUR-2 (T4) — couche « Prix du logement neuf (VEFA acté) », aplat par COMMUNE.

DIAGNOSTIC (préalable au code, cf. docs/audit-2026-08/RATTRAPAGE-KF/RAPPORT-KF-2.md, NOTES_VAGUE_C) :
  · ECLN (Enquête Commercialisation des Logements Neufs, SDES) = **métropole seule, N/A pour le 974**
    (jamais à la parcelle, secret statistique). → écartée. AUCUN stock/écoulement n'est servi (l'ECLN
    seule les porterait) : ces colonnes sont ABSENTES, jamais extrapolées.
  · Ce que le 974 porte réellement : les ventes **VEFA** de DVF (`nature_mutation = 'Vente en l'état
    futur d'achèvement'`), maille commune, fenêtre 3 ans (`neuf_vefa_commune`, M101 B2). La VEFA
    n'atteint le seuil d'effectif que dans une PARTIE des 24 communes → l'aplat n'est peint QUE là,
    l'absence est un état normal (jamais un 0 trompeur).

La couche réutilise tout le plombing des aplats commune (spatial_layers `kind='vefa_neuf'`, géométrie
IGN communes974.geojson, servie par `/map/layers.geojson`). La TRANCHE DE PRIX voyage dans `subtype`
(choropleth par `match`, comme ZFANG) ; le détail (prix, n, millésime) dans `attrs` + `name`.
"""
from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy import text
from sqlalchemy.orm import Session

from .dvf_marche import NEUF_VEFA_FENETRE_ANS, neuf_vefa_commune

# Seuil d'effectif : sous ce nombre de ventes VEFA, la médiane commune ne tient pas → commune ABSENTE
# de la couche (jamais peinte à vide). Aligné sur l'honnêteté statistique du profil neuf (M101 B1.3).
SEUIL_VEFA_AFFICHAGE = 10

# Tranches de prix €/m² bâti neuf (bornes documentées, calées sur la plage VEFA réunionnaise observée
# ~4 000–6 000 €/m²) → subtype pour la couleur choropleth.
TRANCHES = [(4000, "moins_4000"), (4500, "4000_4500"), (5000, "4500_5000"),
            (5500, "5000_5500"), (float("inf"), "5500_plus")]
TRANCHE_LIBELLE = {
    "moins_4000": "< 4 000 €/m²", "4000_4500": "4 000–4 500 €/m²", "4500_5000": "4 500–5 000 €/m²",
    "5000_5500": "5 000–5 500 €/m²", "5500_plus": "≥ 5 500 €/m²",
}


def _tranche(prix: float) -> str:
    for borne, cle in TRANCHES:
        if prix < borne:
            return cle
    return "5500_plus"


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def build_vefa_neuf(session: Session, *, commit: bool = True, log=lambda *_: None) -> dict:
    """Reconstruit l'aplat `vefa_neuf` : un item par commune AU-DESSUS du seuil VEFA. Idempotent
    (DELETE + INSERT). Renvoie {'communes': n_peintes, 'absentes': n_sous_seuil}."""
    geo = json.loads((_repo_root() / "frontend" / "public" / "communes974.geojson").read_text("utf-8"))
    # millésime amont RÉEL = la vente VEFA la plus récente prise en compte (jamais « aujourd'hui »).
    dmax = session.execute(text(
        "SELECT to_char(max(date_mutation), 'YYYY-MM-DD') FROM dvf_mutations_parcelle "
        "WHERE nature_mutation = 'Vente en l''état futur d''achèvement' "
        "  AND date_mutation >= (now() - interval '%d years')::date" % NEUF_VEFA_FENETRE_ANS)).scalar()
    session.execute(text("DELETE FROM spatial_layers WHERE kind = 'vefa_neuf'"))
    n_peintes = absentes = 0
    for feat in geo["features"]:
        insee = feat["properties"].get("code")
        commune = feat["properties"].get("nom") or feat["properties"].get("name")
        if not insee:
            continue
        v = neuf_vefa_commune(session, insee)
        prix, n = v.get("mediane_prix_m2_bati"), v.get("n") or 0
        if not prix or n < SEUIL_VEFA_AFFICHAGE:
            absentes += 1
            continue
        cle = _tranche(float(prix))
        attrs = {"prix_m2_neuf": int(prix), "n_ventes": int(n), "maille": "commune",
                 "fenetre_ans": NEUF_VEFA_FENETRE_ANS, "tranche": TRANCHE_LIBELLE[cle],
                 "millesime": (f"VEFA DVF — {NEUF_VEFA_FENETRE_ANS} ans glissants (dernière vente {dmax})"
                               if dmax else f"VEFA DVF — {NEUF_VEFA_FENETRE_ANS} ans glissants"),
                 "stock": None,   # ECLN N/A DOM → aucun stock/écoulement (jamais extrapolé)
                 "source": "geo-DVF (mutations VEFA, DGFiP) — ECLN non couverte outre-mer"}
        session.execute(text(
            "INSERT INTO spatial_layers (kind, subtype, name, commune, geom, attrs) VALUES "
            "('vefa_neuf', :st, :nom, :c, ST_GeomFromGeoJSON(:g), CAST(:a AS jsonb))"),
            {"st": cle, "nom": f"{commune} · {int(prix)} €/m² · {int(n)} ventes VEFA",
             "c": commune, "g": json.dumps(feat["geometry"]), "a": json.dumps(attrs)})
        n_peintes += 1
    if commit:
        session.commit()
    log(f"vefa_neuf : {n_peintes} communes peintes, {absentes} sous le seuil ({SEUIL_VEFA_AFFICHAGE})")
    return {"communes": n_peintes, "absentes": absentes, "millesime": dmax}
