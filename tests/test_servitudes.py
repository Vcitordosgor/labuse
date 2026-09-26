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
    # plu_gpu_prescription : 01 (EBC) + 05 (ER) + typepsc élargis (PIEGES-RISQUES-2 Lot B) qui grèvent la
    # constructibilité ; les typepsc informatifs (07 patrimoine, 16 changement destination…) restent filtrés.
    assert "boisé classé" in sv._detail("plu_gpu_prescription", "01", "Espaces Boisés Classés", None).lower()
    assert "Emplacement réservé" in sv._detail("plu_gpu_prescription", "05", None, {"libelle": "Emplacement réservé"})
    assert sv._PRESCRIPTION_PIEGE == {"01", "05", "08", "15", "17", "18", "19", "22"}
    assert "07" not in sv._PRESCRIPTION_PIEGE and "16" not in sv._PRESCRIPTION_PIEGE   # informatifs, non surfacés
    assert "logements sociaux" in sv._detail("plu_gpu_prescription", "17", "Clause logements aidés", None).lower()
    assert "recul" in sv._detail("plu_gpu_prescription", "15", "Bande de recul", None).lower()
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
    # M137-T — le bloc NON COUVERT (source unique servitudes.NON_COUVERT) est reporté sur « un lot » :
    # jamais un « RAS » muet. PIEGES-RISQUES-2 (Lot A) : la réponse est désormais l'UNION par contrainte.
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
    assert any("Canalisations" in x for x in out["non_couvert"])        # manque dit, jamais silencieux
    # PIEGES-RISQUES-2 (Lot A) — nouvelle forme : union par contrainte + décompte parcelles ; plus de crible.
    assert "items" not in out and "risque" not in out and "seuils" not in out   # ancien crible cascade retiré
    assert out["n_trouvees"] == 1 and out["n_parcelles"] == 1
    assert isinstance(out["contraintes"], list) and isinstance(out["parcelles"], list)


def test_duediligence_ne_lit_plus_la_cascade():
    # PIEGES-RISQUES-2 (Lot A) — l'outil « un lot » ne dépend PLUS de l'ancien scoring : sa fonction ne
    # lit ni dryrun_cascade_results ni parcel_p_score_v2, et délègue à la MÊME source que « une parcelle ».
    # CASSE si on re-branche la cascade sur cet outil (garde-fou du mandat, « grep prouvé »).
    import ast
    import inspect
    from labuse.api import modules
    src = inspect.getsource(modules.duediligence)
    # RETOUCHES-1 (lot A) — le garde vise le CODE, pas la docstring : celle-ci EXPLIQUE justement que
    # l'outil « ne lit PLUS la cascade (`dryrun_cascade_results`) ni le scoring », ce qui piégeait le
    # simple `not in src`. On retire la docstring (contenu brut) avant le contrôle (le corps exécutable
    # reste strict : re-brancher la cascade dans le code re-casse le garde).
    doc = ast.get_docstring(ast.parse(src.strip()).body[0], clean=False) or ""
    code = src.replace(doc, "")
    assert "dryrun_cascade_results" not in code
    assert "parcel_p_score_v2" not in code
    assert "_diligence_dossier" not in code
    assert "contraintes_parcelle" in code                               # même source que « une parcelle »


@pytest.mark.db
def test_lotB_ppr_gradue_alea_deux_modes_et_fiche(db_session):
    # PIEGES-RISQUES-2 (Lot B/C) — PPR zoné (bleu, lu en direct) + aléa par niveau apparaissent dans
    # `contraintes_parcelle` (donc « une parcelle » ET « un lot »), et la fiche §Pièges & risques
    # (`_aleas_block` → `aleas_parcelle`) rend EXACTEMENT la même liste de risques (fiche == outil).
    from labuse.api import app as app_mod
    s = db_session
    idu = "97499000PP0001"
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,'X','ZZ','9', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"), {"i": idu, "w": _WKT})
    ds = s.execute(text("INSERT INTO data_sources (name, status, last_sync_at) "
                        "VALUES ('DEAL test PP0001', 'ok', '2026-09-13') RETURNING id")).scalar()
    s.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, attrs, data_source_id, geom, geom_2975) VALUES "
        "('ppr','PRESCRIPTION','PPR test', '{\"risque\":\"INONDATION\"}', :ds, ST_GeomFromText(:w,4326), "
        " ST_Transform(ST_GeomFromText(:w,4326),2975))"), {"ds": ds, "w": _WKT})
    s.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, attrs, data_source_id, geom, geom_2975) VALUES "
        "('georisque_alea','mouvement_terrain','Aléa test', '{\"niveau\":\"fort\"}', :ds, ST_GeomFromText(:w,4326), "
        " ST_Transform(ST_GeomFromText(:w,4326),2975))"), {"ds": ds, "w": _WKT})
    s.flush()
    effs = [c["effet"] for c in sv.contraintes_parcelle(s, idu) if c["categorie"].startswith("Risque")]
    assert any("Zone bleue PPR inondation" in e for e in effs)              # PPR bleu gradué (Lot B, É2)
    assert any("Aléa mouvement de terrain" in e and "fort" in e for e in effs)   # aléa par niveau (Lot B)
    fiche = app_mod._aleas_block(s, idu)                                    # Lot C — fiche == outil
    assert fiche and sorted(a["libelle"] for a in fiche["liste"]) == sorted(effs)


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
