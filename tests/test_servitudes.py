"""O5 — SERVITUDES INVISIBLES : décodage des couches dormantes, sourcées + datées.

SUP décodée en effet concret ; dédup ; couches non ingérées dites « non couvertes » (jamais faux RAS).
"""
from __future__ import annotations

import pytest
from sqlalchemy import text

from labuse.api import servitudes as sv


# ───────────────────────── décodage (pur) ─────────────────────────

def test_sup_decode_pm1_risques():
    d = sv._detail("sup", "pm1", "PM1_PPR_i_mvt", {"typeass": "Enveloppe des zonages réglementaires"})
    assert "Risques naturels (PPR)" in d and "Enveloppe" in d


def test_sup_i3_gaz():
    assert "gaz" in sv._detail("sup", "I3", None, None).lower()


def test_sol_pollue_sis():
    assert "SIS" in sv._detail("sol_pollue", "sis", None, None)


def test_bruit_categorie():
    assert "catégorie 3" in sv._detail("bruit_route", "cat3", None, None)


def test_sup_inconnu_ne_ment_pas():
    d = sv._detail("sup", "ZZ9", None, None)
    assert "ZZ9" in d          # code inconnu affiché tel quel, jamais inventé


def test_non_couvert_liste_les_manques():
    assert any("Canalisations" in x for x in sv._NON_COUVERT)


def test_znieff_couverte_et_type_distingue():
    # M137-U — ZNIEFF ingérée = couche servie (dans _KINDS, plus dans NON COUVERT) ; le libellé
    # DISTINGUE type I / type II (ils ne pèsent pas pareil en instruction) et dit que ce n'est pas un blocage.
    assert "znieff" in sv._KINDS
    assert not any("ZNIEFF" in x for x in sv.NON_COUVERT)      # servie → sortie du NON COUVERT
    d1 = sv._detail("znieff", "type I", "Pierrefonds", None)
    d2 = sv._detail("znieff", "type II", "Grand Étang", None)
    assert "type I" in d1 and "Pierrefonds" in d1 and "recours" in d1.lower() and "n'interdit pas" in d1
    assert "type II" in d2 and "Grand Étang" in d2


def test_peb_remis_dans_les_couvertes():
    # RECETTE-3 (T5, décision Vic) — RENVERSE M137-T : la couche `peb` est désormais peuplée
    # (aéroport Roland Garros, zones A/B/C/D en base) → REMISE dans _KINDS et RETIRÉE du NON COUVERT.
    assert "peb" in sv._KINDS
    joined = " · ".join(sv.NON_COUVERT)
    assert "Exposition au Bruit" not in joined              # servi → sorti du NON COUVERT
    for attendu in ("Procédures PLU", "Canalisations", "hors GPU"):
        assert attendu in joined
    # LOT3 (OUTILS-FINALE) — RNIC copro RETIRÉ du NON COUVERT : il EST ingéré (rnic_coproprietes) et
    # surfacé (CoproprietesBlock). L'y laisser était un faux « non couvert » (comme ZNIEFF avant M137-U).
    assert not any("Copropriété" in x or "RNIC" in x for x in sv.NON_COUVERT)
    # SUP : chiffre honnête (8 familles présentes sur 417) ; l'ancien « ~17 familles » (faux) a disparu.
    assert "8 familles" in joined and "417" in joined and "17 familles" not in joined


