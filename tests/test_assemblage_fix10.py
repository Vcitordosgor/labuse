"""FIX-10 — cas cadastral reproductible, intégralement transactionnel sur labuse_test."""
import os

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from labuse.faisabilite.db import parcel_faisabilite


@pytest.fixture
def session_test():
    engine = create_engine(os.environ["LABUSE_DATABASE_URL"])
    with Session(engine) as db:
        assert db.scalar(text("SELECT current_database()")) == "labuse_test"
        yield db
        db.rollback()
    engine.dispose()


def terrain_decoupe(db, bandes, commune="Saint-Paul"):
    pid = db.scalar(text("""
        INSERT INTO parcels (idu, commune, surface_m2, geom, geom_2975)
        SELECT '97415000ZZ9910', :commune, 5000, ST_Transform(g,4326), g
        FROM (SELECT ST_MakeEnvelope(300000,7650000,300100,7650050,2975) g) s RETURNING id
    """), {"commune": commune})
    if not bandes:
        return pid
    db.execute(text("""
        INSERT INTO spatial_layers (kind, commune, subtype, name, attrs, geom, geom_2975)
        SELECT 'plu_gpu_zone',:commune,fam,code,jsonb_build_object('libelle',code),ST_Transform(g,4326),g
        FROM (SELECT CAST(:fam AS text) fam, CAST(:code AS text) code,
                     CAST(:x1 AS float) x1, CAST(:x2 AS float) x2) z
        CROSS JOIN LATERAL (SELECT ST_MakeEnvelope(300000+x1,7650000,300000+x2,7650050,2975) g) s
    """), [dict(fam=fam, code=code, x1=x1, x2=x2, commune=commune) for fam, code, x1, x2 in bandes])
    return pid


def test_dominante_agricole_avec_au_fermee_et_ruban_u(session_test):
    # Les 48 m² en U3c disparaissent au recul de 3 m. Les 1 452 m² en AU3st sont fermés.
    pid = terrain_decoupe(session_test, [("A", "A", 0, 70), ("AUc", "AU3st", 70, 99.04),
                                        ("U", "U3c", 99.04, 100)])
    ctx, capacite = parcel_faisabilite(session_test, pid)
    assert ctx.zone_fam == "A"
    assert ctx.uau_reelle["m2"] == pytest.approx(48, abs=0.01)
    assert capacite.constructible is False


def test_assiette_mixte_quand_la_zone_ouverte_est_dominante(session_test):
    pid = terrain_decoupe(session_test, [("U", "U3c", 0, 55), ("AUc", "AU3st", 55, 100)])
    ctx, capacite = parcel_faisabilite(session_test, pid)
    assert ctx.zone == "U3c" and capacite.constructible
    assert ctx.portion_servie_m2 == 2750


def test_union_retire_au_fermee_de_la_surface_annoncee(session_test):
    from labuse.assemblage import _capacite_union

    pid = terrain_decoupe(session_test, [("U", "U3c", 0, 55), ("AUc", "AU3st", 55, 100)])
    parcelle = session_test.execute(text("SELECT id, idu, commune, surface_m2 FROM parcels WHERE id=:p"),
                                    {"p": pid}).one()
    union = _capacite_union(session_test, [parcelle])
    assert union["surface_constructible_m2"] == 2750
    assert union["pct_hors_zone"] == 45


def test_bilan_nco_nom_de_zone_naturelle_conserve(session_test):
    from labuse.bilan.reperes import sources_parcelle

    db = session_test
    idu = "97415000ZZ9910"
    terrain_decoupe(db, [("N", "Nco", 0, 65), ("AUc", "2AUb", 65, 99.5),
                         ("AUc", "1AUb", 99.5, 100)], commune="Les Trois-Bassins")
    db.execute(text("INSERT INTO parcel_zone_plu (idu,zone_lib,zone_fam) VALUES (:i,'Nco','N')"), {"i": idu})
    src = sources_parcelle(db, idu)
    assert "zone dominante Nco" in src["non_constructible_motif"]
    assert src["constructible_m2"] == 0


