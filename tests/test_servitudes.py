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


# ───────────── OUTILS-P0-1 (#2) — PPR non classé + quatre états (purs) ─────────────

def test_ppr_ligne_rouge_et_bleu():
    # rouge RÉGLEMENTAIRE (INTERDICTION) → « partie INCONSTRUCTIBLE » (fait opposable) ;
    # bleu (PRESCRIPTION) → « zone bleue … sous prescriptions ».
    r = sv._ppr_ligne("rouge", "inondation", 40)
    assert "INCONSTRUCTIBLE" in r["libelle"] and r["redhibitoire"] is True and r["niveau"] == "rouge"
    assert "hors zone rouge (60 %)" in r["libelle"]   # partie hors rouge existante → DITE
    b = sv._ppr_ligne("bleu", "inondation", 20)
    assert "zone bleue" in b["libelle"] and b["redhibitoire"] is False


def test_ppr_ligne_rouge_total_pas_de_phrase_hors_rouge():
    # OUTILS-LOT-4 (pt 4) — toute la parcelle en zone rouge (pct = 100) : pas de « Partie hors zone
    # rouge (0 %) : constructible » (il n'y a aucune partie hors rouge).
    r = sv._ppr_ligne("rouge", "inondation", 100)
    assert "INCONSTRUCTIBLE" in r["libelle"] and r["redhibitoire"] is True
    assert "hors zone rouge" not in r["libelle"].lower()
    assert "(0 %)" not in r["libelle"]


def test_ppr_ligne_non_classe_ne_dit_plus_inconstructible():
    # OUTILS-P0-1 (#2) — un code PPR non reconnu → « Zonage PPR non classé, à vérifier ». Plus de
    # « partie inconstructible » asséné ; l'hypothèse prudente du calcul (retranchée de l'assiette)
    # RESTE mais est DITE comme une hypothèse (redhibitoire=True côté calcul).
    lig = sv._ppr_ligne("autre", "mouvement de terrain", 30)
    bas = lig["libelle"].lower()
    assert "non classé" in bas and "à vérifier" in bas
    assert "INCONSTRUCTIBLE" not in lig["libelle"]         # plus asséné « partie inconstructible »
    assert "hypothèse" in bas                               # l'hypothèse prudente, DITE comme telle
    assert lig["redhibitoire"] is True                     # le calcul reste prudent (part retranchée)
    assert lig["nature"] == "PPR — zonage non classé"


def test_familles_vide_sans_preuve_est_couverture_inconnue():
    # OUTILS-P0-1 (#2) — items vides SANS preuve de couverture : AUCUNE famille « vérifiée » (fini les
    # dix familles « vérifiées »). Toutes « Couverture inconnue ».
    etats = sv.etats_familles([])
    assert len(etats) == len(sv._FAMILLES_VERIFIEES) == 10
    assert all(e["etat"] == sv.ETAT_INCONNU for e in etats)
    assert sv.familles_verifiees([]) == []                  # le cœur du mandat


def test_famille_couverte_sans_intersection_est_claire():
    # couverture DÉMONTRÉE (famille dans `couvertes`) + rien remonté → « Aucune intersection détectée ».
    couv = {"Risques naturels", "Sols pollués"}
    etats = {e["famille"]: e["etat"] for e in sv.etats_familles([], couvertes=couv)}
    assert etats["Risques naturels"] == sv.ETAT_CLAIR
    assert etats["Préemption"] == sv.ETAT_INCONNU           # non démontrée couverte → inconnue
    assert set(sv.familles_verifiees([], couv)) == couv


def test_contrainte_visible_meme_si_famille_pas_demontree_couverte():
    # une contrainte détectée RESTE visible même si le reste de sa famille n'est couvert qu'en partie
    # (ici : couverture NON démontrée) — CONTRAINTE prime sur la couverture.
    items = [{"categorie": "Risque naturel (PPR / aléa)", "effet": "PPR inondation — zone rouge sur 40 %"}]
    etats = {e["famille"]: e["etat"] for e in sv.etats_familles(items, couvertes=set())}
    assert etats["Risques naturels"] == sv.ETAT_CONTRAINTE


