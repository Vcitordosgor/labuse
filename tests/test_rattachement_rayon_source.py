"""RADAR-SOURCES-3 (mandat BANC-RAYON-1, Lot B) — le rayon de rattachement est propre à la PRÉCISION
de la position, jamais à la source :

  · une position À L'ADRESSE (floutée ~50 m, `source_position == 'address'`, p.ex. Bien'ici) cherche
    dans un rayon SERRÉ de 60 m ;
  · une position de QUARTIER (centroïde ville, `source_position` absent / 'city', p.ex. Leboncoin)
    cherche dans 150 m — INCHANGÉ (c'est le verrou demandé pour Leboncoin).

Deux vérités gravées :
  (a) `_rayon` rend 60 m pour une position à l'adresse, 150 m sinon — et les constantes valent bien
      60 et 150 (verrou Leboncoin : RAYON_M ne doit jamais bouger sous les pieds de Leboncoin) ;
  (b) comportement (DB) : une parcelle à ~100 m du point est CANDIDATE pour une position de quartier
      (dans 150 m) et NE L'EST PAS pour une position à l'adresse (hors 60 m) → le rayon serré fait bien
      fondre l'univers. Le rattachement AUTOMATIQUE n'a lieu que s'il reste UNE SEULE candidate.
"""
from __future__ import annotations

import uuid

import pytest
from sqlalchemy import text

from labuse.db import session_scope
from labuse.pige import rattachement_html as rh


# ── (a) le choix du rayon — pur, sans DB (tourne toujours, y compris au hook) ──────────────────────

def test_rayon_leboncoin_reste_150_bienici_60():
    """VERROU LEBONCOIN — RAYON_M = 150 (jamais modifié) ; la position à l'adresse resserre à 60 m."""
    assert rh.RAYON_M == 150, "le rayon des positions de QUARTIER (Leboncoin) doit rester 150 m"
    assert rh.RAYON_M_ADRESSE == 60, "le rayon des positions À L'ADRESSE (Bien'ici) doit être 60 m"
    # Leboncoin : pas de source_position (ou 'city') → 150 m.
    assert rh._rayon({"type": "maison"}) == 150
    assert rh._rayon({"type": "maison", "source_position": "city"}) == 150
    # Bien'ici : position à l'adresse → 60 m.
    assert rh._rayon({"type": "maison", "source_position": "address"}) == 60


# ── (b) comportement : le rayon serré fait fondre l'univers (DB) ───────────────────────────────────

COMMUNE = "RadarRayonVille"
INSEE = "97497"
# PETITE parcelle (~20 m de côté) pour que la DISTANCE au point soit nette (ST_DWithin mesure au bord
# de la géométrie, pas au centroïde). PT_PROCHE est dans la parcelle ; PT_A_100M est ~110 m au sud.
WKT = "POLYGON((55.5000 -21.2000,55.5002 -21.2000,55.5002 -21.2002,55.5000 -21.2002,55.5000 -21.2000))"
PT_PROCHE = (55.5001, -21.2001)            # dans la parcelle → ~0 m
PT_A_100M = (55.5001, -21.2012)            # ~110 m au sud du bord : hors 60 m, dans 150 m


@pytest.fixture
def seed(engine):
    from labuse import communes
    from labuse.pige import intake
    tag = uuid.uuid4().hex[:4].upper()
    idu = f"{INSEE}0{tag}0001"[:14].ljust(14, "0")
    ajoutee = COMMUNE not in communes._OFFICIAL_BY_NAME
    if ajoutee:
        communes._OFFICIAL_BY_NAME[COMMUNE] = INSEE
        intake._COMMUNE_PAR_NORME[intake._norm(COMMUNE)] = COMMUNE
    with session_scope() as s:
        s.execute(text(
            "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox)"
            " VALUES (:i,:c,'ZZ','1',ST_GeomFromText(:w,4326),ST_Transform(ST_GeomFromText(:w,4326),2975),"
            " 500, ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
            {"i": idu, "c": COMMUNE, "w": WKT})
        s.execute(text("INSERT INTO p_model_bati (idu, emprise_bati_m2) VALUES (:i, 100)"), {"i": idu})
    yield {"idu": idu}
    with session_scope() as s:
        s.execute(text("DELETE FROM p_model_bati WHERE idu = :i"), {"i": idu})
        s.execute(text("DELETE FROM parcels WHERE idu = :i"), {"i": idu})
    if ajoutee:
        communes._OFFICIAL_BY_NAME.pop(COMMUNE, None)
        intake._COMMUNE_PAR_NORME.pop(intake._norm(COMMUNE), None)


@pytest.mark.db
def test_parcelle_a_100m_candidate_en_quartier_pas_a_l_adresse(seed):
    """La parcelle de 500 m² est à ~100 m du point de l'annonce :
      · position de quartier (150 m) → elle est CANDIDATE (surface) ;
      · position à l'adresse (60 m)  → elle est HORS rayon → aucune candidate.
    On prouve le resserrement par le détecteur de surface (le même que la cascade)."""
    with session_scope() as db:
        hits_quartier = rh._crit_surface(db, PT_A_100M[0], PT_A_100M[1], COMMUNE, 500.0, rayon=rh.RAYON_M)
        hits_adresse = rh._crit_surface(db, PT_A_100M[0], PT_A_100M[1], COMMUNE, 500.0, rayon=rh.RAYON_M_ADRESSE)
    assert seed["idu"] in hits_quartier, "à 150 m (quartier), la parcelle à ~100 m doit être candidate"
    assert seed["idu"] not in hits_adresse, "à 60 m (adresse), la parcelle à ~100 m doit être EXCLUE"


@pytest.mark.db
def test_cascade_rattache_a_l_adresse_quand_une_seule_candidate(seed):
    """RATTACHEMENT AUTOMATIQUE — un bien à position À L'ADRESSE dont le point tombe DANS la parcelle :
    surface (500=500) ∩ emprise (100 pour 80 m² hab) convergent sur l'unique parcelle du rayon serré
    → rattachee/source. C'est exactement « une seule parcelle candidate »."""
    rec = {"type": "maison", "commune": COMMUNE, "lng": PT_PROCHE[0], "lat": PT_PROCHE[1],
           "surface_terrain": 500.0, "surface_hab": 80.0, "source_position": "address"}
    with session_scope() as db:
        out = rh.rattacher(db, rec)
    assert out["etat"] == "rattachee" and out["niveau"] == "source" and out["idu"] == seed["idu"]


@pytest.mark.db
def test_cascade_a_l_adresse_point_a_100m_reste_a_instruire(seed):
    """Le MÊME bien mais dont la position à l'adresse tombe à ~100 m de la parcelle : hors du rayon
    serré de 60 m, plus aucune candidate → non rattaché (quartier), jamais un pin faux."""
    rec = {"type": "maison", "commune": COMMUNE, "lng": PT_A_100M[0], "lat": PT_A_100M[1],
           "surface_terrain": 500.0, "surface_hab": 80.0, "source_position": "address"}
    with session_scope() as db:
        out = rh.rattacher(db, rec)
    assert out["etat"] != "rattachee", "hors 60 m, aucune candidate → pas de rattachement automatique"