def test_bilan_declasse_servi_mais_capacite_sur_la_portion_ouverte(session_test):
    from labuse.bilan.reperes import garde_fou_bilan, sources_parcelle
    from labuse.faisabilite.potentiel_batir import potentiel_batir

    db = session_test
    pid = terrain_decoupe(db, [("AUc", "AU3st", 0, 86.5), ("U", "U3c", 86.5, 100)])
    idu = "97415000ZZ9910"
    db.execute(text("INSERT INTO parcel_zone_plu (idu,zone_lib,zone_fam) VALUES (:i,'AU3st','AU')"), {"i": idu})
    db.execute(text("INSERT INTO parcel_constructibilite (parcel_id,label,cause) "
                    "VALUES (:p,'declasse_zone_fermee','zone_transition')"), {"p": pid})
    pb = potentiel_batir(db, idu)
    assert pb["constructible"] is True
    source = sources_parcelle(db, idu)
    assert source["non_constructible_motif"] is None
    assert source["constructible_m2"] == 675
    assert "AU3st 86,5 %" in source["zonage"] and "U3c 13,5 %" in source["zonage"]
    assert "seule portion U3c" in source["mention_portion"]
    assert "675 m²" in source["mention_portion"]
    assert "zone à urbaniser fermée" in source["mention_portion"]
    garde = garde_fou_bilan(db, idu)
    assert not garde["non_constructible"]
    assert garde["mention_portion"] == source["mention_portion"]
    assert db.scalar(text("SELECT label FROM parcel_constructibilite WHERE parcel_id=:p"), {"p": pid}) == "declasse_zone_fermee"


@pytest.mark.parametrize(("limite", "surface"), [(85, 750), (99.5, 0)])
def test_bilan_mixte_dominante_n_ignore_la_surface_au_fermee(session_test, limite, surface):
    from labuse.bilan.reperes import sources_parcelle

    db = session_test
    idu = "97415000ZZ9910"
    terrain_decoupe(db, [("N", "N", 0, 65), ("AUc", "AU3st", 65, limite), ("U", "U3c", limite, 100)])
    db.execute(text("INSERT INTO parcel_zone_plu (idu,zone_lib,zone_fam) VALUES (:i,'N','N')"), {"i": idu})
    src = sources_parcelle(db, idu)
    assert src["constructible_m2"] == surface
    if surface:
        assert "seule portion U3c" in src["mention_portion"]
    else:
        assert src["non_constructible_motif"]


def test_comparatif_explique_la_constructibilite_partielle():
    from labuse.exports.blocs.comparatif import _ligne_verdict

    mention = "Capacité calculée sur la seule portion U3c (675 m²)."
    assert mention in _ligne_verdict([{"constructible": True, "mention_portion": mention},
                                      {"constructible": True}])


def test_modele_bilan_lit_derniere_mutation_et_garde_le_repere(session_test):
    from labuse.bilan.reperes import reperes_publics, sources_parcelle

    db = session_test
    terrain_decoupe(db, [("U", "U3c", 0, 100)])
    idu = "97415000ZZ9910"
    db.execute(text("""
        INSERT INTO dvf_mutations_parcelle (id_mutation, id_parcelle, date_mutation, valeur_fonciere, millesime)
        VALUES ('fix10-ancienne',:i,'2022-05-03',110000,2022),
               ('fix10-recente',:i,'2024-08-12',125000,2024)
    """), {"i": idu})
    source = sources_parcelle(db, idu)
    assert source["prix_achat_dvf"] is not None
    assert source["prix_achat_dvf"]["valeur"] == 125000
    assert source["prix_achat_dvf"]["date"] == "2024-08-12"
    assert reperes_publics(db, idu, source)["faisabilite"]["valeur"] > 0
    assert db.scalar(text("SELECT 1")) == 1


def test_comparatif_porte_le_motif_sans_interdiction_generale():
    from labuse.exports.blocs.comparatif import _ligne_verdict

    motif = "Capacité non calculée — zone dominante Nco. La portion ouverte mesure 2 m²."
    html = _ligne_verdict([{"constructible": False, "verdict_motif": motif}])
    assert motif in html
    assert "Non constructible" not in html


def test_lecture_individuelle_reglement_a_verifier(session_test):
    from labuse.bilan.reperes import garde_fou_bilan
    db = session_test
    terrain_decoupe(db, [("AUc", "2AUb", 0, 100)], commune="Les Trois-Bassins")
    # IDU de la commune de la fixture (le régime d'ouverture dépend du code INSEE).
    idu = "97423000ZZ9910"
    db.execute(text("UPDATE parcels SET idu=:i WHERE idu='97415000ZZ9910'"), {"i": idu})
    db.execute(text("INSERT INTO parcel_zone_plu (idu,zone_lib,zone_fam) VALUES (:i,'2AUb','AU')"), {"i": idu})
    garde = garde_fou_bilan(db, idu)
    lecture = garde["lecture_capacite"]
    assert "2AUb" in lecture and "à vérifier" in lecture
    assert garde["surface_a_retenir"] is None
    assert "0 m²" not in lecture


def test_lecture_individuelle_porte_la_surface_retenue(session_test):
    from labuse.bilan.reperes import garde_fou_bilan
    terrain_decoupe(session_test, [("U", "U3c", 0, 100)])
    garde = garde_fou_bilan(session_test, "97415000ZZ9910")
    assert garde["surface_a_retenir"] > 0
    assert "Capacité estimée" in garde["lecture_capacite"]
    assert "reconstruction" in garde["lecture_capacite"]