def test_lecture_indisponible_prime_sur_tout():
    etats = {e["famille"]: e["etat"] for e in
             sv.etats_familles([], couvertes={"Risques naturels"}, indisponibles={"Risques naturels"})}
    assert etats["Risques naturels"] == sv.ETAT_INDISPONIBLE   # une panne n'est jamais « clair »


def test_etats_familles_partition_exacte():
    # OUTILS-P0-1 (#2) — chaque famille a EXACTEMENT un état (partition) ; les quatre états couvrent tout.
    items = [{"categorie": "Risque naturel (PPR / aléa)", "effet": "PPR inondation — zone rouge"}]
    etats = sv.etats_familles(items, couvertes={"Sols pollués"}, indisponibles={"Bruit"})
    assert [e["famille"] for e in etats] == [f for f, _ in sv._FAMILLES_VERIFIEES]   # toutes, une fois
    assert all(e["etat"] in (sv.ETAT_CONTRAINTE, sv.ETAT_CLAIR, sv.ETAT_INCONNU, sv.ETAT_INDISPONIBLE) for e in etats)


def test_parite_un_seul_producteur_du_verdict_familles():
    # OUTILS-P0-1 (#2) — PARITÉ. Le verdict « état par famille » (etats_familles / familles_verifiees) a
    # UN SEUL producteur, l'endpoint servitudes_invisibles, et UN SEUL lecteur (l'écran « Pièges et
    # risques — une parcelle », O5Servitudes). L'outil « un lot » et les PDF/miroir ont leur PROPRE moteur
    # (cascade) : ils ne REPRENNENT pas ce verdict. Garde-fou : si un module le réimporte pour le re-servir
    # ailleurs, ce test casse et on revérifie la parité. (Le `familles_verifiees` du Gabarit est distinct.)
    import inspect
    from labuse.api import modules as _mod
    from labuse.exports import miroir as _mir
    for mod in (_mod, _mir):
        src = inspect.getsource(mod)
        assert "etats_familles" not in src
        assert "familles_verifiees" not in src


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
    # RETOUCHES-1 point 7 + DOCS-1 (décision Vic) — la source n'a pas de millésime amont publié → repli
    # d'ingestion DATÉ « au JJ/MM/AAAA ». OUTILS-LOT-4 (pt 10) : le test attendait encore l'ancien
    # « ingéré le JJ/MM/AAAA » ; l'écran a raison — « ingéré le » est un mot de cuisine interne, banni des
    # documents client (cf. millesime_source.libelle_date_source) — on accorde le test sur « au ».
    assert "Risques naturels" in it["effet"] and it["source"] == "SUP test" and it["date"] == "au 10/07/2026"
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
    # PPR-UNIQUE-1 — libellé canonique : « PPR <risque> — zone bleue … à confirmer au règlement du PPR ».
    assert any("zone bleue" in e and "inondation" in e for e in effs)       # PPR bleu (classification unique)
    assert any("à confirmer au règlement du PPR" in e for e in effs)        # renvoi règlement (exigé)
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


# ───────────── OUTILS-P0-1 (#2) — quatre états bout-en-bout (flux DB) ─────────────

_FAM_COUCHES = {f for f, _ in sv._FAMILLES_VERIFIEES}
_WKT_AILLEURS = "POLYGON((55.6 -21.3,55.601 -21.3,55.601 -21.301,55.6 -21.301,55.6 -21.3))"


def _ins_parcelle(s, idu, commune):
    s.execute(text(
        "INSERT INTO parcels (idu, commune, section, numero, geom, geom_2975, surface_m2, centroid, bbox) VALUES "
        "(:i,:c,'ZZ','1', ST_GeomFromText(:w,4326), ST_Transform(ST_GeomFromText(:w,4326),2975), 800, "
        " ST_Centroid(ST_GeomFromText(:w,4326)), ST_Envelope(ST_GeomFromText(:w,4326)))"),
        {"i": idu, "c": commune, "w": _WKT})
    s.flush()


@pytest.mark.db
def test_zone_blanche_aucune_famille_verifiee(db_session):
    # OUTILS-P0-1 (#2) — ZONE BLANCHE : parcelle dans une commune SANS aucune couche ingérée. Aucune
    # famille de couche n'est « vérifiée » (plus de dix familles) ; toutes « Couverture inconnue ».
    s = db_session
    idu = "97499000ZB0001"
    _ins_parcelle(s, idu, "ZoneBlancheP0Test")
    out = sv.servitudes_invisibles(idu, s)
    assert not (set(out["verifie"]) & _FAM_COUCHES)            # aucune famille de couche « vérifiée »
    assert set(out["couverture_inconnue"]) == _FAM_COUCHES     # toutes inconnues faute de preuve
    assert "familles" in out and len(out["familles"]) == len(_FAM_COUCHES) + 1   # + « Procédure PLU »