def test_recette3_nouveaux_kinds_couverts_et_decodes():
    # RECETTE-3 (T5) — les six couches rajoutées sont dans _KINDS et décodées en effet concret.
    for k in ("dpu", "dpf", "zone_humide", "ens", "plu_gpu_prescription", "peb"):
        assert k in sv._KINDS
    assert "préemption" in sv._detail("dpu", "dpu", "DPU", None).lower()
    assert "renforcé" in sv._detail("dpu", "dpu_renforce", None, None).lower()
    assert "recul" in sv._detail("dpf", "cours_eau", "Ravine Vincendo", None).lower()
    assert "Zone humide" in sv._detail("zone_humide", "habitats_2011", "bassin", None)
    assert "Espace naturel protégé" in sv._detail("ens", "reserve_naturelle", "Etang de Saint-Paul", None)
    # plu_gpu_prescription : seuls 01 (EBC) et 05 (ER) sont des pièges ; les autres typepsc filtrés au rendu.
    assert "boisé classé" in sv._detail("plu_gpu_prescription", "01", "Espaces Boisés Classés", None).lower()
    assert "Emplacement réservé" in sv._detail("plu_gpu_prescription", "05", None, {"libelle": "Emplacement réservé"})
    assert sv._PRESCRIPTION_PIEGE == {"01", "05"}
    # PEB décodé par zone (attrs.zone prioritaire sur subtype).
    assert "Zone C" in sv._detail("peb", "c", "PEB Roland Garros", {"zone": "C"})


# ───────────────────────── flux DB ─────────────────────────

_WKT = "POLYGON((55.45 -20.9,55.451 -20.9,55.451 -20.901,55.45 -20.901,55.45 -20.9))"


@pytest.mark.db
def test_flux_sup_sourcee_datee_et_dedup(db_session):
    s = db_session
    idu = "97499000SV0001"
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"), {"i": idu, "w": _WKT})
    ds = s.execute(text("INSERT INTO data_sources (name, status, last_sync_at) "
                        "VALUES ('SUP test', 'ok', '2026-07-10') RETURNING id")).scalar()
    # deux enveloppes de la MÊME SUP → une seule ligne (dédup)
    for gen in ("gen1", "gen2"):
        s.execute(text(
            "INSERT INTO spatial_layers (kind, subtype, name, attrs, data_source_id, geom, geom_2975) VALUES "
            "('sup','pm1',:n, '{\"typeass\":\"Enveloppe\"}', :ds, ST_GeomFromText(:w,4326), "
            " ST_Transform(ST_GeomFromText(:w,4326),2975))"),
            {"n": f"PM1_{gen}", "ds": ds, "w": _WKT})

    out = sv.servitudes_invisibles(idu, s)
    assert out["n"] == 1                                   # dédup : gen1+gen2 = 1 ligne
    it = out["servitudes"][0]
    assert "Risques naturels" in it["effet"] and it["source"] == "SUP test" and it["date"] == "2026-07-10"
    assert out["non_couvert"]                              # manques listés


@pytest.mark.db
def test_duediligence_reporte_non_couvert_sur_le_lot(db_session):
    # M137-T (fusion outil Risques) — le bloc NON COUVERT (source unique servitudes.NON_COUVERT) est
    # REPORTÉ sur l'entrée « un lot » : jamais un « RAS » muet, même sans flag cascade. + ménage q/a_score.
    from labuse.api import modules
    s = db_session
    idu = "97499000DD0001"
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"), {"i": idu, "w": _WKT})
    s.flush()
    out = modules.duediligence(modules.DueDiligenceIn(refs=idu), s)
    assert out["non_couvert"] == sv.NON_COUVERT
    # RECETTE-3 (T5) — le PEB est désormais servi (kind), le manque témoin devient les canalisations.
    assert any("Canalisations" in x for x in out["non_couvert"])        # manque dit, jamais silencieux
    it = out["items"][0]
    assert "q_score" not in it and "a_score" not in it                  # vestige mort retiré du SELECT


@pytest.mark.db
def test_flux_ras_honnete(db_session):
    s = db_session
    idu = "97499000SV0002"
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','2', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"), {"i": idu, "w": _WKT})
    out = sv.servitudes_invisibles(idu, s)
    assert out["n"] == 0 and "Aucune servitude" in out["synthese"]
    assert "ne vaut pas absence réelle" in out["avertissement"]   # jamais un faux RAS définitif