def test_union_qualifie_seulement_la_part_a_verifier():
    from labuse.faisabilite.lecture_capacite import lecture_union

    zones = [{"zone": "Ub", "sdp_m2": 100}, {"zone": "1AUb", "sdp_m2": 50}]
    lecture, conditionnel = lecture_union(zones, {"1AUb": "Vérifier l'ouverture."}, 150)
    assert conditionnel and "100 m²" in lecture and "50 m²" in lecture and "1AUb" in lecture
    lecture, conditionnel = lecture_union(zones, {"2AUb": "Vérifier le phasage."}, 150)
    assert not conditionnel and "150 m²" in lecture and "2AUb" in lecture


def test_ouverture_conditionnelle_qualifie_aussi_le_bilan(session_test):
    from labuse.bilan.reperes import garde_fou_bilan
    db = session_test
    terrain_decoupe(db, [("AUc", "1AUb", 0, 100)], commune="Les Trois-Bassins")
    idu = "97423000ZZ9910"
    db.execute(text("UPDATE parcels SET idu=:i WHERE idu='97415000ZZ9910'"), {"i": idu})
    garde = garde_fou_bilan(db, idu)
    assert garde["capacite_a_verifier"]
    assert "Hypothèse de reconstruction" in garde["lecture_capacite"]
    assert "commune" in garde["lecture_capacite"].lower()
    assert garde["surface_a_retenir"] is None


def test_aucun_zero_de_bati_conserve_si_lexistant_est_inconnu():
    from labuse.bilan.reperes import bandeau_sans_programme
    _, texte = bandeau_sans_programme({"capacite_terrain_libere_m2": 250,
                                       "capacite_batie_conservee_m2": None})
    assert "0 m² en l'état" not in texte


def test_marque_au_en_attente_reste_visible_meme_sans_couche(session_test):
    from labuse.bilan.reperes import garde_fou_bilan
    db = session_test
    pid = terrain_decoupe(db, [])
    idu = "97415000ZZ9910"
    db.execute(text("INSERT INTO parcel_au_statut (parcel_id,idu,classe,zone_lib,motif) "
                    "VALUES (:p,:i,'declasse_au_statut_inconnu','AUx','Phasage communal à confirmer.')"),
               {"p": pid, "i": idu})
    lecture = garde_fou_bilan(db, idu)["lecture_capacite"]
    assert "Capacité à vérifier" in lecture and "Phasage communal à confirmer" in lecture


def test_couverture_du_bilan_nomme_le_prix_unitaire_du_programme(session_test):
    from labuse.api.bilan import CalculIn, ProduitIn, ProgrammeIn, _hypotheses_bilan
    from labuse.bilan.moteur import EntreesBilan, Moteur
    from labuse.bilan.pdf import construire_html

    corps = CalculIn(programme=ProgrammeIn(sdp=100), produits=[ProduitIn(suv=80, prix_ttc_m2_suv=3000)])
    etude, prix = _hypotheses_bilan(session_test, "97423000ZZ9811", corps)
    assert session_test.scalar(text("SELECT 1")) == 1
    html, _ = construire_html(Moteur().calculer(EntreesBilan()), idu="97423000ZZ9811",
                              etude_reliee=etude, prix_demande=prix)
    assert "3 000 €/m²" in html
    assert "Prix demandé : 3 000" not in html


def test_export_du_constat_quand_la_parcelle_na_aucun_zonage(session_test):
    from labuse.bilan.reperes import garde_fou_bilan
    terrain_decoupe(session_test, [])
    garde = garde_fou_bilan(session_test, "97415000ZZ9910", programme_saisi=False)
    assert "Capacité non calculée" in garde["lecture_capacite"]
    assert garde["surface_a_retenir"] is None
    assert garde["export_constat"]


def test_bandeau_excel_imprime_sur_une_seule_largeur():
    from labuse.bilan.excel import classeur_bilan
    from labuse.bilan.moteur import EntreesBilan
    ws = classeur_bilan(EntreesBilan(), garde_fou={"lecture_capacite": "Capacité à vérifier"}).active
    assert ws.sheet_properties.pageSetUpPr.fitToPage
    assert ws.page_setup.fitToWidth == 1


@pytest.mark.parametrize(("saisie", "attendu"), [(None, "—"), (0, 0), (100, 100)])
def test_excel_surface_vide_distincte_du_zero_saisi(saisie, attendu):
    import io
    from openpyxl import load_workbook
    from labuse.bilan.excel import classeur_bilan_bytes
    from labuse.bilan.moteur import EntreesBilan, Programme
    w = load_workbook(io.BytesIO(classeur_bilan_bytes(EntreesBilan(programme=Programme(sdp=saisie)))),
                      data_only=True)
    row = next(r for r in w.active.values if r[0] == "Surface de plancher")
    assert attendu in row[1:] and (saisie is not None or 0 not in row[1:])
    w.close()