@pytest.mark.db
def test_couverte_sans_intersection_est_claire(db_session):
    # OUTILS-P0-1 (#2) — COUVERTE SANS INTERSECTION : la couche `sol_pollue` est ingérée POUR la commune
    # (preuve de couverture) mais AILLEURS (n'intersecte pas la parcelle) → famille « Sols pollués »
    # passe en « Aucune intersection détectée ».
    s = db_session
    idu = "97499000CV0001"
    _ins_parcelle(s, idu, "CouvP0Test")
    ds = s.execute(text("INSERT INTO data_sources (name, status, last_sync_at) "
                        "VALUES ('BASIAS test', 'ok', '2026-07-10') RETURNING id")).scalar()
    s.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, commune, data_source_id, geom, geom_2975) VALUES "
        "('sol_pollue','casias','site','CouvP0Test', :ds, ST_GeomFromText(:w,4326), "
        " ST_Transform(ST_GeomFromText(:w,4326),2975))"), {"ds": ds, "w": _WKT_AILLEURS})
    s.flush()
    out = sv.servitudes_invisibles(idu, s)
    assert "Sols pollués" in out["verifie"]                   # couverte (commune) + aucune intersection
    assert "Sols pollués" not in out["couverture_inconnue"]
    # une couverture PARTIELLE : les AUTRES familles (non ingérées pour la commune) restent « inconnues »
    assert "Préemption" in out["couverture_inconnue"]


@pytest.mark.db
def test_radar_plu_panne_non_rien_a_signaler(db_session, monkeypatch):
    # OUTILS-P0-1 (#2) — PANNE DU RADAR PLU : un échec de lecture n'est JAMAIS présenté « rien à
    # signaler ». La famille « Procédure PLU » passe en « Lecture indisponible », hors de `verifie`.
    s = db_session
    idu = "97499000RP0001"
    _ins_parcelle(s, idu, "RadarPanneP0Test")
    import labuse.veille_plu as V

    def _boom(*a, **k):
        raise RuntimeError("radar PLU HS")

    monkeypatch.setattr(V, "entry", _boom)
    out = sv.servitudes_invisibles(idu, s)
    assert out["plu_radar_ok"] is False
    assert "Procédure PLU" in out["lecture_indisponible"]
    assert "Procédure PLU" not in out["verifie"]              # jamais « rien à signaler » sur une panne


@pytest.mark.db
def test_ppr_non_classe_flux(db_session):
    # OUTILS-P0-1 (#2) — PPR NON CLASSÉ : un code non reconnu ('i', hérité Saint-Philippe) s'affiche
    # « Zonage PPR non classé, à vérifier », plus « partie inconstructible » ; l'hypothèse prudente reste.
    s = db_session
    idu = "97499000NC0001"
    _ins_parcelle(s, idu, "X")
    ds = s.execute(text("INSERT INTO data_sources (name, status, last_sync_at) "
                        "VALUES ('DEAL NC test', 'ok', '2026-09-13') RETURNING id")).scalar()
    s.execute(text(
        "INSERT INTO spatial_layers (kind, subtype, name, attrs, data_source_id, geom, geom_2975) VALUES "
        "('ppr','i','PPR Saint-Philippe', '{\"risque\":\"MOUVEMENT_DE_TERRAIN\"}', :ds, ST_GeomFromText(:w,4326), "
        " ST_Transform(ST_GeomFromText(:w,4326),2975))"), {"ds": ds, "w": _WKT})
    s.flush()
    effs = [c["effet"] for c in sv.contraintes_parcelle(s, idu) if c["categorie"].startswith("Risque")]
    bas = " · ".join(effs).lower()
    assert "non classé" in bas and "à vérifier" in bas        # le libellé honnête
    assert "inconstructible" not in bas                       # plus « partie inconstructible » asséné
    assert "hypothèse" in bas                                 # hypothèse prudente DITE comme telle