def test_constat_sans_programme_ne_chiffre_pas_le_ca_en_couverture():
    from labuse.bilan.moteur import EntreesBilan, Moteur
    from labuse.bilan.pdf import construire_html
    html, _ = construire_html(Moteur().calculer(EntreesBilan()), idu="97423000ZZ9812",
                              garde_fou={"programme_saisi": False})
    assert "CA TTC : non chiffré" in html
    assert "non calculable — aucun programme saisi" in html


def test_tableau_excel_du_constat_laisse_les_totaux_non_renseignes():
    from io import BytesIO
    from openpyxl import load_workbook
    from labuse.bilan.excel import classeur_bilan_bytes
    from labuse.bilan.moteur import EntreesBilan, Produit
    for produits in ([], [Produit(libelle="Produit 1")]):
        with BytesIO(classeur_bilan_bytes(EntreesBilan(produits=produits))) as contenu:
            wb = load_workbook(contenu, data_only=True)
            cellules = {r[0]: r[4] for r in list(wb.active.values)[3:16]}
            assert [cellules[k] for k in ("Surface vendable", "CA TTC programme", "Nombre de lots")] == ["—"] * 3
            wb.close()


def test_au3st_fermee_ne_devient_pas_une_simple_reserve(session_test):
    from labuse.bilan.reperes import garde_fou_bilan
    db = session_test
    pid = terrain_decoupe(db, [("AUc", "AU3st", 0, 100)])
    db.execute(text("INSERT INTO parcel_zone_plu(idu,zone_lib,zone_fam) VALUES ('97415000ZZ9910','AU3st','AU')"))
    idu = "97415000ZZ9910"
    db.execute(text("INSERT INTO parcel_au_statut (parcel_id,idu,classe,zone_lib,motif) "
                    "VALUES (:p,:i,'conditionnelle_operation','AU3st','Opération à confirmer.')"),
               {"p": pid, "i": idu})
    garde = garde_fou_bilan(db, idu)
    assert "zone à urbaniser fermée" in garde["lecture_capacite"].lower()
    assert not garde["capacite_a_verifier"]
    assert garde["surface_a_retenir"] is None


def test_comparatif_conserve_la_lecture_du_bilan_quand_la_fiche_manque(session_test, monkeypatch):
    from fastapi import HTTPException
    from labuse.api import app as api
    db = session_test
    idu = "97415000ZZ9910"
    terrain_decoupe(db, [])
    def sans_fiche(*args, **kwargs):
        raise HTTPException(404, "Fiche indisponible")
    monkeypatch.setattr(api, "_fiche_servie", sans_fiche)
    data = api.compare(idu + ",97415000ZZ9999", db)
    assert data["echecs"] == [idu]
    assert "Capacité non calculée" in data.get("capacites_sans_fiche", {}).get(idu, "")


def test_hypothese_bati_conserve_reste_lisible_sous_condition(session_test):
    from labuse.bilan.reperes import garde_fou_bilan
    db = session_test
    pid = terrain_decoupe(db, [("AUc", "AU3c", 0, 100)])
    db.execute(text("CREATE TEMP TABLE parcel_residuel (LIKE public.parcel_residuel) ON COMMIT DROP"))
    db.execute(text("INSERT INTO parcel_residuel (parcel_id,sdp_residuelle_m2) VALUES (:p,75)"), {"p": pid})
    garde = garde_fou_bilan(db,"97415000ZZ9910")
    assert garde["surface_a_retenir"] is None
    assert "Hypothèse bâti conservé : 75 m²" in garde["lecture_capacite"]


def test_comparatif_bati_a_verifier_si_les_sources_divergent(session_test, monkeypatch):
    from labuse.api import app as api
    from labuse.exports.blocs.comparatif import _bati_existant
    db = session_test
    idu = "97415000ZZ9910"
    terrain_decoupe(db, [("U", "U3c", 0, 100)])
    db.execute(text("CREATE TEMP TABLE p_model_bati (idu text, emprise_bati_m2 numeric) ON COMMIT DROP"))
    db.execute(text("INSERT INTO p_model_bati VALUES (:i,45)"), {"i": idu})
    monkeypatch.setattr(api, "_fiche_servie", lambda *args: {
        "idu": idu, "commune": "Saint-Paul", "surface_m2": 5000, "etat_bien": "nu",
        "le_bien": {"emprise_batie_m2": 0}})
    row = api.compare(idu, db)["parcels"][0]
    assert row["bati_existant_pct"] is None
    assert "à vérifier" in _bati_existant(row)
